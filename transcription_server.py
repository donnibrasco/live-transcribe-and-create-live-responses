"""
Server that receives audio from clients, processes with OpenAI, and serves HTML overlay
"""
import os
import io
import json
import tempfile
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

# Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_STT_MODEL = os.environ.get("OPENAI_STT_MODEL", "whisper-1")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Server setup
app = FastAPI(title="Live Transcription Server", version="1.0.0")
ROOT = Path(__file__).resolve().parent

# Global state for the latest response
latest_response = {
    "text": "Waiting for audio...",
    "timestamp": datetime.now().isoformat(),
    "user": "System"
}

def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio using OpenAI Whisper"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            
            with open(tmp_file.name, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model=OPENAI_STT_MODEL,
                    file=audio_file,
                    language="en"
                )
            
            os.unlink(tmp_file.name)
            return transcript.text.strip()
            
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return ""

def generate_response(transcript: str) -> str:
    """Generate AI response to transcript"""
    if not transcript:
        return ""
    
    try:
        system_prompt = """You are a helpful AI assistant responding to live audio transcriptions. 
        Keep responses conversational, helpful, and under 50 words. 
        Respond naturally as if you're having a real conversation."""
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Chat generation error: {e}")
        return f"I heard: {transcript}"

@app.post("/api/process_audio")
async def process_audio(audio: UploadFile = File(...)):
    """Process uploaded audio file"""
    global latest_response
    
    try:
        # Read audio data
        audio_bytes = await audio.read()
        print(f"📥 Received {len(audio_bytes)} bytes of audio")
        
        # Transcribe
        print("🎤 Transcribing...")
        transcript = transcribe_audio(audio_bytes)
        
        if not transcript:
            return JSONResponse({"status": "no_speech", "transcript": ""})
        
        print(f"📝 Transcript: {transcript}")
        
        # Generate AI response
        print("🤖 Generating response...")
        ai_response = generate_response(transcript)
        print(f"💬 Response: {ai_response}")
        
        # Update global state
        latest_response = {
            "text": ai_response or transcript,
            "transcript": transcript,
            "timestamp": datetime.now().isoformat(),
            "user": "AI Assistant"
        }
        
        return JSONResponse({
            "status": "success",
            "transcript": transcript,
            "response": ai_response
        })
        
    except Exception as e:
        print(f"❌ Processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/latest")
async def get_latest():
    """Get the latest response for the overlay"""
    return JSONResponse(latest_response)

@app.get("/overlay")
async def get_overlay():
    """Serve the live overlay HTML"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Live AI Response Overlay</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background: transparent;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            color: #ffffff;
            overflow: hidden;
        }
        
        .container {
            position: relative;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .response-box {
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            padding: 20px 25px;
            margin: 10px 0;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(10px);
            animation: fadeIn 0.3s ease-out;
        }
        
        .user-label {
            font-weight: 700;
            font-size: 14px;
            color: #7c5cff;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .response-text {
            font-size: 18px;
            line-height: 1.4;
            margin: 0;
            word-wrap: break-word;
        }
        
        .timestamp {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.6);
            margin-top: 10px;
            text-align: right;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .loading {
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="response-box">
            <div class="user-label">AI Assistant</div>
            <div class="response-text" id="responseText">Waiting for audio...</div>
            <div class="timestamp" id="timestamp">Ready</div>
        </div>
    </div>

    <script>
        const responseText = document.getElementById('responseText');
        const timestamp = document.getElementById('timestamp');
        
        async function updateOverlay() {
            try {
                const response = await fetch('/api/latest');
                const data = await response.json();
                
                if (data.text) {
                    responseText.textContent = data.text;
                    
                    // Format timestamp
                    const time = new Date(data.timestamp);
                    timestamp.textContent = time.toLocaleTimeString();
                    
                    // Add a subtle animation on update
                    responseText.style.animation = 'none';
                    setTimeout(() => {
                        responseText.style.animation = 'fadeIn 0.3s ease-out';
                    }, 10);
                }
            } catch (error) {
                console.error('Failed to fetch latest response:', error);
            }
        }
        
        // Update every 1 second
        setInterval(updateOverlay, 1000);
        
        // Initial update
        updateOverlay();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/")
async def root():
    """Redirect to overlay"""
    return HTMLResponse(content="""
    <html>
    <head><title>Live Transcription Server</title></head>
    <body>
    <h1>Live Transcription Server</h1>
    <p><a href="/overlay">View Overlay</a></p>
    <p>Use this URL in OBS: <code>http://YOUR_SERVER_IP:8080/overlay</code></p>
    </body>
    </html>
    """)

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "openai_configured": bool(OPENAI_API_KEY)}

if __name__ == "__main__":
    print("🚀 Starting Live Transcription Server...")
    print(f"🤖 OpenAI Model: {OPENAI_MODEL}")
    print(f"🎤 STT Model: {OPENAI_STT_MODEL}")
    print("📱 Use /overlay for OBS Browser Source")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
