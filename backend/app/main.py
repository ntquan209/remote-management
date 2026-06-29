from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy.orm import Session
import json

from app.config import settings
from app.database import init_db, SessionLocal
from app.manager import manager
from app.auth_router import router as auth_router
import app.models
from app.models import AuditLog

streaming_agents = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
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

app.include_router(auth_router)

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

@app.websocket("/ws/agent/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect(websocket, agent_id)
    
    global streaming_agents
    db = SessionLocal()

    try:
        is_frontend = agent_id.startswith("agent_001")
        action_type = "FRONTEND_CONNECT" if is_frontend else "AGENT_ONLINE"
        status_text = "Đã kết nối backend" if is_frontend else "Online"
        operator_name = "Hệ thống (System)"
        
        new_log = AuditLog(
            operator=operator_name, action=action_type, target=agent_id, status=status_text, created_at=datetime.now()
        )
        db.add(new_log)
        db.commit()
        
        try:
            await manager.broadcast(json.dumps({
                "command": "audit_log_update",
                "time": new_log.created_at.strftime("%H:%M:%S"),
                "operator": operator_name, "action": action_type, "target": agent_id, "status": status_text
            }))
        except Exception:
            pass
    except Exception:
        pass
    
    online_agents = [aid for aid in manager.active_connections.keys() if aid != agent_id and not aid.startswith("agent_001")]
    if online_agents:
        agent_list_msg = json.dumps({"event": "agent_list", "agents": online_agents})
        await websocket.send_text(agent_list_msg)
    
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
                    event_type = payload["event"]
                    data_content = payload.get("data", {})
                    
                    command_map = {
                        "SHUTDOWN": "shutdown", 
                        "RESTART": "restart",
                        "SCREENSHOT": "take_screenshot", 
                        "START_STREAM": "take_screenshot", 
                        "STOP_STREAM": "stop_stream",
                        "KILL_PROCESS": "kill_process",
                        "REFRESH_PROCS": "get_processes",
                        "APP_CONTROL": "manage_app",
                        "KEYLOGGER_TOGGLE": "toggle_keylogger",
                        "FETCH_FILES": "list_directory",
                        "DOWNLOAD_FILE": "read_file_content",
                        "WEBCAM_START": "get_webcam_frame",
                        "WEBCAM_STOP": "stop_webcam_stream"
                    }
                    
                    cmd = command_map.get(event_type, event_type.lower())
                    if cmd is not None:
                        agent_cmd = {"command": cmd, "data": data_content}
                        sent = await manager.send_to_agent(target_host, json.dumps(agent_cmd))
                        if not sent:
                            try:
                                await websocket.send_text(json.dumps({
                                    "command": "error",
                                    "message": f"Máy trạm [{target_host}] hiện không kết nối hoặc đã offline"
                                }))
                            except Exception:
                                pass
                    
                    log_action = None
                    log_status = "Success"
                    
                    if event_type == "START_STREAM":
                        if target_host not in streaming_agents:
                            streaming_agents.add(target_host)
                            log_action = "START_LIVE_STREAM"
                    elif event_type == "STOP_STREAM":
                        if target_host in streaming_agents:
                            streaming_agents.discard(target_host)
                            log_action = "STOP_LIVE_STREAM"
                            log_status = "Stopped"
                    elif event_type == "SCREENSHOT" and target_host not in streaming_agents:
                        log_action = "TAKE_SCREENSHOT"
                    elif event_type == "KILL_PROCESS":
                        log_action = f"KILL_PID_{data_content.get('pid')}"
                    elif event_type == "APP_CONTROL":
                        app_action = data_content.get("action", "CONTROL")
                        app_name = data_content.get("app_name", "App")
                        log_action = f"{app_action}_APP_{app_name.upper()}"
                    elif event_type == "KEYLOGGER_TOGGLE":
                        kl_state = "START" if data_content.get("capturing", True) else "PAUSE"
                        log_action = f"{kl_state}_KEYLOGGER"
                    elif event_type == "DOWNLOAD_FILE":
                        log_action = "DOWNLOAD_FILE"
                    elif event_type == "WEBCAM_START":
                        log_action = "START_WEBCAM_STREAM"
                    elif event_type == "WEBCAM_STOP":
                        log_action = "STOP_WEBCAM_STREAM"
                        log_status = "Stopped"

                    if log_action:
                        new_log = AuditLog(
                            operator=f"Giảng viên ({agent_id.split('_tab_')[0]})", 
                            action=log_action, 
                            target=target_host, 
                            status=log_status, 
                            created_at=datetime.now()
                        )
                        db.add(new_log)
                        db.commit()
                        
                        try:
                            await manager.broadcast(json.dumps({
                                "command": "audit_log_update", 
                                "time": new_log.created_at.strftime("%H:%M:%S"),
                                "operator": new_log.operator, 
                                "action": new_log.action, 
                                "target": new_log.target, 
                                "status": new_log.status
                            }))
                        except Exception:
                            pass
                            
                else:
                    if payload.get("command") or payload.get("event"):
                        for aid, ws in list(manager.active_connections.items()):
                            if aid != agent_id:
                                try:
                                    await ws.send_text(data)
                                except Exception:
                                    pass
            except json.JSONDecodeError:
                await manager.broadcast(f"Agent {agent_id}: {data}")
    except Exception:
        pass
    finally:
        if agent_id in streaming_agents:
            streaming_agents.discard(agent_id)
        
        await manager.disconnect(agent_id)
        
        try:
            is_frontend = agent_id.startswith("agent_001")
            action_type = "FRONTEND_DISCONNECT" if is_frontend else "AGENT_OFFLINE"
            status_text = "Mất kết nối" if is_frontend else "Offline"
            operator_name = "Hệ thống (System)"
            
            log_out = AuditLog(operator=operator_name, action=action_type, target=agent_id, status=status_text, created_at=datetime.now())
            db.add(log_out)
            db.commit()
            
            try:
                await manager.broadcast(json.dumps({
                    "command": "audit_log_update", "time": log_out.created_at.strftime("%H:%M:%S"),
                    "operator": operator_name, "action": action_type, "target": agent_id, "status": status_text
                }))
            except Exception:
                pass
        except Exception:
            pass
            
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)