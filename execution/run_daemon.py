import time
import datetime
import subprocess
import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_cycle():
    print(f"\n[{datetime.datetime.now()}] Starting Cycle...")
    try:
        script_path = os.path.join(os.path.dirname(__file__), "run_cycle.py")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Errors:\n{result.stderr}")
    except Exception as e:
        print(f"Failed to run cycle: {e}")

def main():
    print("=== AI Follow-Up Daemon Started ===")
    print("Running cycle every 12 hours (43200 seconds).")
    print("Press Ctrl+C to stop.")
    
    while True:
        run_cycle()
        
        print(f"[{datetime.datetime.now()}] Cycle finished. Sleeping for 12 hours...")
        try:
            time.sleep(43200) # 12 hours
        except KeyboardInterrupt:
            print("\nDaemon stopped by user.")
            break

if __name__ == "__main__":
    main()
