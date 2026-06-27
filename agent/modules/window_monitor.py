"""
window_monitor.py - Phát hiện cửa sổ đang focus để hỗ trợ cơ chế sandbox keylogger

📌 CHỨC NĂNG:
- Phát hiện tên cửa sổ đang active trên hệ thống
- Hỗ trợ đa nền tảng: Linux (xdotool/xprop) và Windows (user32)
- Trả về (window_title, process_name) để keylogger kiểm tra sandbox

🔒 BẢO MẬT:
- Chỉ dùng để xác định cửa sổ thực hành, không capture nội dung
- Không lưu trữ hay gửi thông tin cửa sổ đi đâu
"""

import platform
import subprocess
import re

# Cache hệ điều hành để tránh gọi platform.system() nhiều lần
_OS_NAME = platform.system().lower()


# ============================================
# 🐧 LINUX: Dùng xdotool hoặc xprop
# ============================================
def _get_active_window_linux():
    """
    Lấy thông tin cửa sổ đang active trên Linux.
    Thử xdotool trước (nhanh), fallback sang xprop (có sẵn trên Kali).
    Trả về (window_title, process_name) hoặc (None, None).
    """
    title = None
    proc_name = None

    # Cách 1: xdotool (nếu được cài)
    try:
        win_id = subprocess.check_output(
            ["xdotool", "getactivewindow"],
            stderr=subprocess.DEVNULL, timeout=1
        ).strip()

        title = subprocess.check_output(
            ["xdotool", "getwindowname", win_id],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode("utf-8", errors="replace").strip()

        # Lấy PID rồi suy ra tên tiến trình
        pid = subprocess.check_output(
            ["xdotool", "getwindowpid", win_id],
            stderr=subprocess.DEVNULL, timeout=1
        ).strip()
        proc_name = _pid_to_name(pid)
        return title, proc_name
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    # Cách 2: xprop (có sẵn trên Kali/Ubuntu)
    try:
        output = subprocess.check_output(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode("utf-8", errors="replace").strip()
        match = re.search(r'window id # (0x[0-9a-fA-F]+)', output)
        if not match:
            match = re.search(r'#\s*(0x[0-9a-fA-F]+)', output)
        if match:
            win_id = match.group(1).strip()
            # Lấy tên cửa sổ
            name_out = subprocess.check_output(
                ["xprop", "-id", win_id, "WM_NAME"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode("utf-8", errors="replace").strip()
            title_match = re.search(r'WM_NAME\([^)]+\)\s*=\s*"(.+)"', name_out)
            if title_match:
                title = title_match.group(1)

            # Lấy PID của cửa sổ
            pid_out = subprocess.check_output(
                ["xprop", "-id", win_id, "_NET_WM_PID"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode("utf-8", errors="replace").strip()
            pid_match = re.search(r'_NET_WM_PID\([^)]+\)\s*=\s*(\d+)', pid_out)
            if pid_match:
                pid = pid_match.group(1)
                proc_name = _pid_to_name(pid)

        return title, proc_name
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    return None, None


# ============================================
# 🪟 WINDOWS: Dùng ctypes + user32
# ============================================
def _get_active_window_windows():
    """
    Lấy thông tin cửa sổ đang active trên Windows.
    Dùng ctypes để gọi user32 API.
    Trả về (window_title, process_name) hoặc (None, None).
    """
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        # Lấy handle của foreground window
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, None

        # Lấy tiêu đề cửa sổ
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buffer, length)
        title = buffer.value.strip()

        # Lấy PID từ handle
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = _pid_to_name(str(pid.value))

        return title, proc_name
    except Exception:
        return None, None


# ============================================
# 🔧 UTILITY: PID -> Tên tiến trình
# ============================================
def _pid_to_name(pid_str):
    """Chuyển PID thành tên tiến trình dùng psutil (nếu có) hoặc fallback OS."""
    try:
        import psutil
        pid_int = int(pid_str)
        if psutil.pid_exists(pid_int):
            proc = psutil.Process(pid_int)
            return proc.name().lower()
    except (ImportError, ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return None


# ============================================
# 🎯 API CHÍNH
# ============================================
def get_active_window():
    """
    Lấy thông tin cửa sổ đang active trên hệ thống.

    Returns:
        tuple: (window_title: str | None, process_name: str | None)
    """
    if _OS_NAME == "linux":
        return _get_active_window_linux()
    elif _OS_NAME == "windows":
        return _get_active_window_windows()
    return None, None


# ============================================
# 🧪 TEST
# ============================================
if __name__ == "__main__":
    title, proc = get_active_window()
    print(f"🧪 Active Window: title='{title}', process='{proc}'")
