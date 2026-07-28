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
    SystemMonitor, ContextMemory
)

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.1:latest"

class LLMAgent:
    def __init__(self):
        self.email_manager = EmailManager()
        self.calendar_manager = CalendarManager()
        self.file_manager = FileManager()
        self.system_monitor = SystemMonitor()
        self.context_memory = ContextMemory()
        
    def _call_ollama(self, messages):
        """Send chat request to local Ollama instance"""
        try:
            payload = {
                "model": DEFAULT_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.2  # Low temperature for stable tool selection and formatting
                }
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=180)
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "").strip()
            else:
                return f"Error: Ollama returned status code {response.status_code}. Details: {response.text}"
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
                
            elif tool_name == "web_search":
                query = kwargs.get("query")
                if not query:
                    return "Error: Missing 'query'."
                return self.web_search(query)
                
            elif tool_name == "system_status":
                return self.system_monitor.get_system_status()
                
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
        recent = self.context_memory.get_recent_context(5)
        
        system_prompt = f"""You are Luttapi, Adi's personal AI voice assistant running locally on his laptop. You are smart, friendly, slightly witty, and always helpful. You help Adi with his work, answer questions, automate tasks, and keep him productive.
Current Date/Time: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}.

You operate in a ReAct loop (Thought -> Action -> Observation -> Final Answer).
For every turn, you must output a 'Thought:' block followed by either an 'Action:' block (to use a tool) or a 'Final Answer:' block (to speak to Adi).

Available Tools:
- read_file(filepath="path/to/file") : Reads contents of a file (either absolute path or relative to notes folder).
- write_file(filepath="path/to/file", content="text") : Writes/overwrites content to a file.
- search_files(query="filename_word") : Searches for files in notes directory.
- run_command(command="powershell code") : Executes a local powershell terminal command and returns stdout/stderr. Use this to run scripts, count files, list items, launch processes, etc.
- web_search(query="search terms") : Searches the web using DuckDuckGo and returns summaries.
- system_status() : Returns CPU, memory, battery, and process usage.
- send_email(to_email="recipient@example.com", subject="topic", body="message") : Sends email.
- read_emails() : Reads 5 latest emails.
- manage_calendar(action="add"|"list_today"|"list_upcoming", title="Meeting", date_str="YYYY-MM-DD", time_str="HH:MM") : Manages calendar.
- get_time() : Gets the current local time.

Formatting Guidelines:
To invoke a tool, output exactly:
Thought: [Reason about why you need this tool]
Action: tool_name(param1="val1", param2="val2")

When you have the final answer, output exactly:
Thought: [Summarize your findings]
Final Answer: [Your clean spoken response to Adi. Be friendly and call him Adi. Keep responses concise and helpful — this is spoken out loud so avoid long lists or markdown.]

Remember:
1. Always output 'Thought:' first.
2. If you call a tool, you must stop outputting after the 'Action:' block. Wait for the environment to provide the 'Observation:'.
3. Repeat the ReAct loop until you have enough information to write the 'Final Answer:'.
4. For simple questions like time, greetings, or general knowledge, skip tools and answer directly.
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        for turn in recent:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": f"Final Answer: {turn['assistant']}"})
            
        messages.append({"role": "user", "content": user_query})
        
        for step in range(5):
            if socketio:
                socketio.emit("agent_step", {"step": step + 1, "status": "Thinking..."})
                
            model_response = self._call_ollama(messages)
            
            messages.append({"role": "assistant", "content": model_response})
            
            thought_match = re.search(r"Thought:\s*(.*?)(?:Action:|Final Answer:|$)", model_response, re.DOTALL)
            thought = thought_match.group(1).strip() if thought_match else ""
            
            if socketio and thought:
                socketio.emit("agent_thought", {"thought": thought})
                
            if "Action:" in model_response:
                tool_name, kwargs = self.parse_action(model_response)
                if tool_name:
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
