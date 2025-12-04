import os
import json
import time
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SlackNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not set. Notifications will be skipped.")

    def send_message(self, text, blocks=None, retries=3):
        """
        Sends a message to Slack with retry logic.
        """
        if not self.webhook_url:
            logger.error("Cannot send Slack notification: No Webhook URL configured.")
            return False

        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        for attempt in range(retries):
            try:
                response = requests.post(
                    self.webhook_url,
                    data=json.dumps(payload),
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                response.raise_for_status()
                logger.info("Slack notification sent successfully.")
                return True
            except requests.exceptions.RequestException as e:
                wait_time = 2 ** attempt
                logger.warning(f"Slack send failed (Attempt {attempt + 1}/{retries}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        logger.error("Failed to send Slack notification after multiple attempts.")
        return False

    def notify_info(self, message):
        """Alias for send_message to maintain compatibility with events.py"""
        return self.send_message(f":information_source: {message}")

    def notify_error(self, message):
        """Alias for send_message with error formatting"""
        return self.send_message(f":warning: *Error:* {message}")

# Singleton instance
notifier = SlackNotifier()

if __name__ == "__main__":
    # Test
    notifier.send_message("Test notification from SlackNotifier class.")
