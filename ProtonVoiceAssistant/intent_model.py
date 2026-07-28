import os
import json
from typing import Tuple, List

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


INTENT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "intent_model.joblib")
INTENT_LABELS_PATH = os.path.join(os.path.dirname(__file__), "models", "intent_labels.json")


def _ensure_model_dir():
    model_dir = os.path.dirname(INTENT_MODEL_PATH)
    os.makedirs(model_dir, exist_ok=True)


def get_training_data() -> Tuple[List[str], List[str]]:
    """
    Returns example training data for the intent classifier.
    In a real project, you can expand or replace this with your own dataset.
    """
    texts = [
        # Play music
        "play some music", "play despacito", "can you play a song", "play my favorite song", "play a song on youtube",
        # Time
        "what time is it", "tell me the time", "current time please", "what's the time now",
        # Weather
        "what's the weather", "tell me the weather today", "how is the weather outside", "what is the weather in bangalore",
        # Wikipedia
        "search wikipedia for iron man", "wikipedia naruto", "look up albert einstein on wikipedia",
        # System apps
        "open notepad", "launch notepad", "open calculator", "start the calculator",
        # Bluetooth
        "turn on bluetooth", "enable bluetooth", "turn off bluetooth", "disable bluetooth", "scan bluetooth devices", "detect bluetooth devices",
        # Volume
        "volume up", "increase the volume", "volume down", "decrease volume",
        # Battery
        "battery status", "what is my battery percentage",
        # Jokes
        "tell me a joke", "make me laugh",
        # Shutdown / restart
        "shutdown the system", "turn off the computer", "restart the system", "reboot my pc",
        # Email
        "check my emails", "read my emails", "show me new emails", "check email", "read latest email", "send an email",
        # Calendar
        "what's on my calendar", "show my schedule", "what are my events today", "add event to calendar", "schedule a meeting",
        "set a reminder", "remind me in 10 minutes", "what reminders do i have",
        # File Management
        "create a note", "write a note", "read my notes", "list my notes", "show my notes", "delete a note",
        "search for files", "find files", "file information",
        # System Monitoring
        "system status", "system health", "cpu usage", "memory usage", "disk space", "check system", "system diagnostics",
        "running processes", "top processes",
        # Context/Memory
        "what did we talk about", "conversation history", "remember this", "clear history",
    ]

    labels = [
        "PLAY_MUSIC", "PLAY_MUSIC", "PLAY_MUSIC", "PLAY_MUSIC", "PLAY_MUSIC",
        "GET_TIME", "GET_TIME", "GET_TIME", "GET_TIME",
        "GET_WEATHER", "GET_WEATHER", "GET_WEATHER", "GET_WEATHER",
        "WIKIPEDIA_SEARCH", "WIKIPEDIA_SEARCH", "WIKIPEDIA_SEARCH",
        "OPEN_NOTEPAD", "OPEN_NOTEPAD", "OPEN_CALCULATOR", "OPEN_CALCULATOR",
        "ENABLE_BLUETOOTH", "ENABLE_BLUETOOTH", "DISABLE_BLUETOOTH", "DISABLE_BLUETOOTH", "SCAN_BLUETOOTH", "SCAN_BLUETOOTH",
        "VOLUME_UP", "VOLUME_UP", "VOLUME_DOWN", "VOLUME_DOWN",
        "BATTERY_STATUS", "BATTERY_STATUS",
        "JOKE", "JOKE",
        "SHUTDOWN", "SHUTDOWN", "RESTART", "RESTART",
        # Email
        "CHECK_EMAIL", "CHECK_EMAIL", "CHECK_EMAIL", "CHECK_EMAIL", "READ_EMAIL", "SEND_EMAIL",
        # Calendar
        "GET_CALENDAR", "GET_CALENDAR", "GET_CALENDAR", "ADD_EVENT", "ADD_EVENT",
        "SET_REMINDER", "SET_REMINDER", "GET_REMINDERS",
        # File Management
        "CREATE_NOTE", "CREATE_NOTE", "READ_NOTES", "LIST_NOTES", "LIST_NOTES", "DELETE_NOTE",
        "SEARCH_FILES", "SEARCH_FILES", "FILE_INFO",
        # System Monitoring
        "SYSTEM_STATUS", "SYSTEM_HEALTH", "CPU_INFO", "MEMORY_INFO", "DISK_INFO", "SYSTEM_STATUS", "SYSTEM_HEALTH",
        "RUNNING_PROCESSES", "RUNNING_PROCESSES",
        # Context
        "CONVERSATION_HISTORY", "CONVERSATION_HISTORY", "REMEMBER", "CLEAR_HISTORY",
    ]

    return texts, labels


def train_intent_model() -> None:
    """
    Train a simple text classifier for intents and save it to disk.
    You can run this function manually from a separate training script.
    """
    _ensure_model_dir()
    texts, labels = get_training_data()

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )

    pipeline.fit(texts, labels)

    joblib.dump(pipeline, INTENT_MODEL_PATH)
    with open(INTENT_LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(set(labels)), f)


_intent_pipeline: Pipeline | None = None


def load_intent_model() -> Pipeline | None:
    """
    Load the trained intent model from disk if it exists.
    Returns None if no model is found (the assistant will fall back to rules).
    """
    global _intent_pipeline

    if _intent_pipeline is not None:
        return _intent_pipeline

    if not os.path.exists(INTENT_MODEL_PATH):
        return None

    _intent_pipeline = joblib.load(INTENT_MODEL_PATH)
    return _intent_pipeline


def predict_intent(text: str) -> Tuple[str | None, float]:
    """
    Predict the intent for a given text command.
    Returns (intent_label, confidence) or (None, 0.0) if no model is available.
    """
    model = load_intent_model()
    if model is None:
        return None, 0.0

    probs = model.predict_proba([text])[0]
    classes = model.classes_

    max_idx = probs.argmax()
    return str(classes[max_idx]), float(probs[max_idx])


if __name__ == "__main__":
    # Simple entry point to (re)train the model.
    print("Training intent model...")
    train_intent_model()
    print(f"Model saved to: {INTENT_MODEL_PATH}")



