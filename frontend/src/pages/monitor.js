/**
 * Monitor Page Module - Giám sát màn hình và tiến trình
 * (Bản sửa lỗi hoàn chỉnh: Cách ly Tab Session, điều tốc 180ms an toàn, tự nhận diện Mime ảnh)
 */

import { getElementById } from '../utils/dom.js';
import { emitCommand } from '../lib/socket.js';
import { getTargetMachine, addMachineOnline, removeMachineOffline } from '../components/machine-selector.js';

// Sinh khóa định danh ngẫu nhiên cho riêng Tab window này
const TAB_SESSION_ID = "tab_" + Math.random().toString(36).substring(2, 9);
const localWatchdogs = {};

const updateMachineTimestamp = (machine) => {
  sessionStorage.setItem(`last_img_time_${machine}`, Date.now().toString());
};

const getMachineTimestamp = (machine) => {
  return parseInt(sessionStorage.getItem(`last_img_time_${machine}`)) || 0;
};

/**
 * Lôi dữ liệu Audit Log lưu cứng dưới Database SQLite lên giao diện
 */
export const fetchAndRenderAuditLogs = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/audit-logs');
    if (!response.ok) return;
    const logs = await response.json();

    const tbodyTarget = getElementById('audit-log-rows');
    if (!tbodyTarget) return;

    if (logs.length === 0) {
      tbodyTarget.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Hệ thống chưa ghi nhận hoạt động nào...</td></tr>`;
      return;
    }

    tbodyTarget.innerHTML = "";
    logs.forEach(log => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${log.time}</td>
        <td>${log.operator}</td>
        <td><strong style="color:var(--primary)">${log.action}</strong></td>
        <td>${log.target}</td>
        <td><span>${log.status}</span></td>
      `;
      tbodyTarget.appendChild(row);
    });

    const logBadge = getElementById('total-logs-lbl');
    if (logBadge) logBadge.textContent = logs.length;
  } catch (error) {
    console.error("❌ Không thể nạp lịch sử log từ database:", error);
  }
};

/**
 * Đón đầu sự kiện WebSocket từ Backend đổ về để chèn log quay/chụp vào UI tức thì
 */
export const handleIncomingAuditLog = (log) => {
  const tbodyTarget = getElementById('audit-log-rows');
  if (!tbodyTarget) return;

  if (tbodyTarget.innerHTML.includes('Hệ thống chưa ghi nhận')) {
    tbodyTarget.innerHTML = "";
  }

  const row = document.createElement('tr');
  row.innerHTML = `
    <td>${log.time}</td>
    <td>${log.operator}</td>
    <td><strong style="color:var(--primary)">${log.action}</strong></td>
    <td>${log.target}</td>
    <td><span>${log.status}</span></td>
  `;
  tbodyTarget.insertBefore(row, tbodyTarget.firstChild);

  const logBadge = getElementById('total-logs-lbl');
  if (logBadge) {
    let currentCount = parseInt(logBadge.textContent) || 0;
    logBadge.textContent = currentCount + 1;
  }
};

/**
 * Xử lý các thao tác kích hoạt liên quan đến màn hình từ nút bấm UI
 */
export const handleScreenTrigger = (type) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Vui lòng chọn một máy trạm cụ thể trước!");

  const display = getElementById('screen-display-area');
  const stopBtn = getElementById('btn-stop-screen');
  if (!display) return;

  if (localWatchdogs[targetMachine]) {
    clearInterval(localWatchdogs[targetMachine]);
    delete localWatchdogs[targetMachine];
  }

  if (type === 'STATIC') {
    display.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; gap:10px; padding: 40px 0;">
        <i class="ti ti-device-desktop" style="font-size:48px; color:var(--success); animation: blink 1s infinite"></i>
        <span style="color:var(--success); font-weight:600">Đang yêu cầu ảnh màn hình máy ${targetMachine}...</span>
      </div>`;

    sessionStorage.setItem(`screen_mode_${targetMachine}`, 'STATIC');
    sessionStorage.setItem(`monitor_tab_owner_${targetMachine}`, TAB_SESSION_ID);

    emitCommand('SCREENSHOT', targetMachine, {});

  } else if (type === 'LIVE') {
    display.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; gap:10px; padding: 40px 0;">
        <div class="live-badge"><div class="blink"></div>CONNECTING STREAM [${targetMachine}]...</div>
        <span style="color:var(--text-muted)">Đang kết nối luồng truyền tải video...</span>
      </div>`;
    if (stopBtn) stopBtn.disabled = false;

    sessionStorage.setItem(`screen_mode_${targetMachine}`, 'LIVE');
    sessionStorage.setItem(`monitor_tab_owner_${targetMachine}`, TAB_SESSION_ID);
    updateMachineTimestamp(targetMachine);

    emitCommand('START_STREAM', targetMachine, {});

    // Watchdog local cô lập
    localWatchdogs[targetMachine] = setInterval(() => {
      const currentMode = sessionStorage.getItem(`screen_mode_${targetMachine}`);
      const currentTabOwner = sessionStorage.getItem(`monitor_tab_owner_${targetMachine}`);

      if (currentMode === 'LIVE' && currentTabOwner === TAB_SESSION_ID) {
        const timeSinceLastImage = Date.now() - getMachineTimestamp(targetMachine);
        if (timeSinceLastImage > 3000) {
          console.warn(`⚠️ [WATCHDOG] Máy [${targetMachine}] phản hồi chậm luồng. Đang mồi lại...`);
          updateMachineTimestamp(targetMachine);
          emitCommand('SCREENSHOT', targetMachine, {});
        }
      }
    }, 3000);

  } else {
    display.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; gap:10px; padding: 40px 0;">
        <i class="ti ti-device-desktop" style="font-size:48px; color:var(--text-muted)"></i>
        <span style="color:var(--text-muted)">Đã ngừng luồng phát nhận dữ liệu màn hình máy ${targetMachine}</span>
      </div>`;
    if (stopBtn) stopBtn.disabled = true;

    sessionStorage.removeItem(`screen_mode_${targetMachine}`);
    sessionStorage.removeItem(`monitor_tab_owner_${targetMachine}`);

    emitCommand('STOP_STREAM', targetMachine, {});
  }
};

/**
 * Tiếp nhận ảnh dội về từ Socket và xử lý vòng lặp tự động re-trigger
 */
export const handleIncomingScreen = (data) => {
  const incomingMachine = data.machine_name;

  const currentMode = sessionStorage.getItem(`screen_mode_${incomingMachine}`);
  const currentTabOwner = sessionStorage.getItem(`monitor_tab_owner_${incomingMachine}`);

  // Chặn tuyệt đối ảnh Máy A nhảy sang Tab Máy B khi mở song song 2 tab
  if (currentTabOwner !== TAB_SESSION_ID) return;

  updateMachineTimestamp(incomingMachine);

  const activeSelection = getTargetMachine();
  if (incomingMachine !== activeSelection) {
    if (currentMode === 'LIVE' && sessionStorage.getItem(`screen_mode_${incomingMachine}`) === 'LIVE') {
      setTimeout(() => {
        emitCommand('SCREENSHOT', incomingMachine, {});
      }, 300);
    }
    return;
  }

  const display = getElementById('screen-display-area');
  if (!display) return;

  let imgElement = display.querySelector('#live-stream-img');
  if (!imgElement) {
    display.innerHTML = `
      <div style="position: relative; width: 100%; border-radius: 8px; overflow: hidden; background: #000; min-height: 250px; display: flex; align-items: center; justify-content: center;">
        <img id="live-stream-img" style="width:100%; height:auto; display:block; object-fit:contain; max-height:75vh;" alt="Agent Screen Stream" />
      </div>
    `;
    imgElement = display.querySelector('#live-stream-img');
  }

  if (imgElement && data.image_base64) {
    let base64Str = data.image_base64;
    if (base64Str.startsWith("b'") || base64Str.startsWith('b"')) {
      base64Str = base64Str.substring(2, base64Str.length - 1);
    }
    const cleanBase64 = base64Str.replace(/(\r\n|\n|\r)/gm, "").trim();

    // Nhận diện Header thông minh (Tránh lỗi GPU crash nhuộm xanh thẻ ảnh)
    const mimeType = cleanBase64.charAt(0) === '/' ? 'jpeg' : 'png';
    imgElement.src = `data:image/${mimeType};base64,${cleanBase64}`;

    if (currentMode === 'LIVE' && sessionStorage.getItem(`screen_mode_${incomingMachine}`) === 'LIVE') {
      // Tốc độ điều hòa 180ms an toàn tuyệt đối cho card mạng ảo phòng Lab
      setTimeout(() => {
        if (sessionStorage.getItem(`screen_mode_${incomingMachine}`) === 'LIVE') {
          emitCommand('SCREENSHOT', incomingMachine, {});
        }
      }, 180);
    }
  }
};

/**
 * Xử lý dữ liệu tiến trình nhận được từ agent
 */
export const handleProcesses = (data) => {
  const incomingMachine = data.machine_name;
  addMachineOnline(incomingMachine);

  const activeSelection = getTargetMachine();
  if (incomingMachine === activeSelection) {
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

export default { handleScreenTrigger, handleIncomingScreen, handleProcesses, fetchAndRenderAuditLogs };