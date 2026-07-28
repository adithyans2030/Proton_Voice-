# JARVIS Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Setup
```bash
python setup.py
```
This will:
- Create necessary directories
- Train the ML intent model
- Check dependencies

### Step 3: Start JARVIS
```bash
python app.py
```

Then open `http://localhost:5000` in your browser!

## 🎤 First Commands to Try

1. **"What time is it?"** - Get current time
2. **"System status"** - Check your computer's health
3. **"Create note test with hello world"** - Create your first note
4. **"What's on my calendar today?"** - Check your schedule
5. **"Play some music"** - Play music on YouTube

## ⚙️ Optional Configuration

### Enable Advanced Conversations
Set your OpenAI API key:
```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "your-key-here"
```

### Configure Email
When you first use email features, JARVIS will guide you through setup.

## 🎯 Common Commands

### Calendar
- "Add event meeting on 2024-12-25 at 2:00 PM"
- "What's on my calendar today?"
- "Set a reminder to call mom in 30 minutes"

### Notes
- "Create note shopping with milk eggs bread"
- "List my notes"
- "Read note shopping"

### System
- "System health"
- "CPU usage"
- "Memory info"
- "Battery status"

### Email
- "Check my emails"
- "Read my latest email"

## 🐛 Troubleshooting

**Microphone not working?**
- Use browser speech recognition (click "Start Listening")
- Check Windows microphone permissions

**Model not found?**
- Run `python setup.py` again
- Or manually: `python intent_model.py`

**Import errors?**
- Make sure you're in the ProtonVoiceAssistant directory
- Run: `pip install -r requirements.txt`

## 💡 Pro Tips

1. **Wake Word**: Say "Hey Jarvis" or "Hey Proton" to activate
2. **Browser Mic**: More reliable than system microphone
3. **Context**: JARVIS remembers your conversation history
4. **Reminders**: Set reminders like "remind me in 10 minutes to take a break"

Enjoy your JARVIS assistant! 🎉


