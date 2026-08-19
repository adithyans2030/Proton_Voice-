"""
Jarvis LLM Agent Module
Handles local agentic loop using Llama 3.1 via Ollama
"""
import os
import re
import json
import requests
import urllib3
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup

# Disable insecure request warning for verification-free SSL calls (used in local queries/search)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import other Jarvis modules
from jarvis_modules import (
    EmailManager, CalendarManager, FileManager,
    SystemMonitor, ContextMemory, SmartHomeManager
)
from intent_model import predict_intent


FAST_INTENTS = {
    "GET_TIME": lambda self: self.execute_tool("get_time", {}),
    "SYSTEM_STATUS": lambda self: self.execute_tool("system_status", {}),
    "SYSTEM_HEALTH": lambda self: self.execute_tool("system_status", {}),
}
INTENT_CONFIDENCE_THRESHOLD = 0.05

class LLMAgent:
    RISKY_TOOLS = {"run_command", "write_file", "send_email", "run_code", "browse_web"}

    def __init__(self):
        self.email_manager = EmailManager()
        self.calendar_manager = CalendarManager()
        self.file_manager = FileManager()
        self.system_monitor = SystemMonitor()
        self.context_memory = ContextMemory()
        self.smart_home = SmartHomeManager()
        self._browser = None
        self._page = None
        


    def web_search(self, query):
        """Search the web using DuckDuckGo HTML interface without cert verification"""
        try:
            url = f"https://html.duckduckgo.com/html/?q={query}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            res = requests.get(url, headers=headers, verify=False, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            results = []
            for a in soup.find_all("a", class_="result__snippet"):
                parent = a.find_parent("div", class_="result__body")
                if parent:
                    title_a = parent.find("a", class_="result__url")
                    if title_a:
                        title = title_a.text.strip()
                        link = title_a["href"]
                        snippet = a.text.strip()
                        results.append(f"Title: {title}\nURL: {link}\nSnippet: {snippet}\n")
            
            if not results:
                return "No search results found."
            return "\n".join(results[:3])
        except Exception as e:
            return f"Failed to search the web: {str(e)}"

    def run_command(self, command):
        """Execute a shell command locally in PowerShell and return stdout/stderr"""
        try:
            # Run command in powershell
            process = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=30
            )
            output = f"Stdout:\n{process.stdout}\n"
            if process.stderr:
                output += f"Stderr:\n{process.stderr}\n"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def run_code(self, code, language="python"):
        import tempfile
        ext = {"python": ".py", "javascript": ".js"}.get(language, ".py")
        runner = {"python": "python", "javascript": "node"}.get(language, "python")
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, encoding="utf-8") as f:
            f.write(code)
            path = f.name
        try:
            result = subprocess.run([runner, path], capture_output=True, text=True, timeout=30)
            return f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Code execution timed out after 30s."
        finally:
            os.remove(path)

    def browse_web(self, action, url=None, selector=None, text=None):
        """Persistent browser session across ReAct steps so it doesn't reopen a tab every call"""
        from playwright.sync_api import sync_playwright
        if self._browser is None:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=False)
            self._page = self._browser.new_page()

        try:
            if action == "goto" and url:
                self._page.goto(url, timeout=15000)
                return f"Navigated to {url}."
            elif action == "click" and selector:
                self._page.click(selector, timeout=10000)
                return f"Clicked '{selector}'."
            elif action == "fill" and selector and text:
                self._page.fill(selector, text)
                return f"Filled '{selector}'."
            elif action == "extract_text":
                content = self._page.inner_text("body")
                return content[:2000]
            else:
                return "Error: Unknown browse_web action or missing params."
        except Exception as e:
            return f"Error during browse_web: {str(e)}"

    def execute_tool(self, tool_name, kwargs):
        """Route tool names to the actual python modules"""
        try:
            if tool_name == "read_file":
                filepath = kwargs.get("filepath")
                if not filepath:
                    return "Error: Missing 'filepath' parameter."
                # Allow reading notes or other paths
                if not os.path.isabs(filepath):
                    filepath = os.path.join(self.file_manager.notes_path, filepath)
                if not os.path.exists(filepath):
                    return f"Error: File '{filepath}' does not exist."
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()
                    
            elif tool_name == "write_file":
                filepath = kwargs.get("filepath")
                content = kwargs.get("content")
                if not filepath or content is None:
                    return "Error: Missing 'filepath' or 'content'."
                if not os.path.isabs(filepath):
                    filepath = os.path.join(self.file_manager.notes_path, filepath)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Success: Wrote to '{filepath}'"
                
            elif tool_name == "search_files":
                query = kwargs.get("query")
                directory = kwargs.get("directory")
                if not query:
                    return "Error: Missing 'query'."
                if not directory:
                    directory = self.file_manager.notes_path
                return self.file_manager.search_files(directory, query)
                
            elif tool_name == "run_command":
                command = kwargs.get("command")
                if not command:
                    return "Error: Missing 'command'."
                return self.run_command(command)
                
            elif tool_name == "open_application":
                app_name = kwargs.get("app_name")
                if not app_name:
                    return "Error: Missing 'app_name'."
                try:
                    subprocess.Popen(app_name, shell=True)
                    return f"Opened {app_name}."
                except Exception as e:
                    return f"Error opening '{app_name}': {str(e)}"
                    
            elif tool_name == "run_code":
                code = kwargs.get("code")
                language = kwargs.get("language", "python")
                if not code:
                    return "Error: Missing 'code'."
                return self.run_code(code, language)
                
            elif tool_name == "browse_web":
                return self.browse_web(
                    kwargs.get("action"), kwargs.get("url"),
                    kwargs.get("selector"), kwargs.get("text")
                )
                
            elif tool_name == "web_search":
                query = kwargs.get("query")
                if not query:
                    return "Error: Missing 'query'."
                return self.web_search(query)
                
            elif tool_name == "system_status":
                return self.system_monitor.get_system_status()
                
            elif tool_name == "media_control":
                action = kwargs.get("action")
                if not action:
                    return "Error: Missing 'action'."
                try:
                    import pyautogui
                    pyautogui.press(action)
                    return f"Sent media command: {action}"
                except Exception as e:
                    return f"Error controlling media: {str(e)}"
                    
            elif tool_name == "read_clipboard":
                try:
                    import pyperclip
                    content = pyperclip.paste()
                    return f"Clipboard content: {content[:1000]}"
                except Exception as e:
                    return f"Error reading clipboard: {str(e)}"
                    
            elif tool_name == "write_clipboard":
                text = kwargs.get("text")
                if not text:
                    return "Error: Missing 'text'."
                try:
                    import pyperclip
                    pyperclip.copy(text)
                    return "Successfully copied text to clipboard."
                except Exception as e:
                    return f"Error writing to clipboard: {str(e)}"
                    
            elif tool_name == "get_active_window":
                try:
                    import pygetwindow as gw
                    active = gw.getActiveWindow()
                    if active:
                        return f"User is currently looking at window: '{active.title}'"
                    return "No active window detected."
                except Exception as e:
                    return f"Error getting active window: {str(e)}"
                    
            elif tool_name == "control_smart_home":
                device = kwargs.get("device")
                state = kwargs.get("state")
                if not device or not state:
                    return "Error: Missing 'device' or 'state'."
                return self.smart_home.toggle_device(device, state)
                
            elif tool_name == "send_email":
                to_email = kwargs.get("to_email")
                subject = kwargs.get("subject", "No Subject")
                body = kwargs.get("body", "")
                if not to_email or not body:
                    return "Error: Missing 'to_email' or 'body'."
                return self.email_manager.send_email(to_email, subject, body)
                
            elif tool_name == "read_emails":
                num = kwargs.get("num_emails", 5)
                emails = self.email_manager.check_emails(num)
                if isinstance(emails, list):
                    res = "Recent emails:\n"
                    for e in emails:
                        res += f"- From: {e['from']}\n  Subject: {e['subject']}\n  Date: {e['date']}\n\n"
                    return res
                return str(emails)
                
            elif tool_name == "manage_calendar":
                action = kwargs.get("action")
                if not action:
                    return "Error: Missing 'action'."
                if action == "add":
                    title = kwargs.get("title")
                    date_str = kwargs.get("date_str")
                    time_str = kwargs.get("time_str", "12:00")
                    if not title or not date_str:
                        return "Error: Missing 'title' or 'date_str'."
                    return self.calendar_manager.add_event(title, date_str, time_str)
                elif action == "list_today":
                    return self.calendar_manager.get_today_events()
                elif action == "list_upcoming":
                    days = kwargs.get("days", 7)
                    return self.calendar_manager.get_upcoming_events(days)
                else:
                    return f"Error: Unknown calendar action '{action}'."
                    
            elif tool_name == "get_time":
                return f"Current time is {datetime.now().strftime('%I:%M %p')} on {datetime.now().strftime('%Y-%m-%d')}."
                
            else:
                return f"Error: Unknown tool '{tool_name}'."
        except Exception as e:
            return f"Error running tool '{tool_name}': {str(e)}"

    def run_query(self, user_query, socketio=None):
        """Execute the rigid, offline intent-based loop"""
        intent, confidence = predict_intent(user_query)
        
        print(f"[Luttapi] Predicted Intent: {intent} ({confidence:.2f})")
        
        if intent in FAST_INTENTS and confidence >= INTENT_CONFIDENCE_THRESHOLD:
            answer = FAST_INTENTS[intent](self)
            self.context_memory.add_to_history(user_query, answer)
            return answer
            
        # Map intents to rigid actions
        if confidence >= INTENT_CONFIDENCE_THRESHOLD:
            answer = ""
            if intent == "MEDIA_PLAY" or intent == "MEDIA_PAUSE":
                answer = self.execute_tool("media_control", {"action": "playpause"})
            elif intent == "MEDIA_NEXT":
                answer = self.execute_tool("media_control", {"action": "nexttrack"})
            elif intent == "MEDIA_PREV":
                answer = self.execute_tool("media_control", {"action": "prevtrack"})
            elif intent == "MEDIA_MUTE" or intent == "MEDIA_UNMUTE":
                answer = self.execute_tool("media_control", {"action": "volumemute"})
            elif intent == "READ_CLIPBOARD":
                answer = self.execute_tool("read_clipboard", {})
            elif intent == "ACTIVE_WINDOW":
                answer = self.execute_tool("get_active_window", {})
            elif intent == "SMART_HOME_ON":
                if "desk" in user_query.lower():
                    answer = self.execute_tool("control_smart_home", {"device": "desk_lamp", "state": "on"})
                else:
                    answer = self.execute_tool("control_smart_home", {"device": "bedroom_light", "state": "on"})
            elif intent == "SMART_HOME_OFF":
                if "desk" in user_query.lower():
                    answer = self.execute_tool("control_smart_home", {"device": "desk_lamp", "state": "off"})
                else:
                    answer = self.execute_tool("control_smart_home", {"device": "bedroom_light", "state": "off"})
            elif intent == "OPEN_NOTEPAD":
                answer = self.execute_tool("open_application", {"app_name": "notepad"})
            elif intent == "OPEN_CALCULATOR":
                answer = self.execute_tool("open_application", {"app_name": "calc"})
            else:
                answer = f"I understood your intent as '{intent}', but I haven't been programmed to execute it in rigid mode."
                
            self.context_memory.add_to_history(user_query, answer)
            return answer
            
        # Fallback for unrecognized commands
        fallback = "I'm sorry sir, I don't understand that command."
        self.context_memory.add_to_history(user_query, fallback)
        return fallback
