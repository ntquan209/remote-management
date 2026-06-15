import json
import time
import threading
import websocket # Thư viện kết nối WebSocket thuần

# Import các hàm chức năng từ thư mục con modules/
from modules.system import get_process_list, kill_process_by_pid, execute_power_cmd
from modules.media import capture_screen_to_base64

MACHINE_NAME = 'Kali_Lab_01'
is_streaming_screen = False

def screen_stream_worker(ws):
    """Luồng phụ (Worker Thread) chạy song song chuyên gửi ảnh 30 FPS"""
    global is_streaming_screen
    print("🚀 Bắt đầu luồng Live Stream màn hình mượt mà (30 FPS)...")
    
    TARGET_FPS = 30
    FRAME_INTERVAL = 1.0 / TARGET_FPS

    while is_streaming_screen:
        start_time = time.time()
        
        base64_image = capture_screen_to_base64()
        if base64_image:
            payload = {
                "event": "agent_send_screen",
                "machine_name": MACHINE_NAME,
                "image_base64": base64_image
            }
            try:
                ws.send(json.dumps(payload))
            except:
                break # Đứt kết nối thì thoát luồng
                
        # Trừ hao thời gian xử lý ảnh để giữ chuẩn FPS ổn định
        elapsed_time = time.time() - start_time
        sleep_time = FRAME_INTERVAL - elapsed_time
        if sleep_time > 0:
            time.sleep(sleep_time)
            
    print("🛑 Đã dừng luồng Live Stream màn hình.")

def on_message(ws, message):
    """Lắng nghe lệnh từ FastAPI Backend dội xuống"""
    global is_streaming_screen
    try:
        data = json.loads(message)
        action = data.get('action')
        detail = data.get('detail')
        print(f"🎮 Nhận lệnh từ Server FastAPI: [{action}] - Chi tiết: [{detail}]")

        if action == 'START_STREAM':
            if not is_streaming_screen:
                is_streaming_screen = True
                # Kích hoạt luồng phụ xử lý ảnh để không làm đơ kết nối chính
                threading.Thread(target=screen_stream_worker, args=(ws,), daemon=True).start()
                
        elif action == 'STOP_STREAM':
            is_streaming_screen = False
            
        elif action == 'SCREENSHOT':
            base64_image = capture_screen_to_base64()
            if base64_image:
                ws.send(json.dumps({
                    "event": "agent_send_screen",
                    "machine_name": MACHINE_NAME,
                    "image_base64": base64_image
                }))
                print("📸 Đã phản hồi ảnh chụp màn hình đơn lẻ.")

        elif action == 'KILL_PROCESS':
            pid = int(detail.split()[1])
            if kill_process_by_pid(pid):
                print(f"✅ Đã kill thành công PID {pid}. Gửi lại list process mới...")
                ws.send(json.dumps({
                    "event": "agent_send_procs",
                    "machine_name": MACHINE_NAME,
                    "processes": get_process_list()
                }))
                
        elif action in ['SHUTDOWN', 'RESTART']:
            execute_power_cmd(action)
            
    except Exception as e:
        print(f"❌ Lỗi xử lý bản tin lệnh: {e}")

def on_open(ws):
    print(f"✅ [CONNECTED] Đã thông nòng WebSocket tới FastAPI! Tên máy: {MACHINE_NAME}")
    # Đăng ký định danh máy trạm ngay khi vừa mở cổng kết nối thành công
    ws.send(json.dumps({"event": "agent_register", "machine_name": MACHINE_NAME}))

def on_close(ws, close_status_code, close_msg):
    global is_streaming_screen
    is_streaming_screen = False
    print("❌ [DISCONNECTED] Mất kết nối tới Server Backend.")

if __name__ == '__main__':
    # URL kết nối WebSocket khớp định dạng cấu hình của Backend FastAPI (Cổng 8000)
    # LƯU Ý: Nếu chạy máy ảo Kali, đổi 'localhost' thành IP máy Windows của bạn bạn nhé
    BACKEND_WS_URL = f"ws://localhost:8000/ws/agent/{MACHINE_NAME}"
    
    ws_client = websocket.WebSocketApp(
        BACKEND_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close
    )
    
    # Tạo một luồng chạy ngầm độc lập gửi thông số Task Manager định kỳ (5 giây / lần)
    def sys_monitor_loop():
        while True:
            try:
                if ws_client.sock and ws_client.sock.connected:
                    ws_client.send(json.dumps({
                        "event": "agent_send_procs",
                        "machine_name": MACHINE_NAME,
                        "processes": get_process_list()
                    }))
            except: pass
            time.sleep(5)
            
    threading.Thread(target=sys_monitor_loop, daemon=True).start()
    
    # Bắt đầu kích hoạt lắng nghe WebSocket liên tục
    ws_client.run_forever()