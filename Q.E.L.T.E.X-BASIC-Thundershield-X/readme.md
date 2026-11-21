# Q.E.L.T.E.X — Basic Edition
### Cross-Platform Personal AI Assistant — By Thundershield-X

A real-time voice and text AI assistant that can hear, see, understand, and control your computer. Built for Windows, macOS, and Linux with local execution, adaptive tactical HUDs, and zero recurring software subscriptions.

---

## Overview

**Q.E.L.T.E.X Basic Edition** bridges the gap between your operating system and natural intent. Through ultra-low latency voice dialogue or direct text commands, Q.E.L.T.E.X analyzes your screen, processes uploaded documents, checks live weather and news, manages files and reminders, and executes multi-step workflows inside a responsive hybrid interface.

---

## Core Features

| Feature | Description |
|---|---|
| **Real-Time Voice & Text** | Ultra-low latency natural conversation in your language, or seamless fallback to text-only mode |
| **Visual Awareness (Vision)** | Real-time screen analysis and active window diagnostics (`F2`) |
| **System & Desktop Control** | Launch applications, manage system settings, organize desktop workspaces, and automate browser actions |
| **Document & File Processing** | Upload PDFs, Word documents, spreadsheets, or text files directly for instant summaries and analysis |
| **Autonomous Multi-Step Agent** | Built-in task planner and error-recovery engine for complex research and multi-step goals |
| **Live Briefings & Media** | Interactive weather matrix, morning digest, live news ticker, and internet radio streaming |
| **Persistent Long-Term Memory** | Remembers your preferences, projects, and context across sessions |
| **Security & Token Shield** | Built-in network monitoring, PIN lock screen (`F12`), Stealth Mode (`F7`), and real-time API budget tracking |

---

## Quick Start

1. Open a terminal inside the `QELTEX-Basic` folder and run the automated setup:

```bash
python setup.py
```

2. Start Q.E.L.T.E.X:

```bash
python qeltex_main.py
```

3. On first launch, enter your **Gemini API Key** and select your operating system in the initialization window.

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

## Command Matrix: Core Actions

### 🖥️ Desktop & System Subroutines

| Component | Description & Target Prompts |
|---|---|
| **computer_control.py** | Translates operational speech parameters into direct OS keystrokes, window manipulation, and coordinate clicks. <br>• "Minimize all active windows." <br>• "Click in the exact center of the screen." |
| **computer_settings.py** | Direct system hardware interface for updating volume thresholds, display brightness matrices, or toggling network adapters. <br>• "Set the system master volume to 50 percent." <br>• "Enable night light mode." |
| **desktop.py** | File layout utility assigned to sweep, inventory, or refactor assets located directly on the local Desktop. <br>• "Show me the files on my desktop." <br>• "Organize my desktop files." |
| **open_app.py** | Global execution pipeline mapping targeted strings to registered desktop software pathways. <br>• "Open Discord." <br>• "Start the system calculator." |
| **system_monitor.py** | Diagnostic reporting module feeding live metrics regarding CPU load, RAM utilization, and system uptime. <br>• "How is our current CPU usage looking?" <br>• "Open the system monitor." |

### 🔍 Vision, Files & Automation Agents

| Component | Description & Target Prompts |
|---|---|
| **screen_processor.py** | Captures active display buffers and invokes high-level vision logic to process ongoing visual data. <br>• "Tell me what you see on my screen." <br>• "Can you read the error message on my screen?" |
| **file_controller.py** | Handles raw storage operations including file moves, duplication, cleanup, and directory listing. <br>• "Move the image file from the desktop to the pictures folder." <br>• "Delete the temporary text file." |
| **file_processor.py** | Parses, summarizes, and analyzes text content within local PDF, Word, Excel, PowerPoint, Markdown, or TXT files. <br>• "Summarize the PDF report I just uploaded." <br>• "What are the key points in this document?" |
| **browser_control.py** | Automates web navigation, searches, clicking, and page reading in Chromium/Firefox. <br>• "Open the browser and go to nrk.no." <br>• "Search Google for latest AI news." |
| **web_search.py** | Real-time web search and comparison engine for up-to-date facts and research. <br>• "What is the price of Bitcoin today?" <br>• "Compare the latest laptops." |

### 🌐 Briefings, Communication & Security

| Component | Description & Target Prompts |
|---|---|
| **weather_report.py** | Fetches live meteorological data from MET Norway and opens the interactive Weather Matrix window. <br>• "Show me the weather." <br>• "What is the weather forecast for Oslo?" |
| **morning_digest.py** | Generates a complete daily briefing combining weather, top headlines, and active reminders. <br>• "Give me my morning briefing." |
| **news_ticker.py** | Streams live breaking news headlines directly into the interface. <br>• "Show me the latest news." |
| **radio.py** | Streams live Norwegian and international internet radio stations. <br>• "Play NRK P1." <br>• "Stop the radio." |
| **send_message.py** | Sends emails via Gmail or messages across supported platforms. <br>• "Send an email to John saying the report is ready." |
| **reminder.py** | Schedules timed reminders and desktop notifications. <br>• "Remind me in 30 minutes to call the client." |
| **network_shield.py** | Scans active network connections and monitors security status. <br>• "Run a network security scan." |
| **token_budget_shield.py** | Tracks real-time API token consumption and remaining budget balance. <br>• "How much is left on my token budget?" |

### 🧠 Core Orchestra & Memory Layer

| Component | Description |
|---|---|
| **planner.py** | Orchestrates and sequences multi-step execution workflows based on user intent. |
| **executor.py** | Direct execution engine running validated actions and background tasks. |
| **task_queue.py** | Asynchronous message broker managing queued tasks and priority execution. |
| **error_handler.py** | Dynamic exception interceptor handling retries, fallbacks, and recovery plans. |
| **prompt.txt** | Master system protocol defining assistant identity, routing rules, and behavior. |
| **memory_manager.py** | Persistent long-term memory storage tracking user preferences, projects, and context. |
| **config_manager.py** | Manages local configuration state, OS detection, and API credentials (`api_keys.json`). |

---

## License & Copyright

© Thundershield-X. All rights reserved.  
Commercial licensing and custom enterprise modules engineered by **Thundershield-X**.