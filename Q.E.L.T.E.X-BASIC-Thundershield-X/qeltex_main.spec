import os
import sys
import sounddevice
import cv2
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

certifi_datas = collect_data_files('certifi')

sounddevice_dir = os.path.dirname(sounddevice.__file__)
cv2_dir = os.path.dirname(cv2.__file__)

if sys.platform == "win32":
    playwright_browsers_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
elif sys.platform == "darwin":
    playwright_browsers_dir = os.path.expanduser("~/Library/Caches/ms-playwright")
else:
    playwright_browsers_dir = os.path.expanduser("~/.cache/ms-playwright")

playwright_datas = []
if os.path.exists(playwright_browsers_dir):
    playwright_datas = [(playwright_browsers_dir, 'playwright/driver/package/.local-browsers')]
else:
    print("Warning: Playwright browsers directory not found. Run 'playwright install' first!")

a = Analysis(
    ['qeltex_main.py'],
    pathex=[],
    binaries=[(os.path.join(sounddevice_dir, '_sounddevice_data'), '_sounddevice_data')],
    datas=[
        ('core', 'core'),
        ('agent', 'agent'),
        ('memory', 'memory'),
        ('config/world_map.png', 'config'),
        (cv2_dir, 'cv2'),
        ('qeltex_index.html', '.'),
        ('qeltex_huds.js', '.'),
    ] + ([('three.min.js', '.')] if os.path.exists('three.min.js') else []) + playwright_datas + certifi_datas,
    hiddenimports=[
        'certifi',
        'websockets',
        'httpx',
        'httpcore',
        'sounddevice',
        'pyaudio',
        'queue',
        'google',
        'google.genai',
        'requests',
        'Crypto',
        'aiohttp',
        'typing_extensions',
        'dotenv',
        'PyQt6',
        'PyQt6.QtMultimedia',
        'PIL',
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'clr',
        'pythonnet',
        'pyautogui',
        'pyperclip',
        'psutil',
        'send2trash',
        'playwright',
        'pygetwindow',
        'comtypes',
        'pycaw',
        'win10toast',
        'pywinauto',
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'cv2',
        'numpy',
        'mss',
        'pydub',
        'pygame',
        'scapy',
        'bs4',
        'duckduckgo_search',
        'pandas',
        'openpyxl',
        'docx',
        'pptx',
        'pdfplumber',
        'pypdf',
        'PyPDF2',
        'reportlab',
        'qeltex_ui',
        'agent.error_handler',
        'agent.executor',
        'agent.planner',
        'agent.task_queue',
        'memory.config_manager',
        'memory.memory_manager',
        'actions.browser_control',
        'actions.capabilities',
        'actions.computer_control',
        'actions.computer_settings',
        'actions.desktop',
        'actions.file_controller',
        'actions.file_processor',
        'actions.morning_digest',
        'actions.network_shield',
        'actions.news_ticker',
        'actions.open_app',
        'actions.radio',
        'actions.reminder',
        'actions.screen_processor',
        'actions.send_message',
        'actions.system_monitor',
        'actions.token_budget_shield',
        'actions.weather_report',
        'actions.web_search'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='qeltex_sys',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='qeltex.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
