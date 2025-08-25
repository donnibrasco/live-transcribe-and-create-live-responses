#!/bin/bash
# Unified macOS Client Setup Script
# Sets up everything you need in one go

echo "🚀 Setting up Unified macOS Client (Audio + Chat Control)..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 required. Install from https://python.org"
    exit 1
fi

# Check pip3
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 required but not found"
    exit 1
fi

echo "✅ Python 3 and pip3 found"

# Install requirements
echo "📦 Installing dependencies..."
pip3 install -r unified_client_requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Make executable
chmod +x unified_macos_client.py

echo "🎉 Setup complete!"
echo ""
echo "🎯 Usage:"
echo "python3 unified_macos_client.py --server http://YOUR_SERVER_IP:8080"
echo ""
echo "🎹 Features:"
echo "• 🎤 Continuous audio recording and transcription"
echo "• 🧹 Global hotkeys: Cmd+Shift+C (clear chat)"
echo "• 🛑 Global hotkeys: Cmd+Ctrl+C (stop recording)"
echo "• 📱 macOS notifications for chat clear"
echo "• 🔧 Auto-device detection"
echo ""
echo "💡 Example:"
echo "python3 unified_macos_client.py --server http://5.161.143.194:8080"
