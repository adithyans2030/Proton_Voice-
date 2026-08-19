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
from jarvis_modules.llm_agent import LLMAgent

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


# ── Listen (one-shot, no wake word filtering) ─────────────────────────────────

def listen_once(timeout=7, phrase_limit=12) -> str:
    """Listen for a single utterance and return the text (lowercase)."""
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            print("[Luttapi] Listening for command...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        text = recognizer.recognize_google(audio).lower()
        print(f"[Luttapi] Heard: {text}")
        return text
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"[Luttapi] Listen error: {e}")
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

        # Start engine thread
        threading.Thread(
            target=self._startup, daemon=True, name="LuttapiEngine"
        ).start()

    # ── Startup ───────────────────────────────────────────────────────────────

    def _startup(self):
        time.sleep(0.6)  # let UI render first
        self.overlay.show_text("Loading Luttapi AI…", auto_hide_sec=999)
        self.overlay.set_state(STATE_THINKING)

        # Wait a moment for UI
        time.sleep(1.0)

        self.overlay.show_text("Say 'Hey buddy' to wake me!", auto_hide_sec=5)
        self.overlay.set_state(STATE_IDLE)

        # Start wake word detector
        self.wake_detector.start()
        print("[Luttapi] Ready. Say 'hey buddy' to activate.")

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
        try:
            self._wake_cycle()
        except Exception as e:
            print(f"[Luttapi] Wake cycle error: {e}")
            self.overlay.set_state(STATE_IDLE)
        finally:
            self._busy = False

    def _wake_cycle(self):
        """Full wake → listen → respond cycle."""
        # Greet
        self.overlay.set_state(STATE_SPEAKING)
        self.overlay.show_text("Hello buddy! 👋", auto_hide_sec=3)
        speak("Hello buddy!")
        time.sleep(0.3)

        # Listen for command
        self.overlay.set_state(STATE_LISTENING)
        self.overlay.show_text("Listening… 🎙", auto_hide_sec=8)
        command = listen_once(timeout=7, phrase_limit=12)

        if not command:
            self.overlay.show_text("Didn't catch that. Say 'Hey buddy' again!", auto_hide_sec=4)
            self.overlay.set_state(STATE_IDLE)
            speak("I didn't catch that. Please say hey buddy and try again.")
            return

        # Show what was heard
        self.overlay.show_text(f'"{command}"', auto_hide_sec=999)
        self.overlay.set_state(STATE_THINKING)
        print(f"[Luttapi] Processing: {command}")

        # Query Intent Model
        try:
            print("[Luttapi] Querying offline Intent Model...")
            response = self.llm.run_query(command)
            print(f"[Luttapi] Intent Response: {response[:100]}")
        except Exception as e:
            print(f"[Luttapi] LLM error: {e}")
            response = "Sorry Adi, I ran into an error. Please make sure Ollama is running."

        # Speak + show response
        self.overlay.show_text(response, auto_hide_sec=10)
        self.overlay.set_state(STATE_SPEAKING)
        speak(response)

        # Return to idle
        time.sleep(0.5)
        self.overlay.set_state(STATE_IDLE)

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

    app = LuttapiApp()
    app.run()
