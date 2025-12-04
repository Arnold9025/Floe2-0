import os
import sys
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notifications.slack_notifier import notifier

def test_slack():
    print("--- Testing Slack Connection ---")
    
    # Reload env to be sure
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'), override=True)
    
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("ERROR: SLACK_WEBHOOK_URL is missing in .env file.")
        return

    print(f"Found Webhook URL: {webhook_url[:10]}...")
    
    print("Sending test message...")
    success = notifier.notify_info("Test Message: Slack Integration is Working! :rocket:")
    
    if success:
        print("SUCCESS: Message sent to Slack.")
    else:
        print("FAILURE: Could not send message. Check URL and internet connection.")

if __name__ == "__main__":
    test_slack()
