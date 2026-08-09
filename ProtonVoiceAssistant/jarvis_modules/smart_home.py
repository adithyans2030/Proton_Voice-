import requests

class SmartHomeManager:
    """
    Template for controlling smart home devices (lights, plugs, etc.).
    Because brands differ wildly (Hue, Tuya, Kasa, etc.), the easiest 
    way to connect is usually via IFTTT webhooks or local API calls.
    
    Replace the WEBHOOK_URLS below with your actual endpoints.
    """
    
    def __init__(self):
        # Example configuration map
        self.devices = {
            "bedroom_light": {
                "on": "https://maker.ifttt.com/trigger/bedroom_light_on/with/key/YOUR_KEY_HERE",
                "off": "https://maker.ifttt.com/trigger/bedroom_light_off/with/key/YOUR_KEY_HERE"
            },
            "desk_lamp": {
                "on": "http://192.168.1.100/api/turn_on",  # Example local IP trigger
                "off": "http://192.168.1.100/api/turn_off"
            }
        }

    def toggle_device(self, device_name, state):
        """
        device_name: e.g., 'bedroom_light'
        state: 'on' or 'off'
        """
        device_name = device_name.lower().replace(" ", "_")
        state = state.lower()
        
        if device_name not in self.devices:
            return f"Error: Device '{device_name}' not configured in smart_home.py."
            
        if state not in ["on", "off"]:
            return f"Error: Invalid state '{state}'. Must be 'on' or 'off'."
            
        url = self.devices[device_name][state]
        
        # If the user hasn't configured it yet, just return a mock success message
        if "YOUR_KEY_HERE" in url or "192.168.1.100" in url:
            return f"[Simulated] I would have turned {state} the {device_name} here. (Please configure webhook in smart_home.py)"
            
        try:
            # Fire the webhook/API call
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return f"Successfully turned {state} the {device_name}."
            else:
                return f"Failed to turn {state} {device_name}. Status code: {res.status_code}"
        except Exception as e:
            return f"Error contacting device '{device_name}': {str(e)}"
