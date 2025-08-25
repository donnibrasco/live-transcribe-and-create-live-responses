# 🎤 Unified macOS Client - Audio + Chat Control

**One single file that does everything!**

## 🚀 Quick Setup

1. **Download these files to your macOS machine:**
   - `unified_macos_client.py`
   - `unified_client_requirements.txt` 
   - `setup_unified_client.sh`

2. **Run setup:**
   ```bash
   chmod +x setup_unified_client.sh
   ./setup_unified_client.sh
   ```

3. **Start the client:**
   ```bash
   python3 unified_macos_client.py --server http://YOUR_SERVER_IP:8080
   ```

## 🎹 Features

### Audio Recording
- 🎤 **Continuous microphone recording**
- 📡 **Automatic transcription via OpenAI**
- 🤖 **AI chat responses generated**
- 🔧 **Auto-detects best audio device**

### Chat Control
- 🧹 **Cmd+Shift+C** - Clear chat (global hotkey)
- 🧹 **Cmd+Option+X** - Clear chat (alternative)
- 🛑 **Cmd+Ctrl+C** - Stop recording
- 📱 **macOS notifications** when chat cleared

### Terminal Fallback
If global hotkeys don't work:
- **Press Enter** - Clear chat
- **Type 'stop'** - Stop recording  
- **Type 'quit'** - Exit

## 🎯 Usage Examples

```bash
# Connect to server
python3 unified_macos_client.py --server http://5.161.143.194:8080

# Use specific audio device
python3 unified_macos_client.py --server http://YOUR_IP:8080 --device 1

# Custom recording interval
python3 unified_macos_client.py --server http://YOUR_IP:8080 --interval 1.0
```

## 🔧 Permissions

**macOS may ask for permissions:**
- ✅ **Microphone access** - Required for audio recording
- ✅ **Accessibility** - Required for global hotkeys
- ✅ **Notifications** - Optional, for chat clear feedback

## 💡 Tips

- **Keep the terminal open** while using
- **Global hotkeys work anywhere** on macOS
- **Audio auto-adjusts** based on microphone levels
- **Server must be running** for client to work

## 🆘 Troubleshooting

**Connection Error:**
- Check server IP and port
- Ensure server is running
- Try: `curl http://YOUR_SERVER_IP:8080/health`

**No Audio Device:**
- Check microphone permissions
- Try different `--device` numbers
- List devices with: `python3 -c "import sounddevice; print(sounddevice.query_devices())"`

**Hotkeys Not Working:**
- Grant accessibility permissions in System Preferences
- Use terminal fallback (Press Enter to clear chat)

---
**One file, all features! 🎉**
