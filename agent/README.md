# Agent Kali Linux - Remote Lab

## Cài đặt thư viện (chạy 1 lần)

```bash
sudo apt update
sudo apt install -y python3-pip python3-dbus scrot dbus-x11
cd agent
pip3 install -r requirements.txt
python3 agent.py
```

## Yêu cầu
- Backend phải chạy TRƯỚC khi chạy Agent
- Sửa IP Backend trong agent.py dòng BACKEND_WS_URL nếu cần

## Các chức năng hỗ trợ

| Chức năng | Kali Linux | Ghi chú |
|-----------|-----------|---------|
| Chụp màn hình | ✅ | GNOME D-Bus (Wayland) / scrot / mss |
| Webcam | ✅ | Cần camera |
| Process list | ✅ | Tự động gửi mỗi 5s |
| Kill process | ✅ | |
| Shutdown | ✅ | systemctl poweroff -i |
| Restart | ✅ | systemctl reboot -i |
| File sandbox | ✅ | /home/kali/Downloads/ |
| Quản lý app | ✅ | Firefox, Wireshark, BurpSuite, Metasploit, nmap, John, Hydra, aircrack-ng, sqlmap, nikto, gobuster |
| Keylogger | ⚠️ | Cần màn hình desktop (X server) |

## Thứ tự chạy đúng:
```
Bước 1: Backend  → cd backend && uvicorn app.main:app --reload
Bước 2: Agent    → cd agent && python3 agent.py
Bước 3: Frontend → cd frontend && npm run dev
```
