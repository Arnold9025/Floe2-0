# Directive: Follow-Up Sequence

## Goal
Manage the lifecycle of a lead through a multi-touch email sequence until they reply, book a meeting, or the sequence ends.

## Inputs
- `lead_id`: The ID of the lead to process.
- `current_stage`: The current step in the sequence (e.g., 1, 2, 3).

## Tools / Scripts
- `execution/check_reply.py` (or `sync_crm.py`): Checks HubSpot/Gmail for replies.
- `execution/generate_email.py`: Drafts the content using OpenAI.
- `execution/send_email.py`: Sends the email via Gmail API.
- `execution/manage_calendar.py`: Checks Google Calendar for booked meetings.

## Procedure
1. **Pre-Flight Check**
   - Check if lead has **Replied** or **Booked a Meeting** (via HubSpot/Gmail/Calendar).
   - If YES: **Stop Sequence**. Update status to "Engaged" or "Converted". Exit.

2. **Generate Content**
   - Run `execution/generate_email.py` with `lead_id` and `current_stage`.
   - OpenAI generates personalized subject and body based on:
     - Lead's industry/intent.
     - Previous emails sent.
     - Stage goal (e.g., Intro, Nudge, Value, Break-up).

3. **Send Email**
   - Run `execution/send_email.py`.
   - Log the "Sent" event to SQLite and HubSpot.

4. **Schedule Next Step**
   - Determine delay for next follow-up (e.g., 2 days, 4 days).
   - Schedule the next execution of this directive.

## Sequence Logic
- **Stage 1 (Immediate)**: Personalized Intro + Value + Soft CTA.
- **Stage 2 (+2 Days)**: "Did you see this?" / Additional Value.
- **Stage 3 (+4 Days)**: Case Study / Social Proof.
- **Stage 4 (+7 Days)**: "Break-up" email.

## Edge Cases
- **Bounce**: Mark email as invalid in HubSpot, stop sequence.
- **Unsubscribe**: Mark as unsubscribed in HubSpot, stop sequence immediately.
