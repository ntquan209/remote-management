"""
System Module - Quản lý hệ thống máy tính từ xa

📌 CHỨC NĂNG:
- Lấy danh sách tiến trình đang chạy (get_process_list)
- Tắt tiến trình theo PID (kill_process)
- Lấy thông tin hệ thống (get_system_info): hostname, CPU, RAM, Disk
- Điều khiển nguồn: tắt máy (shutdown), khởi động lại (restart)

🔁 LUỒNG HOẠT ĐỘNG:
1. Agent nhận lệnh từ backend (get_processes, kill_process, shutdown...)
2. Gọi phương thức tương ứng trong SystemManager
3. Kết quả trả về agent.py để gửi lại backend

🛠️ CÔNG NGHỆ:
- psutil: Thư viện Python lấy thông tin hệ thống (process, CPU, RAM, Disk)
- platform: Thư viện chuẩn lấy tên máy, hệ điều hành
- subprocess: Gọi lệnh shutdown/restart của OS
"""

import subprocess
import psutil
import platform
from typing import Dict, List, Optional


class SystemManager:
    """Quản lý các thao tác hệ thống"""
    
    @staticmethod
    def get_process_list() -> List[Dict]:
        """
        Lấy danh sách tất cả tiến trình đang chạy
        
        Returns:
            List các dict chứa: pid, name, status của mỗi tiến trình
        
        Sử dụng psutil.process_iter() để duyệt qua tất cả tiến trình,
        bỏ qua các tiến trình không truy cập được (NoSuchProcess, AccessDenied)
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'status': proc.info['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass  # Bỏ qua tiến trình đã kết thúc hoặc không có quyền
        return processes
    
    @staticmethod
    def kill_process(pid: int) -> bool:
        """
        Tắt một tiến trình theo PID
        
        Args:
            pid: Process ID của tiến trình cần tắt
        
        Returns:
            True nếu tắt thành công, False nếu thất bại
        
        Sử dụng psutil.Process(pid).terminate() để gửi tín hiệu tắt
        """
        try:
            p = psutil.Process(pid)
            p.terminate()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    @staticmethod
    def get_system_info() -> Dict:
        """
        Lấy thông tin tổng quan hệ thống
        
        Returns:
            Dict chứa: hostname, platform, processor, cpu_count, memory, disk
        
        Kết hợp:
        - platform.node(): tên máy tính
        - platform.system(): hệ điều hành (Windows/Linux/Darwin)
        - psutil.cpu_count(): số CPU cores
        - psutil.virtual_memory(): thông tin RAM
        - psutil.disk_usage('/'): thông tin ổ đĩa
        """
        return {
            'hostname': platform.node(),
            'platform': platform.system(),
            'processor': platform.processor(),
            'cpu_count': psutil.cpu_count(),
            'memory': psutil.virtual_memory()._asdict(),
            'disk': psutil.disk_usage('/')._asdict()
        }
    
    @staticmethod
    def shutdown(delay: int = 0):
        """
        Tắt máy tính từ xa
        
        Args:
            delay: Thời gian delay trước khi tắt (giây)
        
        Tự động phát hiện hệ điều hành và dùng lệnh phù hợp:
        - Windows: shutdown /s /t {delay}
        - Linux/Mac: shutdown -h {delay}
        """
        system = platform.system()
        if system == "Windows":
            subprocess.run(['shutdown', '/s', '/t', str(delay)])
        elif system in ["Linux", "Darwin"]:
            subprocess.run(['shutdown', '-h', str(delay)])
    
    @staticmethod
    def restart(delay: int = 0):
        """
        Khởi động lại máy tính từ xa
        
        Args:
            delay: Thời gian delay trước khi restart (giây)
        
        Tương tự shutdown nhưng dùng tham số:
        - Windows: shutdown /r /t {delay}
        - Linux/Mac: shutdown -r {delay}
        """
        system = platform.system()
        if system == "Windows":
            subprocess.run(['shutdown', '/r', '/t', str(delay)])
        elif system in ["Linux", "Darwin"]:
            subprocess.run(['shutdown', '-r', str(delay)])


# Global instance - dùng chung cho toàn bộ agent
system_manager = SystemManager()