from notifications.slack_notifier import notifier

def lead_imported(lead):
    """
    Triggered when a new lead is imported from HubSpot.
    """
    msg = f"New Lead Imported: *{lead.get('name', 'Unknown')}* ({lead.get('email')})"
    notifier.notify_info(msg)

def draft_created(lead, stage):
    """
    Triggered when a draft email is created.
    """
    msg = f"New Draft Created — Lead: *{lead.get('name', 'Unknown')}* (Stage {stage})"
    notifier.notify_info(msg)

def email_sent(lead, stage=None):
    """
    Triggered when a user sends a draft.
    """
    stage_info = f"(Stage {stage})" if stage else ""
    msg = f"Email Sent manually :white_check_mark: — Lead: *{lead.get('name', 'Unknown')}* {stage_info}"
    notifier.notify_info(msg)

def reply_detected(lead, reply_status):
    """
    Triggered when a reply is detected and classified.
    """
    icon = ":speech_balloon:"
    if reply_status == "Interested":
        icon = ":rocket:"
    elif reply_status == "Not Interested":
        icon = ":hand:"
        
    msg = f"{icon} Reply Detected — Lead: *{lead.get('name', 'Unknown')}* — Status: *{reply_status}*"
    notifier.notify_info(msg)

def sequence_advanced(lead, new_stage):
    """
    Triggered when a lead moves to the next stage.
    """
    msg = f"Sequence Advanced :arrow_right: Lead: *{lead.get('name', 'Unknown')}* is now at Stage {new_stage}"
    notifier.notify_info(msg)

def error_occurred(error_msg, context="General"):
    """
    Triggered when an error occurs.
    """
    msg = f"Error in {context}: {error_msg}"
    notifier.notify_error(msg)
