path = r'd:\Data\Project\remote-lab-project\agent\agent.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ [WEBCAM] Không thể mở thiết bị ghi hình (Webcam)")
            webcam_streaming = False
            return

    # Ep dinh dang MJPEG de tranh select() timeout
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    time.sleep(0.5)

    # Warmup
    for _ in range(5):
        cap.grab()

    fail_count = 0
    while webcam_streaming:
        try:
            ret, frame = cap.read()
            if not ret:
                fail_count += 1
                print(f"⚠️ [WEBCAM] Không đọc được frame (lần {fail_count})")
                if fail_count >= 10:
                    print("❌ [WEBCAM] Quá nhiều lần lỗi, dừng luồng")
                    break
                time.sleep(0.1)
                continue

            fail_count = 0
            frame_resized = cv2.resize(frame, (640, 480))
            _, buffer = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            payload = {
                "command": "agent_send_webcam",
                "machine_name": MACHINE_NAME,
                "image_base64": img_base64
            }
            enqueue_send(payload)
        except Exception as e:
            print(f"❌ Lỗi truyền gói tin camera: {e}")
            time.sleep(0.5)
        time.sleep(0.25)'''

new = '''    cap = cv2.VideoCapture(0)  # Chi dung FFMPEG backend, khong dung V4L2
    if not cap.isOpened():
        print("❌ [WEBCAM] Không thể mở thiết bị ghi hình (Webcam)")
        webcam_streaming = False
        return

    # Giam FPS va chat luong de tranh JPEG corrupt tren VM
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 8)
    time.sleep(2.0)  # Cho camera on dinh hon

    fail_count = 0
    while webcam_streaming:
        try:
            ret, frame = cap.read()
            if not ret:
                fail_count += 1
                print(f"⚠️ [WEBCAM] Không đọc được frame (lần {fail_count})")
                if fail_count >= 10:
                    print("❌ [WEBCAM] Quá nhiều lần lỗi, dừng luồng")
                    break
                time.sleep(0.2)
                continue

            fail_count = 0
            frame_resized = cv2.resize(frame, (640, 480))
            # Giam chat luong JPEG de giam data va tranh corrupt
            _, buffer = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 35])
            if not buffer:
                print("⚠️ [WEBCAM] JPEG encode that bai")
                continue
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            payload = {
                "command": "agent_send_webcam",
                "machine_name": MACHINE_NAME,
                "image_base64": img_base64
            }
            enqueue_send(payload)
        except Exception as e:
            print(f"❌ Lỗi truyền gói tin camera: {e}")
            time.sleep(0.5)
        time.sleep(0.35)  # ~2.8 FPS, cham hon de giam buffering'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: webcam_stream_worker updated")
else:
    print("FAIL: old text not found")
    import re
    m = re.search(r'def webcam_stream_worker.*?cap\.release\(\)', content, re.DOTALL)
    if m:
        print("Found but text mismatch:")
        print(repr(m.group()[:200]))
