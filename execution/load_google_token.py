import os
import json

def load_token():
    # 1. Load Token (for access)
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json:
        print("Loading Google Token from Environment Variable...")
        with open("token.json", "w") as f:
            f.write(token_json)
        print("token.json created successfully.")
    else:
        print("GOOGLE_TOKEN_JSON not found. Assuming local token.json exists.")

    # 2. Load Credentials (for refresh)
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json:
        print("Loading Google Credentials from Environment Variable...")
        with open("credentials.json", "w") as f:
            f.write(creds_json)
        print("credentials.json created successfully.")
    else:
        print("GOOGLE_CREDENTIALS not found. Assuming local credentials.json exists.")

if __name__ == "__main__":
    load_token()
