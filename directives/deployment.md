# Deployment Instructions

## Overview
This project is configured for deployment on Railway (or similar PaaS).

## Configuration
- **Procfile**: Defines the `web` process running `start.sh`.
- **start.sh**:
  - Loads Google Token (`execution/load_google_token.py`)
  - Starts the Daemon (`execution/run_daemon.py`) in the background.
  - Starts the Web Server (`interface.slack_server:app`) using `gunicorn`.

## Environment Variables
Ensure the following are set in your deployment environment:
- `PORT` (automatically set by Railway)
- `GOOGLE_CREDENTIALS` (JSON string or path, depending on `load_google_token.py` implementation)
- `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` (if applicable)

## Steps
1. Push to GitHub.
2. Connect GitHub repo to Railway.
3. Configure Environment Variables.
4. Deploy.
