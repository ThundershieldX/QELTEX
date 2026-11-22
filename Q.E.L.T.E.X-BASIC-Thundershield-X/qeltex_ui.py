from __future__ import annotations
import os
import sys
import json
import math
import time
import random
import platform
import subprocess
import threading
import importlib.util
from pathlib import Path

import psutil
import webview
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtGui import QFont, QPainter
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QDialog, QVBoxLayout, QFileDialog
)
from PyQt6.QtWebEngineWidgets import QWebEngineView


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR    = _base_dir()
_BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
CONFIG_DIR  = BASE_DIR / "config"
API_FILE    = CONFIG_DIR / "api_keys.json"
HTML_FILE   = (_BUNDLE_DIR / "qeltex_index.html") if (_BUNDLE_DIR / "qeltex_index.html").exists() else (BASE_DIR / "qeltex_index.html")
_OS         = platform.system()

EFFECTS = {}

_MAIN_WIN = None
_WV_WINDOW = None


class _SysMetrics:
    def __init__(self):
        self.cpu = 0.0
        self.mem = 0.0
        self.net = 0.0
        self.gpu = -1.0
        self.r_io = 0.0
        self.w_io = 0.0
        self.adb_status = "OFF"
        self.adb_device = ""
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
                    net = ((nc.bytes_sent - self._last_net.bytes_sent) +
                           (nc.bytes_recv - self._last_net.bytes_recv)) / dt / (1024 * 1024)
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
                capture_output=True, text=True, timeout=1.5,
                creationflags=subprocess.CREATE_NO_WINDOW if _OS == "Windows" else 0
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
                "adb_status": "OFF",
                "adb_device": ""
            }


_metrics = _SysMetrics()


class VisualOverlayWindow(QWidget):
    def __init__(self, mode="matrix", is_game=False):
        super().__init__()
        self.mode = mode.lower().strip()
        self.is_game = is_game
        self._tick = 0
        self.effect = EFFECTS.get(self.mode)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint
        )
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")

        self.esc_btn = QPushButton("ESC", self)
        self.esc_btn.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.esc_btn.setFixedSize(54, 30)
        self.esc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.esc_btn.setStyleSheet(
            "QPushButton { background-color: #051505; color: #00ff55; border: 1px solid #00ff55; }"
            "QPushButton:hover { background-color: #00ff55; color: black; }"
        )
        self.esc_btn.clicked.connect(self.close)
        self.esc_btn.show()

        if self.effect:
            self.effect.init_effect(self.width(), self.height())

        QTimer.singleShot(50, self._layout_esc)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(16)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def _layout_esc(self):
        if hasattr(self, "esc_btn"):
            self.esc_btn.move(self.width() - 70, self.height() - 46)
            self.esc_btn.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_esc()
        if self.effect:
            self.effect.init_effect(self.width(), self.height())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def _update_frame(self):
        self._tick += 1
        if self.effect:
            self.effect.update_effect(self.width(), self.height(), self._tick)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.effect:
            self.effect.paint_effect(p, self.width(), self.height())
        if hasattr(self, "esc_btn"):
            self.esc_btn.raise_()


class JsApi:
    def get_initial_state(self):
        if _MAIN_WIN:
            return _MAIN_WIN.get_full_state()
        return {}

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
                    _MAIN_WIN._log_sig.emit(f"ERR: Weather matrix failed: {e}")
        threading.Thread(target=_open_weather, daemon=True).start()

    def set_theme(self, theme_name: str):
        if _MAIN_WIN:
            _MAIN_WIN.apply_theme(str(theme_name))

    def set_hud(self, hud_name: str):
        if _MAIN_WIN:
            _MAIN_WIN.apply_hud(str(hud_name))

    def launch_visual(self, mode: str):
        pass

    def launch_game(self, game_key: str):
        pass

    def close_overlays(self):
        if _MAIN_WIN:
            _MAIN_WIN.close_active_overlays()

    def camera_action(self, cam_target: str):
        pass

    def gate_action(self, action: str, gate_num: str = ""):
        pass

    def eaton_action(self, action: str, device_id: str = "", state: bool = False):
        pass

    def shc_action(self, action: str, device_id: str = "", state=None, value=None):
        pass

    def plug_action(self, device_id: str, zone: str, state: bool):
        pass

    def hp_action(self, action: str, params: dict = None):
        pass

    def refresh_submenu(self, menu_type: str):
        pass

    def browse_file(self):
        if _MAIN_WIN:
            threading.Thread(target=_MAIN_WIN._open_file_dialog, daemon=True).start()

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
        if _MAIN_WIN:
            return _MAIN_WIN.check_pin(str(pin_str))
        return True

    def save_setup(self, api_key: str, os_name: str) -> bool:
        if _MAIN_WIN:
            return _MAIN_WIN.save_initial_setup(str(api_key), str(os_name))
        return False

class _LabelProxy(QObject):
    """Ekte QObject med @pyqtSlot(str) slik at både .setText() og QMetaObject.invokeMethod() fungerer."""
    def __init__(self, category: str, key: str, win_ref):
        super().__init__()
        self._cat = category
        self._key = key
        self._win = win_ref
        self._txt = ""

    @pyqtSlot(str)
    def setText(self, text: str):
        self._txt = str(text)
        self._win._push_js("updateDeviceLabel", {
            "category": self._cat,
            "key": self._key,
            "text": self._txt
        })

    def text(self) -> str:
        return self._txt

    def setStyleSheet(self, _style: str):
        pass


class _SliderProxy(QObject):
    """Ekte QObject med @pyqtSlot(int) for sanntids synkronisering av SHC-dimmere."""
    def __init__(self, key: str, win_ref):
        super().__init__()
        self._key = key
        self._win = win_ref
        self._val = 0

    def blockSignals(self, _b: bool):
        pass

    @pyqtSlot(int)
    def setValue(self, val: int):
        self._val = int(val)
        self._win._push_js("updateShcSlider", {"key": self._key, "value": self._val})

    def value(self) -> int:
        return self._val


class _ToggleBtnProxy:
    """Fanger opp .click() / .setText() fra qeltex_main.py for Control Core."""
    def __init__(self, win_ref):
        self._win = win_ref

    def click(self):
        self._win._buttons_visible = not self._win._buttons_visible
        self._win._push_js("setControlCoreVisible", self._win._buttons_visible)

    def setText(self, _txt: str):
        pass


class _GridWidgetProxy:
    """Fanger opp .show() / .hide() / .isVisible() fra qeltex_main.py."""
    def __init__(self, win_ref):
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
    def __init__(self, win_ref):
        self._win = win_ref
        self._lines = []

    def write_output(self, text: str):
        cleaned = str(text or "").strip()
        if cleaned:
            self._lines.append(cleaned)
            if len(self._lines) > 250:
                self._lines = self._lines[-250:]
            self._win._push_js("appendTerminal", cleaned)

    def toPlainText(self) -> str:
        return "\n".join(self._lines)

    def clear(self):
        self._lines.clear()
        self._win._push_js("clearTerminal", None)

class _DirectSignalProxy:
    def __init__(self, callback):
        self._cb = callback

    def emit(self, *args):
        threading.Thread(target=self._cb, args=args, daemon=True).start()        


class MainWindow(QWidget):
    _log_sig      = pyqtSignal(str)
    _state_sig    = pyqtSignal(str)
    _status_sig   = pyqtSignal(str)
    _progress_sig = pyqtSignal(int)
    _visuals_sig  = pyqtSignal(str)
    _hud_sig      = pyqtSignal(str)
    _theme_sig    = pyqtSignal(str)
    _browse_sig   = pyqtSignal()
    _js_exec_sig  = pyqtSignal(str)

    def resizeEvent(self, event):
        if event is not None:
            super().resizeEvent(event)

    def __init__(self):
        super().__init__()
        global _MAIN_WIN
        _MAIN_WIN = self

        self.on_text_command = None
        self._muted = False
        self._current_file: str | None = None
        self._buttons_visible = False
        self._stealth_active = False
        self._current_overlay = None
        self.hud = _HudStateProxy()
        self._js_ready = False
        self._pending_js: list[str] = []

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
        self.qeltex_budget_box = _LabelProxy("budget", "main", self)
        self.qeltex_status_label = _LabelProxy("status", "main", self)

        self._log_sig      = _DirectSignalProxy(lambda t: self._push_js("appendLog", str(t)))
        self._state_sig    = _DirectSignalProxy(self._apply_state)
        self._status_sig   = _DirectSignalProxy(lambda t: self._push_js("setStatusText", str(t)))
        self._progress_sig = _DirectSignalProxy(lambda v: self._push_js("setProgressValue", int(v)))
        self._visuals_sig  = _DirectSignalProxy(self._launch_visual_overlay)
        self._hud_sig      = _DirectSignalProxy(self.apply_hud)
        self._theme_sig    = _DirectSignalProxy(self.apply_theme)
        self._browse_sig   = _DirectSignalProxy(self._open_file_dialog)
        self._js_exec_sig  = _DirectSignalProxy(self._eval_in_webview)

        self._ready = self._check_config()
        self._start_global_hardware_hook()

    def _push_js(self, fn_name: str, payload):
        try:
            js_code = f"if(window.qeltexBridge && window.qeltexBridge.{fn_name}){{window.qeltexBridge.{fn_name}({json.dumps(payload)});}}"
            if not self._js_ready or _WV_WINDOW is None:
                self._pending_js.append(js_code)
            else:
                _WV_WINDOW.evaluate_js(js_code)
        except Exception:
            pass

    def _eval_in_webview(self, js_code: str):
        try:
            if _WV_WINDOW is not None:
                _WV_WINDOW.evaluate_js(js_code)
        except Exception:
            pass

    def _flush_pending_js(self):
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
        self.activate_stealth_mode = lambda: self._push_js("setStealthMode", True)
        self.activate_tactical_mode = lambda: self._push_js("setStealthMode", False)
        threading.Thread(target=lambda: (time.sleep(0.1), self._flush_pending_js()), daemon=True).start()

        def _read_json(name, default):
            p = CONFIG_DIR / name
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    pass
            return default

        eaton_reg = {}
        shc_reg = {}
        plugs_reg = {}
        gates_status = {"status": ["0", "0", "0"], "garage1_temp": "-- °C"}

        budget_data = _read_json("token_budget.json", {})
        saldo_nok = budget_data.get("saldo_nok", None)
        brukt_nok = budget_data.get("brukt_nok", None)
        if saldo_nok is not None and brukt_nok is not None:
            budget_text = f"SALDO: {float(saldo_nok):.2f} NOK  /  BRUKT: {float(brukt_nok):.2f} NOK"
        else:
            budget_text = "BUDGET REMAINING: $5.0 / $5.0"

        api_data = _read_json("api_keys.json", {})
        has_pin = bool(str(api_data.get("qeltex_PIN", "")).strip())
        cams_info = []
        visuals_list = []
        games_list = []

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
            "metrics": _metrics.snapshot()
        }

    def _apply_state(self, state: str):
        self.hud.state = str(state)
        self.hud.speaking = (str(state) == "SPEAKING")
        self._push_js("setAiState", str(state))

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        st = "MUTED" if self._muted else "LISTENING"
        self._apply_state(st)
        self._push_js("setMuted", self._muted)
        self._log_sig.emit("SYS: Microphone deactivated." if self._muted else "SYS: Microphone activated.")

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
        self._log_sig.emit(f"User: {cleaned}")
        if cleaned.lower() == "pin lock":
            self.activate_pin_lock()
            return
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(cleaned,), daemon=True).start()

    def _trigger_qeltex_vision(self):
        if self.on_text_command:
            self.set_error_text("SYS: Initiating hardware frame capture...")
            msg = "[SCREEN_PROCESS] angle=screen | text=Analyze the current active window layout and report status parameters in Norwegian."
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _launch_visual_overlay(self, payload: str):
        pass

    def close_active_overlays(self):
        if self._current_overlay is not None:
            try:
                if hasattr(self._current_overlay, "terminate"):
                    self._current_overlay.terminate()
                elif hasattr(self._current_overlay, "close"):
                    self._current_overlay.close()
            except Exception:
                pass
            self._current_overlay = None
        self._push_js("closeDropdowns", None)

    def _open_file_dialog(self):
        if _WV_WINDOW is None:
            return
        try:
            res = _WV_WINDOW.create_file_dialog(webview.OPEN_DIALOG)
            if res and len(res) > 0 and Path(res[0]).exists():
                path = str(res[0])
                self._current_file = path
                p = Path(path)
                sz = p.stat().st_size
                size_str = f"{sz/1024:.1f} KB" if sz < 1024**2 else f"{sz/1024**2:.1f} MB"
                self._push_js("setFileLoaded", {"name": p.name, "size": size_str, "ext": p.suffix.upper().lstrip(".") or "FILE"})
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
        cleaned = str(text or "").strip()
        self._push_js("setErrorText", cleaned)

    def activate_stealth_mode(self):
        self._stealth_active = True
        self._push_js("setStealthMode", True)

    def activate_tactical_mode(self):
        self._stealth_active = False
        self._push_js("setStealthMode", False)

    def activate_pin_lock(self):
        self._push_js("showPinLock", {"cameras": []})

    def check_pin(self, pin_str: str) -> bool:
        try:
            if API_FILE.exists():
                d = json.loads(API_FILE.read_text(encoding="utf-8"))
                expected = str(d.get("qeltex_PIN", ""))
                if not expected or pin_str.strip() == expected:
                    self._log_sig.emit("SYSTEM INTERFACE UNLOCKED")
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
            self._log_sig.emit(f"SYS: Initialization complete. OS={os_name.upper()}. Q.E.L.T.E.X online.")
            return True
        except Exception:
            return False

    def _handle_global_hotkey(self, key_id):
        pass

    def _start_global_hardware_hook(self):
        if _OS != "Windows":
            return

        def _hk_worker():
            pass

        threading.Thread(target=_hk_worker, daemon=True).start()


class _RootShim:
    def __init__(self, win_obj):
        self._win_obj = win_obj

    def mainloop(self):
        webview.start(debug=False)

    def protocol(self, *_):
        pass


class qeltexUI:
    def __init__(self, module_name=None, size=None):
        global _WV_WINDOW
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = MainWindow()
        self._api = JsApi()

        title = f"Q.E.L.T.E.X [{module_name}] — THUNDERSHIELD PROTOCOL" if module_name else "Q.E.L.T.E.X — THUNDERSHIELD PROTOCOL"

        _WV_WINDOW = webview.create_window(
            title,
            url=HTML_FILE.as_uri(),
            js_api=self._api,
            width=1360,
            height=860,
            min_size=(1024, 700),
            background_color="#000301"
        )
        self.root = _RootShim(_WV_WINDOW)

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
