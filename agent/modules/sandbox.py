import os
import base64

SANDBOX_DIR = "/home/kali/Downloads"

def get_sandbox_files():
    """Đọc cấu trúc danh sách tệp tin trong vùng an toàn chỉ định"""
    file_list = []
    try:
        # Nếu thư mục chưa tồn tại thì tự động khởi tạo
        if not os.path.exists(SANDBOX_DIR):
            os.makedirs(SANDBOX_DIR)
            
        for entry in os.scandir(SANDBOX_DIR):
            try:
                stat_info = entry.stat()
                # Định dạng dung lượng tệp tin trực quan
                size_kb = round(stat_info.st_size / 1024, 1)
                size_str = f"{size_kb} KB" if size_kb > 0 else "0 KB"
                if stat_info.st_size > 1024 * 1024:
                    size_str = f"{round(size_kb / 1024, 1)} MB"
                    
                file_list.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": size_str if not entry.is_dir() else "-"
                })
            except Exception:
                pass
    except Exception as e:
        print(f"❌ Lỗi trích xuất File Sandbox: {e}")
    return file_list

def read_file_content(file_name):
    """
    Đọc tệp tin trong vùng an toàn, mã hóa sang Base64 dội ngược lại lên Web.
    Tích hợp bộ lọc bảo mật để tránh rò rỉ file hệ thống tối cao Linux.
    """
    # Ép buộc chỉ lấy tên file thuần, loại bỏ các ký tự độc hại điều hướng lùi như ../
    clean_name = os.path.basename(file_name)
    target_path = os.path.join(SANDBOX_DIR, clean_name)
    
    if not os.path.exists(target_path) or os.path.isdir(target_path):
        print(f"❌ [DOWNLOAD] Tệp tin không tồn tại hoặc là thư mục: {clean_name}")
        return None
        
    try:
        print(f"📦 [DOWNLOAD] Đang đọc và mã hóa tệp tin: {clean_name}")
        with open(target_path, "rb") as f:
            file_bytes = f.read()
            base64_data = base64.b64encode(file_bytes).decode('utf-8')
            return {
                "file_name": clean_name,
                "file_base64": base64_data
            }
    except Exception as e:
        print(f"❌ [DOWNLOAD] Lỗi đọc file {clean_name}: {e}")
        return None
