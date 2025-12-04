import json
import os

def test_preview():
    stage = 1
    sample_email = "test@example.com"
    
    try:
        filename = f"batch_stage_{stage}.json"
        print(f"Attempting to read {filename}")
        with open(filename, "r") as f:
            batch_data = json.load(f)
            content = batch_data['content']
            print(f"Successfully read content: {content.keys()}")
            
            # Simple fill for preview
            preview_body = f"""
*Subject:* {content['subject']}

Hi {sample_email.split('@')[0]},

{content['personalized_hook']}

{content['value_proposition']}

{content['cta_text']}

*Best,*
*Arnold*
"""
            print("Preview Body Generated Successfully:")
            print(preview_body)
            
    except Exception as e:
        print(f"Error reading batch file: {e}")

if __name__ == "__main__":
    test_preview()
