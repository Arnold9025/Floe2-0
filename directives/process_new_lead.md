# Directive: Process New Lead

## Goal
Ingest a new lead, validate their information, analyze their intent/quality using OpenAI, save them to the local SQLite DB and HubSpot, and trigger the appropriate follow-up sequence.

## Inputs
- `lead_data`: JSON object containing at least `email` and optionally `name`, `phone`, `source`, `message`, `metadata`.

## Tools / Scripts
- `execution/ingest_lead.py`: Validates, saves to SQLite, and syncs to HubSpot.
- `execution/analyze_intent.py`: Uses OpenAI to score lead and determine initial context.
- `execution/sync_crm.py`: Updates HubSpot with lead score and intent.

## Procedure
1. **Ingest & Validate**
   - Run `execution/ingest_lead.py` with the `lead_data`.
   - Script checks for duplicates in SQLite and HubSpot.
   - Output: `lead_id` (local ID) and `hubspot_id`.

2. **Analyze Intent**
   - Run `execution/analyze_intent.py` using `lead_id`.
   - OpenAI analyzes `source` and `message` (if any).
   - Determine `lead_score` and `initial_intent`.

3. **Sync to CRM**
   - Run `execution/sync_crm.py` to update the contact in HubSpot with the analysis results.

4. **Initiate Sequence**
   - If `lead_score` > Threshold:
     - Schedule the first email (or send immediately) using `execution/manage_calendar.py` or a scheduler.
   - If `lead_score` is Low:
     - Mark as "Disqualified" in HubSpot.

## Edge Cases
- **Missing Email**: Reject lead.
- **Duplicate**: Update existing record with new interaction timestamp.
- **API Failure**: Retry 3 times, then log error and alert admin.
