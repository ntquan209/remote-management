/**
 * Monitor Page Module - Giám sát màn hình và tiến trình
 * (Bản sửa lỗi tối thượng: Tự động lặp luồng ảnh trên FE, sửa dứt điểm lỗi kẹt LIVE)
 */

import { getElementById } from '../utils/dom.js';
import { emitCommand, onEvent } from '../lib/socket.js';
import { getTargetMachine, addMachineOnline, removeMachineOffline } from '../components/machine-selector.js';

// TẠO ID DUY NHẤT CHO TỪNG TAB ĐỂ TRÁNH XUNG ĐỘT ĐA TAB
const TAB_SESSION_ID = "tab_" + Math.random().toString(36).substring(2, 9);

/**
 * Xử lý các thao tác kích hoạt liên quan đến màn hình từ nút bấm UI
 * @param {string} type - Loại thao tác: "STATIC" | "LIVE" | "STOP"
 */
export const handleScreenTrigger = (type) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Chưa chọn máy trạm!");

  const display = getElementById('screen-display-area');
  const stopBtn = getElementById('btn-stop-screen');
  if (!display) return;

  if (type === 'STATIC') {
    display.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; gap:10px; padding: 40px 0;">
        <i class="ti ti-device-desktop" style="font-size:48px; color:var(--success); animation: blink 1s infinite"></i>
        <span style="color:var(--success); font-weight:600">Đang yêu cầu chụp ảnh màn hình tĩnh...</span>
      </div>`;

    // Đánh dấu tab này chỉ chụp ảnh tĩnh đơn lẻ
    sessionStorage.setItem('screen_mode', 'STATIC');
    sessionStorage.setItem('monitor_tab_id', TAB_SESSION_ID);

    emitCommand('SCREENSHOT', targetMachine);

  } else if (type === 'LIVE') {
    display.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; gap:10px; padding: 40px 0;">
        <div class="live-badge"><div class="blink"></div>CONNECTING STREAM...</div>
        <span style="color:var(--text-muted)">Đang kết nối luồng truyền tải video...</span>
      </div>`;
    if (stopBtn) stopBtn.disabled = false;

    // Đánh dấu tab này đang kích hoạt chế độ XEM LIVE
    sessionStorage.setItem('screen_mode', 'LIVE');
    sessionStorage.setItem('monitor_tab_id', TAB_SESSION_ID);

    // 🎯 CHIÊU ĐỘC: Mượn đường lệnh SCREENSHOT (luồng mạng chắc chắn thông suốt xuống Kali)
    emitCommand('SCREENSHOT', targetMachine);

  } else {
    display.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; gap:10px; padding: 40px 0;">
        <i class="ti ti-device-desktop" style="font-size:48px; color:var(--text-muted)"></i>
        <span style="color:var(--text-muted)">Đã ngừng luồng phát nhận dữ liệu màn hình</span>
      </div>`;
    if (stopBtn) stopBtn.disabled = true;

    // Xóa trạng thái luồng khi bấm dừng
    sessionStorage.removeItem('screen_mode');
    sessionStorage.removeItem('monitor_tab_id');
  }
};

/**
 * Tiếp nhận ảnh dội về từ Socket và xử lý vòng lặp tự động re-trigger
 */
export const handleIncomingScreen = (data) => {
  const targetMachine = getTargetMachine();
  if (data.machine_name !== targetMachine) return;

  const display = getElementById('screen-display-area');
  if (!display) return;

  // Đọc trạng thái lưu trữ riêng biệt của Tab hiện tại
  const currentMode = sessionStorage.getItem('screen_mode');
  const currentTabOwner = sessionStorage.getItem('monitor_tab_id');

  // ĐỒNG BỘ ĐA TAB CHUẨN XÁC: Nếu gói tin dội về không phải do Tab này ra lệnh -> Chặn luôn!
  if (currentTabOwner !== TAB_SESSION_ID) {
    return;
  }

  // Khung chứa render thẻ ảnh thô sạch, chuẩn tỷ lệ gốc, xóa rác chữ
  let imgElement = display.querySelector('#live-stream-img');

  if (!imgElement) {
    display.innerHTML = `
      <div style="position: relative; width: 100%; border-radius: 8px; overflow: hidden; background: #000; min-height: 250px; display: flex; align-items: center; justify-content: center;">
        <img id="live-stream-img" style="width:100%; height:auto; display:block; object-fit:contain; max-height:75vh;" alt="Agent Screen Stream" />
      </div>
    `;
    imgElement = display.querySelector('#live-stream-img');
  }

  // Đổ dữ liệu Base64 thô vào ảnh src
  if (imgElement && data.image_base64) {
    let base64Str = data.image_base64;

    if (base64Str.startsWith("b'") || base64Str.startsWith('b"')) {
      base64Str = base64Str.substring(2, base64Str.length - 1);
    }

    const cleanBase64 = base64Str.replace(/(\r\n|\n|\r)/gm, "").trim();
    imgElement.src = `data:image/jpeg;base64,${cleanBase64}`;

    // 🎯 KÍCH HOẠT VÒNG LẶP LIVE STREAM NGAY TRÊN FRONTEND:
    // Nếu Tab này đang ở chế độ LIVE, ngay sau khi nhận và vẽ xong bức ảnh này,
    // nó sẽ tự động phát đi tiếp một lệnh yêu cầu chụp tấm tiếp theo sau 33ms (đạt tỷ lệ ~30 FPS mượt mà)
    if (currentMode === 'LIVE') {
      setTimeout(() => {
        // Kiểm tra lại lần nữa phòng trường hợp người dùng vừa bấm nút STOP trong 33ms qua
        if (sessionStorage.getItem('screen_mode') === 'LIVE') {
          emitCommand('SCREENSHOT', targetMachine);
        }
      }, 33);
    }
  }
};

/**
 * Xử lý dữ liệu tiến trình nhận được từ agent
 */
export const handleProcesses = (data) => {
  const targetMachine = getTargetMachine();
  addMachineOnline(data.machine_name);

  if (data.machine_name === targetMachine) {
    const tbody = getElementById('process-table-body');
    if (!tbody) return;

    tbody.innerHTML = "";

    data.processes.forEach(proc => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${proc.pid}</td>
        <td><strong>${proc.name}</strong></td>
        <td style="color:var(--warning)">${proc.cpu}</td>
        <td>${proc.ram}</td>
        <td>
          <button class="btn danger" onclick="window.handleKillProcess('${proc.pid}', '${proc.name}')">Kill</button>
        </td>
      `;
      tbody.appendChild(row);
    });

    const procBadge = getElementById('sidebar-proc-badge');
    const procLabel = getElementById('total-procs-lbl');
    if (procBadge) procBadge.textContent = data.processes.length;
    if (procLabel) procLabel.textContent = data.processes.length;
  }
};

// ĐĂNG KÝ CÁC SỰ KIỆN LIÊN QUAN ĐẾN ĐỊNH DANH MÁY TỪ SERVER
onEvent('agent_list', (json) => {
  if (json.agents && Array.isArray(json.agents)) {
    json.agents.forEach(agentId => addMachineOnline(agentId));
  }
});

onEvent('agent_connected', (json) => {
  if (json.agent_id) {
    addMachineOnline(json.agent_id);
  }
});

onEvent('agent_disconnected', (json) => {
  if (json.agent_id) {
    removeMachineOffline(json.agent_id);
  }
});

onEvent('agent_send_screen', handleIncomingScreen);
onEvent('agent_send_procs', handleProcesses);

export default { handleScreenTrigger, handleIncomingScreen, handleProcesses };