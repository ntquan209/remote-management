/**
 * Sidebar Template - Menu điều hướng bên trái
 * 
 * 📌 CHỨC NĂNG:
 * - Hiển thị logo và tên ứng dụng
 * - Menu điều hướng tới các chức năng
 * - Badge hiển thị số lượng (apps, processes)
 * 
 * 📋 CÁC MỤC MENU:
 * - Dashboard: Tổng quan phòng lab
 * - Applications: Danh sách ứng dụng
 * - Processes: Danh sách tiến trình
 * - Screenshot & Live: Chụp/Stream màn hình
 * - Keylogger: Ghi nhận phím bấm
 * - File Sandbox: Quản lý file
 * - Webcam Stream: Camera
 * - Power Control: Tắt/khởi động lại máy
 */

// Sidebar template
export const sidebarTemplate = `
<aside class="sidebar">
  <div class="brand">
    <div class="brand-logo">RL</div>
    <div>
      <div class="brand-title">Remote Lab</div>
      <div style="font-size:11px;color:var(--text-muted)">VNU-HCMUS @2026</div>
    </div>
  </div>

  <div class="nav-section">Giám sát tổng quan</div>
  <a class="nav-item active" onclick="switchPanel('dashboard', this)"><i class="ti ti-layout-dashboard"></i> Dashboard Phòng Lab</a>

  <div class="nav-section">Module chức năng</div>
  <a class="nav-item" onclick="switchPanel('apps', this)"><i class="ti ti-apps"></i> Applications <span class="badge" id="sidebar-apps-badge">0</span></a>
  <a class="nav-item" onclick="switchPanel('procs', this)"><i class="ti ti-cpu"></i> Processes <span class="badge" id="sidebar-proc-badge">0</span></a>
  <a class="nav-item" onclick="switchPanel('screen', this)"><i class="ti ti-device-desktop"></i> Screenshot & Live</a>
  <a class="nav-item" onclick="switchPanel('keylog', this)"><i class="ti ti-keyboard"></i> Keylogger</a>
  <a class="nav-item" onclick="switchPanel('files', this)"><i class="ti ti-folder-download"></i> File Sandbox</a>
  <a class="nav-item" onclick="switchPanel('webcam', this)"><i class="ti ti-camera"></i> Webcam Stream</a>
  <a class="nav-item" onclick="switchPanel('power', this)"><i class="ti ti-power"></i> Power Control</a>
</aside>
`;

export default sidebarTemplate;