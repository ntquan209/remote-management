/**
 * Machine Selector Component - Chọn và quản lý máy trạm
 * (Bản sửa lỗi: Khóa cứng máy trạm đang chọn, bảo vệ luồng Live stream đa máy)
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

  // Giữ lại máy đang chọn trước đó để bảo vệ trạng thái ổn định
  const savedTarget = targetMachine;
  select.innerHTML = "";

  if (currentOnlineList.size === 0) {
    select.innerHTML = '<option value="">-- Trống (Offline) --</option>';
    targetMachine = "";
    updateStatusPill(false);
    return;
  }

  // Tạo option mặc định ban đầu để người dùng chủ động chọn, tránh tự nhảy máy
  const defaultOpt = document.createElement('option');
  defaultOpt.value = "";
  defaultOpt.textContent = "-- Chọn máy trạm mục tiêu --";
  select.appendChild(defaultOpt);

  // Tạo option cho mỗi máy online
  currentOnlineList.forEach(machine => {
    const opt = document.createElement('option');
    opt.value = machine;
    opt.textContent = machine;
    select.appendChild(opt);
  });

  // 🎯 KHÓA TRẠNG THÁI CHÍNH XÁC: 
  // Nếu máy cũ vẫn online, giữ nguyên selection. Tuyệt đối không tự chọn máy đầu tiên!
  if (savedTarget && currentOnlineList.has(savedTarget)) {
    select.value = savedTarget;
    targetMachine = savedTarget;
  } else {
    // Nếu máy cũ đã bốc hơi (offline), trả về trạng thái chờ chọn
    select.value = "";
    targetMachine = "";
  }

  // Cập nhật số máy online trên dashboard
  updateElement('total-online-machines-lbl', currentOnlineList.size);
  updateStatusPill(!!targetMachine);
};

/**
 * Khi người dùng chọn máy từ dropdown
 */
export const onTargetMachineChange = () => {
  const select = getElementById('machine-select');
  if (!select) return;
  targetMachine = select.value;

  // Reset bảng tiến trình về trạng thái chờ nạp dữ liệu của máy mới chọn
  const tbody = getElementById('process-table-body');
  if (tbody) {
    if (targetMachine) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Đang nạp luồng tiến trình thời gian thực của máy [${targetMachine}]...</td></tr>`;
    } else {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Vui lòng chọn một máy trạm để xem tiến trình...</td></tr>`;
    }
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

  if (isOnline && targetMachine) {
    pill.className = "status-pill";
    pill.innerHTML = `<div class="blink"></div>Đang khiển: <strong>${targetMachine}</strong>`;
  } else {
    pill.className = "status-pill offline";
    pill.innerHTML = `<div class="blink"></div>Hệ thống đang chờ thiết bị...`;
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