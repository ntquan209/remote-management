# Remote Lab Management System — Technical Overview

> Hệ thống quản trị phòng thực hành từ xa. Cho phép giảng viên quản lý máy tính phòng lab qua web.

---

## 1. System Architecture (3-Tier)

```
┌────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Browser)                          │
│  Vite + Vanilla JavaScript — port 5173                        │
│  Giao diện quản lý cho giảng viên                             │
│  Role-based UI: student/teacher/admin                         │
└───────────────────────┬────────────────────────────────────────┘
                        │ HTTP (REST) + WebSocket
                        ▼
┌────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI - Python)                  │
│  Chạy trên máy chủ — port 8000                                │
│  Chức năng:                                                   │
│  • Xác thực JWT (login/register)                              │
│  • Chuyển tiếp lệnh Frontend ↔ Agent                          │
│  • Ghi audit log realtime vào SQLite                          │
│  • Phân quyền: student → teacher → admin                      │
└───────────────────────┬────────────────────────────────────────┘
                        │ WebSocket
                        ▼
┌────────────────────────────────────────────────────────────────┐
│              AGENT (Python) — Student Machine                  │
│  Chạy trên máy sinh viên (Kali Linux)                         │
│  Nhận lệnh từ Backend → thực thi → gửi kết quả về             │
└────────────────────────────────────────────────────────────────┘
```

### Communication Protocols

| Channel | Protocol | Usage |
|---------|----------|-------|
| Frontend ↔ Backend | REST (HTTP) | Login, register, fetch audit logs, admin API |
| Frontend ↔ Backend | WebSocket | Real-time commands: screenshot, process list, webcam, keylogger |
| Backend ↔ Agent | WebSocket | Forward commands, receive agent responses |

---

## 2. Technology Stack

### Backend (`backend/`)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | FastAPI (Python) | REST API + WebSocket server |
| Auth | JWT (python-jose) + bcrypt | Token-based authentication |
| Database | SQLite + SQLAlchemy ORM | Lightweight, no server needed |
| Password Hashing | passlib (bcrypt) | Secure password storage |

### Frontend (`frontend/`)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Build Tool | Vite | Fast dev server + bundler |
| UI | Vanilla JavaScript | No framework overhead |
| WebSocket | Native WebSocket API | Real-time bidirectional communication |
| Styling | Custom CSS | Dark theme, responsive layout |

### Agent (`agent/`)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| WebSocket | websocket-client | Connect to backend |
| Screen Capture | PIL + gnome-screenshot / scrot / mss | Multi-method fallback |
| Camera | OpenCV + ffmpeg + GStreamer | Multi-backend webcam streaming |
| Keylogger | pynput | Ethical keylogging with sandbox mode |
| Process | psutil | Task manager data |

---

## 3. Backend Deep Dive (`backend/app/`)

### File Structure

| File | Role | Key Functions |
|------|------|---------------|
| `main.py` | Entry point | FastAPI app, WebSocket handler, REST endpoints |
| `auth_router.py` | Auth API | `/api/register`, `/api/login`, `/api/me`, admin CRUD |
| `auth.py` | Security helpers | `hash_password()`, `verify_password()`, JWT create/decode |
| `models.py` | Database schema | User, Agent, Task, AuditLog |
| `database.py` | DB connection | SQLAlchemy engine, SessionLocal, init_db() |
| `manager.py` | WebSocket manager | `connect()`, `disconnect()`, `send_to_agent()`, `broadcast()` |
| `config.py` | Settings | SECRET_KEY, ALGORITHM, token expiry |

### REST API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Health check |
| GET | `/api/status` | No | Connected agents count |
| GET | `/api/audit-logs` | No | Last 50 audit log entries |
| POST | `/api/register` | No | Create account (default role: student) |
| POST | `/api/login` | No | Authenticate, get JWT |
| GET | `/api/me` | Bearer | Current user info |
| GET | `/api/admin/users` | Admin | List all users |
| PUT | `/api/admin/users/{id}/role` | Admin | Change user role |
| DELETE | `/api/admin/users/{id}` | Admin | Delete user |
| PUT | `/api/admin/users/{id}/toggle-active` | Admin | Lock/unlock user |

### WebSocket Flow (Command Routing)

```
Frontend sends:  { "event": "SCREENSHOT", "target": "Kali_Lab_01", "data": {} }
                       │
                       ▼
Backend main.py: command_map = {
    "SCREENSHOT" → "take_screenshot",
    "KILL_PROCESS" → "kill_process",
    "WEBCAM_START" → "get_webcam_frame",
    "KEYLOGGER_TOGGLE" → "toggle_keylogger",
    ... 12 commands total
}
                       │
                       ▼
Agent receives:  { "command": "take_screenshot", "data": {} }
                       │
                       ▼
Agent responds:  { "command": "agent_send_screen", "machine_name": "...", "image_base64": "..." }
                       │
                       ▼
Backend broadcasts to all Frontend tabs
```

---

## 4. Agent Deep Dive (`agent/`)

### File Structure

| File | Responsibility | Key Features |
|------|---------------|--------------|
| `agent.py` | Main loop | WebSocket connect/reconnect, message dispatch, sender queue |
| `modules/media.py` | Screen capture | DBus → gnome-screenshot → scrot → mss (4-level fallback) |
| `modules/webcam.py` | Webcam streaming | ffmpeg → GStreamer → OpenCV (3-level fallback), BGR correction, YUYV recovery |
| `modules/keylogger.py` | Ethical keylogger | Sandbox mode, blocked keywords, real-time status reporting |
| `modules/system.py` | Process manager | psutil-based process list, kill, shutdown/restart |
| `modules/app_control.py` | App launcher | Predefined Kali apps dictionary (14 apps) |
| `modules/sandbox.py` | File sandbox | Downloads directory access, base64 encoding |
| `modules/screen_notify.py` | Visual warning | Tkinter overlay banner "MÀN HÌNH ĐANG BỊ QUẢN LÝ" |
| `modules/window_monitor.py` | Active window | xdotool → xprop (Linux) / user32 (Windows) |

### Threading Model

```
main thread: WebSocket event loop (run_forever)
    │
    ├── sender_loop (daemon) — single-threaded WebSocket writer via queue
    │
    ├── sys_monitor_loop (daemon) — sends process list every 5s
    │
    ├── webcam_stream_worker (daemon) — camera capture loop
    │
    ├── keylogger listener (pynput) — keyboard event callbacks
    │
    └── tk-warning (daemon) — Tkinter overlay window
```

**Key Design Decision:** All WebSocket writes go through a single `queue.Queue` + `sender_loop` to avoid thread-safety issues with `websocket-client`.

---

## 5. Authentication & Authorization

### Role Hierarchy

```
admin (level 3) ─── full access + user management
    │
teacher (level 2) ── agent control (screenshot, process, keylogger, webcam, power)
    │
student (level 1) ── view-only dashboard
```

### Auth Flow

```
User → Login Form → POST /api/login
                        │
                        ▼
              Backend verifies password (bcrypt)
                        │
                        ▼
              JWT created (30 min expiry)
                        │
                        ▼
              Token stored in localStorage
                        │
                        ▼
              Page reload → checkAuth() → GET /api/me
                        │
                  ┌─────┴─────┐
                  ▼           ▼
              Valid        Expired
                  │           │
                  ▼           ▼
            renderApp()   renderAuthPage()
```

### Frontend Role-Based UI Control

```javascript
// api.js — hasRole() uses numeric comparison
const ROLES = { admin: 3, teacher: 2, student: 1 };

// index.js — applyRoleBasedUI()
// student: Hides Control/Monitor nav sections
// teacher: Shows all features
// admin: Shows all + "Quản trị hệ thống" menu
```

---

## 6. Webcam Streaming Pipeline

```
Agent receives "get_webcam_frame" command
         │
         ▼
set_v4l2_mjpg() — try to set MJPEG format via v4l2-ctl
         │
         ▼
try_ffmpeg_pipe() — fastest: pipe raw MJPEG from ffmpeg
   └─ fail → try_gstreamer_capture() — GStreamer pipeline
        └─ fail → try_opencv_backends() — V4L2 → FFMPEG → default
             └─ fail → log_v4l2_info() + abort
         │
         ▼
Frame loop (every 350ms):
   read frame → resize 640×480
   → try_yuyv_from_3ch() — fix YUYV mis-decoded as BGR
   → pick_bgr_permutation() — fix wrong channel order
   → encode JPEG quality 75 → base64 → send via queue
```

---

## 7. Ethical Keylogger with Sandbox

### Sandbox Rules

| Rule Type | Description | Example |
|-----------|-------------|---------|
| **Process allowlist** | Only capture in terminals/editors/IDEs | `gnome-terminal`, `code`, `gedit`, `nano` |
| **Title keywords** | Only capture in lab-related windows | `lab`, `practice`, `exercise`, `network` |
| **Blocked keywords** | Never capture sensitive windows | `login`, `password`, `banking`, `facebook` |
| **Browser mode** | Allow browser only if title matches sandbox | `Kali - lab - Cisco Packet Tracer` ✓ |

### Data Flow

```
Window focus change → _check_active_window()
    → match against process names and title keywords
    → update _sandbox_active flag
    → notify frontend via WebSocket

Key press → on_press() callback
    → if NOT _sandbox_active → ignore (safe)
    → if sandbox_active → send key via enqueue
```

---

## 8. Database Schema (SQLite)

### Tables

**`users`** — Authentication & authorization
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| username | TEXT UNIQUE | Login name |
| email | TEXT UNIQUE | Contact email |
| hashed_password | TEXT | bcrypt hash |
| role | TEXT | student / teacher / admin |
| is_active | BOOLEAN | Can be locked by admin |

**`agents`** — Registered machines
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| agent_id | TEXT UNIQUE | Machine identifier |
| hostname | TEXT | Machine name |
| ip_address | TEXT | Network address |
| is_online | BOOLEAN | Connection status |

**`audit_logs`** — Real-time activity log
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| operator | TEXT | Who performed action |
| action | TEXT | e.g. TAKE_SCREENSHOT, KILL_PROCESS |
| target | TEXT | Target machine |
| status | TEXT | Success / Stopped |
| created_at | DATETIME | Timestamp |

---

## 9. Project Structure (Full)

```
remote-lab-project/
│
├── agent/                          # Python Agent (student machine)
│   ├── agent.py                    # Main entry point
│   ├── requirements.txt            # Dependencies
│   ├── README.md
│   └── modules/
│       ├── media.py                # Screen capture (4 fallback methods)
│       ├── webcam.py               # Webcam streaming (3 backends)
│       ├── keylogger.py            # Ethical keylogger with sandbox
│       ├── system.py               # Process/task manager
│       ├── app_control.py          # App launcher (14 Kali apps)
│       ├── sandbox.py              # File sandbox (downloads directory)
│       ├── screen_notify.py        # Tkinter warning overlay
│       └── window_monitor.py       # Active window detection
│
├── backend/                        # FastAPI Backend (server)
│   ├── requirements.txt
│   ├── seed.py                     # Create default admin account
│   └── app/
│       ├── main.py                 # FastAPI app + WebSocket handler
│       ├── auth_router.py          # Auth & admin REST API
│       ├── auth.py                 # JWT + bcrypt helpers
│       ├── models.py               # SQLAlchemy schema
│       ├── database.py             # SQLite connection
│       ├── manager.py              # WebSocket connection manager
│       └── config.py               # Settings (secret key, expiry)
│
├── frontend/                       # Vite Frontend (teacher browser)
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── index.js                # App entry: auth check, routing
│       ├── config/app.config.js    # Server URLs configuration
│       ├── lib/
│       │   ├── api.js              # REST client (login, register, admin)
│       │   └── socket.js           # WebSocket client (commands, events)
│       ├── pages/
│       │   ├── auth.js             # Login/register UI
│       │   ├── monitor.js          # Screen, process, webcam, keylog handlers
│       │   └── control.js          # Power, webcam toggle commands
│       ├── templates/
│       │   ├── renderer.js         # App layout builder
│       │   ├── panels.js           # Dashboard, Monitor, Control, Admin panels
│       │   ├── sidebar.js          # Navigation menu
│       │   └── topbar.js           # Machine selector, user info
│       ├── components/
│       │   └── machine-selector.js # Agent dropdown management
│       ├── utils/
│       │   ├── audit.js            # Audit log UI helpers
│       │   └── dom.js              # DOM switching utilities
│       └── styles/
│           └── style.css           # Complete dark theme
│
├── STRUCTURE.md                    # This file
└── run_project.bat                 # Quick start launcher
```

---

## 10. Deployment & Quick Start

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                              # Creates admin/admin123
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                                 # http://localhost:5173
```

### Agent (on each student machine)
```bash
cd agent
pip install -r requirements.txt
python agent.py
```

### Default Accounts
| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| New user | (register) | (user-set) → role: student |

---

## 11. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Vanilla JS (no React/Vue)** | Lab environment: no build complexity, works on any browser |
| **SQLite (no PostgreSQL)** | No server installation, single file DB, sufficient for classroom scale |
| **Single sender thread** | `websocket-client` is NOT thread-safe → all writes via one queue |
| **Multi-method fallback** | Different Linux distros have different tools; agent auto-detects |
| **Mutable stop_flag** | `webcam_active = [False]` — reference semantics for thread communication |
| **Ethical keylogger** | Sandbox mode ensures only lab-relevant keystrokes are captured |

---

## 12. Feature Summary

| Feature | Backend | Frontend | Agent |
|---------|---------|----------|-------|
| User authentication | ✅ JWT | ✅ Login/register | — |
| Role-based access | ✅ require_role() | ✅ hasRole() + UI hide | — |
| Live screen view | ✅ WebSocket relay | ✅ Real-time image | ✅ 4-method capture |
| Process monitor | ✅ WebSocket relay | ✅ Top 15 processes | ✅ psutil (5s loop) |
| Kill process | ✅ Forward command | ✅ Button + confirm | ✅ psutil.terminate() |
| App control | ✅ Forward command | ✅ Start/stop buttons | ✅ 14 Kali apps |
| Webcam streaming | ✅ WebSocket relay | ✅ Live video panel | ✅ 3-backend pipeline |
| Keylogger | ✅ Status notification | ✅ Live key stream | ✅ Sandbox mode |
| File browser | ✅ Forward command | ✅ File list + download | ✅ Downloads dir |
| Shutdown/Restart | ✅ Forward command | ✅ Power buttons | ✅ systemctl command |
| Audit log | ✅ SQLite + broadcast | ✅ Real-time feed | — |
| Admin user mgmt | ✅ CRUD API | ✅ Admin panel | — |
| Reconnection | — | ✅ Auto-reconnect | ✅ Auto-reconnect |
| Screen notification | — | — | ✅ Tkinter overlay |