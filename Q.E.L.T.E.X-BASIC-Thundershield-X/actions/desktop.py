import os
import sys
import json
import shutil
import subprocess
import tempfile
import platform
from pathlib import Path
from datetime import datetime

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

_OS = platform.system()

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_api_key() -> str:
    """Fetches the API key dynamically on each call to prevent caching and thread-locking."""
    path = _get_base_dir() / "config" / "api_keys.json"
    if not path.exists():
        print(f"[Desktop] ❌ Configuration file missing: {path}")
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "")
    except Exception as e:
        print(f"[Desktop] ❌ Error reading api_keys.json: {e}")
        return ""
    
def _get_desktop() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DESKTOP_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    fallback = Path.home() / "Desktop"
    try:
        if fallback.exists(): return fallback
    except Exception: pass
    return Path.home()

def _build_sandbox() -> dict:
    import time
    safe_builtins = {
        "print": print,
        "len": len, "str": str, "int": int, "float": float,
        "bool": bool, "list": list, "dict": dict, "tuple": tuple,
        "range": range, "enumerate": enumerate, "sorted": sorted,
        "isinstance": isinstance, "hasattr": hasattr, "getattr": getattr,
        "max": max, "min": min, "sum": sum, "abs": abs,
        "zip": zip, "map": map, "filter": filter,
    }
    sandbox = {
        "__builtins__": safe_builtins,
        "Path": Path,
        "time": time,
        "shutil": type("shutil", (), {
            "copy2":      shutil.copy2,
            "copytree":   shutil.copytree,
            "disk_usage": shutil.disk_usage,
        })(),
        "os_path": os.path,  
    }
    if _PYAUTOGUI:
        sandbox["pyautogui"] = pyautogui
    if _OS == "Windows":
        try:
            import ctypes
            import winreg
            sandbox["ctypes"] = ctypes
            sandbox["winreg"] = type("winreg", (), {
                "OpenKey":      winreg.OpenKey,
                "QueryValueEx": winreg.QueryValueEx,
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            })()
        except Exception: pass
    return sandbox

def _strip_markdown(code: str) -> str:
    clean_code = str(code).strip()
    if clean_code.startswith("```"):
        lines = clean_code.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean_code = "\n".join(lines).strip()
    return clean_code

def _execute_generated_code(code: str, player=None) -> str:
    if not code or str(code).strip() == "UNSAFE":
        return "This action cannot be performed safely."
    try:
        clean_code = _strip_markdown(code)
    except Exception: return "Failed to parse generation stream."
    sandbox      = _build_sandbox()
    output_lines = []
    sandbox["__builtins__"]["print"] = lambda *a: output_lines.append(" ".join(str(x) for x in a))
    try:
        exec(compile(clean_code, "<qeltex_desktop>", "exec"), sandbox)
        return "\n".join(output_lines) if output_lines else "Done."
    except Exception as e:
        print(f"[Desktop] Exec error: {e}\nCode:\n{clean_code[:300]}")
        return f"Execution error: {e}"

def _ask_gemini_for_desktop_action(task: str) -> str:
    try:
        from google import genai
        HAS_GEMINI_DESKTOP = True
    except ImportError: HAS_GEMINI_DESKTOP = False
    if not HAS_GEMINI_DESKTOP:
        print("[Desktop] ❌ Missing installation: 'google-genai' is absent.")
        return "UNSAFE"
        
    api_key = _get_api_key()
    if not api_key: return "UNSAFE"
    try:
        client = genai.Client(api_key=api_key)
        desktop = str(_get_desktop())
        os_specific = ""
        if _OS == "Windows": os_specific = "- ctypes (Windows API calls, read-only)\n- winreg (registry READ only)"
        else: os_specific = "- subprocess is NOT available; use pyautogui or Path only"
        prompt = f"You are a desktop automation assistant.\nCurrent OS: {_OS}\nDesktop path: {desktop}\n\nGenerate safe Python code to accomplish the task below.\nAllowed modules ONLY:\n- pyautogui\n- pathlib.Path\n- shutil.copy2, copytree, disk_usage\n- os_path\n- time.sleep\n{os_specific}\n\nHard rules:\n- NO file deletion\n- NO subprocess calls\n- NO exec() or eval()\n- NO import statements\n- NO file write operations\n- If unsafe, output exactly: UNSAFE\n\nOutput ONLY the Python code. No explanation, no markdown.\n\nTask: {task}"
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        code = response.text.strip() if response.text else "UNSAFE"
        code = _strip_markdown(code)
        return code
    except Exception as e:
        print(f"[Desktop] AI code generation failed: {e}")
        return "UNSAFE"

def set_wallpaper(image_path: str) -> str:
    try:
        path = Path(image_path).expanduser().resolve()
    except Exception:
        return "Invalid file path format, sir."
    if not path.exists():
        return f"Image not found: {image_path}"
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return f"Unsupported format: {path.suffix}. Use jpg, png, bmp or webp."
    try:
        if _OS == "Windows":
            import ctypes
            if path.suffix.lower() in {".webp", ".png"}:
                try:
                    from PIL import Image
                    pictures_dir = Path(os.environ.get("USERPROFILE", tempfile.gettempdir())) / "Pictures"
                    pictures_dir.mkdir(exist_ok=True)
                    bmp_path = pictures_dir / f"qeltex_wp_{int(datetime.now().timestamp())}.bmp"
                    
                    img = Image.open(path)
                    img.convert("RGB").save(bmp_path, "BMP")
                    path = bmp_path
                except ImportError:
                    print("[Desktop] Pillow missing. Cannot convert png/webp to bmp on Windows.")
                    print("[Desktop] Please execute command: pip install Pillow")
                except Exception as img_err:
                    print(f"[Desktop] Image conversion matrix failed: {img_err}")
            try:
                ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3)
                return f"Wallpaper set: {path.name}"
            except Exception as ctypes_err:
                return f"Windows API failed to apply wallpaper: {ctypes_err}"
        elif _OS == "Darwin":
            script = f'tell application "System Events" to tell every desktop to set picture to POSIX file "{path}"'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            return f"Wallpaper set: {path.name}"
        else:
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            uri = f"file://{path}"
            if "gnome" in desktop_env or "unity" in desktop_env:
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], capture_output=True, timeout=5)
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], capture_output=True, timeout=5)
            elif "kde" in desktop_env:
                script = f'var allDesktops = desktops(); for (var i = 0; i < allDesktops.length; i++) {{ d = allDesktops[i]; d.wallpaperPlugin = "org.kde.image"; d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"]; d.writeConfig("Image", "file://{path}"); }}'
                subprocess.run(["qdbus", "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script], capture_output=True, timeout=5)
            elif "xfce" in desktop_env:
                subprocess.run(["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor0/workspace0/last-image", "-s", str(path)], capture_output=True, timeout=5)
            else:
                result = subprocess.run(["feh", "--bg-scale", str(path)], capture_output=True, timeout=5)
                if result.returncode != 0:
                    return f"Could not set wallpaper automatically on {desktop_env}. Try manually or install 'feh'."
            return f"Wallpaper set: {path.name}"
    except Exception as e:
        return f"Could not set wallpaper: {e}"

def set_wallpaper_from_url(url: str) -> str:
    try:
        import urllib.request
        import random
        import ssl
        input_string = str(url or "").strip()
        
        if input_string.startswith("qeltex_WALLPAPER:"):
            _, keyword = input_string.split(":", 1)
            random_num = random.randint(1, 1084)
            base_url = "https://picsum.photos"
            full_url = f"{base_url}/id/{random_num}/1920/1080"
            print(f"[Desktop] Extracted short tag: '{keyword}'. Compiled safe local URL: {full_url}")
        else:
            full_url = input_string

        url_just_path = full_url.split("?")[0]
        suffix = Path(url_just_path).suffix or ".jpg"
        if suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}: 
            suffix = ".jpg"
            
        pictures_dir = Path(os.environ.get("USERPROFILE", tempfile.gettempdir())) / "Pictures"
        pictures_dir.mkdir(exist_ok=True)
        tmp = pictures_dir / f"qeltex_download_{int(datetime.now().timestamp())}{suffix}"
        
        req = urllib.request.Request(
            full_url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
            }
        )
        
        try: 
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            ssl_handler = urllib.request.HTTPSHandler(context=ctx)
            cookie_handler = urllib.request.HTTPCookieProcessor()
            opener = urllib.request.build_opener(ssl_handler, cookie_handler)
            
            with opener.open(req, timeout=10) as response:
                with open(tmp, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
        except Exception as dl_err: 
            return f"Failed to download wallpaper image from URL matrix: {dl_err}"
            
        if tmp.exists() and tmp.stat().st_size > 1000:
            result = set_wallpaper(str(tmp))
            return result
        else:
            if tmp.exists():
                tmp.unlink()
            return "Download failed: File is empty, too small or corrupted."
            
    except Exception as e: 
        return f"Could not download wallpaper: {e}"


def get_current_wallpaper() -> str:
    try:
        if _OS == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop")
            val, _ = winreg.QueryValueEx(key, "Wallpaper")
            winreg.CloseKey(key)
            return f"Current wallpaper: {val}"
        elif _OS == "Darwin":
            script = 'tell application "System Events" to get picture of desktop 1'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            stdout_str = result.stdout.strip() if result.stdout else "Unknown"
            return f"Current wallpaper: {stdout_str}"
        else:
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            if "gnome" in desktop_env or "unity" in desktop_env:
                result = subprocess.run(["gsettings", "get", "org.gnome.desktop.background", "picture-uri"], capture_output=True, text=True, timeout=5)
                stdout_str = result.stdout.strip() if result.stdout else "Unknown"
                return f"Current wallpaper: {stdout_str}"
            return "Wallpaper path retrieval not supported for this desktop environment, sir."
    except Exception as e: return f"Could not get wallpaper: {e}"

FILE_TYPE_MAP = {
    "Images":      {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
    "Documents":   {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp"},
    "Videos":      {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Music":       {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Archives":    {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Code":        {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".cpp", ".java", ".cs", ".go", ".rs", ".sh", ".php"},
    "Executables": {".exe", ".msi", ".bat", ".cmd", ".sh", ".appimage", ".deb", ".rpm"},
}

_SKIP_EXTENSIONS = {
    "Windows": {".lnk", ".url"},
    "Darwin":  {".webloc"},
    "Linux":   {".desktop"},
}

def organize_desktop(mode: str = "by_type") -> str:
    try:
        desktop = _get_desktop()
        if not desktop.exists(): return "Desktop folder does not exist, sir."
        clean_mode = str(mode or "by_type").lower().strip()
        skip_exts     = _SKIP_EXTENSIONS.get(_OS, set())
        moved, skipped = [], []
        for item in desktop.iterdir():
            try:
                if item.is_dir() or item.name.startswith("."): continue
                if item.suffix.lower() in skip_exts: continue
                if clean_mode == "by_date":
                    try: stat_val = item.stat().st_mtime
                    except Exception: continue
                    mtime       = datetime.fromtimestamp(stat_val)
                    folder_name = mtime.strftime("%Y-%m")
                else:
                    ext         = item.suffix.lower()
                    folder_name = "Others"
                    for folder, exts in FILE_TYPE_MAP.items():
                        if ext in exts:
                            folder_name = folder
                            break
                target_dir = desktop / folder_name
                target_dir.mkdir(exist_ok=True)
                new_path = target_dir / item.name
                if new_path.exists():
                    skipped.append(item.name)
                    continue
                shutil.move(str(item), str(new_path))
                moved.append(f"{item.name} → {folder_name}/")
            except (PermissionError, FileNotFoundError): continue
        result = f"Desktop organized ({clean_mode}): {len(moved)} files moved."
        if moved:
            result += "\n" + "\n".join(moved[:8])
            if len(moved) > 8: result += f"\n... and {len(moved) - 8} more."
        if skipped: result += f"\n{len(skipped)} file(s) skipped (name conflict)."
        return result
    except Exception as e: return f"Failed to organize desktop: {e}"


def list_desktop() -> str:
    try:
        desktop = _get_desktop()
        if not desktop.exists(): return "Desktop folder does not exist, sir."
        items   = []
        for item in sorted(desktop.iterdir()):
            if item.name.startswith("."): continue
            if item.is_dir():
                try: count = len(list(item.iterdir()))
                except Exception: count = "?"
                items.append(f"📁 {item.name}/ ({count} items)")
            else:
                try:
                    size = item.stat().st_size
                    size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
                    items.append(f"📄 {item.name} ({size_str})")
                except Exception: continue
        if not items: return "Desktop is empty."
        return f"Desktop ({len(items)} items):\n" + "\n".join(items)
    except Exception as e: return f"Failed to list desktop items: {e}"

def clean_desktop() -> str:
    try:
        desktop = _get_desktop()
        if not desktop.exists(): return "Desktop folder does not exist, sir."
        skip_exts   = _SKIP_EXTENSIONS.get(_OS, set())
        today       = datetime.now().strftime("%Y-%m-%d")
        archive_dir = desktop / f"Desktop Archive {today}"
        archive_dir.mkdir(exist_ok=True)
        moved = 0
        for item in desktop.iterdir():
            try:
                if item.is_dir() or item.name.startswith("."): continue
                if item.suffix.lower() in skip_exts: continue
                if item.name == archive_dir.name: continue
                new_path = archive_dir / item.name
                if not new_path.exists():
                    shutil.move(str(item), str(new_path))
                    moved += 1
            except Exception: continue
        return f"Desktop cleaned: {moved} files archived to '{archive_dir.name}'."
    except Exception as e: return f"Could not clean desktop: {e}"


def get_desktop_stats() -> str:
    try:
        desktop = _get_desktop()
        if not desktop.exists(): return "Desktop folder does not exist, sir."
        files      = []
        folders    = []
        for i in desktop.iterdir():
            try:
                if i.is_file(): files.append(i)
                elif i.is_dir(): folders.append(i)
            except Exception: continue
        total_size = 0
        for f in files:
            try:
                if f.exists(): total_size += f.stat().st_size
            except Exception: continue
        size_str   = f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / 1024 / 1024:.1f} MB"
        return f"Desktop stats ({_OS}):\n  Files   : {len(files)}\n  Folders : {len(folders)}\n  Size    : {size_str}\n  Path    : {desktop}"
    except Exception as e: return f"Could not gather desktop stats: {e}"

def desktop_control(parameters: dict = None, response=None, player=None, session_memory=None) -> str:
    params = parameters or {}
    if isinstance(params, str):
        try: params = json.loads(params)
        except Exception: params = {"action": "task", "task": parameters}
    if not isinstance(params, dict): params = {}
    
    action = str(params.get("action", "")).lower().strip()
    task   = str(params.get("task", "")).strip()
    url_val = str(params.get("url", "")).strip()
    path_val = str(params.get("path", "")).strip()
    
    check_str = f"{action} {task} {url_val} {path_val}".lower()

    if player and hasattr(player, "write_log"):
        try: 
            log_text = "local_matrix" if any(kw in f"{task} {url_val} {path_val}".lower() for kw in ["lokal", "standard", "windows", "pc"]) else "url_matrix"
            player.write_log(f"[desktop] action triggered: {log_text}")
        except Exception: pass

    if any(kw in f"{task} {url_val} {path_val}".lower() for kw in ["url", "nett", "online", "internett", "random"]):
        if any(kw in check_str for kw in ["wallpaper", "bakgrunn", "background", "skrivebord"]):
            return set_wallpaper_from_url("qeltex_WALLPAPER:random")
        
    if any(kw in f"{task} {url_val} {path_val}".lower() for kw in ["lokal", "standard", "windows", "pc"]):
        if any(kw in check_str for kw in ["wallpaper", "bakgrunn", "background", "skrivebord"]):
            try:
                import random
                wp_root = Path(r"C:\Windows\Web\Wallpaper")
                if wp_root.exists():
                    valid_exts = {".jpg", ".jpeg", ".png", ".bmp"}
                    local_images = [str(p) for p in wp_root.rglob("*") if p.is_file() and p.suffix.lower() in valid_exts]
                    if local_images:
                        return set_wallpaper(random.choice(local_images))
            except Exception:
                pass

    if any(o in check_str for o in ["open", "åpne", "vis"]):
        if any(w in check_str for w in ["wallpaper", "bakgrunn", "background", "skrivebord"]):
            try:
                if _OS == "Windows":
                    subprocess.Popen("explorer.exe ms-settings:personalization-background", shell=True)
                    return "Opening Windows background settings panel, sir."
            except Exception as open_err:
                return f"Failed to open settings panel: {open_err}"

    if "qeltex_WALLPAPER:" in task or "qeltex_WALLPAPER:" in action:
        incoming_tag = task if "qeltex_WALLPAPER:" in task else action
        return set_wallpaper_from_url(incoming_tag)
        
    try:
        if action == "wallpaper":
            path = str(params.get("path", "")).strip()
            return set_wallpaper(path) if path else "No image path provided."
        elif action == "wallpaper_url":
            url = str(params.get("url", "")).strip()
            return set_wallpaper_from_url(url) if url else "No URL provided."
        elif action == "current_wallpaper":
            return get_current_wallpaper()
        elif action == "organize":
            return organize_desktop(str(params.get("mode", "by_type")))
        elif action == "clean":
            return clean_desktop()
        elif action == "list":
            return list_desktop()
        elif action == "stats":
            return get_desktop_stats()
        elif action == "task" or task:
            actual_task = task or str(params.get("description", "")).strip()
            if not actual_task: return "Please describe what you want to do on the desktop."
            print(f"[Desktop] Asking Gemini: {actual_task}")
            if player and hasattr(player, "write_log"):
                try: player.write_log("[Desktop] Generating action...")
                except Exception: pass
            code = _ask_gemini_for_desktop_action(actual_task)
            return _execute_generated_code(code, player=player)
        else:
            if action:
                code = _ask_gemini_for_desktop_action(action)
                return _execute_generated_code(code, player=player)
            return "No action or task specified."
    except Exception as e:
        print(f"[Desktop] Error: {e}")
        return f"Desktop control error: {e}"