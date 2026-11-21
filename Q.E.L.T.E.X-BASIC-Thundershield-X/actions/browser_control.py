
from __future__ import annotations

import asyncio
import concurrent.futures
import os
import platform
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional

HAS_PLAYWRIGHT = True
try:
    from playwright.async_api import (
        async_playwright,
        BrowserContext,
        Page,
        Playwright,
        TimeoutError as PlaywrightTimeout,
    )
except ImportError:
    HAS_PLAYWRIGHT = False

_OS = platform.system()

def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return "about:blank"
    if "://" in url:
        return url
    if "." not in url:
        url = url + ".com"
    return "https://" + url


def _user_agent() -> str:
    if _OS == "Windows":
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    if _OS == "Darwin":
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    return (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )


def _real_profile_dir(browser: str) -> str:
    home  = Path.home()
    local = os.environ.get("LOCALAPPDATA", "")
    roam  = os.environ.get("APPDATA", "")

    candidates: list[Path] = []

    if _OS == "Windows":
        m = {
            "chrome":   [Path(local) / "Google"          / "Chrome"          / "User Data"],
            "edge":     [Path(local) / "Microsoft"        / "Edge"            / "User Data"],
            "brave":    [Path(local) / "BraveSoftware"    / "Brave-Browser"   / "User Data"],
            "vivaldi":  [Path(local) / "Vivaldi"          / "User Data"],
            "opera":    [Path(roam)  / "Opera Software"   / "Opera Stable",
                         Path(local) / "Opera Software"   / "Opera Stable"],
            "operagx":  [Path(roam)  / "Opera Software"   / "Opera GX Stable",
                         Path(local) / "Opera Software"   / "Opera GX Stable"],
        }
        candidates = m.get(browser, [])

    elif _OS == "Darwin":
        lib = home / "Library" / "Application Support"
        m = {
            "chrome":   [lib / "Google"             / "Chrome"],
            "edge":     [lib / "Microsoft Edge"],
            "brave":    [lib / "BraveSoftware"       / "Brave-Browser"],
            "vivaldi":  [lib / "Vivaldi"],
            "opera":    [lib / "com.operasoftware.Opera"],
            "operagx":  [lib / "com.operasoftware.OperaGX"],
        }
        candidates = m.get(browser, [])

    elif _OS == "Linux":
        cfg = home / ".config"
        m = {
            "chrome":   [cfg / "google-chrome", cfg / "chromium"],
            "edge":     [cfg / "microsoft-edge"],
            "brave":    [cfg / "BraveSoftware" / "Brave-Browser"],
            "vivaldi":  [cfg / "vivaldi"],
            "opera":    [cfg / "opera"],
            "operagx":  [cfg / "opera-gx"],
        }
        candidates = m.get(browser, [])

    try:
        for p in candidates:
            if p.exists():
                print(f"[Browser] ✅ Real profile found for {browser}: {p}")
                return str(p)
    except Exception:
        pass

    fallback = home / ".qeltex_profiles" / browser
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[Browser] ⚠️ Could not create fallback profile directory: {e}")
        return str(Path.gettempdir())
        
    print(f"[Browser] ⚠️ Real profile not found for {browser}, using: {fallback}")
    return str(fallback)

def _firefox_profile_dir() -> Optional[str]:
    home = Path.home()

    if _OS == "Windows":
        base = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox"
    elif _OS == "Darwin":
        base = home / "Library" / "Application Support" / "Firefox"
    else:
        base = home / ".mozilla" / "firefox"

    ini = base / "profiles.ini"
    if not ini.exists():
        return None

    try:
        current: dict[str, str] = {}
        default_path: Optional[str] = None

        for line in ini.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("["):
                p = current.get("Path", "")
                if p and current.get("Default") == "1":
                    is_rel = current.get("IsRelative", "1") == "1"
                    default_path = str(base / p) if is_rel else p
                current = {}
            elif "=" in line:
                k, _, v = line.partition("=")
                current[k.strip()] = v.strip()

        p = current.get("Path", "")
        if p and current.get("Default") == "1":
            is_rel = current.get("IsRelative", "1") == "1"
            default_path = str(base / p) if is_rel else p

        if default_path and Path(default_path).exists():
            print(f"[Browser] Firefox real profile: {default_path}")
            return default_path
    except Exception as e:
        print(f"[Browser] ⚠️ Error parsing Firefox profile database: {e}")
        
    return None

def _find_opera_windows() -> Optional[str]:
    local  = os.environ.get("LOCALAPPDATA", "")
    prog   = os.environ.get("PROGRAMFILES", "")
    prog86 = os.environ.get("PROGRAMFILES(X86)", "")

    candidates = [
        Path(local)  / "Programs" / "Opera"    / "opera.exe",
        Path(local)  / "Programs" / "Opera GX" / "opera.exe",
        Path(prog)   / "Opera"    / "opera.exe",
        Path(prog86) / "Opera"    / "opera.exe",
    ]
    for p in candidates:
        try:
            if p.exists():
                print(f"[Browser] Opera found at: {p}")
                return str(p)
        except Exception:
            pass

    try:
        import winreg
        keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe",
            r"SOFTWARE\Clients\StartMenuInternet\OperaStable\shell\open\command",
            r"SOFTWARE\Clients\StartMenuInternet\OperaGXStable\shell\open\command",
            r"SOFTWARE\Clients\StartMenuInternet\opera\shell\open\command",
        ]
        for key_path in keys:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    k   = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(k, None)
                    winreg.CloseKey(k)
                    
                    if not val or not isinstance(val, str):
                        continue
                        
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        print(f"[Browser] Opera found via registry: {exe}")
                        return exe
                except Exception:
                    continue
    except (ImportError, Exception):
        pass

    try:
        return shutil.which("opera") or None
    except Exception:
        return None

def _find_exe_windows(prog_name: str) -> Optional[str]:
    try:
        import winreg
        paths_to_try = [
            rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{prog_name}.exe",
            rf"SOFTWARE\Clients\StartMenuInternet\{prog_name}\shell\open\command",
        ]
        for key_path in paths_to_try:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    k   = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(k, None)
                    winreg.CloseKey(k)
                    
                    if not val or not isinstance(val, str):
                        continue
                        
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        return exe
                except Exception:
                    continue
    except (ImportError, Exception):
        pass
    return None

_BROWSER_SPECS: dict[str, dict] = {
    "Windows": {
        "chrome":   {"engine": "chromium", "channel": "chrome",  "bins": []},
        "edge":     {"engine": "chromium", "channel": "msedge",  "bins": []},
        "firefox":  {"engine": "firefox",  "channel": None,      "bins": ["firefox.exe"]},
        "opera":    {"engine": "chromium", "channel": None,      "bins": ["opera.exe"],  "special": "opera_windows"},
        "operagx":  {"engine": "chromium", "channel": None,      "bins": [],             "special": "opera_windows"},
        "brave":    {"engine": "chromium", "channel": None,      "bins": ["brave.exe"]},
        "vivaldi":  {"engine": "chromium", "channel": None,      "bins": ["vivaldi.exe"]},
        "safari":   None,
    },
    "Darwin": {
        "chrome":   {"engine": "chromium", "channel": "chrome",  "bins": []},
        "edge":     {"engine": "chromium", "channel": "msedge",  "bins": ["microsoft-edge"]},
        "firefox":  {"engine": "firefox",  "channel": None,      "bins": ["firefox"]},
        "opera":    {"engine": "chromium", "channel": None,      "bins": ["opera"]},
        "operagx":  {"engine": "chromium", "channel": None,      "bins": ["opera"]},
        "brave":    {"engine": "chromium", "channel": None,      "bins": ["brave browser", "brave"]},
        "vivaldi":  {"engine": "chromium", "channel": None,      "bins": ["vivaldi"]},
        "safari":   {"engine": "webkit",   "channel": None,      "bins": []},
    },
    "Linux": {
        "chrome":   {"engine": "chromium", "channel": None,
                     "bins": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]},
        "edge":     {"engine": "chromium", "channel": None,
                     "bins": ["microsoft-edge", "microsoft-edge-stable"]},
        "firefox":  {"engine": "firefox",  "channel": None, "bins": ["firefox"]},
        "opera":    {"engine": "chromium", "channel": None, "bins": ["opera", "opera-stable"]},
        "operagx":  {"engine": "chromium", "channel": None, "bins": ["opera", "opera-stable"]},
        "brave":    {"engine": "chromium", "channel": None, "bins": ["brave-browser", "brave"]},
        "vivaldi":  {"engine": "chromium", "channel": None, "bins": ["vivaldi-stable", "vivaldi"]},
        "safari":   None,
    },
}

_ALIASES: dict[str, str] = {
    "google chrome":   "chrome",
    "google-chrome":   "chrome",
    "microsoft edge":  "edge",
    "ms edge":         "edge",
    "msedge":          "edge",
    "mozilla firefox": "firefox",
    "opera gx":        "operagx",
    "opera_gx":        "operagx",
}


def _resolve_browser(name: str) -> dict | None:
    try:
        name   = _ALIASES.get(name.lower().strip(), name.lower().strip())
    except Exception:
        name = str(name).lower().strip()
        
    os_map = _BROWSER_SPECS.get(_OS, {})
    spec   = os_map.get(name)
    if spec is None:
        return None

    engine  = spec["engine"]
    channel = spec.get("channel")
    bins    = spec.get("bins", [])
    exe     = None

    if spec.get("special") == "opera_windows":
        exe = _find_opera_windows()
        if not exe:
            print(f"[Browser] ⚠️  Opera executable not found on Windows.")
        return {"engine": engine, "exe": exe, "channel": channel}

    for b in bins:
        try:
            found = shutil.which(b)
            if found:
                exe = found
                break
        except Exception:
            pass

    if not exe and _OS == "Darwin":
        app_names = {
            "chrome":  ["Google Chrome.app"],
            "edge":    ["Microsoft Edge.app"],
            "firefox": ["Firefox.app"],
            "opera":   ["Opera.app", "Opera GX.app"],
            "brave":   ["Brave Browser.app"],
            "vivaldi": ["Vivaldi.app"],
        }
        for app in app_names.get(name, []):
            try:
                app_dir = Path("/Applications") / app / "Contents" / "MacOS"
                if app_dir.exists():
                    found_bins = list(app_dir.iterdir())
                    if found_bins:
                        exe = str(found_bins[0])
                        break
            except Exception:
                pass

    if not exe and _OS == "Windows" and not channel:
        exe = _find_exe_windows(name)

    return {"engine": engine, "exe": exe, "channel": channel}


def _detect_default_browser() -> str:
    try:
        if _OS == "Windows":
            try:
                import winreg
                k = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\Shell\Associations"
                    r"\UrlAssociations\http\UserChoice",
                )
                prog_id = str(winreg.QueryValueEx(k, "ProgId")[0]).lower()
                winreg.CloseKey(k)
                for kw in ("edge", "firefox", "opera", "brave", "vivaldi", "chrome"):
                    if kw in prog_id:
                        return kw
            except (ImportError, Exception):
                pass
        elif _OS == "Darwin":
            out = subprocess.run(
                ["defaults", "read",
                 "com.apple.LaunchServices/com.apple.launchservices.secure",
                 "LSHandlers"],
                capture_output=True, text=True, timeout=5,
            ).stdout.lower()
            for kw in ("firefox", "opera", "brave", "vivaldi", "safari", "chrome", "edge"):
                if kw in out:
                    return kw
        elif _OS == "Linux":
            out = subprocess.run(
                ["xdg-settings", "get", "default-web-browser"],
                capture_output=True, text=True, timeout=5,
            ).stdout.lower()
            for kw in ("firefox", "opera", "brave", "vivaldi", "chrome", "edge"):
                if kw in out:
                    return kw
    except Exception:
        pass
    return "chrome"


class _BrowserSession:

    def __init__(self, browser_name: str):
        self.browser_name = browser_name
        self._spec        = _resolve_browser(browser_name)

        self._loop:    asyncio.AbstractEventLoop | None = None
        self._thread:  threading.Thread | None          = None
        self._ready    = threading.Event()

        self._pw:      Playwright     | None = None
        self._context: BrowserContext | None = None
        self._page:    Page           | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        try:
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name=f"BrowserThread-{self.browser_name}",
            )
            self._thread.start()
            self._ready.wait(timeout=20)
        except Exception as e:
            print(f"[Browser] ❌ Could not start session thread: {e}")

    def _run_loop(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._async_init())
            self._ready.set()
            self._loop.run_forever()
        except Exception as e:
            print(f"[Browser] ❌ Error in browser asynchronous execution loop: {e}")
            self._ready.set()

    async def _async_init(self):
        if not HAS_PLAYWRIGHT:
            print("[Browser] ❌ Playwright is not installed. Unable to initialize browser environment matrix.")
            return
        try:
            self._pw = await async_playwright().start()
        except Exception as e:
            print(f"[Browser] ❌ Error during async_playwright initialization: {e}")

    def run(self, coro, timeout: int = 60) -> str:
        if not self._loop:
            raise RuntimeError(f"Session for '{self.browser_name}' not started.")
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result(timeout=timeout)
        except Exception as e:
            print(f"[Browser] ❌ Error during execution in specialized thread: {e}")
            return f"Error: {e}"

    def close(self):
        if self._loop:
            try:
                asyncio.run_coroutine_threadsafe(self._async_close(), self._loop).result(10)
            except Exception:
                pass

    async def _async_close(self):
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self._context = self._page = None

    async def _launch(self):
        if self._context is not None:
            return

        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright is not installed. Please run 'python setup.py' first.")

        if self._spec is None:
            raise RuntimeError(
                f"'{self.browser_name}' is not supported on this platform ({_OS})."
            )

        engine_name = self._spec["engine"]
        exe         = self._spec["exe"]
        channel     = self._spec["channel"]
        
        try:
            engine_obj  = getattr(self._pw, engine_name)
        except AttributeError:
            raise RuntimeError(f"Playwright engine '{engine_name}' is not available.")

        if engine_name == "firefox":
            profile = _firefox_profile_dir() or str(
                Path.home() / ".qeltex_profiles" / "firefox"
            )
            kwargs: dict = {
                "headless":    False,
                "slow_mo":     0,
                "viewport":    None,
                "no_viewport": True,
            }
            if exe:
                kwargs["executable_path"] = exe
            try:
                self._context = await engine_obj.launch_persistent_context(profile, **kwargs)
            except Exception as e:
                print(f"[Browser] Firefox real profile failed ({e}), using qeltex profile")
                qeltex = str(Path.home() / ".qeltex_profiles" / "firefox_qeltex")
                try:
                    Path(qeltex).mkdir(parents=True, exist_ok=True)
                except Exception:
                    from tempfile import gettempdir
                    qeltex = str(Path(gettempdir()) / "firefox_qeltex")
                self._context = await engine_obj.launch_persistent_context(qeltex, **kwargs)

            await asyncio.sleep(0.5)  
            self._page = await self._context.new_page()
            print(f"[Browser] ✅ Firefox launched")
            return

        if engine_name == "webkit":
            safari_profile = str(Path.home() / ".qeltex_profiles" / "safari")
            try:
                Path(safari_profile).mkdir(parents=True, exist_ok=True)
            except Exception:
                from tempfile import gettempdir
                safari_profile = str(Path(gettempdir()) / "safari")
            kwargs = {
                "headless":    False,
                "slow_mo":     0,
                "viewport":    None,
                "no_viewport": True,
            }
            self._context = await engine_obj.launch_persistent_context(safari_profile, **kwargs)
            await asyncio.sleep(0.5)
            self._page = await self._context.new_page()
            print(f"[Browser] ✅ Safari launched")
            return

        profile = _real_profile_dir(self.browser_name)

        kwargs = {
            "headless":    False,
            "slow_mo":     0,
            "viewport":    None,
            "no_viewport": True,
            "args": [
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-default-apps",
                "--no-default-browser-check",
            ],
        }

        if exe:
            kwargs["executable_path"] = exe
        elif channel:
            kwargs["channel"] = channel

        label = (
            f"{self.browser_name}"
            + (f"/{channel}" if channel else "")
            + (f" @ {exe}" if exe else "")
        )

        try:
            self._context = await engine_obj.launch_persistent_context(profile, **kwargs)
            await asyncio.sleep(0.5) 
            self._page = await self._context.new_page()
            print(f"[Browser] ✅ Launched [{label}] profile={profile}")
            return
        except Exception as e:
            print(f"[Browser] ⚠️  Real profile failed for {label}: {e}")

        qeltex_profile = str(Path.home() / ".qeltex_profiles" / self.browser_name)
        try:
            Path(qeltex_profile).mkdir(parents=True, exist_ok=True)
        except Exception:
            from tempfile import gettempdir
            qeltex_profile = str(Path(gettempdir()) / self.browser_name)
            
        print(f"[Browser] Retrying with qeltex profile: {qeltex_profile}")

        try:
            self._context = await engine_obj.launch_persistent_context(qeltex_profile, **kwargs)
            await asyncio.sleep(0.5)
            self._page = await self._context.new_page()
            print(f"[Browser] ✅ Launched [{label}] with qeltex profile")
        except Exception as e2:
            raise RuntimeError(f"Could not launch {self.browser_name}: {e2}") from e2


    async def _get_page(self) -> Page:
        await self._launch()
        if self._context is None:
            raise RuntimeError("Browser context is unavailable.")
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
            await asyncio.sleep(0.2)
        return self._page

    async def go_to(self, url: str) -> str:
        url      = _normalize_url(url)
        page     = await self._get_page()
        prev_url = page.url

        async def _do_goto(p: Page) -> str:
            try:
                await p.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await asyncio.sleep(0.3)
            except (PlaywrightTimeout, Exception) as e:
                print(f"[Browser] goto exception or timeout (non-fatal): {e}")
            try:
                return p.url
            except Exception:
                return "about:blank"

        result_url = await _do_goto(page)

        if result_url in ("about:blank", "", None, prev_url) and prev_url in ("about:blank", "", None):
            print(f"[Browser] Still blank after goto — retrying on new tab: {url}")
            if self._context:
                try:
                    new_page   = await self._context.new_page()
                    self._page = new_page
                    result_url = await _do_goto(new_page)
                except Exception as e:
                    print(f"[Browser] New-tab retry failed: {e}")

        if result_url and result_url not in ("about:blank", "", None):
            return f"Opened: {result_url}"
        return f"Could not open: {url}"

    async def search(self, query: str, engine: str = "google") -> str:
        _engines = {
            "google":     "https://www.google.com/search?q=",
            "bing":       "https://www.bing.com/search?q=",
            "duckduckgo": "https://duckduckgo.com/?q=",
            "yandex":     "https://yandex.com/search/?text=",
        }
        try:
            target_engine = str(engine).lower() if engine else "google"
        except Exception:
            target_engine = "google"
            
        base = _engines.get(target_engine, _engines["google"])
        
        try:
            clean_query = str(query).replace(" ", "+") if query else ""
        except Exception:
            clean_query = ""
            
        return await self.go_to(base + clean_query)

    async def click(self, selector: str = None, text: str = None) -> str:
        try:
            page = await self._get_page()
            if text:
                await page.get_by_text(str(text), exact=False).first.click(timeout=8_000)
                return f"Clicked text: '{text}'"
            if selector:
                await page.click(str(selector), timeout=8_000)
                return f"Clicked selector: {selector}"
            return "No selector or text provided."
        except PlaywrightTimeout:
            return "Element not found (timeout)."
        except Exception as e:
            return f"Click error: {e}"

    async def type_text(self, selector: str = None, text: str = "",
                        clear_first: bool = True) -> str:
        try:
            page = await self._get_page()
            el = page.locator(str(selector)).first if selector else page.locator(":focus")
            if clear_first:
                try:
                    await el.clear()
                except Exception:
                    pass
            await el.type(str(text), delay=50)
            return "Text typed."
        except Exception as e:
            return f"Type error: {e}"

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        try:
            page = await self._get_page()
            y = amount if str(direction).lower() == "down" else -amount
            await page.mouse.wheel(0, y)
            return f"Scrolled {direction}."
        except Exception as e:
            return f"Scroll error: {e}"

    async def press(self, key: str) -> str:
        try:
            page = await self._get_page()
            await page.keyboard.press(str(key))
            return f"Pressed: {key}"
        except Exception as e:
            return f"Key error: {e}"

    async def get_text(self) -> str:
        try:
            page = await self._get_page()
            text = await page.inner_text("body")
            return text[:4_000] if text else ""
        except Exception as e:
            return f"Could not get page text: {e}"

    async def get_url(self) -> str:
        try:
            page = await self._get_page()
            return page.url
        except Exception:
            return "about:blank"

    async def fill_form(self, fields: dict) -> str:
        if not isinstance(fields, dict):
            return "Invalid fields format."
        try:
            page    = await self._get_page()
        except Exception as e:
            return f"Could not get browser page: {e}"
            
        results = []
        for selector, value in fields.items():
            try:
                el = page.locator(str(selector)).first
                try:
                    await el.clear()
                except Exception:
                    pass
                await el.type(str(value), delay=40)
                results.append(f"✓ {selector}")
            except Exception as e:
                results.append(f"✗ {selector}: {e}")
        return "Form filled: " + ", ".join(results)

    async def smart_click(self, description: str) -> str:
        try:
            page = await self._get_page()
        except Exception as e:
            return f"Could not get browser page: {e}"
            
        desc_str = str(description)
        for role in ("button", "link", "searchbox", "textbox", "menuitem", "tab"):
            try:
                loc = page.get_by_role(role, name=desc_str)
                if await loc.count() > 0:
                    await loc.first.click(timeout=5_000)
                    return f"Clicked ({role}): '{description}'"
            except Exception:
                pass
                
        try:
            await page.get_by_text(desc_str, exact=False).first.click(timeout=5_000)
            return f"Clicked: '{description}'"
        except Exception:
            pass
            
        try:
            await page.get_by_placeholder(desc_str, exact=False).first.click(timeout=5_000)
            return f"Clicked: '{description}'"
        except Exception:
            pass
            
        try:
            await page.locator(
                f'[alt*="{desc_str}" i],[title*="{desc_str}" i],'
                f'[aria-label*="{desc_str}" i]'
            ).first.click(timeout=5_000)
            return f"Clicked: '{description}'"
        except Exception:
            pass
            
        return f"Could not find element: '{description}'"

    async def smart_type(self, description: str, text: str) -> str:
        try:
            page = await self._get_page()
            desc_str = str(description)
            text_str = str(text)
            candidates = [
                ("placeholder", page.get_by_placeholder(desc_str, exact=False)),
                ("label",       page.get_by_label(desc_str, exact=False)),
                ("role",        page.get_by_role("textbox", name=desc_str)),
                ("searchbox",   page.get_by_role("searchbox")),
                ("combobox",    page.get_by_role("combobox", name=desc_str)),
            ]
            for method, loc in candidates:
                try:
                    el = loc.first
                    if await el.count() == 0:
                        continue
                    try:
                        await el.clear()
                    except Exception:
                        pass
                    await el.type(text_str, delay=50)
                    return f"Typed into ({method}): '{description}'"
                except Exception:
                    continue
        except Exception as e:
            return f"Smart type error: {e}"
        return f"Could not find input: '{description}'"

    async def new_tab(self, url: str = "") -> str:
        try:
            page = await self._get_page()
            ctx  = page.context
            new  = await ctx.new_page()
            self._page = new
            if url:
                return await self.go_to(str(url))
            return "New tab opened."
        except Exception as e:
            return f"New tab error: {e}"

    async def close_tab(self) -> str:
        try:
            page = self._page
            if page and not page.is_closed():
                ctx   = page.context
                await page.close()
                try:
                    pages = ctx.pages
                    self._page = pages[-1] if pages else None
                except Exception:
                    self._page = None
                return "Tab closed."
        except Exception as e:
            print(f"[Browser] Could not safely close the browser tab instance: {e}")
        return "No active tab to close."

    async def screenshot(self, path: str = None) -> str:
        try:
            page = await self._get_page()
            save_path = path or str(Path.home() / "Desktop" / "qeltex_screenshot.png")
            
            try:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
                
            await page.screenshot(path=save_path, full_page=False)
            return f"Screenshot saved: {save_path}"
        except Exception as e:
            return f"Screenshot error: {e}"

    async def back(self) -> str:
        try:
            page = await self._get_page()
            await page.go_back(timeout=10_000)
            return f"Navigated back: {page.url}"
        except Exception as e:
            return f"Back error: {e}"

    async def forward(self) -> str:
        try:
            page = await self._get_page()
            await page.go_forward(timeout=10_000)
            return f"Navigated forward: {page.url}"
        except Exception as e:
            return f"Forward error: {e}"

    async def reload(self) -> str:
        try:
            page = await self._get_page()
            await page.reload(timeout=15_000)
            return f"Page reloaded: {page.url}"
        except Exception as e:
            return f"Reload error: {e}"

    async def close_browser(self) -> str:
        try:
            await self._async_close()
        except Exception:
            pass
        return f"{self.browser_name} closed."

class _SessionRegistry:

    def __init__(self):
        self._sessions:       dict[str, _BrowserSession] = {}
        self._active_browser: str                        = ""
        self._lock            = threading.Lock()

    def _get_or_create(self, browser_name: str) -> _BrowserSession:
        with self._lock:
            if browser_name not in self._sessions:
                try:
                    sess = _BrowserSession(browser_name)
                    sess.start()
                    self._sessions[browser_name] = sess
                    print(f"[Registry] New session: {browser_name}")
                except Exception as e:
                    print(f"[Registry] ❌ Could not start browser session {browser_name}: {e}")
                    raise
            return self._sessions[browser_name]

    def get(self, browser_name: str | None = None) -> _BrowserSession:
        try:
            if not browser_name:
                browser_name = self._active_browser or _detect_default_browser()
            browser_name = _ALIASES.get(str(browser_name).lower().strip(), str(browser_name).lower().strip())
        except Exception:
            browser_name = "chrome"
            
        sess = self._get_or_create(browser_name)
        self._active_browser = browser_name
        return sess

    def switch(self, browser_name: str) -> str:
        try:
            browser_name = _ALIASES.get(str(browser_name).lower().strip(), str(browser_name).lower().strip())
            self._get_or_create(browser_name)
            self._active_browser = browser_name
            return f"Active browser → {browser_name}"
        except Exception as e:
            return f"Switch failed: {e}"

    def close_one(self, browser_name: str) -> str:
        try:
            b_name = str(browser_name).lower().strip()
            b_name = _ALIASES.get(b_name, b_name)
        except Exception:
            return "Invalid browser name."
            
        with self._lock:
            sess = self._sessions.pop(b_name, None)
        if sess:
            try:
                sess.close()
            except Exception:
                pass
            if self._active_browser == b_name:
                self._active_browser = ""
            return f"{browser_name} closed."
        return f"No active session for: {browser_name}"

    def close_all(self) -> str:
        with self._lock:
            names    = list(self._sessions.keys())
            sessions = list(self._sessions.values())
            self._sessions.clear()
            self._active_browser = ""
        for s in sessions:
            try:
                s.close()
            except Exception as e:
                print(f"[Registry] ⚠️ Error during close_all session termination: {e}")
        return "All browsers closed: " + (", ".join(names) if names else "none")

    def list_sessions(self) -> str:
        with self._lock:
            if not self._sessions:
                return "No active browser sessions."
            lines = []
            for name in self._sessions:
                marker = " ◀ active" if name == self._active_browser else ""
                lines.append(f"  • {name}{marker}")
            return "Open browsers:\n" + "\n".join(lines)


_registry = _SessionRegistry()

def browser_control(
    parameters:    dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    if not HAS_PLAYWRIGHT:
        result = "Playwright module or browsers missing. Please run setup.py first."
        _log(player, result)
        return result

    params  = parameters or {}
    
    action  = str(params.get("action", "")).lower().strip()
    browser = str(params.get("browser", "")).lower().strip() or None
    result  = "Unknown action."

    if action == "switch":
        target = browser or str(params.get("target", "")).lower().strip()
        result = _registry.switch(target) if target else "Please specify a browser."
        _log(player, result)
        return result

    if action == "list_browsers":
        result = _registry.list_sessions()
        _log(player, result)
        return result

    if action == "close_all":
        result = _registry.close_all()
        _log(player, result)
        return result

    try:
        sess = _registry.get(browser)
    except Exception as e:
        result = f"Could not start browser session: {e}"
        _log(player, result)
        return result

    try:
        if action == "go_to":
            result = sess.run(sess.go_to(params.get("url", "")))
        elif action == "search":
            result = sess.run(sess.search(params.get("query", ""), params.get("engine", "google")))
        elif action == "click":
            result = sess.run(sess.click(params.get("selector"), params.get("text")))
        elif action == "type":
            result = sess.run(sess.type_text(
                params.get("selector"), params.get("text", ""), params.get("clear_first", True)))
        elif action == "scroll":
            try:
                scroll_amount = int(params.get("amount", 500))
            except (ValueError, TypeError):
                scroll_amount = 500
            result = sess.run(sess.scroll(params.get("direction", "down"), scroll_amount))
        elif action == "fill_form":
            result = sess.run(sess.fill_form(params.get("fields", {})))
        elif action == "smart_click":
            result = sess.run(sess.smart_click(params.get("description", "")))
        elif action == "smart_type":
            result = sess.run(sess.smart_type(params.get("description", ""), params.get("text", "")))
        elif action == "get_text":
            result = sess.run(sess.get_text())
        elif action == "get_url":
            result = sess.run(sess.get_url())
        elif action == "press":
            result = sess.run(sess.press(params.get("key", "Enter")))
        elif action == "new_tab":
            result = sess.run(sess.new_tab(params.get("url", "")))
        elif action == "close_tab":
            result = sess.run(sess.close_tab())
        elif action == "screenshot":
            result = sess.run(sess.screenshot(params.get("path")))
        elif action == "back":
            result = sess.run(sess.back())
        elif action == "forward":
            result = sess.run(sess.forward())
        elif action == "reload":
            result = sess.run(sess.reload())
        elif action == "close":
            target = browser or _registry._active_browser
            result = _registry.close_one(target) if target else "No browser specified."
        else:
            result = f"Unknown browser action: '{action}'"

    except concurrent.futures.TimeoutError:
        result = f"Browser action '{action}' timed out (60s)."
    except Exception as e:
        result = f"Browser error ({action}): {e}"

    _log(player, result)
    return result


def _log(player, text: str):
    try:
        short = str(text)[:80]
        print(f"[Browser] {short}")
        if player and hasattr(player, "write_log"):
            player.write_log(f"[browser] {short[:60]}")
    except Exception:
        pass