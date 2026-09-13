r"""
Time Tracker
------------------------------------------------------------
A minimal, Apple-inspired time tracking tool for Windows, covering
three categories: Focus / AI Chat / Reading.

Usage: pick a category at the top, tap the round button to start
timing, tap it again to stop and save. It's a stopwatch, not a
countdown -- it just records how long you spent.

Dependencies: Python standard library only (tkinter). No third-party
packages required.
Data is stored at: %APPDATA%\FocusTimer\sessions.json (Windows)
                    ~/.focus_timer/sessions.json (other OSes, for dev)
"""

import json
import os
import time
import tkinter as tk
from datetime import datetime

# ---------------------------------------------------------------- Colors / fonts
# Warm, soft, low-saturation palette for a calm, unhurried feel
BG = "#FAF6F1"           # warm off-white background
FG_PRIMARY = "#4A4644"    # primary text (soft warm charcoal, not pure black)
FG_SECONDARY = "#ADA49B"  # secondary text (warm gray)
CORAL = "#E3A296"         # "stop" color, shared across all categories
CORAL_HALO = "#F8E8E3"
DIVIDER = "#ECE5DC"

FONT_TITLE = ("Segoe UI", 12)
FONT_TAB = ("Segoe UI", 11)
FONT_TIMER = ("Consolas", 34)
FONT_BUTTON = ("Segoe UI", 13)
FONT_STAT_NUM = ("Segoe UI", 18)
FONT_STAT_LABEL = ("Segoe UI", 11)
FONT_ROW = ("Segoe UI", 11)

# Three categories, each with its own soft accent color (used for the
# start button and the selected tab)
CATEGORIES = [
    {"key": "focus", "label": "Focus", "accent": "#93BFA3", "halo": "#E4EFE8"},
    {"key": "ai_chat", "label": "AI Chat", "accent": "#96AFC9", "halo": "#E7ECF3"},
    {"key": "reading", "label": "Reading", "accent": "#D9B47E", "halo": "#F6ECDA"},
]


def data_file_path() -> str:
    """Return the JSON file path used to store sessions (APPDATA on Windows)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        folder = os.path.join(appdata, "FocusTimer")
    else:
        folder = os.path.join(os.path.expanduser("~"), ".focus_timer")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "sessions.json")


def load_sessions():
    path = data_file_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_sessions(sessions):
    with open(data_file_path(), "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def fmt_hms(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_duration(seconds: int) -> str:
    total_min = max(1, round(seconds / 60))
    h, m = divmod(total_min, 60)
    if h:
        return f"{h}h {m}m" if m else f"{h}h"
    return f"{m}m"


class FocusTimerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Time Tracker")
        self.root.configure(bg=BG)
        self.root.geometry("340x600")
        self.root.minsize(270, 400)
        self.root.resizable(True, True)  # drag any edge/corner to resize

        self.sessions = load_sessions()
        self.running = False
        self.start_time = None
        self._tick_job = None
        self.current_category = CATEGORIES[0]["key"]

        self._build_ui()
        self._select_category(self.current_category)

    # ------------------------------------------------------------ Build UI
    def _build_ui(self):
        pad_x = 22

        tk.Label(self.root, text="Time Tracker", font=FONT_TITLE,
                 bg=BG, fg=FG_SECONDARY).pack(pady=(18, 10))

        # Category switcher (segmented control)
        tab_frame = tk.Frame(self.root, bg=BG)
        tab_frame.pack()
        self.tab_labels = {}
        for cat in CATEGORIES:
            lbl = tk.Label(tab_frame, text=cat["label"], font=FONT_TAB,
                            bg=BG, fg=FG_SECONDARY, padx=10, pady=5, cursor="hand2")
            lbl.pack(side="left", padx=3)
            lbl.bind("<Button-1>", lambda e, k=cat["key"]: self._select_category(k))
            self.tab_labels[cat["key"]] = lbl

        self.timer_label = tk.Label(self.root, text="00:00:00", font=FONT_TIMER,
                                     bg=BG, fg=FG_PRIMARY)
        self.timer_label.pack(pady=(14, 16))

        # Round start/stop button, hand-drawn on a Canvas: a soft light
        # halo ring around a solid circle
        self.canvas_size = 128
        self.btn_diameter = 94
        self.canvas = tk.Canvas(self.root, width=self.canvas_size, height=self.canvas_size,
                                 bg=BG, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", lambda e: self.toggle())

        # Divider
        tk.Frame(self.root, bg=DIVIDER, height=1).pack(fill="x", padx=pad_x, pady=(22, 14))

        # Today's stats
        stat_frame = tk.Frame(self.root, bg=BG)
        stat_frame.pack(fill="x", padx=pad_x)
        self.stat_label = tk.Label(stat_frame, font=FONT_STAT_LABEL, bg=BG, fg=FG_SECONDARY)
        self.stat_label.pack(side="left")
        self.total_label = tk.Label(stat_frame, font=FONT_STAT_NUM, bg=BG, fg=FG_PRIMARY)
        self.total_label.pack(side="right")

        tk.Label(self.root, text="Today's Log", font=FONT_STAT_LABEL,
                 bg=BG, fg=FG_SECONDARY).pack(anchor="w", padx=pad_x, pady=(20, 6))

        # Today's session list
        list_frame = tk.Frame(self.root, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=pad_x, pady=(0, 20))

        self.history_list = tk.Listbox(list_frame, font=FONT_ROW, bg=BG, fg=FG_PRIMARY,
                                        relief="flat", highlightthickness=0,
                                        selectbackground=DIVIDER, activestyle="none",
                                        bd=0)
        self.history_list.pack(fill="both", expand=True)

    def _draw_button(self, color, halo_color, text):
        self.canvas.delete("all")
        c = self.canvas_size
        d = self.btn_diameter
        offset = (c - d) / 2
        self.canvas.create_oval(0, 0, c, c, fill=halo_color, outline="")
        self.canvas.create_oval(offset, offset, offset + d, offset + d,
                                 fill=color, outline="")
        self.canvas.create_text(c / 2, c / 2, text=text, font=FONT_BUTTON, fill="white")

    def _category(self, key):
        return next(c for c in CATEGORIES if c["key"] == key)

    # ------------------------------------------------------------ Category switching
    def _select_category(self, key):
        if self.running:
            return  # locked while a session is running, to avoid logging the wrong category
        self.current_category = key
        for cat in CATEGORIES:
            selected = cat["key"] == key
            self.tab_labels[cat["key"]].config(
                bg=cat["halo"] if selected else BG,
                fg=cat["accent"] if selected else FG_SECONDARY,
            )
        cat = self._category(key)
        self.timer_label.config(text="00:00:00")
        self._draw_button(cat["accent"], cat["halo"], "Start")
        self._refresh_history()

    # ------------------------------------------------------------ Timer logic
    def toggle(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.running = True
        self.start_time = time.time()
        self._draw_button(CORAL, CORAL_HALO, "Stop")
        self._tick()

    def _stop(self):
        self.running = False
        if self._tick_job is not None:
            self.root.after_cancel(self._tick_job)
            self._tick_job = None

        duration = time.time() - self.start_time
        if duration >= 5:  # ignore accidental very short taps
            self.sessions.append({
                "category": self.current_category,
                "start": datetime.fromtimestamp(self.start_time).isoformat(),
                "end": datetime.now().isoformat(),
                "duration_sec": round(duration),
            })
            save_sessions(self.sessions)

        self.start_time = None
        self.timer_label.config(text="00:00:00")
        cat = self._category(self.current_category)
        self._draw_button(cat["accent"], cat["halo"], "Start")
        self._refresh_history()

    def _tick(self):
        elapsed = time.time() - self.start_time
        self.timer_label.config(text=fmt_hms(elapsed))
        self._tick_job = self.root.after(1000, self._tick)

    # ------------------------------------------------------------ History
    def _refresh_history(self):
        today = datetime.now().date()
        label = self._category(self.current_category)["label"]
        todays = [s for s in self.sessions
                  if s.get("category", "focus") == self.current_category
                  and datetime.fromisoformat(s["start"]).date() == today]

        total_sec = sum(s["duration_sec"] for s in todays)
        self.stat_label.config(text=f"Today's {label}")
        self.total_label.config(text=fmt_duration(total_sec) if total_sec else "0m")

        self.history_list.delete(0, "end")
        for s in reversed(todays):
            start = datetime.fromisoformat(s["start"])
            end = datetime.fromisoformat(s["end"])
            row = f"  {start:%H:%M} - {end:%H:%M}      {fmt_duration(s['duration_sec'])}"
            self.history_list.insert("end", row)

        if not todays:
            self.history_list.insert("end", f"  No {label} sessions yet -- tap the button above to start")


def main():
    root = tk.Tk()
    FocusTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
