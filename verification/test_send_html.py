import os
import sys
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.send_email import get_service, send_message

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

def test_send_html():
    print("--- Testing HTML Email Sending ---")
    
    # Use a hardcoded test email or one from args
    to_email = "adadjisso.arnold@gmail.com" # Using the user's email from logs
    subject = "Test HTML Email from Script"
    
    html_body = """
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h1 style="color: #0066cc;">This is a Test HTML Email</h1>
        <p>If you see this rendered correctly (blue header, formatted text), then the HTML sending logic is working.</p>
        <p><strong>Bold Text</strong> and <em>Italic Text</em>.</p>
        <hr>
        <p style="font-size: 12px; color: #777;">Sent via verification/test_send_html.py</p>
    </body>
    </html>
    """
    
    try:
        service = get_service()
        print(f"Sending to {to_email}...")
        send_message(service, "me", to_email, subject, html_body)
        print("Sent successfully.")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_send_html()
