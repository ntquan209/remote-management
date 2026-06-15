import io
import base64
import mss
from PIL import Image

def capture_screen_to_base64():
    """Chụp màn hình siêu tốc bằng phần cứng, hạ độ phân giải và nén JPEG 45%"""
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1] # Màn hình chính
            sct_img = sct.grab(monitor)
            
            # Chuyển raw bytes của mss sang PIL Image để tiến hành nén
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img = img.resize((960, 540), Image.Resampling.LANCZOS) # Hạ phân giải xuống 540p cho nhẹ mạng
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=45) # Giữ chất lượng 45% để đạt 30 FPS mượt mà
            
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"❌ Lỗi khi chụp màn hình: {e}")
        return None