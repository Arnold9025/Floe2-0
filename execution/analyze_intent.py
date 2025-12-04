import sys
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.db import get_lead_by_email, get_db_connection, update_lead_analysis

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Initialize OpenAI client
# Assumes OPENAI_API_KEY is in environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_lead(lead_data):
    """
    Analyzes the lead data using OpenAI to determine score and intent.
    """
    prompt = f"""
    Analyze the following lead and provide a JSON response with:
    1. "score": A score from 0-100 indicating lead quality.
    2. "intent": A short description of their intent (e.g., "Ready to buy", "Just browsing").
    3. "suggested_action": One of ["sequence_start", "manual_review", "disqualify"].
    4. "reasoning": Brief explanation.

    Lead Data:
    Name: {lead_data.get('name')}
    Source: {lead_data.get('source')}
    Message: {lead_data.get('metadata', {}).get('message', 'No message')}
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
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return {
            "score": 50,
            "intent": "Unknown (Error)",
            "suggested_action": "manual_review",
            "reasoning": f"Analysis failed: {str(e)}"
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_intent.py <lead_email>")
        sys.exit(1)

    email = sys.argv[1]
    lead = get_lead_by_email(email)
    
    if not lead:
        print(f"Error: Lead not found for email {email}")
        sys.exit(1)

    print(f"Analyzing lead: {email}...")
    analysis = analyze_lead(lead)
    
    update_lead_analysis(lead['id'], analysis)
    
    print(json.dumps(analysis, indent=2))

if __name__ == '__main__':
    main()
