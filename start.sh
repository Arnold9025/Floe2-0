#!/bin/bash

# Load Google Token
python3 execution/load_google_token.py

# Initialize DB (if needed, handled by app logic but good to ensure)
python3 execution/db.py 

# Start Daemon in Background
python3 execution/run_daemon.py &

# Start Web Server (Foreground)
# Use gunicorn for production
gunicorn interface.slack_server:app --bind 0.0.0.0:$PORT
