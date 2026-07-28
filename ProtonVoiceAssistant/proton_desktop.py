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

import subprocess
import json

# ── Speech engine (single dedicated thread) ──────────────────────────────────

_speech_queue  = queue.Queue()
_speech_ready  = threading.Event()

def _speech_worker():
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except ImportError:
        pass
    engine = None
    try:
        engine = pyttsx3.init()
        # Slightly slower, more natural voice
        engine.setProperty("rate", 165)
    except Exception as e:
        print(f"[Speech] Init error: {e}")
    _speech_ready.set()
    while True:
        text = _speech_queue.get()
        if text is None:
            break
        print(f"[Luttapi] Speaking: {text[:60]}")
        if engine:
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as ex:
                print(f"[Speech] Error: {ex}")
                try:
                    engine = pyttsx3.init()
                    engine.setProperty("rate", 165)
                except Exception:
                    pass
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

class OpenClawAgent:
    """Wrapper to run OpenClaw locally via CLI"""
    def run_query(self, command: str) -> str:
        try:
            print(f"[OpenClaw] Querying: {command}")
            # Run the embedded agent locally (no gateway required)
            result = subprocess.run(
                ["openclaw", "agent", "--message", command, "--local", "--json"],
                capture_output=True,
                text=True,
                timeout=45
            )
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    # The JSON structure of OpenClaw agent usually contains a 'text' or 'message' field
                    return data.get("text", data.get("message", "I finished the task with OpenClaw!"))
                except json.JSONDecodeError:
                    return result.stdout.strip()
            else:
                raise Exception(f"Exit code {result.returncode}: {result.stderr}")
        except Exception as e:
            print(f"[OpenClaw] Error: {e}")
            raise

class LuttapiApp:

    def __init__(self):
        self.overlay    = ProtonOverlay()
        self.llm        = LLMAgent()         # Original Python ReAct fallback
        self.openclaw   = OpenClawAgent()    # New OpenClaw backend
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
        self.overlay.show_text("Hey Adi! 👋", auto_hide_sec=3)
        speak("Hey Adi! How can I help you?")
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

        # Query LLM
        try:
            # Attempt to use OpenClaw first
            print("[Luttapi] Trying OpenClaw backend...")
            response = self.openclaw.run_query(command)
            if not response or "GatewayCredentialsRequiredError" in response:
                raise Exception("OpenClaw not fully configured, falling back to local Python agent.")
            print(f"[Luttapi] OpenClaw Response: {response[:100]}")
        except Exception as e:
            print(f"[Luttapi] OpenClaw failed, using local LLM agent: {e}")
            try:
                response = self.llm.run_query(command)
                print(f"[Luttapi] Python LLM Response: {response[:100]}")
            except Exception as e2:
                print(f"[Luttapi] Both LLM backends failed: {e2}")
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
