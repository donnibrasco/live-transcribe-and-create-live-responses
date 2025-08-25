#!/usr/bin/env python3
"""
Unified macOS Client - Audio Recording + Chat Control
This single file handles both audio transcription and chat clearing
"""
import os
import io
import time
import wave
import argparse
import requests
import numpy as np
import sounddevice as sd
import threading
import sys
from pathlib import Path

# Audio settings
SAMPLE_RATE = 16000
CHUNK_DURATION = 5.0  # seconds per chunk
CHANNELS = 1

class UnifiedClient:
    def __init__(self, server_url, device_id=None, interval=0.5):
        self.server_url = server_url.rstrip('/')
        self.device_id = device_id
        self.interval = interval
        self.recording = False
        self.audio_thread = None
        self.hotkey_thread = None
        
    def find_working_device(self):
        """Find a working audio input device (macOS optimized)"""
        try:
            devices = sd.query_devices()
            print("🔍 Available audio devices:")
            
            # Print all devices for reference
            for i, device in enumerate(devices):
                marker = "📥" if device.get('max_input_channels', 0) > 0 else "📤"
                print(f"  {marker} {i}: {device['name']} (in:{device.get('max_input_channels', 0)}, out:{device.get('max_output_channels', 0)})")
            
            # Try default input first
            try:
                default_input = sd.default.device[0]
                if default_input is not None:
                    test_stream = sd.InputStream(device=default_input, channels=CHANNELS, samplerate=SAMPLE_RATE, blocksize=1024)
                    test_stream.close()
                    print(f"✅ Using default input device: {default_input}")
                    return int(default_input)
            except Exception as e:
                print(f"⚠️  Default device test failed: {e}")
            
            # Try each input device
            for i, info in enumerate(devices):
                if info.get('max_input_channels', 0) > 0:
                    try:
                        test_stream = sd.InputStream(device=i, channels=CHANNELS, samplerate=SAMPLE_RATE, blocksize=1024)
                        test_stream.close()
                        print(f"✅ Found working device: {i} - {info['name']}")
                        return i
                    except Exception as e:
                        print(f"⚠️  Device {i} failed: {e}")
            
            print("❌ No working audio devices found!")
            return None
            
        except Exception as e:
            print(f"❌ Error finding audio device: {e}")
            return None

    def audio_to_wav_bytes(self, audio_data, sample_rate):
        """Convert audio data to WAV bytes"""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            
            # Convert float to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wav_file.writeframes(audio_int16.tobytes())
        
        return buffer.getvalue()

    def send_audio_to_server(self, wav_bytes):
        """Send audio data to server"""
        try:
            files = {'audio': ('audio.wav', wav_bytes, 'audio/wav')}
            response = requests.post(f"{self.server_url}/api/process_audio", files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"📝 Transcription: {result.get('transcription', 'No text')}")
                if result.get('ai_responses'):
                    print(f"🤖 AI Responses: {len(result['ai_responses'])} generated")
            else:
                print(f"❌ Server error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except Exception as e:
            print(f"❌ Network error: {e}")

    def clear_chat(self):
        """Clear chat on server"""
        try:
            response = requests.post(f"{self.server_url}/api/clear_chat", timeout=5)
            if response.status_code == 200:
                print("✅ Chat cleared successfully")
                # Optional: macOS notification
                try:
                    import subprocess
                    subprocess.run([
                        'osascript', '-e', 
                        'display notification "Chat cleared!" with title "Live Chat" sound name "Glass"'
                    ], capture_output=True)
                except:
                    pass
            else:
                print(f"❌ Failed to clear chat: {response.status_code}")
        except Exception as e:
            print(f"❌ Error clearing chat: {e}")

    def setup_hotkeys(self):
        """Setup global hotkeys for chat clearing"""
        try:
            from pynput import keyboard
            from pynput.keyboard import Key, Listener
            
            pressed_keys = set()
            
            def on_press(key):
                pressed_keys.add(key)
                
                # Cmd+Shift+C - Clear chat
                if (Key.cmd in pressed_keys and 
                    Key.shift in pressed_keys and 
                    hasattr(key, 'char') and key.char and key.char.lower() == 'c'):
                    self.clear_chat()
                
                # Cmd+Option+X - Clear chat (alternative)
                elif (Key.cmd in pressed_keys and 
                      Key.alt in pressed_keys and 
                      hasattr(key, 'char') and key.char and key.char.lower() == 'x'):
                    self.clear_chat()
                
                # Cmd+Ctrl+C - Stop recording
                elif (Key.cmd in pressed_keys and 
                      Key.ctrl in pressed_keys and 
                      hasattr(key, 'char') and key.char and key.char.lower() == 'c'):
                    print("🛑 Stopping recording...")
                    self.recording = False
            
            def on_release(key):
                try:
                    pressed_keys.discard(key)
                except:
                    pass
                
                if key == Key.esc:
                    print("👋 Hotkey listener stopped")
                    return False
            
            print("🎹 Global hotkeys active:")
            print("   Cmd+Shift+C: Clear chat")
            print("   Cmd+Option+X: Clear chat (alternative)")
            print("   Cmd+Ctrl+C: Stop recording")
            print("   Esc: Quit")
            
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
                
        except ImportError:
            print("⚠️  pynput not available. Install with: pip3 install pynput")
            print("💡 Using keyboard shortcuts in terminal instead:")
            self.terminal_controls()
        except Exception as e:
            print(f"❌ Hotkey setup failed: {e}")
            self.terminal_controls()

    def terminal_controls(self):
        """Fallback terminal controls"""
        print("🎹 Terminal controls:")
        print("   Press Enter: Clear chat")
        print("   Type 'stop': Stop recording")
        print("   Type 'quit': Exit")
        
        while self.recording:
            try:
                user_input = input().strip().lower()
                if user_input == '':
                    self.clear_chat()
                elif user_input in ['stop', 's']:
                    print("🛑 Stopping recording...")
                    self.recording = False
                elif user_input in ['quit', 'q', 'exit']:
                    print("🛑 Quitting...")
                    self.recording = False
                    break
            except (EOFError, KeyboardInterrupt):
                self.recording = False
                break

    def start_audio_recording(self):
        """Start continuous audio recording"""
        if self.device_id is None:
            self.device_id = self.find_working_device()
            if self.device_id is None:
                return False
        
        self.recording = True
        print(f"🎤 Starting audio recording (device {self.device_id})...")
        print(f"📡 Server: {self.server_url}")
        print(f"⏱️  Recording {CHUNK_DURATION}s chunks every {self.interval}s")
        print("🎵 Speak into your microphone...")
        
        while self.recording:
            try:
                # Record audio chunk
                duration = CHUNK_DURATION
                frames = int(duration * SAMPLE_RATE)
                
                print(f"🔴 Recording {duration}s...")
                audio_data = sd.rec(frames, samplerate=SAMPLE_RATE, channels=CHANNELS, device=self.device_id, dtype=np.float32)
                sd.wait()  # Wait for recording to complete
                
                # Flatten to 1D array
                audio_data = audio_data.flatten()
                
                # Check audio level
                rms = np.sqrt(np.mean(audio_data ** 2))
                print(f"🔊 Audio level: {rms:.4f}")
                
                if rms < 0.001:  # Very quiet threshold
                    print("🔇 Audio too quiet, skipping...")
                else:
                    # Convert to WAV and send
                    wav_bytes = self.audio_to_wav_bytes(audio_data, SAMPLE_RATE)
                    print(f"📤 Sending {len(wav_bytes)} bytes to server...")
                    self.send_audio_to_server(wav_bytes)
                
                # Wait before next recording
                if self.interval > 0:
                    time.sleep(self.interval)
                    
            except Exception as e:
                print(f"❌ Recording error: {e}")
                time.sleep(1)  # Brief pause before retry
        
        return True

    def test_connection(self):
        """Test connection to server with auto-restart capability"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Connected to server: {self.server_url}")
                return True
            else:
                print(f"⚠️  Server responded with status: {response.status_code}")
                return self.try_restart_server()
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return self.try_restart_server()

    def try_restart_server(self):
        """Try to restart the server remotely"""
        try:
            # Extract IP from server URL
            server_ip = self.server_url.replace('http://', '').replace('https://', '').split(':')[0]
            restart_url = f"http://{server_ip}:8081/restart"
            
            print("🔄 Attempting to restart server...")
            response = requests.post(restart_url, timeout=10)
            
            if response.status_code == 200:
                print("✅ Server restart requested")
                print("⏳ Waiting for server to come back online...")
                
                # Wait up to 30 seconds for server to restart
                for i in range(30):
                    try:
                        health_response = requests.get(f"{self.server_url}/health", timeout=5)
                        if health_response.status_code == 200:
                            print(f"✅ Server is back online! (took {i+1}s)")
                            return True
                    except:
                        pass
                    time.sleep(1)
                
                print("⚠️  Server restart timed out")
                return False
            else:
                print("❌ Server restart failed - manual intervention needed")
                return False
                
        except Exception as e:
            print(f"❌ Auto-restart failed: {e}")
            print("💡 Try manual restart or check server status")
            return False

    def run(self):
        """Run the unified client"""
        print("🚀 Unified macOS Client - Audio + Chat Control")
        print(f"🔗 Server: {self.server_url}")
        
        # Test connection
        if not self.test_connection():
            print("❌ Cannot connect to server. Check server URL and ensure server is running.")
            return 1
        
        # Start hotkey listener in background
        self.hotkey_thread = threading.Thread(target=self.setup_hotkeys, daemon=True)
        self.hotkey_thread.start()
        
        # Start audio recording in main thread
        try:
            self.start_audio_recording()
        except KeyboardInterrupt:
            print("\n🛑 Stopping client...")
            self.recording = False
        
        print("👋 Client stopped")
        return 0

def main():
    parser = argparse.ArgumentParser(description="Unified macOS Client - Audio Recording + Chat Control")
    parser.add_argument("--server", default="http://localhost:8080", help="Server URL (default: http://localhost:8080)")
    parser.add_argument("--device", type=int, help="Audio device ID (auto-detect if not specified)")
    parser.add_argument("--interval", type=float, default=0.5, help="Interval between recordings in seconds (default: 0.5)")
    
    args = parser.parse_args()
    
    client = UnifiedClient(args.server, args.device, args.interval)
    return client.run()

if __name__ == "__main__":
    sys.exit(main())
