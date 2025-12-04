import os
import json
import subprocess
import sys

def run_command(command):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"Output: {result.stdout}")
    return result.stdout

def main():
    # 1. Test Lead Ingestion
    print("\n--- Testing Lead Ingestion ---")
    lead_data = {
        "email": "test@example.com",
        "name": "Test User",
        "source": "Website",
        "metadata": {"message": "I am interested in your services."}
    }
    lead_json = json.dumps(lead_data)
    output = run_command(f"python3 execution/ingest_lead.py '{lead_json}'")
    
    try:
        result = json.loads(output)
        lead_id = result.get('lead_id')
        print(f"Lead Ingested. ID: {lead_id}")
    except json.JSONDecodeError:
        print("Failed to parse ingestion output.")
        sys.exit(1)

    # 2. Test Intent Analysis (Mocking API Key if missing)
    print("\n--- Testing Intent Analysis ---")
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set. Expecting failure or mock response.")
    
    run_command(f"python3 execution/analyze_intent.py test@example.com")

    # 3. Test Email Sending (Mocking Creds if missing)
    print("\n--- Testing Email Sending ---")
    run_command(f"python3 execution/send_email.py test@example.com 'Welcome' 'Hello there!'")

    # 4. Test CRM Sync
    print("\n--- Testing CRM Sync ---")
    run_command(f"python3 execution/sync_crm.py 'email_sent' '{json.dumps({'subject': 'Welcome'})}'")

    # 5. Test Calendar Check
    print("\n--- Testing Calendar Check ---")
    run_command(f"python3 execution/manage_calendar.py check")

if __name__ == '__main__':
    main()
