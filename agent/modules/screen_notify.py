"""
screen_notify.py - Cảnh báo nổi góc phải màn hình khi đang bị quản lý

Sử dụng Tkinter (có sẵn trong Python) để tạo cửa sổ luôn nổi trên cùng,
hiển thị thông báo đỏ cảnh báo sinh viên rằng màn hình đang bị giám sát.

Luồng hoạt động:
  - Thread riêng chạy Tkinter mainloop
  - show_warning() -> hiện banner đỏ góc phải
  - hide_warning() -> ẩn banner
"""

import threading
import tkinter as tk
from tkinter import font as tkfont

# ============================================
# Biến toàn cục
# ============================================
_root = None           # Tkinter root window
_label = None          # Label widget hiển thị cảnh báo
_tk_thread = None      # Thread chạy Tkinter mainloop
_warning_active = False

# Kích thước & vị trí banner
BANNER_WIDTH = 320
BANNER_HEIGHT = 60
MARGIN_RIGHT = 20
MARGIN_TOP = 20

# Nội dung cảnh báo
WARNING_TEXT = "MÀN HÌNH ĐANG BỊ QUẢN LÝ"
WARNING_TEXT_EN = "SCREEN BEING MONITORED"
BG_COLOR = "#cc0000"        # Đỏ cảnh báo
FG_COLOR = "#ffffff"        # Chữ trắng


def _create_window():
    """Tạo cửa sổ Tkinter không viền, luôn trên cùng, góc phải màn hình"""
    global _root, _label

    _root = tk.Tk()
    _root.title("Monitoring Warning")
    _root.overrideredirect(True)           # Không có viền/titlebar
    _root.attributes('-topmost', True)     # Luôn trên cùng
    _root.attributes('-alpha', 0.92)       # Hơi trong suốt

    # Lấy kích thước màn hình
    screen_width = _root.winfo_screenwidth()
    screen_height = _root.winfo_screenheight()

    # Tính vị trí góc phải phía trên
    x_pos = screen_width - BANNER_WIDTH - MARGIN_RIGHT
    y_pos = MARGIN_TOP
    _root.geometry(f"{BANNER_WIDTH}x{BANNER_HEIGHT}+{x_pos}+{y_pos}")

    # Khung chứa có viền đỏ đậm (border 2px)
    _root.configure(bg="#880000")
    container = tk.Frame(_root, bg="#880000")
    container.pack(fill="both", expand=True, padx=2, pady=2)

    # Label cảnh báo bên trong khung
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

    # Ẩn ban đầu
    _root.withdraw()


def _tk_loop():
    """Thread worker: chạy Tkinter mainloop"""
    _create_window()
    _root.mainloop()


def show_warning():
    """Hiển thị banner cảnh báo góc phải màn hình"""
    global _tk_thread, _warning_active

    if _warning_active:
        return  # Đã hiển thị rồi

    _warning_active = True

    if _tk_thread is None or not _tk_thread.is_alive():
        _tk_thread = threading.Thread(target=_tk_loop, name="tk-warning", daemon=True)
        _tk_thread.start()
        # Đợi đến khi cửa sổ được tạo
        while _root is None:
            import time
            time.sleep(0.05)
        while not _root.winfo_exists():
            import time
            time.sleep(0.05)

    # Hiện cửa sổ (cả lần đầu và các lần sau)
    _root.after(0, _show_window)


def _show_window():
    """Hiện cửa sổ (gọi từ thread Tkinter)"""
    global _warning_active
    if _root and _warning_active:
        _root.deiconify()
        _root.lift()
        _root.attributes('-topmost', True)


def hide_warning():
    """Ẩn banner cảnh báo"""
    global _warning_active
    _warning_active = False
    if _root and _root.winfo_exists():
        try:
            _root.after(0, _root.withdraw)
        except Exception:
            pass


def update_warning_text(text: str):
    """Cập nhật nội dung cảnh báo (gọi từ bất kỳ thread nào)"""
    global _label, _warning_active
    if _label and _warning_active:
        try:
            _root.after(0, lambda: _label.config(text=text))
        except Exception:
            pass


def destroy():
    """Hủy toàn bộ cửa sổ Tkinter (khi agent thoát)"""
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


if __name__ == "__main__":
    # Test thử
    import time
    print("🧪 Test screen_notify: hiển thị cảnh báo 5 giây...")
    show_warning()
    time.sleep(5)
    print("🧪 Ẩn cảnh báo...")
    hide_warning()
    time.sleep(1)
    destroy()
    print("🧪 OK")
