#!/usr/bin/env python3
"""
Client-side Server Restart Utility
Allows macOS clients to restart the server remotely
"""

import requests
import sys
import time
import argparse

def restart_server(server_ip, port=8081, timeout=30):
    """Restart the server remotely"""
    try:
        restart_url = f"http://{server_ip}:{port}/restart"
        health_url = f"http://{server_ip}:8080/health"
        
        print(f"🔄 Requesting server restart...")
        print(f"📡 Restart endpoint: {restart_url}")
        
        # Send restart request
        response = requests.post(restart_url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result.get('message', 'Restart requested')}")
            
            # Wait and check if server comes back online
            print("⏳ Waiting for server to restart...")
            
            for i in range(timeout):
                try:
                    health_response = requests.get(health_url, timeout=5)
                    if health_response.status_code == 200:
                        print(f"✅ Server is back online! (took {i+1}s)")
                        return True
                except:
                    pass
                
                if i < timeout - 1:
                    print(f"⏳ Waiting... ({i+1}/{timeout}s)")
                    time.sleep(1)
            
            print("⚠️  Server restart requested but health check failed")
            return False
            
        else:
            print(f"❌ Restart request failed: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

def check_server_status(server_ip, main_port=8080, restart_port=8081):
    """Check both main server and restart service status"""
    print(f"📊 Checking server status at {server_ip}...")
    
    # Check main server
    try:
        main_response = requests.get(f"http://{server_ip}:{main_port}/health", timeout=5)
        if main_response.status_code == 200:
            print("✅ Main server is running")
            main_healthy = True
        else:
            print(f"⚠️  Main server responded with status: {main_response.status_code}")
            main_healthy = False
    except:
        print("❌ Main server is not responding")
        main_healthy = False
    
    # Check restart service
    try:
        restart_response = requests.get(f"http://{server_ip}:{restart_port}/health", timeout=5)
        if restart_response.status_code == 200:
            print("✅ Restart service is available")
            restart_available = True
        else:
            print("⚠️  Restart service responded with error")
            restart_available = False
    except:
        print("❌ Restart service is not available")
        restart_available = False
    
    return main_healthy, restart_available

def main():
    parser = argparse.ArgumentParser(description="Remote Server Management Utility")
    parser.add_argument("server_ip", help="Server IP address")
    parser.add_argument("--action", choices=["restart", "status"], default="status", 
                       help="Action to perform (default: status)")
    parser.add_argument("--timeout", type=int, default=30, 
                       help="Timeout for restart verification (default: 30s)")
    
    args = parser.parse_args()
    
    print("🖥️  Remote Server Management Utility")
    print(f"🎯 Target server: {args.server_ip}")
    print("─" * 40)
    
    if args.action == "status":
        main_healthy, restart_available = check_server_status(args.server_ip)
        
        if main_healthy and restart_available:
            print("\n🎉 Everything is working perfectly!")
        elif main_healthy:
            print("\n⚠️  Main server OK, but restart service unavailable")
        elif restart_available:
            print("\n⚠️  Main server down, but restart service available")
            print("💡 Try: python3 client_restart.py {} --action restart".format(args.server_ip))
        else:
            print("\n❌ Both services are down - manual intervention needed")
            
    elif args.action == "restart":
        main_healthy, restart_available = check_server_status(args.server_ip)
        
        if not restart_available:
            print("❌ Restart service is not available")
            sys.exit(1)
            
        success = restart_server(args.server_ip, timeout=args.timeout)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
