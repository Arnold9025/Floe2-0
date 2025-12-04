import os
import json

def load_token():
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json:
        print("Loading Google Token from Environment Variable...")
        with open("token.json", "w") as f:
            f.write(token_json)
        print("token.json created successfully.")
    else:
        print("GOOGLE_TOKEN_JSON not found. Assuming local token.json exists.")

if __name__ == "__main__":
    load_token()
