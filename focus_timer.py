r"""
时间记录器 (Time Tracker)
------------------------------------------------------------
一个极简、苹果风格的时间记录工具（Windows 桌面应用），分三类：
专注 / AI对话 / 看书。

用法：先在上面选一个分类，点一下圆形按钮开始记录，再点一下结束并保存。
不是倒计时——只是单纯地记录你花了多久。

依赖：仅使用 Python 标准库（tkinter），无需安装任何第三方包。
数据保存在：%APPDATA%\FocusTimer\sessions.json （Windows）
           ~/.focus_timer/sessions.json （其他系统，便于开发调试）
"""

import json
import os
import time
import tkinter as tk
from datetime import datetime

# ---------------------------------------------------------------- 配色 / 字体
# 整体基调偏暖、偏柔和，减少高饱和度色块，营造平和安静的感觉
BG = "#FAF6F1"           # 暖白色背景（而非冷调纯白/浅灰）
FG_PRIMARY = "#4A4644"    # 主文字（温润的深灰，而非纯黑）
FG_SECONDARY = "#ADA49B"  # 次要文字（暖灰）
CORAL = "#E3A296"         # 结束 - 柔和珊瑚色（三个分类通用的“停止”提示色）
CORAL_HALO = "#F8E8E3"
DIVIDER = "#ECE5DC"

FONT_TITLE = ("Segoe UI", 13)
FONT_TAB = ("Segoe UI", 12)
FONT_TIMER = ("Consolas", 38)
FONT_BUTTON = ("Segoe UI", 14)
FONT_STAT_NUM = ("Segoe UI", 19)
FONT_STAT_LABEL = ("Segoe UI", 11)
FONT_ROW = ("Segoe UI", 11)

# 三个分类：各自的名称 + 专属的柔和主题色（开始按钮 / 选中标签用）
CATEGORIES = [
    {"key": "focus", "label": "专注", "accent": "#93BFA3", "halo": "#E4EFE8"},
    {"key": "ai_chat", "label": "AI对话", "accent": "#96AFC9", "halo": "#E7ECF3"},
    {"key": "reading", "label": "看书", "accent": "#D9B47E", "halo": "#F6ECDA"},
]


def data_file_path() -> str:
    """返回保存记录的 JSON 文件路径，Windows 上放在 APPDATA 目录。"""
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


def fmt_duration_zh(seconds: int) -> str:
    total_min = max(1, round(seconds / 60))
    h, m = divmod(total_min, 60)
    if h:
        return f"{h}小时{m}分钟" if m else f"{h}小时"
    return f"{m}分钟"


class FocusTimerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("时间记录")
        self.root.configure(bg=BG)
        self.root.geometry("360x640")
        self.root.minsize(340, 480)
        self.root.resizable(True, True)  # 鼠标移到窗口边缘/角落即可拖拽缩放

        self.sessions = load_sessions()
        self.running = False
        self.start_time = None
        self._tick_job = None
        self.current_category = CATEGORIES[0]["key"]

        self._build_ui()
        self._select_category(self.current_category)

    # ------------------------------------------------------------ UI 构建
    def _build_ui(self):
        pad_x = 28

        tk.Label(self.root, text="时间记录", font=FONT_TITLE,
                 bg=BG, fg=FG_SECONDARY).pack(pady=(24, 12))

        # 分类切换（分段控件）
        tab_frame = tk.Frame(self.root, bg=BG)
        tab_frame.pack()
        self.tab_labels = {}
        for cat in CATEGORIES:
            lbl = tk.Label(tab_frame, text=cat["label"], font=FONT_TAB,
                            bg=BG, fg=FG_SECONDARY, padx=14, pady=6, cursor="hand2")
            lbl.pack(side="left", padx=4)
            lbl.bind("<Button-1>", lambda e, k=cat["key"]: self._select_category(k))
            self.tab_labels[cat["key"]] = lbl

        self.timer_label = tk.Label(self.root, text="00:00:00", font=FONT_TIMER,
                                     bg=BG, fg=FG_PRIMARY)
        self.timer_label.pack(pady=(18, 22))

        # 圆形开始/结束按钮，用 Canvas 手绘：外圈是浅色光晕，营造柔和感
        self.canvas_size = 150
        self.btn_diameter = 112
        self.canvas = tk.Canvas(self.root, width=self.canvas_size, height=self.canvas_size,
                                 bg=BG, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", lambda e: self.toggle())

        # 分割线
        tk.Frame(self.root, bg=DIVIDER, height=1).pack(fill="x", padx=pad_x, pady=(32, 18))

        # 今日统计
        stat_frame = tk.Frame(self.root, bg=BG)
        stat_frame.pack(fill="x", padx=pad_x)
        self.stat_label = tk.Label(stat_frame, font=FONT_STAT_LABEL, bg=BG, fg=FG_SECONDARY)
        self.stat_label.pack(side="left")
        self.total_label = tk.Label(stat_frame, font=FONT_STAT_NUM, bg=BG, fg=FG_PRIMARY)
        self.total_label.pack(side="right")

        tk.Label(self.root, text="今日记录", font=FONT_STAT_LABEL,
                 bg=BG, fg=FG_SECONDARY).pack(anchor="w", padx=pad_x, pady=(20, 6))

        # 今日记录列表
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

    # ------------------------------------------------------------ 分类切换
    def _select_category(self, key):
        if self.running:
            return  # 记录进行中不允许切换分类，避免时间记错类别
        self.current_category = key
        for cat in CATEGORIES:
            selected = cat["key"] == key
            self.tab_labels[cat["key"]].config(
                bg=cat["halo"] if selected else BG,
                fg=cat["accent"] if selected else FG_SECONDARY,
            )
        cat = self._category(key)
        self.timer_label.config(text="00:00:00")
        self._draw_button(cat["accent"], cat["halo"], "开始")
        self._refresh_history()

    # ------------------------------------------------------------ 计时逻辑
    def toggle(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.running = True
        self.start_time = time.time()
        self._draw_button(CORAL, CORAL_HALO, "结束")
        self._tick()

    def _stop(self):
        self.running = False
        if self._tick_job is not None:
            self.root.after_cancel(self._tick_job)
            self._tick_job = None

        duration = time.time() - self.start_time
        if duration >= 5:  # 忽略手滑点击造成的极短记录
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
        self._draw_button(cat["accent"], cat["halo"], "开始")
        self._refresh_history()

    def _tick(self):
        elapsed = time.time() - self.start_time
        self.timer_label.config(text=fmt_hms(elapsed))
        self._tick_job = self.root.after(1000, self._tick)

    # ------------------------------------------------------------ 历史记录
    def _refresh_history(self):
        today = datetime.now().date()
        label = self._category(self.current_category)["label"]
        todays = [s for s in self.sessions
                  if s.get("category", "focus") == self.current_category
                  and datetime.fromisoformat(s["start"]).date() == today]

        total_sec = sum(s["duration_sec"] for s in todays)
        self.stat_label.config(text=f"今日{label}")
        self.total_label.config(text=fmt_duration_zh(total_sec) if total_sec else "0分钟")

        self.history_list.delete(0, "end")
        for s in reversed(todays):
            start = datetime.fromisoformat(s["start"])
            end = datetime.fromisoformat(s["end"])
            row = f"  {start:%H:%M} - {end:%H:%M}      {fmt_duration_zh(s['duration_sec'])}"
            self.history_list.insert("end", row)

        if not todays:
            self.history_list.insert("end", f"  还没有{label}记录，点击上方按钮开始吧")


def main():
    root = tk.Tk()
    FocusTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
