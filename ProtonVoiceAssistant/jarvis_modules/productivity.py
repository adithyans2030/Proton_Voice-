"""
Jarvis Productivity Module
Handles to-do lists, alarms/timers, math eval, and voice notes.
"""
import os
import json
import threading
import time
from datetime import datetime
import math

class ProductivityManager:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.todo_file = os.path.join(self.data_dir, "todo.json")
        self.notes_file = os.path.join(self.data_dir, "voice_notes.txt")
        self._ensure_todo_file()

    def _ensure_todo_file(self):
        if not os.path.exists(self.todo_file):
            with open(self.todo_file, 'w') as f:
                json.dump({"tasks": []}, f)

    def add_todo(self, task_name):
        with open(self.todo_file, 'r') as f:
            data = json.load(f)
        task_id = len(data["tasks"]) + 1
        data["tasks"].append({"id": task_id, "task": task_name, "status": "pending"})
        with open(self.todo_file, 'w') as f:
            json.dump(data, f, indent=4)
        return f"Added '{task_name}' to your to-do list."

    def list_todos(self):
        with open(self.todo_file, 'r') as f:
            data = json.load(f)
        if not data["tasks"]:
            return "Your to-do list is empty."
        res = "To-Do List:\n"
        for t in data["tasks"]:
            status = "[x]" if t["status"] == "completed" else "[ ]"
            res += f"{t['id']}. {status} {t['task']}\n"
        return res

    def remove_todo(self, task_id):
        with open(self.todo_file, 'r') as f:
            data = json.load(f)
        initial_len = len(data["tasks"])
        data["tasks"] = [t for t in data["tasks"] if str(t["id"]) != str(task_id)]
        if len(data["tasks"]) < initial_len:
            with open(self.todo_file, 'w') as f:
                json.dump(data, f, indent=4)
            return f"Removed task {task_id}."
        return f"Task ID {task_id} not found."

    def set_timer(self, minutes, message, alert_callback):
        """Sets a timer in a background thread"""
        try:
            mins = float(minutes)
            def timer_thread():
                time.sleep(mins * 60)
                alert_callback(f"Timer Alert: {message}")
            threading.Thread(target=timer_thread, daemon=True).start()
            return f"Timer set for {mins} minutes. I will remind you: '{message}'"
        except Exception as e:
            return f"Error setting timer: {str(e)}"

    def take_voice_note(self, text):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.notes_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {text}\n")
            return "Voice note saved successfully."
        except Exception as e:
            return f"Error saving voice note: {str(e)}"

    def math_eval(self, expression):
        """Safely evaluate a mathematical expression"""
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        try:
            # We trust the LLM, but still use restricted eval
            code = compile(expression, "<string>", "eval")
            for name in code.co_names:
                if name not in allowed_names:
                    raise NameError(f"Use of {name} not allowed")
            result = eval(code, {"__builtins__": {}}, allowed_names)
            return f"Result: {result}"
        except Exception as e:
            return f"Error evaluating expression: {str(e)}"
