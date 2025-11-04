# 🍎 macOS Client Setup Guide

**Connect your macOS computer to the live transcription server**

## 📋 Prerequisites

Before starting, make sure you have:
- macOS 10.15 or later
- Python 3.8 or later
- Homebrew (optional but recommended)
- Microphone access permissions

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

Open Terminal and run:

```bash
# Install PortAudio (required for audio recording)
brew install portaudio

# Install Python packages
pip3 install sounddevice numpy requests
```

If you don't have Homebrew, install it first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Download the Client

Download `audio_client.py` from the server or use the existing file.

### Step 3: Run the Client

```bash
python3 audio_client.py --server http://65.109.187.67:8000
```

**That's it!** Your microphone is now connected to the server.

---

## 🎯 Detailed Instructions

### Option 1: Simple Audio Client (Recommended)

The simplest way to connect your microphone:

```bash
python3 audio_client.py --server http://65.109.187.67:8000
```

**What it does:**
- 🎤 Records your microphone in 5-second chunks
- 📤 Sends audio to the server
- 🤖 Server transcribes and generates AI responses
- 💬 Responses appear in the overlay at http://65.109.187.67:8000/overlay

**Command Options:**
```bash
# Specify audio device (if auto-detection fails)
python3 audio_client.py --server http://65.109.187.67:8000 --device 1

# Change recording duration (default: 5 seconds)
python3 audio_client.py --server http://65.109.187.67:8000 --duration 3

# Change interval between recordings (default: 0.5 seconds)
python3 audio_client.py --server http://65.109.187.67:8000 --interval 1.0
```

### Option 2: Unified Client (Advanced)

Full-featured client with hotkeys and chat control:

```bash
python3 unified_macos_client.py --server http://65.109.187.67:8000
```

**Features:**
- 🎤 Audio recording (same as simple client)
- 🎹 Global hotkeys for chat control
- 🔄 Auto-restart server if connection fails
- 💬 Clear chat with keyboard shortcuts

**Global Hotkeys:**
- `Cmd+Shift+C` - Clear chat overlay
- `Cmd+Option+X` - Clear chat (alternative)
- `Cmd+Ctrl+C` - Stop recording
- `Esc` - Quit application

---

## 🔧 Troubleshooting

### Problem: "No audio devices found"

**Solution:**
1. Grant microphone permissions:
   - Go to **System Preferences → Security & Privacy → Privacy → Microphone**
   - Enable access for **Terminal** or **Python**

2. List available audio devices:
   ```bash
   python3 -c "import sounddevice; print(sounddevice.query_devices())"
   ```

3. Specify device manually:
   ```bash
   python3 audio_client.py --server http://65.109.187.67:8000 --device 0
   ```

### Problem: "Module not found: sounddevice"

**Solution:**
```bash
# Install PortAudio first
brew install portaudio

# Then install Python package
pip3 install sounddevice
```

### Problem: "Cannot connect to server"

**Solution:**
1. Check server is running:
   ```bash
   curl http://65.109.187.67:8000/health
   ```
   Should return: `{"status":"healthy","openai_configured":true}`

2. Check your internet connection

3. Try restarting the server (from the unified client, it will attempt this automatically)

### Problem: "Audio too quiet, skipping..."

**Solution:**
- Speak louder or closer to the microphone
- Check macOS sound input level:
  - **System Preferences → Sound → Input**
  - Increase input volume slider

---

## 📱 Using with OBS

Once the client is running:

1. Open OBS Studio
2. Add a **Browser Source**
3. Set URL to: `http://65.109.187.67:8000/overlay`
4. Set Width: 800, Height: 600
5. The live chat will appear in your stream!

---

## 🎮 Advanced Usage

### Environment Variable (Optional)

Instead of typing `--server` every time, set an environment variable:

```bash
# Add to ~/.zshrc or ~/.bash_profile
export TRANSCRIBE_SERVER="http://65.109.187.67:8000"

# Then just run:
python3 audio_client.py
```

### Multiple Clients

You can run multiple clients on different computers, all connected to the same server!

### Custom Recording Settings

```bash
# Record longer chunks (10 seconds)
python3 audio_client.py --server http://65.109.187.67:8000 --duration 10

# No pause between recordings
python3 audio_client.py --server http://65.109.187.67:8000 --interval 0
```

---

## 🆘 Getting Help

If you're stuck:

1. Check the server health: http://65.109.187.67:8000/health
2. View the live overlay: http://65.109.187.67:8000/overlay
3. Check audio devices:
   ```bash
   python3 -c "import sounddevice; print(sounddevice.query_devices())"
   ```

---

## 📊 System Requirements

**Minimum:**
- macOS 10.15 (Catalina) or later
- Python 3.8+
- 2GB RAM
- Internet connection
- Microphone

**Recommended:**
- macOS 11.0 (Big Sur) or later
- Python 3.10+
- 4GB RAM
- Stable broadband connection
- Good quality microphone

---

## 🔐 Security Note

The server is currently open to the internet. The OpenAI API key is configured on the server side, so your client doesn't need any API keys.

---

## ✅ Quick Test

To verify everything works:

```bash
# 1. Test server connection
curl http://65.109.187.67:8000/health

# 2. List audio devices
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# 3. Start client
python3 audio_client.py --server http://65.109.187.67:8000

# 4. Speak into microphone
# 5. Check overlay at http://65.109.187.67:8000/overlay
```

---

**🎉 You're all set! Start talking and watch the AI responses appear in the overlay!**
