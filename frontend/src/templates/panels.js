/**
 * Panels Templates - Tất cả các panel nội dung (8 panel)
 * 
 * 📌 CHỨC NĂNG:
 * - Định nghĩa HTML cho 8 panel chức năng
 * - Mỗi panel là một template string (template literal)
 * - Được render bởi renderer.js và ẩn/hiện bởi switchPanel()
 * 
 * 📋 DANH SÁCH PANEL:
 * 1. dashboardPanel: Thống kê tổng quan (số máy, process, audit log)
 * 2. appsPanel: Danh sách ứng dụng whitelist
 * 3. processPanel: Danh sách tiến trình đang chạy
 * 4. screenPanel: Chụp màn hình và live stream
 * 5. keylogPanel: Keylogger feed
 * 6. filePanel: File sandbox
 * 7. webcamPanel: Webcam stream
 * 8. powerPanel: Điều khiển nguồn (Restart/Shutdown)
 * 
 * 🔗 CÁC LIÊN KẾT:
 * - Mỗi panel có id="panel-{name}" để switchPanel() tìm và active
 * - Các button gọi hàm global: triggerScreen(), triggerWebcam(), triggerPower()
 * - Các bảng có id để pages/*.js cập nhật nội dung động
 */

// Content panels template

/**
 * Dashboard - Tổng quan hệ thống
 * Hiển thị 4 thông số: máy online, process, audit logs, quyền
 * Bảng audit log sẽ được cập nhật động bởi audit.js
 */
export const dashboardPanel = `
<div class="panel active" id="panel-dashboard">
  <div class="panel-hdr">
    <span class="panel-title">Hệ thống quản trị phòng thực hành</span>
    <span class="panel-subtitle">Tổng quan realtime kết nối</span>
  </div>
  <div class="grid-4">
    <div class="card"><div class="stat-lbl">Máy Lab trực tuyến</div><div class="stat-val" id="total-online-machines-lbl">0</div></div>
    <div class="card"><div class="stat-lbl">Tiến trình (Máy đang chọn)</div><div class="stat-val" id="total-procs-lbl" style="color:var(--warning)">0</div></div>
    <div class="card"><div class="stat-lbl">Hành động ghi Log</div><div class="stat-val" id="total-logs-lbl" style="color:var(--success)">0</div></div>
    <div class="card"><div class="stat-lbl">Quyền tài khoản</div><div class="stat-val" style="color:white;font-size:18px;margin-top:6px">Giảng viên (Teacher)</div></div>
  </div>
  <div class="card">
    <h3 style="font-size:15px;margin-bottom:12px;color:var(--text-title)">Nhật ký hành động hệ thống gần đây (Audit Log)</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Thời gian</th><th>Người thực hiện</th><th>Thao tác</th><th>Máy trạm</th><th>Trạng thái</th></tr></thead>
        <tbody id="audit-log-rows">
          <tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Hệ thống chưa ghi nhận hoạt động nào...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
`;

/**
 * Applications - Danh sách ứng dụng whitelist
 * Hiển thị các ứng dụng được phép chạy trên máy trạm
 */
export const appsPanel = `
<div class="panel" id="panel-apps">
  <div class="panel-hdr">
    <span class="panel-title">Ứng dụng (Applications Whitelist)</span>
    <span class="panel-subtitle">Chỉ hiển thị và kiểm soát phần mềm được phép</span>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Tên ứng dụng</th><th>Trạng thái</th><th>Tác vụ tương tác</th></tr></thead>
      <tbody id="apps-table-body">
        <tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Vui lòng chọn máy trạm để tải danh sách phần mềm Whitelist...</td></tr>
      </tbody>
    </table>
  </div>
</div>
`;

/**
 * Processes - Danh sách tiến trình
 * Hiển thị top 15 tiến trình với PID, tên, CPU, RAM
 * Có nút Kill để tắt tiến trình
 */
export const processPanel = `
<div class="panel" id="panel-procs">
  <div class="panel-hdr">
    <span class="panel-title">Danh sách tiến trình hệ thống (Processes từ Agent)</span>
    <span class="panel-subtitle">Liệt kê top 15 tiến trình thật quét định kỳ qua Socket</span>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>PID</th><th>Tên tiến trình (Process Name)</th><th>CPU %</th><th>RAM</th><th>Xử lý</th></tr></thead>
      <tbody id="process-table-body">
        <tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Vui lòng chọn hoặc bật máy trạm mục tiêu để xem luồng dữ liệu...</td></tr>
      </tbody>
    </table>
  </div>
</div>
`;

/**
 * Screen - Chụp màn hình và Live Stream
 * - Nút "Chụp ảnh màn hình": chụp tĩnh
 * - Nút "Live Stream": stream 1 FPS
 * - Nút "Dừng stream": tắt live
 * - Consent box thông báo về bảo mật
 */
export const screenPanel = `
<div class="panel" id="panel-screen">
  <div class="panel-hdr">
    <span class="panel-title">Xem và giám sát màn hình từ xa</span>
  </div>
  <div class="toolbar">
    <button class="btn" onclick="triggerScreen('STATIC')"><i class="ti ti-camera"></i> Chụp ảnh màn hình</button>
    <button class="btn secondary" onclick="triggerScreen('LIVE')"><i class="ti ti-live-view"></i> Chạy Live Stream (1 FPS)</button>
    <button class="btn danger" id="btn-stop-screen" onclick="triggerScreen('STOP')" disabled>Dừng luồng stream</button>
  </div>
  <div class="screen-container">
    <div class="screen-img" id="screen-display-area">
      <i class="ti ti-device-desktop" style="font-size:48px;color:var(--text-muted)"></i>
      <span style="color:var(--text-muted)">Chưa có luồng dữ liệu hình ảnh được nạp</span>
    </div>
  </div>
  <div class="consent-box">
    <i class="ti ti-info-circle"></i>
    <div><strong>Giới hạn bảo mật & đạo đức:</strong> Khi bật chức năng này, hệ thống Agent dưới máy trạm bắt buộc hiển thị cảnh báo nổi trên góc phải màn hình của sinh viên để thông báo màn hình đang bị quản lý.</div>
  </div>
</div>
`;

/**
 * Keylogger - Ghi nhận phím bấm
 * - Nút bật/tắt ghi nhận phím
 * - Nút xóa dữ liệu hiển thị
 * - Khu vực hiển thị phím theo thời gian thực
 */
export const keylogPanel = `
<div class="panel" id="panel-keylog">
  <div class="panel-hdr">
    <span class="panel-title">Bắt phím kiểm tra (Keylogger Demo)</span>
    <span class="panel-subtitle">Chỉ ghi nhận luồng phím trong phạm vi được thông báo công khai</span>
  </div>
  <div class="toolbar">
    <button class="btn secondary" id="btn-toggle-kl" onclick="toggleKlState()">Tạm dừng bắt phím</button>
    <button class="btn danger" onclick="clearKlArea()"><i class="ti ti-trash"></i> Xóa dữ liệu khung view</button>
  </div>
  <div class="key-feed" id="key-stream-area">
    <div style="color:var(--text-muted);font-style:italic">Đang chờ phím bấm thời gian thực từ máy trạm...</div>
  </div>
  <div class="consent-box">
    <i class="ti ti-shield-alert"></i>
    <div><strong>Nguyên tắc minh bạch phòng Lab:</strong> Module keylogger này được cài đặt cơ chế sandbox chỉ ghi nhận phím khi sinh viên mở ô nhập liệu thực hành, không theo dõi lén thông tin cá nhân và mật khẩu hệ thống.</div>
  </div>
</div>
`;

/**
 * File - File Sandbox
 * Khu vực an toàn để xem và tải file từ máy trạm
 * Giới hạn trong thư mục chỉ định, chống path traversal
 */
export const filePanel = `
<div class="panel" id="panel-files">
  <div class="panel-hdr">
    <span class="panel-title">Truy cập dữ liệu tệp tin (File Sandbox)</span>
    <span class="panel-subtitle">Thư mục cấu hình an toàn: /home/kali/Downloads/</span>
  </div>
  <div class="file-grid" id="file-list-area">
    <div style="text-align:center;color:var(--text-muted);padding:14px">Chưa có tệp tin nào được tải lên hoặc đồng bộ...</div>
  </div>
  <div class="consent-box">
    <i class="ti ti-lock"></i>
    <div><strong>An toàn thư mục gốc (Path Traversal Protection):</strong> Agent từ chối tuyệt đối mọi truy xuất lệnh nhảy cấp thư mục như \`../../etc/passwd\`. Chỉ được xem và tải file nằm trong vùng chỉ định.</div>
  </div>
</div>
`;

/**
 * Webcam - Webcam Stream
 * Bật/tắt webcam trên máy trạm
 * Yêu cầu sự đồng ý của sinh viên trước khi bật
 */
export const webcamPanel = `
<div class="panel" id="panel-webcam">
  <div class="panel-hdr">
    <span class="panel-title">Kiểm soát thiết bị ghi hình (Webcam Access)</span>
  </div>
  <div class="toolbar">
    <button class="btn" onclick="triggerWebcam(true)"><i class="ti ti-video"></i> Yêu cầu luồng Webcam</button>
    <button class="btn danger" onclick="triggerWebcam(false)">Tắt Webcam</button>
  </div>
  <div class="webcam-box" id="webcam-display-box">
    <div style="text-align:center;color:var(--text-muted)">
      <i class="ti ti-camera-off" style="font-size:40px;margin-bottom:8px"></i>
      <div>Webcam đang đóng</div>
    </div>
  </div>
  <div class="consent-box">
    <i class="ti ti-user-check"></i>
    <div><strong>Yêu cầu bắt buộc sự đồng ý (Consent Model):</strong> Luồng webcam hoàn toàn không thể kích hoạt lén. Một hộp thoại popup xác nhận rõ ràng sẽ hiện bên phía sinh viên. Nếu chọn từ chối, Server sẽ lập tức hủy phiên làm việc.</div>
  </div>
</div>
`;

/**
 * Power - Điều khiển nguồn
 * Restart: Khởi động lại máy trạm
 * Shutdown: Tắt nguồn máy trạm
 * Cả 2 đều có cảnh báo xác nhận
 */
export const powerPanel = `
<div class="panel" id="power-panel">
  <div class="panel-hdr">
    <span class="panel-title">Điều khiển nguồn điện máy tính trạm</span>
    <span class="panel-subtitle">Hành động nhạy cảm - Cần thực hiện có trách nhiệm</span>
  </div>
  <div class="power-grid">
    <div class="power-card animate" onclick="triggerPower('RESTART')">
      <div class="power-icon" style="color:var(--warning)"><i class="ti ti-refresh"></i></div>
      <div class="power-name">Khởi động lại (Restart)</div>
      <div class="power-desc">Làm mới hệ điều hành máy trạm</div>
    </div>
    <div class="power-card danger-zone" onclick="triggerPower('SHUTDOWN')">
      <div class="power-icon" style="color:var(--danger)"><i class="ti ti-power"></i></div>
      <div class="power-name">Tắt máy nguồn từ xa (Shutdown)</div>
      <div class="power-desc">Sập nguồn hoàn toàn máy trạm mục tiêu</div>
    </div>
  </div>
</div>
`;

export default {
  dashboardPanel,
  appsPanel,
  processPanel,
  screenPanel,
  keylogPanel,
  filePanel,
  webcamPanel,
  powerPanel
};