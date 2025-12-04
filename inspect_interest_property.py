import os
from hubspot import HubSpot
from dotenv import load_dotenv
import certifi

load_dotenv()
os.environ['SSL_CERT_FILE'] = certifi.where()

def list_properties():
    client = HubSpot(access_token=os.getenv('HUBSPOT_ACCESS_TOKEN'))
    try:
        response = client.crm.properties.core_api.get_all(object_type="contacts")
        for prop in response.results:
            if 'interest' in prop.name.lower() or 'service' in prop.name.lower() or 'category' in prop.name.lower():
                print(f"Name: {prop.name}, Label: {prop.label}, Type: {prop.type}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_properties()
