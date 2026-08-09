"""
Jarvis System Control Module
Handles hardware control, power states, and application management.
"""
import os
import subprocess
import time

class SystemControlManager:
    def __init__(self):
        pass

    def adjust_brightness(self, level):
        """Set screen brightness (0-100)"""
        try:
            import screen_brightness_control as sbc
            level = max(0, min(100, int(level)))
            sbc.set_brightness(level)
            return f"Screen brightness set to {level}%."
        except ImportError:
            return "Error: screen-brightness-control library not installed."
        except Exception as e:
            return f"Error adjusting brightness: {str(e)}"

    def toggle_wifi(self, state):
        """Enable or disable Wi-Fi on Windows"""
        try:
            action = "enable" if state.lower() == "on" else "disable"
            # Using netsh to find Wi-Fi interface and toggle it
            cmd = f'netsh interface set interface "Wi-Fi" admin={action}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Wi-Fi has been turned {state}."
            else:
                return f"Failed to turn {state} Wi-Fi. Note: This usually requires Administrator privileges."
        except Exception as e:
            return f"Error toggling Wi-Fi: {str(e)}"

    def power_action(self, action):
        """Execute system power commands"""
        action = action.lower()
        try:
            if action == "lock":
                os.system("rundll32.exe user32.dll,LockWorkStation")
                return "Workstation locked."
            elif action == "sleep":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                return "System going to sleep."
            elif action == "shutdown":
                os.system("shutdown /s /t 0")
                return "System shutting down."
            elif action == "restart":
                os.system("shutdown /r /t 0")
                return "System restarting."
            else:
                return f"Error: Unknown power action '{action}'."
        except Exception as e:
            return f"Error executing power action '{action}': {str(e)}"

    def take_screenshot(self, filename="screenshot.png"):
        """Take a screenshot and save it"""
        try:
            import pyautogui
            import os
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if not filename.endswith(".png"):
                filename += ".png"
            filepath = os.path.join(desktop, filename)
            pyautogui.screenshot(filepath)
            return f"Screenshot saved to your Desktop as {filename}."
        except Exception as e:
            return f"Error taking screenshot: {str(e)}"

    def close_application(self, app_name):
        """Force close an application by name"""
        try:
            if not app_name.endswith(".exe"):
                app_name += ".exe"
            cmd = f'taskkill /F /IM {app_name} /T'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Successfully closed {app_name}."
            else:
                return f"Could not close {app_name}. It might not be running, or I lack permission."
        except Exception as e:
            return f"Error closing application '{app_name}': {str(e)}"
