#!/usr/bin/env python3
"""
Remote Server Restart Endpoint
Allows clients to restart the server remotely
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Server Restart Service")
SCRIPT_DIR = Path(__file__).parent
RESTART_FLAG = SCRIPT_DIR / ".restart_requested"

@app.post("/restart")
async def restart_server():
    """Request server restart"""
    try:
        # Create restart flag file
        RESTART_FLAG.touch()
        return JSONResponse({"status": "restart_requested", "message": "Server will restart within 10 seconds"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/health")
async def health():
    """Health check for restart service"""
    return {"status": "healthy", "service": "restart_endpoint"}

if __name__ == "__main__":
    print("🔄 Starting Remote Restart Service on port 8081...")
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="warning")
