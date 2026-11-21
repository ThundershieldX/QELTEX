def show_capabilities(parameters: dict = None, player=None) -> str:
    guide = (
        "==================================================\n"
        "   Q.E.L.T.E.X BASIC - CAPABILITIES & COMMANDS\n"
        "==================================================\n\n"
        " SYSTEM & DESKTOP CONTROL\n"
        "  - Open Apps:      'Open Discord' / 'Start calculator'\n"
        "  - OS Settings:    'Set volume to 50%' / 'Turn on night light'\n"
        "  - Desktop:        'Organize my desktop files'\n"
        "  - Automation:     'Minimize all windows' / 'Type hello'\n"
        "  - Diagnostics:    'Show system monitor' / 'Check CPU usage'\n\n"
        " VISION & DOCUMENT ANALYSIS\n"
        "  - Screen Vision:  'What do you see on my screen?' (or press F2)\n"
        "  - File Analysis:  Upload a PDF/Word/Excel file -> 'Summarize this file'\n"
        "  - File Manager:   'Move report.pdf from Desktop to Documents'\n\n"
        " WEB, BRIEFINGS & MEDIA\n"
        "  - Web Search:     'What is the weather in London?' / 'Search for AI news'\n"
        "  - Browser:        'Open nrk.no in the browser'\n"
        "  - Weather:        'Show me the weather' / 'Forecast for Oslo'\n"
        "  - Morning Digest: 'Give me my morning briefing'\n"
        "  - Live News:      'Show me the latest news'\n"
        "  - Internet Radio: 'Play NRK P1' / 'Stop the radio'\n\n"
        " COMMUNICATION, MEMORY & SECURITY\n"
        "  - Messages/Email: 'Send an email to John saying the report is ready'\n"
        "  - Reminders:      'Remind me in 30 minutes to call the client'\n"
        "  - Long-Term Mem:  'Remember that my next meeting is on Friday'\n"
        "  - Network Shield: 'Run a network security scan'\n"
        "  - Token Budget:   'How much is left on my token budget?'\n\n"
        " MULTI-STEP AUTONOMOUS AGENT\n"
        "  - Complex Goals:  'Research AI trends and save a summary on Desktop'\n\n"
        " INTERFACE & SHORTCUTS\n"
        "  - F2: Screen Vision   | F4: Mute Mic      | F7: Stealth Mode\n"
        "  - F11: Fullscreen     | F12: PIN Lock     | Shift+F10: HUDs\n"
        "=================================================="
    )

    if player and hasattr(player, "_win") and hasattr(player._win, "qeltex_terminal_stream"):
        player._win.qeltex_terminal_stream.clear()
        player._win.qeltex_terminal_stream.write_output(guide)

    return "Displayed full capabilities list and example commands in the right terminal window."