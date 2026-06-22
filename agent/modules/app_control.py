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
            
            if app_name == "thunar":
                # SỬA LỖI: Dùng pkill -x (khớp chính xác tên) để dọn dẹp trước ẩn danh, tránh giết nhầm Agent
                subprocess.Popen("pkill -x thunar > /dev/null 2>&1", shell=True).wait()
                # Khởi chạy phi đồng bộ bằng shell ngầm
                subprocess.Popen("thunar > /dev/null 2>&1 &", shell=True)
            elif app_name == "firefox":
                os.system("rm -f ~/.mozilla/firefox/*.default-esr/.parentlock > /dev/null 2>&1")
                os.system("rm -f ~/.mozilla/firefox/*.default/.parentlock > /dev/null 2>&1")
                subprocess.Popen("firefox > /dev/null 2>&1 &", shell=True)
            else:
                subprocess.Popen(f"{app_name} > /dev/null 2>&1 &", shell=True)
            return True
            
        elif action == "STOP":
            print(f"🛑 [APPS] Cưỡng bức đóng toàn bộ tiến trình: {app_name}")
            
            if app_name == "thunar":
                # SỬA LỖI: Gọi thunar -q để đóng chuẩn GUI, sau đó dùng pkill -x để thanh trừng chính xác tiến trình tên 'thunar'
                # Tuyệt đối không dùng -f để tránh quét trúng các câu lệnh có chứa chữ thunar làm chết Agent
                subprocess.Popen("thunar -q > /dev/null 2>&1; pkill -9 -x thunar", shell=True)
            elif app_name == "firefox":
                subprocess.Popen("pkill -9 -f firefox; sleep 0.2; rm -f ~/.mozilla/firefox/*.default-esr/.parentlock; rm -f ~/.mozilla/firefox/*.default/.parentlock", shell=True)
            else:
                subprocess.Popen(f"pkill -9 -x {app_name}", shell=True)
            return True
            
    except Exception as e:
        print(f"❌ Lỗi xử lý ứng dụng {app_name}: {e}")
    return False
