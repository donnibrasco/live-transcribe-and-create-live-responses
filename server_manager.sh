#!/bin/bash
# Server Manager - Keeps transcription server running in background
# Auto-restarts if it crashes and provides remote restart capability

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_SCRIPT="$SCRIPT_DIR/transcription_server.py"
PID_FILE="$SCRIPT_DIR/server.pid"
LOG_FILE="$SCRIPT_DIR/server.log"
RESTART_FLAG_FILE="$SCRIPT_DIR/.restart_requested"

# Server configuration
HOST="0.0.0.0"
PORT="8080"

# Function to check if server is running
is_server_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            # Check if it's actually our server process
            if ps -p "$pid" -o cmd= | grep -q "transcription_server.py"; then
                return 0  # Server is running
            fi
        fi
    fi
    return 1  # Server is not running
}

# Function to start the server
start_server() {
    echo "🚀 Starting transcription server..."
    cd "$SCRIPT_DIR"
    
    # Start server in background and capture PID
    nohup python3 "$SERVER_SCRIPT" > "$LOG_FILE" 2>&1 &
    local server_pid=$!
    
    # Save PID to file
    echo "$server_pid" > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 3
    if is_server_running; then
        echo "✅ Server started successfully (PID: $server_pid)"
        echo "📋 Logs: $LOG_FILE"
        echo "🌐 URL: http://$(hostname -I | awk '{print $1}'):$PORT"
        return 0
    else
        echo "❌ Failed to start server"
        echo "📋 Check logs: $LOG_FILE"
        return 1
    fi
}

# Function to stop the server
stop_server() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        echo "🛑 Stopping server (PID: $pid)..."
        
        # Try graceful shutdown first
        kill "$pid" 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚡ Force killing server..."
            kill -9 "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        echo "✅ Server stopped"
    else
        echo "⚠️  No PID file found"
    fi
}

# Function to restart the server
restart_server() {
    echo "🔄 Restarting server..."
    stop_server
    sleep 1
    start_server
}

# Function to check restart flag (for remote restart)
check_restart_flag() {
    if [ -f "$RESTART_FLAG_FILE" ]; then
        echo "🔄 Restart requested remotely"
        rm -f "$RESTART_FLAG_FILE"
        restart_server
    fi
}

# Function to show server status
show_status() {
    echo "📊 Server Status Check"
    echo "─────────────────────"
    
    if is_server_running; then
        local pid=$(cat "$PID_FILE")
        echo "✅ Server is RUNNING (PID: $pid)"
        
        # Test if server responds
        if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
            echo "✅ Server is RESPONDING"
        else
            echo "⚠️  Server process exists but not responding"
        fi
    else
        echo "❌ Server is NOT RUNNING"
    fi
    
    echo "📋 Log file: $LOG_FILE"
    echo "🌐 URL: http://$(hostname -I | awk '{print $1}'):$PORT"
}

# Function to monitor and auto-restart
monitor_server() {
    echo "👁️  Starting server monitor (auto-restart enabled)..."
    echo "📝 Press Ctrl+C to stop monitoring"
    
    while true; do
        # Check restart flag first
        check_restart_flag
        
        # Check if server is running
        if ! is_server_running; then
            echo "⚠️  Server not running, starting it..."
            start_server
        else
            # Check if server responds to health check
            if ! curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
                echo "⚠️  Server not responding, restarting..."
                restart_server
            fi
        fi
        
        # Wait before next check
        sleep 10
    done
}

# Function to create remote restart endpoint
create_restart_endpoint() {
    cat > "$SCRIPT_DIR/restart_server.py" << 'EOF'
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
EOF
    
    chmod +x "$SCRIPT_DIR/restart_server.py"
    echo "✅ Remote restart endpoint created: restart_server.py"
}

# Main script logic
case "${1:-}" in
    "start")
        start_server
        ;;
    "stop")
        stop_server
        ;;
    "restart")
        restart_server
        ;;
    "status")
        show_status
        ;;
    "monitor")
        monitor_server
        ;;
    "install")
        create_restart_endpoint
        echo "🎉 Server manager installed!"
        echo ""
        echo "📋 Available commands:"
        echo "  ./server_manager.sh start     - Start server"
        echo "  ./server_manager.sh stop      - Stop server"
        echo "  ./server_manager.sh restart   - Restart server"
        echo "  ./server_manager.sh status    - Check status"
        echo "  ./server_manager.sh monitor   - Auto-restart monitoring"
        echo "  ./server_manager.sh daemon    - Run as background daemon"
        echo ""
        echo "🌐 Remote restart URL (for clients):"
        echo "  curl -X POST http://YOUR_SERVER_IP:8081/restart"
        ;;
    "daemon")
        echo "🔧 Starting as background daemon..."
        nohup "$0" monitor > monitor.log 2>&1 &
        echo $! > monitor.pid
        echo "✅ Monitor daemon started (PID: $(cat monitor.pid))"
        echo "📋 Monitor logs: monitor.log"
        echo "🛑 To stop: kill $(cat monitor.pid)"
        ;;
    *)
        echo "🎛️  Server Manager - Keep Transcription Server Running"
        echo "════════════════════════════════════════════════════"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|monitor|daemon|install}"
        echo ""
        echo "Commands:"
        echo "  start     - Start the server"
        echo "  stop      - Stop the server"
        echo "  restart   - Restart the server"
        echo "  status    - Check server status"
        echo "  monitor   - Monitor and auto-restart (foreground)"
        echo "  daemon    - Run monitor as background daemon"
        echo "  install   - Install remote restart capability"
        echo ""
        echo "Examples:"
        echo "  $0 install    # First time setup"
        echo "  $0 daemon     # Run in background"
        echo "  $0 status     # Check if running"
        ;;
esac
