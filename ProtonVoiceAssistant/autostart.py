"""
autostart.py
Registers / removes Proton from Windows startup (HKCU registry key).
Run once to install; the assistant will then start on every boot.
"""
import sys
import os
import winreg

STARTUP_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME     = "ProtonAssistant"


def get_launch_command():
    """Build the command that Windows will run on startup."""
    python_exe = sys.executable
    # Resolve the path to proton_desktop.py relative to this file's location
    this_dir = os.path.dirname(os.path.abspath(__file__))
    script   = os.path.join(this_dir, "proton_desktop.py")
    # Use pythonw.exe (no console window) if available
    pythonw = python_exe.replace("python.exe", "pythonw.exe")
    if os.path.exists(pythonw):
        python_exe = pythonw
    return f'"{python_exe}" "{script}"'


def install():
    """Add Proton to Windows startup."""
    cmd = get_launch_command()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_KEY,
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        print(f"[Autostart] Proton will start on every Windows boot.")
        print(f"[Autostart] Command: {cmd}")
        return True
    except Exception as e:
        print(f"[Autostart ERROR] Could not write registry: {e}")
        return False


def uninstall():
    """Remove Proton from Windows startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_KEY,
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print("[Autostart] Proton removed from startup.")
        return True
    except FileNotFoundError:
        print("[Autostart] Entry not found (already removed or never installed).")
        return False
    except Exception as e:
        print(f"[Autostart ERROR] {e}")
        return False


def is_installed():
    """Check if the autostart entry exists."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_KEY,
            0, winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
