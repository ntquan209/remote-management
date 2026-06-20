"""
SQLAlchemy ORM Models - Định nghĩa cấu trúc bảng database

📌 CHỨC NĂNG:
- Định nghĩa các bảng trong database dưới dạng Python classes
- Mỗi class tương ứng với một bảng trong SQLite
- SQLAlchemy tự động tạo bảng dựa vào các class này

📋 CÁC BẢNG:
1. User - Người dùng hệ thống (giảng viên)
2. Agent - Máy trạm từ xa (máy sinh viên)
3. Task - Lệnh/lịch sử tác vụ đã gửi tới agent
4. AuditLog - Nhật ký hành động hệ thống thời gian thực (Mới bổ sung)

🔁 LUỒNG HOẠT ĐỘNG:
- Khi init_db() được gọi, SQLAlchemy đọc các class kế thừa Base
- Tự động tạo bảng nếu chưa tồn tại dựa vào __tablename__ và các Column
- Các model này dùng để CRUD dữ liệu qua session
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
from app.database import Base


class User(Base):
    """
    Bảng users - Lưu thông tin tài khoản đăng nhập
    
    Các trường:
    - id: ID tự tăng (khóa chính)
    - username: Tên đăng nhập (duy nhất)
    - email: Email (duy nhất)
    - hashed_password: Mật khẩu đã mã hóa bcrypt
    - is_active: Trạng thái hoạt động
    - created_at: Thời gian tạo tài khoản
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Agent(Base):
    """
    Bảng agents - Lưu thông tin máy trạm từ xa
    
    Các trường:
    - id: ID tự tăng (khóa chính)
    - agent_id: Mã định danh duy nhất của máy (ví dụ: "agent_001")
    - hostname: Tên máy tính
    - ip_address: Địa chỉ IP
    - is_online: Trạng thái online/offline
    - last_seen: Lần cuối thấy online
    - created_at: Thời gian đăng ký
    """
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, index=True)
    hostname = Column(String)
    ip_address = Column(String)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    """
    Bảng tasks - Lưu lịch sử lệnh đã gửi tới agent
    
    Các trường:
    - id: ID tự tăng (khóa chính)
    - agent_id: ID của agent nhận lệnh
    - command: Tên lệnh (ví dụ: "take_screenshot", "kill_process")
    - status: Trạng thái (pending, running, completed, failed)
    - result: Kết quả trả về (dạng text/JSON)
    - created_at: Thời gian gửi lệnh
    - completed_at: Thời gian hoàn thành
    """
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, index=True)
    command = Column(String)
    status = Column(String, default="pending")  # pending, running, completed, failed
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """
    Bảng audit_logs - Lưu nhật ký hành động hệ thống gần đây hiển thị lên Web UI
    
    Các trường:
    - id: ID tự tăng (khóa chính)
    - operator: Người thực hiện (ví dụ: "Giảng viên (agent_001)", "Hệ thống (System)")
    - action: Thao tác thực hiện (ví dụ: "START_LIVE_STREAM", "STOP_LIVE_STREAM", "KILL_PROCESS")
    - target: Máy trạm mục tiêu chịu tác động (ví dụ: "Kali_Lab_01")
    - status: Trạng thái của hành động (ví dụ: "Success", "Stopped", "Failed")
    - created_at: Thời gian ghi nhận nhật ký hành động
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    operator = Column(String, index=True)
    action = Column(String, index=True)
    target = Column(String, nullable=True)
    status = Column(String, default="Success")
    created_at = Column(DateTime, default=datetime.utcnow)