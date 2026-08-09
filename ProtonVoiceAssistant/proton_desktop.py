"""
proton_desktop.py  —  Luttapi Voice Assistant (Native Desktop Mode)
=====================================================================
No browser needed. Animated robot mascot lives on your desktop.

Flow:
  [Boot] -> Luttapi loads silently -> robot appears bottom-right
  ["Hey Buddy"] -> "Hey Adi! How can I help?" -> listens for command
  [Command] -> Llama AI thinks -> Luttapi speaks + shows bubble

Usage:
    python proton_desktop.py
    pythonw proton_desktop.py     (no console, silent background)
"""

import sys
import os
import threading
import time
import speech_recognition as sr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui.overlay import (
    ProtonOverlay,
    STATE_IDLE, STATE_LISTENING, STATE_THINKING,
    STATE_SPEAKING, STATE_SLEEPING,
)
from jarvis_modules.wakeword_detector import WakeWordDetector
from jarvis_modules.clap_detector import ClapDetector
from jarvis_modules.llm_agent import LLMAgent
import keyboard

import pyttsx3
import queue
import asyncio
import tempfile

# ── Voice configuration ──────────────────────────────────────────────────────
# edge-tts voices: en-US-GuyNeural (calm male), en-US-AriaNeural (female)
# en-GB-RyanNeural (British male — closest to JARVIS)
EDGE_VOICE = "en-GB-RyanNeural"

# ── Speech engine (single dedicated thread) ──────────────────────────────────

_speech_queue  = queue.Queue()
_speech_ready  = threading.Event()

def _speak_edge(text: str) -> bool:
    """Speak using edge-tts neural voice. Returns True if successful."""
    try:
        import edge_tts
        import pygame

        async def _generate():
            communicate = edge_tts.Communicate(text, EDGE_VOICE)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                path = f.name
            await communicate.save(path)
            return path

        path = asyncio.run(_generate())

        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
        os.remove(path)
        return True
    except Exception as e:
        print(f"[Speech] edge-tts error: {e}")
        return False

_pyttsx_engine = None

def _speak_pyttsx(text: str):
    """Fallback: pyttsx3 (built-in Windows voice)."""
    global _pyttsx_engine
    try:
        if _pyttsx_engine is None:
            _pyttsx_engine = pyttsx3.init()
            _pyttsx_engine.setProperty("rate", 165)
        _pyttsx_engine.say(text)
        _pyttsx_engine.runAndWait()
    except Exception as e:
        print(f"[Speech] pyttsx3 error: {e}")
        try:
            _pyttsx_engine = pyttsx3.init()
            _pyttsx_engine.setProperty("rate", 165)
        except Exception:
            pass

def _speech_worker():
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except ImportError:
        pass
    _speech_ready.set()
    while True:
        text = _speech_queue.get()
        if text is None:
            break
        print(f"[Luttapi] Speaking: {text[:60]}")
        # Try neural voice first; fall back to system TTS
        if not _speak_edge(text):
            _speak_pyttsx(text)
        _speech_queue.task_done()

threading.Thread(target=_speech_worker, daemon=True, name="SpeechWorker").start()
_speech_ready.wait(timeout=5)

def speak(text: str):
    _speech_queue.put(text)


# ── Listen (one-shot, Whisper AI offline) ───────────────────────────────────

def listen_once(timeout=7, phrase_limit=12) -> str:
    """Listen for a single utterance and return the text (lowercase) using offline Whisper."""
    recognizer = sr.Recognizer()
    
    # Retry opening microphone if it is temporarily locked by background threads
    for attempt in range(5):
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                print("[Luttapi] Listening for command (Whisper)...")
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            
            # Use local whisper model ("base.en" is ~140MB and fast)
            text = recognizer.recognize_whisper(audio, model="base.en").lower()
            print(f"[Luttapi] Heard: {text}")
            return text
            
        except (OSError, IOError) as e:
            if attempt < 4:
                time.sleep(0.3)
                continue
            print(f"[Luttapi] Microphone lock error: {e}")
            return ""
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            print(f"[Luttapi] Listen error (Whisper): {e}")
            return ""
    
    return ""


# ── Main App ──────────────────────────────────────────────────────────────────

class LuttapiApp:

    def __init__(self):
        self.overlay    = ProtonOverlay()
        self.llm        = LLMAgent()
        self._paused    = False
        self._running   = True
        self._busy      = False   # prevent overlapping wake cycles

        # Wire overlay menu
        self.overlay.pause_callback  = self._pause
        self.overlay.resume_callback = self._resume
        self.overlay.exit_callback   = self._exit

        # Wake word detector → triggers _on_wake()
        self.wake_detector = WakeWordDetector(on_wake_word=self._on_wake_safe, wake_word="hey buddy")
        
        # Double-clap detector
        self.clap_detector = ClapDetector(on_double_clap=self._on_wake_safe)

        # Global Hotkey (Ninja Mode)
        try:
            keyboard.add_hotkey('ctrl+shift+space', self._on_wake_safe)
            print("[Luttapi] Ninja Mode hotkey registered: Ctrl+Shift+Space")
        except Exception as e:
            print(f"[Luttapi] Failed to register global hotkey: {e}")

        # Start engine threads
        threading.Thread(
            target=self._startup, daemon=True, name="LuttapiEngine"
        ).start()
        
        # Start morning briefing thread
        threading.Thread(
            target=self._morning_briefing_loop, daemon=True, name="MorningBriefing"
        ).start()

    # ── Startup ───────────────────────────────────────────────────────────────

    def _startup(self):
        time.sleep(0.6)  # let UI render first
        self.overlay.show_text("Loading Luttapi AI…", auto_hide_sec=999)
        self.overlay.set_state(STATE_THINKING)

        # Test LLM connectivity
        print("[Luttapi] Testing Ollama connection...")
        test = self.llm._call_ollama([
            {"role": "user", "content": "Reply with just: ready"}
        ])
        if "Error" in test or "error" in test:
            print(f"[Luttapi] Ollama warning: {test}")
            self.overlay.show_text(
                "⚠ Ollama not responding.\nMake sure 'ollama serve' is running.",
                auto_hide_sec=8
            )
            self.overlay.set_state(STATE_IDLE)
            time.sleep(5)

        self.overlay.show_text("Say 'Hey buddy' to wake me!", auto_hide_sec=5)
        self.overlay.set_state(STATE_IDLE)

        # Start wake detectors
        self.wake_detector.start()
        # self.clap_detector.start()  # Disabled due to PyAudio threading segfault with wake_detector
        print("[Luttapi] Ready. Say 'hey buddy', double-clap, or press Ctrl+Shift+Space to activate.")

    # ── Wake cycle ────────────────────────────────────────────────────────────

    def _on_wake_safe(self):
        """Thread-safe wrapper — prevents overlapping wake cycles."""
        if self._paused or self._busy:
            return
        threading.Thread(target=self._on_wake, daemon=True, name="WakeCycle").start()

    def _on_wake(self):
        if self._busy or self._paused:
            return
        self._busy = True
        self.wake_detector.pause()
        self.clap_detector.pause()
        try:
            self._wake_cycle()
        except Exception as e:
            print(f"[Luttapi] Wake cycle error: {e}")
            self.overlay.set_state(STATE_IDLE)
        finally:
            self.wake_detector.resume()
            self.clap_detector.resume()
            self._busy = False

    def _wake_cycle(self):
        """Full wake → listen → respond cycle with continuous conversation loop."""
        # Greet
        self.overlay.set_state(STATE_SPEAKING)
        self.overlay.show_text("Hello sir! 👋", auto_hide_sec=3)
        speak("Hello sir!")
        time.sleep(0.3)

        consecutive_silence = 0

        while True:
            # Listen for command
            self.overlay.set_state(STATE_LISTENING)
            self.overlay.show_text("Listening… 🎙", auto_hide_sec=8)
            
            # Use shorter timeout for follow-ups
            command = listen_once(timeout=6, phrase_limit=15)

            if not command:
                consecutive_silence += 1
                if consecutive_silence >= 1:
                    # After silence, go back to sleep
                    self.overlay.show_text("Going to sleep.", auto_hide_sec=3)
                    self.overlay.set_state(STATE_IDLE)
                    speak("Standing by.")
                    break
                continue

            consecutive_silence = 0

            # Show what was heard
            self.overlay.show_text(f'"{command}"', auto_hide_sec=999)
            self.overlay.set_state(STATE_THINKING)
            print(f"[Luttapi] Processing: {command}")

            # Query LLM
            try:
                print("[Luttapi] Querying local Ollama LLM...")
                response = self.llm.run_query(command)
                print(f"[Luttapi] Python LLM Response: {response[:100]}")
            except Exception as e:
                print(f"[Luttapi] LLM error: {e}")
                response = "Sorry sir, I ran into an error."

            # Speak + show response
            self.overlay.show_text(response, auto_hide_sec=10)
            self.overlay.set_state(STATE_SPEAKING)
            speak(response)

            # Wait for speech to roughly finish before listening again
            # We add a slight delay based on word count to prevent him listening to himself
            words = len(response.split())
            time.sleep(max(1.0, words * 0.3))
            
            # Loop restarts to listen for follow-up questions
            
    def _morning_briefing_loop(self):
        """Automatically triggers the morning briefing at 8:00 AM once a day."""
        has_run_today = False
        last_run_day = -1
        
        while self._running:
            now = time.localtime()
            
            # Reset the daily flag at midnight
            if now.tm_yday != last_run_day and now.tm_hour < 8:
                has_run_today = False
                
            if now.tm_hour == 8 and now.tm_min == 0 and not has_run_today:
                if not self._paused and not self._busy:
                    print("[Luttapi] Triggering morning briefing automation!")
                    has_run_today = True
                    last_run_day = now.tm_yday
                    
                    self._busy = True
                    try:
                        self.overlay.set_state(STATE_THINKING)
                        self.overlay.show_text("Preparing Morning Briefing...", auto_hide_sec=999)
                        speak("Good morning sir. Preparing your briefing.")
                        response = self.llm.run_query("It is exactly 8 AM. Give me my morning briefing: check the time, system status, and any calendar events for today, then summarize my day.")
                        self.overlay.set_state(STATE_SPEAKING)
                        self.overlay.show_text(response, auto_hide_sec=15)
                        speak(response)
                    except Exception as e:
                        print(f"Morning briefing error: {e}")
                    finally:
                        self.overlay.set_state(STATE_IDLE)
                        self._busy = False
                        
            time.sleep(45)

    # ── Menu callbacks ────────────────────────────────────────────────────────

    def _pause(self):
        self._paused = True
        self.overlay.show_text("Luttapi paused.\nRight-click → Resume.", auto_hide_sec=999)
        self.overlay.set_state(STATE_SLEEPING)

    def _resume(self):
        self._paused = False
        self.overlay.show_text("Say 'Hey buddy' to wake me!", auto_hide_sec=4)
        self.overlay.set_state(STATE_IDLE)

    def _exit(self):
        self._running = False
        self.wake_detector.stop()
        self.clap_detector.stop()
        _speech_queue.put(None)
        self.overlay.stop()

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        self.overlay.run()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Register autostart on first run
    try:
        from autostart import install, is_installed
        if not is_installed():
            print("[Autostart] Registering Windows startup entry...")
            install()
    except Exception as e:
        print(f"[Autostart] {e}")

    try:
        app = LuttapiApp()
        app.run()
    except Exception as e:
        import traceback
        with open("crash.txt", "w") as f:
            traceback.print_exc(file=f)
