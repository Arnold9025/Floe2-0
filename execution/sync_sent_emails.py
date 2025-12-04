import os
import json
import datetime
import sys

# Add parent dir to path to import notifications
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_db_connection
from send_email import get_service
from hubspot_utils import update_contact_property
from sync_crm import sync_event
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

def get_sent_messages(service, to_email):
    """Get messages sent to a specific email."""
    try:
        query = f"to:{to_email} label:SENT"
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        return messages
    except Exception as e:
        print(f"Error fetching sent messages: {e}")
        return []

def get_message_details(service, msg_id):
    try:
        msg = service.users().messages().get(userId='me', id=msg_id).execute()
        payload = msg['payload']
        headers = payload.get('headers')
        date_header = next(h['value'] for h in headers if h['name'] == 'Date')
        # Parse date (simplified) - Gmail date format is complex, using a library or robust parsing is better
        # For now, we rely on internalDate which is timestamp in ms
        internal_date = int(msg['internalDate']) / 1000
        return internal_date
    except Exception as e:
        print(f"Error fetching message details: {e}")
        return 0

def main():
    print("--- Syncing Sent Emails ---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE status NOT IN ('disqualified', 'converted', 'unsubscribed')")
    rows = cursor.fetchall()
    
    service = get_service()
    
    for row in rows:
        lead = dict(row)
        email = lead['email']
        
        if not lead.get('metadata'):
            continue
            
        try:
            metadata = json.loads(lead['metadata'])
        except:
            continue
            
        draft_stage = metadata.get('draft_created_for_stage')
        
        if not draft_stage:
            continue
            
        print(f"Checking if draft for Stage {draft_stage} was sent to {email}...")
        
        # Check Sent folder
        messages = get_sent_messages(service, email)
        if not messages:
            print("  No sent messages found.")
            continue
            
        # Get latest sent message time
        latest_msg = messages[0]
        sent_time = get_message_details(service, latest_msg['id'])
        
        # If sent recently (e.g., after the draft was created or simply check if it exists)
        # A robust way is to check if sent_time > last_contacted_at (if it exists)
        # But since we only create draft when due, any recent sent email likely corresponds to it.
        # Let's assume if we find a sent email within the last 24 hours (or since draft creation), it's the one.
        
        # Simplified logic: If we have a 'draft_created_for_stage' and we see a sent email 
        # that is NEWER than the previous 'last_contacted_at', then it's sent.
        
        # Safety Check: Detect ANY sent email since last contact
        # If we find an email that is NOT the draft we expected (or even if it is),
        # we treat it as a "Contact Event".
        
        last_contacted_str = metadata.get('last_contacted_at')
        last_contacted_ts = 0
        if last_contacted_str:
            last_contacted_ts = datetime.datetime.fromisoformat(last_contacted_str).timestamp()
            
        if sent_time > last_contacted_ts:
            print(f"  Found sent email! (Time: {datetime.datetime.fromtimestamp(sent_time)})")
            
            # Logic:
            # If we had a draft pending for Stage X, and we see a sent email, we assume Stage X is done.
            # If we DIDN'T have a draft pending, but we see a sent email, it means the user sent something manually.
            # In that case, we should probably just advance the 'last_contacted_at' so we don't send the next auto-email too soon.
            
            new_stage = draft_stage if draft_stage else metadata.get('sequence_stage', 0)
            
            # If it was a manual send unrelated to the draft, we might want to skip the current stage?
            # For now, let's just update timestamp and clear the draft flag if it exists.
            
            metadata['last_contacted_at'] = datetime.datetime.fromtimestamp(sent_time).isoformat()
            
            if draft_stage:
                print(f"  Matched pending draft for Stage {draft_stage}.")
                metadata['sequence_stage'] = draft_stage
                metadata.pop('draft_created_for_stage', None) # Clear flag
                
                # Update HubSpot Status for Stage Advance
                hubspot_status = "ATTEMPTED_TO_CONTACT"
                if draft_stage == 4:
                    hubspot_status = "UNQUALIFIED"
                
                if lead.get('hubspot_id'):
                     print(f"  Updating HubSpot Status to {hubspot_status}...")
                     update_contact_property(lead['hubspot_id'], "hs_lead_status", hubspot_status)
            else:
                print("  Detected manual email (no draft pending). Updating last_contacted_at.")
                # Optional: Increment stage or just wait? 
                # If user sent a manual email, maybe we consider that "Stage X" done?
                # Let's just update timestamp. The next auto-email will be delayed by the cadence logic.
            
            # Update DB
            cursor.execute("UPDATE leads SET metadata = ? WHERE id = ?", (json.dumps(metadata), lead['id']))
            conn.commit()
            
            # Sync to HubSpot
            sync_event("Email Sent", {
                "email": email,
                "stage": new_stage,
                "note": "Detected sent email (Manual or Draft)."
            })
            
            # Notify Slack
            from notifications.events import email_sent, sequence_advanced
            email_sent(lead, new_stage)
            if draft_stage:
                sequence_advanced(lead, new_stage)
                 
            print("  Lead updated.")
        else:
            print("  No new sent email detected.")
            
    conn.close()

if __name__ == '__main__':
    main()
