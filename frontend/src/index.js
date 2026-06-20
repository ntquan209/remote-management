/**
 * File chính của Frontend - Ứng dụng Remote Lab Monitor & Control
 * (Bản cấu trúc ID Động: Giúp mở vô số Tab xem vô số máy cùng lúc không bị đá mạng)
 */

import { initSocket, onEvent, emitCommand } from './lib/socket.js';
import { renderApp } from './templates/renderer.js';
import { switchPanel } from './utils/dom.js';
import { addMachineOnline, onTargetMachineChange } from './components/machine-selector.js';
import { handleScreenTrigger, handleIncomingScreen, handleProcesses, handleIncomingAuditLog, fetchAndRenderAuditLogs } from './pages/monitor.js';
import { handleWebcamTrigger, handlePowerCommand, toggleKeyloggerState, clearKeyloggerArea } from './pages/control.js';
import { addAuditRow, logSystemEvent } from './utils/audit.js';
import { isAuthenticated, getUser, logout, hasRole, adminListUsers, adminUpdateRole, adminDeleteUser, adminToggleActive } from './lib/api.js';
import { renderAuthPage } from './pages/auth.js';

// =============================================
// Bước 1: Khởi dựng khung xương giao diện (DOM)
// =============================================
renderApp();

    // =============================================
    // Bước 3: Expose các hàm ra window để HTML onclick hoạt động
    // =============================================
    window.switchPanel = switchPanel;
    window.onTargetMachineChange = onTargetMachineChange;
    window.triggerScreen = handleScreenTrigger;
    window.triggerWebcam = handleWebcamTrigger;
    window.triggerPower = handlePowerCommand;
    window.toggleKlState = toggleKeyloggerState;
    window.clearKlArea = clearKeyloggerArea;

// Xử lý nút Kill tiến trình từ xa
window.handleKillProcess = (pid, name) => {
    if (confirm(`Bạn có chắc chắn muốn kết liễu tiến trình ${name} (PID: ${pid}) không?`)) {
        emitCommand('KILL_PROCESS', null, { pid: parseInt(pid), name: name });
        addAuditRow('KILL_PROCESS', pid, `Đã bắn lệnh kết liễu: ${name}`);
    }
};

// =============================================
// Bước 3: Đăng ký các sự kiện hứng dữ liệu WebSocket
// =============================================

// 🎯 ĐIỂM SỬA ĐỔI LỚN: Sinh ID động duy nhất cho Tab này (Ví dụ: agent_001_tab_f4b2)
// Giúp Server hiểu đây là các kết nối quản trị độc lập, không đá ghế nhau.
const UNIQUE_TAB_SUFFIX = Math.random().toString(36).substring(2, 6);
const TEACHER_AGENT_ID = `agent_001_tab_${UNIQUE_TAB_SUFFIX}`;

onEvent('connect', () => {
    console.log(`✓ Frontend Tab (${TEACHER_AGENT_ID}) đã kết nối tới backend.`);
    logSystemEvent('FRONTEND_CONNECT', TEACHER_AGENT_ID, 'Đã kết nối quản trị', true);
});

onEvent('disconnect', () => {
    console.log(`✗ Frontend Tab (${TEACHER_AGENT_ID}) mất kết nối.`);
    logSystemEvent('FRONTEND_DISCONNECT', TEACHER_AGENT_ID, 'Mất kết nối', false);
});

// Tiếp nhận danh sách các máy trạm đang trực tuyến ban đầu từ Server
onEvent('agent_list', (data) => {
    if (data.agents && Array.isArray(data.agents)) {
        data.agents.forEach(agentId => {
            // Chỉ thêm vào dropdown các máy trạm là sinh viên, bỏ qua các tab quản trị khác
            if (!agentId.startsWith("agent_001")) {
                addMachineOnline(agentId);
            }
        });
    }
});

// Tiếp nhận thông báo có máy trạm mới vừa Onl mạng
onEvent('agent_connected', (data) => {
    const agentId = data.agent_id || data.data;
    if (agentId && !agentId.startsWith("agent_001")) {
        addMachineOnline(agentId);
    }
});

// Điều hướng ảnh màn hình về hàm xử lý cô lập đa tab của monitor.js
onEvent('agent_send_screen', (data) => {
    handleIncomingScreen(data);
});

// Điều hướng danh sách tiến trình về đúng luồng lọc đa nhiệm
onEvent('agent_send_procs', (data) => {
    handleProcesses(data);
});

// Đón nhận gói tin nhật ký hành động real-time dội từ database qua cổng mạng
onEvent('audit_log_update', (data) => {
    handleIncomingAuditLog(data);
});

onEvent('message', (data) => {
    console.log("📩 Thông báo hệ thống:", data);
});

onEvent('error', (data) => {
    console.error("❌ Lỗi từ hệ thống Agent:", data);
});

// =============================================
// Bước 4: Chạy tuần tự luồng nạp dữ liệu an toàn
// =============================================
const bootstrapApp = async () => {
    try {
        // 1. Nạp dữ liệu nhật ký cũ từ SQLite lên bảng trước để lấp đầy DOM ổn định
        await fetchAndRenderAuditLogs();

        // 2. Sau khi dữ liệu tĩnh lên thong thả, mới chính thức mở cổng kết nối mạng đón dữ liệu tốc độ cao
        initSocket(TEACHER_AGENT_ID);
    } catch (error) {
        console.error("❌ Lỗi trong quá trình khởi động luồng dữ liệu App:", error);
        initSocket(TEACHER_AGENT_ID);
    }
};

// Kích hoạt bệ phóng cỗ máy đa nhiệm
bootstrapApp();