"""
Authentication & Security - Xác thực và bảo mật

📌 CHỨC NĂNG:
- Băm mật khẩu bằng bcrypt (hash_password, verify_password)
- Tạo JWT token cho phiên đăng nhập (create_access_token)
- Giải mã và xác thực JWT token (decode_token)

🔁 LUỒNG HOẠT ĐỘNG:
1. Đăng ký: hash_password() → lưu hashed_password vào database
2. Đăng nhập: verify_password() → so sánh password với hash trong DB
3. Tạo token: create_access_token() → mã hóa user data + thời gian hết hạn
4. Xác thực: decode_token() → giải mã token, trả về None nếu hết hạn hoặc sai

🔐 CÔNG NGHỆ:
- bcrypt: Thuật toán băm mật khẩu an toàn
- JWT (JSON Web Token): Token chứa thông tin user, có chữ ký số
- passlib: Thư viện hash password (hỗ trợ bcrypt)
- python-jose: Thư viện tạo/xác thực JWT
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# Context cho password hashing - cấu hình dùng bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Băm mật khẩu bằng bcrypt
    
    Đầu vào: password dạng text thuần
    Đầu ra: chuỗi hash (vd: "$2b$12$...")
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Xác thực mật khẩu
    
    So sánh password người dùng nhập với hash đã lưu trong DB
    Trả về True nếu đúng, False nếu sai
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Tạo JWT access token
    
    Args:
        data: Dữ liệu cần mã hóa vào token (vd: {"sub": username})
        expires_delta: Thời gian hết hạn (tùy chọn, mặc định 30 phút)
    
    Returns:
        Chuỗi JWT token đã mã hóa
    
    Cấu trúc JWT:
    header.payload.signature
    - header: Thuật toán (HS256)
    - payload: Dữ liệu + thời gian hết hạn (exp)
    - signature: Chữ ký số dùng SECRET_KEY
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Giải mã và xác thực JWT token
    
    Args:
        token: Chuỗi JWT token cần giải mã
    
    Returns:
        Payload (dict) nếu token hợp lệ
        None nếu token hết hạn hoặc không hợp lệ
    
    Quá trình:
    1. Dùng SECRET_KEY và thuật toán để giải mã
    2. Kiểm tra chữ ký số
    3. Kiểm tra thời gian hết hạn (exp)
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None