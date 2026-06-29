import os
import psutil

def get_process_list():
    process_list = []
    try:
        for proc in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]),
                           key=lambda p: p.info["cpu_percent"] or 0, reverse=True)[:15]:
            ram_mb = round(proc.info["memory_info"].rss / (1024 * 1024), 1)
            process_list.append({
                "pid": proc.info["pid"],
                "name": proc.info["name"],
                "cpu": f"{proc.info['cpu_percent'] or 0.0}%",
                "ram": f"{ram_mb} MB"
            })
    except Exception:
        pass
    return process_list

def kill_process_by_pid(pid):
    try:
        p = psutil.Process(pid)
        p.terminate()
        return True
    except Exception:
        return False

def execute_power_cmd(action):
    try:
        if action == "SHUTDOWN":
            os.system("systemctl poweroff -i")
        elif action == "RESTART":
            os.system("systemctl reboot -i")
    except Exception:
        pass