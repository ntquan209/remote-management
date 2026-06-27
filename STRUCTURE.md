# 🧭 Hướng Dẫn Hiểu Toàn Bộ Dự Án Remote Lab

## 1. TỔNG QUAN 

Hệ thống **quản trị phòng thực hành từ xa** (Remote Lab Management).

📌 **Mục tiêu:** Cho phép giảng viên (teacher) quản lý các máy tính trong phòng lab từ xa qua web.

**Ví dụ thực tế:**
- Giảng viên đang ở nhà, đăng nhập vào web
- Thấy danh sách máy sinh viên đang online
- Có thể xem màn hình máy sinh viên, chụp ảnh màn hình
- Có thể tắt/khởi động lại máy sinh viên từ xa
- Có thể xem danh sách tiến trình đang chạy
- Có thể ghi nhận phím bấm (keylogger) trên máy sinh viên

## 2. KIẾN TRÚC HỆ THỐNG

```
┌──────────────────────────────────────────────────────────────┐
│                     TRÌNH DUYỆT WEB                          │
│  Frontend (Vite + JavaScript) - port 5173                   │
│  Giao diện quản lý cho giảng viên                           │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP (REST API) + WebSocket
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI - Python)                │
│  Chạy trên máy chủ - port 8000                               │
│  - Xác thực (JWT login/register)                             │
│  - Chuyển tiếp lệnh tới Agent Python                         │
│  - Lưu dữ liệu vào SQLite                                    │
└────────────────────┬─────────────────────────────────────────┘
                     │ WebSocket
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                     AGENT PYTHON                              │
│  Chạy trên MÁY SINH VIÊN (máy trạm)                         │
│  - Thực thi lệnh nhận từ Backend                             │
│  - Chụp màn hình, quét process, bật webcam...                │
└──────────────────────────────────────────────────────────────┘
```

## 3. CÁC FILE QUAN TRỌNG VÀ CHỨC NĂNG

### 📁 `backend/` (Python - FastAPI)

| File | Chức năng |
|------|-----------|
| `app/main.py` | **File chính** - Khởi tạo server, khai báo API, WebSocket |
| `app/routes.py` | **API đăng nhập/đăng ký/phân quyền** - Xác thực người dùng |
| `app/auth.py` | **Bảo mật** - Mã hóa mật khẩu (bcrypt), tạo JWT token |
| `app/models.py` | **Cấu trúc database** - Định nghĩa bảng User, Agent, Task |
| `app/database.py` | **Kết nối database** - SQLAlchemy + SQLite |
| `app/manager.py` | **Quản lý WebSocket** - Kết nối với các Agent |
| `seed.py` | **Tạo tài khoản admin** - Chạy 1 lần khi cài đặt |

### 📁 `frontend/` (JavaScript - Vite)

| File | Chức năng |
|------|-----------|
| `src/index.js` | **File chính Frontend** - Kiểm tra đăng nhập, render giao diện, WebSocket |
| `src/lib/api.js` | **Gọi API backend** - Login, register, logout, admin API |
| `src/lib/socket.js` | **Kết nối WebSocket** - Gửi/nhận lệnh realtime |
| `src/pages/auth.js` | **Trang đăng nhập/đăng ký** - Giao diện login form |
| `src/templates/renderer.js` | **Render toàn bộ giao diện** - Ghép các template |
| `src/templates/panels.js` | **Các panel chức năng** - Dashboard, Monitor, Control, Admin |
| `src/templates/sidebar.js` | **Menu bên trái** - Các mục điều hướng |
| `src/templates/topbar.js` | **Thanh trên cùng** - Chọn máy, trạng thái |
| `src/pages/monitor.js` | **Xử lý màn hình + process** - Chụp màn hình, xem tiến trình |
| `src/pages/control.js` | **Xử lý điều khiển** - Power, webcam, keylogger |
| `src/config/app.config.js` | **Cấu hình** - URL backend, WebSocket |

## 4. LUỒNG ĐĂNG NHẬP (AUTH FLOW)

```
1. Mở web → index.js kiểm tra localStorage có token không?
   
   ❌ Không có token → renderAuthPage() → hiện form login
   
   ✅ Có token → renderApp() → hiện giao diện chính

2. Điền username/password → click "Đăng nhập"
   
   Login form → gọi api.js: login() → POST /api/login
   
   Backend routes.py: kiểm tra user, verify password
   
   ✅ Đúng → trả về JWT token + thông tin user
   
   Frontend lưu token vào localStorage → reload trang

3. Sau reload → có token → render giao diện chính
   
   index.js kiểm tra user.role:
   - student → ẩn hết mục điều khiển, chỉ xem dashboard
   - teacher → hiện toàn bộ chức năng
   - admin → hiện toàn bộ + thêm "Quản trị hệ thống"
```

## 5. PHÂN QUYỀN (ROLES)

| Role | Dashboard | Điều khiển Agent | Quản lý User |
|------|-----------|-------------------|--------------|
| **student** (mặc định) | ✅ Chỉ xem | ❌ Không | ❌ Không |
| **teacher** | ✅ Xem | ✅ Shutdown, Restart, Screen... | ❌ Không |
| **admin** | ✅ Xem | ✅ Toàn quyền | ✅ Thêm/Sửa/Xóa user |

**Cách backend kiểm tra quyền:**
```python
# routes.py - require_role()
def require_role(required_role):
    def role_checker(user):
        ROLES = {"admin": 3, "teacher": 2, "student": 1}
        if user_role < required_role → raise HTTPException 403
    return role_checker
```

**Cách frontend ẩn giao diện:**
```javascript
// index.js - applyRoleBasedUI()
if (!hasRole('teacher')) {
    // Ẩn các nút: Process, Screen, Keylog, Webcam, Power
}
if (hasRole('admin')) {
    // Thêm mục "Quản trị hệ thống" vào sidebar
}
```

## 6. LUỒNG ĐIỀU KHIỂN (Frontend → Backend → Agent)

```
Giảng viên click "Chụp màn hình"
        │
        ▼
control.js: emitCommand('SCREENSHOT', targetMachine)
        │
        ▼
socket.js: gửi JSON qua WebSocket
{ "event": "SCREENSHOT", "target": "agent-01" }
        │
        ▼
Backend main.py: nhận lệnh
→ thấy có "target": "agent-01"
→ chuyển tiếp tới agent-01 qua WebSocket
{ "command": "take_screenshot" }
        │
        ▼
Agent Python: nhận lệnh
→ thực thi system_manager.take_screenshot()
→ chụp ảnh màn hình
→ gửi ảnh (base64) về backend
        │
        ▼
Backend: nhận ảnh từ agent
→ broadcast tới frontend (agent_001)
        │
        ▼
Frontend index.js: nhận sự kiện 'screenshot'
→ hiển thị ảnh trong #screen-display-area
```

## 7. DATABASE (SQLite)

File: `backend/remote_lab.db` (tự động tạo, không cần cài đặt)

**Bảng users:**
| id | username | email | password (hash) | role | is_active |
|----|----------|-------|-----------------|------|-----------|
| 1 | admin | admin@... | (bcrypt) | admin | true |
| 2 | student1 | sv1@... | (bcrypt) | student | true |

**Bảng agents:** Lưu thông tin máy trạm (agent_id, hostname, ip...)
**Bảng tasks:** Lưu lịch sử lệnh đã gửi (command, status, result...)

## 8. CÁCH CHẠY

### Backend:
```bash
cd backend
python -m venv .venv          # Tạo môi trường (nếu chưa có)
source .venv/bin/activate     # Kích hoạt (Linux/Kali)
pip install -r requirements.txt  # Cài thư viện (nếu chưa có)
python seed.py                # Tạo tài khoản admin (chạy 1 lần)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
→ Backend chạy tại: `http://localhost:8000`

### Frontend:
```bash
cd frontend
npm install                   # Cài thư viện (nếu chưa có)
npm run dev
```
→ Frontend chạy tại: `http://localhost:5173`

### Tài khoản mặc định:
- **Admin:** admin / admin123
- **User mới:** tự đăng ký → mặc định là sinh viên

## 9. CÁC THUẬT NGỮ

| Thuật ngữ | Ý nghĩa |
|-----------|---------|
| **Agent** | Máy tính sinh viên (máy trạm), chạy script Python |
| **Backend** | Máy chủ trung tâm, chạy FastAPI |
| **Frontend** | Giao diện web giảng viên dùng |
| **JWT** | Token xác thực, hết hạn sau 30 phút |
| **WebSocket** | Kết nối 2 chiều realtime (gửi lệnh, nhận kết quả) |
| **SQLite** | Database file nhẹ, không cần cài server |
| **Role** | Vai trò người dùng (student/teacher/admin) |