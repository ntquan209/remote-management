/**
 * File chính của Frontend - Ứng dụng Remote Lab Monitor & Control
 * (Bản cấu trúc ID Động: Giúp mở vô số Tab xem vô số máy cùng lúc không bị đá mạng)
 */

import { initSocket, onEvent, emitCommand } from './lib/socket.js';
import { renderApp } from './templates/renderer.js';
import { switchPanel } from './utils/dom.js';
import { addMachineOnline, onTargetMachineChange } from './components/machine-selector.js';
import {
    handleScreenTrigger,
    handleIncomingScreen,
    handleProcesses,
    handleIncomingAuditLog,
    fetchAndRenderAuditLogs,
    handleIncomingWebcam,
    handleFileList,
    handleIncomingKeylog,
    toggleKlState,
    clearKlArea
} from './pages/monitor.js';
import { handleWebcamTrigger, handlePowerCommand } from './pages/control.js';
import { addAuditRow, logSystemEvent } from './utils/audit.js';
import { isAuthenticated, getUser, logout, hasRole, adminListUsers, adminUpdateRole, adminDeleteUser, adminToggleActive } from './lib/api.js';
import { renderAuthPage } from './pages/auth.js';

// =============================================
// Bước 1: Kiểm tra xác thực
// =============================================
// Hard refresh: Xóa cache cũ nếu có lỗi
// Xóa token cũ hết hạn - thử gọi API /api/me để kiểm tra token còn sống không
const checkAuth = async () => {
    // Xóa cache cũ - hard reset!
    const token = localStorage.getItem('auth_token');

    // Nếu không có token → chắc chắn chưa login
    if (!token) {
        console.log('🔐 Không tìm thấy token → render auth page');
        renderAuthPage();
        return false;
    }

    // Có token, kiểm tra backend có chạy không
    try {
        const response = await fetch('http://localhost:8000/api/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            console.log('🔐 Token hợp lệ → render app');
            return true; // Token còn hiệu lực
        }

        // Token hết hạn (401) → xóa và về trang login
        console.log('🔐 Token hết hạn → xóa và về login');
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        renderAuthPage();
        return false;
    } catch (e) {
        // Backend chưa chạy → xóa token cũ và về trang login
        console.log('🔐 Backend không chạy được → xóa token cũ, về login');
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        renderAuthPage();
        return false;
    }
};

// Bắt đầu kiểm tra
const startApp = async () => {
    const authenticated = await checkAuth();
    if (!authenticated) return;

    console.log('🔐 Đã đăng nhập → render app');
    // =============================================
    // Bước 2: Render giao diện chính (đã đăng nhập)
    // =============================================
    renderApp();

    // =============================================
    // Expose các hàm ra window để HTML onclick hoạt động
    // =============================================
    window.switchPanel = switchPanel;
    window.onTargetMachineChange = onTargetMachineChange;
    window.triggerScreen = handleScreenTrigger;
    window.triggerWebcam = handleWebcamTrigger;
    window.triggerPower = handlePowerCommand;

    // 🎯 SỬA CHỐT ĐỒNG BỘ: Định tuyến trúng hàm xử lý chuẩn của monitor.js điều phối cờ phẳng Backend
    window.toggleKlState = toggleKlState;
    window.clearKlArea = clearKlArea;

    // Xử lý nút Kill tiến trình từ xa
    window.handleKillProcess = (pid, name) => {
        if (confirm(`Bạn có chắc chắn muốn kết liễu tiến trình ${name} (PID: ${pid}) không?`)) {
            // Lấy target machine từ dropdown
            const machineSelect = document.getElementById('machine-select');
            const targetMachine = machineSelect ? machineSelect.value : null;
            if (!targetMachine) {
                alert('Vui lòng chọn máy trạm mục tiêu trước!');
                return;
            }
            emitCommand('KILL_PROCESS', targetMachine, { pid: parseInt(pid), name: name });
            addAuditRow('KILL_PROCESS', pid, `Đã gửi lệnh kill PID ${pid} tới ${targetMachine}`);
        }
    };

    // Xử lý đăng xuất
    window.handleLogout = () => {
        if (confirm('Bạn có chắc muốn đăng xuất?')) {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
            window.location.reload();
        }
    };

    // Cập nhật hiển thị quyền tài khoản trên dashboard + topbar
    const user = getUser();
    if (user) {
        setTimeout(() => {
            // Cập nhật dashboard
            const roleEl = document.getElementById('user-role-display');
            if (roleEl) {
                const roleMap = { admin: 'Quản trị viên (Admin)', teacher: 'Giảng viên (Teacher)', student: 'Sinh viên (Student)' };
                roleEl.textContent = roleMap[user.role] || user.role;
            }
            // Cập nhật topbar: tên user + nút logout
            const userInfoArea = document.getElementById('user-info-area');
            if (userInfoArea) {
                userInfoArea.innerHTML = `
                    <span style="color:var(--text-muted);font-size:12px;border-left:1px solid var(--border-color);padding-left:12px">
                        👤 ${user.full_name || user.username} (${user.role})
                    </span>
                    <button class="btn" style="font-size:11px;padding:4px 10px;background:#334155;color:var(--text-title)" onclick="handleLogout()">
                        Đăng xuất
                    </button>
                `;
            }
        }, 200);
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
            const navItems = document.querySelectorAll('.nav-item');
            navItems.forEach(item => {
                const panel = item.getAttribute('onclick');
                if (panel && (panel.includes('process') || panel.includes('screen') || panel.includes('keylog') || panel.includes('webcam') || panel.includes('power'))) {
                    item.style.display = 'none';
                }
            });
            document.querySelectorAll('.nav-section').forEach(s => {
                if (s.textContent.includes('ĐIỀU KHIỂN') || s.textContent.includes('MONITOR')) {
                    s.style.display = 'none';
                }
            });
        }
        // Admin: hiển thị thêm mục Quản trị
        if (hasRole('admin')) {
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

    // =============================================
    // Đăng ký các sự kiện WebSocket
    // =============================================

    // 🎯 Sinh ID động duy nhất cho Tab này
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

    onEvent('agent_list', (data) => {
        if (data.agents && Array.isArray(data.agents)) {
            data.agents.forEach(agentId => {
                if (!agentId.startsWith("agent_001")) {
                    addMachineOnline(agentId);
                }
            });
        }
    });

    onEvent('agent_connected', (data) => {
        const agentId = data.agent_id || data.data;
        if (agentId && !agentId.startsWith("agent_001")) {
            addMachineOnline(agentId);
        }
    });

    onEvent('agent_send_screen', (data) => {
        handleIncomingScreen(data);
    });

    onEvent('agent_send_procs', (data) => {
        handleProcesses(data);
    });

    onEvent('audit_log_update', (data) => {
        handleIncomingAuditLog(data);
    });

    // 🚀 ĐOẠN ĐĂNG KÝ SỰ KIỆN MỚI CHO WEBCAM, SANDBOX, KEYLOGGER
    onEvent('agent_send_webcam', (data) => {
        handleIncomingWebcam(data);
    });

    onEvent('agent_send_files', (data) => {
        handleFileList(data);
    });

    onEvent('agent_send_key', (data) => {
        handleIncomingKeylog(data);
    });

    // 🎯 LUỒNG TIẾP NHẬN DATA FILE BASE64 VÀ ÉP TRÌNH DUYỆT TẢI XUỐNG CỨNG
    onEvent('agent_download_ready', (data) => {
        const incomingMachine = data.machine_name;
        const activeSelection = document.getElementById('machine-select')?.value;

        if (activeSelection && incomingMachine !== activeSelection) return;

        if (!data.file_base64 || !data.file_name) {
            console.error("❌ [DOWNLOAD] Thiếu dữ liệu file_name hoặc file_base64 trong phản hồi:", data);
            alert("Tải file thất bại: Thiếu dữ liệu từ máy trạm!");
            return;
        }

        // Kiểm tra base64 hợp lệ trước khi decode
        if (typeof data.file_base64 !== 'string' || data.file_base64.length < 10) {
            console.error("❌ [DOWNLOAD] Dữ liệu base64 không hợp lệ (quá ngắn hoặc không đúng định dạng)");
            alert("Dữ liệu file từ máy trạm bị hỏng hoặc rỗng!");
            return;
        }

        try {
            console.log(`💾 Đang tiến hành giải mã và tải tệp tin: ${data.file_name} (${Math.round(data.file_base64.length * 0.75 / 1024)} KB)`);

            // Sử dụng fetch với blob để xử lý base64 an toàn hơn
            const byteCharacters = atob(data.file_base64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'application/octet-stream' });

            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = data.file_name;

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(link.href);

            console.log(`✅ Đã tải xuống thành công tệp tin: ${data.file_name}`);
        } catch (error) {
            console.error("❌ Lỗi xử lý giải mã tệp tin tải về:", error);
            alert(`Không thể giải mã tệp tin "${data.file_name}" từ máy trạm! Lỗi: ${error.message}`);
        }
    });

    onEvent('message', (data) => {
        console.log("📩 Thông báo hệ thống:", data);
    });

    onEvent('error', (data) => {
        console.error("❌ Lỗi từ hệ thống:", data);
        // Hiển thị thông báo lỗi trực quan trên giao diện
        const msg = data.message || (typeof data === 'string' ? data : JSON.stringify(data));
        if (msg) {
            const errMsg = data.message || msg || '';
            // Nếu là lỗi máy trạm offline, reset screen display
            if (errMsg.includes('không kết nối') || errMsg.includes('offline') || errMsg.includes('offline')) {
                const display = document.getElementById('screen-display-area');
                if (display) {
                    display.innerHTML = `
                        <div style="display:flex; flex-direction:column; align-items:center; gap:10px; padding: 40px 0;">
                            <i class="ti ti-cloud-off" style="font-size:48px; color:var(--danger)"></i>
                            <span style="color:var(--danger); font-weight:600">${data.message}</span>
                        </div>`;
                }
            }
            
            // Nếu là lỗi keylogger không khả dụng, hiển thị cảnh báo trong key-stream-area
            if (msg.includes('Keylogger') || msg.includes('keylogger')) {
                const klArea = document.getElementById('key-stream-area');
                if (klArea) {
                    klArea.innerHTML = `<div style="color:var(--danger);font-weight:600;padding:10px;background:rgba(239,68,68,0.1);border-radius:4px;border:1px solid rgba(239,68,68,0.3);">
                        <i class="ti ti-alert-triangle"></i> ⚠️ ${msg}
                    </div>`;
                }
            }
            
            // Nếu là lỗi file download
            if (msg.includes('file') || msg.includes('File')) {
                const fileArea = document.getElementById('file-list-area');
                if (fileArea) {
                    fileArea.innerHTML = `<div style="text-align:center;color:var(--danger);padding:14px;grid-column:1/-1;background:rgba(239,68,68,0.1);border-radius:6px;">
                        <i class="ti ti-alert-triangle"></i> ⚠️ ${msg}
                    </div>`;
                }
            }
            
            // Luôn hiển thị toast thông báo trên topbar (dùng notification API nếu có)
            try {
                const toast = document.createElement('div');
                toast.style.cssText = 'position:fixed;top:16px;right:16px;background:rgba(239,68,68,0.9);color:white;padding:12px 20px;border-radius:8px;font-size:13px;z-index:9999;max-width:400px;box-shadow:0 8px 24px rgba(0,0,0,0.4);animation:slideIn 0.3s ease;';
                toast.textContent = `⚠️ ${msg}`;
                document.body.appendChild(toast);
                setTimeout(() => {
                    toast.style.opacity = '0';
                    toast.style.transition = 'opacity 0.5s';
                    setTimeout(() => toast.remove(), 500);
                }, 8000);  // Thời gian toast lâu hơn (8s thay vì 5s)
            } catch (e) {}
        }
    });

    // =============================================
    // Chạy tuần tự luồng nạp dữ liệu an toàn
    // =============================================
    const bootstrapApp = async () => {
        try {
            // Áp dụng giao diện theo role
            setTimeout(() => {
                applyRoleBasedUI();
                if (hasRole('admin')) {
                    setTimeout(() => {
                        if (typeof window.loadAdminUsers === 'function') {
                            window.loadAdminUsers();
                        }
                    }, 200);
                }
            }, 150);

            // 1. Nạp dữ liệu nhật ký cũ từ SQLite
            await fetchAndRenderAuditLogs();

            // 2. Mở kết nối WebSocket
            initSocket(TEACHER_AGENT_ID);
        } catch (error) {
            console.error("❌ Lỗi trong quá trình khởi động luồng dữ liệu App:", error);
            initSocket(TEACHER_AGENT_ID);
        }
    };

    // Kích hoạt
    bootstrapApp();
};

// Kích hoạt chu trình chạy hệ thống
startApp();