import os
import sys
import json
import time
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
LOGS_DIR = BASE_DIR / "memory" / "logs"
BUDGET_FILE = BASE_DIR / "config" / "token_budget.json"

PRICE_INPUT_TOKEN_NOK = 0.80 / 1_000_000
PRICE_OUTPUT_TOKEN_NOK = 3.18 / 1_000_000
PRICE_AUDIO_TOKEN_NOK = 2.15 / 1_000_000

def update_token_window_ui(player, balance: float, spent: float):
    try:
        target_box = None
        if hasattr(player, "qeltex_budget_box"):
            target_box = player.qeltex_budget_box
        elif hasattr(player, "_win") and hasattr(player._win, "qeltex_budget_box"):
            target_box = player._win.qeltex_budget_box

        if target_box:
            new_text = f"BALANCE: {balance:.2f} NOK  /  SPENT: {spent:.2f} NOK"
            target_box.setText(new_text)
    except Exception as e:
        print(f"[BudgetShield UI] Error updating box: {e}")

def budget_shield_action(parameters: dict, player=None) -> str:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    params = parameters if isinstance(parameters, dict) else {}
    action = str(params.get("action", "check")).lower().strip()
    
    input_tokens = int(params.get("input_tokens", 0))
    output_tokens = int(params.get("output_tokens", 0))
    tokens_used = int(params.get("tokens_used", 0))
    
    if tokens_used > 0 and input_tokens == 0 and output_tokens == 0:
        input_tokens = int(tokens_used * 0.75)
        output_tokens = int(tokens_used * 0.25)
        
    max_usd_per_hour = float(params.get("max_usd_per_hour", 5.0))

    if not BUDGET_FILE.exists():
        default_config = {
            "max_usd_per_hour": max_usd_per_hour,
            "accumulated_cost_hour": 0.0,
            "last_reset_timestamp": time.time(),
            "balance_nok": 200.00,
            "spent_nok": 0.00
        }
        try:
            BUDGET_FILE.write_text(json.dumps(default_config, indent=4), encoding="utf-8")
        except Exception:
            pass

    try:
        config = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    except Exception:
        config = {
            "max_usd_per_hour": max_usd_per_hour, 
            "accumulated_cost_hour": 0.0, 
            "last_reset_timestamp": time.time(),
            "balance_nok": 200.00,
            "spent_nok": 0.00
        }

    if "balance_nok" not in config:
        config["balance_nok"] = config.pop("saldo_nok", 200.00)
    if "spent_nok" not in config:
        config["spent_nok"] = config.pop("brukt_nok", 0.00)

    current_time = time.time()
    if current_time - config.get("last_reset_timestamp", 0) > 3600:
        config["accumulated_cost_hour"] = 0.0
        config["last_reset_timestamp"] = current_time

    if action == "log_tokens" or action == "log_action":
        cost_nok = 0.0
        
        if input_tokens > 0 or output_tokens > 0:
            cost_nok = (input_tokens * PRICE_INPUT_TOKEN_NOK) + (output_tokens * PRICE_OUTPUT_TOKEN_NOK)
        else:
            called_tool = str(params.get("called_tool", "")).lower().strip()
            
            heavy_tools = [
                "screen_processor", "file_processor", "agent_task"
            ]
            medium_tools = [
                "web_search", "news_ticker", "weather_report", 
                "morning_digest", "browser_control", "system_monitor", "network_shield"
            ]
            
            if any(t in called_tool for t in heavy_tools):
                cost_nok = 0.35
            elif any(m in called_tool for m in medium_tools):
                cost_nok = 0.08
            elif called_tool:
                cost_nok = 0.02
            else:
                cost_nok = 0.05

        usd_rate = 10.60
        estimated_cost_usd = cost_nok / usd_rate
        config["accumulated_cost_hour"] = config.get("accumulated_cost_hour", 0.0) + estimated_cost_usd
        
        config["balance_nok"] = max(0.00, config["balance_nok"] - cost_nok)
        config["spent_nok"] += cost_nok
        
        try:
            BUDGET_FILE.write_text(json.dumps(config, indent=4), encoding="utf-8")
        except Exception:
            pass

        if player:
            update_token_window_ui(player, config["balance_nok"], config["spent_nok"])

        if config["accumulated_cost_hour"] >= config.get("max_usd_per_hour", 5.0):
            msg = f"CRITICAL: Token budget exceeded (${round(config['accumulated_cost_hour'], 4)}). Triggering system lockdown, sir."
            _log(msg, player)
            
            if player and hasattr(player, "set_state"):
                player.set_state("THINKING")
            if player and hasattr(player, "set_status_text"):
                player.set_status_text("BUDGET SHIELD: EXCEEDED")
                
            return "LOCKDOWN"
            
        return "OK"

    elif action == "set_budget":
        config["max_usd_per_hour"] = max_usd_per_hour
        try:
            BUDGET_FILE.write_text(json.dumps(config, indent=4), encoding="utf-8")
            msg = f"Hourly API consumption ceiling updated to ${max_usd_per_hour} per hour, sir."
        except Exception as e:
            msg = f"Failed to commit budget adjustments to file matrix: {e}"
        _log(msg, player)
        return msg

    else:
        current_hourly_cost = config.get("accumulated_cost_hour", 0.0)
        allowed_ceiling = config.get("max_usd_per_hour", 5.0)
        remaining = max(0.0, allowed_ceiling - current_hourly_cost)
        
        if player:
            update_token_window_ui(player, config["balance_nok"], config["spent_nok"])
            
        msg = f"Budget Status: Active | Hourly Cost: ${round(current_hourly_cost, 4)} / ${allowed_ceiling} | Remaining: ${round(remaining, 4)} | Balance: {config['balance_nok']:.2f} NOK, sir."
        _log(msg, player)
        return msg

def _log(message: str, player=None) -> None:
    print(f"[BudgetShield] {message}")
    if player and hasattr(player, "write_log"):
        try:
            player.write_log(f"qeltex: {message}")
        except Exception:
            pass