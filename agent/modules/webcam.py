import cv2
import numpy as np
import subprocess
import threading
import time
import queue
import base64


def set_v4l2_mjpg():
    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", "/dev/video0", "-v", "width=640,height=480,pixelformat=MJPG,framerate=8/1"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, Exception):
        return False


def log_v4l2_info():
    try:
        r = subprocess.run(
            ["v4l2-ctl", "-d", "/dev/video0", "--list-formats-ext"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines()[:60]:
                if line.strip():
                    print(f"   {line}")
        r2 = subprocess.run(
            ["v4l2-ctl", "-d", "/dev/video0"],
            capture_output=True, text=True, timeout=5
        )
        if r2.returncode == 0:
            for line in r2.stdout.splitlines()[:40]:
                if line.strip():
                    print(f"   {line}")
    except Exception:
        pass


def try_ffmpeg_pipe():
    try:
        proc = subprocess.Popen(
            ["ffmpeg", "-f", "v4l2", "-i", "/dev/video0",
             "-vf", "scale=640:480", "-f", "image2pipe",
             "-vcodec", "mjpeg", "-q:v", "4", "pipe:1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
        )
        return proc
    except (FileNotFoundError, Exception):
        return False


def try_gstreamer_capture():
    try:
        pipeline = (
            "v4l2src device=/dev/video0 ! "
            "video/x-raw,format=YUY2,width=640,height=480,framerate=8/1 ! "
            "videoconvert ! video/x-raw,format=BGR ! "
            "appsink drop=true max-buffers=1"
        )
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            return cap
    except Exception:
        pass
    try:
        pipeline = (
            "v4l2src device=/dev/video0 ! "
            "image/jpeg,width=640,height=480,framerate=8/1 ! "
            "jpegdec ! videoconvert ! video/x-raw,format=BGR ! "
            "appsink drop=true max-buffers=1"
        )
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            return cap
    except Exception:
        pass
    return None


def try_opencv_backends():
    cap = None
    for backend_name, backend in [("V4L2", cv2.CAP_V4L2), ("FFMPEG", cv2.CAP_FFMPEG), ("default", 0)]:
        if cap:
            cap.release()
        cap = cv2.VideoCapture(0, backend)
        if cap.isOpened():
            return cap
        cap = None
    return None


def pick_bgr_permutation(frame):
    b, g, r = cv2.split(frame)
    means = [b.mean(), g.mean(), r.mean()]
    max_m, min_m = max(means), min(means)
    if min_m > 0 and max_m / min_m < 1.8:
        return frame, False
    perms = {
        'as_is': cv2.merge((b, g, r)),
        'swap_rb': cv2.merge((r, g, b)),
        'swap_gb': cv2.merge((g, b, r)),
        'swap_rg': cv2.merge((b, r, g)),
    }
    best = frame
    best_score = float('inf')
    chosen = False
    for name, candidate in perms.items():
        cb, cg, cr = cv2.split(candidate)
        vals = [cb.mean(), cg.mean(), cr.mean()]
        mx, mn = max(vals), min(vals)
        score = mx / mn if mn > 0 else float('inf')
        if score < best_score:
            best_score = score
            best = candidate
            chosen = True
    return best, chosen


def try_yuyv_from_3ch(frame):
    b, g, r = cv2.split(frame)
    if g.mean() > 20 and (b.mean() < 12 or r.mean() < 12):
        h, w = frame.shape[:2]
        try:
            for offset in range(3):
                raw = frame.tobytes()[offset:offset + h * w * 2]
                if len(raw) < h * w * 2:
                    continue
                arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 2)
                converted = cv2.cvtColor(arr, cv2.COLOR_YUV2BGR_YUY2)
                cb, cg, cr = cv2.split(converted)
                if cg.mean() > 15 and cb.mean() > 10 and cr.mean() > 10:
                    return converted
        except Exception:
            pass
    return None


def configure_camera_cap(cap):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 8)
    time.sleep(0.5)
    for _ in range(5):
        cap.read()
    time.sleep(0.2)
    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        cap.release()
        return None
    return test_frame


def ffmpeg_reader(proc, q):
    buf = b''
    try:
        while True:
            chunk = proc.stdout.read(65536)
            if not chunk:
                break
            buf += chunk
            while True:
                start = buf.find(b'\xff\xd8')
                if start == -1:
                    buf = buf[-1:]
                    break
                end = buf.find(b'\xff\xd9', start + 2)
                if end == -1:
                    break
                end += 2
                q.put(buf[start:end])
                buf = buf[end:]
    except Exception:
        pass
    finally:
        q.put(None)


def webcam_stream_worker(ws, send_queue, machine_name, stop_flag):
    """
    Main webcam streaming loop.
    
    Args:
        ws: WebSocketApp instance (unused, kept for compatibility)
        send_queue: queue.Queue to send frames
        machine_name: str, machine identifier
        stop_flag: list[bool], mutable container - set stop_flag[0] = False to stop
    """
    set_v4l2_mjpg()
    time.sleep(0.5)

    cap = None
    ffmpeg_proc = None
    use_ffmpeg = False
    frame_queue = None

    ffmpeg_proc = try_ffmpeg_pipe()
    if ffmpeg_proc is not None:
        use_ffmpeg = True
        frame_queue = queue.Queue(maxsize=5)
        reader = threading.Thread(target=ffmpeg_reader, args=(ffmpeg_proc, frame_queue), daemon=True)
        reader.start()
    else:
        cap = try_gstreamer_capture()
    if cap is None and not use_ffmpeg:
        cap = try_opencv_backends()

    if not cap and not use_ffmpeg:
        log_v4l2_info()
        stop_flag[0] = False
        return

    test_frame = None
    if use_ffmpeg:
        try:
            jpeg = frame_queue.get(timeout=8.0)
            if jpeg is None:
                raise ValueError("ffmpeg ended early")
            frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError("imdecode empty")
            test_frame = frame
        except Exception:
            if ffmpeg_proc:
                ffmpeg_proc.kill()
            use_ffmpeg = False
            ffmpeg_proc = None
            cap = try_gstreamer_capture()
            if cap is None:
                cap = try_opencv_backends()
            if not cap:
                log_v4l2_info()
                stop_flag[0] = False
                return
            test_frame = configure_camera_cap(cap)
            if test_frame is None:
                stop_flag[0] = False
                return
    else:
        test_frame = configure_camera_cap(cap)
        if test_frame is None:
            stop_flag[0] = False
            return

    fail_count = 0
    while stop_flag[0]:
        try:
            if use_ffmpeg:
                jpeg = frame_queue.get(timeout=10.0)
                if jpeg is None:
                    break
                frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    fail_count += 1
                    if fail_count >= 10:
                        break
                    time.sleep(0.2)
                    continue
            else:
                ret, frame = cap.read()
                if not ret:
                    fail_count += 1
                    if fail_count >= 10:
                        break
                    time.sleep(0.2)
                    continue

            fail_count = 0
            frame_resized = cv2.resize(frame, (640, 480))
            fixed = try_yuyv_from_3ch(frame_resized)
            if fixed is not None:
                rgb = cv2.cvtColor(fixed, cv2.COLOR_BGR2RGB)
            else:
                best, _ = pick_bgr_permutation(frame_resized)
                rgb = cv2.cvtColor(best, cv2.COLOR_BGR2RGB)
            _, buffer = cv2.imencode('.jpg', rgb, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if buffer is None or len(buffer) == 0:
                continue
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            payload = {
                "command": "agent_send_webcam",
                "machine_name": machine_name,
                "image_base64": img_base64
            }
            send_queue.put_nowait(payload)
        except queue.Empty:
            break
        except Exception:
            time.sleep(0.5)
        time.sleep(0.35)

    if cap:
        cap.release()
    if ffmpeg_proc:
        try:
            ffmpeg_proc.kill()
        except Exception:
            pass

    stop_flag[0] = False