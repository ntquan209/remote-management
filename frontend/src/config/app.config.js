/**
 * App Configuration - Cấu hình ứng dụng Frontend
 * 
 * 📌 CHỨC NĂNG:
 * - Định nghĩa các hằng số cấu hình cho toàn bộ frontend
 * - URL kết nối tới backend (HTTP + WebSocket)
 * - Thời gian chờ reconnect
 * 
 * 🔧 CÁC CẤU HÌNH:
 * - API_BASE_URL: URL gốc của FastAPI backend (REST API)
 * - WS_URL: URL gốc của WebSocket endpoint
 * - RECONNECT_INTERVAL: Thời gian chờ trước khi thử kết nối lại (ms)
 */

export const APP_CONFIG = {
    // URL của FastAPI backend (REST API)
    API_BASE_URL: "http://localhost:8000",
    
    // Endpoint WebSocket đã định nghĩa trong backend/app/main.py
    // Kết nối đầy đủ: ws://localhost:8000/ws/agent/{agent_id}
    WS_URL: "ws://localhost:8000/ws/agent", 
    
    // Thời gian chờ trước khi tự động kết nối lại (5 giây)
    RECONNECT_INTERVAL: 5000
};