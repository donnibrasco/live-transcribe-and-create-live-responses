import tempfile
import os
import queue
import json
import time
import threading
from datetime import datetime
import argparse
import shutil
import random
from collections import deque

# Lazy imports for audio/array libs will happen inside functions to allow --dry-run without full deps
try:
    from openai import OpenAI  # optional
    _openai_import_ok = True
except Exception:
    OpenAI = None  # type: ignore
    _openai_import_ok = False

DEVICE_OPTIONS = [13, 12, 1, 0]
SAMPLE_RATE = 16000
CHUNK_DURATION = 1
OVERLAP_DURATION = 0.5
MODEL_NAME = "small"
BACKEND = os.getenv("WHISPER_BACKEND", "auto")  # 'auto' | 'whisper' | 'faster'

# Portable chat file location (can override with CHAT_FILE_PATH env var)
CHAT_FILE = os.getenv("CHAT_FILE_PATH", os.path.join(os.getcwd(), "chat_messages.json"))

# OpenAI API key
# Uses the OPENAI_API_KEY environment variable. (Hardcode only in openai_cloud_live.py.)
OPENAI_STATIC_API_KEY = ""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or OPENAI_STATIC_API_KEY.strip()

# OpenAI config (set OPENAI_API_KEY in your environment or via OPENAI_STATIC_API_KEY). Pick a non-GPT5 model by default.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# Hard-disable GPT-5 models if accidentally configured
if OPENAI_MODEL.lower().startswith("gpt-5"):
    print("ℹ️ GPT-5 models are disabled in this app. Falling back to 'gpt-4o-mini'.")
    OPENAI_MODEL = "gpt-4o-mini"
OPENAI_ENABLED = bool(OPENAI_API_KEY) and _openai_import_ok

client = None
if OPENAI_ENABLED and OpenAI is not None:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print(f"💡 OpenAI enabled. Using model: {OPENAI_MODEL}")
    except Exception as e:
        print(f"⚠️ Failed to initialize OpenAI client: {e}. Falling back to local responses.")
        client = None
        OPENAI_ENABLED = False

def _mask_key(key: str) -> str:
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "****"
    return key[:6] + "…" + key[-4:]

def print_openai_diagnostics():
    print("\n=== OpenAI Diagnostics ===")
    print(f"Package import: {'OK' if _openai_import_ok else 'MISSING'}")
    print(f"API key present: {'YES' if bool(OPENAI_API_KEY) else 'NO'}")
    print(f"API key (masked): {_mask_key(OPENAI_API_KEY or '')}")
    print(f"Model: {OPENAI_MODEL}")
    if not _openai_import_ok:
        print("Hint: pip install openai")
    if not OPENAI_API_KEY:
        print("Hint: set OPENAI_API_KEY env var or fill OPENAI_STATIC_API_KEY in the script.")
    if OPENAI_ENABLED and client is None:
        print("Client init failed earlier; see above error. Check internet, firewall, and key validity.")
    print("==========================\n")

def ensure_ffmpeg_available():
    if shutil.which("ffmpeg") is None:
        print("⚠️ FFmpeg not found in PATH. Whisper may fail to transcode audio. Install FFmpeg and restart.")

class Transcriber:
    def __init__(self, backend: str, impl):
        self.backend = backend  # 'whisper' or 'faster'
        self.impl = impl

    def transcribe_file(self, path: str) -> dict:
        if self.backend == 'whisper':
            result = self.impl.transcribe(path, fp16=False, language="en")
            return {"text": result.get("text", "")}
        elif self.backend == 'faster':
            segments, info = self.impl.transcribe(path, language="en")
            text = " ".join(seg.text for seg in segments)
            return {"text": text.strip()}
        else:
            raise RuntimeError(f"Unknown backend: {self.backend}")

def load_transcriber(name: str, backend: str = "auto") -> Transcriber:
    # Try openai-whisper if requested or auto
    if backend in ("whisper", "auto"):
        try:
            import whisper  # type: ignore
            try:
                model = whisper.load_model(name)
            except Exception as e:
                if name != "base":
                    print("↩️ Falling back to 'base' model…")
                    model = whisper.load_model("base")
                else:
                    raise e
            print("🎛 Using backend: openai-whisper")
            return Transcriber('whisper', model)
        except Exception as e:
            if backend == "whisper":
                raise RuntimeError("openai-whisper not available: " + str(e)) from e
            print("ℹ️ openai-whisper unavailable, trying faster-whisper…", e)
    # Fallback to faster-whisper
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(name if name != 'large' else 'large-v2', device="cpu")
        print("🎛 Using backend: faster-whisper (CPU)")
        return Transcriber('faster', model)
    except Exception as e2:
        raise RuntimeError("No transcription backend available. Install either openai-whisper (with PyTorch) or faster-whisper. Error: " + str(e2)) from e2

transcriber = None
audio_queue = queue.Queue()
last_text = ""

# Queue and worker to generate AI questions without blocking audio
ai_queue = queue.Queue(maxsize=10)
stop_event = threading.Event()

COLOR_PALETTE = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3",
    "#A29BFE", "#55EFC4", "#74B9FF", "#FAB1A0", "#81ECEC", "#FDCB6E"
]

# Simple, varied username generator
_ADJECTIVES = [
    "Swift", "Lucky", "Sneaky", "Crimson", "Pixel", "Electric", "Mellow", "Hyper",
    "Cosmic", "Silent", "Dynamic", "Frosty", "Turbo", "Solar", "Neon", "Quantum"
]
_NOUNS = [
    "Comet", "Falcon", "Drift", "Pixel", "Nimbus", "Vortex", "Spectre", "Ranger",
    "Echo", "Glitch", "Nova", "Phantom", "Circuit", "Rider", "Pilot", "Blaze"
]
_recent_usernames = deque(maxlen=200)

def generate_username() -> str:
    for _ in range(5):  # attempt a few times for uniqueness
        adj = random.choice(_ADJECTIVES)
        noun = random.choice(_NOUNS)
        number = str(random.randint(1, 9999)) if random.random() < 0.9 else ""
        style_prefix = "xX" if random.random() < 0.1 else ""
        style_suffix = "Xx" if style_prefix else ("_" if random.random() < 0.25 else "")
        sep = "_" if (random.random() < 0.3 and not style_suffix.endswith("_")) else ""
        name = f"{style_prefix}{adj}{sep}{noun}{style_suffix}{number}"
        # trim to reasonable length
        name = name[:20]
        if name not in _recent_usernames:
            _recent_usernames.append(name)
            return name
    # fallback if collisions
    fallback = f"Viewer{random.randint(1000,9999)}"
    _recent_usernames.append(fallback)
    return fallback

def random_color() -> str:
    return random.choice(COLOR_PALETTE)

_STOPWORDS = {
    "the","a","an","of","to","and","that","is","it","in","on","for","with","as","at","be","this","you","i","we","they","are","was","were","or","by","from"
}

def _extract_keyword(text: str) -> str:
    words = [w.strip(".,!?;:""'()[]{}-").lower() for w in text.split()]
    candidates = [w for w in words if len(w) > 3 and w.isalpha() and w not in _STOPWORDS]
    if not candidates:
        return "that"
    return random.choice(candidates[:10] if len(candidates) > 10 else candidates)

def _fallback_question(text: str) -> str:
    kw = _extract_keyword(text)
    templates = [
        "Can you explain more about {kw}?",
        "Why did you choose {kw}?",
        "What’s your tip for handling {kw}?",
        "Could you show that {kw} part again?",
        "How do you approach {kw} in practice?",
        "Any beginner mistakes around {kw} to avoid?",
    ]
    q = random.choice(templates).format(kw=kw)
    if random.random() < 0.3:
        q += random.choice([" 🤔", " 🔥", " 🙌", " �"])  # light spice
    return q

def generate_audience_question_from_text(text: str) -> dict:
    """Generate a viewer-style question and username.

    Returns a dict: {"message": str, "username": Optional[str], "color": Optional[str]}.
    Falls back to a transcript-aware question and locally generated username/color.
    """
    # Basic guardrails
    if not text or len(text.strip()) < 5:
        return {"message": _fallback_question("topic"), "username": generate_username(), "color": random_color()}

    if not OPENAI_ENABLED or client is None:
        return {"message": _fallback_question(text), "username": generate_username(), "color": random_color()}

    try:
        system_msg = (
            "You are a realistic live stream viewer. Respond ONLY with a compact JSON object. "
            "Generate: 'username' (random, human-like, <=20 chars) and 'message' (ONE short, natural question) "
            "about the provided transcript. Keep the question under 20 words, end with a question mark, "
            "avoid hashtags, repetition, profanity, or private info. Example format: {\"username\":\"SwiftNova12\",\"message\":\"What's your plan for the next lap?\"}."
        )
        user_msg = (
            "Transcript snippet from the streamer:"\
            f"\n\n{text}\n\n"\
            "Return ONLY JSON with 'username' and 'message'."
        )
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=80,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip common code fences if present
        if raw.startswith("```"):
            raw = raw.strip("`\n ")
            if raw.startswith("json"):
                raw = raw[4:].lstrip()
        try:
            obj = json.loads(raw)
            username = str(obj.get("username") or "").strip() or generate_username()
            message = str(obj.get("message") or "").strip()
        except Exception:
            # Parse failure, fallback to using full text as generation seed
            username = generate_username()
            message = _fallback_question(text)

        # Post-process message
        if message and not message.endswith(("?", "？")):
            message = message.rstrip(".!") + "?"
        if len(message) > 140:
            message = message[:137].rstrip() + "…?"

        return {"message": message or _fallback_question(text), "username": username, "color": random_color()}
    except Exception as e:
        print(f"⚠️ OpenAI request failed: {e}")
        return {"message": _fallback_question(text), "username": generate_username(), "color": random_color()}

def ai_generation_worker_loop():
    """Background worker that consumes transcripts and posts generated questions to the overlay."""
    while not stop_event.is_set():
        try:
            item = ai_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            payload = generate_audience_question_from_text(item)
            update_chat_overlay(payload["message"], username=payload.get("username"), color=payload.get("color"))
        finally:
            ai_queue.task_done()

def find_working_device(preferred_indices=None):
    try:
        import sounddevice as sd  # type: ignore
    except Exception as e:
        print("⚠️ sounddevice not available:", e)
        return None, None
    indices = preferred_indices or DEVICE_OPTIONS
    for device_id in indices:
        try:
            # Test with 1 channel first
            test_stream = sd.InputStream(device=device_id, channels=1, samplerate=SAMPLE_RATE, blocksize=1024)
            test_stream.close()
            print(f"✅ Found working device: {device_id}")
            return device_id, 1
        except:
            try:
                # Test with 2 channels
                test_stream = sd.InputStream(device=device_id, channels=2, samplerate=SAMPLE_RATE, blocksize=1024)
                test_stream.close()
                print(f"✅ Found working device: {device_id} (2 channels)")
                return device_id, 2
            except:
                continue
    # Fallback: auto-pick the first input-capable device
    try:
        devices = sd.query_devices()
        default_idx = sd.default.device[0]
        if default_idx is not None:
            try:
                test_stream = sd.InputStream(device=default_idx, channels=1, samplerate=SAMPLE_RATE, blocksize=1024)
                test_stream.close()
                print(f"✅ Using default input device: {default_idx}")
                return int(default_idx), 1
            except Exception:
                pass
        for i, info in enumerate(devices):
            if info.get('max_input_channels', 0) > 0:
                try:
                    test_stream = sd.InputStream(device=i, channels=1, samplerate=SAMPLE_RATE, blocksize=1024)
                    test_stream.close()
                    print(f"✅ Auto-selected input device: {i}")
                    return i, 1
                except Exception:
                    continue
    except Exception as e:
        print(f"⚠️ Could not auto-detect devices: {e}")

    print("❌ No working audio device found!")
    return None, None

def audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status)
    audio_queue.put(indata.copy())

def update_chat_overlay(chat_message, *, username=None, color=None):
    try:
        messages = []
        if os.path.exists(CHAT_FILE):
            try:
                with open(CHAT_FILE, 'r') as f:
                    messages = json.load(f)
            except Exception as e:
                print(f"⚠️ Could not parse existing chat file, starting fresh: {e}")
        else:
            # ensure parent dir exists
            os.makedirs(os.path.dirname(CHAT_FILE) or ".", exist_ok=True)
        
        new_message = {
            "username": username or generate_username(),
            "message": chat_message,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "color": color or random_color(),
        }
        
        messages.append(new_message)
        messages = messages[-10:]
        
        # Atomic write to avoid partial/corrupt file
        tmp_path = CHAT_FILE + ".tmp"
        with open(tmp_path, 'w') as f:
            json.dump(messages, f, indent=2)
        os.replace(tmp_path, CHAT_FILE)
        
        print(f"💬 {new_message['username']}: {chat_message}")
    except Exception as e:
        print(f"Error updating chat overlay: {e}")

def transcribe_stream(device_id, channels, *, silence_threshold=0.001, enqueue_cooldown=5.0, dry_run=False):
    import numpy as np  # type: ignore
    from scipy.io.wavfile import write  # type: ignore
    global last_text
    buffer = np.zeros(int(SAMPLE_RATE * (CHUNK_DURATION + OVERLAP_DURATION)), dtype=np.float32)
    SILENCE_THRESHOLD = silence_threshold
    last_enqueue_time = 0.0
    ENQUEUE_COOLDOWN_SEC = enqueue_cooldown  # avoid spamming API on tiny updates
    
    while True:
        data = audio_queue.get()
        if data is None:
            break
        
        buffer[:-len(data)] = buffer[len(data):]
        if channels == 2:
            buffer[-len(data):] = np.mean(data, axis=1)  # Convert to mono
        else:
            buffer[-len(data):] = data.flatten()
        
        rms = np.sqrt(np.mean(buffer ** 2))
        print(f"🔊 Audio RMS: {rms:.4f} (threshold: {SILENCE_THRESHOLD})")
        
        if rms < SILENCE_THRESHOLD:
            print("🔇 Audio too quiet, skipping...")
            continue
        
        print("🎤 Processing audio for transcription...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            write(tmpfile.name, SAMPLE_RATE, buffer)
            tmp_path = tmpfile.name
        
        if dry_run:
            # Simulate a transcript without invoking Whisper, for quick plumbing checks
            result = {"text": "Hello world, testing the pipeline."}
        else:
            result = transcriber.transcribe_file(tmp_path)
        text = result.get("text", "").strip()
        
        if text and text != last_text:
            print("🗣", text)
            last_text = text
            now = time.time()
            # Throttle enqueueing so we don't flood the API/overlay
            if now - last_enqueue_time >= ENQUEUE_COOLDOWN_SEC:
                last_enqueue_time = now
                try:
                    # Prefer async question generation to avoid blocking audio
                    if not ai_queue.full():
                        ai_queue.put_nowait(text)
                    else:
                        print("⚠️ AI queue full, dropping this transcript chunk")
                except Exception:
                    payload = generate_audience_question_from_text(text)
                    update_chat_overlay(payload["message"], username=payload.get("username"), color=payload.get("color"))
            else:
                print("⏱️ Skipping enqueue due to cooldown")
        
        os.remove(tmp_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live transcribe and generate audience questions.")
    parser.add_argument("--device", type=int, default=None, help="Audio input device index to use.")
    parser.add_argument("--model", type=str, default=MODEL_NAME, help="Whisper model name (tiny, base, small, medium, large)")
    parser.add_argument("--cooldown", type=float, default=5.0, help="Seconds between AI question generations")
    parser.add_argument("--silence", type=float, default=0.001, help="RMS silence threshold")
    parser.add_argument("--dry-run", action="store_true", help="Don’t call Whisper; simulate transcript for plumbing test")
    parser.add_argument("--diagnose", action="store_true", help="Print detailed OpenAI diagnostics and exit")
    parser.add_argument("--backend", type=str, default=BACKEND, choices=["auto","whisper","faster"], help="Transcription backend")
    args = parser.parse_args()

    ensure_ffmpeg_available()

    transcriber = load_transcriber(args.model, backend=args.backend) if not args.dry_run else None

    print(f"💬 Chat messages will be saved to: {CHAT_FILE}")
    if args.diagnose:
        print_openai_diagnostics()
    if OPENAI_ENABLED:
        print(f"🤖 AI questions enabled via model: {OPENAI_MODEL}")
    else:
        if not _openai_import_ok:
            print("ℹ️ 'openai' package not installed. Using canned responses. Install with: pip install openai")
        elif not OPENAI_API_KEY:
            print("ℹ️ OPENAI_API_KEY not set. Using canned responses. Set it in your environment or code to enable AI.")
        else:
            print("ℹ️ OpenAI disabled due to initialization failure. Run with --diagnose for details.")

    worker_thread = threading.Thread(target=ai_generation_worker_loop, name="ai-worker", daemon=True)
    worker_thread.start()

    if args.dry_run:
        samples = [
            "Dry run: pipeline test one.",
            "Dry run: pipeline test two.",
        ]
        for s in samples:
            if not ai_queue.full():
                ai_queue.put_nowait(s)
        ai_queue.join()
        stop_event.set()
        worker_thread.join(timeout=2.0)
        print("✅ Dry-run completed. Check chat_messages.json.")
        exit(0)

    device_id, channels = (args.device, 1) if args.device is not None else find_working_device()
    if device_id is None:
        print("Cannot start - no working audio device found!")
        stop_event.set()
        worker_thread.join(timeout=2.0)
        exit(1)
    print(f"🎙 Starting with device {device_id}, {channels} channels")
    try:
        import sounddevice as sd  # type: ignore
    except Exception as e:
        print(f"❌ sounddevice import failed: {e}")
        stop_event.set()
        worker_thread.join(timeout=2.0)
        exit(1)
    stream = sd.InputStream(
        device=device_id,
        channels=channels,
        samplerate=SAMPLE_RATE,
        callback=audio_callback,
        blocksize=int(SAMPLE_RATE * CHUNK_DURATION)
    )
    try:
        with stream:
            transcribe_stream(device_id, channels, silence_threshold=args.silence, enqueue_cooldown=args.cooldown, dry_run=False)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
    finally:
        stop_event.set()
        try:
            ai_queue.put_nowait("")
        except Exception:
            pass
        worker_thread.join(timeout=2.0)
