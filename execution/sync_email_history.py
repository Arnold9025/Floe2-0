import os
import json
import datetime
import sys

# Add parent dir to path to import notifications
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from dotenv import load_dotenv
from hubspot_utils import get_hubspot_client, update_contact_property, get_all_contacts
from send_email import get_service
from db import get_db_connection

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_latest_email_content(service, email_address):
    """
    Searches for the latest email thread with the given address.
    Returns the content of the last message.
    """
    try:
        # Search for messages from or to the email
        query = f"from:{email_address} OR to:{email_address}"
        results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return None
            
        # Get full message details
        msg_id = messages[0]['id']
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        
        # Extract snippet or body
        snippet = message.get('snippet', '')
        
        # Check if it was sent BY the lead (incoming)
        headers = message['payload']['headers']
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        
        is_from_lead = email_address.lower() in sender.lower()
        
        return {
            "content": snippet,
            "is_from_lead": is_from_lead,
            "date": next((h['value'] for h in headers if h['name'] == 'Date'), '')
        }
        
    except Exception as e:
        print(f"Error checking Gmail for {email_address}: {e}")
        return None

def analyze_status(email_content):
    """
    Uses LLM to determine the status based on the email content.
    """
    prompt = f"""
    Analyze the following email content from a lead and determine their status.
    
    Email Content: "{email_content}"
    
    Possible Statuses:
    - "Replied" (General reply)
    - "Interested" (Positive reply)
    - "Not Interested" (Negative reply)
    - "Meeting Booked" (If they confirm a time)
    - "No Change" (If the content is irrelevant or just an auto-reply)
    
    Return ONLY the status string.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a sales operations assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error analyzing status: {e}")
        return "No Change"

def analyze_sent_email(email_content):
    """
    Analyzes an email WE sent to determine the stage/status.
    """
    prompt = f"""
    Analyze the following email that WAS SENT TO a lead. Determine what stage of outreach this represents.
    
    Email Content: "{email_content}"
    
    Possible Statuses:
    - "New" (If it looks like a first touch/intro)
    - "Attempted to Contact" (If it's a follow-up)
    - "Connected" (If we are replying to them)
    
    Return ONLY the status string.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a sales operations assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error analyzing sent email: {e}")
        return "No Change"

def main():
    print("--- Syncing Email History to HubSpot ---")
    
    # 1. Get all contacts from HubSpot
    contacts = get_all_contacts()
    print(f"Found {len(contacts)} contacts in HubSpot.")
    
    # 2. Initialize Gmail Service
    try:
        service = get_service()
    except Exception as e:
        print(f"Failed to connect to Gmail: {e}")
        sys.exit(1)
        
    for contact in contacts:
        email = contact.properties.get('email')
        if not email:
            continue
            
        print(f"Checking history for {email}...")
        
        # 3. Get latest email
        latest_email = get_latest_email_content(service, email)
        
        if not latest_email:
            print("  No email history found.")
            continue
            
        hubspot_property = "hs_lead_status"
        hubspot_value = None
        new_status = "No Change"

        if latest_email['is_from_lead']:
            # THEY replied
            print(f"  Found reply from lead: '{latest_email['content'][:50]}...'")
            new_status = analyze_status(latest_email['content'])
            print(f"  Analyzed Reply Status: {new_status}")
            
            # Notify Slack
            from notifications.events import reply_detected
            # We need to pass a lead dict, but we only have contact object here.
            # We can construct a minimal lead dict or fetch from DB.
            # Since we fetch local_lead below, let's do it there or construct one.
            lead_info = {"name": contact.properties.get('firstname', 'Unknown'), "email": email}
            reply_detected(lead_info, new_status)
            
            # Update Local DB Metadata for Suppression
            # Fetch current metadata to update it
            # We need to get the lead from DB first.
            # Since we iterate contacts from HubSpot, we need to find the local lead by email.
            from db import get_lead_by_email, get_db_connection
            import json
            
            local_lead = get_lead_by_email(email)
            if local_lead:
                metadata = local_lead.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                # Always mark as replied
                metadata['has_replied'] = True
                
                if new_status == "Interested":
                    hubspot_value = "OPEN_DEAL"
                elif new_status == "Meeting Booked":
                    hubspot_value = "CONNECTED"
                    metadata['meeting_booked'] = True
                elif new_status == "Not Interested":
                    hubspot_value = "UNQUALIFIED"
                elif new_status == "Unsubscribe":
                    hubspot_value = "UNQUALIFIED"
                    metadata['do_not_contact'] = True
                elif new_status == "Wrong Person":
                    hubspot_value = "UNQUALIFIED"
                elif new_status == "Ooo":
                    print("  Out of Office. No status change.")
                    continue
                else:
                    hubspot_value = "CONNECTED"

                # Save metadata to DB
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE leads SET metadata = ? WHERE id = ?", (json.dumps(metadata), local_lead['id']))
                conn.commit()
                conn.close()
            else:
                print(f"  Warning: Lead {email} not found locally. Skipping metadata update.")
                # Still update HubSpot below
                if new_status == "Interested": hubspot_value = "OPEN_DEAL"
                elif new_status == "Meeting Booked": hubspot_value = "CONNECTED"
                elif new_status == "Not Interested": hubspot_value = "UNQUALIFIED"
                elif new_status == "Unsubscribe": hubspot_value = "UNQUALIFIED"
                elif new_status == "Wrong Person": hubspot_value = "UNQUALIFIED"
                else: hubspot_value = "CONNECTED"

        else:
            # WE sent the last email (No reply yet)
            print(f"  Last email was sent BY US: '{latest_email['content'][:50]}...'")
            new_status = analyze_sent_email(latest_email['content'])
            print(f"  Analyzed Sent Status: {new_status}")
            
            if new_status == "New":
                hubspot_value = "NEW"
            elif new_status == "Attempted to Contact":
                hubspot_value = "ATTEMPTED_TO_CONTACT"
            elif new_status == "Connected":
                hubspot_value = "CONNECTED"

        if hubspot_value:
            # Only update if it's different (optional optimization, but good to just set it)
            print(f"  Updating HubSpot {hubspot_property} to {hubspot_value}...")
            update_contact_property(contact.id, hubspot_property, hubspot_value)
        else:
            print(f"  Status '{new_status}' does not map to a status change.")

if __name__ == '__main__':
    main()
