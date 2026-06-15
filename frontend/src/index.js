/**
 * File chính của Frontend - Ứng dụng Remote Lab Monitor & Control
 * 
 * 📌 CHỨC NĂNG:
 * - Render toàn bộ giao diện người dùng (sidebar, topbar, panels)
 * - Khởi tạo kết nối WebSocket tới backend
 * - Expose các hàm xử lý ra window.onclick để HTML inline onclick gọi được
 * - Xử lý dữ liệu nhận từ WebSocket (screenshot, process list...)
 * 
 * 🤝 QUY ƯỚC AGENT ID:
 * - "agent_001" = Frontend (máy giảng viên - teacher)
 * - "agent-01"  = Agent Python (máy sinh viên - student)
 * 
 * 🔁 LUỒNG LỆNH (Frontend → Backend → Agent Python):
 * 1. Giảng viên click nút Shutdown trên giao diện
 * 2. control.js: emitCommand("SHUTDOWN", targetMachine)
 * 3. socket.js: gửi JSON {"event":"SHUTDOWN","target":"agent-01"}
 * 4. Backend parse, thấy "target":"agent-01" → gửi {"command":"SHUTDOWN"} tới agent-01
 * 5. Agent Python nhận lệnh, thực thi system_manager.shutdown()
 * 
 * ⚠️ IMPORTANT:
 * Các template HTML (panels.js, sidebar.js) dùng onclick="fn()" inline.
 * Vì đây là ES module, các hàm export KHÔNG tự động có ở global scope.
 * Phải gán chúng vào window object.
 */

import { initSocket, onEvent, emitCommand } from './lib/socket.js';
import { renderApp } from './templates/renderer.js';
import { switchPanel } from './utils/dom.js';
import { addMachineOnline, onTargetMachineChange, setTargetMachine } from './components/machine-selector.js';
import { handleScreenTrigger, handleProcesses } from './pages/monitor.js';
import { handleWebcamTrigger, handlePowerCommand, toggleKeyloggerState, clearKeyloggerArea } from './pages/control.js';
import { addAuditRow, logSystemEvent } from './utils/audit.js';

// =============================================
// Bước 1: Render giao diện
// =============================================
renderApp();

// =============================================
// Bước 2: Expose các hàm ra window để HTML onclick hoạt động
// =============================================
window.switchPanel = switchPanel;
window.onTargetMachineChange = onTargetMachineChange;
window.triggerScreen = handleScreenTrigger;
window.triggerWebcam = handleWebcamTrigger;
window.triggerPower = handlePowerCommand;
window.toggleKlState = toggleKeyloggerState;
window.clearKlArea = clearKeyloggerArea;

// Xử lý nút Kill process
window.handleKillProcess = (pid, name) => {
    if (confirm(`Kill process ${name} (PID: ${pid})?`)) {
        emitCommand('KILL_PROCESS', { pid, name });
        addAuditRow('KILL_PROCESS', pid, `Đã kill: ${name}`);
    }
};

// =============================================
// Bước 3: Thiết lập và kết nối WebSocket
// =============================================
const TEACHER_AGENT_ID = "agent_001";  // Frontend = máy giảng viên

// Khi WebSocket kết nối thành công
onEvent('connect', () => {
    console.log(`✓ Frontend (${TEACHER_AGENT_ID}) đã kết nối tới backend`);
    logSystemEvent('FRONTEND_CONNECT', TEACHER_AGENT_ID, 'Đã kết nối backend', true);
});

// Khi WebSocket mất kết nối
onEvent('disconnect', () => {
    console.log(`✗ Frontend (${TEACHER_AGENT_ID}) mất kết nối`);
    logSystemEvent('FRONTEND_DISCONNECT', TEACHER_AGENT_ID, 'Mất kết nối', false);
});

// =============================================
// Bước 4: Xử lý dữ liệu nhận từ backend
// =============================================

// Khi mới kết nối, backend gửi danh sách agent đang online
onEvent('agent_list', (data) => {
    if (data.agents && data.agents.length > 0) {
        data.agents.forEach(agentId => {
            if (agentId !== TEACHER_AGENT_ID) {
                addMachineOnline(agentId);
                logSystemEvent('AGENT_ONLINE', agentId, 'Online', true);
            }
        });
    }
});

// Có agent mới kết nối (backend broadcast báo)
onEvent('agent_connected', (data) => {
    const agentId = data.agent_id || data.data;
    if (agentId && agentId !== TEACHER_AGENT_ID) {
        addMachineOnline(agentId);
        logSystemEvent('AGENT_ONLINE', agentId, 'Online', true);
    }
});

// Xử lý ảnh chụp màn hình (từ agent Python)
onEvent('screenshot', (data) => {
    if (data.data) {
        const display = document.getElementById('screen-display-area');
        if (display) {
            display.innerHTML = `<img src="data:image/png;base64,${data.data}" style="max-width:100%;max-height:280px;object-fit:contain" />`;
        }
    }
});

// Xử lý danh sách tiến trình (từ agent Python)
onEvent('process_list', (data) => {
    handleProcesses(data);
});

// Xử lý thông báo text thuần túy
onEvent('message', (data) => {
    console.log("📩 Thông báo từ hệ thống:", data);
});

// Xử lý kết quả lệnh
onEvent('command_result', (data) => {
    console.log("✅ Kết quả lệnh:", data);
    if (data.status === 'shutting down') {
        addAuditRow('SHUTDOWN', 'agent-01', 'Đã tắt máy thành công');
    }
});

// Xử lý lỗi
onEvent('error', (data) => {
    console.error("❌ Lỗi từ agent:", data);
    addAuditRow('ERROR', 'agent-01', data.message || 'Lỗi không xác định');
});

// Khởi tạo kết nối
initSocket(TEACHER_AGENT_ID);