import os
import sys
import requests
import json
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

def debug_slack():
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    print("--- Debugging Slack Webhook ---")
    
    if not webhook_url:
        print("ERROR: SLACK_WEBHOOK_URL is NOT set in .env")
        return
        
    print(f"Webhook URL found: {webhook_url[:30]}...")
    
    payload = {
        "text": "Test message from debug_slack.py :rocket:",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Test Message* from debug script.\nIf you see this, the webhook works."
                }
            }
        ]
    }
    
    try:
        print("Sending request...")
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Slack accepted the request.")
        else:
            print("FAILURE: Slack rejected the request.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    debug_slack()
