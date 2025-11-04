"""
Server that receives audio from clients, processes with OpenAI, and serves HTML overlay
"""
import os
from dotenv import load_dotenv
import io
import json
import tempfile
import asyncio
import random
import time
import threading
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from collections import deque

try:
    from pynput import keyboard
    from pynput.keyboard import Key, Listener
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required. Please set it in a .env file or your environment.")

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
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "user": "System"
}

# Global messages list for chat overlay
chat_messages = []

# Chat timing variables for realistic sequences
last_chat_time = 0
chat_queue = []
chat_timer_active = False

# Username generator for random usernames
_ADJECTIVES = [
    "Swift", "Lucky", "Sneaky", "Crimson", "Pixel", "Electric", "Mellow", "Hyper",
    "Cosmic", "Silent", "Dynamic", "Frosty", "Turbo", "Solar", "Neon", "Quantum",
    "Shadow", "Blazing", "Crystal", "Thunder", "Azure", "Golden", "Silver", "Steel"
]
_NOUNS = [
    "Comet", "Falcon", "Drift", "Pixel", "Nimbus", "Vortex", "Spectre", "Ranger",
    "Echo", "Glitch", "Nova", "Phantom", "Circuit", "Rider", "Pilot", "Blaze",
    "Wolf", "Raven", "Tiger", "Dragon", "Phoenix", "Storm", "Star", "Moon"
]
_recent_usernames = deque(maxlen=200)

def generate_username() -> str:
    """Generate a random gaming-style username"""
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
    """Generate a random color for usernames"""
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3",
        "#A29BFE", "#55EFC4", "#74B9FF", "#FAB1A0", "#81ECEC", "#FDCB6E",
        "#7C5CFF", "#FF5722", "#4CAF50", "#2196F3", "#9C27B0", "#FF9800"
    ]
    return random.choice(colors)

def get_chat_response(transcript: str) -> str:
    """Get either a troll/casual response or AI response"""
    # 15% chance for troll/casual responses (balanced for realistic chat)
    if random.random() < 0.15:
        return get_troll_response(transcript)
    else:
        return generate_response(transcript)

def get_troll_response(transcript: str) -> str:
    """Generate natural casual responses"""
    troll_responses = [
        "lol",
        "haha",
        "nice",
        "cool",
        "wow",
        "damn",
        "yep",
        "nah",
        "true",
        "same",
        "real",
        "facts",
        "totally",
        "exactly",
        "for sure",
        "no way",
        "seriously",
        "huh",
        "what",
        "why",
        "how",
        "when",
        "where",
        "okay",
        "alright", 
        "sure",
        "maybe",
        "probably",
        "definitely",
        "possibly",
        "honestly",
        "actually",
        "basically",
        "literally",
        "obviously",
        "clearly",
        "apparently",
        "hopefully",
        "finally",
        "anyway",
        "whatever",
        "nevermind",
        "forget it",
        "my bad",
        "sorry 😅",
        "thanks 🙏",
        "welcome 👋",
        "good luck 🍀",
        "take care 💜",
        "see ya 👋",
        "later ✌️",
        "bye 👋"
    ]
    
    # Context-aware responses
    transcript_lower = transcript.lower()
    
    if any(word in transcript_lower for word in ["money", "rich", "cash", "paid"]):
        return random.choice(["nice 💰", "cool 💵", "wow 🤑", "damn 💸", "lucky 🍀", "sweet 💎"])
    
    if any(word in transcript_lower for word in ["game", "play", "win", "lose"]):
        return random.choice(["nice game 🎮", "good one 👏", "gg 🎯", "well played 🏆", "unlucky 😔", "better luck next time 🍀"])
    
    if any(word in transcript_lower for word in ["chat", "viewers", "stream"]):
        return random.choice(["hey chat 👋", "whats up 🤙", "love this stream ❤️", "good content 👏", "keep it up 💪"])
    
    if any(word in transcript_lower for word in ["new", "channel", "upload"]):
        return random.choice(["first 🥇", "early 🌅", "nice upload 📺", "been waiting ⏰", "good stuff 👌"])
    
    # Default random response
    return random.choice(troll_responses)

def get_context_acronym(transcript: str) -> str:
    """Generate context-aware responses based on transcript"""
    transcript_lower = transcript.lower()
    
    # Natural responses for different contexts
    business_responses = ["makes sense", "good point", "smart move", "solid plan", "fair enough", "i get it"]
    tech_responses = ["nice work", "looks good", "cool tech", "interesting", "pretty neat", "solid build"]
    gaming_responses = ["nice play", "good game", "well done", "not bad", "decent", "smooth"]
    social_responses = ["totally", "same here", "i feel you", "no doubt", "for sure", "exactly"]
    general_responses = ["true that", "makes sense", "good call", "fair point", "sounds right", "i agree"]
    
    # Context-based response selection
    if any(word in transcript_lower for word in ["business", "money", "work", "company", "startup"]):
        return random.choice(business_responses)
    elif any(word in transcript_lower for word in ["tech", "code", "app", "software", "computer", "program"]):
        return random.choice(tech_responses)
    elif any(word in transcript_lower for word in ["game", "play", "level", "character", "battle", "fight"]):
        return random.choice(gaming_responses)
    elif any(word in transcript_lower for word in ["social", "friend", "party", "fun", "hang", "meet"]):
        return random.choice(social_responses)
    else:
        return random.choice(general_responses)

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
    """Generate human-like response to transcript"""
    if not transcript:
        return ""
    
    try:
        system_prompt = """You are a regular person chatting naturally. Never mention that you're an AI or assistant. 
        Respond like a friend or viewer would - casual, relatable, and authentic. Use everyday language, 
        contractions, and speak like you're just having a normal conversation. Keep it under 30 words. 
        No explanations, no helpful tips, just natural human reactions and responses."""
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            max_tokens=80,
            temperature=0.9
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Chat generation error: {e}")
        # Fallback human-like response
        return random.choice(["yeah totally", "that's wild", "lol same", "fr though", "nah man", "true that"])

def add_message_with_delay(message, username, delay_seconds):
    """Add a message to chat after a delay"""
    def delayed_add():
        global chat_messages
        time.sleep(delay_seconds)
        chat_messages.append({
            "username": username,
            "message": message,
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
        })
        # Keep only last 20 messages
        chat_messages = chat_messages[-20:]
    
    thread = threading.Thread(target=delayed_add, daemon=True)
    thread.start()

def schedule_realistic_chat_sequence(initial_message, initial_username, transcript=""):
    """Schedule a realistic sequence of chat messages"""
    global chat_timer_active, last_chat_time
    
    current_time = time.time()
    
    # Don't start new sequence if one is already active (increased cooldown)
    if chat_timer_active or (current_time - last_chat_time) < 15:
        return
    
    chat_timer_active = True
    last_chat_time = current_time
    
    # Add the initial message immediately
    chat_messages.append({
        "username": initial_username,
        "message": initial_message,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
    })
    
    # Generate follow-up messages with context acronyms and emojis
    context_acronym = get_context_acronym(transcript) if transcript else ""
    follow_up_messages = [
        ("true ✅", random.uniform(2, 5)),
        ("same 💯", random.uniform(3, 7)),
        ("real 💯", random.uniform(5, 10)),
        ("facts 📝", random.uniform(8, 15)),
        ("yep 👍", random.uniform(4, 8)),
        ("totally 💯", random.uniform(6, 12)),
        ("lol 😂", random.uniform(3, 6)),
        ("yeah man 🙌", random.uniform(4, 9)),
        ("exactly 💯", random.uniform(7, 12)),
        ("100% 💯", random.uniform(5, 11)),
        ("🔥", random.uniform(2, 4)),
        ("💯", random.uniform(3, 6)),
        ("😂", random.uniform(4, 7)),
        ("👏", random.uniform(5, 8)),
        ("💀", random.uniform(6, 9)),
        ("✨", random.uniform(3, 5)),
    ]
    
    # Add context acronym if available
    if context_acronym:
        follow_up_messages.append((context_acronym, random.uniform(3, 9)))
    
    # Randomly select 1-3 follow-up messages for more realistic chat activity
    num_messages = random.randint(1, 3)  # Increased for more responses
    if num_messages > 0:
        selected_messages = random.sample(follow_up_messages, min(num_messages, len(follow_up_messages)))
        
        for msg, delay in selected_messages:
            add_message_with_delay(msg, generate_username(), delay)
    
    # Reset timer after the longest delay + buffer
    def reset_timer():
        time.sleep(max(delay for _, delay in selected_messages) + 5)
        global chat_timer_active
        chat_timer_active = False
    
    threading.Thread(target=reset_timer, daemon=True).start()

def start_ambient_chat():
    """Start background ambient chat messages"""
    def ambient_loop():
        global chat_messages
        ambient_messages = [
            "hey", "whats up", "yo", "nice", "cool", "lol", "same", "true", "yeah", "nah", 
            "haha", "omg", "wow", "damn", "nice one", "good stuff", "love it", "awesome", 
            "sweet", "dope", "sick", "tight", "solid", "clean", "smooth", "fire", "lit", 
            "wild", "crazy", "insane", "mad", "hard", "tough", "rough", "soft", "chill", 
            "relax", "calm", "peace", "quiet", "loud", "big", "small", "fast", "slow",
            "�", "💯", "🔥", "👏", "💀", "�", "�", "🤔", "�", "✨", "�", "�", "❤️", "�"
        ]
        
        while True:
            # Random delay between 30-120 seconds for ambient messages (30s-2min for more activity)
            delay = random.uniform(30, 120)
            time.sleep(delay)
            
            # Only add ambient if not too active and lower threshold
            if not chat_timer_active and len(chat_messages) < 10:
                message = random.choice(ambient_messages)
                username = generate_username()
                
                chat_messages.append({
                    "username": username,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
                })
                
                # Keep only last 20 messages
                chat_messages = chat_messages[-20:]
    
    # Start ambient chat in background
    ambient_thread = threading.Thread(target=ambient_loop, daemon=True)
    ambient_thread.start()

@app.post("/api/process_audio")
async def process_audio(audio: UploadFile = File(...)):
    """Process uploaded audio file"""
    global latest_response, chat_messages
    
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
        ai_response = get_chat_response(transcript)
        print(f"💬 Response: {ai_response}")
        
        # Schedule realistic chat sequence instead of just adding one message
        if ai_response:
            username = generate_username()
            schedule_realistic_chat_sequence(ai_response, username, transcript)
        
        # Update global state
        latest_response = {
            "text": ai_response or transcript,
            "transcript": transcript,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": generate_username()
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

@app.get("/api/messages")
async def get_messages():
    """Get chat messages for the overlay"""
    return JSONResponse(chat_messages)

@app.post("/api/clear_chat")
async def clear_chat():
    """Clear all chat messages"""
    global chat_messages
    chat_messages.clear()
    
    # Also clear the chat_messages.json file
    chat_file = ROOT / "chat_messages.json"
    try:
        with open(chat_file, 'w') as f:
            json.dump([], f)
        print("🧹 Chat cleared by user")
        return JSONResponse({"status": "Chat cleared successfully"})
    except Exception as e:
        print(f"❌ Error clearing chat file: {e}")
        return JSONResponse({"error": f"Failed to clear chat file: {e}"}, status_code=500)

@app.post("/api/test_text")
async def test_text_input(data: dict):
    """Test endpoint for manual text input (for testing AI responses)"""
    global latest_response
    
    try:
        text = data.get("text", "")
        if not text:
            return JSONResponse({"error": "No text provided"}, status_code=400)
        
        print(f"📝 Manual text input: {text}")
        
        # Generate AI response
        print("🤖 Generating response...")
        ai_response = get_chat_response(text)
        print(f"💬 Response: {ai_response}")
        
        # Update global state
        latest_response = {
            "text": ai_response,
            "transcript": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": generate_username()
        }
        
        return JSONResponse({
            "status": "success",
            "input": text,
            "response": ai_response
        })
        
    except Exception as e:
        print(f"❌ Text processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/overlay")
async def get_overlay():
    """Serve the live overlay HTML"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: transparent;
            font-family: 'Segoe UI', 'Helvetica Neue', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 16px;
            padding: 15px;
            overflow: hidden;
            color: #FFFFFF;
            font-weight: 400;
        }
        
        .chat-container {
            width: 450px;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            gap: 6px;
        }
        
        .chat-message {
            padding: 8px 12px;
            background: transparent;
            border-radius: 0;
            font-size: 15px;
            line-height: 1.4;
            backdrop-filter: none;
            animation: fadeIn 0.4s ease-out;
            box-shadow: none;
            border: none;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .platform-logo {
            width: 18px;
            height: 18px;
            border-radius: 2px;
            flex-shrink: 0;
            opacity: 0.8;
        }
        
        .timestamp {
            color: rgba(255, 255, 255, 0.6);
            font-size: 11px;
            font-weight: 400;
            margin-right: 6px;
            flex-shrink: 0;
        }
        
        .message-content {
            display: flex;
            align-items: baseline;
            gap: 8px;
            flex-grow: 1;
        }
        
        .username {
            font-weight: 700;
            margin-right: 0;
            opacity: 1.0;
            letter-spacing: 0.3px;
            text-shadow: none;
        }
        
        .message-text {
            color: #FFFFFF;
            font-weight: 400;
        }
        
        /* Bright, vibrant username colors for black background */
        .username.color-1 { color: #FF6B6B; }  /* Bright Red */
        .username.color-2 { color: #4ECDC4; }  /* Bright Teal */
        .username.color-3 { color: #45B7D1; }  /* Bright Blue */
        .username.color-4 { color: #96CEB4; }  /* Bright Green */
        .username.color-5 { color: #FECA57; }  /* Bright Yellow */
        .username.color-6 { color: #FF9FF3; }  /* Bright Pink */
        .username.color-7 { color: #54A0FF; }  /* Electric Blue */
        .username.color-8 { color: #5F27CD; }  /* Bright Purple */
        .username.color-9 { color: #00D2D3; }  /* Cyan */
        .username.color-10 { color: #FF6348; } /* Bright Orange */
        .username.color-11 { color: #C44569; } /* Magenta */
        .username.color-12 { color: #F8B500; } /* Gold */
        .username.color-13 { color: #6C5CE7; } /* Lavender */
        .username.color-14 { color: #A3CB38; } /* Lime Green */
        .username.color-15 { color: #FD79A8; } /* Hot Pink */
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="chat-container" id="chat"></div>
    
    <script>
        let lastContent = '';
        let usernameColorMap = {};
        let colorIndex = 1;
        
        function getUsernameColor(username) {
            // Return white color for all usernames
            return 'color: #ffffff;';
        }
        
        function getPlatformLogo() {
            const logos = [
                // YouTube logo
                `<svg class="platform-logo" viewBox="0 0 24 24" fill="#FF0000">
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                </svg>`,
                
                // Kick logo
                `<svg class="platform-logo" viewBox="0 0 24 24" fill="#53FC18">
                    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm6 18H6V6h3v4.5l4.5-4.5H18l-6 6 6 6z"/>
                </svg>`
            ];
            
            return logos[Math.floor(Math.random() * logos.length)];
        }
        
        async function updateChat() {
            try {
                const response = await fetch('/api/messages?' + Math.random());
                const messages = await response.json();
                const newContent = JSON.stringify(messages);
                
                if (newContent !== lastContent) {
                    lastContent = newContent;
                    
                    const container = document.getElementById('chat');
                    container.innerHTML = '';
                    
                    messages.slice(-8).forEach(msg => {
                        const div = document.createElement('div');
                        div.className = 'chat-message';
                        
                        const usernameColorClass = getUsernameColor(msg.username);
                        const platformLogo = getPlatformLogo();
                        
                        div.innerHTML = `
                            ${platformLogo}
                            <span class="timestamp">${msg.timestamp}</span>
                            <div class="message-content">
                                <span class="username ${usernameColorClass}">${msg.username}</span>
                                <span class="message-text">${msg.message}</span>
                            </div>
                        `;
                        container.appendChild(div);
                    });
                    
                    // Force DOM refresh for OBS
                    container.style.display = 'none';
                    container.offsetHeight;
                    container.style.display = 'flex';
                }
            } catch (e) {
                console.log('Loading...');
            }
        }
        
        // Update every 100ms - very aggressive
        setInterval(updateChat, 100);
        updateChat();
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

def clear_chat_from_keyboard():
    """Clear chat when called from keyboard shortcut"""
    global chat_messages
    chat_messages.clear()
    
    # Clear the chat_messages.json file
    chat_file = ROOT / "chat_messages.json"
    try:
        with open(chat_file, 'w') as f:
            json.dump([], f)
        print("\n🧹 Chat cleared by keyboard shortcut (Ctrl/Cmd+O)")
    except Exception as e:
        print(f"\n❌ Error clearing chat file: {e}")

def keyboard_listener():
    """Listen for keyboard shortcuts - tries pynput first, falls back to terminal input"""
    
    # Try pynput for global hotkeys first
    if PYNPUT_AVAILABLE:
        try:
            # Test if we can create a listener (works in GUI environments)
            from pynput.keyboard import Listener
            
            # Track pressed keys
            pressed_keys = set()
            
            def on_press(key):
                """Handle key press events"""
                try:
                    pressed_keys.add(key)
                    
                    # Check for Cmd+O (macOS) or Ctrl+O (Linux/Windows)
                    if (
                        (Key.cmd in pressed_keys or Key.ctrl_l in pressed_keys or Key.ctrl_r in pressed_keys) and
                        hasattr(key, 'char') and key.char and key.char.lower() == 'o'
                    ):
                        clear_chat_from_keyboard()
                        
                except AttributeError:
                    pass
                except Exception as e:
                    print(f"Key press error: {e}")
            
            def on_release(key):
                """Handle key release events"""
                try:
                    pressed_keys.discard(key)
                except:
                    pass
            
            print("🎹 Global keyboard shortcuts active:")
            print("   Cmd+O (macOS) or Ctrl+O (Linux/Windows): Clear chat")
            print("   On macOS: Grant accessibility permissions if prompted")
            
            # Start the global keyboard listener
            with Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
                
        except Exception as e:
            print(f"⚠️ Global keyboard listener failed: {e}")
            print("� Falling back to terminal input method...")
    
    # Fallback to terminal input method with Ctrl+L support
    try:
        import sys
        import tty
        import termios
        
        print("🎹 Terminal keyboard control active:")
        print("   Ctrl+L: Clear chat (standard terminal clear shortcut)")
        print("   Type 'clear' + Enter: Clear chat")
        print("   Type 'quit' + Enter: Exit server")
        print("   Ctrl+C: Exit server")
        
        # Set terminal to raw mode to capture Ctrl+L
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        
        buffer = ""
        
        while True:
            char = sys.stdin.read(1)
            
            # Check for Ctrl+L (ASCII 12)
            if ord(char) == 12:
                clear_chat_from_keyboard()
                buffer = ""
                continue
            
            # Check for Ctrl+C (ASCII 3)
            elif ord(char) == 3:
                print("\n🛑 Shutting down server...")
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                os._exit(0)
            
            # Check for Enter (ASCII 13 or 10)
            elif ord(char) in [13, 10]:
                if buffer.strip().lower() in ['clear', 'c', 'cls']:
                    clear_chat_from_keyboard()
                elif buffer.strip().lower() in ['quit', 'exit', 'q']:
                    print("\n🛑 Shutting down server...")
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    os._exit(0)
                buffer = ""
            
            # Check for backspace (ASCII 127 or 8)
            elif ord(char) in [127, 8]:
                if buffer:
                    buffer = buffer[:-1]
            
            # Regular character
            elif ord(char) >= 32:
                buffer += char
                
    except Exception as e:
        print(f"⚠️ Terminal keyboard listener error: {e}")
        print("💡 Falling back to simple input method...")
        
        # Simple fallback
        print("🎹 Simple keyboard control active:")
        print("   Type 'clear' and press Enter: Clear chat")
        print("   Type 'quit' to exit server")
        
        while True:
            try:
                user_input = input().strip().lower()
                
                if user_input in ['clear', 'c', 'cls']:
                    clear_chat_from_keyboard()
                elif user_input in ['quit', 'exit', 'q']:
                    print("🛑 Shutting down server...")
                    os._exit(0)
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Input error: {e}")
                break
    finally:
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Live Transcription Server...")
    print(f"🤖 OpenAI Model: {OPENAI_MODEL}")
    print(f"🎤 STT Model: {OPENAI_STT_MODEL}")
    print("📱 Use /overlay for OBS Browser Source")
    print("💬 Starting ambient chat system...")
    
    # Start ambient chat system
    start_ambient_chat()
    
    # Start keyboard listener in a separate thread
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
