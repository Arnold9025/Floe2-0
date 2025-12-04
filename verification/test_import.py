import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.process_sequence import create_sample_draft, get_leads_by_stage

def test_import_error():
    print("Testing create_sample_draft...")
    # We need a stage with leads.
    # Let's assume stage 1 has leads (from logs).
    try:
        # We need to mock the batch file existence or ensure it exists.
        # But first let's see if it even gets to the import error.
        # If the error is "No module named 'send_email'", it might happen before file check if it's a lazy import? No.
        
        # Let's try to call it.
        # It will likely fail with "Batch data not found" if I don't create the file.
        # But if it fails with "No module named 'send_email'", then we reproduced it.
        
        create_sample_draft(1)
    except Exception as e:
        print(f"Caught exception: {e}")

if __name__ == "__main__":
    test_import_error()
