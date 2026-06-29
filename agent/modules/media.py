import io
import os
import base64
import subprocess
import tempfile
from PIL import Image


def _cleanup_temp(tmp_path):
    if tmp_path and os.path.exists(tmp_path):
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _encode(img):
    img = img.resize((960, 540), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=60)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _try_gnome_dbus(tmp_path):
    import dbus
    bus = dbus.SessionBus()
    obj = bus.get_object("org.gnome.Shell.Screenshot", "/org/gnome/Shell/Screenshot")
    method = obj.get_dbus_method("Screenshot", "org.gnome.Shell.Screenshot")
    result = method(False, False, tmp_path)
    if result and os.path.getsize(tmp_path) > 500:
        with Image.open(tmp_path) as img:
            return _encode(img)
    return None


def _try_gnome_cli(tmp_path):
    subprocess.run(
        ["gnome-screenshot", "-f", tmp_path],
        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
        with Image.open(tmp_path) as img:
            return _encode(img)
    return None


def _try_scrot(tmp_path):
    result = subprocess.run(
        ["scrot", "-z", "-o", tmp_path],
        capture_output=True, timeout=15
    )
    if result.returncode == 0 and os.path.getsize(tmp_path) > 500:
        with Image.open(tmp_path) as img:
            return _encode(img)
    return None


def _try_mss():
    import mss
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGBA", sct_img.size, sct_img.bgra)
        r, g, b, a = img.split()
        img = Image.merge("RGB", (b, g, r))
        return _encode(img)


def capture_screen_to_base64():
    # Method 1: GNOME DBus API (fastest)
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        result = _try_gnome_dbus(tmp_path)
        if result:
            return result
    except ImportError:
        pass
    except Exception:
        pass
    finally:
        _cleanup_temp(tmp_path)

    # Method 2: gnome-screenshot CLI
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        result = _try_gnome_cli(tmp_path)
        if result:
            return result
    except FileNotFoundError:
        pass
    except Exception:
        pass
    finally:
        _cleanup_temp(tmp_path)

    # Method 3: scrot CLI
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        result = _try_scrot(tmp_path)
        if result:
            return result
    except FileNotFoundError:
        pass
    except Exception:
        pass
    finally:
        _cleanup_temp(tmp_path)

    # Method 4: mss (python library)
    try:
        return _try_mss()
    except Exception:
        pass

    return None