import subprocess
import os

KALI_APPS = {
    "firefox": {"start": "firefox", "stop": "pkill -9 -f firefox"},
    "terminator": {"start": "terminator", "stop": "pkill -9 -x terminator"},
    "nmap": {"start": "xfce4-terminal -e nmap", "stop": "pkill -9 -x nmap"},
    "wireshark": {"start": "wireshark", "stop": "pkill -9 -x wireshark"},
    "burpsuite": {"start": "burpsuite", "stop": "pkill -9 -f burpsuite"},
    "metasploit": {"start": "msfconsole", "stop": "pkill -9 -x msfconsole"},
    "john": {"start": "xfce4-terminal -e john", "stop": "pkill -9 -x john"},
    "hydra": {"start": "xfce4-terminal -e hydra", "stop": "pkill -9 -x hydra"},
    "aircrack-ng": {"start": "airodump-ng", "stop": "pkill -9 -x airodump-ng"},
    "sqlmap": {"start": "xfce4-terminal -e sqlmap", "stop": "pkill -9 -x sqlmap"},
    "nikto": {"start": "xfce4-terminal -e nikto", "stop": "pkill -9 -x nikto"},
    "gobuster": {"start": "xfce4-terminal -e gobuster", "stop": "pkill -9 -x gobuster"},
    "gedit": {"start": "gedit", "stop": "pkill -9 -x gedit"},
    "thunar": {"start": "thunar", "stop": "thunar -q; pkill -9 -x thunar"},
}

def get_available_apps():
    return KALI_APPS

def manage_application(action, app_name):
    apps = get_available_apps()
    if app_name not in apps:
        return False
    app_config = apps[app_name]
    try:
        if action == "START":
            subprocess.Popen("{} > /dev/null 2>&1 &".format(app_config["start"]), shell=True)
            return True
        elif action == "STOP":
            subprocess.Popen("{} > /dev/null 2>&1".format(app_config["stop"]), shell=True)
            return True
    except Exception:
        pass
    return False