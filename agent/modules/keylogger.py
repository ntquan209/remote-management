import threading, time
from pynput import keyboard
from modules.window_monitor import get_active_window

TK_AVAILABLE = False
try:
    import tkinter as tk
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

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

def configure_keylogger(enqueue_func, ws_ref_container):
    global _enqueue_func, _ws_ref
    _enqueue_func = enqueue_func
    _ws_ref = ws_ref_container

def start_keylogger_module(ws, machine_name):
    global keylogger_capturing, keylogger_listener, _sandbox_checker_running

    if keylogger_capturing:
        return

    keylogger_capturing = True

    def on_press(key):
        if not keylogger_capturing:
            return False
        if not _sandbox_active:
            return

        try:
            key_str = str(key)
            if hasattr(key, 'char') and key.char is not None:
                key_str = key.char
            elif hasattr(key, 'name'):
                key_str = f'[{key.name}]'
            else:
                key_str = str(key)

            # Filter all modifier and system keys
            ignore_prefixes = [
                'Key.shift', 'Key.ctrl', 'Key.alt', 'Key.cmd',
                'Key.caps_lock', 'Key.num_lock', 'Key.scroll_lock',
                'Key.tab', 'Key.esc', 'Key.delete', 'Key.insert',
                'Key.home', 'Key.end', 'Key.page_up', 'Key.page_down',
                'Key.menu', 'Key.print_screen', 'Key.pause',
                'Key.up', 'Key.down', 'Key.left', 'Key.right',
                'Key.f1', 'Key.f2', 'Key.f3', 'Key.f4', 'Key.f5', 'Key.f6',
                'Key.f7', 'Key.f8', 'Key.f9', 'Key.f10', 'Key.f11', 'Key.f12',
            ]
            if any(key_str.startswith(p) for p in ignore_prefixes):
                return

            if _enqueue_func:
                _enqueue_func({
                    "command": "agent_send_key",
                    "machine_name": machine_name,
                    "key": key_str
                })
        except Exception:
            pass

    try:
        keylogger_listener = keyboard.Listener(on_press=on_press)
        keylogger_listener.start()
    except Exception as e:
        keylogger_capturing = False
        return

    sandbox_thread = threading.Thread(target=_sandbox_checker_loop,
                                       name="sandbox-checker",
                                       daemon=True)
    sandbox_thread.start()

def stop_keylogger_module():
    global keylogger_capturing, keylogger_listener, _sandbox_checker_running

    if not keylogger_capturing:
        return

    keylogger_capturing = False
    _sandbox_checker_running = False
    _last_sandbox_status = None

    if keylogger_listener is not None:
        try:
            keylogger_listener.stop()
        except Exception:
            pass
        keylogger_listener = None