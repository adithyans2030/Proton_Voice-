"""
JARVIS - Just A Rather Very Intelligent System
A comprehensive AI assistant inspired by Iron Man's Jarvis
"""
import speech_recognition as sr
import pyttsx3
import pywhatkit
import datetime
import wikipedia
import webbrowser
import os
import subprocess
import random
import requests
import ctypes
import asyncio
import threading
import psutil
import queue
from bleak import BleakScanner
import openai
import re
from intent_model import predict_intent
from jarvis_modules.llm_agent import LLMAgent

# Import Jarvis modules
from jarvis_modules import (
    EmailManager, CalendarManager, FileManager,
    SystemMonitor, ContextMemory
)

# Global state
paused = False
socketio = None
wake_word_detection = True
wake_words = ["hey jarvis", "hey proton", "jarvis", "proton", "boot up"]

# Desktop overlay callback hooks (set by proton_desktop.py)
status_callback   = None   # fn(text: str)  — called on status changes
command_callback  = None   # fn(text: str)  — called when a command is recognized
response_callback = None   # fn(text: str)  — called when a response is ready

def _emit(event: str, data: dict):
    """Unified emit that works with both socketio and desktop callbacks."""
    if socketio:
        socketio.emit(event, data)
    text = data.get("text", "")
    if event == "status" and status_callback:
        status_callback(text)
    elif event == "command_received" and command_callback:
        command_callback(text)
    elif event in ("response", "speaking") and response_callback:
        response_callback(text)

# Initialize OpenAI
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    openai.api_key = openai_key

# Initialize Jarvis modules
email_manager = EmailManager()
calendar_manager = CalendarManager()
file_manager = FileManager()
system_monitor = SystemMonitor()
context_memory = ContextMemory()
llm_agent = LLMAgent()

speech_queue = queue.Queue()

def speak_worker():
    """Dedicated background thread worker for pyttsx3 to prevent COM threading crashes"""
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except ImportError:
        pass
        
    engine = None
    try:
        engine = pyttsx3.init()
    except Exception as e:
        print(f"[Speech Worker Error] Failed to initialize pyttsx3: {e}")
        
    while True:
        try:
            text = speech_queue.get()
            if text is None:
                break
                
            print(f"[Jarvis Speaking]: {text}")
            _emit("speaking", {"text": text})
            _emit("response", {"text": text})
                
            if engine:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as ex:
                    print(f"[Speech Worker Error] Engine speaking failed: {ex}")
                    try:
                        engine = pyttsx3.init()
                    except Exception:
                        pass
            speech_queue.task_done()
        except Exception as e:
            print(f"[Speech Worker Exception] {e}")

speech_initialized = False
speech_worker_thread = None

def speak(text):
    """Thread-safe speak wrapper that pushes text to speech queue"""
    global speech_initialized, speech_worker_thread
    if not speech_initialized:
        speech_initialized = True
        speech_worker_thread = threading.Thread(target=speak_worker, daemon=True)
        speech_worker_thread.start()
    speech_queue.put(text)

def listen():
    """Enhanced listen function with wake word detection"""
    global paused
    if paused:
        return ""

    if socketio:
        socketio.emit("status", {"text": "Listening..."})

    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            try:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except Exception as e:
                print(f"[Warning] Could not adjust for ambient noise: {e}")
            
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                if socketio:
                    socketio.emit("status", {"text": "No speech detected"})
                return ""

        try:
            command = recognizer.recognize_google(audio).lower()
            print(f"You said: {command}")
            
            # Wake word detection
            if wake_word_detection:
                for wake_word in wake_words:
                    if wake_word in command:
                        command = command.replace(wake_word, "").strip()
                        if not command:
                            speak("Yes, how can I assist you?")
                            return ""
                        break
                else:
                    # No wake word detected, ignore
                    return ""
            
            if socketio:
                socketio.emit("command_received", {"text": command})
            return command
        except sr.UnknownValueError:
            if socketio:
                socketio.emit("no_response")
            return ""
        except sr.RequestError as e:
            error_msg = f"Speech recognition service error: {str(e)}"
            print(f"[Error] {error_msg}")
            if socketio:
                socketio.emit("error", {"text": error_msg})
            return ""
    except OSError as e:
        error_msg = f"Microphone not accessible: {str(e)}"
        print(f"[Error] {error_msg}")
        if socketio:
            socketio.emit("error", {"text": error_msg})
        return ""
    except Exception as e:
        error_msg = f"Unexpected error in listen: {str(e)}"
        print(f"[Error] {error_msg}")
        if socketio:
            socketio.emit("error", {"text": error_msg})
        return ""

def set_volume(change):
    """Set system volume"""
    try:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            current_volume = volume.GetMasterVolumeLevelScalar()
            new_volume = max(0.0, min(1.0, current_volume + (change/100)))
            volume.SetMasterVolumeLevelScalar(new_volume, None)
            
            volume_percent = int(new_volume * 100)
            if socketio:
                socketio.emit("volume_change", {"volume": volume_percent})
            speak(f"Volume set to {volume_percent}%")
            return
            
        except ImportError:
            pass
        
        if os.name == 'nt':
            if change > 0:
                for _ in range(abs(change)//2):
                    os.system(r'nircmd.exe changesysvolume 2000')
            else:
                for _ in range(abs(change)//2):
                    os.system(r'nircmd.exe changesysvolume -2000')
            
            current_vol = 50 + change
            current_vol = max(0, min(100, current_vol))
            
            if socketio:
                socketio.emit("volume_change", {"volume": current_vol})
            speak(f"Volume adjusted to {current_vol}%")
        else:
            speak("Volume control not implemented for this operating system")
            
    except Exception as e:
        print(f"[Volume Control Error] {str(e)}")
        speak("Failed to adjust volume")

def get_battery_status():
    """Get battery status"""
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            speak("No battery detected")
            return
        
        percent = battery.percent
        plugged = battery.power_plugged
        status = "plugged in" if plugged else "not plugged in"
        
        if percent < 20 and not plugged:
            status_message = f"Warning! Battery is critically low at {percent}% and {status}"
        else:
            status_message = f"Battery is at {percent}% and {status}"
        
        speak(status_message)
        
    except Exception as e:
        speak("Could not get battery status")
        print(f"[Battery Error] {e}")

def get_weather(city="Bangalore"):
    """Get weather information"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        speak("The weather API key is not configured.")
        return
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=10).json()
        if response["cod"] != "404":
            weather_desc = response["weather"][0]["description"]
            temp = response["main"]["temp"]
            speak(f"The current temperature in {city} is {temp} degrees Celsius with {weather_desc}.")
        else:
            speak("Sorry, I couldn't fetch the weather details.")
    except Exception as e:
        speak("Failed to get weather information")
        print(f"[Weather Error] {e}")

def change_wallpaper():
    """Change desktop wallpaper"""
    wallpapers = [
        r"C:\Users\adith\Downloads\one_piece_wallpaper1.jpg",
        r"C:\Users\adith\Downloads\c1c4e3c7-026e-439d-bb63-32c74ee57a86.jfif",
        r"C:\Users\adith\Downloads\820950fc-ee4c-423f-8c68-c992eaa6a33c.jfif",
        r"C:\Users\adith\Downloads\ode_4k_wallpaper_by_thesyanart_derf1y7-fullview.jpg",
    ]
    try:
        wallpaper_path = random.choice(wallpapers)
        ctypes.windll.user32.SystemParametersInfoW(20, 0, wallpaper_path, 0)
        speak("Wallpaper has been changed successfully.")
    except Exception as e:
        speak("Failed to change wallpaper")
        print(f"[Wallpaper Error] {e}")

async def detect_bluetooth():
    """Detect Bluetooth devices"""
    print("Scanning for Bluetooth devices...")
    devices = await BleakScanner.discover()
    if devices:
        print(f"Found {len(devices)} devices nearby.")
        for device in devices:
            print(f"Device: {device.name} - {device.address}")
        speak(f"Found {len(devices)} Bluetooth devices nearby.")
    else:
        print("No Bluetooth devices found.")
        speak("No Bluetooth devices found.")

def run_bluetooth_scan():
    """Run Bluetooth scan in async context"""
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(detect_bluetooth())

def enable_bluetooth():
    """Enable Bluetooth"""
    try:
        result = subprocess.run(["powershell", "-Command", "(Get-Service bthserv).Status"],
                              capture_output=True, text=True)
        if "Stopped" in result.stdout:
            subprocess.run(["powershell", "-Command", "Start-Service bthserv"], capture_output=True)
            speak("Bluetooth is now enabled.")
        else:
            speak("Bluetooth is already ON.")
    except Exception as e:
        speak("Failed to enable Bluetooth.")
        print(f"[ERROR] {e}")

def disable_bluetooth():
    """Disable Bluetooth"""
    try:
        subprocess.run(["powershell", "-Command", "Stop-Service bthserv"], capture_output=True)
        speak("Bluetooth is now disabled.")
    except Exception as e:
        speak("Failed to disable Bluetooth.")
        print(f"[ERROR] {e}")

def extract_parameters(command, patterns):
    """Extract parameters from command using regex patterns"""
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    return None

def execute_command(command):
    """Main command execution function routed through local LLM agent"""
    global paused
    if not command:
        return

    # Handle pause/resume
    if "pause assistant" in command or "pause jarvis" in command:
        paused = True
        speak("Assistant paused. Say 'Resume assistant' to continue.")
        return
    elif "resume assistant" in command or "resume jarvis" in command:
        paused = False
        speak("Assistant resumed. How can I assist you?")
        return

    try:
        response = llm_agent.run_query(command, socketio=socketio)
        speak(response)
    except Exception as e:
        error_msg = f"Failed to process query: {str(e)}"
        print(f"[Error] {error_msg}")
        speak("I encountered an error while processing your request.")


def main_loop():
    """Main assistant loop"""
    while True:
        command = listen()
        if command:
            execute_command(command)

def start_assistant():
    """Start the assistant with wake word detection"""
    if wake_word_detection:
        speak("JARVIS online. Say 'Hey Jarvis' or 'Hey Proton' to activate.")
    else:
        speak("JARVIS online. How can I assist you?")
    wake_up_assistant()

def wake_up_assistant():
    """Wake word detection loop"""
    while True:
        command = listen()
        if command:
            if wake_word_detection:
                # Already processed wake word in listen()
                main_loop()
            else:
                main_loop()
