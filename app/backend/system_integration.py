import os
import sys
import winreg
import subprocess
import urllib.request
import webbrowser
import threading
import time

def check_startup_registration(script_dir=None):
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        if script_dir is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bat_path = os.path.join(script_dir, 'dynamic-token.bat')
        if not os.path.exists(bat_path):
            bat_path = os.path.expandvars(r"%USERPROFILE%\dynamic-token\dynamic-token.bat")

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            try:
                val, _ = winreg.QueryValueEx(key, 'DynamicTokenHUD')
                if val != f'"{bat_path}"':
                    winreg.SetValueEx(key, 'DynamicTokenHUD', 0, winreg.REG_SZ, f'"{bat_path}"')
            except FileNotFoundError:
                winreg.SetValueEx(key, 'DynamicTokenHUD', 0, winreg.REG_SZ, f'"{bat_path}"')
    except Exception:
        pass

def check_9router_health():
    try:
        req = urllib.request.Request('http://127.0.0.1:20128', headers={'User-Agent': 'DynamicTokenHUD/1.0'})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status in (200, 301, 302, 401, 403)
    except Exception:
        return False

def run_9router():
    already_up = check_9router_health()
    if not already_up:
        cmd = os.path.expandvars(r"%APPDATA%\npm\9router.cmd")
        if not os.path.exists(cmd):
            cmd = "9router"
        try:
            creationflags = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
            subprocess.Popen([cmd, "--no-browser"], creationflags=creationflags, shell=False)
        except Exception:
            try:
                subprocess.Popen(f'start /b "" "{cmd}" --no-browser', shell=True)
            except Exception:
                pass

    def _open_web():
        for _ in range(12):
            if check_9router_health():
                break
            time.sleep(0.5)
        webbrowser.open('http://127.0.0.1:20128')

    threading.Thread(target=_open_web, daemon=True).start()
