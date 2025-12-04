import os
import sys
import json
import threading
from flask import Flask, request, jsonify

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.db import get_db_connection, get_lead_by_email
from execution.send_email import send_message, get_service
from execution.hubspot_utils import update_contact_property
from execution.sync_crm import sync_event
from notifications.slack_notifier import notifier
import datetime

app = Flask(__name__)

# Verification token (Optional: Verify request comes from Slack)
# SLACK_VERIFICATION_TOKEN = os.getenv("SLACK_VERIFICATION_TOKEN")

from execution.process_sequence import create_sample_draft, execute_batch_blast, generate_generic_stage_content, request_stage_approval

def handle_approve_template(batch_id, response_url):
    """
    Phase 1 -> Phase 2: Template Approved, Create Sample.
    """
    print(f"Template for Batch {batch_id} approved. Creating sample...")
    
    draft_id, sample_email = create_sample_draft(batch_id)
    
    if not draft_id:
        return ":x: Error creating sample draft. Check logs."
        
    # Load content for preview
    try:
        filename = f"batch_{batch_id}.json"
        print(f"DEBUG: Attempting to read {filename}")
        with open(filename, "r") as f:
            batch_data = json.load(f)
            content = batch_data['content']
            print(f"DEBUG: Successfully read content: {content.keys()}")
            
            # Simple fill for preview
            preview_body = f"""Subject: {content['subject']}

Hi {sample_email.split('@')[0]},

{content['personalized_hook']}

{content['value_proposition']}

{content['cta_text']}

Best,
Arnold"""
    except Exception as e:
        print(f"DEBUG: Error reading batch file: {e}")
        preview_body = f"Preview unavailable (Error: {e})"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:white_check_mark: Template Approved for Batch {batch_id}*\nI've created a sample draft for *{sample_email}*.\n<{f'https://mail.google.com/mail/u/0/#drafts/{draft_id}'}|View Sample in Gmail>"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Sample Preview:*\n```\n{preview_body}\n```"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Does it look perfect? If yes, I will blast it to all leads in this stage."
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Confirm & Blast All",
                        "emoji": True
                    },
                    "style": "primary",
                    "value": batch_id,
                    "action_id": "confirm_blast"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Cancel",
                        "emoji": True
                    },
                    "style": "danger",
                    "value": batch_id,
                    "action_id": "cancel_blast"
                }
            ]
        }
    ]
    
    # We need to return the JSON structure for Slack to replace the message
    return {
        "replace_original": True,
        "blocks": blocks,
        "text": "Sample Draft Created"
    }

def handle_confirm_blast(batch_id):
    """
    Phase 2 -> Phase 3: Blast All.
    """
    print(f"Blasting Batch {batch_id}...")
    
    count = execute_batch_blast(batch_id)
    
    return f":rocket: *Blast Complete!* Sent {count} emails for Batch {batch_id}."

def handle_regenerate(stage):
    # Re-run generation
    # This is tricky because we need to update the message asynchronously.
    # For now, let's just say "Please run the script again" or try to call it.
    return ":arrows_counterclockwise: Regeneration not yet fully implemented via button. Please re-run the script."

import requests

@app.route('/slack/actions', methods=['POST'])
def slack_actions():
    payload = json.loads(request.form['payload'])
    
    # Handle Modal Submission
    if payload['type'] == 'view_submission':
        # Ack immediately to close modal
        # We can return "response_action": "update" to update the view, but we want to update the message.
        # So we just return empty 200 and do work in background.
        
        # Extract data
        metadata = json.loads(payload['view']['private_metadata'])
        batch_id = metadata['batch_id']
        response_url = metadata['response_url']
        feedback = payload['view']['state']['values']['feedback_block']['feedback_input']['value']
        
        def process_refine():
            handle_refine_submit(batch_id, feedback, response_url)
            
        thread = threading.Thread(target=process_refine)
        thread.start()
        
        return jsonify({"response_action": "clear"})

    # Handle Button Clicks
    if payload['type'] == 'block_actions':
        action = payload['actions'][0]
        action_id = action['action_id']
        action_value = action['value']
        response_url = payload['response_url']
        
        # Define a worker to handle the request asynchronously
        def process_action():
            response_data = None
            
            if action_id == 'approve_template':
                response_data = handle_approve_template(action_value, response_url)
            elif action_id == 'confirm_blast':
                text = handle_confirm_blast(action_value)
                response_data = {"replace_original": True, "text": text}
            elif action_id == 'cancel_blast':
                response_data = {"replace_original": True, "text": ":no_entry_sign: Blast Cancelled."}
            elif action_id == 'regenerate_template':
                text = handle_regenerate(action_value)
                response_data = {"replace_original": True, "text": text}
            elif action_id == 'refine_template':
                trigger_id = payload['trigger_id']
                open_refine_modal(trigger_id, action_value, response_url)
                
            if response_data:
                try:
                    requests.post(response_url, json=response_data)
                except Exception as e:
                    print(f"Error sending to response_url: {e}")

        thread = threading.Thread(target=process_action)
        thread.start()

        return "", 200
    
    return "", 200

def open_refine_modal(trigger_id, batch_id, response_url):
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("SLACK_BOT_TOKEN not found for modal")
        return

    # Store context in private_metadata
    metadata = json.dumps({
        "batch_id": batch_id,
        "response_url": response_url
    })

    view = {
        "type": "modal",
        "callback_id": "refine_submit",
        "private_metadata": metadata,
        "title": {"type": "plain_text", "text": "Refine Template"},
        "submit": {"type": "plain_text", "text": "Regenerate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "feedback_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "feedback_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "e.g., Make it more professional, mention our new AI feature..."}
                },
                "label": {"type": "plain_text", "text": "Feedback Instructions"}
            }
        ]
    }
    
    requests.post("https://slack.com/api/views.open", headers={"Authorization": f"Bearer {token}"}, json={"trigger_id": trigger_id, "view": view})

def handle_refine_submit(batch_id, feedback, response_url):
    print(f"Refining batch {batch_id} with feedback: {feedback}")
    
    # Load current batch to get details
    try:
        with open(f"batch_{batch_id}.json", "r") as f:
            batch_data = json.load(f)
    except:
        requests.post(response_url, json={"replace_original": False, "text": ":x: Error: Batch data not found."})
        return

    stage = batch_data['stage']
    interest = batch_data['interest']
    lead_count = batch_data['lead_count']
    
    # Regenerate content
    new_content = generate_generic_stage_content(stage, interest, feedback)
    
    if not new_content:
        requests.post(response_url, json={"replace_original": False, "text": ":x: Error regenerating content."})
        return
        
    # Update batch file
    batch_data['content'] = new_content
    with open(f"batch_{batch_id}.json", "w") as f:
        json.dump(batch_data, f)
        
    # Construct new blocks (Reuse logic from request_stage_approval, but we can't import it easily without circular deps or refactoring)
    # So we'll just reconstruct the blocks here.
    
    preview_text = f"""
*Subject:* {new_content['subject']}

Hi {{name}},

{new_content['personalized_hook']}

{new_content['value_proposition']}

{new_content['cta_text']}

*Best,*
*Arnold*
"""

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:mega: Batch Proposal for Stage {stage} ({interest})* ({lead_count} leads)\n*Refined based on:* _{feedback}_\nReview the new template below:"
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
                        "text": "Refine Again",
                        "emoji": True
                    },
                    "value": batch_id,
                    "action_id": "refine_template"
                }
            ]
        }
    ]
    
    # Update the original message
    requests.post(response_url, json={"replace_original": True, "blocks": blocks, "text": "Template Refined"})

@app.route('/', methods=['GET'])
def health_check():
    return "Slack Control Center is Running", 200

@app.route('/test-slack', methods=['GET', 'POST'])
def test_slack():
    success = notifier.send_message("Test notification from Slack Control Center!")
    if success:
        return "Notification sent!", 200
    else:
        return "Failed to send notification. Check logs.", 500

@app.route('/trigger-import', methods=['GET', 'POST'])
def trigger_import():
    try:
        # Run import_leads.py logic here or call it
        from execution.import_leads import main as import_main
        
        # Capture stdout to show user
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            import_main()
        
        output = f.getvalue()
        return f"<pre>{output}</pre>", 200
    except Exception as e:
        return f"Error running import: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
