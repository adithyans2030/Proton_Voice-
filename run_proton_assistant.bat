@echo off
cd /d "C:\Users\adith\OneDrive\Desktop\ProtonVoiceAssistant\ProtonVoiceAssistant"
echo Starting Proton Assistant...
start /min "" ollama serve
timeout /t 3 /nobreak >nul
ollama run luttapi:latest ""
"C:\Users\adith\AppData\Local\Programs\Python\Python312\python.exe" proton_desktop.py
