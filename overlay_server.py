"""
Minimal overlay server for Linux (or Windows) that:
- Serves an HTML page at /overlay.html which displays the latest text.
- Exposes POST /api/message to receive text from your local PC.
- Stores a rolling list in chat_messages.json for optional reuse.

Run (Linux):
  pip install -r server_requirements.txt
  uvicorn overlay_server:app --host 0.0.0.0 --port 3000

In OBS, set Browser Source URL to: http://YOUR_SERVER_IP:3000/overlay.html
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

CHAT_FILE = os.getenv("CHAT_FILE_PATH", str(ROOT / "chat_messages.json"))

app = FastAPI(title="Overlay Server", version="1.0.0")


# Serve static files (including overlay.html)
app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")


def _read_messages() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(CHAT_FILE):
            with open(CHAT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _write_messages(msgs: List[Dict[str, Any]]) -> None:
    # Keep last 50; write atomically
    msgs = msgs[-50:]
    tmp = CHAT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(msgs, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CHAT_FILE)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


@app.post("/api/message")
async def post_message(req: Request) -> JSONResponse:
    body = await req.json()
    text = str(body.get("text", "")).strip()
    user = str(body.get("user", "PC")).strip()[:64] or "PC"
    ts = int(body.get("ts") or 0) or int(datetime.utcnow().timestamp() * 1000)
    if not text:
        return JSONResponse({"error": "text required"}, status_code=400)

    msgs = _read_messages()
    entry = {
        "username": user,
        "message": text[:2000],
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "ts": ts,
    }
    msgs.append(entry)
    _write_messages(msgs)
    return JSONResponse({"ok": True})


@app.get("/api/last")
def get_last() -> JSONResponse:
    msgs = _read_messages()
    if not msgs:
        return JSONResponse({"user": "", "text": "", "ts": 0})
    m = msgs[-1]
    return JSONResponse({"user": m.get("username", ""), "text": m.get("message", ""), "ts": m.get("ts", 0)})


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/overlay.html", status_code=302)
