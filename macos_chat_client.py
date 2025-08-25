#!/usr/bin/env python3
"""
macOS Global Hotkey Client for Chat Clear
This script runs on your macOS machine and provides global hotkeys to clear chat
"""

import requests
import time
import sys
import subprocess
import json
from threading import Thread

# Server configuration - UPDATE THIS WITH YOUR SERVER IP
SERVER_URL = "http://5.161.143.194:8080"  # Replace with your actual server IP

def clear_chat():
    """Send clear chat request to server"""
    try:
        response = requests.post(f"{SERVER_URL}/api/clear_chat", timeout=5)
        if response.status_code == 200:
            print("✅ Chat cleared successfully")
            # Optional: Show macOS notification
            subprocess.run([
                'osascript', '-e', 
                'display notification "Chat cleared!" with title "Live Chat" sound name "Glass"'
            ], capture_output=True)
        else:
            print(f"❌ Failed to clear chat: {response.status_code}")
    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure the server is running and accessible")

def setup_global_hotkey():
    """Setup global hotkey using macOS shortcuts"""
    try:
        # Try to use pynput for global hotkeys
        from pynput import keyboard
        from pynput.keyboard import Key, Listener
        
        pressed_keys = set()
        
        def on_press(key):
            pressed_keys.add(key)
            
            # Check for Cmd+Shift+C (Clear Chat)
            if (Key.cmd in pressed_keys and 
                Key.shift in pressed_keys and 
                hasattr(key, 'char') and key.char and key.char.lower() == 'c'):
                clear_chat()
            
            # Check for Cmd+Option+C (Alternative)
            elif (Key.cmd in pressed_keys and 
                  Key.alt in pressed_keys and 
                  hasattr(key, 'char') and key.char and key.char.lower() == 'c'):
                clear_chat()
        
        def on_release(key):
            try:
                pressed_keys.discard(key)
            except:
                pass
            
            # Esc to quit
            if key == Key.esc:
                print("👋 Hotkey client stopped")
                return False
        
        print("🎹 macOS Global Hotkeys Active:")
        print("   Cmd+Shift+C: Clear chat")
        print("   Cmd+Option+C: Clear chat (alternative)")
        print("   Esc: Quit this client")
        print("⚠️  Grant accessibility permissions if prompted")
        
        with Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
            
    except ImportError:
        print("❌ pynput not installed. Install with: pip3 install pynput")
        return False
    except Exception as e:
        print(f"❌ Hotkey setup failed: {e}")
        return False
    
    return True

def setup_applescript_shortcuts():
    """Create AppleScript shortcuts as fallback"""
    script_content = f'''
on run
    try
        do shell script "curl -X POST {SERVER_URL}/api/clear_chat"
        display notification "Chat cleared!" with title "Live Chat" sound name "Glass"
    on error
        display notification "Failed to clear chat" with title "Live Chat" sound name "Basso"
    end try
end run
'''
    
    try:
        # Save AppleScript to Applications folder
        script_path = "/Applications/ClearChat.app"
        subprocess.run([
            'osacompile', '-o', script_path, '-e', script_content
        ], check=True)
        
        print("📱 Created ClearChat.app in Applications folder")
        print("💡 You can:")
        print("   1. Double-click ClearChat.app to clear chat")
        print("   2. Add it to Dock for quick access")
        print("   3. Assign a keyboard shortcut in System Preferences")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create AppleScript app")
        return False

def test_connection():
    """Test connection to server"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server connection OK")
            return True
        else:
            print(f"⚠️  Server responded with status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Update SERVER_URL in this script with your server IP")
        return False

def main():
    """Main function"""
    print("🚀 macOS Chat Clear Client")
    print(f"🔗 Server: {SERVER_URL}")
    print()
    
    # Test connection first
    if not test_connection():
        print("❌ Cannot connect to server. Exiting.")
        sys.exit(1)
    
    print("Choose an option:")
    print("1. Global hotkeys (Cmd+Shift+C)")
    print("2. Create AppleScript app")
    print("3. Manual clear (press Enter)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        if not setup_global_hotkey():
            print("Falling back to manual mode...")
            choice = "3"
    
    elif choice == "2":
        setup_applescript_shortcuts()
        print("✅ AppleScript created. You can now use ClearChat.app")
        return
    
    if choice == "3":
        print("💡 Manual mode: Press Enter to clear chat, 'q' to quit")
        while True:
            try:
                user_input = input().strip().lower()
                if user_input == 'q':
                    break
                elif user_input == '':
                    clear_chat()
            except KeyboardInterrupt:
                break
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
