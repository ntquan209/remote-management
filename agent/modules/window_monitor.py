import platform
import subprocess
import re

_OS_NAME = platform.system().lower()

def _get_active_window_linux():
    title = None
    proc_name = None

    try:
        win_id = subprocess.check_output(
            ["xdotool", "getactivewindow"],
            stderr=subprocess.DEVNULL, timeout=1
        ).strip()
        title = subprocess.check_output(
            ["xdotool", "getwindowname", win_id],
            stderr=subprocess.DEVNULL, timeout=1
        ).decode("utf-8", errors="replace").strip()
        pid = subprocess.check_output(
            ["xdotool", "getwindowpid", win_id],
            stderr=subprocess.DEVNULL, timeout=1
        ).strip()
        proc_name = _pid_to_name(pid)
        return title, proc_name
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

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
            name_out = subprocess.check_output(
                ["xprop", "-id", win_id, "WM_NAME"],
                stderr=subprocess.DEVNULL, timeout=1
            ).decode("utf-8", errors="replace").strip()
            title_match = re.search(r'WM_NAME\([^)]+\)\s*=\s*"(.+)"', name_out)
            if title_match:
                title = title_match.group(1)
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

def _get_active_window_windows():
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, None
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buffer, length)
        title = buffer.value.strip()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = _pid_to_name(str(pid.value))
        return title, proc_name
    except Exception:
        return None, None

def _pid_to_name(pid_str):
    try:
        import psutil
        pid_int = int(pid_str)
        if psutil.pid_exists(pid_int):
            proc = psutil.Process(pid_int)
            return proc.name().lower()
    except (ImportError, ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return None

def get_active_window():
    if _OS_NAME == "linux":
        return _get_active_window_linux()
    elif _OS_NAME == "windows":
        return _get_active_window_windows()
    return None, None