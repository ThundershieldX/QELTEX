import os
import sys
import json
import random
import subprocess
import time
from pathlib import Path

_ACTIVE_STATION = None
_RADIO_PROCESS = None

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.path.realpath(sys.executable)).parent
    return Path(__file__).resolve().parent.parent

def _load_radio_streams() -> dict:
    base_nrk = "https://" + "lyd.nrk" + ".no"
    base_garden = "https://" + "radio." + "garden"
    base_bauer = "https://" + "live-bauerno.sharp-stream" + ".com"
    base_hls = "https://" + "p4-live.p4" + ".no"
    
    streams = {
        "p247kos": base_garden + "/listen/p24-7" + "-kos/ZOnuMbm6" + "?hl=no",
        "juleradioen": base_bauer + "/station17_no_mp3",
        "radionorge": base_bauer + "/radionorge_no_mp3",
        "nrjnorge": base_bauer + "/nrj_no_mp3",
        "p247mix": base_bauer + "/p247mix_no_mp3",
        "p11dance": base_garden + "/listen/p11" + "-dance/aYgckI6H" + "?hl=no",
        "90s90stechno": base_garden + "/listen/90s90s-techno/CQwDdbeG" + "?hl=no",
        "p5hits": base_garden + "/listen/p5" + "-hits/aaqRXFND" + "?hl=no",
        "p8pop": base_garden + "/listen/p8" + "-pop-80s-and-90s/rzzGm7Xx" + "?hl=no",
        "p10country": base_garden + "/listen/p10" + "-country/jiGukWGg" + "?hl=no",
        "p9retro": base_garden + "/listen/p9" + "-retro/cgOgDmMd" + "?hl=no",
        "radiometro": base_garden + "/listen/radio" + "-metro/Cj0HBsnE" + "?hl=no",
        "p12hitmix": base_garden + "/listen/p12" + "-hitmix/DMT8yHj4" + "?hl=no",
        "p7klem": base_garden + "/listen/klemfm" + "/DwNvxRwS" + "?hl=no",
        "silkeveienradio": base_garden + "/listen/silkeveien" + "-radio/g2Bbnu8Y" + "?hl=no",
        "radionova": base_garden + "/listen/radionova" + "/Sdi1oMAb" + "?hl=no",
        "ordentligradio": base_garden + "/listen/ordentligradio" + "/joIZecti" + "?hl=no",
        "radionnano": base_garden + "/listen/radio" + "-nano/OxRb1WgM" + "?hl=no",
        "radiorox": base_garden + "/listen/radiorox" + "/PiF7TPxI" + "?hl=no",
        "nrkp13": base_garden + "/listen/nrk" + "-p13/mEOEVbLn" + "?hl=no",
        "p6rock": base_garden + "/listen/p6" + "/PhMQjvGC" + "?hl=no",
        "radiotønsberg": base_garden + "/listen/radio" + "-tonsberg-fm-102-8/nISkGB5q" + "?hl=no",
        "p4": base_garden + "/listen/p4" + "/RWkbyuhu" + "?hl=no",
        "radionorge": base_garden + "/listen/radio" + "-norge/9Xg9wXfX",
        "nrkmp3": base_nrk + "/nrk_radio_mp3_mp3_h",
        "p1": base_nrk + "/nrk_radio_p1_ostlandssendingen_mp3_h",
        "p2": base_nrk + "/nrk_radio_p2_mp3_h",
        "p3": base_nrk + "/nrk_radio_p3_mp3_h",
        "p3unrørt": base_nrk + "/nrk_radio_p3_urort_mp3_m",
        "alltidnyheter": base_nrk + "/nrk_radio_alltid_nyheter_mp3_h",
        "folkemusikk": base_nrk + "/nrk_radio_folkemusikk_mp3_h",
        "jazz": base_nrk + "/nrk_radio_jazz_mp3_h",
        "klassisk": base_nrk + "/nrk_radio_klassisk_mp3_h",
        "p1pluss": base_nrk + "/nrk_radio_p1plus_mp3_h",
        "super": base_nrk + "/nrk_radio_super_mp3_m"
    }
    return streams

def execute_radio_action(parameters: dict, player=None) -> str:
    global _ACTIVE_STATION, _RADIO_PROCESS
    
    params = parameters if isinstance(parameters, dict) else {}
    action = str(params.get("action", "play")).lower().strip()
    station_query = str(params.get("station", "")).lower().replace(" ", "").strip()
    
    db = _load_radio_streams()
    
    if action in ("list", "show", "find", "vis", "finn"):
        found_stations = [f"-> {key}" for key in db.keys()]
        found_stations.sort()
        header = f"[qeltex DATABASE]: DISCOVERED {len(found_stations)} UNIQUE RADIO STREAMS:\n"
        return header + "\n".join(found_stations)
        
    if action in ("stop", "off", "stopp", "slåav"):
        try:
            os.system("taskkill /f /im msedge.exe")
            _RADIO_PROCESS = None
            _ACTIVE_STATION = None
            return "[RADIO CONTROL] Internet radio stream matrix terminated cleanly, sir."
        except Exception as e:
            return f"Radio termination error: {e}, sir."
            
    target_url = None
    matched_key = None
    
    if station_query:
        if station_query in db:
            target_url = db[station_query]
            matched_key = station_query
        else:
            sorted_keys = sorted(db.keys(), key=len, reverse=True)
            for key in sorted_keys:
                if station_query in key or key in station_query:
                    target_url = db[key]
                    matched_key = key
                    break
                
    if not target_url and action == "play":
        matched_key, target_url = "nrkmp3", db["nrkmp3"]
        
    if not target_url:
        return f"Could not resolve radio station channel blueprint for '{station_query}', sir."
        
    try:
        os.system("taskkill /f /im msedge.exe")
    except Exception:
        pass
        
    edge_path = "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        
    if not os.path.exists(edge_path):
        return "Microsoft Edge binary core could not be resolved on local disk, sir."
        
    try:
        profile_dir = _base_dir() / "config" / "qeltex_radio_profile"
        
        if "radio.garden" in target_url:
            cmd = [
                edge_path,
                f"--app={target_url}",
                f"--user-data-dir={str(profile_dir)}",
                "--no-first-run",
                "--no-default-browser-check",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=Translate",
                "--window-size=10,10",
                "--window-position=850,600"
            ]
            _RADIO_PROCESS = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            time.sleep(7)
            try:
                import win32com.client
                import win32gui
                import win32con
                shell = win32com.client.Dispatch("WScript.Shell")
                
                def enum_handler(hwnd, extra):
                    title = win32gui.GetWindowText(hwnd)
                    if "Radio Garden" in title:
                        extra.append(hwnd)
                    return True
                    
                target_hwnds = []
                win32gui.EnumWindows(enum_handler, target_hwnds)
                
                if shell.AppActivate("Radio Garden"):
                    time.sleep(0.5)
                    shell.SendKeys("{TAB}")
                    time.sleep(0.3)
                    shell.SendKeys("{ENTER}")
                    time.sleep(0.3)
                    shell.SendKeys(" ")
                    time.sleep(0.5)
                    for h in target_hwnds:
                        win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
            except Exception:
                pass
        else:
            html_content = f'<html lang="no"><head><title>qeltex_radio_engine</title></head><body style="background:#000;margin:0;display:flex;justify-content:center;align-items:center;"><audio id="r" src="{target_url}" autoplay controls style="width:100%;height:100%;"></audio><script>window.onload=()=>{{\nvar a=document.getElementById("r");\na.volume=1.0;\na.play().catch(e=>{{}});\n}};</script></body></html>'
            config_dir = _base_dir() / "config"
            if not config_dir.exists():
                os.makedirs(config_dir, exist_ok=True)
                
            temp_html = config_dir / "qeltex_radio_engine.html"
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            cmd = [
                edge_path,
                f"--app={temp_html.as_uri()}",
                f"--user-data-dir={str(profile_dir)}",
                "--no-first-run",
                "--no-default-browser-check",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=Translate",
                "--window-size=10,10",
                "--window-position=850,600"
            ]
            _RADIO_PROCESS = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            time.sleep(2)
            try:
                import win32com.client
                import win32gui
                import win32con
                shell = win32com.client.Dispatch("WScript.Shell")
                if shell.AppActivate("qeltex_radio_engine"):
                    shell.SendKeys(" ")
                    time.sleep(0.5)
                    hwnd = win32gui.FindWindow(None, "qeltex_radio_engine")
                    if hwnd:
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            except Exception:
                pass
                
        _ACTIVE_STATION = matched_key
        report_text = f"[qeltex RADIO]: BROADCAST LIVE -> {matched_key.upper()} STREAM ENGAGED"
        
        if player and hasattr(player, "ui"):
            if hasattr(player.ui, "_win") and hasattr(player.ui._win, "qeltex_terminal_stream"):
                try: player.ui._win.qeltex_terminal_stream.write_output(report_text)
                except Exception: pass
            elif hasattr(player.ui, "qeltex_terminal_stream"):
                try: player.ui.qeltex_terminal_stream.write_output(report_text)
                except Exception: pass
                
        print(report_text)
        return f"Radio deployment sequence initialized via browser core: {matched_key.upper()}, sir."
        
    except Exception as err:
        return f"Radio stream deployment disruption detected: {err}, sir."