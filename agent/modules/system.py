import os
import psutil

def get_process_list():
    """Quét hệ thống và trả về danh sách 15 tiến trình ngốn CPU nhất"""
    process_list = []
    try:
        for proc in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']), 
                           key=lambda p: p.info['cpu_percent'] or 0, reverse=True)[:15]:
            
            ram_mb = round(proc.info['memory_info'].rss / (1024 * 1024), 1)
            process_list.append({
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'cpu': f"{proc.info['cpu_percent'] or 0.0}%",
                'ram': f"{ram_mb} MB"
            })
    except Exception as e:
        print(f"❌ Lỗi quét tiến trình: {e}")
    return process_list

def kill_process_by_pid(pid):
    """Đóng tiến trình theo mã PID"""
    try:
        p = psutil.Process(pid)
        p.terminate()
        return True
    except Exception as e:
        print(f"❌ Không thể đóng tiến trình {pid}: {e}")
        return False

def execute_power_cmd(action):
    """Thực thi lệnh nguồn hệ thống"""
    if action == 'SHUTDOWN':
        print("⚠️ Đang thực thi lệnh tắt máy...")
        os.system('shutdown -h now')
    elif action == 'RESTART':
        print("⚠️ Đang thực thi lệnh khởi động lại...")
        os.system('reboot')