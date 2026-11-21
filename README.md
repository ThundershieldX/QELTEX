# Q.E.L.T.E.X — Basic Edition
### Modular Cross-Platform Personal AI Assistant — By Thundershield-X

A real-time voice and text AI assistant that can hear, see, understand, and control your computer. Built as an extensible foundation for Windows, macOS, and Linux with adaptive tactical HUDs, multi-step autonomous agents, and a plug-and-play module architecture.

---

## Overview

**Q.E.L.T.E.X Basic Edition** bridges the gap between your operating system and natural intent. Through ultra-low latency voice dialogue or direct text commands, Q.E.L.T.E.X analyzes your screen, processes uploaded documents, checks live weather and news, manages files and reminders, and executes multi-step workflows inside a responsive hybrid interface (`pywebview` + `PyQt6`).

Designed as a modular core, this Basic Edition provides 18 built-in tools and a clean extension pipeline so you can easily build and plug in your own custom modules (such as stock trackers, local LLM backends, smart home controllers, or security tools).

---

## Core Features

| Feature | Description |
|---|---|
| **Real-Time Voice & Text** | Ultra-low latency natural conversation via Gemini Live, or seamless fallback to text-only mode |
| **Visual Awareness (Vision)** | Real-time screen capture and active window diagnostics (`F2`) |
| **System & Desktop Control** | Launch applications, adjust hardware/OS settings, organize desktop workspaces, and automate browsers |
| **Document & File Processing** | Upload PDFs, Word documents, spreadsheets, or text files directly for instant summaries and analysis |
| **Autonomous Multi-Step Agent** | Built-in task planner, queue broker, and error-recovery engine for complex multi-step workflows |
| **Live Briefings & Media** | Interactive weather matrix, morning digest, live news ticker, and internet radio streaming |
| **Persistent Long-Term Memory** | Remembers user preferences, ongoing projects, and context across sessions |
| **Security & Token Shield** | Built-in network monitoring, PIN lock screen (`F12`), Stealth Mode (`F7`), and real-time API budget tracking |
| **Modular Extension Engine** | Add custom Python modules in `actions/` with full AI voice integration, HUD buttons, and separate PyQt6 windows |

---

## Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com
cd QELTEX/Q.E.L.T.E.X-BASIC-Thundershield-X
```

2. **Run the automated setup:**
```bash
python setup.py
```

3. **Launch Q.E.L.T.E.X:**
```bash
python qeltex_main.py
```

4. **Configure API Keys:**  
On first launch, enter your **Gemini API Key** (and optional OpenRouter key) in the startup screen or directly inside `config/api_keys.json`.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `F2` | Capture and analyze active screen (Q.E.L.T.E.X Vision) |
| `F4` | Mute / Unmute microphone |
| `F7` | Toggle Stealth Mode (Minimalist HUD) |
| `F11` | Toggle Fullscreen Mode |
| `F12` | Engage PIN Security Lock |
| `Shift + F10` | Open HUD Display Selector |
| `Esc` | Close active dropdowns or exit Stealth Mode |

---

## System Requirements

| Requirement | Details |
|---|---|
| **Operating System** | Windows 10/11, macOS, or Linux |
| **Python** | Python 3.11 or 3.12 |
| **Audio** | Microphone and speakers/headset (optional — automatic text-only fallback if absent) |
| **API Key** | Google Gemini API key (configured via the startup screen or `config/api_keys.json`) |

---

## Built-In Command Matrix (18 Core Tools)

### 🖥️ Desktop & System Subroutines
* **`computer_control.py`** — Translates operational speech parameters into direct OS keystrokes, window manipulation, and coordinate clicks.
* **`computer_settings.py`** — Direct system hardware interface for updating volume thresholds, display brightness matrices, or toggling network adapters.
* **`desktop.py`** — File layout utility assigned to sweep, inventory, or refactor assets located directly on the local Desktop.
* **`open_app.py`** — Global execution pipeline mapping targeted strings to registered desktop software pathways.
* **`system_monitor.py`** — Diagnostic reporting module feeding live metrics regarding CPU load, RAM utilization, and system uptime in a dedicated PyQt6 window.

### 🔍 Vision, Files & Automation Agents
* **`screen_processor.py`** — Captures active display buffers and invokes high-level vision logic to analyze ongoing visual data.
* **`file_controller.py`** — Handles raw storage operations including file moves, duplication, cleanup, and directory listing.
* **`file_processor.py`** — Parses, summarizes, and analyzes text content within local PDF, Word, Excel, PowerPoint, Markdown, or TXT files.
* **`browser_control.py`** — Automates web navigation, searches, clicking, and page reading in Chromium/Firefox.
* **`web_search.py`** — Real-time web search and comparison engine for up-to-date facts and research.

### 🌐 Briefings, Communication & Security
* **`weather_report.py`** — Fetches live meteorological data from MET Norway and opens the interactive Weather Matrix window.
* **`morning_digest.py`** — Generates a complete daily briefing combining weather, top headlines, and active reminders.
* **`news_ticker.py`** — Streams live breaking news headlines directly into the interface.
* **`radio.py`** — Streams live Norwegian and international internet radio stations.
* **`send_message.py`** — Sends emails via Gmail or messages across supported platforms.
* **`reminder.py`** — Schedules timed reminders and desktop notifications.
* **`network_shield.py`** — Scans active network connections and monitors security status.
* **`token_budget_shield.py`** — Tracks real-time API token consumption and remaining budget balance.

### 🧠 Core Orchestra & Memory Layer
* **`agent/planner.py`** — Orchestrates and sequences multi-step execution workflows based on user intent.
* **`agent/executor.py`** — Direct execution engine running validated actions and background tasks.
* **`agent/task_queue.py`** — Asynchronous message broker managing queued tasks and priority execution.
* **`agent/error_handler.py`** — Dynamic exception interceptor handling retries, fallbacks, and recovery plans.
* **`core/prompt.txt`** — Master system protocol defining assistant identity, routing rules, and behavior.
* **`memory/memory_manager.py`** — Persistent long-term memory storage tracking user preferences, projects, and context.
* **`memory/config_manager.py`** — Manages local configuration state, OS detection, and API credentials (`config/api_keys.json`).

---

## Extending Q.E.L.T.E.X (Building Custom Modules)

Q.E.L.T.E.X Basic is engineered to be easily expanded with your own custom tools. Every new module follows a clean 4-step integration pattern:

1. **Create the Action (`actions/my_module.py`)**  
   Define `def my_module(parameters: dict = None, player=None) -> str:`.
   * Load API keys dynamically via `get_base_dir() / "config" / "api_keys.json"`.
   * Stream detailed tables, logs, or reports to the right terminal (`player._win.qeltex_terminal_stream.write_output(...)`).
   * Return a concise summary string for the AI voice/text engine to speak back to the user.
   * For custom GUI windows, spawn a separate daemon process using `multiprocessing.Process` with its own `QApplication` instance.

2. **Register with the AI Engine (`qeltex_main.py`)**  
   * Import the module function at the top of `qeltex_main.py`.
   * Add its `FunctionDeclaration` to `tool_declarations` inside `_build_config()`.
   * Route the tool call inside `_execute_tool(self, fc)`.

3. **Connect to the Autonomous Agent (`agent/planner.py` & `agent/executor.py`)**  
   * Document the tool name and parameters in `PLANNER_PROMPT` (`agent/planner.py`).
   * Add the execution handler inside `_call_tool()` (`agent/executor.py`).

4. **Optional HUD Control Button (`qeltex_ui.py` & `qeltex_index.html`)**  
   * Add a zero-token daemon thread trigger inside `class JsApi` in `qeltex_ui.py` and bind it to a button in the Control Core grid in `qeltex_index.html`.

---

## License & Copyright

© Thundershield-X. All rights reserved.  
Engineered by **Thundershield-X**.
