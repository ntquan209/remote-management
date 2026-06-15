"""
Connection Manager - Quản lý kết nối WebSocket

📌 CHỨC NĂNG:
- Quản lý danh sách các agent đang kết nối WebSocket
- Chấp nhận/ngắt kết nối agent
- Gửi tin nhắn tới một hoặc nhiều agent
- Dọn dẹp khi server shutdown

🗂️ CẤU TRÚC DỮ LIỆU:
- active_connections: Dict {agent_id: WebSocket} - Map ID -> kết nối
- agents: Set[str] - Tập hợp các agent ID đang online

🔁 LUỒNG HOẠT ĐỘNG:
1. connect() -> Chấp nhận WebSocket, lưu vào dict và set
2. disconnect() -> Xóa khỏi dict và set
3. broadcast() -> Gửi tin nhắn tới TẤT CẢ agent
4. send_to_agent() -> Gửi tin nhắn tới MỘT agent cụ thể
5. cleanup() -> Đóng toàn bộ kết nối khi server tắt
"""

from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    """Quản lý các kết nối WebSocket"""
    
    def __init__(self):
        # Format: {agent_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Danh sách agent_id đang online
        self.agents: Set[str] = set()
    
    async def connect(self, websocket: WebSocket, agent_id: str):
        """
        Đăng ký kết nối mới cho agent
        
        Các bước:
        1. Chấp nhận handshake WebSocket (websocket.accept())
        2. Lưu WebSocket vào dictionary với key = agent_id
        3. Thêm agent_id vào set agents
        """
        await websocket.accept()
        self.active_connections[agent_id] = websocket
        self.agents.add(agent_id)
        print(f"✓ Agent {agent_id} connected")
    
    async def disconnect(self, agent_id: str):
        """
        Ngắt kết nối agent
        
        Xóa agent khỏi cả dictionary và set
        """
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]
            self.agents.discard(agent_id)
            print(f"✗ Agent {agent_id} disconnected")
    
    async def broadcast(self, message: str):
        """
        Gửi tin nhắn tới tất cả agent đang kết nối
        
        Duyệt qua từng agent trong active_connections,
        gửi text message qua WebSocket của họ.
        Nếu lỗi thì in ra console nhưng không dừng vòng lặp.
        """
        for agent_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to {agent_id}: {e}")
    
    async def send_to_agent(self, agent_id: str, message: str):
        """
        Gửi tin nhắn tới một agent cụ thể
        
        Trả về True nếu gửi thành công, False nếu thất bại
        """
        if agent_id in self.active_connections:
            try:
                await self.active_connections[agent_id].send_text(message)
                return True
            except Exception as e:
                print(f"Error sending to {agent_id}: {e}")
                return False
        return False
    
    async def cleanup(self):
        """Dọn dẹp toàn bộ kết nối khi server shutdown"""
        for agent_id in list(self.active_connections.keys()):
            await self.disconnect(agent_id)
        print("✓ Connection manager cleaned up")


# Global connection manager instance - dùng chung cho toàn bộ ứng dụng
manager = ConnectionManager()