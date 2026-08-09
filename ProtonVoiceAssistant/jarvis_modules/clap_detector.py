"""
clap_detector.py
Detects two sharp claps within a time window using PyAudio.
Runs in a background daemon thread and fires a callback when double-clap is detected.
"""
import threading
import time
import math

# Thresholds
CLAP_THRESHOLD   = 0.35   # RMS amplitude to count as a clap (0-1 scale)
MIN_GAP_SEC      = 0.15   # minimum gap between two claps (avoid single clap echo)
MAX_GAP_SEC      = 1.4    # maximum gap between two claps
CHUNK            = 1024
RATE             = 16000
CHANNELS         = 1
SILENCE_FRAMES   = 3      # frames below threshold to consider clap ended


class ClapDetector:
    """
    Listens to the microphone in a background thread.
    Calls `on_double_clap()` when two claps are detected within MAX_GAP_SEC.
    """

    def __init__(self, on_double_clap, sensitivity=CLAP_THRESHOLD):
        self._callback   = on_double_clap
        self._threshold  = sensitivity
        self._running    = False
        self._paused     = False
        self._thread     = None
        self._last_clap  = 0.0
        self._clap_count = 0

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[ClapDetector] Started. Double-clap to wake Luttapi.")

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def _listen_loop(self):
        try:
            import pyaudio
            import struct

            pa     = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )

            below_count = 0
            in_clap     = False

            while self._running:
                if self._paused:
                    time.sleep(0.5)
                    continue

                try:
                    data  = stream.read(CHUNK, exception_on_overflow=False)
                    # Compute RMS
                    count = len(data) // 2
                    fmt   = f"{count}h"
                    shorts = struct.unpack(fmt, data)
                    rms   = math.sqrt(sum(s * s for s in shorts) / count) / 32768.0

                    now = time.time()

                    if rms > self._threshold:
                        if not in_clap:
                            in_clap     = True
                            below_count = 0
                            self._on_clap_start(now)
                    else:
                        if in_clap:
                            below_count += 1
                            if below_count >= SILENCE_FRAMES:
                                in_clap     = False
                                below_count = 0

                except Exception as e:
                    print(f"[ClapDetector] Stream read error: {e}")
                    time.sleep(0.05)

            stream.stop_stream()
            stream.close()
            pa.terminate()

        except ImportError:
            print("[ClapDetector] PyAudio not available. Falling back to voice wake word.")
            self._fallback_loop()
        except Exception as e:
            print(f"[ClapDetector] Fatal error: {e}. Falling back to voice wake word.")
            self._fallback_loop()

    def _on_clap_start(self, now):
        gap = now - self._last_clap
        if gap > MIN_GAP_SEC:
            if gap <= MAX_GAP_SEC and self._clap_count >= 1:
                # Second clap within window — fire!
                print("[ClapDetector] Double clap detected! 👏👏")
                self._clap_count = 0
                self._last_clap  = 0.0
                try:
                    self._callback()
                except Exception as e:
                    print(f"[ClapDetector] Callback error: {e}")
            else:
                # First clap (or reset)
                self._clap_count = 1
                self._last_clap  = now
        # If gap <= MIN_GAP_SEC, ignore (echo/noise)

    def _fallback_loop(self):
        """
        If PyAudio fails, fall back to voice wake-word detection so
        the assistant still works.
        """
        import speech_recognition as sr
        r = sr.Recognizer()
        wake_words = ["hey luttapi", "luttapi", "hey jarvis", "jarvis", "hey proton"]
        print("[ClapDetector] Fallback: listening for voice wake word...")
        while self._running:
            if self._paused:
                time.sleep(0.5)
                continue

            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=0.3)
                    audio = r.listen(src, timeout=5, phrase_time_limit=4)
                text = r.recognize_whisper(audio, model="base.en").lower()
                print(f"[ClapDetector fallback] Heard: {text}")
                if any(w in text for w in wake_words):
                    print("[ClapDetector fallback] Wake word detected!")
                    try:
                        self._callback()
                    except Exception as e:
                        print(f"[ClapDetector] Callback error: {e}")
            except Exception:
                pass
