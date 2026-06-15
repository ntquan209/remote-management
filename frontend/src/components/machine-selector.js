/**
 * Machine Selector Component - Chọn và quản lý máy trạm (Bản sửa đổi tự động nạp)
 */

import { getElementById, updateElement } from '../utils/dom.js';

let currentOnlineList = new Set();  // Danh sách máy online
let targetMachine = "";              // Máy đang được chọn

export const getCurrentOnlineList = () => currentOnlineList;
export const getTargetMachine = () => targetMachine;
export const setTargetMachine = (machine) => { targetMachine = machine; };

/**
 * Thêm máy vào danh sách online (Kích hoạt lập tức không cần đợi tiến trình)
 */
export const addMachineOnline = (machine) => {
  if (!machine) return;
  if (!currentOnlineList.has(machine)) {
    currentOnlineList.add(machine);
    updateMachineDropdown();  // Cập nhật lại dropdown giao diện ngay lập tức
  }
};

/**
 * Xóa máy khỏi danh sách online (khi agent ngắt kết nối)
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
 */
export const onTargetMachineChange = () => {
  const select = getElementById('machine-select');
  if (!select) return;
  targetMachine = select.value;

  // Reset process table với thông báo nạp luồng thông tin mới
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