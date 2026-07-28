# JARVIS Troubleshooting Guide

## Common Errors and Solutions

### 🔴 Speech Recognition Network Errors

**Problem:** Continuous "Speech recognition error: network" messages

**Solutions:**
1. **Check Internet Connection**
   - Web Speech API requires internet connection
   - Ensure you're connected to the internet

2. **Browser Compatibility**
   - Use Chrome or Edge (best support)
   - Firefox and Safari have limited support
   - Try a different browser

3. **Disable Browser Speech Recognition**
   - If network errors persist, the backend microphone will be used
   - Click "Stop Listening" and restart
   - Backend mic doesn't require internet

4. **Microphone Permissions**
   - Allow microphone access in browser settings
   - Check Windows microphone permissions
   - Restart browser after granting permissions

### 🎤 Microphone Not Working

**Problem:** "Microphone not accessible" error

**Solutions:**
1. **Check Windows Permissions**
   - Settings → Privacy → Microphone
   - Enable "Allow apps to access your microphone"
   - Enable "Allow desktop apps to access your microphone"

2. **Check Browser Permissions**
   - Click the lock icon in address bar
   - Allow microphone access
   - Refresh the page

3. **Test Microphone**
   - Use Windows Voice Recorder to test
   - Ensure microphone is not muted
   - Check microphone volume levels

4. **Use Backend Microphone**
   - If browser mic fails, backend mic will be used automatically
   - Backend mic works without browser permissions

### 📦 Import Errors

**Problem:** "ModuleNotFoundError" or import errors

**Solutions:**
1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Check Python Version**
   ```bash
   python --version  # Should be 3.8 or higher
   ```

3. **Virtual Environment** (Recommended)
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

### 🤖 ML Model Not Found

**Problem:** "Model not found" or intent classification not working

**Solutions:**
1. **Train the Model**
   ```bash
   python intent_model.py
   ```
   Or run:
   ```bash
   python setup.py
   ```

2. **Check Models Directory**
   - Ensure `models/` folder exists
   - Should contain `intent_model.joblib` and `intent_labels.json`

### 📧 Email Errors

**Problem:** Email features not working

**Solutions:**
1. **Gmail Setup**
   - Use App Passwords (not regular password)
   - Enable 2-Factor Authentication first
   - Generate App Password: Google Account → Security → App Passwords

2. **Other Email Providers**
   - Check IMAP/SMTP settings
   - Ensure IMAP is enabled in email settings
   - Use correct server addresses and ports

### 🔄 Infinite Restart Loop

**Problem:** Speech recognition keeps restarting after errors

**Solutions:**
1. **Fixed in Latest Version**
   - The latest code includes error handling
   - Auto-restart is limited to 3 retries
   - Network errors stop auto-restart

2. **Manual Restart**
   - Click "Stop Listening"
   - Wait 2-3 seconds
   - Click "Start Listening" again

### 💻 System Control Errors

**Problem:** Commands like shutdown/restart not working

**Solutions:**
1. **Admin Permissions**
   - Run Python script as Administrator
   - Right-click → Run as Administrator

2. **Windows Security**
   - Some commands require elevated permissions
   - Check Windows Defender/antivirus settings

### 🌐 Socket.IO Connection Issues

**Problem:** "Connection failed" or "Disconnected"

**Solutions:**
1. **Check Server**
   - Ensure `app.py` is running
   - Check console for errors
   - Restart the server

2. **Port Conflicts**
   - Default port is 5000
   - Change port in `app.py` if needed
   - Check firewall settings

3. **Browser Console**
   - Press F12 to open developer tools
   - Check Console tab for errors
   - Check Network tab for connection issues

### 🧠 OpenAI API Errors

**Problem:** "OpenAI API error" or conversations not working

**Solutions:**
1. **API Key**
   - Set environment variable: `OPENAI_API_KEY`
   - Get key from: https://platform.openai.com/api-keys
   - Restart server after setting key

2. **API Credits**
   - Check OpenAI account has credits
   - Free tier has limited usage

3. **Fallback**
   - Assistant works without OpenAI
   - Only advanced conversations require it

## Quick Fixes

### Reset Everything
1. Stop the server (Ctrl+C)
2. Delete `data/` folder (optional, clears user data)
3. Restart server: `python app.py`
4. Refresh browser

### Reinstall Dependencies
```bash
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### Check Logs
- Server console shows all errors
- Browser console (F12) shows frontend errors
- Check both for complete error information

## Still Having Issues?

1. **Check Error Messages**
   - Read the full error message
   - Search for the error online
   - Check if it's a known issue

2. **Update Dependencies**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **Test Components**
   - Test microphone separately
   - Test internet connection
   - Test Python installation

4. **Report Issues**
   - Note the exact error message
   - Include Python version
   - Include browser and OS version
   - Include steps to reproduce

---

**Most Common Fix:** Restart the server and browser, then try again! 🔄

