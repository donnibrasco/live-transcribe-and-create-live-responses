import os
import io
import time
import json
import argparse
import tempfile
from datetime import datetime
import random
from collections import deque

import numpy as np
import sounddevice as sd
import wave

try:
    from openai import OpenAI
except Exception as e:  # pragma: no cover
    raise SystemExit("openai package not installed. Run: pip install openai")


def wav_bytes_from_float_pcm(data: np.ndarray, samplerate: int) -> bytes:
    # Ensure mono float32 in [-1, 1]
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    data = np.clip(data, -1.0, 1.0).astype(np.float32)
    # Convert to int16
    pcm16 = (data * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()


FIRST_NAMES = [
    "Liam","Noah","Oliver","Elijah","James","William","Benjamin","Lucas","Henry","Alexander",
    "Emma","Olivia","Ava","Sophia","Isabella","Mia","Charlotte","Amelia","Evelyn","Abigail",
    "Aiden","Jackson","Logan","Mason","Ethan","Sebastian","Jack","Levi","Mateo","Daniel",
    "Harper","Ella","Elizabeth","Sofia","Avery","Mila","Scarlett","Eleanor","Madison","Layla"
]
LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
    "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
    "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson",
    "Walker","Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores"
]
_recent_names = deque(maxlen=200)

def generate_real_name() -> str:
    # Avoid very recent repeats for realism
    for _ in range(10):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        if name not in _recent_names:
            _recent_names.append(name)
            return name
    # Fallback if collisions
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    _recent_names.append(name)
    return name

def update_chat_overlay(chat_file: str, message: str, username: str = None, color: str = "#55EFC4"):
    try:
        msgs = []
        if os.path.exists(chat_file):
            try:
                with open(chat_file, 'r') as f:
                    msgs = json.load(f)
            except Exception:
                msgs = []
        os.makedirs(os.path.dirname(chat_file) or ".", exist_ok=True)
        if not username:
            username = generate_real_name()
        entry = {
            "username": username,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "color": color,
        }
        msgs.append(entry)
        msgs = msgs[-10:]
        tmp = chat_file + ".tmp"
        with open(tmp, 'w') as f:
            json.dump(msgs, f, indent=2)
        os.replace(tmp, chat_file)
        print(f"chat ➜ {username}: {message}")
    except Exception as e:
        print("overlay write error:", e)


def transcribe_chunk(client: OpenAI, wav_bytes: bytes, model: str) -> str:
    # Use OpenAI cloud STT (avoids PyTorch on your machine)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(wav_bytes)
        tmp.flush()
        path = tmp.name
    try:
        with open(path, "rb") as fh:
            resp = client.audio.transcriptions.create(model=model, file=fh)
        # whisper-1 returns .text; newer models similar
        text = getattr(resp, "text", None) or (resp.get("text") if isinstance(resp, dict) else None) or ""
        return text.strip()
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def generate_question(client: OpenAI, transcript: str, model: str) -> str:
    sys = (
        "You are a realistic live stream viewer. Return ONE short natural question (<20 words) "
        "about the transcript. Do not add hashtags or extra commentary."
    )
    user = f"Transcript:\n\n{transcript}"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ],
        temperature=0.6,
        max_tokens=60,
    )
    msg = resp.choices[0].message.content.strip()
    return msg


def main():
    ap = argparse.ArgumentParser(description="Simple OpenAI cloud live transcribe + question")
    ap.add_argument("--seconds", type=float, default=5.0, help="Record duration per chunk")
    ap.add_argument("--samplerate", type=int, default=16000, help="Sample rate (Hz)")
    ap.add_argument("--device", type=int, default=None, help="sounddevice input device index")
    # Continuous by default; use --once to run a single chunk
    ap.add_argument("--once", action="store_true", help="Record once and exit (default is continuous)")
    ap.add_argument("--interval", type=float, default=0.2, help="Pause between chunks when looping (seconds)")
    # Back-compat: --loop is no longer needed; continuous is default
    ap.add_argument("--loop", action="store_true", help="Deprecated: continuous is default; use --once to disable")
    ap.add_argument("--stt-model", type=str, default=os.getenv("OPENAI_STT_MODEL", "whisper-1"), help="OpenAI STT model")
    ap.add_argument("--chat-model", type=str, default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), help="OpenAI chat model")
    ap.add_argument("--out", type=str, default=os.getenv("CHAT_FILE_PATH", os.path.join(os.getcwd(), "chat_messages.json")), help="Overlay JSON path")
    ap.add_argument("--no-ai", action="store_true", help="Skip generating a viewer question; only print transcript")
    args = ap.parse_args()

    # Use environment variable for security
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY in file or environment to use OpenAI APIs.")

    client = OpenAI(api_key=api_key)
    sd.default.samplerate = args.samplerate
    if args.device is not None:
        sd.default.device = (args.device, None)

    def once():
        print(f"Recording {args.seconds}s @ {args.samplerate} Hz…")
        audio = sd.rec(int(args.seconds * args.samplerate), channels=1, dtype='float32')
        sd.wait()
        wav_bytes = wav_bytes_from_float_pcm(audio[:, 0], args.samplerate)
        print("Uploading to OpenAI for transcription…")
        text = transcribe_chunk(client, wav_bytes, args.stt_model)
        print("Transcript:", text or "<empty>")
        if text and not args.no_ai:
            q = generate_question(client, text, args.chat_model)
            update_chat_overlay(args.out, q)

    if args.once:
        once()
        return
    
    print("Running continuously. Press Ctrl+C to stop.")
    try:
        while True:
            try:
                once()
            except Exception as e:
                print("chunk error:", e)
                # brief backoff to avoid busy-loop on repeated errors
                time.sleep(0.5)
            time.sleep(max(0.0, args.interval))
    except KeyboardInterrupt:
        print("\nStopping…")


if __name__ == "__main__":
    main()
