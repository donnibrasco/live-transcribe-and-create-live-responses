#!/usr/bin/env python3
"""
macOS Hotkey Client for Chat Clear
Run this script on your macOS machine to enable Cmd+O hotkey
"""

import requests
import time
from pynput import keyboard
from pynput.keyboard import Key, Listener

# Server configuration
SERVER_URL = "http://YOUR_SERVER_IP:8080"  # Replace with your actual server IP

def clear_chat():
    """Send clear chat request to server"""
    try:
        response = requests.post(f"{SERVER_URL}/api/clear_chat", timeout=5)
        if response.status_code == 200:
            print("✅ Chat cleared successfully")
        else:
            print(f"❌ Failed to clear chat: {response.status_code}")
    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure the server is running and accessible")

def main():
    """Main hotkey listener for macOS"""
    pressed_keys = set()
    
    def on_press(key):
        """Handle key press events"""
        pressed_keys.add(key)
        
        # Check for Cmd+O
        if Key.cmd in pressed_keys and hasattr(key, 'char') and key.char == 'o':
            print("🎹 Cmd+O detected - Clearing chat...")
            clear_chat()
    
    def on_release(key):
        """Handle key release events"""
        try:
            pressed_keys.discard(key)
        except:
            pass
        
        # Esc to quit
        if key == Key.esc:
            print("👋 Hotkey client stopped")
            return False
    
    print("🎹 macOS Hotkey Client Started")
    print(f"🔗 Connected to: {SERVER_URL}")
    print("🎯 Press Cmd+O to clear chat")
    print("🛑 Press Esc to quit")
    print("⚠️  Grant accessibility permissions if prompted")
    
    # Test connection
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server connection OK")
        else:
            print("⚠️  Server connection issue")
    except:
        print("❌ Cannot connect to server")
        print("💡 Update SERVER_URL in this script with your server IP")
    
    # Start listening
    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()
