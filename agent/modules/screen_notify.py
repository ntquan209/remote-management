import threading
import tkinter as tk
from tkinter import font as tkfont

_root = None
_label = None
_tk_thread = None
_warning_active = False

BANNER_WIDTH = 320
BANNER_HEIGHT = 60
MARGIN_RIGHT = 20
MARGIN_TOP = 20

WARNING_TEXT = "MÀN HÌNH ĐANG BỊ QUẢN LÝ"
BG_COLOR = "#cc0000"
FG_COLOR = "#ffffff"

def _create_window():
    global _root, _label
    _root = tk.Tk()
    _root.title("Monitoring Warning")
    _root.overrideredirect(True)
    _root.attributes('-topmost', True)
    _root.attributes('-alpha', 0.92)

    screen_width = _root.winfo_screenwidth()
    screen_height = _root.winfo_screenheight()
    x_pos = screen_width - BANNER_WIDTH - MARGIN_RIGHT
    y_pos = MARGIN_TOP
    _root.geometry(f"{BANNER_WIDTH}x{BANNER_HEIGHT}+{x_pos}+{y_pos}")
    _root.configure(bg="#880000")

    container = tk.Frame(_root, bg="#880000")
    container.pack(fill="both", expand=True, padx=2, pady=2)

    _label = tk.Label(
        container,
        text=WARNING_TEXT,
        font=("DejaVu Sans", 9, "bold"),
        bg=BG_COLOR,
        fg=FG_COLOR,
        padx=10,
        pady=8,
        wraplength=BANNER_WIDTH - 24,
        justify="center"
    )
    _label.pack(fill="both", expand=True)
    _root.resizable(False, False)
    _root.withdraw()

def _tk_loop():
    _create_window()
    _root.mainloop()

def show_warning():
    global _tk_thread, _warning_active
    if _warning_active:
        return
    _warning_active = True
    if _tk_thread is None or not _tk_thread.is_alive():
        _tk_thread = threading.Thread(target=_tk_loop, name="tk-warning", daemon=True)
        _tk_thread.start()
        while _root is None:
            import time
            time.sleep(0.05)
        while not _root.winfo_exists():
            import time
            time.sleep(0.05)
    _root.after(0, _show_window)

def _show_window():
    global _warning_active
    if _root and _warning_active:
        _root.deiconify()
        _root.lift()
        _root.attributes('-topmost', True)

def hide_warning():
    global _warning_active
    _warning_active = False
    if _root and _root.winfo_exists():
        try:
            _root.after(0, _root.withdraw)
        except Exception:
            pass

def update_warning_text(text: str):
    global _label, _warning_active
    if _label and _warning_active:
        try:
            _root.after(0, lambda: _label.config(text=text))
        except Exception:
            pass

def destroy():
    global _root, _tk_thread, _warning_active
    _warning_active = False
    if _root and _root.winfo_exists():
        try:
            _root.after(0, _root.destroy)
        except Exception:
            pass
    if _tk_thread and _tk_thread.is_alive():
        _tk_thread.join(timeout=2)
    _root = None
    _tk_thread = None