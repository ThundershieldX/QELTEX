from __future__ import annotations
import os
import sys
import json
import time
import platform
import subprocess
import threading
from pathlib import Path

import psutil
import webview


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR    = _base_dir()
_BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
CONFIG_DIR  = BASE_DIR / "config"
API_FILE    = CONFIG_DIR / "api_keys.json"
HTML_FILE   = (
    (_BUNDLE_DIR / "qeltex_index.html")
    if (_BUNDLE_DIR / "qeltex_index.html").exists()
    else (BASE_DIR / "qeltex_index.html")
)
_OS = platform.system()

_MAIN_WIN: MainWindow | None = None
_WV_WINDOW = None


class _SysMetrics:
    def __init__(self):
        self.cpu = 0.0
        self.mem = 0.0
        self.net = 0.0
        self.gpu = -1.0
        self.r_io = 0.0
        self.w_io = 0.0
        self._lock = threading.Lock()
        try:
            self._last_net = psutil.net_io_counters()
        except Exception:
            self._last_net = None
        try:
            io = psutil.disk_io_counters()
            self._last_r = io.read_bytes if io else 0
            self._last_w = io.write_bytes if io else 0
        except Exception:
            self._last_r = 0
            self._last_w = 0
        self._last_t = time.time()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
                now = time.time()
                dt = max(0.1, now - self._last_t)
                nc = psutil.net_io_counters()
                if self._last_net and nc:
                    net = (
                        (nc.bytes_sent - self._last_net.bytes_sent)
                        + (nc.bytes_recv - self._last_net.bytes_recv)
                    ) / dt / (1024 * 1024)
                else:
                    net = 0.0
                self._last_net = nc

                io = psutil.disk_io_counters()
                if io:
                    r_io = max(0.0, (io.read_bytes - self._last_r) / dt / (1024 * 1024))
                    w_io = max(0.0, (io.write_bytes - self._last_w) / dt / (1024 * 1024))
                    self._last_r = io.read_bytes
                    self._last_w = io.write_bytes
                else:
                    r_io, w_io = 0.0, 0.0

                self._last_t = now
                gpu = self._get_gpu()

                with self._lock:
                    self.cpu, self.mem, self.net, self.gpu = cpu, mem, net, gpu
                    self.r_io, self.w_io = r_io, w_io
            except Exception:
                pass
            time.sleep(1.5)

    def _get_gpu(self) -> float:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=1.5,
                creationflags=subprocess.CREATE_NO_WINDOW if _OS == "Windows" else 0,
            )
            if r.returncode == 0 and r.stdout.strip():
                vals = [float(x.strip()) for x in r.stdout.strip().splitlines() if x.strip()]
                if vals:
                    return sum(vals) / len(vals)
        except Exception:
            pass
        return -1.0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu": round(self.cpu, 1),
                "mem": round(self.mem, 1),
                "net": round(self.net, 2),
                "gpu": round(self.gpu, 1),
                "r_io": round(self.r_io, 2),
                "w_io": round(self.w_io, 2),
                "procs": len(psutil.pids()),
                "uptime": int(time.time() - psutil.boot_time()),
            }


_metrics = _SysMetrics()


class JsApi:
    """Eksponert til JavaScript som window.pywebview.api"""

    def get_initial_state(self):
        return _MAIN_WIN.get_full_state() if _MAIN_WIN else {}

    def get_metrics(self):
        return _metrics.snapshot()

    def send_command(self, text: str):
        if _MAIN_WIN:
            _MAIN_WIN.handle_js_command(str(text))

    def toggle_mute(self):
        if _MAIN_WIN:
            _MAIN_WIN._toggle_mute()
            return _MAIN_WIN._muted
        return False

    def toggle_fullscreen(self):
        if _MAIN_WIN:
            _MAIN_WIN._toggle_fullscreen()

    def trigger_vision(self):
        if _MAIN_WIN:
            _MAIN_WIN._trigger_qeltex_vision()

    def trigger_weather(self):
        def _open_weather():
            try:
                from actions.weather_report import weather_report
                res = weather_report({"action": "play"})
                if _MAIN_WIN:
                    _MAIN_WIN.qeltex_terminal_stream.write_output(f"[WEATHER REPORT]\n{res}")
            except Exception as e:
                if _MAIN_WIN:
                    _MAIN_WIN._push_js("appendLog", f"ERR: Weather matrix failed: {e}")

        threading.Thread(target=_open_weather, daemon=True).start()

    def set_theme(self, theme_name: str):
        if _MAIN_WIN:
            _MAIN_WIN.apply_theme(str(theme_name))

    def set_hud(self, hud_name: str):
        if _MAIN_WIN:
            _MAIN_WIN.apply_hud(str(hud_name))

    def close_overlays(self):
        if _MAIN_WIN:
            _MAIN_WIN.close_active_overlays()

    def browse_file(self):
        if _MAIN_WIN:
            _MAIN_WIN._open_file_dialog()

    def clear_file(self):
        if _MAIN_WIN:
            _MAIN_WIN._current_file = None

    def set_stealth(self, active: bool):
        if _MAIN_WIN:
            if active:
                _MAIN_WIN.activate_stealth_mode()
            else:
                _MAIN_WIN.activate_tactical_mode()

    def activate_pin_lock(self):
        if _MAIN_WIN:
            _MAIN_WIN.activate_pin_lock()

    def verify_pin(self, pin_str: str) -> bool:
        return _MAIN_WIN.check_pin(str(pin_str)) if _MAIN_WIN else True

    def save_setup(self, api_key: str, os_name: str) -> bool:
        return _MAIN_WIN.save_initial_setup(str(api_key), str(os_name)) if _MAIN_WIN else False


class _BudgetLabelProxy:
    """Beholdt for kompatibilitet med actions/token_budget_shield.py"""

    def __init__(self, win_ref: MainWindow):
        self._win = win_ref
        self._txt = ""

    def setText(self, text: str):
        self._txt = str(text)
        self._win._push_js(
            "updateDeviceLabel",
            {"category": "budget", "key": "main", "text": self._txt},
        )

    def text(self) -> str:
        return self._txt


class _ToggleBtnProxy:
    def __init__(self, win_ref: MainWindow):
        self._win = win_ref

    def click(self):
        self._win._buttons_visible = not self._win._buttons_visible
        self._win._push_js("setControlCoreVisible", self._win._buttons_visible)

    def setText(self, _txt: str):
        pass


class _GridWidgetProxy:
    def __init__(self, win_ref: MainWindow):
        self._win = win_ref

    def show(self):
        self._win._buttons_visible = True
        self._win._push_js("setControlCoreVisible", True)

    def hide(self):
        self._win._buttons_visible = False
        self._win._push_js("setControlCoreVisible", False)

    def raise_(self):
        pass

    def isVisible(self) -> bool:
        return self._win._buttons_visible


class _HudStateProxy:
    def __init__(self):
        self.state = "LISTENING"
        self.muted = False
        self.speaking = False


class _TerminalProxy:
    def __init__(self, win_ref: MainWindow):
        self._win = win_ref
        self._lines: list[str] = []
        self._lock = threading.Lock()

    def write_output(self, text: str):
        cleaned = str(text or "").strip()
        if cleaned:
            with self._lock:
                self._lines.append(cleaned)
                if len(self._lines) > 250:
                    self._lines = self._lines[-250:]
            self._win._push_js("appendTerminal", cleaned)

    def toPlainText(self) -> str:
        with self._lock:
            return "\n".join(self._lines)

    def clear(self):
        with self._lock:
            self._lines.clear()
        self._win._push_js("clearTerminal", None)


class _SignalBridge:
    """Enkel emit-bro for actions/-moduler som kaller .emit()"""

    def __init__(self, callback):
        self._cb = callback

    def emit(self, *args):
        self._cb(*args)


class MainWindow:
    def __init__(self):
        global _MAIN_WIN
        _MAIN_WIN = self

        self.on_text_command = None
        self._muted = False
        self._current_file: str | None = None
        self._buttons_visible = False
        self._stealth_active = False
        self.hud = _HudStateProxy()

        self._js_ready = False
        self._pending_js: list[str] = []
        self._js_lock = threading.Lock()

        self.active_theme = "green"
        self.active_hud = "classic"
        try:
            if API_FILE.exists():
                cfg = json.loads(API_FILE.read_text(encoding="utf-8"))
                self.active_theme = cfg.get("qeltex_theme", "green")
                self.active_hud = cfg.get("qeltex_hud", "classic")
        except Exception:
            pass

        self._toggle_trigger_btn = _ToggleBtnProxy(self)
        self._button_grid_widget = _GridWidgetProxy(self)
        self.qeltex_terminal_stream = _TerminalProxy(self)
        self.qeltex_budget_box = _BudgetLabelProxy(self)

        # Beholdt slik at eksterne actions/-moduler som kaller _hud_sig / _theme_sig / _log_sig fungerer
        self._log_sig = _SignalBridge(lambda t: self._push_js("appendLog", str(t)))
        self._hud_sig = _SignalBridge(self.apply_hud)
        self._theme_sig = _SignalBridge(self.apply_theme)

        self._ready = self._check_config()

    def _push_js(self, fn_name: str, payload):
        js_code = (
            f"if(window.qeltexBridge && window.qeltexBridge.{fn_name})"
            f"{{window.qeltexBridge.{fn_name}({json.dumps(payload)});}}"
        )
        with self._js_lock:
            if not self._js_ready or _WV_WINDOW is None:
                self._pending_js.append(js_code)
                return
        try:
            _WV_WINDOW.evaluate_js(js_code)
        except Exception:
            pass

    def _flush_pending_js(self):
        with self._js_lock:
            self._js_ready = True
            if _WV_WINDOW is None:
                return
            pending = list(self._pending_js)
            self._pending_js.clear()
        for code in pending:
            try:
                _WV_WINDOW.evaluate_js(code)
            except Exception:
                pass

    def get_full_state(self) -> dict:
        threading.Thread(
            target=lambda: (time.sleep(0.1), self._flush_pending_js()),
            daemon=True,
        ).start()

        def _read_json(name: str, default: dict) -> dict:
            p = CONFIG_DIR / name
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    pass
            return default

        budget_data = _read_json("token_budget.json", {})
        saldo_nok = budget_data.get("saldo_nok")
        brukt_nok = budget_data.get("brukt_nok")
        if saldo_nok is not None and brukt_nok is not None:
            budget_text = f"SALDO: {float(saldo_nok):.2f} NOK  /  BRUKT: {float(brukt_nok):.2f} NOK"
        else:
            budget_text = "BUDGET REMAINING: $5.0 / $5.0"

        api_data = _read_json("api_keys.json", {})
        has_pin = bool(str(api_data.get("qeltex_PIN", "")).strip())
        os_label = {"Windows": "WIN", "Darwin": "macOS"}.get(_OS, _OS.upper())

        return {
            "theme": self.active_theme,
            "hud": self.active_hud,
            "muted": self._muted,
            "state": self.hud.state,
            "os": os_label,
            "ready": self._ready,
            "pin_required": has_pin,
            "budget": budget_text,
            "metrics": _metrics.snapshot(),
        }

    def _apply_state(self, state: str):
        self.hud.state = str(state)
        self.hud.speaking = str(state) == "SPEAKING"
        self._push_js("setAiState", str(state))

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        st = "MUTED" if self._muted else "LISTENING"
        self._apply_state(st)
        self._push_js("setMuted", self._muted)
        self._push_js(
            "appendLog",
            "SYS: Microphone deactivated." if self._muted else "SYS: Microphone activated.",
        )

    def _toggle_fullscreen(self):
        try:
            if _WV_WINDOW:
                _WV_WINDOW.toggle_fullscreen()
        except Exception:
            pass

    def apply_theme(self, theme_name: str):
        t = theme_name.lower().strip()
        if t in ("green", "blue", "red", "yellow", "purple", "cyan"):
            self.active_theme = t
            self._push_js("setTheme", t)
            try:
                cfg = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
                cfg["qeltex_theme"] = t
                API_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
            except Exception:
                pass

    def apply_hud(self, hud_name: str):
        h = hud_name.lower().strip()
        self.active_hud = h
        self._push_js("setHudStyle", h)
        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
            cfg["qeltex_hud"] = h
            API_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        except Exception:
            pass

    def handle_js_command(self, txt: str):
        cleaned = txt.strip()
        if not cleaned:
            return
        self._push_js("appendLog", f"User: {cleaned}")
        if cleaned.lower() == "pin lock":
            self.activate_pin_lock()
            return
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(cleaned,), daemon=True).start()

    def _trigger_qeltex_vision(self):
        if self.on_text_command:
            self.set_error_text("SYS: Initiating hardware frame capture...")
            msg = (
                "[SCREEN_PROCESS] angle=screen | "
                "text=Analyze the current active window layout and report status parameters in Norwegian."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def close_active_overlays(self):
        self._push_js("closeDropdowns", None)

    def _open_file_dialog(self):
        if _WV_WINDOW is None:
            return
        try:
            res = _WV_WINDOW.create_file_dialog(webview.OPEN_DIALOG)
            if res and len(res) > 0 and Path(res).exists():
                path = str(res)
                self._current_file = path
                p = Path(path)
                sz = p.stat().st_size
                size_str = f"{sz / 1024:.1f} KB" if sz < 1024**2 else f"{sz / 1024**2:.1f} MB"
                self._push_js(
                    "setFileLoaded",
                    {
                        "name": p.name,
                        "size": size_str,
                        "ext": p.suffix.upper().lstrip(".") or "FILE",
                    },
                )
                self._push_js("appendLog", f"FILE: {p.name} ({size_str}) successfully loaded")
                if self.on_text_command:
                    msg = (
                        f"[FILE_UPLOADED] path={path} | name={p.name} | "
                        f"type={p.suffix.lstrip('.')} | size={size_str} | "
                        f"Briefly tell the user you can see the file '{p.name}' "
                        f"({size_str}) has been uploaded and ask what they'd like to do with it."
                    )
                    threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()
        except Exception as e:
            self._push_js("appendLog", f"ERR: File dialog failed: {e}")

    def set_error_text(self, text: str):
        self._push_js("setErrorText", str(text or "").strip())

    def activate_stealth_mode(self):
        self._stealth_active = True
        self._push_js("setStealthMode", True)

    def activate_tactical_mode(self):
        self._stealth_active = False
        self._push_js("setStealthMode", False)

    def activate_pin_lock(self):
        self._push_js("showPinLock", {})

    def check_pin(self, pin_str: str) -> bool:
        try:
            if API_FILE.exists():
                d = json.loads(API_FILE.read_text(encoding="utf-8"))
                expected = str(d.get("qeltex_PIN", ""))
                if not expected or pin_str.strip() == expected:
                    self._push_js("appendLog", "SYSTEM INTERFACE UNLOCKED")
                    return True
                return False
        except Exception:
            pass
        return True

    def _check_config(self) -> bool:
        if not API_FILE.exists():
            return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key")) and bool(d.get("os_system"))
        except Exception:
            return False

    def save_initial_setup(self, key: str, os_name: str) -> bool:
        if not key.strip():
            return False
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            existing = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
            existing["gemini_api_key"] = key.strip()
            existing["os_system"] = os_name.strip()
            API_FILE.write_text(json.dumps(existing, indent=4), encoding="utf-8")
            self._ready = True
            self._apply_state("LISTENING")
            self._push_js(
                "appendLog",
                f"SYS: Initialization complete. OS={os_name.upper()}. Q.E.L.T.E.X online.",
            )
            return True
        except Exception:
            return False


class _RootShim:
    def mainloop(self):
        webview.start(debug=False)


class qeltexUI:
    def __init__(self, module_name=None, size=None):
        global _WV_WINDOW
        self._win = MainWindow()
        self._api = JsApi()

        title = (
            f"Q.E.L.T.E.X [{module_name}] — THUNDERSHIELD PROTOCOL"
            if module_name
            else "Q.E.L.T.E.X — THUNDERSHIELD PROTOCOL"
        )

        _WV_WINDOW = webview.create_window(
            title,
            url=HTML_FILE.as_uri(),
            js_api=self._api,
            width=1360,
            height=860,
            min_size=(1024, 700),
            background_color="#000301",
        )
        self.root = _RootShim()

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._current_file

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win._apply_state(state)

    def write_log(self, text: str):
        self._win._push_js("appendLog", str(text))

    def set_status_text(self, text: str):
        self._win._push_js("setStatusText", str(text))

    def set_progress_value(self, value: int):
        self._win._push_js("setProgressValue", int(value))

    def set_error_text(self, text: str):
        clean_text = str(text).strip()
        self._win.set_error_text(clean_text)
        if clean_text:
            self._win.qeltex_terminal_stream.write_output(clean_text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def activate_stealth_mode(self):
        self._win.activate_stealth_mode()

    def activate_tactical_mode(self):
        self._win.activate_tactical_mode()

    def activate_pin_lock(self):
        self._win.activate_pin_lock()
