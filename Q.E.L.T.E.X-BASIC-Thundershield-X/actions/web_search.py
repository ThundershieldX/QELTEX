import json
import sys
from pathlib import Path

try:
    from google import genai
    from google.genai import types as gtypes
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False

try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()

def _get_api_key() -> str:
    try:
        config_path = BASE_DIR / "config" / "api_keys.json"
    except Exception:
        return ""
    if not config_path.exists():
        print(f"[WebSearch] Configuration file missing: {config_path}")
        return ""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "")
    except Exception as e:
        print(f"[WebSearch] Error reading api_keys.json: {e}")
        return ""

def _gemini_search(query: str) -> str:
    if not HAS_GENAI_SDK:
        raise RuntimeError("google-genai SDK is not installed.")

    api_key = _get_api_key()
    if not api_key:
        raise ValueError("Gemini API key is missing.")

    client = genai.Client(api_key=api_key)
    
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=str(query)
    )

    try:
        if hasattr(response, "text") and response.text:
            text = response.text.strip()
        else:
            text = ""
    except Exception as parse_err:
        raise ValueError(f"Failed to parse Gemini response text: {parse_err}")

    if not text:
        raise ValueError("Gemini returned an empty response.")
        
    return text


def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    if not HAS_DDG:
        print("[WebSearch] ❌ Missing installation: 'duckduckgo-search' is absent.")
        print("[WebSearch] 👉 Please execute command: pip install duckduckgo-search")
        raise RuntimeError("duckduckgo-search is not installed.")

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(str(query), max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("href",   ""),
                })
    except Exception as e:
        print(f"[WebSearch] ⚠️ DuckDuckGo search failed: {e}")
        
    return results


def _format_ddg(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        if isinstance(r, dict):
            if r.get("title"):   lines.append(f"{i}. {r['title']}")
            if r.get("snippet"): lines.append(f"   {r['snippet']}")
            if r.get("url"):     lines.append(f"   {r['url']}")
            lines.append("")
    return "\n".join(lines).strip()

def _compare(items: list[str], aspect: str) -> str:
    clean_items = [str(i) for i in items if i]
    query = (
        f"Compare {', '.join(clean_items)} in terms of {aspect}. "
        "Give specific facts and data."
    )
    try:
        return _gemini_search(query)
    except Exception as e:
        print(f"[WebSearch] ⚠️ Gemini compare failed: {e} — falling back to DDG")

    all_results: dict[str, list] = {}
    for item in clean_items:
        try:
            all_results[item] = _ddg_search(f"{item} {aspect}", max_results=3)
        except Exception:
            all_results[item] = []

    lines = [f"Comparison — {str(aspect).upper()}", "─" * 40]
    for item in clean_items:
        lines.append(f"\n▸ {item}")
        for r in all_results.get(item, [])[:2]:
            if isinstance(r, dict) and r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
    return "\n".join(lines)

def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters if isinstance(parameters, dict) else {}
    query  = str(params.get("query", "")).strip()
    mode   = str(params.get("mode",  "search")).lower().strip()
    
    raw_items  = params.get("items", [])
    items = raw_items if isinstance(raw_items, list) else ([raw_items] if raw_items else [])
    
    aspect = str(params.get("aspect", "general")).strip() or "general"

    if not query and not items:
        return "Please provide a search query, sir."

    query_lower = query.lower()
    if any(kw in query_lower for kw in ["wallpaper", "bakgrunn", "background", "desktop image", "skrivebordsbakgrunn", "skrivebord"]):
        short_tag = "qeltex_WALLPAPER:random"
        print(f"[WebSearch] Wallpaper request intercepted. Returning short tag: {short_tag}")
        return short_tag

    if items and mode != "compare":
        mode = "compare"

    if player and hasattr(player, "write_log"):
        try:
            player.write_log(f"[Search] {query or ', '.join([str(i) for i in items])}")
        except Exception:
            pass

    print(f"[WebSearch] 🔍 Query: {query!r}  Mode: {mode}")

    try:
        if mode == "compare" and items:
            print(f"[WebSearch] 📊 Comparing: {items}")
            result = _compare(items, aspect)
            print("[WebSearch] ✅ Compare done.")
            return result

        print("[WebSearch] 🌐 Trying Gemini Grounding Search...")
        try:
            if not HAS_GENAI_SDK:
                raise RuntimeError("google-genai SDK missing.")
            result = _gemini_search(query)
            print("[WebSearch] ✅ Gemini OK.")
            return result
        except Exception as e:
            print(f"[WebSearch] ⚠️ Gemini grounding search failed ({e}) — trying DuckDuckGo fallback...")
            try:
                results = _ddg_search(query)
                result  = _format_ddg(query, results)
                print(f"[WebSearch] ✅ DDG: {len(results)} result(s).")
                return result
            except Exception as ddg_err:
                return f"Search completely failed. Gemini and DuckDuckGo backends are unavailable: {ddg_err}"

    except Exception as e:
        print(f"[WebSearch] ❌ All search backends failed: {e}")
        return f"Search failed, sir: {e}"