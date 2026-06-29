/**
 * Auth Page Module - Trang Đăng nhập / Đăng ký
 * 
 * 📌 CHỨC NĂNG:
 * - Hiển thị giao diện đăng nhập / đăng ký
 * - Chuyển đổi giữa 2 chế độ (login ↔ register)
 * - Gọi API xác thực, xử lý lỗi, hiển thị thông báo
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. renderAuthPage() → vẽ form login mặc định
 * 2. Người dùng click "Đăng ký" → switchToRegister() → vẽ form register
 * 3. Người dùng click "Đăng nhập" → switchToLogin() → vẽ form login
 * 4. Submit form → gọi API:
 *    - Login thành công → reload trang (vào app)
 *    - Register thành công → hiển thị thông báo chờ admin duyệt
 *    - Thất bại → hiển thị lỗi
 */

/** Hiển thị thông báo chờ admin duyệt sau khi đăng ký */
function showPendingApproval() {
    const loginForm = document.getElementById('auth-login-form');
    const registerForm = document.getElementById('auth-register-form');
    loginForm.style.display = 'none';
    registerForm.style.display = 'none';
    
    const box = document.getElementById('auth-box');
    const msgEl = document.createElement('div');
    msgEl.id = 'pending-approval';
    msgEl.innerHTML = `
        <div style="text-align:center;padding:20px 0">
            <div style="font-size:48px;margin-bottom:16px">✅</div>
            <h2 style="color:var(--success);margin-bottom:12px">Đăng ký thành công!</h2>
            <p style="color:var(--text-muted);line-height:1.6;margin-bottom:20px">
                Tài khoản của bạn đang chờ <strong>Admin</strong> phê duyệt.<br>
                Vui lòng quay lại sau khi tài khoản được kích hoạt.
            </p>
            <button class="auth-btn" onclick="switchToLogin()">Quay lại đăng nhập</button>
        </div>
    `;
    box.appendChild(msgEl);
}

import { login, register } from '../lib/api.js';

// HTML template cho trang auth
const authTemplate = `
<div id="auth-container">
    <div class="auth-background"></div>
    <div class="auth-box" id="auth-box">
        <!-- Header -->
        <div class="auth-header">
            <div class="auth-logo">RL</div>
            <h1 class="auth-title">Remote Lab</h1>
            <p class="auth-subtitle">Hệ thống quản trị phòng thực hành từ xa</p>
        </div>

        <!-- Login Form (mặc định hiển thị) -->
        <form id="auth-login-form" class="auth-form" onsubmit="return handleLogin(event)">
            <h2 class="auth-form-title">Đăng nhập</h2>
            
            <div class="auth-field">
                <label for="login-username">Tên đăng nhập</label>
                <input type="text" id="login-username" placeholder="Nhập tên đăng nhập..." required />
            </div>
            
            <div class="auth-field">
                <label for="login-password">Mật khẩu</label>
                <input type="password" id="login-password" placeholder="Nhập mật khẩu..." required />
            </div>
            
            <div id="login-error" class="auth-error" style="display:none"></div>
            
            <button type="submit" class="auth-btn" id="login-btn">Đăng nhập</button>
            
            <p class="auth-switch">
                Chưa có tài khoản? 
                <a href="#" onclick="switchToRegister(); return false;">Đăng ký ngay</a>
            </p>
        </form>

        <!-- Register Form (ẩn mặc định) -->
        <form id="auth-register-form" class="auth-form" style="display:none" onsubmit="return handleRegister(event)">
            <h2 class="auth-form-title">Đăng ký tài khoản</h2>
            
            <div class="auth-field">
                <label for="reg-fullname">Họ tên (tùy chọn)</label>
                <input type="text" id="reg-fullname" placeholder="Nhập họ tên..." />
            </div>
            
            <div class="auth-field">
                <label for="reg-username">Tên đăng nhập *</label>
                <input type="text" id="reg-username" placeholder="Nhập tên đăng nhập..." required />
            </div>
            
            <div class="auth-field">
                <label for="reg-email">Email *</label>
                <input type="email" id="reg-email" placeholder="Nhập email..." required />
            </div>
            
            <div class="auth-field">
                <label for="reg-password">Mật khẩu *</label>
                <input type="password" id="reg-password" placeholder="Nhập mật khẩu (ít nhất 6 ký tự)..." required />
            </div>
            
            <div class="auth-field">
                <label for="reg-confirm">Xác nhận mật khẩu *</label>
                <input type="password" id="reg-confirm" placeholder="Nhập lại mật khẩu..." required />
            </div>
            
            <div id="register-error" class="auth-error" style="display:none"></div>
            
            <button type="submit" class="auth-btn" id="register-btn">Đăng ký</button>
            
            <p class="auth-switch">
                Đã có tài khoản? 
                <a href="#" onclick="switchToLogin(); return false;">Đăng nhập</a>
            </p>
        </form>
    </div>
</div>
`;

/**
 * Render trang auth vào body (thay thế nội dung hiện tại)
 */
export function renderAuthPage() {
    // Xóa toàn bộ nội dung cũ
    document.body.innerHTML = authTemplate;
}

/**
 * Chuyển sang form đăng ký
 */
window.switchToRegister = function() {
    document.getElementById('auth-login-form').style.display = 'none';
    document.getElementById('auth-register-form').style.display = 'block';
    document.getElementById('login-error').style.display = 'none';
    document.getElementById('register-error').style.display = 'none';
};

/**
 * Chuyển sang form đăng nhập
 */
window.switchToLogin = function() {
    // Xóa thông báo chờ duyệt nếu có
    const pendingEl = document.getElementById('pending-approval');
    if (pendingEl) pendingEl.remove();
    
    document.getElementById('auth-register-form').style.display = 'none';
    document.getElementById('auth-login-form').style.display = 'block';
    document.getElementById('login-error').style.display = 'none';
    document.getElementById('register-error').style.display = 'none';
};

/**
 * Xử lý đăng nhập
 */
window.handleLogin = async function(event) {
    event.preventDefault();
    
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');
    const btn = document.getElementById('login-btn');
    
    if (!username || !password) {
        showError(errorEl, 'Vui lòng nhập đầy đủ thông tin');
        return false;
    }
    
    btn.disabled = true;
    btn.textContent = 'Đang đăng nhập...';
    
    try {
        await login(username, password);
        // Thành công → reload để vào app
        window.location.reload();
    } catch (err) {
        showError(errorEl, err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Đăng nhập';
    }
    
    return false;
};

/**
 * Xử lý đăng ký
 */
window.handleRegister = async function(event) {
    event.preventDefault();
    
    const fullname = document.getElementById('reg-fullname').value.trim();
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirm = document.getElementById('reg-confirm').value;
    const errorEl = document.getElementById('register-error');
    const btn = document.getElementById('register-btn');
    
    // Kiểm tra dữ liệu đầu vào
    if (!username || !email || !password || !confirm) {
        showError(errorEl, 'Vui lòng điền đầy đủ các trường bắt buộc (*)');
        return false;
    }
    
    if (password.length < 6) {
        showError(errorEl, 'Mật khẩu phải có ít nhất 6 ký tự');
        return false;
    }
    
    if (password !== confirm) {
        showError(errorEl, 'Xác nhận mật khẩu không khớp');
        return false;
    }
    
    btn.disabled = true;
    btn.textContent = 'Đang đăng ký...';
    
    try {
        await register(username, email, password, fullname);
        // Thành công → xóa token vì chưa active, hiển thị chờ duyệt
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        showPendingApproval();
    } catch (err) {
        showError(errorEl, err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Đăng ký';
    }
    
    return false;
};

/**
 * Hiển thị lỗi
 */
function showError(el, message) {
    el.textContent = message;
    el.style.display = 'block';
}

export default { renderAuthPage };