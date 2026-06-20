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
import { isAuthenticated, getUser, logout, hasRole, adminListUsers, adminUpdateRole, adminDeleteUser, adminToggleActive } from './lib/api.js';
import { renderAuthPage } from './pages/auth.js';

// =============================================
// Bước 1: Kiểm tra xác thực
// =============================================
// Nếu chưa đăng nhập → render trang auth và dừng lại
if (!isAuthenticated()) {
    renderAuthPage();
} else {
    // =============================================
    // Bước 2: Render giao diện chính (đã đăng nhập)
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

    // Xử lý nút Kill process
    window.handleKillProcess = (pid, name) => {
        if (confirm(`Kill process ${name} (PID: ${pid})?`)) {
            emitCommand('KILL_PROCESS', { pid, name });
            addAuditRow('KILL_PROCESS', pid, `Đã kill: ${name}`);
        }
    };

    // Thêm nút đăng xuất vào topbar
    const user = getUser();
    if (user) {
        // Thêm thông tin user và nút logout vào topbar
        const appendUserInfo = () => {
            const machineInfo = document.querySelector('.machine-info');
            if (machineInfo) {
                machineInfo.innerHTML += `
                    <span style="color:var(--text-muted);font-size:12px;border-left:1px solid var(--border-color);padding-left:12px">
                        👤 ${user.full_name || user.username} (${user.role})
                    </span>
                    <button class="btn" style="font-size:11px;padding:4px 10px;background:#334155;color:var(--text-title)" onclick="handleLogout()">
                        Đăng xuất
                    </button>
                `;
            }
        };
        // Chờ DOM render xong rồi mới append
        setTimeout(appendUserInfo, 100);
        
        // Cập nhật hiển thị quyền tài khoản trên dashboard
        const updateRoleDisplay = () => {
            const roleEl = document.getElementById('user-role-display');
            if (roleEl) {
                const roleMap = { admin: 'Quản trị viên (Admin)', teacher: 'Giảng viên (Teacher)', student: 'Sinh viên (Student)' };
                roleEl.textContent = roleMap[user.role] || user.role;
            }
        };
        setTimeout(updateRoleDisplay, 200);
    }

    // =============================================
    // Admin functions (expose ra window)
    // =============================================
    if (hasRole('admin')) {
        window.adminListUsers = adminListUsers;
        window.adminUpdateRole = adminUpdateRole;
        window.adminDeleteUser = adminDeleteUser;
        window.adminToggleActive = adminToggleActive;
        window.loadAdminUsers = async () => {
            try {
                const users = await adminListUsers();
                const tbody = document.querySelector('#admin-users-table tbody');
                if (!tbody) return;
                tbody.innerHTML = users.map(u => `
                    <tr>
                        <td>${u.id}</td>
                        <td>${u.username}</td>
                        <td>${u.email}</td>
                        <td>${u.full_name || '-'}</td>
                        <td>
                            <select class="select-role" data-user-id="${u.id}" onchange="adminUpdateRole(${u.id}, this.value).then(r => alert(r.message)).catch(e => alert(e.message))">
                                <option value="student" ${u.role === 'student' ? 'selected' : ''}>Sinh viên</option>
                                <option value="teacher" ${u.role === 'teacher' ? 'selected' : ''}>Giảng viên</option>
                                <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                            </select>
                        </td>
                        <td>
                            <span class="badge-status ${u.is_active ? 'run' : 'stop'}">${u.is_active ? 'Hoạt động' : 'Đã khóa'}</span>
                        </td>
                        <td>
                            <button class="btn" style="font-size:11px;padding:3px 8px;background:var(--warning);color:#0f172a" onclick="adminToggleActive(${u.id}).then(r => { alert(r.message); loadAdminUsers(); }).catch(e => alert(e.message))">
                                ${u.is_active ? 'Khóa' : 'Mở khóa'}
                            </button>
                            <button class="btn danger" style="font-size:11px;padding:3px 8px" onclick="if(confirm('Xóa user ${u.username}?')) adminDeleteUser(${u.id}).then(r => { alert(r.message); loadAdminUsers(); }).catch(e => alert(e.message))">
                                Xóa
                            </button>
                        </td>
                    </tr>
                `).join('');
            } catch (err) {
                alert('Lỗi tải danh sách user: ' + err.message);
            }
        };
    }

    // =============================================
    // Role-based UI: Ẩn các chức năng không phù hợp
    // =============================================
    const applyRoleBasedUI = () => {
        // Student: chỉ xem dashboard, không có quyền điều khiển
        if (!hasRole('teacher')) {
            // Ẩn các nav item chỉ dành cho teacher/admin
            const navItems = document.querySelectorAll('.nav-item');
            navItems.forEach(item => {
                const panel = item.getAttribute('onclick');
                if (panel && (panel.includes('process') || panel.includes('screen') || panel.includes('keylog') || panel.includes('webcam') || panel.includes('power'))) {
                    item.style.display = 'none';
                }
            });
            // Ẩn các section nav không cần thiết
            document.querySelectorAll('.nav-section').forEach(s => {
                if (s.textContent.includes('ĐIỀU KHIỂN') || s.textContent.includes('MONITOR')) {
                    s.style.display = 'none';
                }
            });
        }
        // Admin: hiển thị thêm mục Quản trị
        if (hasRole('admin')) {
            // Thêm nav item admin vào sidebar
            const monitoringSection = document.querySelector('.nav-section');
            if (monitoringSection) {
                const adminNav = document.createElement('div');
                adminNav.className = 'nav-item';
                adminNav.setAttribute('onclick', "switchPanel('admin')");
                adminNav.innerHTML = '⚙️ Quản trị hệ thống';
                monitoringSection.parentNode.insertBefore(adminNav, monitoringSection.nextSibling);
            }
        }
    };

    // Xử lý đăng xuất
    window.handleLogout = () => {
        if (confirm('Bạn có chắc muốn đăng xuất?')) {
            logout();
        }
    };

    // =============================================
    // Bước 4: Thiết lập và kết nối WebSocket
    // =============================================
    const TEACHER_AGENT_ID = "agent_001";

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
    // Bước 5: Xử lý dữ liệu nhận từ backend
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

    // Áp dụng giao diện theo role sau khi DOM render xong
    setTimeout(() => {
        applyRoleBasedUI();
        if (hasRole('admin')) {
            // Tự động load danh sách user nếu là admin
            setTimeout(() => {
                if (typeof window.loadAdminUsers === 'function') {
                    window.loadAdminUsers();
                }
            }, 200);
        }
    }, 150);

    // Khởi tạo kết nối WebSocket
    initSocket(TEACHER_AGENT_ID);
}
