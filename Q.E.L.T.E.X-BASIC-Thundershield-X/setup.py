import subprocess
import sys
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

def run_setup():
    print("Checking system requirements...")
    base_dir = _get_base_dir()
    req_txt = base_dir / "requirements.txt"
    req_yxy = base_dir / "requirements.yxy"
    target_req = req_txt if req_txt.exists() else (req_yxy if req_yxy.exists() else None)

    if not target_req:
        print("Warning: Could not find requirements.txt or requirements.yxy.")
        print("Creating an updated requirements.txt file automatically...")
        try:
            default_deps = (
                "google-genai\nrequests\ntyping-extensions\npython-dotenv\n"
                "pycryptodome\n"
                "PyQt6\nPyQt6-WebEngine\npywebview\npythonnet\nPillow\n"
                "pyautogui\npyperclip\npsutil\nsend2trash\nplaywright\n"
                "pygetwindow\ncomtypes\npycaw\nwin10toast\npywinauto\npywin32\n"
                "opencv-python\nnumpy\nmss\npydub\npygame\nscapy\nsounddevice\n"
                "beautifulsoup4\nduckduckgo-search\n"
                "pandas\nopenpyxl\npython-docx\npython-pptx\npdfplumber\npypdf\nPyPDF2\nreportlab\n"
            )
            req_txt.write_text(default_deps, encoding="utf-8")
            target_req = req_txt
        except Exception as e:
            print(f"Error: Could not create requirements file: {e}")
            sys.exit(1)

    print("Upgrading pip to ensure compatibility...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)
    except Exception:
        print("Warning: Could not upgrade pip. Proceeding anyway...")

    print(f"Installing requirements from {target_req.name}...")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(target_req)], capture_output=False)
        if result.returncode != 0:
            print("\nError: Standard pip installation failed.")
            print("Please check your internet connection and run: pip install -r requirements.txt manually.")
            sys.exit(1)
    except Exception as e:
        print(f"\nError: Critical failure during pip installation: {e}")
        sys.exit(1)

    print("Installing Playwright browsers (Chromium & Firefox)...")
    try:
        result_pw = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium", "firefox"], capture_output=False)
        if result_pw.returncode != 0:
            print("\nWarning: Playwright browser installation did not complete successfully.")
            print("Browser control features might be limited until you run: playwright install chromium firefox")
    except Exception as e:
        print(f"\nWarning: Could not execute playwright installation: {e}")

    print("\nSetup process finished! Run 'python qeltex_main.py' to start qeltex.")

if __name__ == "__main__":
    run_setup()