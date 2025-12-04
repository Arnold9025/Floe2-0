import os
import sys
import json
from jinja2 import Template
from dotenv import load_dotenv
from openai import OpenAI

# Add parent dir
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.db import get_db_connection
from execution.send_email import get_service, create_draft

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_test_lead():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Get a lead that hasn't been contacted yet
    cursor.execute("SELECT * FROM leads WHERE status='new' LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        lead = dict(row)
        if lead.get('metadata') and isinstance(lead['metadata'], str):
            try:
                lead['metadata'] = json.loads(lead['metadata'])
            except:
                lead['metadata'] = {}
        return lead
    return None

from execution.google_docs_utils import get_document_text

def get_company_info():
    doc_id = os.getenv("COMPANY_INFO_DOC_ID")
    if not doc_id:
        return "Quartier Digital is an AI automation agency."
    print(f"Fetching company info from Doc ID: {doc_id}...")
    return get_document_text(doc_id) or "Quartier Digital is an AI automation agency."

def generate_content(lead):
    company_info = get_company_info()
    
    prompt = f"""
    You are a sales expert representing 'Quartier Digital'.
    
    Here is information about OUR company and services:
    {company_info[:2000]}
    
    Generate 4 specific components for a cold email to this lead.
    
    Lead Name: {lead.get('name')}
    Company: {lead.get('metadata', {}).get('company', 'their company')}
    Source: {lead.get('source')}
    
    Components needed:
    1. subject: A catchy, short subject line (under 6 words).
    2. personalized_hook: A 1-sentence opening that connects to them personally or their company.
    3. value_proposition: A 1-2 sentence pitch about how WE help companies like theirs, based on the company info provided.
    4. cta_text: A soft call to action (e.g., "Worth a quick chat?").
    
    Return JSON only.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

def main():
    lead = get_test_lead()
    if not lead:
        print("No new leads found to test.")
        return

    print(f"Generating draft for: {lead['email']}")
    content = generate_content(lead)
    
    if not content:
        print("Failed to generate content.")
        return
        
    print("Generated Content:")
    print(json.dumps(content, indent=2))
    
    # Load Template
    template_path = os.path.join(os.path.dirname(__file__), '../templates/universal_template.html')
    with open(template_path, 'r') as f:
        template_str = f.read()
    
    template = Template(template_str)
    html_body = template.render(
        subject=content['subject'],
        name=lead.get('name', 'there'),
        personalized_hook=content['personalized_hook'],
        value_proposition=content['value_proposition'],
        cta_text=content['cta_text'],
        my_name="Arnold", 
        my_title="Founder",
        my_website="https://quartier-digital.com",
        unsubscribe_link="#"
    )
    
    service = get_service()
    # Note: create_draft now defaults to content_type='html'
    draft = create_draft(service, "me", lead['email'], content['subject'], html_body)
    
    if draft:
        print(f"SUCCESS: Draft created! ID: {draft['id']}")
        print(f"Please check your Gmail Drafts folder for an email to {lead['email']}")
    else:
        print("FAILURE: Could not create draft.")

if __name__ == "__main__":
    main()
