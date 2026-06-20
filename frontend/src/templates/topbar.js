/**
 * Topbar Template - Thanh trên cùng
 * 
 * 📌 CHỨC NĂNG:
 * - Dropdown chọn máy trạm mục tiêu (machine-selector)
 * - Status pill hiển thị trạng thái kết nối (online/offline)
 * - Thông tin user đã đăng nhập + nút đăng xuất
 * 
 * 🔗 LIÊN KẾT:
 * - #machine-select: Dropdown, onChange → gọi onTargetMachineChange()
 * - #global-status-pill: Hiển thị trạng thái, cập nhật bởi machine-selector.js
 * - #user-info-area: Hiển thị tên + role + nút logout
 */

// Topbar template
export const topbarTemplate = `
<header class="topbar">
  <div class="machine-selector-wrapper">
    <label for="machine-select" style="font-size: 13px; font-weight: 600; color: var(--text-muted)">MÁY MỤC TIÊU:</label>
    <select id="machine-select" class="select-machine" onchange="onTargetMachineChange()">
      <option value="">-- Trống (Offline) --</option>
    </select>
  </div>
  <div class="machine-info">
    <div id="global-status-pill" class="status-pill offline"><div class="blink"></div>Không có thiết bị kết nối</div>
    <span id="user-info-area" style="margin-left:12px;display:flex;align-items:center;gap:8px"></span>
  </div>
</header>
`;

export default topbarTemplate;