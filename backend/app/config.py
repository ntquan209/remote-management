"""
Cấu hình ứng dụng (Configuration Settings)

📌 CHỨC NĂNG:
- Định nghĩa các biến cấu hình cho toàn bộ backend
- Đọc từ biến môi trường (.env) hoặc dùng giá trị mặc định
- Sử dụng pydantic-settings để tự động validate

🔧 CÁC CẤU HÌNH CHÍNH:
- DATABASE_URL: Đường dẫn tới database SQLite
- SECRET_KEY: Khóa bí mật cho JWT token
- ALGORITHM: Thuật toán mã hóa JWT
- ACCESS_TOKEN_EXPIRE_MINUTES: Thời gian hết hạn token (phút)
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Cài đặt ứng dụng - tự động load từ .env file nếu có"""
    
    # Database - SQLite file trong thư mục backend
    DATABASE_URL: str = "sqlite:///./remote_lab.db"
    
    # JWT Configuration - Xác thực người dùng
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Server
    SERVER_NAME: str = "Remote Lab Management"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    class Config:
        env_file = ".env"


# Global settings instance - dùng chung cho toàn bộ ứng dụng
settings = Settings()