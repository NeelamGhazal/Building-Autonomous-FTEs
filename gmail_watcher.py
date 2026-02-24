import os
import time
import pickle
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

VAULT_PATH = Path("/mnt/e/Hackathon-0/AI_Employee_Vault/AI_Employee_Vault")
CREDENTIALS_FILE = VAULT_PATH / "credentials.json"
TOKEN_FILE = VAULT_PATH / "token.pickle"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CHECK_INTERVAL = 60

def get_gmail_service():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return build('gmail', 'v1', credentials=creds)

def create_action_file(msg_id, sender, subject, snippet):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = NEEDS_ACTION / f"EMAIL_{timestamp}_{msg_id[:8]}.md"
    content = f"""---
type: email
from: {sender}
subject: {subject}
received: {datetime.now().isoformat()}
status: pending
---

## Email Content
{snippet}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
"""
    filename.write_text(content)
    print(f"[{datetime.now()}] New task created: {filename.name}")

def run_watcher():
    print("Starting Gmail Watcher...")
    service = get_gmail_service()
    processed_ids = set()
    print("Connected to Gmail! Watching for emails...")

    while True:
        try:
            results = service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=10
            ).execute()

            messages = results.get('messages', [])

            for msg in messages:
                if msg['id'] in processed_ids:
                    continue

                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject']
                ).execute()

                headers = {h['name']: h['value']
                          for h in msg_data['payload']['headers']}
                snippet = msg_data.get('snippet', '')
                subject = headers.get('Subject', 'No Subject')
                sender = headers.get('From', 'Unknown')

                # Ab sab unread emails process hongi!
                create_action_file(msg['id'], sender, subject, snippet)
                processed_ids.add(msg['id'])

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_watcher()
