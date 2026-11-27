import io
import json
import re
import string
import subprocess
import sys
import time
import random
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE         = _base_dir()
_CONFIG_PATH  = _BASE / "config" / "api_keys.json"
_MEMORY_PATH  = _BASE / "memory" / "long_term.json"

def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get_os() -> str:
    try:
        return str(_load_config().get("os_system", "windows")).lower()
    except Exception:
        return "windows"


def _get_api_key() -> str:
    try:
        return str(_load_config().get("gemini_api_key", ""))
    except Exception:
        return ""

_SAFE_SCREENSHOT_ROOTS = (
    Path.home(),
)

def _safe_screenshot_path(requested: str | None) -> Path:
    fallback = Path.home() / "Desktop" / "qeltex_screenshot.png"
    if not requested:
        return fallback
    try:
        p = Path(str(requested)).expanduser().resolve()
        for root in _SAFE_SCREENSHOT_ROOTS:
            if p.is_relative_to(root.resolve()):
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    return p
                except Exception:
                    pass
    except Exception:
        pass
    return fallback

def _require_pyautogui():
    if not _PYAUTOGUI:
        print("[ComputerControl] ❌ Missing installation: 'pyautogui' is absent.")
        print("[ComputerControl] 👉 Please execute command: pip install pyautogui")
        raise RuntimeError("PyAutoGUI not installed. Please run: pip install pyautogui, sir.")

_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
]
_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "mail.com"]


def _random_data(data_type: str) -> str:
    try:
        dt = str(data_type).lower().strip()
    except Exception:
        dt = "name"

    if dt == "first_name":
        return random.choice(_FIRST_NAMES)

    if dt == "last_name":
        return random.choice(_LAST_NAMES)

    if dt == "name":
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"

    if dt == "email":
        first = random.choice(_FIRST_NAMES).lower()
        last  = random.choice(_LAST_NAMES).lower()
        num   = random.randint(10, 999)
        return f"{first}.{last}{num}@{random.choice(_DOMAINS)}"

    if dt == "username":
        return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100, 9999)}"

    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw   = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.digits)
            + random.choice("!@#$%")
            + "".join(random.choices(chars, k=9))
        )
        return "".join(random.sample(raw, len(raw)))

    if dt == "phone":
        return f"+1{random.randint(200,999)}{random.randint(1_000_000, 9_999_999)}"

    if dt == "birthday":
        y = random.randint(1980, 2000)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        return f"{m:02d}/{d:02d}/{y}"

    if dt == "address":
        num    = random.randint(100, 9999)
        street = random.choice(["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"])
        return f"{num} {street}"

    if dt == "zip_code":
        return str(random.randint(10000, 99999))

    if dt == "city":
        return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])

    return f"random_{dt}_{random.randint(1000, 9999)}"

def _user_profile() -> dict:
    if not _MEMORY_PATH.exists():
        return {}
    try:
        data = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            identity = data.get("identity", {})
            if isinstance(identity, dict):
                return {str(k): v.get("value", "") for k, v in identity.items() if isinstance(v, dict)}
    except Exception as e:
        print(f"[ComputerControl] ⚠️ Could not read user profile from memory core: {e}")
    return {}

def _type(text: str, interval: float = 0.03) -> str:
    _require_pyautogui()
    try:
        clean_interval = float(interval)
    except (ValueError, TypeError):
        clean_interval = 0.03
    try:
        time.sleep(0.3)
        pyautogui.typewrite(str(text), interval=clean_interval)
        return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"
    except Exception as e:
        return f"Typing failed: {e}"


def _smart_type(text: str, clear_first: bool = True) -> str:
    _require_pyautogui()
    try:
        if clear_first:
            _clear_field()
            time.sleep(0.1)

        if len(str(text)) > 20 and _PYPERCLIP:
            try:
                pyperclip.copy(str(text))
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "v")
                return f"Smart-typed (clipboard): {text[:60]}{'…' if len(text) > 60 else ''}"
            except Exception:
                pass

        pyautogui.typewrite(str(text), interval=0.04)
        return f"Smart-typed: {text[:60]}{'…' if len(text) > 60 else ''}"
    except Exception as e:
        return f"Smart typing failed: {e}"


def _click(x=None, y=None, button: str = "left", clicks: int = 1) -> str:
    _require_pyautogui()
    try:
        clean_clicks = int(clicks)
    except (ValueError, TypeError):
        clean_clicks = 1
        
    clean_btn = str(button).lower().strip() if button else "left"
    if clean_btn not in ("left", "right", "middle"):
        clean_btn = "left"

    try:
        if x is not None and y is not None:
            pyautogui.click(int(x), int(y), button=clean_btn, clicks=clean_clicks)
            return f"{'Double-c' if clean_clicks == 2 else 'C'}licked ({int(x)}, {int(y)}) [{clean_btn}]"
        pyautogui.click(button=clean_btn, clicks=clean_clicks)
        return f"Clicked at current position [{clean_btn}]"
    except Exception as e:
        return f"Click failed: {e}"


def _hotkey(*keys) -> str:
    _require_pyautogui()
    try:
        clean_keys = [str(k) for k in keys if k]
        pyautogui.hotkey(*clean_keys)
        return f"Hotkey: {'+'.join(clean_keys)}"
    except Exception as e:
        return f"Hotkey failed: {e}"


def _press(key: str) -> str:
    _require_pyautogui()
    try:
        pyautogui.press(str(key))
        return f"Pressed: {key}"
    except Exception as e:
        return f"Key press failed: {e}"


def _scroll(direction: str = "down", amount: int = 3) -> str:
    _require_pyautogui()
    try:
        clean_amount = int(amount)
    except (ValueError, TypeError):
        clean_amount = 3
        
    clean_dir = str(direction).lower().strip()
    vertical   = clean_dir in ("up", "down")
    clicks     = clean_amount if clean_dir in ("up", "right") else -clean_amount
    try:
        if vertical:
            pyautogui.scroll(clicks)
        else:
            pyautogui.hscroll(clicks)
        return f"Scrolled {clean_dir} ×{clean_amount}"
    except Exception as e:
        return f"Scroll failed: {e}"


def _move(x: int, y: int, duration: float = 0.3) -> str:
    _require_pyautogui()
    try:
        clean_x = int(x)
        clean_y = int(y)
        try: clean_dur = float(duration)
        except (ValueError, TypeError): clean_dur = 0.3
        
        pyautogui.moveTo(clean_x, clean_y, duration=clean_dur)
        return f"Mouse → ({clean_x}, {clean_y})"
    except Exception as e:
        return f"Mouse movement failed: {e}"


def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> str:
    _require_pyautogui()
    try:
        cx1, cy1, cx2, cy2 = int(x1), int(y1), int(x2), int(y2)
        try: clean_dur = float(duration)
        except (ValueError, TypeError): clean_dur = 0.5
        
        pyautogui.moveTo(cx1, cy1, duration=0.2)
        pyautogui.dragTo(cx2, cy2, duration=clean_dur, button="left")
        return f"Dragged ({cx1},{cy1}) → ({cx2},{cy2})"
    except Exception as e:
        return f"Mouse drag failed: {e}"


def _clipboard_get() -> str:
    if _PYPERCLIP:
        try:
            return pyperclip.paste()
        except Exception:
            pass
    _hotkey("ctrl", "c")
    time.sleep(0.2)
    return "(copied — pyperclip unavailable for read)"


def _clipboard_paste(text: str) -> str:
    if _PYPERCLIP:
        try:
            pyperclip.copy(str(text))
            time.sleep(0.1)
            _require_pyautogui()
            pyautogui.hotkey("ctrl", "v")
            return f"Pasted: {text[:60]}{'…' if len(text) > 60 else ''}"
        except Exception:
            pass
    return "pyperclip not available"


def _screenshot(save_path: str | None = None) -> str:
    _require_pyautogui()
    try:
        path = _safe_screenshot_path(save_path)
        img  = pyautogui.screenshot()
        img.save(str(path))
        return f"Screenshot saved: {path}"
    except Exception as e:
        return f"Screenshot failed: {e}"


def _clear_field() -> str:
    _require_pyautogui()
    try:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("delete")
        return "Field cleared"
    except Exception as e:
        return f"Clear field failed: {e}"

def _focus_window(title: str) -> str:
    os_name = _get_os()
    clean_title = str(title).strip()

    if os_name == "windows":
        try:
            script = f'(New-Object -ComObject WScript.Shell).AppActivate("{clean_title}")'
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {clean_title}"
        except Exception as e:
            return f"focus_window (Windows) failed: {e}"

    if os_name == "mac":
        script = (
            f'tell application "System Events" to '
            f'set frontmost of (first process whose name contains "{clean_title}") to true'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {clean_title}"
        except Exception as e:
            return f"focus_window (macOS) failed: {e}"

    if os_name == "linux":
        try:
            result = subprocess.run(
                ["wmctrl", "-a", clean_title],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                time.sleep(0.3)
                return f"Focused window: {clean_title}"
        except FileNotFoundError:
            pass
        except Exception:
            pass
            
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", clean_title, "windowactivate"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                time.sleep(0.3)
                return f"Focused window: {clean_title}"
        except FileNotFoundError:
            return "focus_window (Linux) requires wmctrl or xdotool"
        except Exception as e:
            return f"focus_window (Linux) failed: {e}"

    return f"focus_window: unknown OS '{os_name}'"

def _screen_find(description: str) -> tuple[int, int] | None:
    try:
        from google import genai
        from google.genai import types as gtypes
        HAS_NEW_GENAI = True
    except ImportError:
        HAS_NEW_GENAI = False

    if not HAS_NEW_GENAI:
        print("[ComputerControl] ❌ Missing installation: 'google-genai' is absent.")
        print("[ComputerControl] 👉 Please execute command: pip install google-genai")
        return None

    api_key = _get_api_key()
    if not api_key:
        print("[ComputerControl] ⚠️ No API key for screen_find")
        return None

    try:
        _require_pyautogui()
        
        try:
            w, h = pyautogui.size()
            img = pyautogui.screenshot()
        except Exception as screen_err:
            print(f"[ComputerControl] ⚠️ Screen capture failed: {screen_err}")
            return None
            
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        client = genai.Client(api_key=api_key)
        prompt = (
            f"This is a screenshot of a {w}×{h} pixel screen. "
            f"Locate the UI element described as: '{description}'. "
            f"Reply with ONLY the center coordinates as: x,y "
            f"If the element is not visible, reply: NOT_FOUND"
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=[
                gtypes.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt,
            ],
        )

        text = response.text.strip() if response.text else ""
        if "NOT_FOUND" in text.upper() or not text:
            return None

        match = re.search(r"(\d+)\s*,\s*(\d+)", text)
        if match:
            try:
                target_x = int(match.group(1))
                target_y = int(match.group(2))
                return target_x, target_y
            except (ValueError, TypeError):
                return None

    except Exception as e:
        print(f"[ComputerControl] ⚠️ screen_find failed: {e}")

    return None

def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters if isinstance(parameters, dict) else {}
    action = str(params.get("action", "")).lower().strip()

    if not action:
        return "No action specified for computer_control."

    if player and hasattr(player, "write_log"):
        try:
            player.write_log(f"[Computer] {action}")
        except Exception:
            pass

    print(f"[ComputerControl] ▶ {action}  {params}")

    try:
        if action == "type":
            return _type(params.get("text", ""))

        if action == "smart_type":
            return _smart_type(
                params.get("text", ""),
                clear_first=bool(params.get("clear_first", True)),
            )

        if action in ("click", "left_click"):
            return _click(params.get("x"), params.get("y"), "left", 1)

        if action == "double_click":
            return _click(params.get("x"), params.get("y"), "left", 2)

        if action == "right_click":
            return _click(params.get("x"), params.get("y"), "right", 1)

        if action == "move":
            try: cx = int(params.get("x", 0))
            except (ValueError, TypeError): cx = 0
            try: cy = int(params.get("y", 0))
            except (ValueError, TypeError): cy = 0
            return _move(cx, cy)

        if action == "drag":
            try: cx1 = int(params.get("x1", 0))
            except (ValueError, TypeError): cx1 = 0
            try: cy1 = int(params.get("y1", 0))
            except (ValueError, TypeError): cy1 = 0
            try: cx2 = int(params.get("x2", 0))
            except (ValueError, TypeError): cx2 = 0
            try: cy2 = int(params.get("y2", 0))
            except (ValueError, TypeError): cy2 = 0
            return _drag(cx1, cy1, cx2, cy2)

        if action == "hotkey":
            raw  = params.get("keys", "")
            keys = [str(k).strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            return _hotkey(*keys)

        if action == "press":
            return _press(str(params.get("key", "enter")))

        if action == "scroll":
            try: clean_amount = int(params.get("amount", 3))
            except (ValueError, TypeError): clean_amount = 3
            return _scroll(
                direction=str(params.get("direction", "down")),
                amount=clean_amount,
            )

        if action == "copy":
            return _clipboard_get()

        if action == "paste":
            return _clipboard_paste(params.get("text", ""))

        if action == "screenshot":
            return _screenshot(params.get("path"))

        if action == "screen_find":
            coords = _screen_find(params.get("description", ""))
            if isinstance(coords, tuple) and len(coords) >= 2:
                return f"{coords[0]},{coords[1]}"
            return "NOT_FOUND"

        if action == "screen_click":
            desc = str(params.get("description", "")).strip()
            coords = _screen_find(desc)
            if isinstance(coords, tuple) and len(coords) >= 2:
                time.sleep(0.2)
                _click(x=coords[0], y=coords[1])
                return f"Clicked '{desc}' at {coords}"
            return f"Element not found on screen: '{desc}'"

        if action == "wait":
            try: secs = float(params.get("seconds", 1.0))
            except (ValueError, TypeError): secs = 1.0
            secs = min(secs, 30.0)
            time.sleep(secs)
            return f"Waited {secs}s"

        if action == "clear_field":
            return _clear_field()

        if action == "focus_window":
            return _focus_window(params.get("title", ""))

        if action == "random_data":
            dt = str(params.get("type", "name")).strip()
            result = _random_data(dt)
            print(f"[ComputerControl] 🎲 random {dt} → {result}")
            return result

        if action == "user_data":
            field_name = str(params.get("field", "name")).strip()
            profile = _user_profile()
            value = profile.get(field_name, "") if isinstance(profile, dict) else ""
            if not value:
                value = _random_data(field_name)
                print(f"[ComputerControl] ⚠️ No '{field_name}' in memory, using random: {value}")
            return value

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] ❌ {action}: {e}")
        return f"computer_control '{action}' failed: {e}"