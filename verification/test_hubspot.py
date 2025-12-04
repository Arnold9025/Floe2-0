import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

def main():
    print("--- Verifying HubSpot Configuration ---")
    token = os.getenv('HUBSPOT_ACCESS_TOKEN')
    if not token:
        print("Error: HUBSPOT_ACCESS_TOKEN not found in .env")
        print("Please add it to run the full integration.")
        sys.exit(1)
    
    print("HUBSPOT_ACCESS_TOKEN found.")
    
    # We could try a real API call here, but let's just run the ingestion script
    # which now uses the real client.
    print("\n--- Testing Lead Ingestion with HubSpot ---")
    # This will fail if the token is invalid, which is good for verification.
    import subprocess
    result = subprocess.run(
        ["python3", "execution/ingest_lead.py", '{"email": "hubspot_test@example.com", "name": "HubSpot Test", "source": "Verification"}'],
        capture_output=True, text=True
    )
    
    print("Output:", result.stdout)
    print("Errors:", result.stderr)
    
    if result.returncode != 0:
        print("Ingestion failed.")
    else:
        print("Ingestion script ran successfully (check stderr for sync result).")

if __name__ == '__main__':
    main()
