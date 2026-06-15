/**
 * Audit Log Utilities - Ghi nhật ký hoạt động hệ thống
 * 
 * 📌 CHỨC NĂNG:
 * - Ghi lại mọi hành động của giảng viên trên hệ thống
 * - Thêm dòng log vào bảng audit trong dashboard
 * - Phân biệt log do người dùng (addAuditRow) và log hệ thống (logSystemEvent)
 * - Tự động cập nhật tổng số log trên dashboard
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. Khi có thao tác (shutdown, screenshot...), gọi addAuditRow()
 * 2. Khi có sự kiện hệ thống (connect, disconnect...), gọi logSystemEvent()
 * 3. Hàm tạo dòng mới trong bảng #audit-log-rows
 * 4. Cập nhật số lượng log ở #total-logs-lbl trên dashboard
 * 
 * 📋 CẤU TRÚC MỖI DÒNG LOG:
 * | Thời gian | Người thực hiện | Thao tác | Máy trạm | Trạng thái |
 */

// Audit log utilities
import { getElementById, updateElement } from './dom.js';

let totalLogsCount = 0;

/**
 * Thêm dòng log cho hành động của người dùng (giảng viên)
 * 
 * @param {string} action - Hành động (vd: "SHUTDOWN", "SCREENSHOT")
 * @param {string} machine - Máy trạm mục tiêu
 * @param {string} status - Trạng thái (vd: "Đã bắn lệnh", "Thành công")
 * 
 * Mỗi lần gọi:
 * 1. Nếu là log đầu tiên, xóa dòng "chưa có hoạt động"
 * 2. Tạo dòng mới với thời gian hiện tại + email giảng viên mặc định
 * 3. Chèn dòng mới lên đầu bảng
 * 4. Tăng biến đếm và cập nhật UI
 */
export const addAuditRow = (action, machine, status) => {
  const body = getElementById('audit-log-rows');
  if (!body) return;
  
  // Nếu là log đầu tiên, xóa dòng placeholder
  if (totalLogsCount === 0) {
    body.innerHTML = "";
  }

  const timeStr = new Date().toLocaleTimeString();
  const row = document.createElement('tr');
  row.innerHTML = `
    <td>${timeStr}</td>
    <td>teacher@hcmus.edu.vn</td>
    <td><strong>${action}</strong></td>
    <td>${machine}</td>
    <td><span>${status}</span></td>
  `;
  // Chèn dòng mới lên đầu (mới nhất ở trên)
  body.insertBefore(row, body.firstChild);

  totalLogsCount++;
  updateElement('total-logs-lbl', totalLogsCount);
};

/**
 * Thêm dòng log cho sự kiện hệ thống (agent connect/disconnect...)
 * 
 * @param {string} action - Hành động
 * @param {string} machine - Máy trạm
 * @param {string} status - Trạng thái
 * @param {boolean|null} isOnline - true = online (màu xanh), false = offline (màu đỏ)
 * 
 * Khác với addAuditRow: người thực hiện là "Hệ thống",
 * và có thể tô màu trạng thái theo online/offline
 */
export const logSystemEvent = (action, machine, status, isOnline = null) => {
  const body = getElementById('audit-log-rows');
  if (!body) return;
  
  if (totalLogsCount === 0) {
    body.innerHTML = "";
  }

  // Tô màu trạng thái dựa vào online/offline
  let statusStyle = "";
  if (isOnline === true) {
    statusStyle = `style="color: var(--success); font-weight: bold;"`;
  } else if (isOnline === false) {
    statusStyle = `style="color: var(--danger); font-weight: bold;"`;
  }

  const timeStr = new Date().toLocaleTimeString();
  const row = document.createElement('tr');
  row.innerHTML = `
    <td>${timeStr}</td>
    <td>Hệ thống (System)</td>
    <td><strong>${action}</strong></td>
    <td>${machine}</td>
    <td><span ${statusStyle}>${status}</span></td>
  `;
  body.insertBefore(row, body.firstChild);
  
  totalLogsCount++;
  updateElement('total-logs-lbl', totalLogsCount);
};

export const getTotalLogs = () => totalLogsCount;

export default { addAuditRow, logSystemEvent, getTotalLogs };