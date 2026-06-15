# 📂 Project Structure

## Current Directory Organization

```
remote-lab-management/
├── backend/                       # Central Backend (FastAPI)
│   ├── app/
│   │   ├── __init__.py           # Package initialization
│   │   ├── main.py               # FastAPI application & WebSocket endpoints
│   │   ├── config.py             # Configuration settings (JWT, DB, etc)
│   │   ├── database.py           # SQLAlchemy setup & get_db dependency
│   │   ├── models.py             # ORM models (User, Agent, Task)
│   │   ├── auth.py               # Authentication & JWT utilities
│   │   └── manager.py            # WebSocket connection manager
│   ├── requirements.txt          # Python dependencies
│   └── remote_lab.db             # SQLite database (auto-created)
│
├── agent/                         # Remote Agent (runs on target machines)
│   ├── agent.py                  # Main agent entry point
│   ├── modules/                  # System functionality modules
│   │   ├── __init__.py           # Package initialization
│   │   ├── system.py             # Process & system management
│   │   ├── media.py              # Screenshot & webcam capture
│   │   ├── keylogger.py          # Keyboard input logging
│   │   └── consent.py            # User consent popups
│   └── requirements.txt          # Python dependencies
│
├── frontend/                      # Web UI (React/Vite)
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── index.js
│   │   ├── config/
│   │   │   └── app.config.js
│   │   ├── components/
│   │   │   └── machine-selector.js
│   │   ├── lib/
│   │   │   └── socket.js
│   │   ├── pages/
│   │   │   ├── control.js
│   │   │   └── monitor.js
│   │   ├── styles/
│   │   │   └── style.css
│   │   ├── templates/
│   │   │   ├── panels.js
│   │   │   ├── renderer.js
│   │   │   ├── sidebar.js
│   │   │   └── topbar.js
│   │   ├── utils/
│   │   │   ├── audit.js
│   │   │   └── dom.js
│   │   └── assets/
│   └── package.json
│
├── backend-server/                # Old backend (Node.js) - can be removed
├── remote-agent/                  # Old agent - can be removed
├── PROJECT_GUIDE.md               # Project guidelines & coding standards
├── readme.txt                     # Project information
└── STRUCTURE.md                   # This file

## Architecture

### Backend (Python + FastAPI)
- **Port:** 8000
- **Protocol:** HTTP + WebSocket
- **Database:** SQLite (remote_lab.db)
- **Key Features:**
  - REST API for frontend operations
  - WebSocket server for agent connections
  - JWT authentication
  - Connection manager for multiple agents

### Agent (Python)
- **Connection:** WebSocket client
- **Backend URL:** ws://backend-server:8000/ws/agent/{agent_id}
- **Key Modules:**
  - system.py: Process control, system info
  - media.py: Screenshots, webcam
  - keylogger.py: Keyboard logging
  - consent.py: User notifications

### Frontend (React + Vite)
- **Port:** 3000+
- **Protocol:** HTTP + WebSocket
- **Dependencies:** React, Socket.io client

## Running the Project

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Agent Setup
```bash
cd agent
pip install -r requirements.txt
python agent.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Command Flow

1. **User → Frontend** (HTTP/WebSocket)
2. **Frontend → Backend** (REST API / WebSocket)
3. **Backend → Agent** (WebSocket)
4. **Agent → Backend** (WebSocket response)
5. **Backend → Frontend** (WebSocket/REST response)
6. **Frontend → User** (UI update)
