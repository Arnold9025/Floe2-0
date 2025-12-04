import subprocess
import time
import datetime
import sys
import os

def run_script(script_name):
    print(f"\n[{datetime.datetime.now()}] Running {script_name}...")
    try:
        # Assuming script is in the same directory as this file
        script_path = os.path.join(os.path.dirname(__file__), script_name)
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Errors:\n{result.stderr}")
    except Exception as e:
        print(f"Failed to run {script_name}: {e}")

def main():
    print("=== Starting Slack Control Center Cycle ===")
    print("Note: Ensure 'interface/slack_server.py' is running and exposed via ngrok.")
    
    # 1. Import new leads from HubSpot
    run_script("import_leads.py")
    
    # 2. Check for replies (Sync Status)
    run_script("sync_email_history.py")
    
    # 3. Check for sent drafts (Advance Sequence)
    # Even though we have buttons, we still keep this as a safety net 
    # in case user sends manually from Gmail.
    run_script("sync_sent_emails.py")
    
    # 4. Generate new drafts & Send Slack Notifications
    run_script("process_sequence.py")
    
    print("\n=== Cycle Complete. Check Slack for Pending Approvals. ===")

if __name__ == '__main__':
    main()
