"""
Consent Module - Thông báo và xin phép người dùng

📌 CHỨC NĂNG:
- Hiển thị popup thông báo trên máy trạm (của sinh viên)
- Xin phép người dùng trước khi thực hiện thao tác nhạy cảm
- Hiển thị cảnh báo khi đang bị giám sát

🔁 LUỒNG HOẠT ĐỘNG:
1. Backend gửi lệnh "show_consent" tới agent
2. agent.py gọi consent_manager.show_consent_popup()
3. Một cửa sổ Tkinter hiện ra trên máy sinh viên
4. Sinh viên chọn Yes/No, kết quả trả về callback

🔒 MỤC ĐÍCH BẢO MẬT:
- Đảm bảo sinh viên biết đang bị giám sát (ethics)
- Popup luôn ở trên cùng (topmost) để không bị che khuất
- Chạy trên thread riêng để không block agent

🛠️ CÔNG NGHỆ:
- tkinter: Thư viện GUI chuẩn của Python
- messagebox: Hộp thoại Yes/No, Info, Warning
- threading: Chạy popuptrên thread riêng
"""

import tkinter as tk
from tkinter import messagebox
import threading
from typing import Callable, Optional


class ConsentManager:
    """Quản lý hiển thị popup thông báo/xin phép người dùng"""
    
    @staticmethod
    def show_consent_popup(title: str = "Notice", message: str = "", 
                          callback: Optional[Callable] = None) -> bool:
        """
        Hiển thị hộp thoại xin phép (Yes/No)
        
        Args:
            title: Tiêu đề popup
            message: Nội dung thông báo
            callback: Hàm callback nhận kết quả (True/False)
        
        Returns:
            True luôn (vì chạy bất đồng bộ), kết quả thực tế qua callback
        
        Cách hoạt động:
        1. Tạo cửa sổ Tkinder ẩn (withdraw)
        2. Đặt cửa sổ luôn ở trên cùng (topmost)
        3. Hiển thị messagebox.askyesno (Yes/No)
        4. Nếu có callback, gọi với kết quả người dùng chọn
        5. Đóng cửa sổ
        """
        
        def show_popup():
            root = tk.Tk()
            root.withdraw()  # Ẩn cửa sổ chính
            root.attributes('-topmost', True)  # Luôn ở trên cùng
            
            result = messagebox.askyesno(title, message)
            
            if callback:
                callback(result)
            
            root.destroy()
            return result
        
        # Chạy trên thread riêng để không chặn agent
        thread = threading.Thread(target=show_popup, daemon=True)
        thread.start()
        return True
    
    @staticmethod
    def show_notification(title: str = "Notification", message: str = ""):
        """
        Hiển thị thông báo (Info)
        
        Dùng để thông báo cho sinh viên biết đang bị giám sát màn hình
        """
        def show_msg():
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            messagebox.showinfo(title, message)
            root.destroy()
        
        thread = threading.Thread(target=show_msg, daemon=True)
        thread.start()
    
    @staticmethod
    def show_warning(title: str = "Warning", message: str = ""):
        """
        Hiển thị cảnh báo (Warning)
        
        Dùng để cảnh báo trước khi thực hiện hành động nguy hiểm
        (vd: shutdown máy)
        """
        def show_warn():
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            messagebox.showwarning(title, message)
            root.destroy()
        
        thread = threading.Thread(target=show_warn, daemon=True)
        thread.start()


# Global instance
consent_manager = ConsentManager()