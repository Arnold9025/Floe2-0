import os
from hubspot import HubSpot
from dotenv import load_dotenv
import certifi

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
os.environ['SSL_CERT_FILE'] = certifi.where()

client = HubSpot(access_token=os.getenv('HUBSPOT_ACCESS_TOKEN'))

def get_contact_properties(email):
    try:
        # Search for the contact
        public_object_search_request = {
            "filterGroups": [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}],
            "properties": ["hs_lead_status", "lifecyclestage", "email"],
            "limit": 1
        }
        response = client.crm.contacts.search_api.do_search(public_object_search_request=public_object_search_request)
        if response.results:
            print(f"Properties for {email}:")
            print(response.results[0].properties)
        else:
            print("Contact not found.")
    except Exception as e:
        print(f"Error: {e}")

# Use one of the emails from the screenshot or logs
get_contact_properties("devon@totalph.ca")
