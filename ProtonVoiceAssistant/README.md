# JARVIS - Just A Rather Very Intelligent System

A comprehensive AI-powered voice assistant inspired by Iron Man's JARVIS, built with Python, Flask, and Machine Learning.

## 🚀 Features

### Core Capabilities
- **Voice Recognition**: Advanced speech-to-text using Google Speech Recognition and browser-based Web Speech API
- **ML-Powered Intent Classification**: Machine learning model for understanding user commands
- **Natural Language Processing**: Context-aware conversations with OpenAI GPT integration
- **Wake Word Detection**: Activate with "Hey Jarvis" or "Hey Proton"

### Daily Work Automation

#### 📧 Email Management
- Check and read emails
- Send emails via voice commands
- Email configuration and management

#### 📅 Calendar & Scheduling
- View today's events and upcoming schedule
- Add events and meetings
- Set reminders with custom timing
- View pending reminders

#### 📝 File & Note Management
- Create, read, and delete notes
- Search for files on your system
- Get file information
- Organize your digital workspace

#### 💻 System Monitoring
- Real-time CPU, memory, and disk usage
- System health diagnostics
- Running processes monitoring
- Battery status tracking
- Network statistics

#### 🎵 Media & Entertainment
- Play music on YouTube
- Control system volume
- Change desktop wallpapers

#### 🔧 System Control
- Bluetooth device management
- System shutdown/restart
- Application launching
- Weather information
- Wikipedia searches

#### 🧠 Context & Memory
- Conversation history tracking
- User preference memory
- Context-aware responses
- Personalized interactions

## 📋 Requirements

- Python 3.8 or higher
- Windows 10/11 (primary support)
- Microphone for voice input
- Internet connection for some features

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ProtonVoiceAssistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Train the ML intent model** (first time setup)
   ```bash
   cd ProtonVoiceAssistant
   python intent_model.py
   ```

4. **Configure OpenAI API** (optional, for advanced conversations)
   ```bash
   # Windows PowerShell
   $env:OPENAI_API_KEY = "your-api-key-here"
   
   # Or set it permanently in system environment variables
   ```

5. **Configure Email** (optional)
   - The assistant will prompt you to set up email credentials when needed
   - Supports Gmail and other IMAP/SMTP services

## 🎯 Usage

1. **Start the server**
   ```bash
   python app.py
   ```

2. **Open your browser**
   - Navigate to `http://localhost:5000`
   - Click "Start Assistant"
   - Click "Start Listening"

3. **Voice Commands**
   - Say "Hey Jarvis" or "Hey Proton" to activate (if wake word detection is enabled)
   - Or use the browser's built-in speech recognition
   - Try commands like:
     - "What's on my calendar today?"
     - "Check my emails"
     - "Create a note shopping list with milk and eggs"
     - "Set a reminder to call mom in 30 minutes"
     - "What's my system status?"
     - "Play some music"

## 📁 Project Structure

```
ProtonVoiceAssistant/
├── app.py                      # Flask server and Socket.IO
├── assistant.py                # Main assistant logic
├── intent_model.py             # ML intent classification
├── requirements.txt            # Python dependencies
├── jarvis_modules/             # Feature modules
│   ├── email_manager.py        # Email handling
│   ├── calendar_manager.py     # Calendar & reminders
│   ├── file_manager.py         # File operations
│   ├── system_monitor.py       # System monitoring
│   └── context_memory.py       # Context & memory
├── templates/
│   └── index.html              # Web UI
├── models/                     # ML models (auto-generated)
└── data/                       # User data (auto-generated)
    ├── email_config.json
    ├── calendar_events.json
    ├── reminders.json
    ├── context.json
    └── notes/
```

## 🎨 Example Commands

### Calendar & Reminders
- "What's on my calendar today?"
- "Add event team meeting on 2024-12-25 at 2:00 PM"
- "Set a reminder to take medicine in 30 minutes"
- "What reminders do I have?"

### Email
- "Check my emails"
- "Read my latest email"
- "Send email to john@example.com subject meeting body see you at 3pm"

### Notes & Files
- "Create note shopping list with milk eggs and bread"
- "List my notes"
- "Read note shopping list"
- "Search for files presentation"

### System
- "System status"
- "Check system health"
- "What's my CPU usage?"
- "Show running processes"

### General
- "What time is it?"
- "What's the weather?"
- "Play despacito"
- "Tell me a joke"

## 🔧 Configuration

### Email Setup
When you first use email features, the assistant will guide you through setup. You'll need:
- Email address
- App password (for Gmail, use App Passwords)

### Wake Word Detection
Wake word detection can be toggled in `assistant.py`:
```python
wake_word_detection = True  # Set to False to disable
```

## 🤖 AI/ML Features

### Intent Classification
- Uses scikit-learn with TF-IDF vectorization
- Logistic Regression classifier
- Trained on diverse command examples
- Confidence threshold: 50%

### Natural Language Understanding
- Context-aware conversations
- Conversation history tracking
- User preference learning
- Fallback to OpenAI GPT for complex queries

## 🐛 Troubleshooting

### Microphone Issues
- Check microphone permissions in Windows settings
- Try using browser-based speech recognition (more reliable)

### Model Not Found
- Run `python intent_model.py` to train the model
- Ensure `models/` directory exists

### Email Not Working
- Verify email credentials
- For Gmail, enable "Less secure app access" or use App Passwords
- Check IMAP/SMTP server settings

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.8+)

## 📝 License

This project is for educational and personal use.

## 🙏 Acknowledgments

- Inspired by JARVIS from Iron Man
- Built with Flask, Socket.IO, and scikit-learn
- Uses OpenAI GPT for advanced conversations

## 🔮 Future Enhancements

- [ ] Multi-language support
- [ ] Smart home integration
- [ ] Advanced task automation
- [ ] Voice cloning for responses
- [ ] Mobile app companion
- [ ] Cloud sync for data
- [ ] Advanced ML models (BERT, transformers)
- [ ] Real-time collaboration features

---

**Built with ❤️ for productivity and automation**


