# Live Transcribe + AI Audience Questions

Real-time speech-to-text using Whisper, plus an AI that generates short viewer-style questions from the transcript and writes them to a chat overlay JSON file.

## Features
- Microphone capture via `sounddevice`
- Whisper transcription (`openai-whisper`)
- Optional OpenAI call to generate a concise audience question from each transcript
- Throttled background worker so audio is never blocked
- Windows-friendly chat overlay path via env var

## Requirements
- Python 3.9+
- A working microphone device
- For AI questions: an OpenAI API key with access to your chosen model

Install deps:

```powershell
pip install -r requirements.txt
```

> Whisper requires PyTorch. On Windows, if you hit issues, install a matching PyTorch build for your Python/CPU/GPU from https://pytorch.org/ first, then reinstall `openai-whisper`. Alternatively, use `faster-whisper` which works well on Python 3.13 and doesn’t require Torch.

Python version note (Windows):
- If you want openai-whisper (Torch): prefer Python 3.10–3.12. Python 3.13 may lack wheels.
- If you’re on Python 3.13: use the fallback backend `faster-whisper`.

Quick sanity test without Torch/Whisper:

```powershell
python ".\whisper_ai_stream_questions.py" --dry-run --diagnose
```

This runs the full pipeline without loading Whisper (no Torch needed) and prints OpenAI diagnostics.

## Configure (Windows PowerShell)

```powershell
# Optional: where to save chat overlay
$env:CHAT_FILE_PATH = "C:\Users\Say10\Downloads\chat_messages.json"

# Enable AI questions (optional). If not set, the app falls back to canned responses.
$env:OPENAI_API_KEY = "<your_api_key>"

# Select the model (non-GPT5). Default is a fast, inexpensive model:
$env:OPENAI_MODEL = "gpt-4o-mini"  # or another available non-GPT5 model
```

If your account doesn’t have access to the selected model, the script logs a warning and uses canned responses.

Security: Do not hardcode API keys in source. Prefer environment variables.

## Run

```powershell
python ".\whisper_live_robust.py"
# To force the faster-whisper backend:
# python ".\whisper_live_robust.py" --backend faster
```

Cloud-only (no PyTorch, everything on OpenAI):

```powershell
# Requires: pip install openai sounddevice numpy
$env:OPENAI_API_KEY = "<your_key>"
python ".\openai_cloud_live.py" --seconds 5 --loop
# Optional: pick device index
# python ".\openai_cloud_live.py" --device 1 --seconds 5 --loop
```

It will try configured input device indices and start transcribing. Every ~5 seconds (cooldown), it will enqueue an AI request and append a single viewer-style question to the overlay JSON.

## Tuning
- `DEVICE_OPTIONS` in `whisper_live_robust.py`: order of preferred audio input devices.
- `SAMPLE_RATE`, `CHUNK_DURATION`, `OVERLAP_DURATION`: audio pipeline parameters.
- `ENQUEUE_COOLDOWN_SEC`: how often to generate a question (default 5s).
- `--backend auto|whisper|faster`: choose which transcription engine to use (default auto).

## Troubleshooting
- No AI output: ensure `openai` is installed, `OPENAI_API_KEY` is set, and your key has model access.
- Audio device not found: update `DEVICE_OPTIONS` to match your system `sd.query_devices()`.
- High CPU: use a smaller Whisper model (e.g., `tiny` or `base`).
- PyTorch/Whisper import errors on Python 3.13: run with `--backend faster` to use `faster-whisper` instead of `openai-whisper`.

