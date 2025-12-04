import os
import sys
import json

# Add parent dir to path to import notifications
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hubspot_utils import get_hubspot_client, get_all_contacts
from db import add_lead, get_lead_by_email, update_lead_hubspot_id, get_db_connection, execute_query
from execution.name_utils import normalize_name
from dotenv import load_dotenv

def get_all_local_leads():
    conn = get_db_connection()
    cursor = execute_query(conn, "SELECT id, email, hubspot_id, name, metadata FROM leads")
    rows = cursor.fetchall()
    conn.close()
    
    # Parse metadata JSON
    leads = {}
    for row in rows:
        d = dict(row)
        if isinstance(d['metadata'], str):
            try:
                d['metadata'] = json.loads(d['metadata'])
            except:
                d['metadata'] = {}
        leads[d['email']] = d
    return leads

def delete_local_lead(email):
    conn = get_db_connection()
    execute_query(conn, "DELETE FROM leads WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    print(f"  Deleted local lead: {email} (Removed from HubSpot)")

def main():
    print("--- Importing Leads from HubSpot ---")
    
    contacts = get_all_contacts()
    print(f"Fetched {len(contacts)} contacts from HubSpot.")
    
    local_leads_map = get_all_local_leads()
    hubspot_emails = set()
    
    new_count = 0
    updated_count = 0
    deleted_count = 0
    
    for contact in contacts:
        email = contact.properties.get('email')
        if not email:
            continue
        
        hubspot_emails.add(email)
        
        firstname = contact.properties.get('firstname', '')
        lastname = contact.properties.get('lastname', '')
        company = contact.properties.get('company', '')
        interest = contact.properties.get('interest', '')
        
        # Use Name Normalization
        name = normalize_name(firstname, lastname, email)
        hubspot_id = contact.id
        
        # Check if exists locally
        local_lead = local_leads_map.get(email)
        
        if local_lead:
            # Intelligent Sync: Check for updates
            updates_needed = False
            
            # 1. Check HubSpot ID
            if not local_lead.get('hubspot_id'):
                update_lead_hubspot_id(local_lead['id'], hubspot_id)
                updates_needed = True
                
            # 3. Check Company Change
            local_company = local_lead.get('metadata', {}).get('company', '')
            if company and local_company != company:
                print(f"  Updating company for {email}: {local_company} -> {company}")
                
                metadata = local_lead.get('metadata', {})
                metadata['company'] = company
                
                conn = get_db_connection()
                execute_query(conn, "UPDATE leads SET metadata = ? WHERE email = ?", (json.dumps(metadata), email))
                conn.commit()
                conn.close()
                updates_needed = True

            # 4. Check Interest Change
            local_interest = local_lead.get('metadata', {}).get('interest', '')
            if interest and local_interest != interest:
                print(f"  Updating interest for {email}: {local_interest} -> {interest}")
                
                metadata = local_lead.get('metadata', {})
                metadata['interest'] = interest
                
                conn = get_db_connection()
                execute_query(conn, "UPDATE leads SET metadata = ? WHERE email = ?", (json.dumps(metadata), email))
                conn.commit()
                conn.close()
                updates_needed = True
                
            # 2. Check Name Change (Simple check)
            if local_lead.get('name') != name:
                print(f"  Updating name for {email}: {local_lead.get('name')} -> {name}")
                # Update name in DB
                conn = get_db_connection()
                execute_query(conn, "UPDATE leads SET name = ? WHERE email = ?", (name, email))
                conn.commit()
                conn.close()
                updates_needed = True
            
            if updates_needed:
                updated_count += 1
        else:
            # Add new lead
            print(f"  Importing new lead: {email}")
            lead_data = {
                "email": email,
                "name": name,
                "source": "HubSpot Import",
                "metadata": {
                    "sequence_stage": 0, # Start at beginning
                    "company": company,
                    "interest": interest,
                    "imported_at": str(os.times())
                }
            }
            
            new_id = add_lead(lead_data)
            if new_id:
                update_lead_hubspot_id(new_id, hubspot_id)
                new_count += 1
                
                # Notify Slack via Notifier
                from notifications.slack_notifier import notifier
                notifier.send_message(f":new: New Lead Imported: *{name}* ({email})")
                
    # Handle Deletions
    # If a lead is in local_leads_map but NOT in hubspot_emails, delete it.
    for email in local_leads_map:
        if email not in hubspot_emails:
            delete_local_lead(email)
            deleted_count += 1
                
    print(f"Import Complete. New: {new_count}, Updated: {updated_count}, Deleted: {deleted_count}")

if __name__ == '__main__':
    main()
