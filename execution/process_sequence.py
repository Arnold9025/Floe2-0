import json
import os
import datetime
import sys

# Add parent dir to path to import notifications
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.db import get_db_connection
from execution.send_email import create_draft, get_service, send_message
from execution.analyze_intent import analyze_lead
from execution.sync_crm import sync_event
from dotenv import load_dotenv
from execution.hubspot_utils import update_contact_property
from jinja2 import Template

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_active_leads():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch leads that are not disqualified or converted
    cursor.execute("SELECT * FROM leads WHERE status NOT IN ('disqualified', 'converted', 'unsubscribed')")
    rows = cursor.fetchall()
    conn.close()
    
    leads = []
    for row in rows:
        lead = dict(row)
        if lead.get('metadata') and isinstance(lead['metadata'], str):
            try:
                lead['metadata'] = json.loads(lead['metadata'])
            except:
                lead['metadata'] = {}
        leads.append(lead)
    return leads

from jinja2 import Template

# ... (imports)

from execution.google_docs_utils import get_document_text

# Cache company info to avoid fetching on every lead
COMPANY_INFO_CACHE = None

def get_company_info():
    global COMPANY_INFO_CACHE
    if COMPANY_INFO_CACHE:
        return COMPANY_INFO_CACHE
    
    doc_id = os.getenv("COMPANY_INFO_DOC_ID")
    if not doc_id:
        print("Warning: COMPANY_INFO_DOC_ID not set in .env")
        return "Quartier Digital is an AI automation agency."
        
    print(f"Fetching company info from Doc ID: {doc_id}...")
    text = get_document_text(doc_id)
    if text:
        COMPANY_INFO_CACHE = text
        return text
    return "Quartier Digital is an AI automation agency."

def generate_email_content(lead, stage):
    """
    Generates email content components using OpenAI.
    Returns JSON with: subject, personalized_hook, value_proposition, cta_text
    """
    
    company_info = get_company_info()
    
    # Simplified prompt for components
    prompt = f"""
    You are a sales expert representing 'Quartier Digital'.
    
    Here is information about OUR company and services:
    {company_info[:2000]}  # Limit context to first 2000 chars to save tokens if doc is huge
    
    Generate 4 components for a cold email to this lead.
    
    Lead Name: {lead.get('name')}
    Company: {lead.get('metadata', {}).get('company', 'their company')}
    Source: {lead.get('source')}
    Stage: {stage}
    
    Components needed:
    1. subject: A catchy, short subject line (under 6 words).
    2. personalized_hook: A 1-sentence opening that connects to them personally or their company.
    3. value_proposition: A 1-2 sentence pitch about how WE (Quartier Digital) help companies like theirs, based on the company info provided above.
    4. cta_text: A soft call to action (e.g., "Worth a quick chat?").
    
    Return JSON only.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful sales assistant AI."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content
        print(f"DEBUG: OpenAI Raw Content: {raw_content}")
        
        if not raw_content:
            print("Error: OpenAI returned empty content.")
            return None
            
        return json.loads(raw_content)
    except Exception as e:
        print(f"Error generating email: {e}")
        return None

# --- BATCH WORKFLOW FUNCTIONS ---

def get_leads_by_stage():
    """
    Returns a dict: {stage_int: [lead_dict, ...]}
    """
    leads = get_active_leads()
    grouped = {}
    
    for lead in leads:
        # Check suppression rules first
        metadata = lead.get('metadata', {})
        
        if lead.get('status') in ['converted', 'disqualified', 'unsubscribed']:
            continue
        if metadata.get('do_not_contact') or metadata.get('meeting_booked') or metadata.get('has_replied'):
            continue
            
        current_stage = metadata.get('sequence_stage', 0)
        last_contacted_str = metadata.get('last_contacted_at')
        
        # Determine if actionable
        should_email = False
        next_stage = current_stage + 1
        
        if current_stage == 0:
            should_email = True 
        elif last_contacted_str:
            last_contacted = datetime.datetime.fromisoformat(last_contacted_str)
            days_since = (datetime.datetime.now() - last_contacted).days
            
            if current_stage == 1 and days_since >= 2:
                should_email = True
            elif current_stage == 2 and days_since >= 4:
                should_email = True
            elif current_stage == 3 and days_since >= 5:
                should_email = True
        
        if should_email and next_stage <= 4:
            interest = metadata.get('interest', 'general')
            key = (next_stage, interest)
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(lead)
            
    return grouped

def generate_generic_stage_content(stage, interest="general", feedback=None):
    """
    Generates a GENERIC template for the stage and interest.
    """
    company_info = get_company_info()
    
    feedback_instruction = ""
    if feedback:
        feedback_instruction = f"\nIMPORTANT: The user provided specific feedback to refine this template: '{feedback}'. Please incorporate this feedback."

    prompt = f"""
    You are a sales expert representing 'Quartier Digital'.
    
    Here is information about OUR company and services:
    {company_info[:2000]}
    
    Generate a GENERIC email template for Stage {stage} of our outreach sequence.
    Target Audience Interest: {interest}
    {feedback_instruction}
    
    This template will be sent to multiple leads, so use placeholders like {{name}} and {{company}} where appropriate.
    Focus the value proposition specifically on {interest}.
    
    Components needed:
    1. subject: A catchy, short subject line (under 6 words).
    2. personalized_hook: A generic but engaging opening line (e.g., "I was checking out {{company}} and...")
    3. value_proposition: A strong pitch about how WE help companies like theirs with {interest}.
    4. cta_text: A soft call to action.
    
    Return JSON only.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful sales assistant AI."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = json.loads(response.choices[0].message.content)
        return content
    except Exception as e:
        print(f"Error generating generic content: {e}")
        return None

def request_stage_approval(stage, interest, content, lead_count):
    """
    Sends a Slack message proposing the template for the batch.
    """
    from notifications.slack_notifier import notifier
    
    # Save content to a temporary file/cache for the server to pick up?
    # Actually, we can embed it in the button value if small, or save to a file.
    # Saving to a file `batch_stage_{stage}_{interest}.json` is safest.
    # Sanitize interest for filename
    safe_interest = interest.replace(" ", "_").lower()
    batch_id = f"{stage}_{safe_interest}"
    
    batch_data = {
        "stage": stage,
        "interest": interest,
        "content": content,
        "lead_count": lead_count,
        "status": "pending_template"
    }
    
    with open(f"batch_{batch_id}.json", "w") as f:
        json.dump(batch_data, f)
        
    # Preview
    preview_text = f"""
*Subject:* {content['subject']}

Hi {{name}},

{content['personalized_hook']}

{content['value_proposition']}

{content['cta_text']}

*Best,*
*Arnold*
"""

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:mega: Batch Proposal for Stage {stage} ({interest})* ({lead_count} leads)\nReview the generic template below:"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": preview_text
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Approve Template",
                        "emoji": True
                    },
                    "style": "primary",
                    "value": batch_id,
                    "action_id": "approve_template"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Regenerate",
                        "emoji": True
                    },
                    "value": batch_id,
                    "action_id": "regenerate_template"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Refine (Feedback)",
                        "emoji": True
                    },
                    "value": batch_id,
                    "action_id": "refine_template"
                }
            ]
        }
    ]
    
    notifier.send_message(f"Batch Proposal for Stage {stage}", blocks=blocks)
    print(f"  Sent proposal for Stage {stage} ({lead_count} leads).")

def create_sample_draft(batch_id):
    """
    Creates a sample draft in Gmail for the user to verify.
    """
    # Load batch data
    try:
        with open(f"batch_{batch_id}.json", "r") as f:
            batch_data = json.load(f)
    except:
        print(f"Batch data not found for {batch_id}")
        return None, None

    stage = batch_data['stage']
    interest = batch_data['interest']
    content = batch_data['content']
    
    # Get 1 lead
    leads_by_group = get_leads_by_stage()
    leads = leads_by_group.get((stage, interest), [])
    if not leads:
        print("No leads found for sample.")
        return None
        
    sample_lead = leads[0]
    
    # Render
    try:
        template_path = os.path.join(os.path.dirname(__file__), '../templates/universal_template.html')
        with open(template_path, 'r') as f:
            template_str = f.read()
        
        template = Template(template_str)
        
        # Simple replacement for placeholders if they exist in content, 
        # BUT the content itself has {{name}}. Jinja might get confused if we double render.
        # Strategy: The content strings have {{name}}. We format them first, THEN pass to Jinja.
        
        def fill(text, lead):
            # Handle both {company} and {{company}}
            company = lead.get('metadata', {}).get('company', 'your company')
            name = lead.get('name', 'there')
            
            text = text.replace("{{name}}", name).replace("{name}", name)
            text = text.replace("{{company}}", company).replace("{company}", company)
            return text
            
        html_body = template.render(
            subject=content['subject'],
            name=sample_lead.get('name', 'there'),
            personalized_hook=fill(content['personalized_hook'], sample_lead),
            value_proposition=fill(content['value_proposition'], sample_lead),
            cta_text=fill(content['cta_text'], sample_lead),
            my_name="Arnold", 
            my_title="Founder",
            my_website="https://quartier-digital.com",
            unsubscribe_link="#"
        )
        
        # Create Draft
        service = get_service()
        # create_draft is already imported globally from execution.send_email
        draft = create_draft(service, "me", sample_lead['email'], f"[SAMPLE] {content['subject']}", html_body)
        
        # Save draft_id to batch file for later deletion
        batch_data['sample_draft_id'] = draft['id']
        with open(f"batch_{batch_id}.json", "w") as f:
            json.dump(batch_data, f)
            
        return draft['id'], sample_lead['email']
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error creating sample: {e}")
        return None, None

def execute_batch_blast(batch_id):
    """
    Sends emails to ALL leads in the stage/interest group.
    """
    # Load batch data
    try:
        with open(f"batch_{batch_id}.json", "r") as f:
            batch_data = json.load(f)
    except:
        return 0
        
    stage = batch_data['stage']
    interest = batch_data['interest']
    content = batch_data['content']
    
    leads_by_group = get_leads_by_stage()
    leads = leads_by_group.get((stage, interest), [])
    
    sent_count = 0
    service = get_service()
    
    template_path = os.path.join(os.path.dirname(__file__), '../templates/universal_template.html')
    with open(template_path, 'r') as f:
        template_str = f.read()
    template = Template(template_str)
    
    def fill(text, lead):
        # Handle both {company} and {{company}}
        company = lead.get('metadata', {}).get('company', 'your company')
        name = lead.get('name', 'there')
        
        text = text.replace("{{name}}", name).replace("{name}", name)
        text = text.replace("{{company}}", company).replace("{company}", company)
        return text

    for lead in leads:
        try:
            html_body = template.render(
                subject=content['subject'],
                name=lead.get('name', 'there'),
                personalized_hook=fill(content['personalized_hook'], lead),
                value_proposition=fill(content['value_proposition'], lead),
                cta_text=fill(content['cta_text'], lead),
                my_name="Arnold", 
                my_title="Founder",
                my_website="https://quartier-digital.com",
                unsubscribe_link="#"
            )
            
            send_message(service, "me", lead['email'], content['subject'], html_body)
            
            # Update DB
            metadata = lead.get('metadata', {})
            if isinstance(metadata, str): metadata = json.loads(metadata)
            
            metadata['sequence_stage'] = stage
            metadata['last_contacted_at'] = datetime.datetime.now().isoformat()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE leads SET metadata = ? WHERE id = ?", (json.dumps(metadata), lead['id']))
            conn.commit()
            conn.close()
            
            # Update HubSpot
            hubspot_status = "ATTEMPTED_TO_CONTACT"
            if stage == 4: hubspot_status = "UNQUALIFIED"
            if lead.get('hubspot_id'):
                 update_contact_property(lead['hubspot_id'], "hs_lead_status", hubspot_status)
            
            sent_count += 1
            print(f"  Sent to {lead['email']}")
            
        except Exception as e:
            print(f"  Failed to send to {lead['email']}: {e}")
            
    # Cleanup Sample Draft
    sample_draft_id = batch_data.get('sample_draft_id')
    if sample_draft_id:
        try:
            from execution.send_email import delete_draft
            delete_draft(service, "me", sample_draft_id)
            print(f"  Deleted sample draft {sample_draft_id}")
        except Exception as e:
            print(f"  Failed to delete sample draft: {e}")

    return sent_count

def main():
    print("--- Starting Batch Analysis ---")
    grouped_leads = get_leads_by_stage()
    
    if not grouped_leads:
        print("No actionable leads found.")
        return

    for key, leads in grouped_leads.items():
        stage, interest = key
        print(f"Stage {stage} ({interest}): {len(leads)} leads found.")
        
        # Generate Generic Content
        content = generate_generic_stage_content(stage, interest)
        if content:
            request_stage_approval(stage, interest, content, len(leads))

if __name__ == '__main__':
    main()
