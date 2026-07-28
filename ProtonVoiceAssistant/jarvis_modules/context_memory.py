"""
Jarvis Context Memory Module
Maintains conversation history and context awareness
"""
import os
import json
from datetime import datetime
from collections import deque

class ContextMemory:
    def __init__(self, max_history=50):
        self.max_history = max_history
        self.conversation_history = deque(maxlen=max_history)
        self.user_preferences = {}
        self.context_path = os.path.join(os.path.dirname(__file__), "..", "data", "context.json")
        self.load_context()
    
    def load_context(self):
        """Load conversation history and preferences from file"""
        if os.path.exists(self.context_path):
            try:
                with open(self.context_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = deque(data.get("history", []), maxlen=self.max_history)
                    self.user_preferences = data.get("preferences", {})
            except:
                self.conversation_history = deque(maxlen=self.max_history)
                self.user_preferences = {}
        else:
            self.conversation_history = deque(maxlen=self.max_history)
            self.user_preferences = {}
    
    def save_context(self):
        """Save conversation history and preferences to file"""
        os.makedirs(os.path.dirname(self.context_path), exist_ok=True)
        with open(self.context_path, 'w', encoding='utf-8') as f:
            json.dump({
                "history": list(self.conversation_history),
                "preferences": self.user_preferences
            }, f, indent=2)
    
    def add_to_history(self, user_input, assistant_response):
        """Add a conversation turn to history"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": assistant_response
        }
        self.conversation_history.append(entry)
        self.save_context()
    
    def get_recent_context(self, n=5):
        """Get the last N conversation turns"""
        return list(self.conversation_history)[-n:]
    
    def get_conversation_summary(self):
        """Get a summary of recent conversation"""
        if not self.conversation_history:
            return "No conversation history yet."
        
        recent = list(self.conversation_history)[-5:]
        summary = "Recent conversation:\n"
        for entry in recent:
            summary += f"User: {entry['user']}\nAssistant: {entry['assistant'][:100]}...\n\n"
        
        return summary
    
    def remember_preference(self, key, value):
        """Remember a user preference"""
        self.user_preferences[key] = value
        self.save_context()
        return f"Remembered: {key} = {value}"
    
    def get_preference(self, key):
        """Get a user preference"""
        return self.user_preferences.get(key)
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        self.save_context()
        return "Conversation history cleared."


