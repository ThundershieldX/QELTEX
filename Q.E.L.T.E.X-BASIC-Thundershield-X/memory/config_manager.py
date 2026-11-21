import json
import sys
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR    = get_base_dir()
CONFIG_DIR  = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"

def get_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def get_os() -> str:
    return str(get_config().get("os_system", "windows")).lower()

def is_windows() -> bool:
    return get_os() == "windows"

def is_mac() -> bool:
    return get_os() == "mac"

def is_linux() -> bool:
    return get_os() == "linux"

def ensure_config_dir() -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ [qeltex CONFIG] Could not create configuration directory: {e}")

def config_exists() -> bool:
    return CONFIG_FILE.exists()

def save_api_keys(gemini_api_key: str, openrouter_api_key: str = "") -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            parsed = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            data = parsed if isinstance(parsed, dict) else {}
        except Exception:
            data = {}
    data["gemini_api_key"] = str(gemini_api_key).strip()
    if openrouter_api_key:
        data["openrouter_api_key"] = str(openrouter_api_key).strip()
    try:
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"❌ [qeltex CONFIG] Could not save to api_keys.json: {e}")

def load_api_keys() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        parsed = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        print(f"❌ [qeltex CONFIG] Could not load api_keys.json: {e}")
        return {}

def get_gemini_key() -> str | None:
    return load_api_keys().get("gemini_api_key")

def get_openrouter_key() -> str | None:
    return load_api_keys().get("openrouter_api_key")

def is_configured() -> bool:
    try:
        key = get_gemini_key()
        return bool(key and len(str(key).strip()) > 15)
    except Exception:
        return False

def get_gemini_api_key() -> str:
    try:
        key = get_gemini_key()
        if key:
            return str(key).strip()
    except Exception:
        pass
    return ""