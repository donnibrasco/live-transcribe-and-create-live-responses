# Live Transcription with Client-Server Architecture

This setup separates audio recording (macOS client) from AI processing (Linux server).

## Architecture
- **macOS Client**: Records microphone → sends audio to server
- **Linux Server**: Receives audio → OpenAI transcription → OpenAI response → serves HTML overlay  
- **OBS**: Points to server URL for live overlay display

## Quick Setup

### 1. Linux Server Setup

```bash
# Install dependencies
pip install -r server_requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Optional: customize models
export OPENAI_MODEL="gpt-4o-mini"          # Chat model
export OPENAI_STT_MODEL="whisper-1"        # Speech-to-text model

# Start server (port 8080)
python transcription_server.py
```

The server will be available at `http://YOUR_SERVER_IP:8080`

### 2. macOS Client Setup

```bash
# Install dependencies
pip install -r client_requirements.txt

# Configure server URL
export TRANSCRIBE_SERVER="http://YOUR_SERVER_IP:8080"

# Start audio client
python audio_client.py
```

### 3. OBS Browser Source

Add a Browser Source in OBS with:
- **URL**: `http://YOUR_SERVER_IP:8080/overlay`
- **Width**: 800
- **Height**: 600

## How It Works

1. **Audio Recording**: macOS client records 5-second audio chunks from your microphone
2. **Audio Transfer**: Client sends WAV audio to server via HTTP POST
3. **Transcription**: Server uses OpenAI Whisper to convert speech to text
4. **AI Response**: Server generates conversational AI response using GPT model
5. **Overlay Update**: Server updates the live HTML overlay with the latest response
6. **Display**: OBS shows the overlay URL with real-time AI responses

## Configuration Options

### Client Options
```bash
# Use specific audio device
python audio_client.py --device 1

# Adjust recording duration
python audio_client.py --duration 3.0

# Change server URL
python audio_client.py --server "http://192.168.1.50:8080"
```

### Server Environment Variables
```bash
export OPENAI_API_KEY="your-key"           # Required
export OPENAI_MODEL="gpt-4o-mini"          # Chat model
export OPENAI_STT_MODEL="whisper-1"        # Speech model
```

## Endpoints

- `GET /overlay` - HTML overlay for OBS
- `GET /api/latest` - Latest AI response (JSON)
- `POST /api/process_audio` - Upload audio for processing
- `GET /health` - Server health check

## Files Structure

```
├── audio_client.py              # macOS microphone client
├── transcription_server.py      # Linux server with OpenAI integration
├── client_requirements.txt      # macOS dependencies
├── server_requirements.txt      # Linux server dependencies
└── README.md                   # This file
```

## Troubleshooting

### Audio Issues
- Run `python -c "import sounddevice; print(sounddevice.query_devices())"` to list devices
- Use `--device N` to specify device index
- Check microphone permissions in System Preferences → Security & Privacy → Privacy → Microphone

### Server Issues
- Verify OpenAI API key: `curl http://YOUR_SERVER:8080/health`
- Check firewall: ensure port 8080 is open
- View logs in the server terminal

### Network Issues
- Test connectivity: `curl http://YOUR_SERVER:8080/health`
- Ensure client and server are on same network or have routing configured

### macOS-Specific Setup
- Install Python 3.9+ via Homebrew: `brew install python`
- You may need to install PortAudio: `brew install portaudio`
- Grant microphone permissions when prompted

## Security Notes

- Server runs on all interfaces (0.0.0.0) - restrict as needed
- OpenAI API key should be kept secure
- Consider HTTPS for production use
