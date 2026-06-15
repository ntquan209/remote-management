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
    Endpoint WebSocket cho Agent kết nối
    
    📌 CÁCH HOẠT ĐỘNG:
    1. Agent (Python script) hoặc Frontend mở WebSocket tới URL này
    2. manager.connect() chấp nhận kết nối và lưu vào dictionary
    3. Vòng lặp while True: nhận text từ agent này
    4. Gọi broadcast() để gửi text tới TẤT CẢ các agent khác
    5. Nếu có lỗi hoặc ngắt kết nối, finally block gọi disconnect()
    
    🔗 URL: ws://localhost:8000/ws/agent/{agent_id}
    """
    await manager.connect(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Agent {agent_id}: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(agent_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)