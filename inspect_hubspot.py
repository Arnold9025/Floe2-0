import os
from hubspot import HubSpot
from dotenv import load_dotenv
import certifi

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
os.environ['SSL_CERT_FILE'] = certifi.where()

client = HubSpot(access_token=os.getenv('HUBSPOT_ACCESS_TOKEN'))
print(dir(client.crm.objects.notes))
try:
    print(dir(client.crm.associations))
except:
    print("No crm.associations")
