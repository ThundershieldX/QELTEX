import json
import re
import sys
from pathlib import Path
from enum import Enum

try:
    from google import genai
    from google.genai import types as gtypes
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

class ErrorDecision(Enum):
    RETRY       = "retry"      
    SKIP        = "skip"       
    REPLAN      = "replan"     
    ABORT       = "abort"    

ERROR_ANALYST_PROMPT = """You are the error recovery module of Q.E.L.T.E.X AI assistant.
A task step has failed. Analyze the error and decide what to do.
DECISIONS:
- retry   : Transient error (network timeout, temporary file lock, race condition).
- skip    : This step is not critical and the task can succeed without it.
- replan  : The approach was wrong. A different tool or method should be tried.
- abort   : The task is fundamentally impossible or unsafe to continue.
Return ONLY valid JSON:
{
  "decision": "retry|skip|replan|abort",
  "reason": "why it failed",
  "fix_suggestion": "what to try instead",
  "max_retries": 1,
  "user_message": "Short message to tell the user"
}"""

def _get_api_key() -> str:
    if not API_CONFIG_PATH.exists():
        print(f"[ErrorHandler] Error: Configuration file not found: {API_CONFIG_PATH}")
        return ""
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "")
    except Exception:
        return ""

def analyze_error(step: dict, error: str, attempt: int = 1, max_attempts: int = 2, player = None) -> dict:
    if player and hasattr(player, "set_error_text"):
        try:
            tool_name = str(step.get("tool", "UNKNOWN")).upper()
            player.set_error_text(f"SYSTEM FAULT DETECTED IN: {tool_name}\nERROR TRACKING TRACE:\n{error[:400]}")
        except Exception: pass
    if not HAS_GEMINI:
        print("[ErrorHandler] Missing installation: 'google-genai' is absent.")
        return {"decision": ErrorDecision.REPLAN, "reason": "google-genai missing", "fix_suggestion": "Install packages", "max_retries": 0, "user_message": "Missing libraries."}
    if attempt >= max_attempts:
        print(f"[ErrorHandler] Max attempts reached for step {step.get('step')} — forcing replan")
        return {"decision": ErrorDecision.REPLAN, "reason": f"Failed {attempt} times", "fix_suggestion": "Try a different approach", "max_retries": 0, "user_message": "Trying a different approach."}
    api_key = _get_api_key()
    if not api_key:
        return {"decision": ErrorDecision.ABORT, "reason": "Missing key", "fix_suggestion": "Add key", "max_retries": 0, "user_message": "API key missing."}
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"Failed step:\nTool: {step.get('tool')}\nDescription: {step.get('description')}\nParameters: {json.dumps(step.get('parameters', {}))}\nError:\n{error[:500]}\nAttempt number: {attempt}"
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt, config=gtypes.GenerateContentConfig(system_instruction=ERROR_ANALYST_PROMPT, response_mime_type="application/json"))
        text = response.text.strip() if response.text else "{}"
        match = re.search(r"\{.*\}", text, re.DOTALL)
        text = match.group(0) if match else re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        result = json.loads(text)
        decision_map = {"retry": ErrorDecision.RETRY, "skip": ErrorDecision.SKIP, "replan": ErrorDecision.REPLAN, "abort": ErrorDecision.ABORT}
        result["decision"] = decision_map.get(result.get("decision", "replan").lower(), ErrorDecision.REPLAN)
        if step.get("critical") and result["decision"] == ErrorDecision.SKIP:
            result["decision"]     = ErrorDecision.REPLAN
            result["user_message"] = "This step is critical — finding alternative approach, sir."
        print(f"[ErrorHandler] Decision: {result['decision'].value} — {result.get('reason', '')}")
        return result
    except Exception as e:
        print(f"[ErrorHandler] Analysis failed: {e} — defaulting to replan")
        if player and hasattr(player, "set_error_text"):
            try: player.set_error_text(f"ANALYST ENGINE FAILURE:\n{e}")
            except Exception: pass
        return {"decision": ErrorDecision.REPLAN, "reason": str(e), "fix_suggestion": "Try alternative approach", "max_retries": 1, "user_message": "Encountered an issue."}

def generate_fix(step: dict, error: str, fix_suggestion: str) -> dict:
    if not HAS_GEMINI or not _get_api_key():
        print("[ErrorHandler] Missing installation or key.")
        return {"step": step.get("step"), "tool": "generated_code", "description": f"Fallback for: {step.get('description')}", "parameters": {"description": step.get("description", "")}, "depends_on": step.get("depends_on", []), "critical": step.get("critical", False)}
    try:
        client = genai.Client(api_key=_get_api_key())
        prompt = f"A task step failed.\nOriginal tool: {step.get('tool')}\nError: {error[:300]}\nFix suggestion: {fix_suggestion}\nGenerate a script to fix this."
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        code = response.text.strip() if response.text else ""
        code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()
        return {"step": step.get("step"), "tool": "generated_code", "description": f"Auto-fix for: {step.get('description')}", "parameters": {"description": fix_suggestion, "code": code}, "depends_on": step.get("depends_on", []), "critical": step.get("critical", False)}
    except Exception as e:
        print(f"[ErrorHandler] Fix generation matrix failed in transient runtime: {e}")
        return {"step": step.get("step"), "tool": "generated_code", "description": f"Fallback for: {step.get('description')}", "parameters": {"description": step.get("description", "")}, "depends_on": step.get("depends_on", []), "critical": step.get("critical", False)}