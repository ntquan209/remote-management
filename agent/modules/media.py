import io
import os
import base64
import subprocess
import tempfile
from PIL import Image

def _encode(img):
    img = img.resize((960, 540), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=60)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def _try_gnome_screenshot():
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        subprocess.run(["gnome-screenshot", "-f", tmp_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            with Image.open(tmp_path) as img:
                return _encode(img)
        print("gnome-screenshot returned empty file")
    except FileNotFoundError:
        print("gnome-screenshot not installed")
    except Exception as e:
        print(f"gnome-screenshot error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass
    return None

def capture_screen_to_base64():
    tmp_path = None
    try:
        import dbus
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(tmp_fd)
        bus = dbus.SessionBus()
        screenshot_interface = bus.get_object("org.gnome.Shell.Screenshot", "/org/gnome/Shell/Screenshot")
        screenshot_method = screenshot_interface.get_dbus_method("Screenshot", "org.gnome.Shell.Screenshot")
        result = screenshot_method(False, False, tmp_path)
        if result and os.path.getsize(tmp_path) > 500:
            with Image.open(tmp_path) as img:
                return _encode(img)
        print("gnome dbus failed")
    except ImportError:
        print("dbus missing")
    except Exception as e:
        print(f"gnome dbus error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        subprocess.run(["gnome-screenshot", "-f", tmp_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            with Image.open(tmp_path) as img:
                return _encode(img)
        print("gnome-screenshot returned empty file")
    except FileNotFoundError:
        print("gnome-screenshot not installed")
    except Exception as e:
        print(f"gnome-screenshot error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass

    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(tmp_fd)
        result = subprocess.run(["scrot", "-z", "-o", tmp_path], capture_output=True, timeout=15)
        if result.returncode == 0 and os.path.getsize(tmp_path) > 500:
            with Image.open(tmp_path) as img:
                return _encode(img)
        err = result.stderr.decode() if result.stderr else f"rc={result.returncode}"
        print(f"scrot failed: {err}")
    except FileNotFoundError:
        print("scrot not installed")
    except Exception as e:
        print(f"scrot error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass

    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGBA", sct_img.size, sct_img.bgra)
            r, g, b, a = img.split()
            img = Image.merge("RGB", (b, g, r))
            return _encode(img)
    except Exception as e2:
        print(f"mss failed: {e2}")

    print("ERROR: screenshot failed")
    return None
