#!/bin/bash
# macOS Client Setup Script
# Run this on your macOS machine to set up the chat clear functionality

echo "🚀 Setting up macOS Chat Clear Client..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "💡 Install Python 3 from https://python.org or use Homebrew: brew install python3"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

echo "✅ Python 3 and pip3 found"

# Install requirements
echo "📦 Installing Python dependencies..."
pip3 install -r macos_client_requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Make the client script executable
chmod +x macos_chat_client.py

echo "🎉 Setup complete!"
echo ""
echo "🎯 How to use:"
echo "1. Update SERVER_URL in macos_chat_client.py with your server IP"
echo "2. Run: python3 macos_chat_client.py"
echo "3. Choose option 1 for global hotkeys (Cmd+Shift+C)"
echo "4. Or choose option 2 to create an app you can click"
echo ""
echo "🌐 Browser method:"
echo "Open http://YOUR_SERVER_IP:8080/overlay in browser"
echo "Use: Cmd+O, Cmd+L, Cmd+Shift+C, F5, Delete, or Backspace"
