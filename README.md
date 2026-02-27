# AI Employee - Personal Automation System

## What is this?
A Personal AI Employee that monitors Gmail, WhatsApp, and LinkedIn 24/7, automatically processes tasks, sends emails, and posts on LinkedIn - all with human approval for sensitive actions.

## Bronze Tier Features
- Obsidian Vault as AI Dashboard
- Gmail Watcher (monitors all unread emails)
- Auto-creates task files in /Needs_Action folder
- Claude Code connected to Vault
- Orchestrator (automatic email processing)
- Agent Skills (SKILL.md based automation)

## Silver Tier Features
- Human-in-the-Loop (HITL) Approval System
- Email MCP Server (send emails via Gmail API)
- Cron Scheduling (daily/weekly automated tasks)
- LinkedIn Auto Post with HITL approval (Mock Mode)
- WhatsApp Watcher (keyword-based message detection)
- All AI functionality as Agent Skills

## Tech Stack
- Claude Code (AI Brain)
- Obsidian (Dashboard & Memory)
- Python 3.12 (Watchers & Automation)
- Gmail API (Email Monitoring & Sending)
- Playwright (WhatsApp Automation)
- APScheduler (Cron Scheduling)
- MCP Protocol (External Actions)

## Setup Instructions

### 1. Install Requirements
```bash
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client watchdog playwright apscheduler mcp
```

### 2. Google Cloud Setup
- Enable Gmail API
- Create OAuth credentials
- Download credentials.json to vault folder

### 3. Run All Watchers
```bash
# Terminal 1: Gmail Watcher
python3 gmail_watcher.py

# Terminal 2: Approval Watcher
python3 approval_watcher.py

# Terminal 3: Orchestrator
python3 orchestrator.py

# Terminal 4: Scheduler
python3 scheduler.py
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
├── orchestrator.py
├── approval_watcher.py
├── email_mcp_server.py
├── scheduler.py
├── linkedin_watcher.py
├── whatsapp_watcher.py
├── Needs_Action/
├── Done/
├── Inbox/
├── Plans/
├── Logs/
├── Pending_Approval/
├── Approved/
├── Rejected/
├── Briefings/
└── .claude/skills/
```

## Agent Skills
| Skill | Description |
|-------|-------------|
| email_processor | Process incoming emails |
| hitl_approval | Human approval workflow |
| email_mcp | Send emails via Gmail |
| scheduler | Cron job management |
| linkedin | Auto post generation |
| whatsapp | Message monitoring |

## Quick Demo Commands
```bash
# LinkedIn Auto Post Demo
python3 linkedin_watcher.py --demo "AI automation"

# WhatsApp Keyword Detection Demo
python3 whatsapp_watcher.py --demo

# Check Scheduler Status
python3 scheduler.py --status

# Check Pending Approvals
python3 approval_watcher.py --status
```

## Hackathon
Built for Personal AI Employee Hackathon 0
- Bronze Tier: Foundation
- Silver Tier: Functional Assistant
