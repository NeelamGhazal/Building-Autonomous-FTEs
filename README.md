# 🤖 AI Employee - Personal Automation System

## What is this?
A Personal AI Employee that monitors Gmail 24/7 and automatically creates task files in Obsidian when important emails arrive.

## Bronze Tier Features
- ✅ Obsidian Vault as AI Dashboard
- ✅ Gmail Watcher (monitors all unread emails)
- ✅ Auto-creates task files in /Needs_Action folder
- ✅ Claude Code connected to Vault
- ✅ Human-in-the-Loop approval system

## Tech Stack
- Claude Code (AI Brain)
- Obsidian (Dashboard & Memory)
- Python 3.12 (Gmail Watcher)
- Gmail API (Email Monitoring)

## Setup Instructions

### 1. Install Requirements
```bash
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 2. Google Cloud Setup
- Enable Gmail API
- Create OAuth credentials
- Download credentials.json to vault folder

### 3. Run Gmail Watcher
```bash
python3 gmail_watcher.py
```

### 4. Connect Claude Code
```bash
cd /path/to/AI_Employee_Vault
claude
```

## Folder Structure
```
AI_Employee_Vault/
├── Dashboard.md
├── Company_Handbook.md
├── gmail_watcher.py
├── Needs_Action/
├── Done/
├── Inbox/
├── Plans/
├── Logs/
└── Pending_Approval/
```

## Hackathon
Built for Personal AI Employee Hackathon 0 - Bronze Tier
