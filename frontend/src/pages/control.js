/**
 * Control Page Module - Điều khiển Webcam và Nguồn điện
 * 
 * 📌 CHỨC NĂNG:
 * - Bật/tắt webcam trên máy trạm (handleWebcamTrigger)
 * - Gửi lệnh tắt máy/khởi động lại (handlePowerCommand)
 * - Bật/tắt keylogger recording (toggleKeyloggerState)
 * - Xóa vùng hiển thị keylogger (clearKeyloggerArea)
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. Người dùng click nút Webcam/Power trên UI
 * 2. Hàm kiểm tra máy đã chọn chưa (getTargetMachine)
 * 3. Nếu chưa chọn → alert "Chưa chọn máy trạm!"
 * 4. Nếu đã chọn → emitCommand() gửi lệnh qua WebSocket
 * 
 * 📡 CÁC LỆNH GỬI ĐI:
 * - "WEBCAM_START": Bật webcam
 * - "WEBCAM_STOP": Tắt webcam
 * - "RESTART": Khởi động lại máy
 * - "SHUTDOWN": Tắt máy
 */

// Control page module (Webcam, Power)
import { getElementById } from '../utils/dom.js';
import { emitCommand } from '../lib/socket.js';
import { getTargetMachine } from '../components/machine-selector.js';
import { addAuditRow } from '../utils/audit.js';

/**
 * Xử lý bật/tắt webcam trên máy trạm
 * 
 * @param {boolean} isOn - true: bật webcam, false: tắt webcam
 * 
 * Khi bật:
 * - Hiển thị thông báo "Đang gửi yêu cầu Consent"
 * - Gửi lệnh WEBCAM_START
 * 
 * Khi tắt:
 * - Hiển thị "Webcam đã tắt"
 * - Gửi lệnh WEBCAM_STOP
 */
export const handleWebcamTrigger = (isOn) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Chưa chọn máy trạm!");
  
  const box = getElementById('webcam-display-box');
  if (!box) return;
  
  if (isOn) {
    box.innerHTML = `<div style="color:var(--success);font-weight:600;text-align:center;"><i class="ti ti-camera" style="font-size:40px;margin-bottom:8px;color:var(--primary)"></i><div>Đang gửi yêu cầu Consent xuống máy trạm...</div></div>`;
    sessionStorage.setItem(`webcam_active_${targetMachine}`, 'TRUE');
    console.log(`[WEBCAM CONTROL] Enable webcam for ${targetMachine}`);
    emitCommand('WEBCAM_START', targetMachine);
  } else {
    box.innerHTML = `<div style="text-align:center;color:var(--text-muted)"><i class="ti ti-camera-off" style="font-size:40px;margin-bottom:8px"></i><div>Webcam đã tắt thành công</div></div>`;
    sessionStorage.removeItem(`webcam_active_${targetMachine}`);
    console.log(`[WEBCAM CONTROL] Disable webcam for ${targetMachine}`);
    emitCommand('WEBCAM_STOP', targetMachine);
  }
};

/**
 * Xử lý lệnh điều khiển nguồn (Restart/Shutdown)
 * 
 * @param {string} type - "RESTART" hoặc "SHUTDOWN"
 * 
 * Có cảnh báo xác nhận trước khi gửi lệnh vì đây là hành động nguy hiểm:
 * - Mất dữ liệu chưa lưu của sinh viên
 * - Ghi audit log khi gửi lệnh
 */
export const handlePowerCommand = (type) => {
  const targetMachine = getTargetMachine();
  if (!targetMachine) return alert("Chưa chọn máy trạm!");
  
  const check = confirm(`CẢNH BÁO: Bạn có chắc chắn gửi lệnh mạng [${type}] tới máy ${targetMachine} không? Tất cả dữ liệu chưa lưu của sinh viên sẽ bị mất.`);
  if (check) {
    emitCommand(type, targetMachine);
    addAuditRow(type, targetMachine, 'Đã bắn lệnh hủy nguồn');
  }
};

let klCapturing = true;  // Trạng thái keylogger: true = đang ghi, false = tạm dừng

/**
 * Bật/tắt trạng thái ghi nhận keylogger
 * Thay đổi text trên nút tương ứng
 */
export const toggleKeyloggerState = () => {
  klCapturing = !klCapturing;
  const btn = getElementById('btn-toggle-kl');
  if (btn) btn.textContent = klCapturing ? "Tạm dừng bắt phím" : "Tiếp tục bắt phím";
};

/**
 * Xóa toàn bộ dữ liệu keylogger hiển thị trên UI
 */
export const clearKeyloggerArea = () => {
  const area = getElementById('key-stream-area');
  if (area) area.innerHTML = `<div style="color:var(--text-muted);font-style:italic">Dữ liệu log phím tạm thời trống...</div>`;
};

export default { 
  handleWebcamTrigger, 
  handlePowerCommand, 
  toggleKeyloggerState, 
  clearKeyloggerArea 
};