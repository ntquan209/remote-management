"""
Routes API - Xác thực & Phân quyền

📌 CHỨC NĂNG:
- POST /api/register: Đăng ký tài khoản mới
- POST /api/login: Đăng nhập, trả về JWT token
- GET /api/me: Lấy thông tin user hiện tại (yêu cầu Bearer token)
- GET /api/admin/users: Danh sách user (yêu cầu admin)
- PUT /api/admin/users/{user_id}/role: Đổi role user (yêu cầu admin)
- DELETE /api/admin/users/{user_id}: Xóa user (yêu cầu admin)

🔁 LUỒNG HOẠT ĐỘNG:
1. Đăng ký: Client gửi username, email, password → hash password → lưu DB → trả về token
2. Đăng nhập: Client gửi username, password → verify → tạo JWT token → trả về token
3. Xem profile: Client gửi Authorization: Bearer <token> → giải mã → trả về thông tin user

🔐 PHÂN QUYỀN:
- 2 role: teacher (giảng viên), admin (quản trị hệ thống)
- Mặc định user mới đăng ký có role "teacher" với is_active=False (chờ admin duyệt)
- get_current_user: FastAPI dependency xác thực token
- require_role(): Dependency kiểm tra role, dùng cho các route cần phân quyền
- Chỉ admin mới có thể quản lý user (xem danh sách, đổi role, xóa)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.database import get_db
from app.models import User
from app.auth import hash_password, verify_password, create_access_token, decode_token

# Tạo router cho các API auth
router = APIRouter(prefix="/api", tags=["Authentication"])


# =============================================
# Pydantic Schemas (kiểu dữ liệu request/response)
# =============================================

class RegisterRequest(BaseModel):
    """Schema cho request đăng ký"""
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    email: str = Field(..., description="Email")
    password: str = Field(..., min_length=6, description="Mật khẩu")
    full_name: Optional[str] = Field(None, max_length=100, description="Họ tên đầy đủ")


class LoginRequest(BaseModel):
    """Schema cho request đăng nhập"""
    username: str = Field(..., description="Tên đăng nhập")
    password: str = Field(..., description="Mật khẩu")


class TokenResponse(BaseModel):
    """Schema cho response token"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """Schema cho response thông tin user"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool


# =============================================
# Helper: Lấy user hiện tại từ token
# =============================================

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """
    FastAPI dependency: Lấy user hiện tại từ JWT token trong Authorization header
    
    Lấy token từ header: Authorization: Bearer <token>
    
    Cách dùng trong route:
    @app.get("/api/protected")
    def protected_route(user: User = Depends(get_current_user)):
        ...
    
    Nếu token không hợp lệ hoặc user không tồn tại → raise HTTPException 401
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu token xác thực",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_str = authorization.replace("Bearer ", "")
    token = decode_token(token_str)
    
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = token.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không chứa thông tin user",
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User không tồn tại",
        )
    
    return user


# =============================================
# API Endpoints
# =============================================

@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    📝 Đăng ký tài khoản mới
    
    Request Body:
    {
        "username": "teacher1",
        "email": "teacher1@hcmus.edu.vn",
        "password": "123456",
        "full_name": "Giảng viên A" (tùy chọn)
    }
    
    Response:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer",
        "user": { "id": 1, "username": "teacher1", ... }
    }
    
    Kiểm tra:
    - username đã tồn tại? → 400
    - email đã tồn tại? → 400
    """
    # Kiểm tra username đã tồn tại
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username đã tồn tại"
        )
    
    # Kiểm tra email đã tồn tại
    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng"
        )
    
    # Tạo user mới
    new_user = User(
        username=request.username,
        email=request.email,
        full_name=request.full_name,
    hashed_password=hash_password(request.password),
        role="teacher",  # Mặc định là teacher
        is_active=False  # Chờ admin duyệt
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Tạo JWT token
    access_token = create_access_token(data={"sub": new_user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "is_active": new_user.is_active
        }
    }


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    🔑 Đăng nhập
    
    Request Body:
    {
        "username": "teacher1",
        "password": "123456"
    }
    
    Response:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer",
        "user": { "id": 1, "username": "teacher1", ... }
    }
    
    Kiểm tra:
    - username không tồn tại? → 401
    - sai mật khẩu? → 401
    - tài khoản bị khóa? → 403
    """
    # Tìm user theo username
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu"
        )
    
    # Kiểm tra mật khẩu
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu"
        )
    
    # Kiểm tra tài khoản còn hoạt động
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa"
        )
    
    # Tạo JWT token
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active
        }
    }


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """
    👤 Lấy thông tin user hiện tại
    
    Yêu cầu: Authorization: Bearer <token>
    
    Response:
    {
        "id": 1,
        "username": "teacher1",
        "email": "teacher1@hcmus.edu.vn",
        "full_name": "Giảng viên A",
        "role": "teacher",
        "is_active": true
    }
    """
    return user


# =============================================
# Role-based Access Control
# =============================================

def require_role(required_role: str):
    """
    Factory function tạo dependency kiểm tra role
    
    Cách dùng:
    @router.get("/api/admin/users")
    def list_users(user: User = Depends(require_role("admin"))):
        ...
    
    Nếu user không có role phù hợp → raise HTTPException 403
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        ROLES = {"admin": 2, "teacher": 1}
        if ROLES.get(current_user.role, 0) < ROLES.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền {required_role}. Vai trò hiện tại: {current_user.role}"
            )
        return current_user
    return role_checker


# =============================================
# Admin API Endpoints
# =============================================

class UpdateRoleRequest(BaseModel):
    """Schema cho request đổi role user"""
    role: str = Field(..., pattern="^(admin|teacher)$", description="Vai trò mới")


class UserListResponse(BaseModel):
    """Schema cho response danh sách user"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: Optional[str]


@router.get("/admin/users", response_model=list[UserListResponse])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin"))
):
    """
    📋 Danh sách tất cả người dùng (Yêu cầu quyền admin)
    
    Response: Mảng các user với thông tin chi tiết
    """
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]


@router.put("/admin/users/{user_id}/role")
def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin"))
):
    """
    🔄 Đổi vai trò người dùng (Yêu cầu quyền admin)
    
    - Không thể tự đổi role của chính mình
    - Role hợp lệ: admin, teacher
    """
    # Không cho tự đổi role chính mình
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự thay đổi vai trò của chính mình"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    user.role = request.role
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"Đã đổi vai trò của {user.username} thành {request.role}",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin"))
):
    """
    🗑️ Xóa người dùng (Yêu cầu quyền admin)
    
    - Không thể xóa chính mình
    """
    # Không cho xóa chính mình
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự xóa tài khoản của chính mình"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": f"Đã xóa người dùng {user.username}"}


@router.put("/admin/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin"))
):
    """
    🔒 Khóa/Mở khóa tài khoản người dùng (Yêu cầu quyền admin)
    
    - Không thể khóa chính mình
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự khóa tài khoản của chính mình"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    status_text = "đã mở khóa" if user.is_active else "đã khóa"
    return {
        "message": f"Tài khoản {user.username} {status_text}",
        "is_active": user.is_active
    }
