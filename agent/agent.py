import json
import time
import threading
import websocket  # Thư viện kết nối WebSocket thuần

# Import các hàm chức năng từ thư mục con modules/
from modules.system import get_process_list, kill_process_by_pid, execute_power_cmd
from modules.media import capture_screen_to_base64

MACHINE_NAME = 'Kali_Lab_01'


def on_message(ws, message):
    """Lắng nghe lệnh điều khiển trực tiếp từ FastAPI Backend dội xuống"""
    try:
        data = json.loads(message)
        command = data.get('command')
        data_args = data.get('data', {})

        # 🎯 LUỒNG CHỤP MÀN HÌNH (STATIC & LIVE CHẠY CHUNG):
        # Vì Frontend tự lo vòng lặp (re-trigger), Agent cứ nhận lệnh 'take_screenshot' 
        # là âm thầm chụp đúng 1 tấm gửi về, không in log ra terminal để tránh bị tràn màn hình (loop log).
        if command == 'take_screenshot':
            base64_image = capture_screen_to_base64()
            if base64_image:
                payload = {
                    "command": "agent_send_screen",
                    "machine_name": MACHINE_NAME,
                    "image_base64": base64_image,
                    "is_static": True  # Giữ cờ hiệu để bộ lọc của monitor.js bóc tách đúng tab
                }
                ws.send(json.dumps(payload))
            return

        # 🎯 LUỒNG QUẢN LÝ TIẾN TRÌNH (TASK MANAGER):
        elif command == 'kill_process':
            print(f"📥 [COMMAND] Nhận lệnh kill tiến trình từ hệ thống.")
            pid = data_args.get('pid') if isinstance(data_args, dict) else None
            if pid:
                pid = int(pid)
                if kill_process_by_pid(pid):
                    print(f"✅ Đã kill thành công PID {pid}. Gửi lại danh sách tiến trình mới...")
                    ws.send(json.dumps({
                        "command": "agent_send_procs",
                        "machine_name": MACHINE_NAME,
                        "processes": get_process_list()
                    }))
            return

        # 🎯 LUỒNG ĐIỀU KHIỂN NGUỒN HỆ THỐNG:
        elif command in ['shutdown', 'restart']:
            print(f"⚠️ [POWER] Thực thi điều khiển nguồn: {command.upper()}")
            execute_power_cmd(command.upper())

    except Exception as e:
        print(f"❌ Lỗi xử lý hoặc phân tích bản tin JSON: {e}")


def on_open(ws):
    print(f"✅ [CONNECTED] Đã thông nòng kết nối WebSocket tới FastAPI! Tên máy: {MACHINE_NAME}")
    # Đăng ký định danh máy trạm với Server ngay khi mở cổng thành công
    ws.send(json.dumps({"event": "agent_register", "machine_name": MACHINE_NAME}))


def on_close(ws, close_status_code, close_msg):
    print("❌ [DISCONNECTED] Mất kết nối tới Server Backend.")


if __name__ == '__main__':
    # Đường dẫn IP mạng Wi-Fi/Host-only của máy Windows đang chạy FastAPI Backend
    BACKEND_WS_URL = f"ws://192.168.89.134:8000/ws/agent/{MACHINE_NAME}"

    ws_client = websocket.WebSocketApp(
        BACKEND_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close
    )

    # Luồng chạy ngầm độc lập gửi thông số Task Manager định kỳ (5 giây / lần)
    def sys_monitor_loop():
        while True:
            try:
                if ws_client.sock and ws_client.sock.connected:
                    ws_client.send(json.dumps({
                        "command": "agent_send_procs",
                        "machine_name": MACHINE_NAME,
                        "processes": get_process_list()
                    }))
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=sys_monitor_loop, daemon=True).start()

    # Kích hoạt duy trì lắng nghe cổng mạng liên tục từ WebSocket
    ws_client.run_forever()
