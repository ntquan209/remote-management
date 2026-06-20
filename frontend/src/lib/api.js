/**
 * API Helper - Gọi REST API backend (xác thực + phân quyền)
 * 
 * 📌 CHỨC NĂNG:
 * - Đăng ký tài khoản mới
 * - Đăng nhập, lưu JWT token vào localStorage
 * - Gọi API với Bearer token tự động
 * - Kiểm tra trạng thái đăng nhập
 * - Đăng xuất
 * - Quản lý user (admin): danh sách, đổi role, xóa, khóa/mở khóa
 * 
 * 🔁 LUỒNG HOẠT ĐỘNG:
 * 1. register() / login() → gọi API backend → nhận token
 * 2. Lưu token + thông tin user vào localStorage
 * 3. Các API call sau tự động gắn Authorization header
 * 4. isAuthenticated() kiểm tra token còn hạn không
 * 5. logout() xóa token khỏi localStorage
 * 
 * 🔐 PHÂN QUYỀN:
 * - student: chỉ xem dashboard cơ bản
 * - teacher: xem và điều khiển agent
 * - admin: toàn quyền + quản lý user
 */

import { APP_CONFIG } from '../config/app.config.js';

const API = APP_CONFIG.API_BASE_URL;

/**
 * Gọi API với phương thức POST
 * @param {string} endpoint - Đường dẫn API (vd: "/api/login")
 * @param {object} body - Dữ liệu gửi lên
 * @param {boolean} auth - Có gắn Bearer token không?
 */
async function apiPost(endpoint, body, auth = false) {
    const headers = { 'Content-Type': 'application/json' };
    
    if (auth) {
        const token = getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
    }
    
    const response = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.detail || 'Lỗi kết nối đến server');
    }
    
    return data;
}

/**
 * Gọi API với phương thức GET
 */
async function apiGet(endpoint) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API}${endpoint}`, { headers });
    
    let data;
    try {
        data = await response.json();
    } catch (e) {
        throw new Error('Lỗi đọc phản hồi từ server');
    }
    
    if (!response.ok) {
        const detail = data.detail || data.message || 'Lỗi kết nối đến server';
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    
    return data;
}

// ==================== AUTH API ====================

/**
 * Đăng ký tài khoản mới
 */
export async function register(username, email, password, fullName = '') {
    const data = await apiPost('/api/register', {
        username,
        email,
        password,
        full_name: fullName,
    });
    
    // Lưu token và user info vào localStorage
    localStorage.setItem('auth_token', data.access_token);
    localStorage.setItem('auth_user', JSON.stringify(data.user));
    
    return data;
}

/**
 * Đăng nhập
 */
export async function login(username, password) {
    const data = await apiPost('/api/login', {
        username,
        password,
    });
    
    // Lưu token và user info vào localStorage
    localStorage.setItem('auth_token', data.access_token);
    localStorage.setItem('auth_user', JSON.stringify(data.user));
    
    return data;
}

/**
 * Lấy thông tin user hiện tại từ API (dùng token)
 */
export async function getMe() {
    return await apiGet('/api/me');
}

/**
 * Lấy token từ localStorage
 */
export function getToken() {
    return localStorage.getItem('auth_token');
}

/**
 * Lấy thông tin user từ localStorage
 */
export function getUser() {
    const userStr = localStorage.getItem('auth_user');
    return userStr ? JSON.parse(userStr) : null;
}

/**
 * Kiểm tra đã đăng nhập chưa
 */
export function isAuthenticated() {
    return !!getToken();
}

/**
 * Đăng xuất: xóa token khỏi localStorage
 */
export function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    window.location.reload();
}

// ==================== API PUT/DELETE HELPER ====================

async function apiPut(endpoint, body) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(`${API}${endpoint}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(body),
    });
    let data;
    try {
        data = await response.json();
    } catch (e) {
        throw new Error('Lỗi đọc phản hồi từ server');
    }
    if (!response.ok) {
        const detail = data.detail || data.message || 'Lỗi kết nối đến server';
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    return data;
}

async function apiDelete(endpoint) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(`${API}${endpoint}`, {
        method: 'DELETE',
        headers,
    });
    let data;
    try {
        data = await response.json();
    } catch (e) {
        throw new Error('Lỗi đọc phản hồi từ server');
    }
    if (!response.ok) {
        const detail = data.detail || data.message || 'Lỗi kết nối đến server';
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    return data;
}

// ==================== ADMIN API ====================

/**
 * Lấy danh sách tất cả người dùng (yêu cầu quyền admin)
 */
export async function adminListUsers() {
    return await apiGet('/api/admin/users');
}

/**
 * Đổi vai trò người dùng (yêu cầu quyền admin)
 */
export async function adminUpdateRole(userId, role) {
    return await apiPut(`/api/admin/users/${userId}/role`, { role });
}

/**
 * Xóa người dùng (yêu cầu quyền admin)
 */
export async function adminDeleteUser(userId) {
    return await apiDelete(`/api/admin/users/${userId}`);
}

/**
 * Khóa/Mở khóa tài khoản người dùng (yêu cầu quyền admin)
 */
export async function adminToggleActive(userId) {
    return await apiPut(`/api/admin/users/${userId}/toggle-active`, {});
}

/**
 * Kiểm tra role của user hiện tại
 */
export function hasRole(requiredRole) {
    const user = getUser();
    if (!user) return false;
    const ROLES = { admin: 3, teacher: 2, student: 1 };
    return (ROLES[user.role] || 0) >= (ROLES[requiredRole] || 0);
}
