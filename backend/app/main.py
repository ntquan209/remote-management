"""
File chính của Backend FastAPI - Remote Lab Management System

📌 CHỨC NĂNG:
- Khởi tạo ứng dụng FastAPI với CORS và lifespan
- Định nghĩa các REST API endpoints (health check, status, audit log API)
- Định nghĩa WebSocket endpoint để agent/frontend kết nối, lưu log cứng database chống sập luồng

🔁 LUỒNG HOẠT ĐỘNG:
1. Khi server start: lifespan → init_db() khởi tạo database SQLite
2. Khi có request HTTP:
   - GET /api/audit-logs → Trả về lịch sử nhật ký hệ thống cũ cho Web load lại
3. Khi có tương tác WebSocket: Tự động ghi nhật ký hệ thống vào bảng audit_logs
"""

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy.orm import Session

# Import các module nội bộ
from app.config import settings
from app.database import init_db, SessionLocal
from app.manager import manager
from app.routes import router as auth_router
import app.models
from app.models import AuditLog

streaming_agents = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Auth Routes ============
app.include_router(auth_router)


# ============ REST API Endpoints ============
@app.get("/")
async def root():
    return {"status": "ok", "message": "Remote Lab Management Backend"}


@app.get("/api/status")
async def get_status():
    return {
        "connected_agents": len(manager.active_connections),
        "status": "running"
    }


@app.get("/api/audit-logs")
async def get_audit_logs():
    """
    🎯 API CHUẨN: Lấy danh sách toàn bộ Nhật ký hành động từ Database SQLite
    Frontend sẽ gọi API này khi vừa load trang để tránh bị mất log cũ khi F5.
    """
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(50).all()
        return [
            {
                "id": log.id,
                "time": log.created_at.strftime("%H:%M:%S"),
                "operator": log.operator,
                "action": log.action,
                "target": log.target,
                "status": log.status
            } for log in logs
        ]
    finally:
        db.close()


# ============ WebSocket Endpoints ============
@app.websocket("/ws/agent/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect(websocket, agent_id)
    
    import json
    global streaming_agents
    db = SessionLocal() # Mở session DB riêng cho luồng WebSocket này

    # --- 🎯 GHI LOG CỨNG KHI MÁY KẾT NỐI (AGENT_ONLINE / FRONTEND_CONNECT) ---
    try:
        is_frontend = (agent_id == "agent_001")
        action_type = "FRONTEND_CONNECT" if is_frontend else "AGENT_ONLINE"
        status_text = "Đã kết nối backend" if is_frontend else "Online"
        operator_name = "Hệ thống (System)"
        
        # Ghi cứng database trước
        new_log = AuditLog(
            operator=operator_name, action=action_type, target=agent_id, status=status_text, created_at=datetime.now()
        )
        db.add(new_log)
        db.commit()
        
        # Bắn real-time bọc trong try/except để phòng trường hợp lỗi socket đóng đột ngột không làm sập luồng
        try:
            await manager.broadcast(json.dumps({
                "command": "audit_log_update",
                "time": new_log.created_at.strftime("%H:%M:%S"),
                "operator": operator_name, "action": action_type, "target": agent_id, "status": status_text
            }))
        except Exception:
            pass
    except Exception as e:
        print(f"Lỗi ghi database log ONLINE: {e}")
    
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
                if payload.get("target"):
                    target_host = payload["target"]
                    
                    # Map tên lệnh từ Frontend sang agent.py
                    command_map = {
                        "SHUTDOWN": "shutdown", "RESTART": "restart",
                        "SCREENSHOT": "take_screenshot", "WEBCAM_START": "get_webcam_frame", "WEBCAM_STOP": "none",
                        "KILL_PROCESS": "kill_process", "START_STREAM": "take_screenshot", "STOP_STREAM": "none",
                    }
                    cmd = command_map.get(payload["event"], payload["event"].lower())
                    agent_cmd = {"command": cmd, "data": payload.get("data", {})}
                    await manager.send_to_agent(target_host, json.dumps(agent_cmd))
                    
                    # --- 🎯 GHI LOG VÀ BROADCAST KHI KÍCH HOẠT START_STREAM (LIVE) ---
                    if payload["event"] == "START_STREAM":
                        if target_host not in streaming_agents:
                            streaming_agents.add(target_host)
                            print(f"🎥 [STREAM] Khởi động luồng truyền video mượt mà từ máy: {target_host}")
                            
                            # Lưu database cứng trước để bảo toàn dữ liệu vĩnh viễn
                            new_log = AuditLog(
                                operator=f"Giảng viên ({agent_id})", action="START_LIVE_STREAM", target=target_host, status="Success", created_at=datetime.now()
                            )
                            db.add(new_log)
                            db.commit()
                            
                            # Thử thách phát tán real-time, lỗi mạng kệ cụ nó, database đã lưu thành công!
                            try:
                                await manager.broadcast(json.dumps({
                                    "command": "audit_log_update", "time": new_log.created_at.strftime("%H:%M:%S"),
                                    "operator": new_log.operator, "action": new_log.action, "target": new_log.target, "status": new_log.status
                                }))
                            except Exception:
                                pass
                    
                    # --- 🎯 GHI LOG VÀ BROADCAST KHI KÍCH HOẠT STOP_STREAM ---
                    elif payload["event"] == "STOP_STREAM":
                        if target_host in streaming_agents:
                            streaming_agents.discard(target_host)
                            print(f"🛑 [STREAM] Đã đóng luồng video livestream từ máy: {target_host}")
                            
                            new_log = AuditLog(
                                operator=f"Giảng viên ({agent_id})", action="STOP_LIVE_STREAM", target=target_host, status="Stopped", created_at=datetime.now()
                            )
                            db.add(new_log)
                            db.commit()
                            
                            try:
                                await manager.broadcast(json.dumps({
                                    "command": "audit_log_update", "time": new_log.created_at.strftime("%H:%M:%S"),
                                    "operator": new_log.operator, "action": new_log.action, "target": new_log.target, "status": new_log.status
                                }))
                            except Exception:
                                pass

                    # --- 🎯 GHI LOG VÀ BROADCAST KHI CHỤP ẢNH STATIC ---
                    elif payload["event"] == "SCREENSHOT" and target_host not in streaming_agents:
                        print(f"📸 [CAPTURE] Yêu cầu trích xuất một tấm ảnh tĩnh màn hình từ máy: {target_host}")
                        
                        new_log = AuditLog(
                            operator=f"Giảng viên ({agent_id})", action="TAKE_SCREENSHOT", target=target_host, status="Success", created_at=datetime.now()
                        )
                        db.add(new_log)
                        db.commit()
                        
                        try:
                            await manager.broadcast(json.dumps({
                                "command": "audit_log_update", "time": new_log.created_at.strftime("%H:%M:%S"),
                                "operator": new_log.operator, "action": new_log.action, "target": new_log.target, "status": new_log.status
                            }))
                        except Exception:
                            pass
                    
                    elif cmd != "take_screenshot":
                        print(f"→ Gửi lệnh '{cmd}' tới {target_host}")
                else:
                    if payload.get("command"):
                        for aid, ws in list(manager.active_connections.items()):
                            if aid != agent_id:
                                try:
                                    await ws.send_text(data)
                                except:
                                    pass
            except json.JSONDecodeError:
                await manager.broadcast(f"Agent {agent_id}: {data}")
    except Exception as e:
        print(f"WebSocket error trong vòng lặp chính: {e}")
    finally:
        # --- 🎯 GHI LOG CỨNG KHI MÁY MẤT KẾT NỐI ---
        try:
            is_frontend = (agent_id == "agent_001")
            action_type = "FRONTEND_DISCONNECT" if is_frontend else "AGENT_OFFLINE"
            status_text = "Mất kết nối" if is_frontend else "Offline"
            operator_name = "Hệ thống (System)"
            
            log_out = AuditLog(operator=operator_name, action=action_type, target=agent_id, status=status_text, created_at=datetime.now())
            db.add(log_out)
            db.commit()
            
            # Khối try/except an toàn tuyệt đối chống nghẽn đóng luồng ConnectionState.CLOSED
            try:
                await manager.broadcast(json.dumps({
                    "command": "audit_log_update", "time": log_out.created_at.strftime("%H:%M:%S"),
                    "operator": operator_name, "action": action_type, "target": agent_id, "status": status_text
                }))
            except Exception:
                pass
        except Exception as e:
            print(f"Lỗi ghi database log OFFLINE: {e}")
            
        if agent_id in streaming_agents:
            streaming_agents.discard(agent_id)
        db.close() # Đóng kết nối session an toàn bảo vệ database SQLite
        await manager.disconnect(agent_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)