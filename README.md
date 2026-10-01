# Time Tracker

A minimal, time tracking tool for Windows. Tap the green button to start, tap the red button when you're done, and the session is saved automatically.

## Features

- Four categories: Focus / AI Chat / Reading / Work — switch with a tap at the top
- Start / Stop button records the start and end time of every session (counts up, not down)
- Live elapsed time display (hours:minutes:seconds)
- Each category shows its own "Today's total" and today's session log
- The category switcher locks while a session is running, so you can't accidentally log time to the wrong category; sessions save automatically and persist locally
- If there's no mouse or keyboard activity anywhere on the system for 10 minutes, the session stops itself and is saved up to the moment you actually went idle (not padded with the idle time); its note is tagged "stopped automatically". This check only works on Windows
- If a session runs past midnight, it's automatically cut off and saved as the previous day's session at 00:00, and a new, separate session automatically starts right at 00:00 and keeps timing — so if you're still working past midnight, that time still gets recorded instead of silently going untracked. The two sessions are saved independently; deleting one never affects the other
- Click any row in "Today's Log" to attach a short note (what you read, who you chatted with, etc.); right-click a row to delete it (with a confirmation step)
- Dialogs are styled to match the app itself (warm background, soft-colored buttons) instead of the system's default message boxes
- Click the calendar icon in the top corner to review past days: any date with sessions gets a small dot, and opening a day shows the day's total time, a pie chart of the category split, and a timeline with each Focus / AI Chat / Reading block placed at the actual time it happened, notes included; double-click a block on the timeline to edit that session's note directly
- From the calendar, "Export to Calendar" saves all your sessions as a single .ics file you can double-click to import into Apple Calendar, Outlook, Google Calendar, etc.
- From the calendar, "Export for AI Analysis" lets you pick a range (This Week / This Month / All Records) and turns that period's sessions into AI-friendly text -- a day-by-day list of every session's start/end time, category and note, plus a ready-made analysis prompt at the top. It's copied straight to your clipboard (and a backup copy is saved alongside your data) so you can paste it directly into ChatGPT, Claude, or whatever AI assistant you already use, and have it tell you how your days actually break down, how focus and distraction time stack up, and whether work and life are in balance. No AI is built into the app itself -- the analysis happens entirely in whichever AI tool you paste it into
- Click the gear icon in the top corner for Sync Settings: pick any folder that's synced by a cloud drive (Google Drive, OneDrive, Dropbox, etc.) and this computer will share its log with any other computer signed into the same account — no account to register with the app itself, no server, no network code
- The window can be freely resized by dragging any edge or corner
- Single file, zero dependencies, warm off-white background with soft sage green / dusty blue / tan / coral / deep brown accents, inspired by the simplicity of the iOS Stopwatch app

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

## Where your data is stored / syncing across computers

By default, sessions are saved to `%APPDATA%\FocusTimer\sessions.json` (a plain JSON text file — safe to open, inspect, or back up). **The app will not switch to a different location on its own unless you pick one yourself in Sync Settings** (an earlier version auto-switched to OneDrive whenever it detected one, which on some machines made existing records look like they'd vanished; that's been fixed, and the app now also checks once on startup and automatically recovers any records it finds sitting in an old location).

To sync between computers: click the gear icon in the app → "Choose folder..." → pick any folder on this computer that's kept in sync by a cloud drive (for example, once you install the Google Drive desktop client, it creates a local "Google Drive" folder). On your other computer, open the app, sign into the same cloud account, and make the same choice — the two will then share the log through your cloud drive, with no account needed for the app itself.

## Files

- `focus_timer.py` — all the code, one file, ~250 lines, standard library only
- `run.bat` — run directly with an installed Python
- `build_exe.bat` — build a standalone .exe
