"""
keylogger.py - Ethical Keylogger with SANDBOX mode
Chi ghi nhan phim khi cua so thuc hanh dang focus
Khong ghi nhan ngoai vung thuc hanh (mat khau, info ca nhan)
"""
import threading, time
from pynput import keyboard
from modules.window_monitor import get_active_window

# TKINTER OPTIONAL (headless-safe)
TK_AVAILABLE = False
try:
    import tkinter as tk
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False
    print("[KEYLOGGER] tkinter khong kha dung -> HEADLESS mode (khong GUI)")

# === SANDBOX DEFINITIONS ===
SANDBOX_PROCESS_NAMES = [
    "gnome-terminal","konsole","xfce4-terminal","lxterminal",
    "xterm","uxterm","terminator","tilix","alacritty",
    "kitty","st","mate-terminal","sakura","termite",
    "wezterm","windows-terminal","cmd.exe","powershell.exe","wt.exe",
    "mousepad","gedit","nano","vim","nvim","gvim",
    "code","code-insiders","sublime_text","subl",
    "geany","leafpad","pluma","kate","kedit",
    "notepad.exe","notepad++.exe",
    "codeblocks","eclipse","netbeans","pycharm",
    "thonny","idle","spyder","geany",
]
SANDBOX_TITLE_KEYWORDS = [
    "lab","practice","thuc hanh","bai tap","exercise",
    "network","mang","routing","config","cau hinh",
    "terminal","bash","shell","command","kali",
    "cisco","packet tracer","wireshark","nmap",
    "assignment","project","lap trinh",
    "python","java","c++","html","javascript",
    "sql","database","co so du lieu",
    "root@","student@","kali@",
]
BLOCKED_TITLE_KEYWORDS = [
    "login","password","mat khau","dang nhap","sign in",
    "banking","facebook","zalo","messenger","chat","gmail",
    "mail","email","social","mang xa hoi",
    "otp","2fa","authenticator","xac thuc",
]
BROWSER_NAMES = ["firefox","firefox-esr","chromium","chromium-browser",
                 "google-chrome","chrome","microsoft-edge","edge",
                 "opera","brave","vivaldi"]
SANDBOX_CHECK_INTERVAL = 0.5

# === GLOBAL STATE ===
keylogger_capturing = False
keylogger_listener = None
_sandbox_active = False
_last_sandbox_status = None
root_app = None
gui_ready_event = threading.Event()
_enqueue_func = None
_ws_ref = None
_lbl_status = None
_sandbox_checker_running = False

# === SANDBOX CHECKER ===
def _check_active_window():
    title, proc_name = get_active_window()
    if not title and not proc_name:
        return False, "Khong xac dinh duoc cua so"
    tl = (title or "").lower()
    pl = (proc_name or "").lower()
    for kw in BLOCKED_TITLE_KEYWORDS:
        if kw in tl: return False, f"Chan: {kw}"
    if pl in SANDBOX_PROCESS_NAMES:
        if pl in BROWSER_NAMES:
            for kw in SANDBOX_TITLE_KEYWORDS:
                if kw in tl: return True, f"Browser [{proc_name}]"
            return False, "Browser - ngoai vung"
        return True, f"Sandbox [{proc_name}]"
    for kw in SANDBOX_TITLE_KEYWORDS:
        if kw in tl: return True, f"Title: {kw}"
    return False, f"Ngoai [{proc_name or '?'}]"

def _update_gui_status(text, color="#fef08a"):
    if TK_AVAILABLE and root_app and _lbl_status:
        try: root_app.after(0, lambda: _lbl_status.config(text=text, fg=color))
        except: pass

def _notify_sandbox_status():
    global _sandbox_active, _last_sandbox_status
    in_sbox, reason = _check_active_window()
    _sandbox_active = in_sbox
    if in_sbox != _last_sandbox_status:
        _last_sandbox_status = in_sbox
        s = "ACTIVE" if in_sbox else "INACTIVE"
        print(f"[SANDBOX] {s} - {reason}")
        _update_gui_status("Dang ghi nhan" if in_sbox else "Tam dung",
                          "#86efac" if in_sbox else "#fef08a")
        if _enqueue_func:
            _enqueue_func({"command":"agent_send_sandbox_status",
                           "sandbox_active":in_sbox,"reason":reason})

def _sandbox_checker_loop():
    global _sandbox_checker_running
    _sandbox_checker_running = True
    _notify_sandbox_status()
    while keylogger_capturing and _sandbox_checker_running:
        _notify_sandbox_status()
        time.sleep(SANDBOX_CHECK_INTERVAL)
    _sandbox_checker_running = False


# ============================================
# 🎯 PUBLIC API - Các hàm được agent.py import
# ============================================

def configure_keylogger(enqueue_func, ws_ref_container):
    """
    Lưu tham chiếu đến hàm enqueue và ws_ref container.
    Gọi một lần khi khởi tạo agent.
    
    Args:
        enqueue_func: Hàm enqueue_send (thread-safe, chỉ put vào queue)
        ws_ref_container: list[WebSocketApp | None] - mutable container
    """
    global _enqueue_func, _ws_ref
    _enqueue_func = enqueue_func
    _ws_ref = ws_ref_container
    print("[KEYLOGGER] Da nhan tham chieu enqueue_func va ws_ref")


def start_keylogger_module(ws, machine_name):
    """
    Bắt đầu ghi nhận phím bấm với cơ chế sandbox.
    Chạy pynput listener trong luồng riêng.
    
    Args:
        ws: WebSocketApp instance (có thể dùng để gửi trực tiếp, nhưng khuyên dùng enqueue)
        machine_name: Tên máy agent
    """
    global keylogger_capturing, keylogger_listener, _sandbox_checker_running

    if keylogger_capturing:
        print("[KEYLOGGER] Dang ghi nhan roi, bo qua start")
        return

    keylogger_capturing = True
    print(f"[KEYLOGGER] === BAT DAU GHIH NHAN PHIM (SANDBOX MODE) ===")

    def on_press(key):
        """Callback khi co phim duoc nhan."""
        if not keylogger_capturing:
            return False  # Stop listener

        # Chi gui du lieu neu dang o trong sandbox
        if not _sandbox_active:
            return

        try:
            key_str = str(key)
            # Lam sach gia tri phim
            if hasattr(key, 'char') and key.char is not None:
                key_str = key.char
            elif hasattr(key, 'name'):
                key_str = f'[{key.name}]'
            else:
                key_str = str(key)

            # Bo qua phim dieu khien thuong nhu Shift, Ctrl, Alt...
            control_keys = ['Key.shift', 'Key.ctrl_l', 'Key.ctrl_r',
                            'Key.alt_l', 'Key.alt_r', 'Key.cmd',
                            'Key.caps_lock', 'Key.num_lock', 'Key.scroll_lock']
            if key_str in control_keys:
                return

            # Gui qua enqueue (thread-safe)
            print(f"[KEYLOGGER] Phim nhan duoc: {key_str} (sandbox={_sandbox_active}, enqueue={_enqueue_func is not None})")
            if _enqueue_func:
                _enqueue_func({
                    "command": "agent_send_key",
                    "machine_name": machine_name,
                    "key": key_str
                })
        except Exception as e:
            print(f"[KEYLOGGER] Loi xu ly phim: {e}")

    # Khoi tao pynput listener
    try:
        keylogger_listener = keyboard.Listener(on_press=on_press)
        keylogger_listener.start()
        print("[KEYLOGGER] pynput listener da khoi dong")
    except Exception as e:
        print(f"[KEYLOGGER] LOI khoi tao pynput listener: {e}")
        keylogger_capturing = False
        return

    # Chay sandbox checker trong luong rieng
    sandbox_thread = threading.Thread(target=_sandbox_checker_loop,
                                       name="sandbox-checker",
                                       daemon=True)
    sandbox_thread.start()


def stop_keylogger_module():
    """Dung ghi nhan phim bam va giai phong tai nguyen."""
    global keylogger_capturing, keylogger_listener, _sandbox_checker_running

    if not keylogger_capturing:
        return

    print("[KEYLOGGER] === DUNG GHI NHAN PHIM ===")
    keylogger_capturing = False
    _sandbox_checker_running = False
    _last_sandbox_status = None

    # Dung listener
    if keylogger_listener is not None:
        try:
            keylogger_listener.stop()
        except Exception as e:
            print(f"[KEYLOGGER] Loi dung listener: {e}")
        keylogger_listener = None

    print("[KEYLOGGER] Da dung ghi nhan phim")

