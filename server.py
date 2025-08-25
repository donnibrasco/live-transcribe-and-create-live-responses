from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


APP_PORT = int(os.getenv("PORT", "8000"))
CHAT_FILE_PATH = os.getenv("CHAT_FILE_PATH", str(Path.cwd() / "chat_messages.json"))
PUBLIC_DIR = Path.cwd() / "public"

app = FastAPI(title="Live Transcribe + AI Questions")

# CORS for simple external access; tighten in production
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, Any]:
	return {"ok": True}


@app.get("/api/chat")
def get_chat() -> List[Dict[str, Any]]:
	try:
		if not os.path.exists(CHAT_FILE_PATH):
			return []
		with open(CHAT_FILE_PATH, "r") as f:
			msgs = json.load(f)
		if not isinstance(msgs, list):
			return []
		return msgs
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


# Serve static UI from /public (index.html falls back)
if PUBLIC_DIR.exists():
	app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")


def run():
	import uvicorn

	uvicorn.run("server:app", host="0.0.0.0", port=APP_PORT, reload=False)


if __name__ == "__main__":
	run()

