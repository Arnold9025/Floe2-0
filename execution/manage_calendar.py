import os.path
import sys
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_service():
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), '../token.json')
    creds_path = os.path.join(os.path.dirname(__file__), '../credentials.json')
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"Credentials file not found at {creds_path}")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def check_availability(service, time_min, time_max):
    print(f"Checking availability from {time_min} to {time_max}...")
    events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                          timeMax=time_max, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        return True
    
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])
    
    return False # Simplified logic

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_calendar.py <action> [args]")
        sys.exit(1)

    action = sys.argv[1]
    service = get_service()

    if action == 'check':
        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        check_availability(service, now, None)
    else:
        print(f"Unknown action: {action}")

if __name__ == '__main__':
    main()
