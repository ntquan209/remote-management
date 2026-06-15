/**
 * Monitor Page Module - Giám sát màn hình và tiến trình
 * 
 * 📌 CHỨC NĂNG:
 * - Xử lý chụp ảnh màn hình (STATIC)
 * - Xử lý live stream màn hình (LIVE/STOP)
 * - Xử lý hiển thị danh sách tiến trình từ agent
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. Người dùng click nút trên UI → gọi handleScreenTrigger(type)
 * 2. Hàm kiểm tra máy đã chọn chưa, emitCommand qua WebSocket
 * 3. Khi backend gửi process data → handleProcesses(data) cập nhật bảng
 * 
 * 📡 CÁC LỆNH GỬI ĐI:
 * - "SCREENSHOT": Chụp ảnh màn hình tĩnh
 * - "START_STREAM": Bắt đầu stream màn hình
 * - "STOP_STREAM": Dừng stream
 */

// Screen page module
import { getElementById } from '../utils/dom.js';
import { emitCommand } from '../lib/socket.js';
import { getTargetMachine, addMachineOnline } from '../components/machine-selector.js';

/**
 * Xử lý các thao tác liên quan đến màn hình
 * 
 * @param {string} type - Loại thao tác: "STATIC" | "LIVE" | "STOP"
 * 
 * STATIC: Chụp một ảnh tĩnh
 * - Hiển thị "Đang chụp..." trên màn hình
 * - Gửi lệnh SCREENSHOT tới agent
 * 
 * LIVE: Bắt đầu stream
 * - Hiển thị badge LIVE VIEWING
 * - Bật nút STOP
 * - Gửi lệnh START_STREAM
 * 
 * STOP: Dừng stream
 * - Hiển thị "Đã ngừng"
 * - Tắt nút STOP
 * - Gửi lệnh STOP_STREAM
 */
export const handleScreenTrigger = (type) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Chưa chọn máy trạm!");
  
  const display = getElementById('screen-display-area');
  const stopBtn = getElementById('btn-stop-screen');
  if (!display) return;

  if (type === 'STATIC') {
    display.innerHTML = `<i class="ti ti-device-desktop" style="font-size:48px;color:var(--success)"></i><span style="color:var(--success);font-weight:600">Đang chụp ảnh màn hình...</span>`;
    emitCommand('SCREENSHOT', targetMachine);
  } else if (type === 'LIVE') {
    display.innerHTML = `<div class="live-badge"><div class="blink"></div>LIVE VIEWING - 1 FPS</div>`;
    if (stopBtn) stopBtn.disabled = false;
    emitCommand('START_STREAM', targetMachine);
  } else {
    display.innerHTML = `<i class="ti ti-device-desktop" style="font-size:48px;color:var(--text-muted)"></i><span style="color:var(--text-muted)">Đã ngừng luồng phát nhận dữ liệu</span>`;
    if (stopBtn) stopBtn.disabled = true;
    emitCommand('STOP_STREAM', targetMachine);
  }
};

/**
 * Xử lý dữ liệu tiến trình nhận được từ agent qua WebSocket
 * 
 * @param {object} data - Dữ liệu chứa:
 *   - machine_name: Tên máy gửi dữ liệu
 *   - processes: Array [{pid, name, cpu, ram}, ...]
 * 
 * Luồng:
 * 1. Thêm máy vào danh sách online (nếu chưa có)
 * 2. Nếu dữ liệu thuộc về máy đang chọn:
 *    - Xóa bảng cũ
 *    - Tạo dòng mới cho mỗi tiến trình (kèm nút Kill)
 *    - Cập nhật badge và label số lượng process
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
    
    // Cập nhật số lượng process trên sidebar và dashboard
    const procBadge = getElementById('sidebar-proc-badge');
    const procLabel = getElementById('total-procs-lbl');
    if (procBadge) procBadge.textContent = data.processes.length;
    if (procLabel) procLabel.textContent = data.processes.length;
  }
};

export default { handleScreenTrigger, handleProcesses };