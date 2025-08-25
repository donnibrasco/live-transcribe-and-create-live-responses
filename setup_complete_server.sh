#!/bin/bash
# Complete Server Setup - Background running + Auto-restart + Remote control

echo "🚀 Setting up Complete Server Management System..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make scripts executable
chmod +x "$SCRIPT_DIR/server_manager.sh"
chmod +x "$SCRIPT_DIR/client_restart.py"

echo "✅ Scripts made executable"

# Install server manager
echo "📦 Installing server manager..."
"$SCRIPT_DIR/server_manager.sh" install

# Create systemd service (optional)
echo ""
echo "🔧 System Service Setup (Optional)"
echo "─────────────────────────────────"
echo "To run server as a system service that starts on boot:"
echo ""
echo "1. Copy service file:"
echo "   sudo cp transcription-server.service /etc/systemd/system/"
echo ""
echo "2. Enable and start service:"
echo "   sudo systemctl enable transcription-server"
echo "   sudo systemctl start transcription-server"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status transcription-server"

# Start the background daemon
echo ""
echo "🎯 Starting Background Daemon..."
"$SCRIPT_DIR/server_manager.sh" daemon

# Start restart service
echo ""
echo "🔄 Starting Remote Restart Service..."
cd "$SCRIPT_DIR"
nohup python3 restart_server.py > restart_service.log 2>&1 &
echo $! > restart_service.pid
echo "✅ Restart service started (PID: $(cat restart_service.pid))"

# Show status
sleep 3
"$SCRIPT_DIR/server_manager.sh" status

echo ""
echo "🎉 Complete Setup Finished!"
echo "═══════════════════════════"
echo ""
echo "📊 What's Running:"
echo "  🎤 Main Server: http://$(hostname -I | awk '{print $1}'):8080"
echo "  🔄 Restart Service: http://$(hostname -I | awk '{print $1}'):8081"
echo "  👁️  Auto-restart Monitor: Running in background"
echo ""
echo "🎛️  Control Commands:"
echo "  ./server_manager.sh status    - Check status"
echo "  ./server_manager.sh restart   - Manual restart"
echo "  ./server_manager.sh stop      - Stop everything"
echo ""
echo "🖥️  Client Commands (from macOS):"
echo "  python3 client_restart.py $(hostname -I | awk '{print $1}') --action status"
echo "  python3 client_restart.py $(hostname -I | awk '{print $1}') --action restart"
echo ""
echo "📱 URLs for clients:"
echo "  Overlay: http://$(hostname -I | awk '{print $1}'):8080/overlay"
echo "  Health: http://$(hostname -I | awk '{print $1}'):8080/health"
echo "  Restart: curl -X POST http://$(hostname -I | awk '{print $1}'):8081/restart"
