import json
import re
import sys
import time
import subprocess
import platform
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

_OS = platform.system()

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_api_key() -> str:
    """Fetches the API key dynamically on each call to prevent caching and thread-locking."""
    path = _get_base_dir() / "config" / "api_keys.json"
    if not path.exists():
        print(f"[Settings] ❌ Configuration file missing: {path}")
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "")
    except Exception as e:
        print(f"[Settings] ❌ Error reading api_keys.json: {e}")
        return ""

def _get_macos_wifi_interface() -> str:
    try:
        result = subprocess.run(
            ["networksetup", "-listallhardwareports"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.splitlines() if result.stdout else []
        for i, line in enumerate(lines):
            if "Wi-Fi" in line or "AirPort" in line:
                for j in range(i, min(i + 4, len(lines))):
                    if lines[j].startswith("Device:"):
                        return lines[j].split(":", 1)[1].strip()
    except Exception: pass
    return "en0" 

def volume_up():
    if _OS == "Windows":
        if not _PYAUTOGUI:
            print("[Settings] ❌ Missing installation: 'pyautogui' is absent.")
            print("[Settings] 👉 Please execute command: pip install pyautogui")
            return
        try:
            for _ in range(5): pyautogui.press("volumeup")
        except Exception as e:
            print(f"[Settings] volume_up automation failed: {e}")
    elif _OS == "Darwin":
        try:
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"], capture_output=True, timeout=5)
        except Exception: pass
    else:
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"], capture_output=True, timeout=5)
        except Exception: pass

def volume_down():
    if _OS == "Windows":
        if not _PYAUTOGUI:
            print("[Settings] ❌ Missing installation: 'pyautogui' is absent.")
            print("[Settings] 👉 Please execute command: pip install pyautogui")
            return
        try:
            for _ in range(5): pyautogui.press("volumedown")
        except Exception as e:
            print(f"[Settings] volume_down automation failed: {e}")
    elif _OS == "Darwin":
        try:
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"], capture_output=True, timeout=5)
        except Exception: pass
    else:
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"], capture_output=True, timeout=5)
        except Exception: pass

def volume_mute():
    if _OS == "Windows":
        if not _PYAUTOGUI:
            print("[Settings] ❌ 'pyautogui' is missing.")
            return
        try:
            pyautogui.press("volumemute")
        except Exception as e:
            print(f"[Settings] volume_mute automation failed: {e}")
    elif _OS == "Darwin":
        try:
            subprocess.run(["osascript", "-e", "set volume with output muted"], capture_output=True, timeout=5)
        except Exception: pass
    else:
        try:
            subprocess.run(["pactl", "-sink-mute", "@DEFAULT_SINK@", "toggle"], capture_output=True, timeout=5)
        except Exception: pass

def volume_set(value: int):
    try: clean_value = max(0, min(100, int(value)))
    except (ValueError, TypeError): clean_value = 50
    if _OS == "Windows":
        try:
            import math
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices   = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol       = cast(interface, POINTER(IAudioEndpointVolume))
            vol_db    = -65.25 if clean_value == 0 else max(-65.25, 20 * math.log10(clean_value / 100))
            vol.SetMasterVolumeLevel(vol_db, None)
            return
        except ImportError:
            print("[Settings] ❌ Missing installation: 'pycaw' or 'comtypes' is not installed.")
            print("[Settings] 👉 Please execute command: pip install pycaw comtypes")
            if _PYAUTOGUI:
                try: pyautogui.press("volumemute")
                except Exception: pass
        except Exception as e:
            print(f"[Settings] pycaw failed, using keypress fallback: {e}")
            if _PYAUTOGUI:
                try: pyautogui.press("volumemute")
                except Exception: pass
    elif _OS == "Darwin":
        try: subprocess.run(["osascript", "-e", f"set volume output volume {clean_value}"], capture_output=True, timeout=5)
        except Exception: pass
        return
    else:
        try: subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{clean_value}%"], capture_output=True, timeout=5)
        except Exception: pass
        return

def brightness_up():
    if _OS == "Darwin":
        try: subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 144'], capture_output=True, timeout=5)
        except Exception: pass
    elif _OS == "Linux":
        try:
            check_bc = subprocess.run(["which", "brightnessctl"], capture_output=True, timeout=3)
            if check_bc.returncode == 0:
                subprocess.run(["brightnessctl", "set", "+10%"], capture_output=True, timeout=5)
            else:
                subprocess.run('xrandr --output $(xrandr | grep " connected" | head -1 | cut -d " " -f1) --brightness $(python3 -c "import subprocess; try:\n b=float(subprocess.check_output([\"xrandr\",\"--verbose\"]).decode().split(\"Brightness:\")[1].split()[0]); print(min(1.0,b+0.1))\n except:\n print(1.0)")', shell=True, capture_output=True, timeout=5)
        except Exception as e: print(f"[Settings] Brightness up failed on Linux: {e}")
    else:
        try: subprocess.run(["powershell", "-Command", "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, [math]::Min(100, (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness + 10))"], capture_output=True, timeout=5)
        except Exception as e: print(f"[Settings] Brightness up failed on Windows: {e}")

def brightness_down():
    if _OS == "Darwin":
        try: subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 145'], capture_output=True, timeout=5)
        except Exception: pass
    elif _OS == "Linux":
        try:
            check_bc = subprocess.run(["which", "brightnessctl"], capture_output=True, timeout=3)
            if check_bc.returncode == 0:
                subprocess.run(["brightnessctl", "set", "10%-"], capture_output=True, timeout=5)
            else:
                subprocess.run('xrandr --output $(xrandr | grep " connected" | head -1 | cut -d " " -f1) --brightness $(python3 -c "import subprocess; try:\n b=float(subprocess.check_output([\"xrandr\",\"--verbose\"]).decode().split(\"Brightness:\")[1].split()[0]); print(max(0.1,b-0.1))\n except:\n print(0.5)")', shell=True, capture_output=True, timeout=5)
        except Exception as e: print(f"[Settings] Brightness down failed on Linux: {e}")
    else:
        try: subprocess.run(["powershell", "-Command", "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, [math]::Max(0, (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness - 10))"], capture_output=True, timeout=5)
        except Exception as e: print(f"[Settings] Brightness down failed on Windows: {e}")

def close_app():
    if not _PYAUTOGUI:
        print("[Settings] ❌ Missing installation: 'pyautogui' is absent.")
        return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "q")
        else:               pyautogui.hotkey("alt", "f4")
    except Exception as e: print(f"[Settings] close_app shortcut failed: {e}")

def close_window():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "w")
        else:               pyautogui.hotkey("ctrl", "w")
    except Exception as e: print(f"[Settings] close_window shortcut failed: {e}")

def full_screen():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("ctrl", "command", "f")
        else:               pyautogui.press("f11")
    except Exception as e: print(f"[Settings] full_screen shortcut failed: {e}")

def minimize_window():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "m")
        else:               pyautogui.hotkey("win", "down")
    except Exception as e: print(f"[Settings] minimize_window shortcut failed: {e}")

def maximize_window():
    if _OS == "Darwin":
        try: subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "f" using {control down, command down}'], capture_output=True, timeout=5)
        except Exception: pass
    elif _OS == "Windows":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("win", "up")
            except Exception: pass
    else:
        try: subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"], capture_output=True, timeout=5)
        except Exception:
            if _PYAUTOGUI:
                try: pyautogui.hotkey("super", "up")
                except Exception: pass

def snap_left():
    if _OS == "Windows":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("win", "left")
            except Exception: pass
    elif _OS == "Linux":
        try: subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-e", "0,0,0,960,1080"], capture_output=True, timeout=5)
        except Exception: pass

def snap_right():
    if _OS == "Windows":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("win", "right")
            except Exception: pass
    elif _OS == "Linux":
        try: subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-e", "0,960,0,960,1080"], capture_output=True, timeout=5)
        except Exception: pass

def switch_window():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "tab")
        else:               pyautogui.hotkey("alt", "tab")
    except Exception as e: print(f"[Settings] switch_window shortcut failed: {e}")

def show_desktop():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin":   pyautogui.hotkey("fn", "f11")
        elif _OS == "Windows": pyautogui.hotkey("win", "d")
        else:                  pyautogui.hotkey("super", "d")
    except Exception as e: print(f"[Settings] show_desktop shortcut failed: {e}")

def open_task_manager():
    if _OS == "Windows":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("ctrl", "shift", "esc")
            except Exception: pass
    elif _OS == "Darwin":
        try: subprocess.Popen(["open", "-a", "Activity Monitor"])
        except Exception: pass
    else:
        try:
            for cmd in [["gnome-system-monitor"], ["xfce4-taskmanager"], ["htop"]]:
                check_cmd = subprocess.run(["which", cmd], capture_output=True, timeout=3)
                if check_cmd.returncode == 0:
                    subprocess.Popen(cmd)
                    break
        except Exception: pass

def focus_search():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "l")
        else:               pyautogui.hotkey("ctrl", "l")
    except Exception: pass

def pause_video():
    if not _PYAUTOGUI: return
    try: pyautogui.press("space")
    except Exception: pass

def refresh_page():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "r")
        else:               pyautogui.press("f5")
    except Exception: pass

def close_tab():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "w")
        else:               pyautogui.hotkey("ctrl", "w")
    except Exception: pass

def new_tab():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "t")
        else:               pyautogui.hotkey("ctrl", "t")
    except Exception: pass

def next_tab():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "shift", "bracketright")
        else:               pyautogui.hotkey("ctrl", "tab")
    except Exception: pass

def prev_tab():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "shift", "bracketleft")
        else:               pyautogui.hotkey("ctrl", "shift", "tab")
    except Exception: pass

def go_back():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "left")
        else:               pyautogui.hotkey("alt", "left")
    except Exception: pass

def go_forward():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "right")
        else:               pyautogui.hotkey("alt", "right")
    except Exception: pass

def zoom_in():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "equal")
        else:               pyautogui.hotkey("ctrl", "equal")
    except Exception: pass

def zoom_out():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "minus")
        else:               pyautogui.hotkey("ctrl", "minus")
    except Exception: pass

def zoom_reset():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "0")
        else:               pyautogui.hotkey("ctrl", "0")
    except Exception: pass

def find_on_page():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "f")
        else:               pyautogui.hotkey("ctrl", "f")
    except Exception: pass

def reload_page_n(n: int):
    try: clean_n = int(n)
    except (ValueError, TypeError): clean_n = 1
    for _ in range(max(1, clean_n)):
        refresh_page()
        time.sleep(0.8)

def scroll_up(amount: int = 500):
    if not _PYAUTOGUI: return
    try: clean_amount = int(amount)
    except (ValueError, TypeError): clean_amount = 500
    try: pyautogui.scroll(clean_amount)
    except Exception: pass
    
def scroll_down(amount: int = 500):
    if not _PYAUTOGUI: return
    try: clean_amount = int(amount)
    except (ValueError, TypeError): clean_amount = 500
    try: pyautogui.scroll(-clean_amount)
    except Exception: pass

def scroll_top():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "up")
        else:               pyautogui.hotkey("ctrl", "home")
    except Exception: pass

def scroll_bottom():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "down")
        else:               pyautogui.hotkey("ctrl", "end")
    except Exception: pass

def page_up():
    if not _PYAUTOGUI: return
    try: pyautogui.press("pageup")
    except Exception: pass
    
def page_down():
    if not _PYAUTOGUI: return
    try: pyautogui.press("pagedown")
    except Exception: pass

def copy():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "c")
        else:               pyautogui.hotkey("ctrl", "c")
    except Exception: pass

def paste():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "v")
        else:               pyautogui.hotkey("ctrl", "v")
    except Exception: pass

def cut():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "x")
        else:               pyautogui.hotkey("ctrl", "x")
    except Exception: pass

def undo():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "z")
        else:               pyautogui.hotkey("ctrl", "z")
    except Exception: pass

def redo():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "shift", "z")
        else:               pyautogui.hotkey("ctrl", "y")
    except Exception: pass

def select_all():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "a")
        else:               pyautogui.hotkey("ctrl", "a")
    except Exception: pass

def save_file():
    if not _PYAUTOGUI: return
    try:
        if _OS == "Darwin": pyautogui.hotkey("command", "s")
        else:               pyautogui.hotkey("ctrl", "s")
    except Exception: pass

def press_enter():
    if not _PYAUTOGUI: return
    try: pyautogui.press("enter")
    except Exception: pass
    
def press_escape():
    if not _PYAUTOGUI: return
    try: pyautogui.press("escape")
    except Exception: pass
    
def press_key(key: str):
    if not _PYAUTOGUI: return
    try: pyautogui.press(str(key))
    except Exception: pass

def type_text(text: str, press_enter_after: bool = False):
    if not text: return
    if _PYPERCLIP:
        try:
            pyperclip.copy(str(text))
            time.sleep(0.15)
            paste()
        except Exception:
            if _PYAUTOGUI:
                try: pyautogui.write(str(text), interval=0.03)
                except Exception: pass
    else:
        if _PYAUTOGUI:
            try: pyautogui.write(str(text), interval=0.03)
            except Exception: pass
    if press_enter_after and _PYAUTOGUI:
        try:
            time.sleep(0.1)
            pyautogui.press("enter")
        except Exception: pass

def take_screenshot():
    if _OS == "Windows":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("win", "shift", "s")
            except Exception: pass
    elif _OS == "Darwin":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("command", "shift", "3")
            except Exception: pass
    else:
        try:
            for cmd in ["scrot", "gnome-screenshot", "import"]:
                check_cmd = subprocess.run(["which", cmd], capture_output=True, timeout=3)
                if check_cmd.returncode == 0:
                    if cmd == "import":
                        subprocess.Popen(["import", "-window", "root", "screenshot.png"])
                    else:
                        subprocess.Popen([cmd])
                    return
        except Exception: pass
        if _PYAUTOGUI:
            try: pyautogui.hotkey("ctrl", "print_screen")
            except Exception: pass

def lock_screen():
    if _OS == "Windows":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("win", "l")
            except Exception: pass
    elif _OS == "Darwin":
        try: subprocess.run(["pmset", "displaysleepnow"], capture_output=True, timeout=5)
        except Exception: pass
    else:
        try:
            commands = {
                "gnome-screensaver-command": ["gnome-screensaver-command", "-l"],
                "xdg-screensaver": ["xdg-screensaver", "lock"],
                "loginctl": ["loginctl", "lock-session"]
            }
            for check_name, full_cmd in commands.items():
                check_cmd = subprocess.run(["which", check_name], capture_output=True, timeout=3)
                if check_cmd.returncode == 0:
                    subprocess.run(full_cmd, capture_output=True, timeout=5)
                    return
        except Exception: pass

def open_system_settings():
    if _OS == "Windows":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("win", "i")
            except Exception: pass
    elif _OS == "Darwin":
        try: subprocess.Popen(["open", "-a", "System Preferences"])
        except Exception: pass
    else:
        try:
            for cmd in ["gnome-control-center", "xfce4-settings-manager", "kcmshell5"]:
                check_cmd = subprocess.run(["which", cmd], capture_output=True, timeout=3)
                if check_cmd.returncode == 0:
                    subprocess.Popen([cmd])
                    return
        except Exception: pass

def open_file_explorer():
    if _OS == "Windows":
        if _PYAUTOGUI:
            try: pyautogui.hotkey("win", "e")
            except Exception: pass
    elif _OS == "Darwin":
        try: subprocess.Popen(["open", str(Path.home())])
        except Exception: pass
    else:
        try:
            for cmd in ["nautilus", "thunar", "dolphin", "nemo"]:
                check_cmd = subprocess.run(["which", cmd], capture_output=True, timeout=3)
                if check_cmd.returncode == 0:
                    subprocess.Popen([cmd])
                    return
            subprocess.Popen(["xdg-open", str(Path.home())])
        except Exception: pass

def sleep_display():
    if _OS == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        except Exception as e: print(f"[Settings] sleep_display failed: {e}")
    elif _OS == "Darwin":
        try: subprocess.run(["pmset", "displaysleepnow"], capture_output=True, timeout=5)
        except Exception: pass
    else:
        try: subprocess.run(["xset", "dpms", "force", "off"], capture_output=True, timeout=5)
        except Exception: pass

def open_run():
    if _OS == "Windows" and _PYAUTOGUI:
        try: pyautogui.hotkey("win", "r")
        except Exception: pass

def dark_mode():
    if _OS == "Darwin":
        try:
            subprocess.run(["osascript", "-e", 'tell app "System Events" to tell appearance preferences to set dark mode to not dark mode'], capture_output=True, timeout=5)
        except Exception: pass
    elif _OS == "Windows":
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            current, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 1 - current)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 1 - current)
            winreg.CloseKey(key)
        except Exception as e: print(f"[Settings] dark_mode registry failed: {e}")
    else:
        try:
            result = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"], capture_output=True, text=True, timeout=5)
            current = result.stdout.strip() if result.stdout else ""
            new_scheme = "'default'" if "dark" in current else "'prefer-dark'"
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", new_scheme], capture_output=True, timeout=5)
        except Exception as e: print(f"[Settings] dark_mode Linux failed: {e}")

def toggle_wifi():
    if _OS == "Darwin":
        try:
            iface = _get_macos_wifi_interface()
            result = subprocess.run(["networksetup", "-getairportpower", iface], capture_output=True, text=True, timeout=5)
            state = "off" if result.stdout and "On" in result.stdout else "on"
            subprocess.run(["networksetup", "-setairportpower", iface, state], capture_output=True, timeout=5)
        except Exception as e: print(f"[Settings] toggle_wifi macOS failed: {e}")
    elif _OS == "Windows":
        try:
            subprocess.run(["powershell", "-Command", "$adapter = Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'}; if ($adapter.Status -eq 'Up') { Disable-NetAdapter -Name $adapter.Name -Confirm:$false } else { Enable-NetAdapter -Name $adapter.Name -Confirm:$false }"], capture_output=True, timeout=10)
        except Exception as e: print(f"[Settings] toggle_wifi Windows failed: {e}")
    else:
        try:
            result = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True, timeout=5)
            state  = "off" if result.stdout and "enabled" in result.stdout else "on"
            subprocess.run(["nmcli", "radio", "wifi", state], capture_output=True, timeout=5)
        except Exception as e: print(f"[Settings] toggle_wifi Linux failed: {e}")

def restart_computer():
    try:
        if _OS == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "10"], capture_output=True, timeout=5)
        elif _OS == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to restart'], capture_output=True, timeout=5)
        else:
            subprocess.run(["systemctl", "reboot"], capture_output=True, timeout=5)
    except Exception as e: print(f"[Settings] restart failed: {e}")

def shutdown_computer():
    try:
        if _OS == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "10"], capture_output=True, timeout=5)
        elif _OS == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to shut down'], capture_output=True, timeout=5)
        else:
            subprocess.run(["systemctl", "poweroff"], capture_output=True, timeout=5)
    except Exception as e: print(f"[Settings] shutdown failed: {e}")

def open_background_settings():
    try:
        if _OS == "Windows":
            subprocess.Popen("explorer.exe ms-settings:personalization-background", shell=True)
    except Exception as e: print(f"[Settings] open background failed: {e}")

ACTION_MAP: dict[str, callable] = {
    "volume_up":           volume_up,
    "volume_down":         volume_down,
    "mute":                volume_mute,
    "unmute":              volume_mute,
    "toggle_mute":         volume_mute,
    "brightness_up":       brightness_up,
    "brightness_down":     brightness_down,
    "sleep_display":       sleep_display,
    "screen_off":          sleep_display,
    "pause_video":         pause_video,
    "play_pause":          pause_video,
    "close_app":           close_app,
    "close_window":        close_window,
    "full_screen":         full_screen,
    "fullscreen":          full_screen,
    "minimize":            minimize_window,
    "maximize":            maximize_window,
    "snap_left":           snap_left,
    "snap_right":          snap_right,
    "switch_window":       switch_window,
    "show_desktop":        show_desktop,
    "task_manager":        open_task_manager,
    "focus_search":        focus_search,
    "refresh_page":        refresh_page,
    "reload":              refresh_page,
    "close_tab":           close_tab,
    "new_tab":             new_tab,
    "next_tab":            next_tab,
    "prev_tab":            prev_tab,
    "go_back":             go_back,
    "go_forward":          go_forward,
    "zoom_in":             zoom_in,
    "zoom_out":            zoom_out,
    "zoom_reset":          zoom_reset,
    "find_on_page":        find_on_page,
    "scroll_up":           scroll_up,
    "scroll_down":         scroll_down,
    "scroll_top":          scroll_top,
    "scroll_bottom":       scroll_bottom,
    "page_up":             page_up,
    "page_down":           page_down,
    "copy":                copy,
    "paste":               paste,
    "cut":                 cut,
    "undo":                undo,
    "redo":                redo,
    "select_all":          select_all,
    "save":                save_file,
    "enter":               press_enter,
    "escape":              press_escape,
    "screenshot":          take_screenshot,
    "lock_screen":         lock_screen,
    "open_settings":       open_system_settings,
    "file_explorer":       open_file_explorer,
    "open_run":            open_run,
    "dark_mode":           dark_mode,
    "toggle_wifi":         toggle_wifi,
    "restart":             restart_computer,
    "shutdown":            shutdown_computer,
    "open_background_settings": open_background_settings,
}

_DANGEROUS_ACTIONS = {"restart", "shutdown"}

def _detect_action(description: str) -> dict:
    import re
    try:
        from google import genai
        HAS_GEMINI_SETTINGS = True
    except ImportError:
        HAS_GEMINI_SETTINGS = False

    if not HAS_GEMINI_SETTINGS:
        return {"action": str(description).lower().replace(" ", "_"), "value": None}

    api_key = _get_api_key()
    if not api_key:
        return {"action": str(description).lower().replace(" ", "_"), "value": None}

    try:
        client = genai.Client(api_key=api_key)
        available = ", ".join(sorted(ACTION_MAP.keys())) + ", volume_set, type_text, press_key, reload_page_n"
        prompt = f"You are an intent detector for a computer control assistant. The user issued a command: '{description}' Available actions: {available} Return ONLY a valid JSON object: {{\"action\": \"action_name\", \"value\": null_or_value}} Rules: Pick the single best matching action. For volume_set: value is integer 0-100. For type_text: value is exact text. For press_key: value is key name. For reload_page_n: value is integer. Return ONLY the JSON, no markdown."
        resp = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        text = resp.text.strip() if resp.text else "{}"
        match = re.search(r"\{.*\}", text, re.DOTALL)
        text = match.group(0) if match else re.sub(r"```Header(?:json)?", "", text).strip().rstrip("`").strip()
        import json
        return json.loads(text)
    except Exception as e:
        print(f"[Settings] Intent detection failed: {e}")
        return {"action": str(description).lower().replace(" ", "_"), "value": None}

def computer_settings(parameters: dict = None, response=None, player=None, session_memory=None) -> str:
    if not _PYAUTOGUI:
        print("[Settings] ❌ Missing installation: 'pyautogui' is absent.")
        print("[Settings] 👉 Please execute command: pip install pyautogui")
        return "pyautogui is not installed. Please run: pip install pyautogui to control system settings, sir."
    params = parameters or {}
    if isinstance(params, str):
        try: params = json.loads(params)
        except Exception: params = {"action": "auto", "description": parameters}
    if not isinstance(params, dict): params = {}
    raw_action = str(params.get("action", "")).strip()
    description = str(params.get("description", "")).strip()
    value = params.get("value", None)
    if not raw_action and description:
        detected = _detect_action(description)
        raw_action = str(detected.get("action", ""))
        if value is None: value = detected.get("value")
    action = raw_action.lower().strip().replace(" ", "_").replace("-", "_")
    if not action: return "No action could be determined."
    print(f"[Settings] Action: {action} Value: {value} OS: {_OS}")
    if player and hasattr(player, "write_log"):
        try: player.write_log(f"[Settings] {action}")
        except Exception: pass
    if hasattr(player, "write_log") and action:
        try: player.write_log(f"[settings] {action}")
        except Exception: pass
    if action in _DANGEROUS_ACTIONS:
        confirmed = str(params.get("confirmed", "")).lower()
        if confirmed not in ("yes", "true", "1", "confirm"):
            return f"This will {action} the computer. Please confirm by calling again with confirmed=yes, sir."
    if action in ("volume_set", "mute") and value is not None:
        try: clean_val = int(value or 50)
        except (ValueError, TypeError): clean_val = 50
        try:
            volume_set(clean_val)
            return f"System volume adjusted to {clean_val}%, sir."
        except Exception as e: return f"Could not set volume: {e}"
    if action in ("type_text", "write_on_screen", "type", "write"):
        text = str(value or params.get("text", "")).strip()
        if not text: return "No text provided to type."
        enter_after = str(params.get("press_enter", "false")).lower() in ("true", "1", "yes")
        type_text(text, press_enter_after=enter_after)
        return f"Typed: {text[:80]}"
    if action == "press_key":
        key = str(value or params.get("key", "")).strip()
        if not key: return "No key specified."
        press_key(key)
        return f"Pressed: {key}"
    if action in ("reload_n", "refresh_n", "reload_page_n"):
        try: clean_val = int(value or 1)
        except (ValueError, TypeError): clean_val = 1
        try:
            reload_page_n(clean_val)
            return f"Reloaded {clean_val} time(s)."
        except Exception as e: return f"Reload failed: {e}"
    if action == "scroll_up":
        try: clean_val = int(value or 500)
        except (ValueError, TypeError): clean_val = 500
        scroll_up(clean_val)
        return "Scrolled up."
    if action == "scroll_down":
        try: clean_val = int(value or 500)
        except (ValueError, TypeError): clean_val = 500
        scroll_down(clean_val)
        return "Scrolled down."
    func = ACTION_MAP.get(action)
    if not func: return f"Unknown action: '{raw_action}'."
    try:
        func()
        return f"Done: {action}."
    except Exception as e:
        print(f"[Settings] Action failed ({action}): {e}")
        return f"Action failed ({action}): {e}"