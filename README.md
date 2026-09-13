# Time Tracker

A minimal, Apple-inspired time tracking tool for Windows. **Not a countdown timer** — tap the green button to start, tap the red button when you're done, and the session is saved automatically.

## Features

- Three categories: Focus / AI Chat / Reading — switch with a tap at the top
- Start / Stop button records the start and end time of every session (counts up, not down)
- Live elapsed time display (hours:minutes:seconds)
- Each category shows its own "Today's total" and today's session log
- The category switcher locks while a session is running, so you can't accidentally log time to the wrong category; sessions save automatically and persist locally
- Click any row in "Today's Log" to attach a short note (what you read, who you chatted with, etc.); right-click a row to delete it (with a confirmation step)
- Dialogs are styled to match the app itself (warm background, soft-colored buttons) instead of the system's default message boxes
- The window can be freely resized by dragging any edge or corner
- Single file, zero dependencies, warm off-white background with soft sage green / dusty blue / tan / coral accents, inspired by the simplicity of the iOS Stopwatch app

## Run directly (requires Python)

Most Windows PCs don't come with Python pre-installed. If yours does (3.8+, with tkinter — included by default in the official installer):

1. Double-click `run.bat`

or from a command line:

```
python focus_timer.py
```

## Build a standalone .exe (recommended — no Python needed afterward)

1. Make sure Python is installed (get it from [python.org](https://www.python.org/downloads/) if not, and check "Add python.exe to PATH" during setup)
2. Double-click `build_exe.bat` — it installs PyInstaller and builds the exe automatically
3. Once done, find `TimeTracker.exe` inside the new `dist` folder — that's a standalone app you can double-click, move to your desktop, or share (no Python required on the machine that runs it)

## Where your data is stored

Sessions are saved to: `%APPDATA%\FocusTimer\sessions.json` (a plain JSON text file — safe to open, inspect, or back up)

## Files

- `focus_timer.py` — all the code, one file, ~250 lines, standard library only
- `run.bat` — run directly with an installed Python
- `build_exe.bat` — build a standalone .exe
