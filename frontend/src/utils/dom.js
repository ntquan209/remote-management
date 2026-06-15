/**
 * DOM Utilities - Các hàm tiện ích thao tác DOM
 * 
 * 📌 CHỨC NĂNG:
 * - Các hàm wrapper ngắn gọn cho thao tác DOM thường dùng
 * - Giúp code gọn hơn và dễ đọc hơn
 * 
 * 🔧 CÁC HÀM:
 * - getElementById(id): Lấy element theo ID (wrapper cho document.getElementById)
 * - switchPanel(panelId, element): Chuyển đổi panel đang hiển thị
 * - updateElement(id, content): Cập nhật text content của element
 * - setHTML(id, html): Gán innerHTML cho element
 * - enableButton(id, enabled): Bật/tắt button
 */

// DOM utilities
export const getElementById = (id) => document.getElementById(id);

/**
 * Chuyển đổi panel đang hiển thị
 * 
 * @param {string} panelId - ID của panel (vd: "dashboard", "procs", "screen")
 * @param {HTMLElement} element - Nav item được click (để active highlight)
 * 
 * Luồng:
 * 1. Xóa class 'active' khỏi tất cả panel và nav-item
 * 2. Thêm class 'active' cho panel đích và nav-item được click
 * 
 * Panel được tìm theo ID: "panel-" + panelId hoặc panelId + "-panel"
 */
export const switchPanel = (panelId, element) => {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  
  const targetPanel = getElementById('panel-' + panelId) || getElementById(panelId + '-panel');
  if (targetPanel) targetPanel.classList.add('active');
  if (element) element.classList.add('active');
};

/**
 * Cập nhật text content của một element theo ID
 * Dùng để cập nhật số liệu thống kê (dashboard)
 */
export const updateElement = (id, content) => {
  const el = getElementById(id);
  if (el) el.textContent = content;
};

/**
 * Gán innerHTML cho một element theo ID
 * Dùng để render nội dung động (danh sách process, log...)
 */
export const setHTML = (id, html) => {
  const el = getElementById(id);
  if (el) el.innerHTML = html;
};

/**
 * Bật/tắt trạng thái disabled của button
 * Dùng để vô hiệu hóa nút trong khi đang xử lý
 */
export const enableButton = (id, enabled = true) => {
  const btn = getElementById(id);
  if (btn) btn.disabled = !enabled;
};

export default { switchPanel, getElementById, updateElement, setHTML, enableButton };