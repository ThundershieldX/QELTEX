import json
import re
import sys
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    if not API_CONFIG_PATH.exists():
        print(f"[Planner] Configuration file missing: {API_CONFIG_PATH}")
        return ""
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "")
    except Exception as e:
        print(f"[Planner] Error reading api_keys.json: {e}")
        return ""

PLANNER_PROMPT = """You are the planning module of Q.E.L.T.E.X, a personal AI assistant.
Your job: break any user goal into a sequence of steps using ONLY the tools listed below.

ABSOLUTE RULES:
- NEVER use generated_code or write Python scripts. It does not exist.
- NEVER reference previous step results in parameters. Every step is independent.
- Use web_search for ANY information retrieval, research, or current data.
- Use file_controller to save content to disk.
- Max 5 steps. Use the minimum steps needed.

AVAILABLE TOOLS AND THEIR PARAMETERS:

open_app
  app_name: string (required)

web_search
  query: string (required)
  mode: "search" or "compare" (optional, default: search)
  items: list of strings (optional, for compare mode)
  aspect: string (optional, for compare mode)

browser_control
  action: "go_to" | "search" | "click" | "type" | "scroll" | "get_text" | "press" | "close" (required)
  url: string (for go_to)
  query: string (for search)
  text: string (for click/type)
  direction: "up" | "down" (for scroll)

file_controller
  action: "write" | "create_file" | "read" | "list" | "delete" | "move" | "copy" | "find" | "disk_usage" (required)
  path: string
  name: string
  content: string

file_processor
  action: "summarize" | "extract_text" | "analyze" (required)
  file_path: string (required)

computer_settings
  action: string (required)
  description: string
  value: string (optional)

computer_control
  action: "type" | "click" | "hotkey" | "press" | "scroll" | "screenshot" | "screen_find" | "screen_click" (required)
  text: string (for type)
  x, y: int (for click)
  keys: string (for hotkey, e.g. "ctrl+c")
  key: string (for press)
  direction: "up" | "down" (for scroll)
  description: string (for screen_find/screen_click)

screen_process
  text: string (required)
  angle: "screen" | "camera" (optional)

send_message
  receiver: string (required)
  message_text: string (required)
  platform: string (required)

reminder
  date: string YYYY-MM-DD (required)
  time: string HH:MM (required)
  message: string (required)

desktop_control
  action: "wallpaper" | "organize" | "clean" | "list" | "task" (required)
  path: string (optional)
  task: string (optional)

weather_report
  city: string (required)

morning_digest
  city: string (optional)

news_ticker
  action: "play" | "stop" (optional)

execute_radio_action
  action: "play" | "stop" (required)
  station: string (optional)

system_monitor
  action: "play" | "stop" (optional)

network_shield
  action: "scan" (optional)

EXAMPLES:

Goal: "research mechanical engineering and save it to a notepad file"
Steps:

web_search | query: "mechanical engineering overview definition history"
web_search | query: "mechanical engineering applications and future trends"
file_controller | action: write, path: desktop, name: mechanical_engineering.txt, content: "MECHANICAL ENGINEERING RESEARCH\\n\\nThis file will be filled with web research results."

Goal: "What is the price of Bitcoin"
Steps:

web_search | query: "Bitcoin price today USD"

Goal: "List the files on the desktop and find the largest 5 files"
Steps:

file_controller | action: list, path: desktop
file_controller | action: largest, path: desktop, count: 5

Goal: "Send John a message on WhatsApp saying there is a meeting tomorrow"
Steps:

send_message | receiver: John, message_text: "There is a meeting tomorrow", platform: WhatsApp

Goal: "Open the clock and set a reminder for 30 minutes later"
Steps:

reminder | date: [today], time: [now+30min], message: "Reminder"

OUTPUT — return ONLY valid JSON, no markdown, no explanation, no code blocks:
{
  "goal": "...",
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "description": "what this step does",
      "parameters": {},
      "critical": true
    }
  ]
}
"""


def create_plan(goal: str, context: str = "") -> dict:
    try:
        from google import genai
        from google.genai import types as gtypes
    except ImportError:
        print("\n❌ [Planner] Missing installation: 'google-genai' is absent.")
        print("👉 Please execute command: pip install google-genai")
        return _fallback_plan(goal)
    api_key = _get_api_key()
    if not api_key:
        print("[Planner] ❌ API key missing. Aborting plan creation.")
        return _fallback_plan(goal)
    try:
        client = genai.Client(api_key=api_key)
        user_input = f"Goal: {goal}"
        if context:
            user_input += f"\n\nContext: {context}"
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=user_input,
            config=gtypes.GenerateContentConfig(system_instruction=PLANNER_PROMPT, response_mime_type="application/json")
        )
        text = response.text.strip() if response.text else "{}"
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        else:
            text = re.sub(r"```Header(?:json)?", "", text).strip().rstrip("`").strip()
        plan = json.loads(text)
        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Invalid plan structure")
        for step in plan["steps"]:
            if isinstance(step, dict) and step.get("tool") in ("generated_code",):
                print(f"[Planner] ⚠️ generated_code detected in step {step.get('step')} — replacing with web_search")
                desc = step.get("description", goal)
                step["tool"] = "web_search"
                step["parameters"] = {"query": str(desc)[:200]}
        print(f"[Planner] ✅ Plan generated: {len(plan['steps'])} steps")
        for s in plan["steps"]:
            if isinstance(s, dict):
                print(f"  Step {s.get('step', '?')}: [{s.get('tool', '?')}] {s.get('description', '')}")
        return plan
    except json.JSONDecodeError as e:
        print(f"[Planner] ⚠️ JSON parse failed: {e}")
        return _fallback_plan(goal)
    except Exception as e:
        print(f"[Planner] ⚠️ Planning operation failed: {e}")
        return _fallback_plan(goal)

def _fallback_plan(goal: str) -> dict:
    print("[Planner] 🔄 Executing fallback plan matrix")
    return {
        "goal": goal,
        "steps": [
            {
                "step": 1,
                "tool": "web_search",
                "description": f"Search for: {goal}",
                "parameters": {"query": goal},
                "critical": True
            }
        ]
    }

def replan(goal: str, completed_steps: list, failed_step: dict, error: str) -> dict:
    try:
        from google import genai
        from google.genai import types as gtypes
    except ImportError:
        print("\n❌ [Planner] Missing google-genai installation during replan.")
        return _fallback_plan(goal)
    api_key = _get_api_key()
    if not api_key:
        return _fallback_plan(goal)
    try:
        client = genai.Client(api_key=api_key)
        completed_summary = "\n".join(
            f"  - Step {s['step']} ({s['tool']}): DONE" for s in completed_steps if isinstance(s, dict) and "step" in s and "tool" in s
        )
        failed_tool = failed_step.get("tool", "unknown") if isinstance(failed_step, dict) else "unknown"
        failed_desc = failed_step.get("description", "") if isinstance(failed_step, dict) else ""
        prompt = (
            f"Goal: {goal}\n"
            f"Already completed:\n{completed_summary if completed_summary else '  (none)'}\n\n"
            f"Failed step: [{failed_tool}] {failed_desc}\n"
            f"Error: {error}\n\n"
            f"Create a REVISED plan for the remaining work only. Do not repeat completed steps."
        )
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=gtypes.GenerateContentConfig(system_instruction=PLANNER_PROMPT, response_mime_type="application/json")
        )
        text = response.text.strip() if response.text else "{}"
        match = re.search(r"\{.*\}", text, re.DOTALL)
        text = match.group(0) if match else re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        plan = json.loads(text)
        if not isinstance(plan, dict) or "steps" not in plan:
            return _fallback_plan(goal)
        for step in plan.get("steps", []):
            if isinstance(step, dict) and step.get("tool") == "generated_code":
                step["tool"] = "web_search"
                step["parameters"] = {"query": str(step.get("description", goal))[:200]}
        print(f"[Planner] 🔄 Revised plan loaded into core matrix: {len(plan.get('steps', []))} steps")
        return plan
    except Exception as e:
        print(f"[Planner] ⚠️ Replan operation failed in runtime environment: {e}")
        return _fallback_plan(goal)