"""
macOS Audio Client - Records microphone and sends audio chunks to server
"""
import os
import io
import time
import wave
import argparse
import requests
import numpy as np
import sounddevice as sd
from pathlib import Path

# Audio settings
SAMPLE_RATE = 16000
CHUNK_DURATION = 5.0  # seconds per chunk
CHANNELS = 1

def find_working_device():
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
        input_devices = []
        for i, info in enumerate(devices):
            if info.get('max_input_channels', 0) > 0:
                input_devices.append(i)
                try:
                    test_stream = sd.InputStream(device=i, channels=CHANNELS, samplerate=SAMPLE_RATE, blocksize=1024)
                    test_stream.close()
                    print(f"✅ Found working device: {i} - {info['name']}")
                    return i
                except Exception as e:
                    print(f"⚠️  Device {i} failed: {e}")
                    continue
        
        if not input_devices:
            print("❌ No input devices found!")
            print("💡 On macOS, check System Preferences → Security & Privacy → Privacy → Microphone")
            
    except Exception as e:
        print(f"❌ Error finding audio device: {e}")
        print("💡 Try: brew install portaudio")
    
    print("❌ No working audio device found!")
    return None

def audio_to_wav_bytes(audio_data, sample_rate):
    """Convert numpy audio data to WAV bytes"""
    # Ensure mono and proper range
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)
    audio_data = np.clip(audio_data, -1.0, 1.0)
    
    # Convert to int16
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    # Create WAV bytes
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    
    return buffer.getvalue()

def send_audio_to_server(server_url, audio_bytes):
    """Send audio bytes to server"""
    try:
        files = {'audio': ('audio.wav', audio_bytes, 'audio/wav')}
        response = requests.post(f"{server_url}/api/process_audio", files=files, timeout=30)
        response.raise_for_status()
        result = response.json()
        print(f"✅ Server response: {result.get('status', 'unknown')}")
        if 'transcript' in result:
            print(f"📝 Transcript: {result['transcript']}")
        return True
    except requests.exceptions.Timeout:
        print("⏰ Server timeout")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Server error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Audio client for live transcription")
    parser.add_argument("--server", default=os.environ.get("TRANSCRIBE_SERVER", "http://192.168.1.100:8080"), 
                       help="Server URL (default: $TRANSCRIBE_SERVER or http://192.168.1.100:8080)")
    parser.add_argument("--device", type=int, help="Audio device index")
    parser.add_argument("--duration", type=float, default=CHUNK_DURATION, help="Recording duration per chunk")
    parser.add_argument("--interval", type=float, default=0.5, help="Pause between recordings")
    args = parser.parse_args()
    
    # Find audio device
    device_id = args.device if args.device is not None else find_working_device()
    if device_id is None:
        print("❌ Cannot start - no audio device found")
        return 1
    
    print(f"🎙️ Recording from device {device_id}")
    print(f"🌐 Server: {args.server}")
    print(f"⏱️ Chunk duration: {args.duration}s")
    print("🎵 Press Ctrl+C to stop\n")
    
    try:
        while True:
            try:
                print(f"🔴 Recording {args.duration}s...")
                
                # Record audio
                audio_data = sd.rec(
                    int(args.duration * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    device=device_id,
                    dtype='float32'
                )
                sd.wait()
                
                # Check if audio has content (not just silence)
                rms = np.sqrt(np.mean(audio_data ** 2))
                print(f"🔊 Audio level: {rms:.4f}")
                
                if rms < 0.001:  # Very quiet threshold
                    print("🔇 Audio too quiet, skipping...")
                else:
                    # Convert to WAV and send
                    wav_bytes = audio_to_wav_bytes(audio_data, SAMPLE_RATE)
                    print(f"📤 Sending {len(wav_bytes)} bytes to server...")
                    send_audio_to_server(args.server, wav_bytes)
                
                # Wait before next recording
                if args.interval > 0:
                    time.sleep(args.interval)
                    
            except Exception as e:
                print(f"❌ Recording error: {e}")
                time.sleep(1)  # Brief pause before retry
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping client...")
    
    return 0

if __name__ == "__main__":
    exit(main())
