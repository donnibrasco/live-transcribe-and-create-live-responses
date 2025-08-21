import os
import sys
import argparse
import requests


def main():
    ap = argparse.ArgumentParser(description="Send text to overlay server")
    ap.add_argument("text", nargs="+", help="Text to send")
    ap.add_argument("--server", default=os.environ.get("OVERLAY_SERVER", "http://127.0.0.1:3000"), help="Overlay server base URL")
    ap.add_argument("--user", default="PC", help="Username to display")
    args = ap.parse_args()

    text = " ".join(args.text).strip()
    if not text:
        print("Nothing to send.")
        return 1
    url = args.server.rstrip("/") + "/api/message"
    r = requests.post(url, json={"text": text, "user": args.user}, timeout=10)
    r.raise_for_status()
    print("sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
