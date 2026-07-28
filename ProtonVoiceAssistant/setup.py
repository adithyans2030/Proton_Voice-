"""
Setup script for JARVIS Assistant
Creates necessary directories and trains the ML model
"""
import os
import sys

def setup_directories():
    """Create necessary directories"""
    directories = [
        "models",
        "data",
        "data/notes",
        "jarvis_modules"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def train_model():
    """Train the intent classification model"""
    try:
        from intent_model import train_intent_model
        print("\nTraining ML intent classification model...")
        train_intent_model()
        print("✓ Model trained successfully!")
        return True
    except Exception as e:
        print(f"✗ Error training model: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        "flask",
        "flask_socketio",
        "speech_recognition",
        "pyttsx3",
        "sklearn",
        "openai"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package} installed")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} missing")
    
    if missing:
        print(f"\n⚠ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    return True

def main():
    print("=" * 50)
    print("JARVIS Assistant Setup")
    print("=" * 50)
    
    print("\n1. Creating directories...")
    setup_directories()
    
    print("\n2. Checking dependencies...")
    deps_ok = check_dependencies()
    
    if not deps_ok:
        print("\n⚠ Please install missing dependencies first.")
        return
    
    print("\n3. Training ML model...")
    model_ok = train_model()
    
    if model_ok:
        print("\n" + "=" * 50)
        print("✓ Setup completed successfully!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Set OPENAI_API_KEY environment variable (optional)")
        print("2. Run: python app.py")
        print("3. Open http://localhost:5000 in your browser")
    else:
        print("\n⚠ Setup completed with warnings.")
        print("You may need to install dependencies: pip install -r requirements.txt")

if __name__ == "__main__":
    main()


