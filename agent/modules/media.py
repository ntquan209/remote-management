"""
Media Module - Quản lý đa phương tiện trên máy trạm

📌 CHỨC NĂNG:
- Chụp ảnh màn hình (take_screenshot)
- Chụp khung hình từ webcam (get_webcam_frame)
- Stream màn hình thời gian thực (start_screen_stream)

🔁 LUỒNG HOẠT ĐỘNG:
1. Agent nhận lệnh "take_screenshot" từ backend
2. Gọi media_manager.take_screenshot()
3. Kết quả (bytes ảnh PNG) được chuyển về hex string
4. Gửi lại backend qua send_message("screenshot", {"data": hex_data})

🛠️ CÔNG NGHỆ:
- pyautogui: Chụp ảnh màn hình (chụp toàn bộ màn hình desktop)
- opencv (cv2): Đọc khung hình từ webcam
- Pillow (PIL): Xử lý và lưu ảnh dưới dạng bytes
"""

import cv2
import pyautogui
import io
from typing import Optional


class MediaManager:
    """Quản lý các thao tác đa phương tiện"""
    
    @staticmethod
    def take_screenshot() -> Optional[bytes]:
        """
        Chụp ảnh màn hình desktop
        
        Returns:
            Ảnh dạng bytes (định dạng PNG), None nếu lỗi
        
        Quá trình:
        1. pyautogui.screenshot() chụp toàn bộ màn hình
        2. Lưu vào BytesIO dưới dạng PNG
        3. Trả về bytes để gửi qua WebSocket
        """
        try:
            # Chụp màn hình
            screenshot = pyautogui.screenshot()
            # Chuyển đổi sang bytes
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr.getvalue()
        except Exception as e:
            print(f"Lỗi chụp màn hình: {e}")
            return None
    
    @staticmethod
    def get_webcam_frame() -> Optional[bytes]:
        """
        Chụp một khung hình từ webcam
        
        Returns:
            Khung hình dạng bytes (định dạng JPEG), None nếu lỗi
        
        Quá trình:
        1. Mở camera số 0 (webcam mặc định) bằng OpenCV
        2. Đọc một khung hình (cap.read())
        3. Giải phóng camera ngay sau khi đọc
        4. Mã hóa khung hình sang JPEG bytes
        """
        try:
            # Mở webcam
            cap = cv2.VideoCapture(0)
            # Đọc một khung hình
            ret, frame = cap.read()
            # Giải phóng camera ngay lập tức
            cap.release()
            
            if ret:
                # Mã hóa sang JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                return buffer.tobytes()
            return None
        except Exception as e:
            print(f"Lỗi webcam: {e}")
            return None
    
    @staticmethod
    def start_screen_stream(fps: int = 15):
        """
        Stream màn hình thời gian thực (generator)
        
        Args:
            fps: Số khung hình mỗi giây (mặc định 15)
        
        Yields:
            Dữ liệu khung hình (bytes PNG)
        
        Hoạt động như một generator (yield thay vì return):
        - Mỗi lần yield trả về một khung hình màn hình
        - Vòng lặp while True chụp liên tục
        - Dừng khi có exception (ngắt kết nối)
        """
        try:
            while True:
                screenshot = MediaManager.take_screenshot()
                if screenshot:
                    yield screenshot
        except Exception as e:
            print(f"Lỗi stream: {e}")


# Global instance
media_manager = MediaManager()