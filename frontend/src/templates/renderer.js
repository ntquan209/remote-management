/**
 * Template Renderer - Tổng hợp và render toàn bộ giao diện
 * (Bản khôi phục chuẩn: Vá lỗi bị copy đè mã nguồn socket)
 */

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
  
  // Topbar (thanh trên cùng)
  mainDiv.innerHTML = topbarTemplate;
  
  // Content area với tất cả các panel hành động
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