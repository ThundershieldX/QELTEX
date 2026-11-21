import os
import platform
import subprocess
import json
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

def _get_api_key() -> str:
    try:
        config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    except Exception:
        return ""
    if not config_path.exists():
        return ""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "")
    except Exception:
        return ""

def network_shield(parameters: dict = None, player=None) -> str:
    ping_host = "8.8.8.8"
    is_win = platform.system() == "Windows"
    ping_param = "-n" if is_win else "-c"
    flags = subprocess.CREATE_NO_WINDOW if is_win else 0

    try:
        output = subprocess.run(
            ["ping", ping_param, "1", ping_host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
            creationflags=flags
        )
        connection = "STABLE" if output.returncode == 0 else "UNSTABLE / DISCONNECTED"
    except Exception:
        connection = "COULD NOT VERIFY"

    external_ip = "Hidden / Unknown"
    if requests:
        try:
            response = requests.get("https://ipify.org", timeout=3)
            if response.status_code == 200:
                external_ip = response.json().get("ip", "Unknown")
        except Exception:
            external_ip = "Could not retrieve external IP (Offline or Firewall)"
    else:
        external_ip = "Missing requests library"

    report = (
        f"--- Q.E.L.T.E.X NETWORK SHIELD ---\n"
        f"Internet Connection: {connection}\n"
        f"External IP Address: {external_ip}\n"
        f"Operating System: {platform.system()} ({platform.release()})\n"
        f"----------------------------------"
    )

    if player and hasattr(player, "_win") and hasattr(player._win, "qeltex_terminal_stream"):
        player._win.qeltex_terminal_stream.write_output(report)

    return report

execute_action = network_shield

if __name__ == "__main__":
    print(network_shield())