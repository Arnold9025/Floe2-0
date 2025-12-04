import sys
import json
import os

# Add parent dir to path if running directly or imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from execution.db import get_lead_by_email
from execution.hubspot_utils import log_note

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# from hubspot import HubSpot


def sync_event(event_type, data):
    """
    Syncs an event to HubSpot as a Note.
    """
    email = data.get('email')
    if not email:
        print("Error: Email required for CRM sync")
        return

    lead = get_lead_by_email(email)
    if not lead or not lead.get('hubspot_id'):
        print(f"Lead not found or no HubSpot ID for {email}")
        return

    note_body = f"Event: {event_type}\nData: {json.dumps(data, indent=2)}"
    
    try:
        note_id = log_note(lead['hubspot_id'], note_body)
        if note_id:
            print(f"Logged note to HubSpot for {email}. Note ID: {note_id}")
        else:
            print(f"Failed to log note for {email}")
    except Exception as e:
        print(f"Error syncing to CRM: {e}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python sync_crm.py <event_type> <json_data>")
        sys.exit(1)

    event_type = sys.argv[1]
    try:
        data = json.loads(sys.argv[2])
    except json.JSONDecodeError:
        print("Error: Invalid JSON data")
        sys.exit(1)

    try:
        sync_event(event_type, data)
    except Exception as e:
        print(f"Failed to sync to CRM: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
