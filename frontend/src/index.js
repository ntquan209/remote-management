/**
 * File chính của Frontend - Ứng dụng Remote Lab Monitor & Control
 * 
 * 📌 CHỨC NĂNG:
 * - Render toàn bộ giao diện người dùng (sidebar, topbar, panels)
 * - Khởi tạo kết nối WebSocket tới backend
 * - Đăng ký các event listeners cho socket
 * - Gắn sự kiện click cho các button
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. Import renderApp và socket functions
 * 2. renderApp() → vẽ sidebar + topbar + tất cả panels vào DOM
 * 3. initSocket("agent_001") → mở WebSocket tới backend
 * 4. onEvent('message') → lắng nghe dữ liệu từ backend
 * 5. Gắn onclick cho button screenshot
 * 
 * 📡 KẾT NỐI:
 * - WebSocket tới: ws://localhost:8000/ws/agent/agent_001
 * - Agent ID hiện tại đang hardcode là "agent_001"
 */

import { initSocket, onEvent, emitCommand } from './lib/socket.js';
import { renderApp } from './templates/renderer.js';

// Bước 1: Render toàn bộ giao diện (sidebar, topbar, 8 panels)
renderApp();

// Bước 2: Thiết lập agent ID (sau này sẽ lấy từ machine-selector)
const currentAgentId = "agent_001"; 

// Bước 3: Khởi tạo kết nối WebSocket tới backend
initSocket(currentAgentId);

// Bước 4: Lắng nghe thông điệp từ backend
onEvent('message', (data) => {
    console.log("📩 Thông báo từ hệ thống:", data);
    // TODO: Cập nhật UI thông qua dom.js utilities
});

// Bước 5: Gắn sự kiện click cho button chụp màn hình
document.getElementById('btn-screenshot').onclick = () => {
    emitCommand("TAKE_SCREENSHOT");
};