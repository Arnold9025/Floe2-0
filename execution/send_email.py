import os.path
import base64
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from execution.google_auth import get_credentials

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_service():
    creds = get_credentials()
    return build('gmail', 'v1', credentials=creds)

def send_message(service, sender, to, subject, message_text, content_type='html'):
    message = MIMEText(message_text, content_type)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw}

    try:
        message = (service.users().messages().send(userId="me", body=body).execute())
        print(f'Message Id: {message["id"]}')
        return message
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def create_draft(service, sender, to, subject, message_text, content_type='html'):
    """Create a draft email."""
    message = MIMEText(message_text, content_type)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'message': {'raw': raw}}

    try:
        draft = service.users().drafts().create(userId="me", body=body).execute()
        print(f'Draft Id: {draft["id"]}')
        return draft
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def delete_draft(service, user_id, draft_id):
    """Delete a draft."""
    try:
        service.users().drafts().delete(userId=user_id, id=draft_id).execute()
        print(f'Draft Id: {draft_id} Deleted')
    except HttpError as error:
        print(f'An error occurred: {error}')

def main():
    if len(sys.argv) < 4:
        print("Usage: python send_email.py <to_email> <subject> <body>")
        sys.exit(1)

    to_email = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]

    try:
        service = get_service()
        send_message(service, "me", to_email, subject, body)
    except Exception as e:
        print(f"Failed to send email: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
