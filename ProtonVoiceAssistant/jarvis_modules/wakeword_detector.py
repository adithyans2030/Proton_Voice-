import threading
import time
import speech_recognition as sr

class WakeWordDetector:
    """
    Listens to the microphone in a background thread.
    Calls the provided callback when the wake word is detected.
    """

    def __init__(self, on_wake_word, wake_word="hey buddy"):
        self._callback = on_wake_word
        self._wake_word = wake_word.lower()
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="WakeWordDetector")
        self._thread.start()
        print(f"[WakeWordDetector] Started. Say '{self._wake_word}' to wake Luttapi.")

    def stop(self):
        self._running = False

    def _listen_loop(self):
        recognizer = sr.Recognizer()
        
        while self._running:
            try:
                with sr.Microphone() as source:
                    # Adjust for ambient noise briefly
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    # Listen for a short phrase (wake word should be quick)
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # Try to recognize the speech
                text = recognizer.recognize_google(audio).lower()
                print(f"[WakeWordDetector] Heard: '{text}'")
                
                if self._wake_word in text:
                    print(f"[WakeWordDetector] Wake word '{self._wake_word}' detected! 🎙️")
                    try:
                        self._callback()
                    except Exception as e:
                        print(f"[WakeWordDetector] Callback error: {e}")
                        
            except sr.WaitTimeoutError:
                # This is normal, just loop again
                pass
            except sr.UnknownValueError:
                # Speech was unintelligible, ignore
                pass
            except Exception as e:
                print(f"[WakeWordDetector] Listen error: {e}")
                time.sleep(1)
