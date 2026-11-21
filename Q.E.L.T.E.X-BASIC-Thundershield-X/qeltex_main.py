import os
import asyncio
import re
import threading
import json
import sys
import multiprocessing
multiprocessing.freeze_support()

if "--overlay" in sys.argv:
    _ov_idx = sys.argv.index("--overlay")
    _ov_mode = sys.argv[_ov_idx + 1] if len(sys.argv) > _ov_idx + 1 else "matrix"
    _ov_game = (sys.argv[_ov_idx + 2] == "1") if len(sys.argv) > _ov_idx + 2 else False
    from PyQt6.QtWidgets import QApplication
    from qeltex_ui import VisualOverlayWindow
    _ov_app = QApplication(sys.argv)
    _ov_win = VisualOverlayWindow(mode=_ov_mode, is_game=_ov_game)
    _ov_win.show()
    sys.exit(_ov_app.exec())

import time
import traceback
import subprocess
from pathlib import Path
from PyQt6.QtWebEngineWidgets import QWebEngineView

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

if getattr(sys, "frozen", False):
    _CURRENT_DIR = Path(os.path.realpath(sys.executable)).parent
else:
    _CURRENT_DIR = Path(__file__).resolve().parent

if str(_CURRENT_DIR) not in sys.path:
    sys.path.append(str(_CURRENT_DIR))

if sys.platform == "win32" and getattr(sys, "frozen", False):
    class InvisibleProcess:
        def __init__(self, original_popen):
            self.original_popen = original_popen
        def __call__(self, *args, **kwargs):
            args_str = str(args).lower()
            if any(x in args_str for x in ["portaudio", "sound", "opencv", "video", "cap", "camera"]):
                return self.original_popen(*args, **kwargs)
                
            if "startupinfo" not in kwargs:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                kwargs["startupinfo"] = si
            return self.original_popen(*args, **kwargs)
    subprocess.Popen = InvisibleProcess(subprocess.Popen)

MISSING_PACKAGES = []
try:
    import sounddevice as sd 
except ImportError:
    MISSING_PACKAGES.append("sounddevice")
try:
    from google import genai
    from google.genai import types
except ImportError:
    MISSING_PACKAGES.append("google-genai")

if MISSING_PACKAGES:
    print(f"\n❌ [qeltex] CRITICAL SYSTEM ERROR: Missing required installations for the Thundershield protocol!")
    print(f"👉 Please execute command: pip install {' '.join(MISSING_PACKAGES)}")
    sys.exit(1)

try:
    from qeltex_ui import qeltexUI
    from memory.memory_manager import (
        load_memory, update_memory, format_memory_for_prompt,
    )
except ImportError as e:
    print(f"\n❌ [qeltex] Critical core import failed: {e}")
    sys.exit(1)

try:
    from actions.file_processor import file_processor
    from actions.open_app import open_app
    
    try:
        from actions.weather_report import weather_report
    except ImportError:
        try:
            from actions.weather_report import weather_action as weather_report
        except ImportError:
            from actions.weather_report import weather as weather_report

    from actions.send_message import send_message
    from actions.reminder import reminder
    from actions.computer_settings import computer_settings
    from actions.screen_processor import screen_process
    from actions.desktop import desktop_control
    from actions.browser_control import browser_control
    from actions.file_controller import file_controller
    from actions.web_search import web_search as web_search_action
    from actions.computer_control import computer_control
    from actions.system_monitor import execute_action as system_monitor
    from actions.network_shield import execute_action as network_shield
    from actions.news_ticker import execute_action as news_ticker
    from actions.token_budget_shield import budget_shield_action
    from actions.morning_digest import generate_morning_digest
    from actions.radio import execute_radio_action
    from actions.capabilities import show_capabilities
except ImportError as e:
    print(f"\n❌ [qeltex] Critical error: Could not initialize action catalog: {e}")
    sys.exit(1)

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"

LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

def _get_api_key() -> str:
    if not API_CONFIG_PATH.exists():
        print(f"\n❌ [qeltex] Initialization aborted. File not found: {API_CONFIG_PATH}")
        sys.exit(1)
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            return str(config_data["gemini_api_key"]).strip()
    except Exception as e:
        print(f"\n❌ [qeltex] Critical error in the format of api_keys.json: {e}")
        sys.exit(1)

def _load_system_prompt() -> str:
    fallback_text = (
        "You are QELTEX, pronounced Keltex (Quantum Engineered Logic & Tactical Executor X-system). "
        "Created by a programmer from Norway who calls themselves Thundershield-X. "
        "Communicate in flawless, professional and confident Norwegian. "
        "Respond briefly, concisely and action oriented."
    )
    try:
        if not PROMPT_PATH.exists():
            PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
            PROMPT_PATH.write_text(fallback_text, encoding="utf-8")
            return fallback_text
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[qeltex] ⚠️ Warning reading system prompt: {e}. Activating default Thundershield protocol.")
        return fallback_text

_CTRL_RE = re.compile(r"ltctrl\d+gt", re.IGNORECASE)

def _clean_transcript(text: str) -> str:
    if not isinstance(text, str):
        return ""
    try:
        text = _CTRL_RE.sub("", text)
        text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
        return text.strip()
    except Exception as e:
        print(f"[qeltex] ⚠️ Error during text cleaning: {e}")
        return text.strip() if hasattr(text, "strip") else ""


TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Opens any application on the computer. Use this whenever the user asks to open, launch, or start any app, website, or program. Always call this tool — never just say you opened it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "system_monitor",
        "description": "ALWAYS call this tool immediately when the operator commands to show, check, status, open, or close the hardware performance, system metrics, CPU/RAM status, or diagnostic telemetry. Set action to play to launch the performance ring gauges, or set action to stop to turn off the hardware tracking window cleanly.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "The task to execute: play to initialize and display the hardware diagnostics window, or stop to turn off and close the system metrics overlay."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "execute_radio_action",
        "description": "Call this tool whenever the user wants to play, stop, list, or control local internet live radio streams. You can pass station to filter or find a specific channel like juleradioen, radionorge, nrjnorge, p247mix, p247kos, p11dance, p4, p5hits, p7klem, nrkmp3, p8pop, p10country, p9retro, p12hitmix, p6rock, radiometro, silkeveienradio, radionova, ordentligradio, radionano, radiorox, nrkp13, or radiotønsberg. Set action to stop to turn off the radio broadcast matrix cleanly, or set action to list to display all available live streams inside the automation layout.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "The specific task to perform: play to engage a live internet radio stream, stop to terminate background audio broadcast matrix channels cleanly, or list to output a text list of all registered live radio channels."
                },
                "station": {
                    "type": "STRING",
                    "description": "The name of the target radio channel frequency matrix like juleradioen, radionorge, nrjnorge, p247mix, p247kos, p11dance, p4, p7klem, radiotønsberg, or nrkmp3. Leave blank if not specified."
                }
            }
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"},
                "mode": {"type": "STRING", "description": "search (default) or compare"},
                "items": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "ALWAYS call this tool immediately when the operator commands to show, check, status, open, or close the meteorological matrix, weather reports, regional forecasts, or atmospheric telemetry. Set action to play to launch the weather tracking display, or set action to stop to turn off the weather matrix window cleanly.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "The task to execute: play to initialize and display the weather matrix window, or stop to turn off and close the weather overlay."
                },
                "city": {
                    "type": "STRING",
                    "description": "The target city or region to gather weather telemetry for. Leave empty to automatically detect the operator's current location."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "send_message",
        "description": "ALWAYS call this tool immediately for any request to send an email, email reminder, Gmail, or message to the user. Use this tool directly — NEVER route to agent_task or any other background queue for emails.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver": {"type": "STRING", "description": "Recipient contact email address or name from the system configuration file"},
                "message_text": {"type": "STRING", "description": "The complete body text or content of the email to transmit"},
                "platform": {"type": "STRING", "description": "Must be set to 'email' or 'Gmail' for email transmissions"}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date": {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "screen_process",
        "description": "Captures and analyzes the screen or webcam image. MUST be called when user asks what is on screen, what you see, analyze my screen, look at camera, etc. You have NO visual ability without this tool. After calling this tool, stay SILENT — the Q.E.L.T.E.X vision module speaks directly.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text": {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": "Controls the computer: volume, brightness, window management, keyboard shortcuts, typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. Use for ANY single computer control command. NEVER route to agent_task.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value": {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": "Controls any web browser. Use for: opening websites, searching the web, clicking elements, filling forms, scrolling, screenshots, navigation, any web-based task. Always pass the 'browser' parameter when the user specifies a browser (e.g. 'open in Edge', 'use Firefox', 'open Chrome'). Multiple browsers can run simultaneously.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all"},
                "browser": {"type": "STRING", "description": "Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active browser."},
                "url": {"type": "STRING", "description": "URL for go_to / new_tab action"},
                "query": {"type": "STRING", "description": "Search query for search action"},
                "engine": {"type": "STRING", "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"},
                "selector": {"type": "STRING", "description": "CSS selector for click/type"},
                "text": {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction": {"type": "STRING", "description": "up | down for scroll"},
                "amount": {"type": "INTEGER", "description": "Scroll amount in pixels (default: 500)"},
                "key": {"type": "STRING", "description": "Key name for press action (e.g. Enter, Escape, F5)"},
                "path": {"type": "STRING", "description": "Save path for screenshot"},
                "incognito": {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path": {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name": {"type": "STRING", "description": "New name for rename"},
                "content": {"type": "STRING", "description": "Content for create_file/write"},
                "name": {"type": "STRING", "description": "File name to search for"},
                "extension": {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count": {"type": "INTEGER", "description": "Number of results for largest"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats. ALWAYS use this tool immediately when the user asks to change, update, or set the wallpaper/desktop background, even if they don't provide an image or URL.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING", 
                    "description": "wallpaper (for local path) | wallpaper_url (for internet images or random generation) | organize | clean | list | stats | task"
                },
                "path": {"type": "STRING", "description": "Image path for local wallpaper"},
                "url": {
                    "type": "STRING", 
                    "description": "Image URL for wallpaper_url. CRITICAL: If the user wants a random, new, or unspecified wallpaper, set action to 'wallpaper_url' and pass 'qeltex_WALLPAPER:default' as the url."
                },
                "mode": {"type": "STRING", "description": "by_type or by_date for organize"},
                "task": {"type": "STRING", "description": "Natural language desktop task"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "agent_task",
        "description": "Executes complex multi-step tasks requiring multiple different tools. Examples: 'research X and save to file', 'find and organize files'. DO NOT use for single commands.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal": {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text": {"type": "STRING", "description": "Text to type or paste"},
                "x": {"type": "INTEGER", "description": "X coordinate"},
                "y": {"type": "INTEGER", "description": "Y coordinate"},
                "keys": {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key": {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction": {"type": "STRING", "description": "up | down | left | right"},
                "amount": {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds": {"type": "NUMBER", "description": "Seconds to wait"},
                "title": {"type": "STRING", "description": "Window title for focus_window"},
                "description": {"type": "STRING", "description": "Element description for screen_find/screen_click"},
                "type": {"type": "STRING", "description": "Data type for random_data"},
                "field": {"type": "STRING", "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path": {"type": "STRING", "description": "Save path for screenshot"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "shutdown_qeltex",
        "description": "Shuts down the assistant completely. Call this when the user expresses intent to end the conversation, close the assistant, say goodbye, or stop qeltex. The user can say this in ANY language.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "activate_stealth_mode",
        "description": "ALWAYS call this tool immediately when the user commands 'qeltex, gå til Stealth' or asks to clear/clean the screen to hide panels and show the minimalist core.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "activate_tactical_mode",
        "description": "ALWAYS call this tool immediately when the user asks to show everything, show all panels, restore windows, or 'vis alt' / 'aktiver tactical' to return to full dashboard layout.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "activate_pin_lock",
        "description": "ALWAYS call this tool immediately when the user commands 'pin lock', 'lås skjerm', or requests to lock the secure radar portal interface.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "file_processor",
        "description": "Processes any file that the user has uploaded or dropped onto the interface. Use this when the user refers to an uploaded file and wants an action on it. Supports: images (describe/ocr/resize/compress/convert), PDFs (summarize/extract_text/to_word), Word docs & text files (summarize/fix/reformat/translate), CSV/Excel (analyze/stats/filter/sort/convert), JSON/XML (validate/format/analyze), code files (explain/review/fix/optimize/run/document/test), audio (transcribe/trim/convert/info), video (trim/extract_audio/extract_frame/compress/transcribe/info), archives (list/extract), presentations (summarize/extract_text). ALWAYS call this tool when a file has been uploaded and the user gives a command about it. If the user's command is ambiguous, pick the most logical action for that file type.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
                },
                "action": {
                    "type": "STRING",
                    "description": "What to do with the file. Examples by type:\nimage: describe | ocr | resize | compress | convert | info\npdf: summarize | extract_text | to_word | info\ndocx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\ncsv/excel: analyze | stats | filter | sort | convert | info\njson: validate | format | analyze | to_csv\ncode: explain | review | fix | optimize | run | document | test\naudio: transcribe | trim | convert | info\nvideo: trim | extract_audio | extract_frame | compress | transcribe | info | convert\narchive: list | extract\npptx: summarize | extract_text | analyze"
                },
                "instruction": {
                    "type": "STRING",
                    "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
                },
                "format": {
                    "type": "STRING",
                    "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
                },
                "width":     {"type": "INTEGER", "description": "Target width for image resize"},
                "height":    {"type": "INTEGER", "description": "Target height for image resize"},
                "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
                "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
                "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
                "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
                "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
                "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
                "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
                "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
                "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
                "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
                "destination": {"type": "STRING", "description": "Output folder for archive extract"}
            },
            "required": []
        }
    },
    {
    "name": "save_memory",
    "description": "Save an important personal fact about the user to long-term memory. Call this silently whenever the user reveals something worth remembering: name, age, city, job, preferences, hobbies, relationships, projects, or future plans. Do NOT call for: weather, reminders, searches, or one-time commands. Do NOT announce that you are saving — just call it silently. Values must be in English regardless of the conversation language.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "category": {
                "type": "STRING",
                "description": "identity — name, age, birthday, city, job, language, nationality | preferences — favorite food/color/music/film/game/sport, hobbies | projects — active projects, goals, things being built | relationships — friends, family, partner, colleagues | wishes — future plans, things to buy, travel dreams | notes — habits, schedule, anything else worth remembering"
            },
            "key":   {"type": "STRING", "description": "Short system_key (e.g. operator_alias, core_protocol, defense_matrix)"},
            "value": {"type": "STRING", "description": "Concise value in English (e.g. Thundershield-X, cyber_security, asset_protection)"}
        },
         "required": ["category", "key", "value"]
        }
    },
    {
        "name": "budget_shield",
        "description": "Checks or adjusts the Gemini API token budget and financial safety boundaries.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "check | set_budget"},
                "max_usd_per_hour": {"type": "NUMBER", "description": "Hourly spending ceiling in USD (default: 5.0)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "news_ticker",
        "description": "ALWAYS call this tool immediately when the user asks for latest news headlines or news updates. Tell the user in Norwegian that you are outputting the news ticker directly to the automation terminal stream on screen.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "morning_digest",
        "description": "ALWAYS call this tool immediately when the user asks for a morning briefing ('morgenbrifing', 'morning digest', 'gi meg morgen brifing'). Tell the user in Norwegian that you are outputting the secure data briefing directly to the automation terminal stream on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "Optional target city for the weather outlook in the morning briefing."}
            }
        }
    },
    {
        "name": "show_capabilities",
        "description": "ALWAYS call this tool immediately when the user asks what you can do ('hva kan du gjøre', 'what can you do', 'hjelp', 'kommandoer'). Tell the user in their language that you have displayed the full list of capabilities and example commands in the right terminal panel.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "close_active_menu",
        "description": "ALWAYS call this tool immediately when the operator commands to close, collapse, hide, or shut down any active drop-down overlay or telemetry menu (for example: 'lukk menyen', 'fjern menyen'). This triggers a global escape matrix to drop the panel.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "close_hud_display",
        "description": "ALWAYS call this tool immediately when the operator commands to toggle off, close, hide, or deactivate the active HUD diagnostic layout dashboard panels (for example: 'lukk hud', 'skru av huddisplay', or 'fjern hud').",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "activate_config_theme",
        "description": "ALWAYS call this tool immediately when the operator commands to switch, apply, change, or set a concrete qeltex dashboard layout configuration color theme (for example: 'aktiver theme purple', 'sett farge til rød', 'velg theme cyan', or 'team purple'). Pass theme_name strictly in lowercase english matching the requested palette.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "theme_name": {
                    "type": "STRING",
                    "description": "The exact target color identifier key string in lowercase: 'green', 'blue', 'red', 'yellow', 'purple', or 'cyan'."
                }
            },
            "required": ["theme_name"]
        }
    }
]

class qeltexLive:

    def __init__(self, ui: qeltexUI):
        if ui is None:
            raise RuntimeError("Critical error: qeltexUI instance is invalid. Cannot initialize the Thundershield protocol.")
            
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.last_interaction_time = time.time()
        
        try:
            self.ui.on_text_command = self._on_text_command
        except Exception as e:
            print(f"[qeltex] ⚠️ Could not bind text command to UI interface: {e}")
            
        self._turn_done_event: asyncio.Event | None = None
        self._tool_running = False

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return

        clean_command = str(text).lower().strip()
        
        if hasattr(self, "ui") and self.ui and hasattr(self.ui, "_win"):
            win = self.ui._win
            
            if getattr(win, "_button_grid_widget", None):
                if "lukk" in clean_command or "skjul" in clean_command or "bort" in clean_command:
                    if getattr(win, "_buttons_visible", False):
                        win._buttons_visible = False
                        win._button_grid_widget.hide()
                        if getattr(win, "_toggle_trigger_btn", None):
                            win._toggle_trigger_btn.setText("◈  ENGAGE CONTROL CORE  ◈")
                    if clean_command in ["lukk meny", "lukk", "skjul meny"]:
                        if hasattr(self.ui, "qeltex_terminal_stream"):
                            self.ui.qeltex_terminal_stream.write_output("\nqeltex: Menyen er nå lukket.")
                        return

                elif "meny" in clean_command or any(k in clean_command for k in ["huds", "theme", "radio"]):
                    if not getattr(win, "_buttons_visible", False):
                        win._buttons_visible = True
                        win._button_grid_widget.show()
                        win._button_grid_widget.raise_()
                        if getattr(win, "_toggle_trigger_btn", None):
                            win._toggle_trigger_btn.setText("◈  TERMINATE CONTROL CORE  ◈")
                    
                    if clean_command in ["åpne meny", "meny", "vis meny"]:
                        if hasattr(self.ui, "qeltex_terminal_stream"):
                            self.ui.qeltex_terminal_stream.write_output("\nqeltex: Aktiverer fullt dashboard layout.")
                        return

        if "terminal" in clean_command or "stream" in clean_command or "automatisering" in clean_command:
            try:
                terminal_content = ""
                if hasattr(self.ui, "qeltex_terminal_stream"):
                    terminal_content = self.ui.qeltex_terminal_stream.toPlainText().strip()
                elif hasattr(self.ui, "_win") and hasattr(self.ui._win, "qeltex_terminal_stream"):
                    terminal_content = self.ui._win.qeltex_terminal_stream.toPlainText().strip()
                
                if not terminal_content:
                    terminal_content = "Terminalstrømmen er for øyeblikket tom, sir."
                
                self.ui.set_status_text("SYS: Henter terminalstrøm. Lesing påbegynt.")
                
                forced_reading_prompt = (
                    f"Du skal nå fungere utelukkende som en ordrett tekstoppleser for Thundershield. "
                    f"Les opp følgende tekst nøyaktig slik den står skrevet, ord for ord, uten å omskrive, "
                    f"uten å oppsummere, og uten å legge til egne kommentarer:\n\n{terminal_content}"
                )
                
                import asyncio as local_asyncio
                local_asyncio.run_coroutine_threadsafe(
                    self.session.send_client_content(
                        turns={"parts": [{"text": forced_reading_prompt}]},
                        turn_complete=True
                    ),
                    self._loop
                )
                return
            except Exception as execution_error:
                print(f"[qeltex] Local read failure: {execution_error}")

        try:
            self.last_interaction_time = time.time()
            self.ui.set_status_text("SYS: Processing command sequence...")
            self.ui.set_progress_value(15)
            
            import asyncio as global_asyncio
            global_asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": str(text)}]},
                    turn_complete=True
                ),
                self._loop
            )
            def _reset():
                import time as local_time
                local_time.sleep(1.5)
                if hasattr(self.ui, "_win") and hasattr(self.ui._win, "hud"):
                    if self.ui._win.hud.state not in ("SPEAKING", "THINKING"):
                        self.ui.set_status_text("QELTEX Core: System Standby")
                        self.ui.set_progress_value(0)
            
            import threading as global_threading
            global_threading.Thread(target=_reset, daemon=True).start()
        except Exception as e:
            print(f"[qeltex] ⚠️ Error sending text command: {e}")
            self.ui.set_status_text("QELTEX Core: System Standby")
            self.ui.set_progress_value(0)

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": str(text)}]},
                    turn_complete=True
                ),
                self._loop
            )
        except Exception as e:
            print(f"[qeltex] ⚠️ Error during speak transmission: {e}")

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Thundershield, the tool {tool_name} encountered an error. Details: {short}")
        self.ui.set_status_text("QELTEX Core: System Standby")
        self.ui.set_progress_value(0)

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime
        try:
            memory     = load_memory()
            mem_str    = format_memory_for_prompt(memory)
        except Exception as e:
            print(f"[qeltex] ⚠️ Warning: Could not load memory module: {e}")
            mem_str = ""
        sys_prompt = _load_system_prompt()
        user_email = ""
        try:
            if API_CONFIG_PATH.exists():
                with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    user_email = str(config_data.get("gmail_username", "")).strip()
        except Exception:
            pass

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        email_ctx = ""
        if user_email:
            email_ctx = (
                f"[USER CONTACT CONFIGURATION]\n"
                f"The operator's email address is stored securely as: {user_email}\n"
                f"Always target this address automatically when executing emails.\n\n"
            )

        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
            f"{email_ctx}"
        )
        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        extended_declarations = list(TOOL_DECLARATIONS)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": extended_declarations}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = str(fc.name or "").strip()
        args = dict(fc.args or {})
        print(f"[qeltex] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")
        self._tool_running = True
        
        if name == "save_memory":
            category = str(args.get("category", "notes"))
            key      = str(args.get("key", ""))
            value    = str(args.get("value", ""))
            if key and value:
                try:
                    update_memory({category: {key: {"value": value}}})
                    print(f"[qeltex] 💾 Long-term memory saved: {category}/{key} = {value}")
                    res_msg = "ok"
                except Exception as e:
                    print(f"[qeltex] ❌ Could not update memory file: {e}")
                    res_msg = f"failed to save memory: {e}"
            else:
                res_msg = "missing key or value"
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": res_msg, "silent": True}
            )
           
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        if hasattr(self, "ui") and self.ui and hasattr(self.ui, "_win"):
            win = self.ui._win
            if getattr(win, "_toggle_trigger_btn", None) and getattr(win, "_button_grid_widget", None):
                
                is_closing_command = False
                if "close" in name:
                    is_closing_command = True
                elif str(args.get("state", "")).lower() in ["false", "off"]:
                    is_closing_command = True
                    
                if is_closing_command:
                    if getattr(win, "_buttons_visible", False) or win._button_grid_widget.isVisible():
                        win._toggle_trigger_btn.click()
                else:
                    target_arg = str(args.get("target", "")).lower().strip()
                    
                    is_ui_request = (
                        "menu" in name or 
                        "menu" in target_arg
                    )
                    
                    if is_ui_request:
                        if not getattr(win, "_buttons_visible", False) or not win._button_grid_widget.isVisible():
                            win._toggle_trigger_btn.click()

        if name == "execute_radio_action":
            try:
                from actions.radio import execute_radio_action
                result = await loop.run_in_executor(None, lambda: execute_radio_action(parameters=args, player=self.ui))
                if result:
                    if hasattr(self.ui, "_win") and hasattr(self.ui._win, "qeltex_terminal_stream"):
                        self.ui._win.qeltex_terminal_stream.write_output(result)
                    elif hasattr(self.ui, "qeltex_terminal_stream"):
                        self.ui.qeltex_terminal_stream.write_output(result)
            except Exception as e:
                result = f"Could not launch radio framework backend layout: {e}"
                print(f"[qeltex] Radio matrix routing error: {e}")
            self._tool_running = False
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(id=fc.id, name=name, response={"result": result})

        if name == "activate_hud_display":
            try:
                mode_arg = str(args.get("mode", "")).lower().strip()
                if mode_arg and mode_arg != "none":
                    try:
                        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                            config_data = json.load(f)
                        config_data["qeltex_hud"] = mode_arg
                        with open(API_CONFIG_PATH, "w", encoding="utf-8") as f:
                            json.dump(config_data, f, indent=4, ensure_ascii=False)
                        print(f"--- MAIN: HUD DISPLAY MODE SAVED TO CONFIG JSON -> {mode_arg} ---")
                    except Exception as json_err:
                        print(f"--- MAIN ERROR: COULD NOT WRITE HUD TO CONFIG JSON: {json_err} ---")

                if not mode_arg or mode_arg == "none" or mode_arg == "classic":
                    import ctypes
                    ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x79, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x79, 0, 2, 0)
                    ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
                else:
                    if hasattr(self.ui, "_win") and hasattr(self.ui._win, "_hud_sig"):
                        self.ui._win._hud_sig.emit(mode_arg)
            except Exception as e:
                print(f"[qeltex ERROR] HUD display failed to ignite: {e}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"status": "complete", "result": f"hud display updated and saved as {mode_arg}"}
            )

        result = "Done."

        try:
            if name == "system_monitor":
                try:
                    params = fc.args if hasattr(fc, "args") else {}
                    action_type = str(params.get("action", "play")).lower().strip()
                    
                    if action_type in ("stop", "off", "stopp", "slåav"):
                        try:
                            import ctypes
                            import win32gui
                            import win32con
                            
                            ctypes.windll.winmm.mciSendStringW("stop Q.E.L.T.E.X_S.Y.S_M.A.P", None, 0, 0)
                            ctypes.windll.winmm.mciSendStringW("close Q.E.L.T.E.X_S.Y.S_M.A.P", None, 0, 0)
                            
                            hwnd = win32gui.FindWindow(None, "qeltex_system_diagnostics")
                            if hwnd:
                                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                                
                            result = "[DIAGNOSTICS CONTROL] Diagnostics overlay terminated cleanly, sir."
                        except Exception as e:
                            result = f"ERROR: Ctypes window termination failed: {e}"
                    else:
                        result = await loop.run_in_executor(None, lambda: system_monitor(params))
                except Exception as e:
                    result = f"ERROR: System monitor operations disruption: {e}"
                    
                if hasattr(self.ui, "_win") and hasattr(self.ui._win, "qeltex_terminal_stream"):
                    self.ui._win.qeltex_terminal_stream.write_output(f"[SYSTEM MONITOR]\n{result}")
                if not self.ui.muted: 
                    self.ui.set_state("LISTENING")
                return types.FunctionResponse(id=fc.id, name=name, response={"status": "complete"})

            elif name == "network_shield":
                result = await loop.run_in_executor(None, network_shield)
                if hasattr(self.ui, "_win") and hasattr(self.ui._win, "qeltex_terminal_stream"):
                    self.ui._win.qeltex_terminal_stream.write_output(f"[NETWORK SHIELD]\n{result}")
                if not self.ui.muted: self.ui.set_state("LISTENING")
                return types.FunctionResponse(id=fc.id, name=name, response={"status": "complete"})

            elif name == "news_ticker":
                try:
                    result = await loop.run_in_executor(None, lambda: news_ticker(parameters=args, player=self.ui))
                    if result:
                        if hasattr(self.ui, '_win') and hasattr(self.ui._win, 'qeltex_terminal_stream'):
                            self.ui._win.qeltex_terminal_stream.write_output(f"[NEWS TICKER]\n{result}")
                        elif hasattr(self.ui, 'qeltex_terminal_stream'):
                            self.ui.qeltex_terminal_stream.write_output(f"[NEWS TICKER]\n{result}")
                except Exception as e:
                    result = f"Failed to execute news ticker pipeline: {e}"
                if not self.ui.muted: self.ui.set_state("LISTENING")
                return types.FunctionResponse(id=fc.id, name=name, response={"status": "complete", "result": str(result)})

            elif name == "morning_digest":
                try:
                    self.ui.set_status_text("SYS: Compiling Morning Briefing...")
                    import threading
                    def _run_digest():
                        try:
                            content = generate_morning_digest(parameters=args, player=self.ui)
                            if hasattr(self.ui, '_win') and hasattr(self.ui._win, 'qeltex_terminal_stream'):
                                self.ui._win.qeltex_terminal_stream.write_output(f"[MORNING BRIEFING]\n{content}")
                            elif hasattr(self.ui, 'qeltex_terminal_stream'):
                                self.ui.qeltex_terminal_stream.write_output(f"[MORNING BRIEFING]\n{content}")
                        except Exception as e:
                            from pathlib import Path
                            import traceback
                            with open(Path(__file__).resolve().parent / "morning_error.txt", "w", encoding="utf-8") as f:
                                f.write(f"Terminal Output Error: {str(e)}\n")
                                traceback.print_exc(file=f)
                        if hasattr(self.ui, 'set_status_text'):
                            self.ui.set_status_text("QELTEX Core: System Standby")
                    threading.Thread(target=_run_digest, daemon=True).start()
                    result = "Success"
                except Exception as e:
                    result = f"Failed to execute morning briefing pipeline: {e}"
                if not self.ui.muted: self.ui.set_state("LISTENING")
                return types.FunctionResponse(id=fc.id, name=name, response={"status": "complete"})
        except Exception as e:
            print(f"[qeltex ERROR] Could not execute extension {name}: {e}")
            result = f"Error executing {name}: {str(e)}"
            if not self.ui.muted: self.ui.set_state("LISTENING")
            return types.FunctionResponse(id=fc.id, name=name, response={"result": result})

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                try:
                    params = fc.args if hasattr(fc, "args") else {}
                    action_type = str(params.get("action", "play")).lower().strip()
                    
                    if action_type in ("stop", "off", "stopp", "slåav", "lukk"):
                        try:
                            import ctypes
                            import win32gui
                            import win32con
                            
                            ctypes.windll.winmm.mciSendStringW("stop Q.E.L.T.E.X_W.E.A.T.H.E.R", None, 0, 0)
                            ctypes.windll.winmm.mciSendStringW("close Q.E.L.T.E.X_W.E.A.T.H.E.R", None, 0, 0)
                            
                            hwnd = win32gui.FindWindow(None, "qeltex_weather_matrix")
                            if hwnd:
                                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                                
                            result = "[WEATHER CONTROL] Weather matrix overlay terminated cleanly, sir."
                        except Exception as e:
                            result = f"ERROR: Ctypes window termination failed: {e}"
                    else:
                        from actions.weather_report import weather_report
                        result = weather_report(params)
                except Exception as e:
                    result = f"ERROR: Weather operations disruption: {e}"
                    
                if hasattr(self.ui, "_win") and hasattr(self.ui._win, "qeltex_terminal_stream"):
                    self.ui._win.qeltex_terminal_stream.write_output(f"[WEATHER REPORT]\n{result}")
                if not self.ui.muted: 
                    self.ui.set_state("LISTENING")
                return types.FunctionResponse(id=fc.id, name=name, response={"status": "complete"})

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Browser operation executed."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "File control operation executed."

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder configured."

            elif name == "show_capabilities":
                r = await loop.run_in_executor(None, lambda: show_capabilities(parameters=args, player=self.ui))
                result = r or "Displayed capabilities list in the right terminal panel."

            elif name == "screen_process":
                try:
                    import threading
                    threading.Thread(
                        target=screen_process,
                        kwargs={"parameters": args, "response": None,
                                "player": self.ui, "session_memory": None},
                        daemon=True
                    ).start()
                    result = "Vision module activated. Please remain silent — the vision module will report status directly."
                except Exception as e:
                    result = f"Could not start vision module: {e}"

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "System settings updated."

            elif name == "desktop_control":
                if isinstance(args, dict):
                    check_clean = (str(args.get("task", "")) + " " + str(args.get("url", "")) + " " + str(args.get("action", ""))).lower()
                    if any(kw in check_clean for kw in ["url", "nett", "online", "internett", "random"]):
                        args["task"] = "url"
                    else:
                        args["task"] = "lokal"
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Desktop operation executed."

            elif name == "agent_task":
                try:
                    from agent.task_queue import get_queue, TaskPriority
                    priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                    priority = priority_map.get(str(args.get("priority", "normal")).lower(), TaskPriority.NORMAL)
                    task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                    result   = f"Complex task initiated (ID: {task_id})."
                except Exception as e:
                    result = f"Could not queue task: {e}"
                    print(f"[qeltex] ❌ TaskQueue error: {e}")

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Search completed."

            elif name == "budget_shield":
                r = await loop.run_in_executor(None, lambda: budget_shield_action(parameters=args, player=self.ui))
                result = r or "Budget shield monitoring active."
                
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "File processing completed."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Interface control completed."

            elif name == "activate_stealth_mode":
                self.ui.activate_stealth_mode()
                result = "Success"

            elif name == "activate_pin_lock":
                if hasattr(self.ui._win, "activate_pin_lock"):
                    self.ui._win.activate_pin_lock()
                result = "Success"

            elif name == "activate_tactical_mode":
                self.ui.activate_tactical_mode()
                result = "Success"

            elif name == "shutdown_qeltex":
                try: self.ui.write_log("SYS: Shutdown initiated.")
                except Exception: pass
                self.speak("Thundershield protocol deactivating. Closing core components now. System going offline.")
                def _shutdown():
                    import time, os
                    time.sleep(1.2)
                    os._exit(0)
                
                import threading as local_threading
                local_threading.Thread(target=_shutdown, daemon=True).start()

            elif name == "close_active_menu":
                try:
                    print("--- MAIN: CLOSING OVERLAY ATTEMPT VIA GLOBAL ESCAPE SEQUENCE ---")
                    import ctypes
                    ctypes.windll.user32.keybd_event(0x1B, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x1B, 0, 2, 0)
                except Exception as e:
                    print(f"--- MAIN ERROR: ESCAPE SEQUENCE FAILED: {e} ---")
                self._tool_running = False
                if not self.ui.muted: self.ui.set_state("LISTENING")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "menu overlay closed"})

            elif name == "close_hud_display":
                try:
                    print("--- MAIN: CLOSING HUD MENU VIA ESCAPE SIMULATION ---")
                    import ctypes
                    ctypes.windll.user32.keybd_event(0x1B, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x1B, 0, 2, 0)
                except Exception as e:
                    print(f"--- MAIN ERROR: HUD CLOSE FAILED: {e} ---")
                self._tool_running = False
                if not self.ui.muted: self.ui.set_state("LISTENING")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "hud overlay closed"})

            elif name == "activate_config_theme":
                t_target = "unknown"
                try:
                    raw_args_str = str(args).lower()
                    for color_option in ["green", "blue", "red", "yellow", "purple", "cyan"]:
                        if color_option in raw_args_str:
                            t_target = color_option
                            break
                    print(f"--- MAIN: SIMULATING CONFIG THEME CHANGE SIGNAL -> {t_target} ---")
                    if t_target != "unknown" and hasattr(self.ui, "_win") and hasattr(self.ui._win, "_theme_sig"):
                        self.ui._win._theme_sig.emit(t_target)
                except Exception as e:
                    print(f"--- MAIN ERROR: THEME CHANGE MATRIX FAILED: {e} ---")
                self._tool_running = False
                if not self.ui.muted: self.ui.set_state("LISTENING")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"configuration color theme shifted to {t_target}"})

            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[qeltex] 📤 {name} → {str(result)[:80]}")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            try:
                msg = await self.out_queue.get()
                if self.session:
                    await self.session.send_realtime_input(media=msg)
            except Exception as e:
                print(f"[qeltex] ⚠️ Error during realtime signal transmission: {e}")
                await asyncio.sleep(0.5)

    async def _listen_audio(self):
        print("[qeltex] 🎤 Initializing microphone signal...")
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                qeltex_speaking = self._is_speaking
            if not qeltex_speaking and not self.ui.muted:
                try:
                    data = indata.tobytes()
                    import time
                    self.last_interaction_time = time.time()
                    loop.call_soon_threadsafe(
                        self.out_queue.put_nowait,
                        {"data": data, "mime_type": "audio/pcm"}
                    )
                except Exception:
                    pass

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[qeltex] 🎤 Microphone signal operational and streaming.")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[qeltex] ⚠️ Running in text-only mode (No microphone detected): {e}")
            try:
                self.ui.write_log("SYS: ⌨️ Text-only mode active (No microphone detected).")
                self.ui.set_status_text("QELTEX Core: ⌨️ Text Mode")
            except Exception:
                pass
            return

    async def _receive_audio(self):
        print("[qeltex] 👂 Audio reception channel initialized.")
        out_buf, in_buf = [], []
        try:
            while True:
                session_active = False
                async for response in self.session.receive():
                    session_active = True
                    if not response:
                        continue
                        
                    if hasattr(response, 'thought') and response.thought:
                        continue

                    if response.data:
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        self.audio_in_queue.put_nowait(response.data)
                    if response.server_content:
                        sc = response.server_content
                        if sc.output_transcription and sc.output_transcription.text:
                            raw_txt = sc.output_transcription.text
                            if "thought" not in raw_txt.lower() and "i need to find" not in raw_txt.lower():
                                txt = _clean_transcript(raw_txt)
                                if txt: out_buf.append(txt)
                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt: in_buf.append(txt)
                        if sc.turn_complete:
                            if self._turn_done_event: self._turn_done_event.set()
                            
                            logged = False
                            try:
                                if hasattr(response, "usage_metadata") and response.usage_metadata and response.usage_metadata:
                                    meta = response.usage_metadata
                                    in_t = getattr(meta, "prompt_token_count", 0) or 0
                                    out_t = getattr(meta, "candidates_token_count", 0) or 0
                                    if in_t > 0 or out_t > 0:
                                        from actions.token_budget_shield import budget_shield_action
                                        budget_shield_action({"action": "log_tokens", "input_tokens": in_t, "output_tokens": out_t, "tokens_used": (in_t + out_t)}, player=self.ui)
                                        logged = True
                            except Exception as token_err:
                                print(f"[qeltex] Error logging tokens: {token_err}")

                            if not logged:
                                try:
                                    from actions.token_budget_shield import budget_shield_action
                                    budget_shield_action({"action": "log_action", "called_tool": "audio_stream_turn"}, player=self.ui)
                                except Exception:
                                    pass

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                try: self.ui.write_log(f"User: {full_in}")
                                except Exception: pass
                            in_buf = []
                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                try: self.ui.write_log(f"qeltex: {full_out}")
                                except Exception: pass
                            out_buf = []
                            self.ui.set_status_text("QELTEX Core: System Standby")
                            self.ui.set_progress_value(0)
                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[qeltex] 📞 Received tool call: {fc.name}")
                            
                            try:
                                from actions.token_budget_shield import budget_shield_action
                                budget_shield_action({"action": "log_action", "called_tool": str(fc.name)}, player=self.ui)
                            except Exception:
                                pass

                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        try:
                            retry_count = 0
                            while self.session is None and retry_count < 10:
                                await asyncio.sleep(0.5)
                                retry_count += 1
                            if self.session:
                                await self.session.send_tool_response(function_responses=fn_responses)
                            else:
                                print("[qeltex] Live session became unavailable during background operation execution.")
                        except Exception as e:
                            print(f"[qeltex] Could not transmit tool response matrix: {e}")
                await asyncio.sleep(0.05)
        except Exception as e:
            raise e

    async def _play_audio(self):
        print("[qeltex] 🔊 Initializing audio playback...")
        
        try:
            stream = sd.RawOutputStream(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
            )
            stream.start()
        except Exception as e:
            print(f"[qeltex] ❌ Could not start audio playback (audio device busy or missing): {e}")
            try: self.ui.write_log("SYS: Audio playback error — hardware device unavailable.")
            except Exception: pass
            while True:
                await asyncio.sleep(5)

        try:
            while True:
                if self.session is None:
                    await asyncio.sleep(0.5)
                    continue

                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                    continue
                if getattr(self.ui, "state", "") != "THINKING":
                    self.set_speaking(True)
                self.last_interaction_time = time.time()
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[qeltex] ❌ Playback stream interrupted: {e}")
        finally:
            self.set_speaking(False)
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    async def _monitor_keepalive(self):
        while True:
            await asyncio.sleep(10)
            if self._tool_running:
                self.last_interaction_time = time.time()
                continue

    async def run(self):
        while True:
            try:
                print("[qeltex] 🔌 Connecting to Live Stream API...")
                self.ui.set_state("THINKING")
                self.last_interaction_time = time.time()
                try:
                    api_key = _get_api_key()
                except Exception as e:
                    print(f"[qeltex] ❌ Error retrieving API key: {e}")
                    try:
                        self.ui.write_log("SYS: Gemini API key is missing or invalid.")
                    except Exception:
                        pass
                    await asyncio.sleep(5)
                    continue

                config = self._build_config()
                if hasattr(config, "safety_settings"):
                    del config.safety_settings

                client = genai.Client(
                    api_key=api_key,
                    http_options={"api_version": "v1beta"}
                )

                async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
                    self.session = session
                    try:
                        self._loop = asyncio.get_running_loop()
                    except RuntimeError:
                        self._loop = asyncio.get_event_loop()
                        
                    if self.audio_in_queue:
                        while not self.audio_in_queue.empty():
                            try:
                                self.audio_in_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                            
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)
                    self._turn_done_event = asyncio.Event()
                    print("[qeltex] ✅ Connection established.")
                    self.ui.set_state("LISTENING")
                    try:
                        self.ui.write_log("SYS: Q.E.L.T.E.X online.")
                    except Exception:
                        pass
                    
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(self._send_realtime())
                        tg.create_task(self._listen_audio())
                        tg.create_task(self._receive_audio())
                        tg.create_task(self._play_audio())
                        tg.create_task(self._monitor_keepalive())
            except Exception as e:
                print(f"[qeltex] 🔌 Session closed or timeout encountered: {e}")
            
            self.session = None
            self.set_speaking(False)
            try:
                self.ui.set_state("THINKING")
            except Exception:
                pass
            print("[qeltex] 🔄 Reconnecting in 3 seconds...")
            await asyncio.sleep(3)

def mousePressEvent(self, event):
        if hasattr(self.ui, "effect") and self.ui.effect:
            if hasattr(self.ui.effect, "mousePressEvent"):
                try:
                    self.ui.effect.mousePressEvent(event)
                except Exception:
                    pass

def main():
    try:
        ui = qeltexUI("BASIC")
    except Exception as e:
        print(f"[qeltex] ❌ Critical failure initializing main user interface layout context: {e}")
        return

    import qeltex_ui

    qeltex_ui.MainWindow._stealth_active = False
    _orig_resize = qeltex_ui.MainWindow.resizeEvent

    def _custom_resize(self, event):
        if getattr(self, '_stealth_active', False):
            super(qeltex_ui.MainWindow, self).resizeEvent(event)
            W = self._central.width()
            H = self._central.height()
            if W <= 0 or H <= 0:
                return
            self._right_panel.setGeometry(-1000, -1000, 0, 0)
            self.header_widget.setGeometry(-1000, -1000, 0, 0)
            self.footer_widget.setGeometry(-1000, -1000, 0, 0)
            self._control_bar_layout.setGeometry(-1000, -1000, 0, 0)
            self._left_panel.setGeometry(-1000, -1000, 0, 0)
            
            if hasattr(self, "_center_metrics_widget") and self._center_metrics_widget:
                self._center_metrics_widget.setGeometry(-1000, -1000, 0, 0)
                
            if hasattr(self, "_button_grid_widget") and self._button_grid_widget:
                self._button_grid_widget.setGeometry(-1000, -1000, 0, 0)
            hud_sz = min(720, int(H * 0.85))
            self.hud.setGeometry((W - hud_sz) // 2, (H - hud_sz) // 2, hud_sz, hud_sz)
            if hasattr(self, '_stealth_menu'):
                self._stealth_menu.setParent(self._central)
                self._stealth_menu.setGeometry(30, H - 75, 250, 45)
                self._stealth_menu.show()
        else:
            _orig_resize(self, event)

    qeltex_ui.MainWindow.resizeEvent = _custom_resize

    def _stealth(self):
        if hasattr(self, '_win'):
            self._win._stealth_active = True
            self._win.resizeEvent(None)
        print("Success: Stealth mode active")

    def _tactical(self):
        if hasattr(self, '_win'):
            self._win._stealth_active = False
            if hasattr(self._win, '_stealth_menu') and hasattr(self._win, '_left_panel'):
                self._win._stealth_menu.setParent(self._win._left_panel)
            self._win.resizeEvent(None)
        print("Success: Tactical HUD active")

    qeltex_ui.qeltexUI.activate_stealth_mode = _stealth
    qeltex_ui.qeltexUI.activate_tactical_mode = _tactical

    def _lock(self):
        if hasattr(self, '_win') and hasattr(self._win, 'activate_pin_lock'):
            self._win.activate_pin_lock()
        print("Success: Lock mode active")
    
    qeltex_ui.qeltexUI.activate_pin_lock = _lock
    
    if hasattr(ui, '_win'):
        ui._win.activate_stealth_mode = lambda: _stealth(ui)
        ui._win.activate_tactical_mode = lambda: _tactical(ui)

    def runner():
        try:
            ui.wait_for_api_key()
            qeltex = qeltexLive(ui)
            
            try:
                from actions.token_budget_shield import BUDGET_FILE, oppdater_token_vindu_ui
                if BUDGET_FILE.exists():
                    import json
                    c_data = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
                    oppdater_token_vindu_ui(ui, c_data.get("saldo_nok", 500.00), c_data.get("brukt_nok", 0.00))
            except Exception as init_token_err:
                print(f"[qeltex] Error reading initial budget matrix: {init_token_err}")

            asyncio.run(qeltex.run())
        except KeyboardInterrupt:
            print("\n🔴 Thundershield protocol interrupted by operator. System halting.")
        except Exception as e:
            print(f"[qeltex] ❌ Critical system error in background operator: {e}")
            traceback.print_exc()

    try:
        threading.Thread(target=runner, daemon=True).start()
        ui.root.mainloop()
    except Exception as e:
        print(f"[qeltex] ❌ Fatal error in main interface loop (mainloop): {e}")

if __name__ == "__main__":
    main()