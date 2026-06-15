/**
 * Template Renderer - Tổng hợp và render toàn bộ giao diện
 * 
 * 📌 CHỨC NĂNG:
 * - Import tất cả template HTML từ các file khác
 * - renderApp() → Ghép các template lại và đưa vào DOM
 * - Tạo cấu trúc: sidebar (trái) + main (phải: topbar + content-area)
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. Query selector tìm div.app trong index.html
 * 2. Tạo sidebar div và gán sidebarTemplate (từ sidebar.js)
 * 3. Tạo main div và gán topbarTemplate (từ topbar.js)
 * 4. Tạo content-area và gán tất cả panel templates (từ panels.js)
 * 5. Ghép tất cả vào DOM
 * 
 * 📋 CÁC PANEL:
 * - dashboardPanel: Thống kê tổng quan
 * - appsPanel: Danh sách ứng dụng
 * - processPanel: Danh sách tiến trình
 * - screenPanel: Chụp màn hình
 * - keylogPanel: Keylogger
 * - filePanel: File sandbox
 * - webcamPanel: Webcam
 * - powerPanel: Điều khiển nguồn
 */

// Template renderer
import { sidebarTemplate } from './sidebar.js';
import { topbarTemplate } from './topbar.js';
import {
  dashboardPanel,
  appsPanel,
  processPanel,
  screenPanel,
  keylogPanel,
  filePanel,
  webcamPanel,
  powerPanel
} from './panels.js';

/**
 * renderApp - Hàm chính để vẽ toàn bộ giao diện
 * 
 * Được gọi từ index.js khi trang load
 * Tạo cấu trúc HTML:
 * <div class="app">
 *   <aside class="sidebar">...</aside>
 *   <main class="main">
 *     <header class="topbar">...</header>
 *     <div class="content-area">
 *       <div id="panel-dashboard">...</div>
 *       <div id="panel-apps">...</div>
 *       ...các panel khác
 *     </div>
 *   </main>
 * </div>
 */
export const renderApp = () => {
  const appContainer = document.querySelector('.app');
  if (!appContainer) {
    console.error('Không tìm thấy container .app trong DOM');
    return;
  }

  // Render sidebar (menu bên trái)
  const sidebarDiv = document.createElement('div');
  sidebarDiv.innerHTML = sidebarTemplate;
  appContainer.appendChild(sidebarDiv.firstElementChild);

  // Render main content (khu vực chính bên phải)
  const mainDiv = document.createElement('main');
  mainDiv.className = 'main';
  
  // Topbar (thanh trên cùng: chọn máy + trạng thái)
  mainDiv.innerHTML = topbarTemplate;
  
  // Content area với tất cả các panel
  const contentArea = document.createElement('div');
  contentArea.className = 'content-area';
  contentArea.innerHTML = `
    ${dashboardPanel}
    ${appsPanel}
    ${processPanel}
    ${screenPanel}
    ${keylogPanel}
    ${filePanel}
    ${webcamPanel}
    ${powerPanel}
  `;
  
  mainDiv.appendChild(contentArea);
  appContainer.appendChild(mainDiv);
};

export default renderApp;