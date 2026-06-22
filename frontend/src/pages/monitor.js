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

    const mimeType = cleanBase64.charAt(0) === '/' ? 'jpeg' : 'png';
    imgElement.src = `data:image/${mimeType};base64,${cleanBase64}`;

    if (currentMode === 'LIVE' && sessionStorage.getItem(`screen_mode_${incomingMachine}`) === 'LIVE') {
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

    updateAppsStatusFromProcs(data.processes);
  }
};

// ==========================================
// 🚀 ĐOẠN CODE BỔ SUNG MỚI (ĐÃ ĐỒNG BỘ CHUẨN KIẾN TRÚC MẠNG)
// ==========================================

/**
 * Thao tác bật/tắt ứng dụng Whitelist
 */
export const triggerApp = (action, appName) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Vui lòng chọn một máy trạm để điều khiển ứng dụng!");
  emitCommand('APP_CONTROL', targetMachine, { action: action, app_name: appName });
};

/**
 * Kích hoạt hoặc tắt luồng stream dữ liệu Webcam
 */
export const triggerWebcam = (status) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Vui lòng chọn máy trạm để điều khiển Webcam!");

  const displayBox = getElementById('webcam-display-box');
  if (!displayBox) return;

  if (status) {
    displayBox.innerHTML = `
      <div id="webcam-placeholder-area" style="text-align:center;color:var(--warning)">
        <i class="ti ti-loader animate-spin" style="font-size:40px;margin-bottom:8px"></i>
        <div>Đang gửi yêu cầu và đợi sinh viên xác nhận quyền Webcam...</div>
      </div>`;
    sessionStorage.setItem(`webcam_active_${targetMachine}`, 'TRUE');
    emitCommand('WEBCAM_START', targetMachine, { status: true });
  } else {
    displayBox.innerHTML = `
      <div id="webcam-placeholder-area" style="text-align:center;color:var(--text-muted)">
        <i class="ti ti-camera-off" style="font-size:40px;margin-bottom:8px"></i>
        <div>Webcam đang đóng</div>
      </div>`;
    sessionStorage.removeItem(`webcam_active_${targetMachine}`);
    emitCommand('WEBCAM_STOP', targetMachine, { status: false });
  }
};

/**
 * Đón nhận luồng dữ liệu hình ảnh Webcam dạng Base64 từ Socket đổ về
 */
export const handleIncomingWebcam = (data) => {
  const incomingMachine = data.machine_name;
  const activeSelection = getTargetMachine();

  if (incomingMachine !== activeSelection) return;
  if (!sessionStorage.getItem(`webcam_active_${incomingMachine}`)) return;

  const displayBox = getElementById('webcam-display-box');
  if (!displayBox) return;

  let imgElement = displayBox.querySelector('#live-webcam-img');
  if (!imgElement) {
    displayBox.innerHTML = `<img id="live-webcam-img" style="width:100%; height:auto; display:block; object-fit:contain; max-height:60vh;" alt="Webcam Feed" />`;
    imgElement = displayBox.querySelector('#live-webcam-img');
  }

  if (imgElement && data.image_base64) {
    let base64Str = data.image_base64;
    if (base64Str.startsWith("b'") || base64Str.startsWith('b"')) {
      base64Str = base64Str.substring(2, base64Str.length - 1);
    }
    const cleanBase64 = base64Str.replace(/(\r\n|\n|\r)/gm, "").trim();
    const mimeType = cleanBase64.charAt(0) === '/' ? 'jpeg' : 'png';
    imgElement.src = `data:image/${mimeType};base64,${cleanBase64}`;
  }
};

/**
 * Yêu cầu nạp lại danh sách File Sandbox trong thư mục cấu hình
 */
export const refreshSandboxFiles = () => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Vui lòng chọn máy trạm để đồng bộ File Sandbox!");

  const fileArea = getElementById('file-list-area');
  if (fileArea) {
    fileArea.innerHTML = `<div style="text-align:center;color:var(--warning);padding:14px;grid-column:1/-1;"><i class="ti ti-refresh animate-spin"></i> Đang đọc danh sách tệp tin từ Agent...</div>`;
  }
  emitCommand('FETCH_FILES', targetMachine, {});
};

/**
 * Render mảng danh sách tệp dội về lên lưới hiển thị
 */
export const handleFileList = (data) => {
  const incomingMachine = data.machine_name;
  const activeSelection = getTargetMachine();
  if (incomingMachine !== activeSelection) return;

  const fileArea = getElementById('file-list-area');
  if (!fileArea) return;

  if (!data.files || data.files.length === 0) {
    fileArea.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:14px;grid-column:1/-1;">Thư mục trống hoặc chưa có dữ liệu đồng bộ.</div>`;
    return;
  }

  fileArea.innerHTML = "";
  data.files.forEach(file => {
    const item = document.createElement('div');
    item.className = "file-item";

    item.style = "display:flex; flex-direction:column; align-items:center; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:12px; border-radius:6px; text-align:center; gap:6px; cursor:pointer; transition: background 0.2s;";

    item.onmouseover = () => item.style.background = "rgba(255,255,255,0.08)";
    item.onmouseout = () => item.style.background = "rgba(255,255,255,0.03)";

    let fileIcon = "ti-file";
    if (['.png', '.jpg', '.jpeg', '.gif'].some(ext => file.name.toLowerCase().endsWith(ext))) fileIcon = "ti-photo";
    else if (['.txt', '.md', '.py', '.json', '.js'].some(ext => file.name.toLowerCase().endsWith(ext))) fileIcon = "ti-file-code";
    else if (file.is_dir) fileIcon = "ti-folder";

    item.innerHTML = `
      <i class="ti ${fileIcon}" style="font-size:32px; color:var(--primary)"></i>
      <span style="font-size:12px; font-weight:500; text-overflow:ellipsis; overflow:hidden; white-space:nowrap; width:100%; color:var(--text-main)" title="${file.name}">${file.name}</span>
      <span style="font-size:10px; color:var(--text-muted)">${file.size}</span>
    `;

    if (!file.is_dir) {
      item.onclick = () => {
        if (confirm(`Bạn có muốn tải tệp tin "${file.name}" từ máy trạm về không?`)) {
          emitCommand('DOWNLOAD_FILE', activeSelection, { file_name: file.name });
        }
      };
    } else {
      item.onclick = () => alert("Tính năng duyệt thư mục con đang được khóa bảo vệ Sandbox!");
    }

    fileArea.appendChild(item);
  });
};

/**
 * Xử lý sự kiện hứng phím Keylogger thời gian thực
 */
export const handleIncomingKeylog = (data) => {
  const incomingMachine = data.machine_name;
  const activeSelection = getTargetMachine();
  if (incomingMachine !== activeSelection) return;

  const streamArea = getElementById('key-stream-area');
  if (!streamArea) return;

  if (streamArea.innerHTML.includes('Đang chờ phím bấm')) {
    streamArea.innerHTML = "";
  }

  if (sessionStorage.getItem(`keylog_suspended_${incomingMachine}`) === 'TRUE') return;

  const keySpan = document.createElement('span');
  keySpan.style = "margin-right: 4px; padding: 2px 4px; background: rgba(56, 189, 248, 0.1); border-radius:3px;";

  if (data.key === "Key.space") keySpan.textContent = "[Space]";
  else if (data.key === "Key.enter") keySpan.textContent = "[Enter]\n";
  else if (data.key === "Key.backspace") keySpan.textContent = "[Backspace]";
  else keySpan.textContent = data.key.replace(/'/g, "");

  streamArea.appendChild(keySpan);
  streamArea.scrollTop = streamArea.scrollHeight;
};

/**
 * SỬA LỖI ĐIỀU KHIỂN BẬT/TẮT VÀ ĐỔI CHỮ NÚT BẤM REALTIME KHỚP BACKEND
 */
export const toggleKlState = () => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Vui lòng chọn máy trạm mục tiêu trước khi kiểm soát phím!");

  const btn = getElementById('btn-toggle-kl');
  if (!btn) return;

  const isCurrentlyCapturing = sessionStorage.getItem(`keylog_running_${targetMachine}`) === 'TRUE';

  if (!isCurrentlyCapturing) {
    sessionStorage.setItem(`keylog_running_${targetMachine}`, 'TRUE');
    sessionStorage.removeItem(`keylog_suspended_${targetMachine}`);

    btn.textContent = "Tạm dừng bắt phím";
    btn.className = "btn danger";
    btn.style.background = "var(--danger)";

    emitCommand('KEYLOGGER_TOGGLE', targetMachine, { capturing: true });
    console.log(`🚀 [KEYLOG] Đã phát lệnh KÍCH HOẠT xuống máy ${targetMachine}`);
  } else {
    sessionStorage.removeItem(`keylog_running_${targetMachine}`);

    btn.textContent = "Kích hoạt bắt phím thực hành";
    btn.className = "btn success";
    btn.style.background = "var(--success)";

    emitCommand('KEYLOGGER_TOGGLE', targetMachine, { capturing: false });
    console.log(`🚀 [KEYLOG] Đã phát lệnh TẠM DỪNG xuống máy ${targetMachine}`);
  }
};

/**
 * Xóa trắng khung dữ liệu lưu phím hiển thị
 */
export const clearKlArea = () => {
  const streamArea = getElementById('key-stream-area');
  if (streamArea) {
    streamArea.innerHTML = `<div style="color:var(--text-muted);font-style:italic">Đã xóa sạch bộ đệm hiển thị. Đang đợi phím mới...</div>`;
  }
};

/**
 * Tự động đồng bộ Trạng thái và Text của nút dựa trên tiến trình chạy thật dưới Agent
 */
export const updateAppsStatusFromProcs = (processes) => {
  const whitelist = ["firefox", "mousepad", "thunar"];

  whitelist.forEach(app => {
    const isRunning = processes.some(p => p.name.toLowerCase().includes(app));
    const row = document.querySelector(`tr[data-app="${app}"]`);
    if (!row) return;

    const statusTd = row.querySelector('.app-status');
    const toggleBtn = row.querySelector('.btn-toggle-app');

    if (toggleBtn) {
      const pendingAction = toggleBtn.getAttribute('data-pending-action');

      if (pendingAction === "START" && isRunning) {
        toggleBtn.removeAttribute('data-pending-action');
      } else if (pendingAction === "STOP" && !isRunning) {
        toggleBtn.removeAttribute('data-pending-action');
      }

      if (toggleBtn.hasAttribute('data-pending-action')) return;
    }

    if (isRunning) {
      if (statusTd) statusTd.innerHTML = `<span class="badge-status run" style="background:rgba(34,197,94,0.1);color:#22c55e;padding:4px 8px;border-radius:4px;">Đang bật</span>`;
      if (toggleBtn) {
        toggleBtn.innerHTML = `<i class="ti ti-player-stop"></i> Cưỡng bức đóng`;
        toggleBtn.style.background = "var(--danger)";
      }
    } else {
      if (statusTd) statusTd.innerHTML = `<span class="badge-status stop" style="background:rgba(239,68,68,0.1);color:#ef4444;padding:4px 8px;border-radius:4px;">Đang tắt</span>`;
      if (toggleBtn) {
        toggleBtn.innerHTML = `<i class="ti ti-player-play"></i> Khởi chạy`;
        toggleBtn.style.background = "var(--success)";
      }
    }
  });
};

/**
 * Điều phối hành động duy nhất (Toggle) từ nút bấm đơn
 */
export const toggleAppAction = (appName) => {
  const row = document.querySelector(`tr[data-app="${appName}"]`);
  if (!row) return;

  const toggleBtn = row.querySelector('.btn-toggle-app');
  const statusTd = row.querySelector('.app-status');
  if (!toggleBtn) return;

  const isCurrentlyRunning = toggleBtn.innerHTML.includes('Cưỡng bức đóng');
  const nextAction = isCurrentlyRunning ? "STOP" : "START";

  toggleBtn.setAttribute('data-pending-action', nextAction);

  if (nextAction === "START") {
    if (statusTd) statusTd.innerHTML = `<span class="badge-status run" style="background:rgba(34,197,94,0.1);color:#22c55e;padding:4px 8px;border-radius:4px;">Đang bật</span>`;
    toggleBtn.innerHTML = `<i class="ti ti-player-stop"></i> Cưỡng bức đóng`;
    toggleBtn.style.background = "var(--danger)";
  } else {
    if (statusTd) statusTd.innerHTML = `<span class="badge-status stop" style="background:rgba(239,68,68,0.1);color:#ef4444;padding:4px 8px;border-radius:4px;">Đang tắt</span>`;
    toggleBtn.innerHTML = `<i class="ti ti-player-play"></i> Khởi chạy`;
    toggleBtn.style.background = "var(--success)";
  }

  triggerApp(nextAction, appName);
};

/**
 * 🎯 ĐÃ VÁ LỖI MẠNG: Hàm tiếp nhận lệnh Kill Process trùng khớp viết thường 'kill_process' với Agent
 */
export const handleKillProcess = (pid, procName) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Vui lòng chọn một máy trạm cụ thể trước!");

  if (confirm(`⚠️ Bạn có chắc chắn muốn cưỡng bức đóng tiến trình [${procName}] (PID: ${pid}) trên máy [${targetMachine}] không?`)) {
    // 🎯 ĐỔI TÊN LỆNH: Từ 'KILL_PROCESS' thành 'kill_process' viết thường để Agent hiểu được
    emitCommand('kill_process', targetMachine, { pid: parseInt(pid), proc_name: procName });
    console.log(`🚀 [PROCESS] Đã phát lệnh KILL tiến trình ${procName} (PID: ${pid}) xuống máy ${targetMachine}`);
  }
};

/**
 * 🎯 ĐÃ BỔ SUNG: Hàm tiếp nhận lệnh tương tác nguồn điện tự nhận diện từ click ở panels.js
 */
export const handlePowerCommand = (type) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Vui lòng cấu hình chọn máy trạm phòng Lab trước khi thực hiện!");

  const label = type === 'RESTART' ? 'Khởi động lại' : 'Tắt nguồn';
  if (confirm(`⚠️ CẢNH BÁO: Bạn chắc chắn muốn phát lệnh [${label}] xuống máy [${targetMachine}] chứ?`)) {
    // 🎯 ĐỔI TÊN LỆNH: Gửi trực tiếp chữ viết thường 'restart' / 'shutdown' đồng bộ hoàn toàn với logic của agent.py
    emitCommand(type.toLowerCase(), targetMachine, {});
    console.log(`🚀 [POWER] Đã phát lệnh ${type.toLowerCase()} xuống máy ${targetMachine}`);
  }
};

// Gắn các hàm tương tác mới vào window toàn cục để các thẻ HTML onclick nhận dạng được ngay lập tức
window.triggerApp = triggerApp;
window.refreshSandboxFiles = refreshSandboxFiles;
window.toggleKlState = toggleKlState;
window.toggleAppAction = toggleAppAction;
window.handleKillProcess = handleKillProcess;
window.triggerPower = handlePowerCommand; // 🎯 KHÔI PHỤC EXPOSE: Khớp với onclick="window.triggerPower(...)" bên panels.js

export default {
  handleScreenTrigger,
  handleIncomingScreen,
  handleProcesses,
  fetchAndRenderAuditLogs,
  triggerApp,
  triggerWebcam,
  handleIncomingWebcam,
  refreshSandboxFiles,
  handleFileList,
  handleIncomingKeylog,
  toggleKlState,
  clearKlArea,
  updateAppsStatusFromProcs,
  toggleAppAction,
  handleKillProcess,
  handlePowerCommand
};