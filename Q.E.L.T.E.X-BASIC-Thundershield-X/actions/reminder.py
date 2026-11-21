import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _get_os() -> str:
    config_file = _base_dir() / "config" / "api_keys.json"
    if not config_file.exists():
        return "windows"
    try:
        cfg = json.loads(config_file.read_text(encoding="utf-8"))
        return str(cfg.get("os_system", "windows")).lower()
    except Exception:
        return "windows"


def _scripts_dir() -> Path:
    try:
        d = Path.home() / ".qeltex" / "reminders"
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception as e:
        print(f"[Reminder] ⚠️ Could not create default scripts path ({e}). Deploying temporary directory fallback workflow.")
        tmp_dir = Path(tempfile.gettempdir()) / "qeltex_reminders"
        try:
            tmp_dir.mkdir(parents=True, exist_ok=True)
            return tmp_dir
        except Exception:
            return Path(tempfile.gettempdir())


def _sanitise(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    return (
        str(text).replace("\\", "")
            .replace('"', "")
            .replace("'", "")
            .replace("\n", " ")
            .replace("\r", "")
            .strip()
    )[:max_len]

def _write_notify_script(task_name: str, message: str, os_name: str) -> Path:
    script_path = _scripts_dir() / f"{task_name}.py"
    msg_literal = json.dumps(str(message if message else "Reminder Alert"))  

    if os_name == "windows":
        notify_block = f"""
message = {msg_literal}
notified = False

try:
    from plyer import notification
    notification.notify(title="qeltex Reminder", message=message, timeout=15)
    notified = True
except Exception:
    pass

if not notified:
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast("qeltex Reminder", message, duration=15, threaded=False)
        notified = True
    except Exception:
        pass

if not notified:
    try:
        import subprocess
        subprocess.run(["msg", "*", "/TIME:30", message], check=False)
    except Exception:
        pass

try:
    import winsound
    for freq in:
        winsound.Beep(freq, 180)
        import time; time.sleep(0.08)
except Exception:
    pass
"""

    elif os_name == "mac":
        notify_block = f"""
message = {msg_literal}
notified = False

try:
    from plyer import notification
    notification.notify(title="qeltex Reminder", message=message, timeout=15)
    notified = True
except Exception:
    pass

if not notified:
    try:
        import subprocess
        script = 'display notification "{{}}" with title "qeltex Reminder"'.format(
            message.replace('"', '')
        )
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception:
        pass
"""

    else:
        notify_block = f"""
message = {msg_literal}
notified = False

try:
    from plyer import notification
    notification.notify(title="qeltex Reminder", message=message, timeout=15)
    notified = True
except Exception:
    pass

if not notified:
    try:
        import subprocess
        subprocess.run(
            ["notify-send", "--urgency=normal", "--expire-time=15000",
             "qeltex Reminder", message],
            check=False
        )
    except Exception:
        pass
"""

    script_body = f"""import sys, os, pathlib
{notify_block}
try:
    pathlib.Path(__file__).unlink(missing_ok=True)
except Exception:
    pass
"""
    try:
        script_path.write_text(script_body, encoding="utf-8")
        try:
            script_path.chmod(0o600)
        except Exception:
            pass
    except Exception as e:
        print(f"[Reminder] ❌ Could not write reminder background target script: {e}")
        
    return script_path

def _schedule_windows(target_dt: datetime, task_name: str,
                      script_path: Path, message: str) -> str:
    if not isinstance(target_dt, datetime):
        print("[Reminder] ❌ Invalid date format passed to Windows scheduler matrix.")
        return ""

    python_exe = Path(sys.executable)
    pythonw = python_exe.parent / "pythonw.exe"
    if pythonw.exists():
        python_exe = pythonw

    xml_path = _scripts_dir() / f"{task_name}.xml"
    
    try:
        start_boundary = target_dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        start_boundary = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    xml_content = (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        '  <RegistrationInfo><Description>qeltex Reminder Framework</Description></RegistrationInfo>\n'
        '  <Triggers><TimeTrigger>\n'
        f'    <StartBoundary>{start_boundary}</StartBoundary>\n'
        '    <Enabled>true</Enabled>\n'
        '  </TimeTrigger></Triggers>\n'
        '  <Actions><Exec>\n'
        f'    <Command>{python_exe}</Command>\n'
        f'    <Arguments>"{script_path}"</Arguments>\n'
        '  </Exec></Actions>\n'
        '  <Settings>\n'
        '    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n'
        '    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n'
        '    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n'
        '    <StartWhenAvailable>true</StartWhenAvailable>\n'
        '    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>\n'
        '    <Enabled>true</Enabled>\n'
        '  </Settings>\n'
        '  <Principals><Principal>\n'
        '    <LogonType>InteractiveToken</LogonType>\n'
        '    <RunLevel>LeastPrivilege</RunLevel>\n'
        '  </Principal></Principals>\n'
        '</Task>'
    )

    try:
        xml_path.write_text(xml_content, encoding="utf-16")
    except Exception as e:
        print(f"[Reminder] ❌ Could not write temporary configuration matrix XML file: {e}")
        return ""

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", str(task_name), "/XML", str(xml_path), "/F"],
        capture_output=True, text=True,
    )

    try:
        if xml_path.exists():
            xml_path.unlink(missing_ok=True)
    except Exception:
        pass

    if result.returncode != 0:
        try:
            if script_path.exists():
                script_path.unlink(missing_ok=True)
        except Exception:
            pass
        err = (result.stderr or result.stdout or "Unknown Error").strip()
        print(f"[Reminder] ❌ schtasks failed: {err}")
        return ""  

    return task_name


def _schedule_mac(target_dt: datetime, task_name: str,
                  script_path: Path) -> str:
    if not isinstance(target_dt, datetime):
        print("[Reminder] ❌ Invalid date format passed to macOS scheduler matrix.")
        return ""

    try:
        agents_dir = Path.home() / "Library" / "LaunchAgents"
        agents_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[Reminder] ❌ Could not create LaunchAgents directory infrastructure: {e}")
        return ""

    label     = f"com.qeltex.reminder.{task_name}"
    plist_path = agents_dir / f"{label}.plist"

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>             <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{sys.executable}</string>
    <string>{script_path}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Year</key>   <integer>{target_dt.year}</integer>
    <key>Month</key>  <integer>{target_dt.month}</integer>
    <key>Day</key>    <integer>{target_dt.day}</integer>
    <key>Hour</key>   <integer>{target_dt.hour}</integer>
    <key>Minute</key> <integer>{target_dt.minute}</integer>
  </dict>
  <key>RunAtLoad</key>         <false/>
  <key>StandardOutPath</key>   <string>/dev/null</string>
  <key>StandardErrorPath</key> <string>/dev/null</string>
</dict>
</plist>
"""
    try:
        plist_path.write_text(plist_content, encoding="utf-8")
        try:
            plist_path.chmod(0o644)
        except Exception:
            pass
    except Exception as e:
        print(f"[Reminder] ❌ Could not write plist layout configuration: {e}")
        try:
            if script_path.exists():
                script_path.unlink(missing_ok=True)
        except Exception:
            pass
        return ""

    result = subprocess.run(
        ["launchctl", "load", str(plist_path)],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        try:
            if plist_path.exists(): plist_path.unlink(missing_ok=True)
            if script_path.exists(): script_path.unlink(missing_ok=True)
        except Exception:
            pass
        print(f"[Reminder] ❌ launchctl task load execution aborted: {result.stderr.strip()}")
        return ""

    return label


def _schedule_linux(target_dt: datetime, task_name: str,
                    script_path: Path) -> str:
    if not isinstance(target_dt, datetime):
        return ""

    if shutil.which("systemd-run"):
        try:
            on_calendar = target_dt.strftime("%Y-%m-%d %H:%M:00")
            result = subprocess.run(
                [
                    "systemd-run",
                    "--user",
                    f"--on-calendar={on_calendar}",
                    f"--unit={task_name}",
                    "--",
                    sys.executable, str(script_path),
                ],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                return task_name
            print(f"[Reminder] ⚠️ systemd-run failed: {result.stderr.strip()}, trying 'at'")
        except Exception as e:
            print(f"[Reminder] ⚠️ systemd-run exception: {e}")

    if shutil.which("at"):
        try:
            at_time = target_dt.strftime("%H:%M %Y-%m-%d")
            cmd_str = f"{sys.executable} {script_path}\n"
            result  = subprocess.run(
                ["at", at_time],
                input=cmd_str, capture_output=True, text=True,
            )
            if result.returncode == 0:
                return task_name
            print(f"[Reminder] ❌ at: {result.stderr.strip()}")
            return ""
        except Exception as e:
            print(f"[Reminder] ❌ at exception: {e}")
            return ""

    print("[Reminder] ❌ Missing installation: Neither 'systemd-run' nor 'at' was discovered on the Linux target system environment.")
    print("[Reminder] 👉 Please install the 'at' binary layout package: sudo apt install at")
    return ""

def reminder(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters if isinstance(parameters, dict) else {}

    date_str = str(params.get("date", "")).strip()
    time_str = str(params.get("time", "")).strip()
    message  = str(params.get("message", "Reminder")).strip()

    if not date_str or not time_str:
        return "I need both a date and a time to set a reminder."

    try:
        target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "I couldn't parse that date or time. Please use YYYY-MM-DD and HH:MM."

    if target_dt <= datetime.now():
        return "That time has already passed — I can't set a reminder in the past."

    os_name    = _get_os()
    safe_msg   = _sanitise(message)
    task_name  = f"qeltexReminder_{target_dt.strftime('%Y%m%d_%H%M%S')}"

    try:
        script_path = _write_notify_script(task_name, safe_msg, os_name)
    except Exception as e:
        return f"Could not prepare the reminder script: {e}"

    try:
        if os_name == "windows":
            job_id = _schedule_windows(target_dt, task_name, script_path, safe_msg)
        elif os_name == "mac":
            job_id = _schedule_mac(target_dt, task_name, script_path)
        else:
            job_id = _schedule_linux(target_dt, task_name, script_path)
    except Exception as e:
        try:
            if script_path and script_path.exists():
                script_path.unlink(missing_ok=True)
        except Exception:
            pass
        print(f"[Reminder] ❌ Scheduling exception: {e}")
        return "Something went wrong while scheduling the reminder."

    if not job_id:
        return "I couldn't register the reminder with the system scheduler."

    if player and hasattr(player, "write_log"):
        try:
            player.write_log(f"[Reminder] ✅ {date_str} {time_str} — {safe_msg[:40]}")
        except Exception:
            pass

    try:
        friendly_time = target_dt.strftime("%B %d at %I:%M %p")
    except Exception:
        friendly_time = f"{date_str} at {time_str}"
        
    return f"Reminder set for {friendly_time}."