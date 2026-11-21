import xml.etree.ElementTree as ET
import sys
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

def news_ticker(parameters: dict = None, player=None) -> str:
    if not requests:
        return "ERROR: 'requests' library is missing. Please install it to pull down news updates."

    rss_url = "https://nrk.no/nyheter/siste.rss"
    
    try:
        response = requests.get(rss_url, timeout=5)
        if response.status_code != 200:
            return f"ERROR: Could not connect to target news feed data endpoint (Status: {response.status_code})"
        
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        report = "--- Q.E.L.T.E.X DATASTREAM: LIVE NEWS ---\n\n"
        
        for i, item in enumerate(items[:5], 1):
            title = item.find("title").text if item.find("title") is not None else "No title available"
            description = item.find("description").text if item.find("description") is not None else ""
            if description:
                description = description.split("<")[0] if "<" in description else description
                description = description.strip()
            else:
                description = "No description available"
            
            report += f"{i}. {title}\n   {description[:140]}...\n\n"
            
        report += "-----------------------------------------"

        if player and hasattr(player, "_win") and hasattr(player._win, "qeltex_terminal_stream"):
            player._win.qeltex_terminal_stream.write_output(report)

        return report

    except Exception as e:
        return f"ERROR: Failed to synchronize global news data matrix loop: {str(e)}"

execute_action = news_ticker

if __name__ == "__main__":
    print(news_ticker())