import os
import sys
import json
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.db import get_db_connection, get_lead_by_email

def reset_lead_stage(email, stage=0):
    print(f"Resetting {email} to Stage {stage}...")
    
    lead = get_lead_by_email(email)
    if not lead:
        print("Lead not found.")
        return

    try:
        metadata = json.loads(lead['metadata']) if isinstance(lead['metadata'], str) else lead['metadata']
    except:
        metadata = {}
    
    # Update Stage
    metadata['sequence_stage'] = stage
    
    # Clear other flags that might block sending
    metadata.pop('last_contacted_at', None)
    metadata.pop('draft_created_for_stage', None)
    metadata.pop('pending_draft', None)
    metadata.pop('has_replied', None)
    metadata.pop('meeting_booked', None)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET metadata = ? WHERE id = ?", (json.dumps(metadata), lead['id']))
    
    # Also reset status if needed
    cursor.execute("UPDATE leads SET status = 'active' WHERE id = ?", (lead['id'],))
    
    conn.commit()
    conn.close()
    print("Success. Lead reset.")

if __name__ == "__main__":
    reset_lead_stage("petit.ange2604@gmail.com", 0)
