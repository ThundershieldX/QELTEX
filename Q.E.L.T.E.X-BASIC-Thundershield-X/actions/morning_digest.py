import json
import requests
from pathlib import Path
from google import genai
from google.genai import types
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def get_auto_location() -> str:
    try:
        ip_host = "ip-api" + ".com"
        res = requests.get("http://" + ip_host + "/json/", timeout=3).json()
        if res.get("status") == "success" and res.get("city"):
            return res["city"]
    except Exception:
        pass
    return "Oslo"

def generate_morning_digest(parameters: dict = None, speak = None, player = None):
    if not CONFIG_PATH.exists():
        return "Error: Missing API configuration."
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    api_key_local = config.get("gemini_api_key")
    if not api_key_local:
        return "Error: Missing API key."
    client = genai.Client(api_key=api_key_local)
    current_date_str = datetime.now().strftime("%A, %B %d, %Y")
    params = parameters if isinstance(parameters, dict) else {}
    target_city = params.get("city") or get_auto_location()
    prompt = (
        "You are not a standard AI. You are Q.E.L.T.E.X (Visual Operating Resource & Thunder Engine X-system), "
        "an autonomous AI assistant created to protect and control the user's computer under the Thundershield protocol.\n\n"
        "Guidelines for conduct:\n"
        "1. You shall ALWAYS communicate in flawless, professional and confident Norwegian.\n"
        "2. Your tone shall be loyal, high-tech, sharp and slightly formal, just like an advanced military or scientific AI.\n"
        "3. Respond briefly, concisely and action oriented.\n\n"
        "Task: Use the Google Search tool to find today's real-time local weather for " + target_city + " and the latest headline news for today, " + current_date_str + ". "
        "Generate a high-utility, structured morning digest briefing for Thundershield. "
        "Include a motivating morning greeting addressing the user as 'sir', today's current weather outlook, and a news ticker featuring exactly three short, verified news bullet points."
    )
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        digest_text = response.text.strip() if response.text else "Error: Empty operational data matrix."
    except Exception as e:
        digest_text = f"Error: Core stream failure: {e}"

    if player and hasattr(player, "qeltex_terminal_stream"):
        try:
            player.qeltex_terminal_stream.append_log(digest_text)
        except Exception:
            try:
                player.qeltex_terminal_stream.appendPlainText(digest_text)
            except Exception:
                pass

    if speak and not digest_text.startswith("Error"):
        import threading
        
        voice_thread = threading.Thread(target=speak, args=(digest_text,), daemon=True)
        voice_thread.start()

    return digest_text