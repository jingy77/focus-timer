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

import calendar
import json
import math
import os
import time
import tkinter as tk
from datetime import datetime, date, timedelta
from tkinter import filedialog

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
        self._overlay = None  # calendar / day-view frame, when one is open

        self.main_frame = tk.Frame(self.root, bg=BG)
        self._build_main(self.main_frame)
        self.main_frame.pack(fill="both", expand=True)
        self._select_category(self.current_category)

    # ------------------------------------------------------------ Build UI
    def _build_main(self, root):
        pad_x = 22

        tk.Label(root, text="Time Tracker", font=FONT_TITLE,
                 bg=BG, fg=FG_SECONDARY).pack(pady=(18, 10))

        cal_btn = tk.Label(root, text="\U0001F4C5", font=("Segoe UI", 13),
                            bg=BG, fg=FG_SECONDARY, cursor="hand2")
        cal_btn.place(relx=1.0, x=-16, y=16, anchor="ne")
        cal_btn.bind("<Button-1>", lambda e: self._open_calendar())

        # Category switcher (segmented control)
        tab_frame = tk.Frame(root, bg=BG)
        tab_frame.pack()
        self.tab_labels = {}
        for cat in CATEGORIES:
            lbl = tk.Label(tab_frame, text=cat["label"], font=FONT_TAB,
                            bg=BG, fg=FG_SECONDARY, padx=10, pady=5, cursor="hand2")
            lbl.pack(side="left", padx=3)
            lbl.bind("<Button-1>", lambda e, k=cat["key"]: self._select_category(k))
            self.tab_labels[cat["key"]] = lbl

        self.timer_label = tk.Label(root, text="00:00:00", font=FONT_TIMER,
                                     bg=BG, fg=FG_PRIMARY)
        self.timer_label.pack(pady=(14, 16))

        # Round start/stop button, hand-drawn on a Canvas: a soft light
        # halo ring around a solid circle
        self.canvas_size = 128
        self.btn_diameter = 94
        self.canvas = tk.Canvas(root, width=self.canvas_size, height=self.canvas_size,
                                 bg=BG, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", lambda e: self.toggle())

        # Divider
        tk.Frame(root, bg=DIVIDER, height=1).pack(fill="x", padx=pad_x, pady=(22, 14))

        # Today's stats
        stat_frame = tk.Frame(root, bg=BG)
        stat_frame.pack(fill="x", padx=pad_x)
        self.stat_label = tk.Label(stat_frame, font=FONT_STAT_LABEL, bg=BG, fg=FG_SECONDARY)
        self.stat_label.pack(side="left")
        self.total_label = tk.Label(stat_frame, font=FONT_STAT_NUM, bg=BG, fg=FG_PRIMARY)
        self.total_label.pack(side="right")

        log_header = tk.Frame(root, bg=BG)
        log_header.pack(fill="x", padx=pad_x, pady=(20, 6))
        tk.Label(log_header, text="Today's Log", font=FONT_STAT_LABEL,
                 bg=BG, fg=FG_SECONDARY).pack(side="left")
        tk.Label(log_header, text="click: note · right-click: delete", font=("Segoe UI", 9),
                 bg=BG, fg=FG_SECONDARY).pack(side="right")

        # Today's session list
        list_frame = tk.Frame(root, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=pad_x, pady=(0, 20))

        self.history_list = tk.Listbox(list_frame, font=FONT_ROW, bg=BG, fg=FG_PRIMARY,
                                        relief="flat", highlightthickness=0,
                                        selectbackground=DIVIDER, activestyle="none",
                                        bd=0)
        self.history_list.pack(fill="both", expand=True)
        self.history_list.bind("<Button-1>", self._on_history_left_click)
        self.history_list.bind("<Button-3>", self._on_history_right_click)
        self._visible_sessions = []  # rows currently shown, same order as the listbox

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
        self._visible_sessions = list(reversed(todays))
        for s in self._visible_sessions:
            self.history_list.insert("end", self._row_text(s))

        if not todays:
            self.history_list.insert("end", f"  No {label} sessions yet -- tap the button above to start")

    def _row_summary(self, s):
        start = datetime.fromisoformat(s["start"])
        end = datetime.fromisoformat(s["end"])
        return f"{start:%H:%M} - {end:%H:%M}   {fmt_duration(s['duration_sec'])}"

    def _row_text(self, s):
        note = s.get("note", "").strip()
        tail = f"  · {note}" if note else "   +"
        return f"  {self._row_summary(s)}{tail}"

    def _on_history_left_click(self, event):
        index = self.history_list.nearest(event.y)
        if index < 0 or index >= len(self._visible_sessions):
            return  # empty-state placeholder row
        session = self._visible_sessions[index]
        new_note = self._prompt_note(session.get("note", ""))
        if new_note is not None:
            session["note"] = new_note
            save_sessions(self.sessions)
            self._refresh_history()

    def _on_history_right_click(self, event):
        index = self.history_list.nearest(event.y)
        if index < 0 or index >= len(self._visible_sessions):
            return  # empty-state placeholder row, or nothing to delete
        self.history_list.selection_clear(0, "end")
        self.history_list.selection_set(index)
        session = self._visible_sessions[index]
        if self._confirm_delete(self._row_summary(session)):
            self.sessions.remove(session)
            save_sessions(self.sessions)
            self._refresh_history()

    # ------------------------------------------------------------ Dialogs
    # Small modal windows styled to match the app instead of the system's
    # default message boxes.
    def _dialog_shell(self, title):
        win = tk.Toplevel(self.root, bg=BG)
        win.title(title)
        win.resizable(False, False)
        win.transient(self.root)
        win.configure(bg=BG)
        return win

    def _place_dialog(self, win, w, h):
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.grab_set()
        win.wait_window()

    def _dialog_buttons(self, win, cancel_text, action_text, action_color, on_cancel, on_action):
        row = tk.Frame(win, bg=BG)
        row.pack(fill="x", padx=22, pady=(16, 20))
        tk.Button(row, text=cancel_text, font=FONT_ROW, bg=DIVIDER, fg=FG_PRIMARY,
                  relief="flat", bd=0, padx=12, pady=7, cursor="hand2",
                  activebackground=DIVIDER, command=on_cancel).pack(side="left", expand=True,
                                                                     fill="x", padx=(0, 6))
        tk.Button(row, text=action_text, font=FONT_ROW, bg=action_color, fg="white",
                  relief="flat", bd=0, padx=12, pady=7, cursor="hand2",
                  activebackground=action_color, command=on_action).pack(side="right", expand=True,
                                                                          fill="x", padx=(6, 0))

    def _confirm_delete(self, summary):
        win = self._dialog_shell("Delete Session")
        result = {"ok": False}
        tk.Label(win, text="Delete this session?", font=FONT_STAT_LABEL,
                 bg=BG, fg=FG_PRIMARY).pack(padx=22, pady=(20, 6))
        tk.Label(win, text=summary, font=FONT_ROW, bg=BG, fg=FG_SECONDARY).pack(padx=22)

        def cancel():
            win.destroy()

        def confirm():
            result["ok"] = True
            win.destroy()

        self._dialog_buttons(win, "Cancel", "Delete", CORAL, cancel, confirm)
        self._place_dialog(win, 300, 170)
        return result["ok"]

    def _prompt_note(self, current):
        cat = self._category(self.current_category)
        win = self._dialog_shell("Note")
        result = {"value": None}
        tk.Label(win, text="Note", font=FONT_STAT_LABEL, bg=BG, fg=FG_PRIMARY).pack(
            padx=22, pady=(20, 8), anchor="w")
        entry = tk.Entry(win, font=FONT_ROW, bg="white", fg=FG_PRIMARY, relief="flat",
                          highlightthickness=1, highlightbackground=DIVIDER,
                          highlightcolor=cat["accent"])
        entry.insert(0, current)
        entry.pack(padx=22, fill="x", ipady=6)
        entry.focus_set()
        entry.icursor("end")

        def cancel():
            win.destroy()

        def save():
            result["value"] = entry.get().strip()
            win.destroy()

        entry.bind("<Return>", lambda e: save())
        entry.bind("<Escape>", lambda e: cancel())
        self._dialog_buttons(win, "Cancel", "Save", cat["accent"], cancel, save)
        self._place_dialog(win, 300, 170)
        return result["value"]

    def _info_dialog(self, title, message):
        win = self._dialog_shell(title)
        tk.Label(win, text=title, font=FONT_STAT_LABEL, bg=BG, fg=FG_PRIMARY).pack(
            padx=22, pady=(20, 6))
        tk.Label(win, text=message, font=FONT_ROW, bg=BG, fg=FG_SECONDARY,
                 justify="left", wraplength=260).pack(padx=22)

        def close():
            win.destroy()

        row = tk.Frame(win, bg=BG)
        row.pack(fill="x", padx=22, pady=(16, 20))
        accent = self._category(self.current_category)["accent"]
        tk.Button(row, text="OK", font=FONT_ROW, bg=accent, fg="white",
                  relief="flat", bd=0, padx=12, pady=7, cursor="hand2",
                  activebackground=accent, command=close).pack(fill="x")
        self._place_dialog(win, 300, 210)

    # ------------------------------------------------------------ Calendar / day review
    # An overlay frame (calendar month grid, or a single day's timeline)
    # shown on top of the main timer view. The timer keeps running
    # underneath even while browsing history.
    def _sessions_for_date(self, d):
        return sorted(
            (s for s in self.sessions if datetime.fromisoformat(s["start"]).date() == d),
            key=lambda s: s["start"],
        )

    def _shift_month(self, year, month, delta):
        m = month - 1 + delta
        return year + m // 12, m % 12 + 1

    def _show_overlay(self, build_fn):
        if self._overlay is not None:
            self._overlay.destroy()
        self.main_frame.pack_forget()
        frame = tk.Frame(self.root, bg=BG)
        build_fn(frame)
        frame.pack(fill="both", expand=True)
        self._overlay = frame

    def _close_overlay(self):
        if self._overlay is not None:
            self._overlay.destroy()
            self._overlay = None
        self.main_frame.pack(fill="both", expand=True)

    def _open_calendar(self, year=None, month=None):
        today = date.today()
        self._show_overlay(lambda f: self._build_calendar(f, year or today.year, month or today.month))

    def _open_day(self, d):
        self._show_overlay(lambda f: self._build_day(f, d))

    def _export_ics(self):
        if not self.sessions:
            self._info_dialog("Export to Calendar", "No sessions to export yet.")
            return

        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//FocusTimer//EN//",
                 "CALSCALE:GREGORIAN"]
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        for i, s in enumerate(sorted(self.sessions, key=lambda s: s["start"])):
            start = datetime.fromisoformat(s["start"])
            end = datetime.fromisoformat(s["end"])
            cat = self._category(s.get("category", "focus"))
            note = s.get("note", "").strip()
            lines += [
                "BEGIN:VEVENT",
                f"UID:{start.strftime('%Y%m%dT%H%M%S')}-{i}@focustimer",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{self._ics_escape(cat['label'])}",
            ]
            if note:
                lines.append(f"DESCRIPTION:{self._ics_escape(note)}")
            lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        content = "\r\n".join(lines) + "\r\n"

        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export to Calendar",
            defaultextension=".ics", filetypes=[("iCalendar file", "*.ics")],
            initialfile="time_tracker.ics",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self._info_dialog(
            "Exported",
            f"Saved as:\n{os.path.basename(path)}\n\n"
            "Double-click it to import into your calendar app "
            "(Apple Calendar, Outlook, Google Calendar, etc.).",
        )

    @staticmethod
    def _ics_escape(text):
        return (text.replace("\\", "\\\\").replace(";", "\\;")
                    .replace(",", "\\,").replace("\n", "\\n"))

    def _build_calendar(self, root, year, month):
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=22, pady=(18, 0))
        back = tk.Label(top, text="‹ Back", font=FONT_ROW, bg=BG, fg=FG_SECONDARY,
                         cursor="hand2")
        back.pack(side="left")
        back.bind("<Button-1>", lambda e: self._close_overlay())
        export_lbl = tk.Label(top, text="Export to Calendar", font=FONT_ROW, bg=BG,
                               fg=FG_SECONDARY, cursor="hand2")
        export_lbl.pack(side="right")
        export_lbl.bind("<Button-1>", lambda e: self._export_ics())

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=22, pady=(10, 4))
        py, pm = self._shift_month(year, month, -1)
        ny, nm = self._shift_month(year, month, 1)
        prev_lbl = tk.Label(header, text="‹", font=("Segoe UI", 14), bg=BG, fg=FG_SECONDARY,
                             cursor="hand2")
        prev_lbl.pack(side="left")
        prev_lbl.bind("<Button-1>", lambda e: self._open_calendar(py, pm))
        tk.Label(header, text=f"{calendar.month_name[month]} {year}", font=FONT_STAT_LABEL,
                 bg=BG, fg=FG_PRIMARY).pack(side="left", expand=True)
        next_lbl = tk.Label(header, text="›", font=("Segoe UI", 14), bg=BG, fg=FG_SECONDARY,
                             cursor="hand2")
        next_lbl.pack(side="right")
        next_lbl.bind("<Button-1>", lambda e: self._open_calendar(ny, nm))

        grid = tk.Frame(root, bg=BG)
        grid.pack(fill="both", expand=True, padx=22, pady=(4, 20))
        for i in range(7):
            grid.columnconfigure(i, weight=1)
        for i, wd in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            tk.Label(grid, text=wd, font=("Segoe UI", 9), bg=BG, fg=FG_SECONDARY).grid(
                row=0, column=i, pady=(0, 8))

        today = date.today()
        weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                d = date(year, month, day)
                cell = tk.Frame(grid, bg=BG)
                cell.grid(row=r, column=c, sticky="nsew", pady=3)
                num_bg = DIVIDER if d == today else BG
                num = tk.Label(cell, text=str(day), font=FONT_ROW, bg=num_bg, fg=FG_PRIMARY,
                                width=3, cursor="hand2")
                num.pack()
                dot = tk.Label(cell, text="•" if self._sessions_for_date(d) else " ",
                                font=("Segoe UI", 8), bg=BG, fg=FG_SECONDARY, cursor="hand2")
                dot.pack()
                for w in (cell, num, dot):
                    w.bind("<Button-1>", lambda e, dd=d: self._open_day(dd))

    def _time_range(self, sessions, d):
        starts, ends = [], []
        for s in sessions:
            sd = datetime.fromisoformat(s["start"])
            ed = datetime.fromisoformat(s["end"])
            starts.append(sd.hour + sd.minute / 60)
            ends.append(24.0 if ed.date() != d else ed.hour + ed.minute / 60)
        lo = max(0, math.floor(min(starts)) - 1)
        hi = min(24, math.ceil(max(ends)) + 1)
        if hi - lo < 4:
            lo, hi = max(0, hi - 4), min(24, lo + 4)
        return lo, hi

    def _build_day(self, root, d):
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=22, pady=(18, 0))
        back = tk.Label(top, text="‹ Calendar", font=FONT_ROW, bg=BG, fg=FG_SECONDARY,
                         cursor="hand2")
        back.pack(side="left")
        back.bind("<Button-1>", lambda e: self._open_calendar(d.year, d.month))

        nav = tk.Frame(root, bg=BG)
        nav.pack(fill="x", padx=22, pady=(10, 14))
        prev_lbl = tk.Label(nav, text="‹", font=("Segoe UI", 14), bg=BG, fg=FG_SECONDARY,
                             cursor="hand2")
        prev_lbl.pack(side="left")
        prev_lbl.bind("<Button-1>", lambda e: self._open_day(d - timedelta(days=1)))
        tk.Label(nav, text=d.strftime("%a, %b %d"), font=FONT_STAT_LABEL, bg=BG,
                 fg=FG_PRIMARY).pack(side="left", expand=True)
        next_lbl = tk.Label(nav, text="›", font=("Segoe UI", 14), bg=BG, fg=FG_SECONDARY,
                             cursor="hand2")
        next_lbl.pack(side="right")
        next_lbl.bind("<Button-1>", lambda e: self._open_day(d + timedelta(days=1)))

        sessions = self._sessions_for_date(d)
        if not sessions:
            tk.Label(root, text="No sessions this day", font=FONT_ROW, bg=BG,
                     fg=FG_SECONDARY).pack(pady=40)
            return

        # ---- Daily report: total time + a pie chart of the category split ----
        per_cat_sec = {c["key"]: 0 for c in CATEGORIES}
        for s in sessions:
            per_cat_sec[s.get("category", "focus")] += s["duration_sec"]
        day_total = sum(per_cat_sec.values())

        report = tk.Frame(root, bg=BG)
        report.pack(fill="x", padx=22, pady=(0, 16))
        tk.Label(report, text=f"Total today: {fmt_duration(day_total)}", font=FONT_STAT_LABEL,
                 bg=BG, fg=FG_PRIMARY).pack(anchor="w")

        body = tk.Frame(report, bg=BG)
        body.pack(fill="x", pady=(10, 0))
        pie_size = 96
        pie_cv = tk.Canvas(body, width=pie_size, height=pie_size, bg=BG, highlightthickness=0)
        pie_cv.pack(side="left")
        legend = tk.Frame(body, bg=BG)
        legend.pack(side="left", padx=(18, 0), fill="y")

        angle = 90.0
        for cat in CATEGORIES:
            sec = per_cat_sec[cat["key"]]
            if sec <= 0:
                continue
            fraction = sec / day_total
            extent = -fraction * 360
            pie_cv.create_arc(2, 2, pie_size - 2, pie_size - 2, start=angle, extent=extent,
                               fill=cat["accent"], outline=BG, width=2)
            angle += extent

            row = tk.Frame(legend, bg=BG)
            row.pack(anchor="w", pady=2)
            tk.Frame(row, bg=cat["accent"], width=10, height=10).pack(side="left")
            tk.Label(row, text=f" {cat['label']}  {fmt_duration(sec)} ({round(fraction * 100)}%)",
                     font=("Segoe UI", 9), bg=BG, fg=FG_PRIMARY).pack(side="left")

        tk.Frame(root, bg=DIVIDER, height=1).pack(fill="x", padx=22, pady=(0, 4))
        tk.Label(root, text="double-click a block to edit its note", font=("Segoe UI", 9), bg=BG,
                 fg=FG_SECONDARY).pack(anchor="e", padx=22, pady=(0, 6))

        lo, hi = self._time_range(sessions, d)
        px = 70               # pixels per hour
        label_w = 46          # left column reserved for hour labels
        block_w = 190         # width of the colored session blocks
        canvas_w = label_w + 10 + block_w + 16
        canvas_h = int((hi - lo) * px)

        def y_of(hour):
            return (hour - lo) * px

        outer = tk.Frame(root, bg=BG)
        outer.pack(fill="both", expand=True, padx=(22, 8), pady=(0, 20))
        vsb = tk.Scrollbar(outer, orient="vertical")
        vsb.pack(side="right", fill="y")
        cv = tk.Canvas(outer, bg=BG, highlightthickness=0, width=canvas_w,
                        yscrollcommand=vsb.set)
        cv.pack(side="left", fill="both", expand=True)
        vsb.config(command=cv.yview)
        cv.bind("<MouseWheel>", lambda e: cv.yview_scroll(int(-e.delta / 120), "units"))

        for h in range(lo, hi + 1):
            y = y_of(h)
            cv.create_line(label_w, y, canvas_w, y, fill=DIVIDER)
            cv.create_text(label_w - 8, y, text=f"{h:02d}:00", font=("Segoe UI", 9),
                            fill=FG_SECONDARY, anchor="e")

        x0, x1 = label_w + 10, label_w + 10 + block_w
        blocks = []  # (y0, y1, session) -- used to find which block a double-click landed on
        for s in sessions:
            cat = self._category(s.get("category", "focus"))
            start_dt = datetime.fromisoformat(s["start"])
            end_dt = datetime.fromisoformat(s["end"])
            sh = start_dt.hour + start_dt.minute / 60
            eh = 24.0 if end_dt.date() != d else end_dt.hour + end_dt.minute / 60
            y0, y1 = y_of(sh), max(y_of(eh), y_of(sh) + 3)
            cv.create_rectangle(x0, y0, x1, y1, fill=cat["accent"], outline="")
            blocks.append((y0, y1, s))
            if y1 - y0 >= 18:
                text = f"{cat['label']}  {start_dt:%H:%M}-{end_dt:%H:%M}"
                note = s.get("note", "").strip()
                if note and y1 - y0 >= 34:
                    text += f"\n{note}"
                cv.create_text(x0 + 8, y0 + 4, text=text, font=("Segoe UI", 9),
                                fill="white", anchor="nw")

        cv.configure(scrollregion=(0, 0, canvas_w, canvas_h))

        def on_double_click(event):
            cx, cy = cv.canvasx(event.x), cv.canvasy(event.y)
            if not (x0 <= cx <= x1):
                return
            for by0, by1, s in blocks:
                if by0 <= cy <= by1:
                    new_note = self._prompt_note(s.get("note", ""))
                    if new_note is not None:
                        s["note"] = new_note
                        save_sessions(self.sessions)
                        self._open_day(d)  # re-render this day so the new note shows up
                    break

        cv.bind("<Double-Button-1>", on_double_click)


def main():
    root = tk.Tk()
    FocusTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
