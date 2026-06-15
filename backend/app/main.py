"""
File chính của Backend FastAPI - Remote Lab Management System

📌 CHỨC NĂNG:
- Khởi tạo ứng dụng FastAPI với CORS và lifespan
- Định nghĩa các REST API endpoints (health check, status)
- Định nghĩa WebSocket endpoint để agent/frontend kết nối

🔁 LUỒNG HOẠT ĐỘNG:
1. Khi server start: lifespan → init_db() khởi tạo database SQLite
2. Khi có request HTTP:
   - GET / → trả về status "ok"
   - GET /api/status → trả về số agent đang kết nối
3. Khi có WebSocket kết nối tới /ws/agent/{agent_id}:
   - Gọi manager.connect() để chấp nhận kết nối
   - Lắng nghe và broadcast dữ liệu từ agent này tới các agent khác
4. Khi server shutdown: lifespan → manager.cleanup() đóng toàn bộ kết nối
"""

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import các module nội bộ
from app.config import settings
from app.database import init_db
from app.manager import manager
# QUAN TRỌNG: Import models để SQLAlchemy biết các bảng cần tạo khi gọi init_db()
import app.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Vòng đời ứng dụng - chạy khi server start và shutdown
    
    Startup: Khởi tạo database (tạo các bảng nếu chưa có)
    Shutdown: Dọn dẹp toàn bộ kết nối WebSocket đang mở
    """
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: Cleanup resources
    await manager.cleanup()


app = FastAPI(
    title="Remote Lab Management System",
    description="Central Backend for Remote Lab Management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware - Cho phép frontend (Vite ở port khác) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ REST API Endpoints ============
@app.get("/")
async def root():
    """Health check - Kiểm tra backend đang chạy"""
    return {"status": "ok", "message": "Remote Lab Management Backend"}


@app.get("/api/status")
async def get_status():
    """
    Lấy trạng thái hệ thống hiện tại
    - connected_agents: số lượng agent đang kết nối WebSocket
    - status: trạng thái running
    """
    return {
        "connected_agents": len(manager.active_connections),
        "status": "running"
    }


# ============ WebSocket Endpoints ============
@app.websocket("/ws/agent/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """
    Endpoint WebSocket - Trung tâm chuyển tiếp lệnh

    📌 CÁCH HOẠT ĐỘNG:
    1. Frontend ("agent_001") gửi lệnh JSON: {"event":"SHUTDOWN","target":"agent-01"}
    2. Backend kiểm tra nếu có "target" → chuyển tiếp lệnh tới agent đó
    3. Agent Python nhận lệnh {"command":"SHUTDOWN"} và thực thi
    4. Kết quả từ Agent được broadcast về Frontend
    
    🤝 QUY ƯỚC AGENT ID:
    - "agent_001" = Frontend (máy giảng viên, teacher)
    - "agent-01"  = Agent Python (máy sinh viên, student)
    """
    await manager.connect(websocket, agent_id)
    
    import json
    
    # Gửi danh sách agent đang online cho agent vừa kết nối (để Frontend biết)
    online_agents = [aid for aid in manager.active_connections.keys() if aid != agent_id]
    if online_agents:
        agent_list_msg = json.dumps({"event": "agent_list", "agents": online_agents})
        await websocket.send_text(agent_list_msg)
    
    # Thông báo cho các agent khác biết có agent mới
    new_agent_msg = json.dumps({"event": "agent_connected", "agent_id": agent_id})
    for aid, ws in list(manager.active_connections.items()):
        if aid != agent_id:
            try:
                await ws.send_text(new_agent_msg)
            except:
                pass
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                # Lệnh từ Frontend có target? (vd: {"event":"SHUTDOWN","target":"agent-01"})
                if payload.get("target"):
                    # Map tên lệnh từ Frontend (SHUTDOWN) sang agent.py (shutdown)
                    command_map = {
                        "SHUTDOWN": "shutdown",
                        "RESTART": "restart",
                        "SCREENSHOT": "take_screenshot",
                        "WEBCAM_START": "get_webcam_frame",
                        "WEBCAM_STOP": "none",
                        "KILL_PROCESS": "kill_process",
                        "START_STREAM": "take_screenshot",
                        "STOP_STREAM": "none",
                    }
                    cmd = command_map.get(payload["event"], payload["event"].lower())
                    agent_cmd = {"command": cmd, "data": payload.get("data", {})}
                    await manager.send_to_agent(payload["target"], json.dumps(agent_cmd))
                    print(f"→ Gửi lệnh '{cmd}' tới {payload['target']}")
                else:
                    # Chỉ chuyển tiếp dữ liệu sang các kết nối KHÁC (Frontend/Các máy khác), không gửi ngược lại chính nó
                    if payload.get("command"):
                        for aid, ws in list(manager.active_connections.items()):
                            if aid != agent_id: # 🎯 CHẶN KHÔNG CHO DỘI NGƯỢC VỀ CHÍNH NÓ
                                try:
                                    await ws.send_text(data)
                                except:
                                    pass
            except json.JSONDecodeError:
                # Text thuần: broadcast kèm prefix
                await manager.broadcast(f"Agent {agent_id}: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(agent_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)