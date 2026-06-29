import os
import base64

SANDBOX_DIR = f"/home/{os.environ.get('USER', 'kali')}/Downloads"

def get_sandbox_files():
    file_list = []
    try:
        if not os.path.exists(SANDBOX_DIR):
            os.makedirs(SANDBOX_DIR)
            return file_list
        for entry in os.scandir(SANDBOX_DIR):
            try:
                stat_info = entry.stat()
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
    except Exception:
        pass
    return file_list

def read_file_content(file_name):
    clean_name = os.path.basename(file_name)
    target_path = os.path.join(SANDBOX_DIR, clean_name)
    if not os.path.exists(target_path) or os.path.isdir(target_path):
        return None
    try:
        with open(target_path, "rb") as f:
            file_bytes = f.read()
            base64_data = base64.b64encode(file_bytes).decode("utf-8")
            return {
                "file_name": clean_name,
                "file_base64": base64_data
            }
    except Exception:
        return None