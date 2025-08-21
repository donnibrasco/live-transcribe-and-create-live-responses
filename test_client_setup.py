"""
Test script to verify the macOS client setup works
"""
import sounddevice as sd
import numpy as np

def test_audio_setup():
    print("🔍 Testing audio setup...")
    
    try:
        # List audio devices
        devices = sd.query_devices()
        print(f"✅ Found {len(devices)} audio devices:")
        
        input_devices = []
        for i, device in enumerate(devices):
            if device.get('max_input_channels', 0) > 0:
                input_devices.append(i)
                print(f"  {i}: {device['name']} (inputs: {device['max_input_channels']})")
        
        if not input_devices:
            print("❌ No input devices found!")
            return False
            
        # Test default device
        default_device = sd.default.device[0]
        print(f"\n🎤 Default input device: {default_device}")
        
        # Try a short recording test
        print("🔴 Testing 1-second recording...")
        test_audio = sd.rec(16000, samplerate=16000, channels=1, dtype='float32')
        sd.wait()
        
        rms = np.sqrt(np.mean(test_audio ** 2))
        print(f"✅ Recording test complete. Audio level: {rms:.4f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio test failed: {e}")
        return False

if __name__ == "__main__":
    if test_audio_setup():
        print("\n✅ Client setup looks good!")
        print("💡 Next steps:")
        print("   1. Set up your Linux server with: python transcription_server.py")
        print("   2. Set server URL: export TRANSCRIBE_SERVER='http://YOUR_SERVER_IP:8080'")
        print("   3. Start client: python audio_client.py")
    else:
        print("\n❌ Setup issues detected.")
        print("💡 On macOS, check System Preferences → Security & Privacy → Privacy → Microphone")
        print("💡 You may need: brew install portaudio")
