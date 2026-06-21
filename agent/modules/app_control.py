import subprocess
import os

# Khóa cứng danh mục ứng dụng an toàn cấu hình từ trước
WHITELIST_APPS = ["firefox", "mousepad", "thunar", "ristretto"]

def manage_application(action, app_name):
    """Khởi chạy hoặc cưỡng bức tắt phần mềm trong Whitelist"""
    if app_name not in WHITELIST_APPS:
        print(f"⚠️ [WARNING] Từ chối thao tác: {app_name} không nằm trong danh mục Whitelist!")
        return False
        
    try:
        if action == "START":
            print(f"🚀 [APPS] Khởi chạy ứng dụng: {app_name}")
            # Chuyển hướng đầu ra vào DEVNULL để chạy ngầm hoàn toàn độc lập, không block luồng mạng
            subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif action == "STOP":
            print(f"🛑 [APPS] Cưỡng bức đóng toàn bộ tiến trình: {app_name}")
            os.system(f"pkill -f {app_name}")
            return True
    except Exception as e:
        print(f"❌ Lỗi xử lý ứng dụng {app_name}: {e}")
    return False
