/**
 * Socket Library - Quản lý kết nối WebSocket Native
 * 
 * 📌 CHỨC NĂNG:
 * - Khởi tạo kết nối WebSocket thuần (Native) tới backend FastAPI
 * - Quản lý sự kiện: connect, message, disconnect, error
 * - Tự động kết nối lại khi mất kết nối
 * - Đăng ký listener cho các sự kiện tùy chỉnh
 * - Gửi lệnh dạng JSON tới backend
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. initSocket(agentId) → Tạo WebSocket tới ws://localhost:8000/ws/agent/{agentId}
 * 2. WebSocket.onopen → Gọi handler 'connect' nếu đã đăng ký
 * 3. WebSocket.onmessage → Parse JSON hoặc text, gọi handler tương ứng
 * 4. WebSocket.onclose → Gọi handler 'disconnect', tự động reconnect sau 5s
 * 5. onEvent(event, callback) → Đăng ký handler cho event cụ thể
 * 6. emitCommand(type, payload) → Gửi JSON { event, data } tới backend
 * 
 * 📡 GIAO THỨC:
 * - Gửi: JSON { event: "TAKE_SCREENSHOT", data: {...} }
 * - Nhận: JSON { event: "message", ... } hoặc text thuần
 * - Không dùng Socket.io, chỉ dùng WebSocket API của trình duyệt
 */

import { APP_CONFIG } from '../config/app.config.js';

let socket = null;
let eventHandlers = {};  // Map lưu các event listeners: { "connect": fn, "message": fn, ... }

/**
 * Khởi tạo kết nối WebSocket tới backend
 * @param {string} agentId - ID của agent (vd: "agent_001")
 * 
 * URL kết nối: APP_CONFIG.WS_URL + "/" + agentId
 * Ví dụ: ws://localhost:8000/ws/agent/agent_001
 */
export const initSocket = (agentId) => {
    // Đóng kết nối cũ nếu có
    if (socket) socket.close();

    const url = `${APP_CONFIG.WS_URL}/${agentId}`;
    
    // Tạo kết nối WebSocket mới (Native - không cần thư viện)
    socket = new WebSocket(url);

    // --- Khi kết nối thành công ---
    socket.onopen = () => {
        console.log(`✓ [WS] Đã kết nối tới Agent: ${agentId}`);
        if (typeof eventHandlers['connect'] === 'function') eventHandlers['connect']();
    };

    // --- Khi nhận được dữ liệu từ backend ---
    socket.onmessage = (event) => {
        const rawData = event.data;
        
        try {
            // Thử parse dữ liệu dạng JSON
            const json = JSON.parse(rawData);
            // Nếu có event type cụ thể, gọi handler tương ứng
            if (json.event && eventHandlers[json.event]) {
                eventHandlers[json.event](json);
            } else if (eventHandlers['message']) {
                eventHandlers['message'](json);
            }
        } catch (e) {
            // Nếu không phải JSON (text thuần), gọi handler 'message'
            if (eventHandlers['message']) {
                eventHandlers['message'](rawData);
            }
        }
    };

    // --- Khi kết nối bị đóng ---
    socket.onclose = (e) => {
        console.log(`✗ [WS] Mất kết nối. Code: ${e.code}`);
        if (typeof eventHandlers['disconnect'] === 'function') eventHandlers['disconnect'](e);

        // Tự động kết nối lại sau một khoảng thời gian
        const timer = setTimeout(() => {
            console.log("... Đang kết nối lại");
            initSocket(agentId);
        }, APP_CONFIG.RECONNECT_INTERVAL);
    };

    // --- Khi có lỗi WebSocket ---
    socket.onerror = (err) => {
        console.error("! [WS] Lỗi Socket:", err);
    };

    return socket;
};

/**
 * Lấy đối tượng WebSocket hiện tại
 * Dùng để kiểm tra trạng thái kết nối: getSocket().readyState
 */
export const getSocket = () => socket;

/**
 * Đăng ký hàm xử lý cho một sự kiện
 * @param {string} event - Tên sự kiện: "connect", "message", "disconnect", hoặc event tùy chỉnh
 * @param {function} callback - Hàm xử lý khi sự kiện xảy ra
 * 
 * Ví dụ:
 * onEvent('message', (data) => console.log(data))
 * onEvent('screenshot', (json) => displayImage(json.data))
 */
export const onEvent = (event, callback) => {
    eventHandlers[event] = callback;
};

/**
 * Gửi lệnh tới Backend/Agent qua WebSocket
 * @param {string} type - Loại lệnh (vd: "SHUTDOWN", "SCREENSHOT")
 * @param {any} payload - Dữ liệu kèm theo
 *   - Nếu là string (tên máy): gửi dạng {"event":type, "target":payload}
 *   - Nếu là object: gửi dạng {"event":type, "data":payload}
 *   - null: gửi dạng {"event":type}
 * 
 * Backend xử lý:
 * - Có "target" → chuyển tiếp tới agent đó (định dạng {command, data})
 * - Có "data" → broadcast tới tất cả agent
 */
export const emitCommand = (type, payload = null) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        let messageObj;
        if (typeof payload === 'string') {
            // payload là tên agent mục tiêu (vd: "agent-01")
            messageObj = { event: type, target: payload };
        } else if (payload) {
            // payload là object data
            messageObj = { event: type, data: payload };
        } else {
            messageObj = { event: type };
        }
        const data = JSON.stringify(messageObj);
        socket.send(data);
    } else {
        console.error("! Không thể gửi: WebSocket chưa kết nối.");
    }
};
