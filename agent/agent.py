"""
Agent Main Application - Ứng dụng chạy trên máy trạm từ xa

📌 CHỨC NĂNG:
- Kết nối tới Backend qua WebSocket
- Lắng nghe lệnh từ Backend
- Thực thi các tác vụ hệ thống (chụp màn hình, kill process, shutdown...)
- Gửi kết quả về Backend

🔁 LUỒNG HOẠT ĐỘNG:
1. Khởi tạo RemoteAgent với agent_id và backend_url
2. run() -> Vòng lặp chính:
   - Nếu chưa kết nối: connect() tới backend, nếu thất bại thì đợi 5s thử lại
   - Nếu đã kết nối: listen() để nhận lệnh từ backend
3. Khi nhận lệnh: handle_command() phân tích lệnh và gọi module tương ứng
4. Kết quả được gửi ngược lại backend qua send_message()

📡 CÁC LỆNH HỖ TRỢ:
- get_system_info -> Lấy thông tin hệ thống
- get_processes -> Lấy danh sách tiến trình
- kill_process -> Tắt một tiến trình
- take_screenshot -> Chụp màn hình
- start_keylogger / stop_keylogger -> Bắt phím
- show_consent -> Hiện thông báo
- shutdown -> Tắt máy
"""

import asyncio
import websockets
import json
import logging
from typing import Optional

# Import các module chức năng
from modules.system import system_manager
from modules.media import media_manager
from modules.keylogger import key_logger
from modules.consent import consent_manager


# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Agent")


class RemoteAgent:
    """Agent từ xa - chạy trên máy sinh viên để thực thi lệnh"""
    
    def __init__(self, agent_id: str, backend_url: str = "ws://localhost:8000/ws/agent"):
        """
        Khởi tạo agent
        
        Args:
            agent_id: Mã định danh duy nhất (vd: "agent-01")
            backend_url: URL của backend WebSocket server
        """
        self.agent_id = agent_id
        self.backend_url = f"{backend_url}/{agent_id}"  # URL đầy đủ tới backend
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
    
    async def connect(self):
        """Kết nối tới backend qua WebSocket"""
        try:
            self.websocket = await websockets.connect(self.backend_url)
            self.is_running = True
            logger.info(f"✓ Đã kết nối tới backend: {self.backend_url}")
            return True
        except Exception as e:
            logger.error(f"Kết nối thất bại: {e}")
            return False
    
    async def disconnect(self):
        """Ngắt kết nối khỏi backend"""
        if self.websocket:
            await self.websocket.close()
            self.is_running = False
            logger.info("✗ Đã ngắt kết nối backend")
    
    async def send_message(self, command: str, data: dict = None):
        """
        Gửi tin nhắn tới backend
        
        Args:
            command: Loại lệnh (vd: "system_info", "screenshot")
            data: Dữ liệu kèm theo (kết quả thực thi)
        
        Cấu trúc tin nhắn JSON gửi đi:
        {
            "agent_id": "agent-01",
            "command": "system_info",
            "data": { ... }
        }
        """
        if not self.websocket:
            return
        
        message = {
            "agent_id": self.agent_id,
            "command": command,
            "data": data or {}
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Lỗi gửi tin nhắn: {e}")
    
    async def handle_command(self, message: dict):
        """
        Xử lý lệnh nhận được từ backend
        
        Phân tích lệnh và gọi module tương ứng:
        - system_manager: cho system_info, processes, kill, shutdown
        - media_manager: cho screenshot
        - key_logger: cho keylogger
        - consent_manager: cho hiển thị thông báo
        """
        command = message.get("command")
        data = message.get("data", {})
        
        try:
            if command == "get_system_info":
                # Lấy thông tin hệ thống (CPU, RAM, Disk...)
                result = system_manager.get_system_info()
                await self.send_message("system_info", result)
            
            elif command == "get_processes":
                # Lấy danh sách tiến trình đang chạy
                result = system_manager.get_process_list()
                await self.send_message("process_list", {"processes": result})
            
            elif command == "kill_process":
                # Tắt một tiến trình theo PID
                pid = data.get("pid")
                success = system_manager.kill_process(pid)
                await self.send_message("kill_result", {"pid": pid, "success": success})
            
            elif command == "take_screenshot":
                # Chụp ảnh màn hình
                screenshot = media_manager.take_screenshot()
                # Chuyển đổi bytes sang hex để gửi qua WebSocket text
                await self.send_message("screenshot", {"data": screenshot.hex() if screenshot else None})
            
            elif command == "start_keylogger":
                # Bắt đầu ghi nhận phím bấm
                key_logger.start()
                await self.send_message("keylogger_status", {"status": "started"})
            
            elif command == "stop_keylogger":
                # Dừng ghi nhận phím và gửi log về
                key_logger.stop()
                logs = key_logger.get_logs()
                await self.send_message("keylogger_logs", {"logs": logs})
            
            elif command == "show_consent":
                # Hiển thị popup thông báo cho người dùng máy trạm
                title = data.get("title", "Notice")
                message_text = data.get("message", "")
                consent_manager.show_consent_popup(title, message_text)
            
            elif command == "shutdown":
                # Tắt máy (có thể delay)
                delay = data.get("delay", 0)
                system_manager.shutdown(delay)
                await self.send_message("command_result", {"status": "shutting down"})
            
            else:
                logger.warning(f"Lệnh không xác định: {command}")
        
        except Exception as e:
            logger.error(f"Lỗi thực thi lệnh: {e}")
            await self.send_message("error", {"message": str(e)})
    
    async def listen(self):
        """Lắng nghe và xử lý tin nhắn từ backend"""
        try:
            # Vòng lặp bất đồng bộ: nhận từng tin nhắn từ WebSocket
            async for message_str in self.websocket:
                try:
                    message = json.loads(message_str)
                    await self.handle_command(message)
                except json.JSONDecodeError:
                    logger.error(f"JSON không hợp lệ: {message_str}")
        except Exception as e:
            logger.error(f"Lỗi lắng nghe: {e}")
    
    async def run(self):
        """
        Vòng lặp chính của agent
        
        Luồng:
        1. Nếu chưa kết nối -> thử connect() tới backend
        2. Nếu kết nối thành công -> listen() để nhận lệnh
        3. Nếu có lỗi -> disconnect() và đợi 5s thử lại
        """
        while True:
            if not self.is_running:
                if not await self.connect():
                    await asyncio.sleep(5)  # Thử lại sau 5 giây
                    continue
            
            try:
                await self.listen()
            except Exception as e:
                logger.error(f"Lỗi runtime: {e}")
                await self.disconnect()
                await asyncio.sleep(5)


async def main():
    """Điểm vào chính - khởi tạo và chạy agent"""
    agent = RemoteAgent(agent_id="agent-01")
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Đang tắt agent...")
        await agent.disconnect()


if __name__ == "__main__":
    asyncio.run(main())