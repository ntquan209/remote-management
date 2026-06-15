/**
 * Socket Library - Quản lý kết nối WebSocket Native (Cập nhật tương thích FastAPI)
 * 📌 CHỨC NĂNG:
 * - Khởi tạo kết nối WebSocket thuần (Native) tới backend FastAPI
 * - Tự động kết nối lại khi mất kết nối
 * - Đồng bộ linh hoạt giữa trường "event" (Frontend) và trường "command" (Agent)
 * - Đăng ký listener cho các sự kiện tùy chỉnh
 */

import { APP_CONFIG } from '../config/app.config.js';

let socket = null;
let eventHandlers = {};  // Map lưu các event listeners: { "connect": fn, "agent_send_screen": fn, ... }

/**
 * Khởi tạo kết nối WebSocket tới backend
 * @param {string} agentId - ID của agent (vd: "agent_001")
 */
export const initSocket = (agentId) => {
    // Đóng kết nối cũ nếu có
    if (socket) socket.close();

    const url = `${APP_CONFIG.WS_URL}/${agentId}`;

    // Tạo kết nối WebSocket mới (Native)
    socket = new WebSocket(url);

    // --- Khi kết nối thành công ---
    socket.onopen = () => {
        console.log(`✓ [WS] Đã kết nối với định danh: ${agentId}`);
        if (typeof eventHandlers['connect'] === 'function') eventHandlers['connect']();
    };

    // --- Khi nhận được dữ liệu từ backend ---
    socket.onmessage = (event) => {
        const rawData = event.data;

        try {
            // Thử parse dữ liệu dạng JSON
            const json = JSON.parse(rawData);

            // 🎯 ĐIỂM CẬP NHẬT CHÍ CHÓC: Hỗ trợ đọc cả khóa 'event' từ FE hoặc khóa 'command' từ Agent gửi lên
            const eventKey = json.event || json.command;

            if (eventKey && eventHandlers[eventKey]) {
                eventHandlers[eventKey](json);
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
        setTimeout(() => {
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
 */
export const getSocket = () => socket;

/**
 * Đăng ký hàm xử lý cho một sự kiện
 * @param {string} event - Tên sự kiện: "connect", "agent_send_screen", "agent_send_procs"
 * @param {function} callback - Hàm xử lý khi sự kiện xảy ra
 */
export const onEvent = (event, callback) => {
    eventHandlers[event] = callback;
};

/**
 * Gửi lệnh tới Backend/Agent qua WebSocket
 */
export const emitCommand = (type, payload = null) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        let messageObj;
        if (typeof payload === 'string') {
            messageObj = { event: type, target: payload };
        } else if (payload) {
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