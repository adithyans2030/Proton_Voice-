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
    SystemMonitor, ContextMemory, SmartHomeManager,
    SystemControlManager, ProductivityManager
)
from intent_model import predict_intent

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "luttapi:latest"

FAST_INTENTS = {
    "GET_TIME": lambda self: self.execute_tool("get_time", {}),
    "SYSTEM_STATUS": lambda self: self.execute_tool("system_status", {}),
    "SYSTEM_HEALTH": lambda self: self.execute_tool("system_status", {}),
}
INTENT_CONFIDENCE_THRESHOLD = 0.10

class LLMAgent:
    RISKY_TOOLS = {"run_command", "write_file", "send_email", "run_code", "browse_web"}

    def __init__(self):
        self.email_manager = EmailManager()
        self.calendar_manager = CalendarManager()
        self.file_manager = FileManager()
        self.system_monitor = SystemMonitor()
        self.context_memory = ContextMemory()
        self.smart_home = SmartHomeManager()
        self.system_control = SystemControlManager()
        self.productivity = ProductivityManager()
        self._browser = None
        self._page = None
        
    def _call_ollama(self, messages, socketio=None):
        """Send chat request to local Ollama instance, streaming tokens as they arrive"""
        try:
            payload = {
                "model": DEFAULT_MODEL,
                "messages": messages,
                "stream": True,
                "keep_alive": "30m",       # don't unload the model between queries
                "options": {
                    "temperature": 0.2,
                    "num_predict": 300,    # cap generation length — unbounded replies are a silent slowdown
                }
            }
            full_text = ""
            with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=180) as response:
                if response.status_code != 200:
                    return f"Error: Ollama returned status code {response.status_code}. Details: {response.text}"
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    full_text += token
                    if socketio and token:
                        socketio.emit("agent_token", {"token": token})
            return full_text.strip()
        except Exception as e:
            return f"Error connecting to Ollama: {str(e)}. Make sure Ollama is running (`ollama serve`)."

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
                    
            elif tool_name == "adjust_brightness":
                level = kwargs.get("level")
                if not level: return "Error: Missing 'level'."
                return self.system_control.adjust_brightness(level)
                
            elif tool_name == "toggle_wifi":
                state = kwargs.get("state")
                if not state: return "Error: Missing 'state'."
                return self.system_control.toggle_wifi(state)
                
            elif tool_name == "power_action":
                action = kwargs.get("action")
                if not action: return "Error: Missing 'action'."
                return self.system_control.power_action(action)
                
            elif tool_name == "take_screenshot":
                filename = kwargs.get("filename", "screenshot.png")
                return self.system_control.take_screenshot(filename)
                
            elif tool_name == "close_application":
                app_name = kwargs.get("app_name")
                if not app_name: return "Error: Missing 'app_name'."
                return self.system_control.close_application(app_name)
                
            elif tool_name == "file_ops":
                action = kwargs.get("action")
                src = kwargs.get("src")
                dest = kwargs.get("dest")
                if not action or not src: return "Error: Missing 'action' or 'src'."
                return self.file_manager.file_ops(action, src, dest)
                
            elif tool_name == "zip_ops":
                action = kwargs.get("action")
                zip_file = kwargs.get("zip_file")
                target = kwargs.get("target")
                if not action or not zip_file: return "Error: Missing 'action' or 'zip_file'."
                return self.file_manager.zip_ops(action, zip_file, target)
                
            elif tool_name == "organize_downloads":
                return self.file_manager.organize_downloads()
                
            elif tool_name == "read_pdf":
                file_path = kwargs.get("file_path")
                if not file_path: return "Error: Missing 'file_path'."
                return self.file_manager.read_pdf(file_path)
                
            elif tool_name == "add_todo":
                task_name = kwargs.get("task_name")
                if not task_name: return "Error: Missing 'task_name'."
                return self.productivity.add_todo(task_name)
                
            elif tool_name == "list_todos":
                return self.productivity.list_todos()
                
            elif tool_name == "remove_todo":
                task_id = kwargs.get("task_id")
                if not task_id: return "Error: Missing 'task_id'."
                return self.productivity.remove_todo(task_id)
                
            elif tool_name == "set_timer":
                minutes = kwargs.get("minutes")
                message = kwargs.get("message", "Timer finished!")
                if not minutes: return "Error: Missing 'minutes'."
                return self.productivity.set_timer(minutes, message, lambda msg: self.context_memory.add_to_history("SYSTEM", msg))
                
            elif tool_name == "take_voice_note":
                text = kwargs.get("text")
                if not text: return "Error: Missing 'text'."
                return self.productivity.take_voice_note(text)
                
            elif tool_name == "math_eval":
                expression = kwargs.get("expression")
                if not expression: return "Error: Missing 'expression'."
                return self.productivity.math_eval(expression)

            elif tool_name == "get_time":
                return f"Current time is {datetime.now().strftime('%I:%M %p')} on {datetime.now().strftime('%Y-%m-%d')}."
                
            else:
                return f"Error: Unknown tool '{tool_name}'."
        except Exception as e:
            return f"Error running tool '{tool_name}': {str(e)}"

    def parse_action(self, response_text):
        """Parse action name and arguments from Llama output"""
        action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response_text, re.DOTALL)
        if not action_match:
            return None, {}
            
        tool_name = action_match.group(1).strip()
        args_str = action_match.group(2).strip()
        
        # Try parsing as JSON first
        if args_str.startswith("{") and args_str.endswith("}"):
            try:
                return tool_name, json.loads(args_str)
            except:
                pass
                
        # Try parsing as python kwargs: key=val or key="val"
        kwargs = {}
        matches = re.finditer(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,]+))', args_str)
        for m in matches:
            key = m.group(1)
            val = m.group(2) or m.group(3) or m.group(4)
            kwargs[key] = val
            
        return tool_name, kwargs

    def run_query(self, user_query, socketio=None):
        """Execute the main agentic loop (ReAct loop)"""
        intent, confidence = predict_intent(user_query)
        if intent in FAST_INTENTS and confidence >= INTENT_CONFIDENCE_THRESHOLD:
            answer = FAST_INTENTS[intent](self)
            self.context_memory.add_to_history(user_query, answer)
            return answer

        recent = self.context_memory.get_recent_context(3)
        
        system_prompt = f"""You are Luttapi — Adi's personal AI assistant, running entirely on his local machine. Think JARVIS from Iron Man: razor-sharp intellect, dry wit, unfailingly precise, and completely devoted to making Adi's life easier and more productive. You speak with calm confidence, a slight edge of dry humor, and zero fluff.

Current Date/Time: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}.

PERSONALITY & VOICE:
- Address Adi as "sir" occasionally for the JARVIS feel, but "Adi" is also fine and natural.
- Be concise. You're being listened to, not read — no bullet lists, no markdown, no asterisks.
- Dry wit is welcome but never at Adi's expense. Be the smartest person in the room who is still genuinely helpful.
- If you don't know something, say so crisply. Never make things up.
- When completing a task, confirm it with brief satisfaction — "Done, sir." or "Consider it handled."
- Never apologize excessively. Confidence is your default setting.
- Proactively point out if something Adi is about to do looks risky or inefficient.

RESPONSE RULES:
- Keep Final Answers SHORT. One to three sentences is ideal. This is spoken out loud.
- Never use markdown formatting, asterisks, numbered lists, or code blocks in your Final Answer.
- Use natural spoken language. Write how a smart, confident person talks.

You operate in a ReAct loop (Thought -> Action -> Observation -> Final Answer).
For every turn, output a 'Thought:' block followed by either an 'Action:' block (to use a tool) or a 'Final Answer:' block.

Available Tools:
- read_file(filepath="path/to/file") : Reads contents of a file.
- write_file(filepath="path/to/file", content="text") : Writes or overwrites a file.
- search_files(query="filename_word") : Searches for files in the notes directory.
- run_command(command="powershell code") : Executes a PowerShell command, returns output.
- open_application(app_name="notepad") : Opens an application by name or path.
- browse_web(action="goto"|"click"|"fill"|"extract_text", url="...", selector="...", text="...") : Controls a real browser — navigate, click, fill forms, or read page text.
- run_code(code="...", language="python") : Executes code and returns stdout/stderr.
- web_search(query="search terms") : Searches the web via DuckDuckGo, returns summaries.
- system_status() : Returns CPU, RAM, battery, and process usage.
- send_email(to_email="...", subject="...", body="...") : Sends an email.
- read_emails() : Reads the 5 most recent emails.
- manage_calendar(action="add"|"list_today"|"list_upcoming", title="...", date_str="YYYY-MM-DD", time_str="HH:MM") : Manages the calendar.
- get_time() : Returns the current local time.
- media_control(action="playpause"|"nexttrack"|"prevtrack"|"volumeup"|"volumedown"|"volumemute") : Controls Spotify, YouTube, or system media.
- read_clipboard() : Reads text currently copied to Adi's clipboard.
- write_clipboard(text="...") : Copies text to Adi's clipboard so he can paste it.
- get_active_window() : Checks what application/window Adi is currently looking at on his screen.
- control_smart_home(device="bedroom_light"|"desk_lamp", state="on"|"off") : Turns smart home devices on or off.
- adjust_brightness(level="50") : Set screen brightness (0-100).
- toggle_wifi(state="on"|"off") : Enable or disable Wi-Fi.
- power_action(action="lock"|"sleep"|"shutdown"|"restart") : Control system power state.
- take_screenshot(filename="screenshot.png") : Takes a screenshot and saves it to Desktop.
- close_application(app_name="notepad") : Force closes an application.
- file_ops(action="move"|"copy"|"delete", src="path1", dest="path2") : Perform file operations.
- zip_ops(action="extract"|"compress", zip_file="archive.zip", target="folder") : Compress or extract zips.
- organize_downloads() : Organizes the user's Downloads folder into categorized folders.
- read_pdf(file_path="path.pdf") : Reads and extracts text from a PDF file.
- add_todo(task_name="...") : Add a task to the to-do list.
- list_todos() : List all pending and completed to-do tasks.
- remove_todo(task_id="1") : Remove a to-do task by ID.
- set_timer(minutes="5", message="...") : Set a timer that will remind Adi in the background.
- take_voice_note(text="...") : Instantly save a timestamped thought/note to voice_notes.txt.
- math_eval(expression="5*12") : Calculate a mathematical expression safely.

Formatting:
To call a tool:
Thought: [Brief reasoning]
Action: tool_name(param1="val1", param2="val2")

To give a final spoken response:
Thought: [Brief summary of findings]
Final Answer: [Spoken response. Concise. Natural. No markdown.]

Remember:
1. Always output 'Thought:' first.
2. Stop after 'Action:' — wait for the Observation before continuing.
3. Loop until you have enough information for a confident Final Answer.
4. For simple questions — time, greetings, general knowledge — answer directly without tools.
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        for turn in recent:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": f"Final Answer: {turn['assistant']}"})
            
        messages.append({"role": "user", "content": user_query})
        
        for step in range(5):
            if socketio:
                socketio.emit("agent_step", {"step": step + 1, "status": "Thinking..."})
                
            model_response = self._call_ollama(messages, socketio=socketio)
            
            messages.append({"role": "assistant", "content": model_response})
            
            thought_match = re.search(r"Thought:\s*(.*?)(?:Action:|Final Answer:|$)", model_response, re.DOTALL)
            thought = thought_match.group(1).strip() if thought_match else ""
            
            if socketio and thought:
                socketio.emit("agent_thought", {"thought": thought})
                
            if "Action:" in model_response:
                tool_name, kwargs = self.parse_action(model_response)
                if tool_name:
                    if tool_name in self.RISKY_TOOLS and socketio:
                        socketio.emit("confirm_required", {"tool": tool_name, "args": kwargs})
                        if not kwargs.pop("_confirmed", False):
                            observation = f"Paused: '{tool_name}' needs your confirmation before running. Click 'Confirm' to proceed."
                            messages.append({"role": "user", "content": f"Observation: {observation}"})
                            socketio.emit("agent_observation", {"observation": observation})
                            continue
                    if socketio:
                        socketio.emit("agent_action", {"tool": tool_name, "args": kwargs})
                        
                    observation = self.execute_tool(tool_name, kwargs)
                    
                    if socketio:
                        socketio.emit("agent_observation", {"observation": observation})
                        
                    messages.append({"role": "user", "content": f"Observation: {observation}"})
                else:
                    observation = "Error: Failed to parse tool action syntax. Please use: Action: tool_name(param1=\"val1\")"
                    messages.append({"role": "user", "content": f"Observation: {observation}"})
            
            elif "Final Answer:" in model_response:
                final_match = re.search(r"Final Answer:\s*(.*)", model_response, re.DOTALL)
                final_answer = final_match.group(1).strip() if final_match else model_response
                self.context_memory.add_to_history(user_query, final_answer)
                return final_answer
                
            else:
                self.context_memory.add_to_history(user_query, model_response)
                return model_response
                
        fallback = "I apologize, but that task requires too many actions. Is there a specific part you would like me to perform first?"
        self.context_memory.add_to_history(user_query, fallback)
        return fallback
