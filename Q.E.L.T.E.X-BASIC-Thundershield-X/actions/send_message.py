import json
import subprocess
import sys
import time
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.06
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

def _get_os() -> str:
    config_file = _base_dir() / "config" / "api_keys.json"
    if not config_file.exists():
        return "windows"
    try:
        cfg = json.loads(config_file.read_text(encoding="utf-8"))
        return str(cfg.get("os_system", "windows")).lower()
    except Exception:
        return "windows"


def _require_pyautogui():
    if not _PYAUTOGUI:
        print("[SendMessage] ❌ Missing installation: 'pyautogui' is absent.")
        print("[SendMessage] 👉 Please execute command: pip install pyautogui")
        raise RuntimeError("PyAutoGUI not installed. Please run: pip install pyautogui, sir.")


def _paste_text(text: str) -> None:
    _require_pyautogui()

    os_name = _get_os()
    paste_hotkey = ("command", "v") if os_name == "mac" else ("ctrl", "v")

    if _PYPERCLIP:
        try:
            pyperclip.copy(str(text))
            time.sleep(0.15)
            pyautogui.hotkey(*paste_hotkey)
            time.sleep(0.1)
            return
        except Exception as clipboard_err:
            print(f"[SendMessage] ⚠️ Pyperclip copy failed, falling back to pyautogui.write: {clipboard_err}")
            
    try:
        pyautogui.write(str(text), interval=0.03)
    except Exception as e:
        print(f"[SendMessage] ❌ Failed to write text via automation: {e}")


def _clear_and_paste(text: str) -> None:
    _require_pyautogui()
    os_name = _get_os()
    select_all = ("command", "a") if os_name == "mac" else ("ctrl", "a")
    try:
        pyautogui.hotkey(*select_all)
        time.sleep(0.1)
        pyautogui.press("delete")
        time.sleep(0.1)
        _paste_text(text)
    except Exception as e:
        print(f"[SendMessage] ❌ Clear and paste failed: {e}")

def _open_app(app_name: str) -> bool:
    _require_pyautogui()
    os_name = _get_os()

    try:
        if os_name == "windows":
            pyautogui.press("win")
            time.sleep(0.5)
            _paste_text(app_name)
            time.sleep(0.6)
            pyautogui.press("enter")
            time.sleep(2.5)
            return True

        elif os_name == "mac":
            result = subprocess.run(
                ["open", "-a", str(app_name)],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["open", "-a", f"{app_name}.app"],
                    capture_output=True, text=True, timeout=10,
                )
            time.sleep(2.5)
            return result.returncode == 0

        else: 
            launched = False
            for launcher in [
                ["gtk-launch", str(app_name).lower()],
                [str(app_name).lower()],
            ]:
                try:
                    subprocess.Popen(
                        launcher,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            time.sleep(2.5)
            return launched

    except Exception as e:
        print(f"[SendMessage] ⚠️ Could not open {app_name}: {e}")
        return False


def _open_browser_url(url: str) -> bool:
    import webbrowser
    try:
        webbrowser.open(str(url))
        time.sleep(4.0) 
        return True
    except Exception as e:
        print(f"[SendMessage] ⚠️ Could not open browser: {e}")
        return False

def _search_in_app(query: str) -> None:
    _require_pyautogui()
    os_name = _get_os()
    search_hotkey = ("command", "f") if os_name == "mac" else ("ctrl", "f")

    try:
        pyautogui.hotkey(*search_hotkey)
        time.sleep(0.5)
        _clear_and_paste(query)
        time.sleep(1.0)
    except Exception as e:
        print(f"[SendMessage] ⚠️ Automation shortcut failed: {e}")

def _desktop_send(app_name: str, receiver: str, message: str) -> str:
    if not _open_app(app_name):
        return f"Could not open {app_name}."

    try:
        time.sleep(1.0)
        _search_in_app(receiver)
        pyautogui.press("enter")
        time.sleep(0.8)

        _paste_text(message)
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.3)
        return f"Message sent to {receiver} via {app_name}."
    except Exception as e:
        return f"Failed to complete keystroke automation for {app_name}: {e}"

def _send_whatsapp(receiver: str, message: str) -> str:
    return _desktop_send("WhatsApp", receiver, message)

def _send_telegram(receiver: str, message: str) -> str:
    return _desktop_send("Telegram", receiver, message)

def _send_signal(receiver: str, message: str) -> str:
    return _desktop_send("Signal", receiver, message)


def _send_discord(receiver: str, message: str) -> str:
    return _desktop_send("Discord", receiver, message)


def _send_instagram(receiver: str, message: str) -> str:
    _require_pyautogui()

    if not _open_browser_url("https://www.instagram.com/direct/new/"):
        return "Could not open Instagram in browser."

    try:
        _paste_text(receiver)
        time.sleep(1.5)

        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")   
        time.sleep(0.4)

        for _ in range(4):
            pyautogui.press("tab")
            time.sleep(0.15)
        pyautogui.press("enter")
        time.sleep(2.0)

        _paste_text(message)
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.3)
        return f"Message sent to {receiver} via Instagram."
    except Exception as e:
        return f"Instagram automation failed: {e}"


def _send_messenger(receiver: str, message: str) -> str:
    _require_pyautogui()

    if not _open_browser_url("https://www.messenger.com/"):
        return "Could not open Messenger in browser."

    try:
        _search_in_app(receiver)
        time.sleep(0.5)
        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1.0)

        _paste_text(message)
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.3)
        return f"Message sent to {receiver} via Messenger."
    except Exception as e:
        return f"Messenger automation failed: {e}"

_PLATFORM_MAP = [
    ({"whatsapp", "wp", "wapp"},              _send_whatsapp),
    ({"telegram", "tg"},                      _send_telegram),
    ({"instagram", "ig", "insta"},            _send_instagram),
    ({"signal"},                               _send_signal),
    ({"discord"},                              _send_discord),
    ({"messenger", "facebook", "fb"},         _send_messenger),
]


def _resolve_platform(platform_str: str):
    try:
        key = str(platform_str).lower().strip()
    except Exception:
        key = "whatsapp"
        
    for keywords, handler in _PLATFORM_MAP:
        if any(k in key for k in keywords):
            return handler
            
    try:
        fallback_title = str(platform_str).strip().title()
    except Exception:
        fallback_title = "WhatsApp"
    return lambda r, m: _desktop_send(fallback_title, r, m)


def send_message(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters if isinstance(parameters, dict) else {}
    
    receiver     = str(params.get("receiver", "")).strip()
    message_text = str(params.get("message_text", "")).strip()
    platform     = str(params.get("platform", "whatsapp")).strip()

    if not receiver:
        return "Please specify a recipient."
    if not message_text:
        return "Please specify the message content."
        
    if not _PYAUTOGUI:
        print("[SendMessage] ❌ Missing installation: 'pyautogui' is absent.")
        print("[SendMessage] 👉 Please execute command: pip install pyautogui")
        return "PyAutoGUI is not installed — cannot execute desktop messaging automation, sir."

    preview = message_text[:50] + ("…" if len(message_text) > 50 else "")
    print(f"[SendMessage] 📨 {platform} → {receiver}: {preview}")
    
    if player and hasattr(player, "write_log"):
        player.write_log(f"[msg] {platform} → {receiver}")

    try:
        handler = _resolve_platform(platform)
        result  = handler(receiver, message_text)
    except Exception as e:
        result = f"Could not send message: {e}"

    print(f"[SendMessage] {'✅' if 'sent' in result.lower() else '❌'} {result}")
    
    if player and hasattr(player, "write_log"):
        player.write_log(f"[msg] {result}")

    return result