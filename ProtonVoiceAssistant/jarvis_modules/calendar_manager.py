"""
Jarvis Calendar Management Module
Handles scheduling, reminders, and calendar events
"""
import os
import json
from datetime import datetime, timedelta
import threading
import time

class CalendarManager:
    def __init__(self):
        self.events_path = os.path.join(os.path.dirname(__file__), "..", "data", "calendar_events.json")
        self.reminders_path = os.path.join(os.path.dirname(__file__), "..", "data", "reminders.json")
        self.events = []
        self.reminders = []
        self.load_events()
        self.load_reminders()
        self.reminder_thread = None
        self.start_reminder_checker()
    
    def load_events(self):
        """Load calendar events from file"""
        if os.path.exists(self.events_path):
            with open(self.events_path, 'r') as f:
                data = json.load(f)
                self.events = data.get("events", [])
        else:
            self.events = []
            self.save_events()
    
    def save_events(self):
        """Save calendar events to file"""
        os.makedirs(os.path.dirname(self.events_path), exist_ok=True)
        with open(self.events_path, 'w') as f:
            json.dump({"events": self.events}, f, indent=2)
    
    def load_reminders(self):
        """Load reminders from file"""
        if os.path.exists(self.reminders_path):
            with open(self.reminders_path, 'r') as f:
                data = json.load(f)
                self.reminders = data.get("reminders", [])
        else:
            self.reminders = []
            self.save_reminders()
    
    def save_reminders(self):
        """Save reminders to file"""
        os.makedirs(os.path.dirname(self.reminders_path), exist_ok=True)
        with open(self.reminders_path, 'w') as f:
            json.dump({"reminders": self.reminders}, f, indent=2)
    
    def add_event(self, title, date_str, time_str=None, description=""):
        """Add a calendar event"""
        try:
            event = {
                "id": len(self.events) + 1,
                "title": title,
                "date": date_str,
                "time": time_str or "00:00",
                "description": description,
                "created": datetime.now().isoformat()
            }
            self.events.append(event)
            self.save_events()
            return f"Event '{title}' added to calendar for {date_str}"
        except Exception as e:
            return f"Failed to add event: {str(e)}"
    
    def get_today_events(self):
        """Get events for today"""
        today = datetime.now().strftime("%Y-%m-%d")
        today_events = [e for e in self.events if e["date"] == today]
        
        if not today_events:
            return "You have no events scheduled for today."
        
        result = f"You have {len(today_events)} event(s) today:\n"
        for event in today_events:
            result += f"- {event['title']} at {event['time']}\n"
        
        return result
    
    def get_upcoming_events(self, days=7):
        """Get upcoming events for the next N days"""
        today = datetime.now()
        upcoming = []
        
        for event in self.events:
            try:
                event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                if today <= event_date <= today + timedelta(days=days):
                    upcoming.append(event)
            except:
                continue
        
        if not upcoming:
            return f"No upcoming events in the next {days} days."
        
        result = f"You have {len(upcoming)} upcoming event(s):\n"
        for event in sorted(upcoming, key=lambda x: x["date"]):
            result += f"- {event['title']} on {event['date']} at {event['time']}\n"
        
        return result
    
    def add_reminder(self, message, minutes_from_now):
        """Add a reminder"""
        reminder_time = datetime.now() + timedelta(minutes=minutes_from_now)
        reminder = {
            "id": len(self.reminders) + 1,
            "message": message,
            "time": reminder_time.isoformat(),
            "completed": False
        }
        self.reminders.append(reminder)
        self.save_reminders()
        return f"Reminder set for {minutes_from_now} minutes from now: {message}"
    
    def start_reminder_checker(self):
        """Start background thread to check reminders"""
        def check_reminders():
            while True:
                now = datetime.now()
                for reminder in self.reminders:
                    if not reminder.get("completed", False):
                        reminder_time = datetime.fromisoformat(reminder["time"])
                        if now >= reminder_time:
                            # Mark as completed and save
                            reminder["completed"] = True
                            self.save_reminders()
                            # The reminder message will be returned and handled by assistant
                            # This is a simple implementation - in production, use a callback
                time.sleep(10)  # Check every 10 seconds
        
        if self.reminder_thread is None or not self.reminder_thread.is_alive():
            self.reminder_thread = threading.Thread(target=check_reminders, daemon=True)
            self.reminder_thread.start()
    
    def get_pending_reminders(self):
        """Get all pending reminders"""
        now = datetime.now()
        pending = [r for r in self.reminders 
                  if not r.get("completed", False) 
                  and datetime.fromisoformat(r["time"]) > now]
        
        if not pending:
            return "No pending reminders."
        
        result = f"You have {len(pending)} pending reminder(s):\n"
        for reminder in sorted(pending, key=lambda x: x["time"]):
            reminder_time = datetime.fromisoformat(reminder["time"])
            time_until = reminder_time - now
            minutes = int(time_until.total_seconds() / 60)
            result += f"- {reminder['message']} (in {minutes} minutes)\n"
        
        return result

