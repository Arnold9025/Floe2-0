import sys
import json
import os
from dotenv import load_dotenv
from db import init_db, add_lead, get_lead_by_email, update_lead_hubspot_id

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from hubspot_utils import create_contact

def sync_to_hubspot(lead_data):
    """
    Syncs the lead data to HubSpot.
    Returns the HubSpot Contact ID.
    """
    try:
        contact_id = create_contact(lead_data)
        if contact_id:
            sys.stderr.write(f"Synced {lead_data.get('email')} to HubSpot. ID: {contact_id}\n")
            return contact_id
        else:
            sys.stderr.write(f"Failed to sync {lead_data.get('email')} to HubSpot (Duplicate or Error)\n")
            return "duplicate_or_error"
    except Exception as e:
        sys.stderr.write(f"Error syncing to HubSpot: {e}\n")
        return None

def main():
    # Ensure DB is initialized
    init_db()

    # Read input from stdin or argument
    if len(sys.argv) > 1:
        try:
            lead_data = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print("Error: Invalid JSON argument")
            sys.exit(1)
    else:
        # Read from stdin
        try:
            input_str = sys.stdin.read()
            if not input_str:
                print("Error: No input provided")
                sys.exit(1)
            lead_data = json.loads(input_str)
        except json.JSONDecodeError:
            print("Error: Invalid JSON from stdin")
            sys.exit(1)

    # Validation
    if 'email' not in lead_data:
        print("Error: Email is required")
        sys.exit(1)

    # Check for duplicate locally
    existing_lead = get_lead_by_email(lead_data['email'])
    if existing_lead:
        sys.stderr.write(f"Lead already exists: {existing_lead['id']}\n")
        # Ideally we would update the existing lead here
        print(json.dumps({"status": "duplicate", "lead_id": existing_lead['id']}))
        return

    # Save locally
    local_id = add_lead(lead_data)
    if not local_id:
        print("Error: Failed to save lead locally")
        sys.exit(1)

    # Sync to HubSpot
    try:
        hubspot_id = sync_to_hubspot(lead_data)
        update_lead_hubspot_id(local_id, hubspot_id)
    except Exception as e:
        print(f"Warning: Failed to sync to HubSpot: {e}")
        # Continue anyway, we have it locally

    print(json.dumps({
        "status": "success",
        "lead_id": local_id,
        "hubspot_id": hubspot_id
    }))

if __name__ == '__main__':
    main()
