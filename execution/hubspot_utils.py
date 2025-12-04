import os
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput
from hubspot.crm.objects.notes import SimplePublicObjectInputForCreate
from hubspot.crm.objects.notes import ApiException as NoteApiException
from dotenv import load_dotenv
import certifi
import datetime

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
os.environ['SSL_CERT_FILE'] = certifi.where()

def get_hubspot_client():
    access_token = os.getenv('HUBSPOT_ACCESS_TOKEN')
    if not access_token:
        raise ValueError("HUBSPOT_ACCESS_TOKEN not found in .env")
    return HubSpot(access_token=access_token)

def create_contact(lead_data):
    client = get_hubspot_client()
    properties = {
        "email": lead_data.get('email'),
        "firstname": lead_data.get('name', '').split(' ')[0],
        "lastname": ' '.join(lead_data.get('name', '').split(' ')[1:]) if ' ' in lead_data.get('name', '') else '',
        "phone": lead_data.get('phone'),
        "lifecyclestage": "lead"
    }
    
    try:
        simple_public_object_input = SimplePublicObjectInput(properties=properties)
        api_response = client.crm.contacts.basic_api.create(simple_public_object_input_for_create=simple_public_object_input)
        return api_response.id
    except Exception as e:
        # Check if it's a duplicate (409 conflict) - simplified check
        if "409" in str(e):
            print(f"Contact already exists or error: {e}")
            return None
        raise e

def log_note(contact_id, note_body):
    client = get_hubspot_client()
    properties = {
        "hs_timestamp": str(int(datetime.datetime.now().timestamp() * 1000)), 
        "hs_note_body": note_body
    }
    
    associations = [
        {
            "to": {"id": contact_id},
            "types": [
                {
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": 202
                }
            ]
        }
    ]
    
    try:
        note_input = SimplePublicObjectInputForCreate(properties=properties, associations=associations)
        note_response = client.crm.objects.notes.basic_api.create(simple_public_object_input_for_create=note_input)
        return note_response.id
    except Exception as e:
        print(f"Failed to log note: {e}")
        return None

def get_all_contacts():
    client = get_hubspot_client()
    try:
        # Get all contacts with email and firstname/lastname
        api_response = client.crm.contacts.basic_api.get_page(
            limit=100,
            properties=["email", "firstname", "lastname", "lifecyclestage", "company", "interest"],
            archived=False
        )
        return api_response.results
    except Exception as e:
        print(f"Error fetching contacts: {e}")
        return []

def update_contact_property(contact_id, property_name, value):
    client = get_hubspot_client()
    properties = {
        property_name: value
    }
    try:
        simple_public_object_input = SimplePublicObjectInput(properties=properties)
        api_response = client.crm.contacts.basic_api.update(
            contact_id=contact_id,
            simple_public_object_input=simple_public_object_input
        )
        return api_response
    except Exception as e:
        print(f"Error updating contact {contact_id}: {e}")
        return None
