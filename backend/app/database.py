"""
Database Connection & SQLAlchemy Setup

📌 CHỨC NĂNG:
- Thiết lập kết nối tới database SQLite
- Tạo engine và session factory cho SQLAlchemy ORM
- Cung cấp dependency get_db() cho FastAPI routes
- Tự động tạo các bảng khi ứng dụng khởi động

🔁 LUỒNG HOẠT ĐỘNG:
1. Khởi tạo SQLAlchemy engine với database URL từ config
2. Tạo session factory (SessionLocal) để tạo các session riêng biệt
3. init_db() được gọi khi server start → tạo tất cả bảng trong database
4. get_db() là FastAPI dependency:
   - Mỗi request tạo một session mới
   - Tự động đóng session khi request kết thúc
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Tạo engine kết nối database
# connect_args={"check_same_thread": False} là cần thiết cho SQLite
# vì SQLite không cho phép dùng cùng connection ở nhiều thread
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Session factory - tạo các session độc lập cho mỗi request
# autocommit=False: tự commit thủ công
# autoflush=False: tự động đồng bộ dữ liệu trước query
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho tất cả model - SQLAlchemy dùng để biết các bảng cần tạo
Base = declarative_base()


def init_db():
    """Khởi tạo database - tạo tất cả bảng nếu chưa tồn tại"""
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized")


def get_db():
    """
    FastAPI dependency - tạo database session cho mỗi request
    
    Cách dùng trong route:
    @app.get("/items")
    def get_items(db: Session = Depends(get_db)):
        ...
    
    Khi request kết thúc, session tự động đóng (finally block)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()