/**
 * Machine Selector Component - Chọn và quản lý máy trạm
 * 
 * 📌 CHỨC NĂNG:
 * - Quản lý danh sách máy trạm đang online
 * - Dropdown chọn máy mục tiêu (target machine)
 * - Cập nhật trạng thái kết nối (online/offline)
 * - Cập nhật giao diện khi có máy mới kết nối hoặc mất kết nối
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. Khi có agent kết nối: addMachineOnline(machine_name) được gọi
 * 2. Hàm này thêm vào Set currentOnlineList và gọi updateMachineDropdown()
 * 3. updateMachineDropdown() xóa dropdown cũ, tạo lại từ Set
 * 4. Nếu không có máy nào: hiển thị "-- Trống (Offline) --"
 * 5. Khi người dùng chọn máy: onTargetMachineChange() lưu target và reset process table
 * 
 * 📊 BIẾN TRẠNG THÁI:
 * - currentOnlineList: Set chứa tên các máy đang online
 * - targetMachine: String tên máy đang được chọn
 */

// Machine selector component
import { getElementById, updateElement } from '../utils/dom.js';

let currentOnlineList = new Set();  // Danh sách máy online
let targetMachine = "";              // Máy đang được chọn

export const getCurrentOnlineList = () => currentOnlineList;
export const getTargetMachine = () => targetMachine;
export const setTargetMachine = (machine) => { targetMachine = machine; };

/**
 * Thêm máy vào danh sách online (khi có agent kết nối)
 * Gọi từ monitor.js khi nhận được process data
 */
export const addMachineOnline = (machine) => {
  if (!currentOnlineList.has(machine)) {
    currentOnlineList.add(machine);
    updateMachineDropdown();  // Cập nhật lại dropdown
  }
};

/**
 * Xóa máy khỏi danh sách online (khi agent ngắt kết nối)
 * Nếu máy bị xóa đang là target, reset targetMachine về rỗng
 */
export const removeMachineOffline = (machine) => {
  currentOnlineList.delete(machine);
  if (targetMachine === machine) {
    targetMachine = "";
  }
  updateMachineDropdown();
};

/**
 * Cập nhật dropdown select và status pill
 * 
 * Luồng:
 * 1. Lưu lại target đang chọn
 * 2. Xóa toàn bộ options cũ
 * 3. Nếu không có máy online: hiển thị "Offline"
 * 4. Nếu có: tạo option cho mỗi máy trong Set
 * 5. Khôi phục selection nếu máy cũ vẫn online, nếu không chọn máy đầu tiên
 * 6. Cập nhật số lượng máy online trên dashboard
 */
export const updateMachineDropdown = () => {
  const select = getElementById('machine-select');
  if (!select) return;
  
  const savedTarget = targetMachine;
  select.innerHTML = "";
  
  if (currentOnlineList.size === 0) {
    select.innerHTML = '<option value="">-- Trống (Offline) --</option>';
    updateStatusPill(false);
    return;
  }

  // Tạo option cho mỗi máy online
  currentOnlineList.forEach(machine => {
    const opt = document.createElement('option');
    opt.value = machine;
    opt.textContent = machine;
    select.appendChild(opt);
  });

  // Khôi phục selection hoặc chọn máy đầu tiên
  if (currentOnlineList.has(savedTarget)) {
    select.value = savedTarget;
  } else {
    select.value = Array.from(currentOnlineList)[0];
    targetMachine = select.value;
  }
  
  // Cập nhật số máy online trên dashboard
  updateElement('total-online-machines-lbl', currentOnlineList.size);
  updateStatusPill(true);
};

/**
 * Khi người dùng chọn máy từ dropdown
 * - Cập nhật targetMachine
 * - Reset process table với thông báo loading
 * - Reset badge và label process về 0
 */
export const onTargetMachineChange = () => {
  const select = getElementById('machine-select');
  targetMachine = select.value;
  
  // Reset process table (sẽ load lại từ socket data)
  const tbody = getElementById('process-table-body');
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Đang nạp luồng tiến trình thời gian thực của máy [${targetMachine}]...</td></tr>`;
  }
  
  updateElement('sidebar-proc-badge', "0");
  updateElement('total-procs-lbl', "0");
  updateStatusPill(!!targetMachine);
};

/**
 * Cập nhật status pill (hiển thị trạng thái kết nối ở topbar)
 * 
 * @param {boolean} isOnline - true: hiển thị online (màu xanh), false: offline (màu đỏ)
 */
export const updateStatusPill = (isOnline) => {
  const pill = getElementById('global-status-pill');
  if (!pill) return;
  
  if (isOnline) {
    pill.className = "status-pill";
    pill.innerHTML = `<div class="blink"></div>Đang khiển: ${targetMachine}`;
  } else {
    pill.className = "status-pill offline";
    pill.innerHTML = `<div class="blink"></div>Không có thiết bị kết nối`;
  }
};

export default {
  getCurrentOnlineList,
  getTargetMachine,
  setTargetMachine,
  addMachineOnline,
  removeMachineOffline,
  updateMachineDropdown,
  onTargetMachineChange,
  updateStatusPill
};