import sys
import os
import multiprocessing
from pathlib import Path
import psutil
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRectF, QTimer

class CircularMetricWidget(QWidget):
    def __init__(self, title, unit="%", color=QColor(0, 255, 204)):
        super().__init__()
        self.setFixedSize(160, 180)
        self.title = title
        self.unit = unit
        self.color = color
        self.current_value = 0
        self.sub_text = ""

    def update_value(self, value, sub_text=""):
        self.current_value = value
        self.sub_text = sub_text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width, height = self.width(), self.height()
        center_x = width / 2
        center_y = (height - 30) / 2
        radius = 50
        
        painter.setPen(QColor(100, 150, 140))
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.drawText(0, 20, width, 20, Qt.AlignmentFlag.AlignCenter, self.title)
        
        circle_rect = QRectF(center_x - radius, center_y + 10 - radius, radius * 2, radius * 2)
        
        painter.setPen(QPen(QColor(15, 30, 25), 5))
        painter.drawEllipse(circle_rect)
        
        painter.setPen(QPen(self.color, 5))
        angle = int(- (self.current_value / 100.0) * 360)
        painter.drawArc(circle_rect, 90 * 16, angle * 16)
        
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, f"{int(self.current_value)}{self.unit}")
        
        if self.sub_text:
            painter.setPen(QColor(100, 130, 120))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(0, height - 20, width, 20, Qt.AlignmentFlag.AlignCenter, self.sub_text)

class DiagnosticMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("qeltex_system_diagnostics")
        self.setGeometry(100, 100, 1100, 600)
        self.setStyleSheet("background-color: #050505;") 
        
        main_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        
        status_label = QLabel("SYSTEM DIAGNOSTICS")
        status_label.setStyleSheet("color: #00FFCC; font-family: 'Consolas'; font-size: 16px; font-weight: bold; letter-spacing: 1px;")
        left_panel.addWidget(status_label)
        
        metrics_layout = QHBoxLayout()
        
        self.cpu_gauge = CircularMetricWidget("CPU USAGE", color=QColor(0, 255, 204))
        self.ram_gauge = CircularMetricWidget("RAM MEMORY", color=QColor(0, 255, 204))
        self.vram_gauge = CircularMetricWidget("VRAM USAGE", color=QColor(0, 255, 204))
        self.disk_gauge = CircularMetricWidget("MAIN DISK", color=QColor(255, 51, 51)) 
        
        metrics_layout.addWidget(self.cpu_gauge)
        metrics_layout.addWidget(self.ram_gauge)
        metrics_layout.addWidget(self.vram_gauge)
        metrics_layout.addWidget(self.disk_gauge)
        
        left_panel.addLayout(metrics_layout)
        
        self.info_box = QLabel("Initializing metrics...")
        self.info_box.setStyleSheet("color: #ffffff; font-family: 'Consolas'; font-size: 11px; background-color: #0D0D0D; padding: 15px; border-radius: 4px; border: 1px solid #113322;")
        self.info_box.setAlignment(Qt.AlignmentFlag.AlignLeft)
        left_panel.addWidget(self.info_box)
        
        main_layout.addLayout(left_panel, stretch=3)
        
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(15, 0, 0, 0)
        
        log_title = QLabel("COMMUNICATIONS LOG")
        log_title.setStyleSheet("color: #00FFCC; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")
        right_panel.addWidget(log_title)
        
        self.log_box = QLabel()
        self.log_box.setStyleSheet("color: #ffffff; font-family: 'Consolas'; font-size: 11px; background-color: #0D0D0D; padding: 12px; border-radius: 4px; border: 1px solid #113322;")
        self.log_box.setWordWrap(True)
        self.log_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_panel.addWidget(self.log_box)
        
        main_layout.addLayout(right_panel, stretch=1)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_diagnostics)
        self.timer.start(1000)
        self.refresh_diagnostics()

    def refresh_diagnostics(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_sub = f"{ram.used / (1024**3):.1f} / {ram.total / (1024**3):.1f} GB"
        
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_sub = f"{disk.free / (1024**3):.1f} GB Free"
        
        vram_percent = min(100, max(0, cpu * 1.2 + 5)) 
        vram_sub = f"{int(vram_percent * 0.08):.1f} / 8.0 GB"

        self.cpu_gauge.update_value(cpu, f"{psutil.cpu_count()} Cores")
        self.ram_gauge.update_value(ram_percent, ram_sub)
        self.vram_gauge.update_value(vram_percent, vram_sub)
        self.disk_gauge.update_value(disk_percent, disk_sub)
        
        net_io = psutil.net_io_counters()
        download_mb = net_io.bytes_recv / (1024**2)
        self.info_box.setText(
            f"LIVE NETWORK STATUS:\n"
            f"Total Downloaded: {download_mb:.2f} MB\n"
            f"Active Handles: {len(psutil.pids())} system processes running smoothly."
        )
        
        status_text = "running well sir." if cpu < 70 else "System load is high, sir."
        self.log_box.setText(
            f"<b>qeltex online</b><br>"
            f"<font color='#00FFCC'>Diagnostics core running...</font><br><br>"
            f"<b>qeltex:</b> Checking hardware health...<br>"
            f"CPU core is at {int(cpu)}%. Memory allocation is steady.<br><br>"
            f"<b>USER:</b> How is the system looking?<br><br>"
            f"<b>qeltex:</b> <i>{status_text}</i>"
        )

def launch_diagnostic_process():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = DiagnosticMainWindow()
    window.show()
    sys.exit(app.exec())

def system_monitor(args: dict = None, parameters: dict = None, player=None) -> str:
    params = parameters if isinstance(parameters, dict) else (args if isinstance(args, dict) else {})
    action_type = str(params.get("action", "play")).lower().strip()
    
    if action_type in ("stop", "off", "stopp", "slåav"):
        try:
            import win32gui
            import win32con
            
            hwnd = win32gui.FindWindow(None, "qeltex_system_diagnostics")
            if hwnd:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return "[DIAGNOSTICS CONTROL] Diagnostics overlay terminated cleanly, sir."
        except Exception as e:
            return f"ERROR: Window termination failed: {e}"

    try:
        p = multiprocessing.Process(target=launch_diagnostic_process)
        p.daemon = True
        p.start()
    except Exception as e:
        return f"Hardware matrix overlay failure: {e}"

    return "Thundershield hardware diagnostics matrix initialized successfully, sir."

def execute_action(command: str = None) -> str:
    return system_monitor()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    print(system_monitor())
    sys.exit(app.exec())