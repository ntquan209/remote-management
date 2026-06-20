"""
Seed script - Tạo tài khoản admin mặc định
Chạy: python seed.py

Tạo tài khoản admin:
- Username: admin
- Password: admin123
- Email: admin@hcmus.edu.vn
- Role: admin
"""

from app.database import SessionLocal, init_db
from app.models import User
from app.auth import hash_password

def seed_admin():
    """Tạo tài khoản admin nếu chưa tồn tại"""
    # Khởi tạo database
    init_db()
    
    # Tạo session
    db = SessionLocal()
    
    try:
        # Kiểm tra admin đã tồn tại chưa
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print(f"✓ Tài khoản admin đã tồn tại (id={existing.id}, role={existing.role})")
            return
        
        # Tạo admin user
        admin = User(
            username="admin",
            email="admin@hcmus.edu.vn",
            full_name="Quản trị hệ thống",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Đã tạo tài khoản admin thành công!")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   Email: admin@hcmus.edu.vn")
        print(f"   Role: admin")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()