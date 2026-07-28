from flask import Flask, render_template
from flask_socketio import SocketIO, emit, disconnect
import threading
import assistant
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Inject socketio into assistant.py
assistant.socketio = socketio

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("start")
def handle_start():
    try:
        assistant_thread = threading.Thread(target=assistant.start_assistant)
        assistant_thread.daemon = True
        assistant_thread.start()
        time.sleep(0.5)  # Small delay to ensure thread starts
        emit("status", {"text": "Assistant started"})
    except Exception as e:
        print(f"Error starting assistant: {str(e)}")
        emit("error", {"text": "Failed to start assistant"})

@socketio.on("start_listening")
def handle_start_listening():
    try:
        emit("status", {"text": "Listening"})
    except Exception as e:
        print(f"Error in start_listening: {str(e)}")

@socketio.on("stop_listening")
def handle_stop_listening():
    try:
        emit("status", {"text": "Idle"})
    except Exception as e:
        print(f"Error in stop_listening: {str(e)}")
        emit("error", {"text": "Failed to stop listening"})
        # Only disconnect if there's a critical error, not on every stop_listening

@socketio.on("command")
def handle_command(data):
    try:
        command = data.get("text", "")
        print(f"Received command: {command}")  # Debug print
        if command:
            emit("command_received", {"text": command})
            assistant.execute_command(command)
    except Exception as e:
        print(f"Error executing command: {str(e)}")
        emit("error", {"text": "Command failed to execute"})

if __name__ == "__main__":
    print("Starting server...")
    # Removed deprecated/unsupported 'log_output' argument to prevent startup crash
    socketio.run(app, debug=True)