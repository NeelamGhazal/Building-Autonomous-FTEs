# AI Employee Architecture Documentation

## Gold Tier Submission - Hackathon 0: Building Autonomous FTEs

**Version:** 1.0.0
**Date:** 2026-03-04
**Tier Achieved:** Gold (100% Complete)
**Repository:** https://github.com/NeelamGhazal/Building-Autonomous-FTEs

---

## 1. Project Overview

### What Is This?

The **Personal AI Employee** is an autonomous Full-Time Equivalent (FTE) system that monitors communication channels (Gmail, WhatsApp, LinkedIn), processes tasks automatically, and executes actions with human-in-the-loop approval for sensitive operations.

### Tagline

> *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

### Key Capabilities

| Capability | Description |
|------------|-------------|
| Email Monitoring | 24/7 Gmail monitoring with automatic task extraction |
| Social Media Automation | LinkedIn, Facebook, Instagram, Twitter/X posting |
| WhatsApp Monitoring | Keyword-based urgent message detection |
| ERP Integration | Odoo accounting system integration |
| Autonomous Tasks | Multi-step task execution via Ralph Wiggum loop |
| CEO Briefings | Weekly automated business reports |
| Human Approval | HITL workflow for all sensitive actions |

### Tier Progression

| Tier | Status | Completion |
|------|--------|------------|
| Bronze | Foundation | 100% |
| Silver | Functional Assistant | 100% |
| Gold | Enterprise Features | 100% |
| Platinum | Not Started | 0% |

---

## 2. System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           PERSONAL AI EMPLOYEE SYSTEM                                │
│                              Gold Tier Architecture                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              INPUT LAYER                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │   │
│  │  │ Gmail API    │  │ WhatsApp Web │  │ Odoo ERP    │  │ Manual Input │     │   │
│  │  │ (Watcher)    │  │ (Playwright) │  │ (JSON-RPC)  │  │ (CLI/Vault)  │     │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │   │
│  └─────────┼─────────────────┼─────────────────┼─────────────────┼─────────────┘   │
│            │                 │                 │                 │                  │
│            ▼                 ▼                 ▼                 ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           OBSIDIAN VAULT                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │   │
│  │  │                        /Needs_Action/                                   │ │   │
│  │  │   EMAIL_*.md  │  WA_*.md  │  TASK_*.md  │  Other requests              │ │   │
│  │  └────────────────────────────────────────────────────────────────────────┘ │   │
│  │                                    │                                         │   │
│  │                                    ▼                                         │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │   │
│  │  │                      ORCHESTRATOR (orchestrator.py)                     │ │   │
│  │  │                    Detects new files, triggers Claude                   │ │   │
│  │  └────────────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                                       ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           CLAUDE CODE (Brain)                                │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │   │
│  │  │  Agent Skills (.claude/skills/)                                        │ │   │
│  │  │  ├── email_processor    ├── hitl_approval    ├── scheduler            │ │   │
│  │  │  ├── linkedin           ├── whatsapp         ├── social_media         │ │   │
│  │  │  ├── ceo_briefing       ├── odoo_mcp         ├── ralph_wiggum         │ │   │
│  │  │  └── error_recovery                                                    │ │   │
│  │  └────────────────────────────────────────────────────────────────────────┘ │   │
│  │                                    │                                         │   │
│  │                     Creates action requests                                  │   │
│  │                                    │                                         │   │
│  └────────────────────────────────────┼─────────────────────────────────────────┘   │
│                                       ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         HITL APPROVAL SYSTEM                                 │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │   │
│  │  │ /Pending_Approval│───▶│ Human Decision   │───▶│ /Approved/ or    │      │   │
│  │  │ (JSON requests)  │    │ (Move file)      │    │ /Rejected/       │      │   │
│  │  └──────────────────┘    └──────────────────┘    └────────┬─────────┘      │   │
│  │                                                           │                  │   │
│  │                    approval_watcher.py detects            │                  │   │
│  │                                                           ▼                  │   │
│  └───────────────────────────────────────────────────────────┼──────────────────┘   │
│                                                               │                      │
│                                                               ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              OUTPUT LAYER                                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │   │
│  │  │ Gmail API    │  │ LinkedIn     │  │ FB/IG/Twitter│  │ Odoo ERP    │     │   │
│  │  │ (Send Email) │  │ (Mock Post)  │  │ (Mock Post)  │  │ (JSON-RPC)  │     │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │   │
│  │                                                                              │   │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                         /Done/ + /Logs/                               │   │   │
│  │  │   Completed tasks, audit logs, post history, CEO briefings           │   │   │
│  │  └──────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   INPUT     │────▶│   VAULT     │────▶│   CLAUDE    │────▶│   HITL      │
│  Watchers   │     │ /Needs_     │     │   Process   │     │  Approval   │
│             │     │  Action/    │     │   + Plan    │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                    │
                    ┌─────────────┐     ┌─────────────┐            │
                    │   /Done/    │◀────│   EXECUTE   │◀───────────┘
                    │   + Logs    │     │   Action    │
                    └─────────────┘     └─────────────┘
```

---

## 3. All Components Built

### Bronze Tier - Foundation

| Component | File | Purpose |
|-----------|------|---------|
| Obsidian Dashboard | `Dashboard.md` | Real-time status display |
| Company Handbook | `Company_Handbook.md` | AI rules of engagement |
| Gmail Watcher | `gmail_watcher.py` | Monitor inbox for new emails |
| Orchestrator | `orchestrator.py` | Process tasks, trigger Claude |
| Email Processor Skill | `.claude/skills/email_processor/` | Email handling instructions |

### Silver Tier - Functional Assistant

| Component | File | Purpose |
|-----------|------|---------|
| HITL Approval System | `approval_watcher.py` | Human approval workflow |
| Email MCP Server | `email_mcp_server.py` | Send emails via Gmail API |
| Cron Scheduler | `scheduler.py` | APScheduler for automated jobs |
| LinkedIn Watcher | `linkedin_watcher.py` | Auto-generate LinkedIn posts |
| WhatsApp Watcher | `whatsapp_watcher.py` | Playwright-based monitoring |
| 5 Agent Skills | `.claude/skills/` | HITL, Email, Scheduler, LinkedIn, WhatsApp |

### Gold Tier - Enterprise Features

| Component | File | Purpose |
|-----------|------|---------|
| Ralph Wiggum Loop | `ralph_wiggum.py` | Autonomous multi-step tasks |
| Error Recovery | `error_recovery.py` | Graceful degradation + retry |
| Audit Logger | `audit_logger.py` | JSON action logging |
| Odoo MCP Server | `odoo_mcp_server.py` | ERP integration via JSON-RPC |
| CEO Briefing | `ceo_briefing.py` | Weekly business audit |
| Facebook/Instagram | `facebook_instagram.py` | Social media posting |
| Twitter/X | `twitter_x.py` | Tweet automation |
| 4 Additional Skills | `.claude/skills/` | Ralph Wiggum, Error Recovery, Odoo, CEO Briefing, Social Media |

---

## 4. Tech Stack

### Core Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| AI Brain | Claude Code (Opus 4.5) | Reasoning and task execution |
| Dashboard/GUI | Obsidian | Local Markdown-based interface |
| Runtime | Python 3.12 | Watchers, MCP servers, automation |
| Email | Gmail API | Monitor and send emails |
| Browser Automation | Playwright | WhatsApp Web integration |
| Scheduling | APScheduler | Cron-style job scheduling |
| External Actions | MCP Protocol | Standardized tool interface |
| File Watching | Watchdog | Folder monitoring (with polling fallback) |
| ERP | Odoo 17 (Docker) | Accounting and CRM |

### Python Dependencies

```bash
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 \
    google-api-python-client watchdog playwright apscheduler \
    mcp anthropic requests
```

### External Services

| Service | Purpose | Auth Method |
|---------|---------|-------------|
| Gmail | Email monitoring/sending | OAuth 2.0 |
| Odoo | ERP integration | JSON-RPC + session auth |
| LinkedIn | Social posting (mock) | OAuth 2.0 (future) |
| Facebook/Instagram | Social posting (mock) | Graph API (future) |
| Twitter/X | Tweet posting (mock) | OAuth 2.0 (future) |
| WhatsApp | Message monitoring | Playwright + QR code |

---

## 5. How Each Component Works

### 5.1 Gmail Watcher (`gmail_watcher.py`)

```
Polls Gmail API every 30 seconds
         │
         ▼
┌─────────────────────────┐
│ New unread email found? │
└────────────┬────────────┘
             │ Yes
             ▼
┌─────────────────────────┐
│ Create EMAIL_*.md in    │
│ /Needs_Action/          │
└─────────────────────────┘
```

**Key Features:**
- OAuth 2.0 authentication with Gmail
- Creates structured markdown files
- Extracts sender, subject, body, date
- Marks emails as read after processing

### 5.2 Orchestrator (`orchestrator.py`)

```
Watches /Needs_Action/ for new files
         │
         ▼
┌─────────────────────────┐
│ New file detected?      │
└────────────┬────────────┘
             │ Yes
             ▼
┌─────────────────────────┐
│ Read file content       │
│ Trigger Claude Code     │
│ Generate plan in /Plans/│
└─────────────────────────┘
```

**Key Features:**
- Uses watchdog with polling fallback (WSL2 fix)
- Triggers Claude to analyze and plan
- Coordinates between input and processing

### 5.3 Approval Watcher (`approval_watcher.py`)

```
Watches /Approved/ and /Rejected/ folders
         │
         ▼
┌─────────────────────────┐
│ File moved to folder?   │
└────────────┬────────────┘
             │ Yes
             ▼
┌─────────────────────────┐
│ Load JSON, route to     │
│ appropriate executor    │
│ (email, post, etc.)     │
└─────────────────────────┘
```

**Key Features:**
- Detects file moves (not just creation)
- Routes to correct executor based on action_type
- Polling fallback every 5 seconds
- Logs all actions to audit log

### 5.4 Scheduler (`scheduler.py`)

```
APScheduler runs background jobs
         │
         ▼
┌─────────────────────────────────────┐
│ Scheduled Jobs:                      │
│ - process_emails (Daily 8 AM)       │
│ - generate_ceo_briefing (Sun 9 PM)  │
│ - check_expired_approvals (Hourly)  │
└─────────────────────────────────────┘
```

**Key Features:**
- Cron-style scheduling
- Misfire grace time (1 hour)
- Job coalescing for missed runs
- CLI commands: `--status`, `--run <job>`

### 5.5 Ralph Wiggum Loop (`ralph_wiggum.py`)

```
Task created in /Active_Tasks/
         │
         ▼
┌─────────────────────────┐
│ Claude works on task    │
│ (up to 10 iterations)   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Stop hook checks:       │
│ Task in /Done/?         │
└────────────┬────────────┘
        Yes/│\No
           ▼  ▼
     Exit   Continue
```

**Key Features:**
- Autonomous multi-step task execution
- Stop hook for iteration control
- YAML frontmatter for task metadata
- Max 10 iterations safety limit

### 5.6 Odoo MCP Server (`odoo_mcp_server.py`)

```
JSON-RPC calls to Odoo
         │
         ▼
┌─────────────────────────────────────┐
│ Tools:                               │
│ - get_customers                     │
│ - get_invoices                      │
│ - get_financial_summary             │
│ - create_customer (HITL)            │
│ - create_invoice (HITL)             │
└─────────────────────────────────────┘
```

**Key Features:**
- JSON-RPC API (not XML-RPC)
- Session-based authentication
- Financial summary with collection rates
- Write operations require HITL

### 5.7 CEO Briefing (`ceo_briefing.py`)

```
Collects data from all sources
         │
         ▼
┌─────────────────────────────────────┐
│ Data Sources:                        │
│ - Odoo (financials)                 │
│ - Audit logs                        │
│ - HITL approvals                    │
│ - Ralph Wiggum tasks                │
│ - Email activity                    │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Generate markdown report            │
│ Save to /Briefings/                 │
└─────────────────────────────────────┘
```

### 5.8 Social Media (`facebook_instagram.py`, `twitter_x.py`)

```
Post request with content
         │
         ▼
┌─────────────────────────┐
│ Create approval JSON    │
│ in /Pending_Approval/   │
└────────────┬────────────┘
             │ Human approves
             ▼
┌─────────────────────────┐
│ Mock publish + save to  │
│ /Social_Media/*.md      │
└─────────────────────────┘
```

**Key Features:**
- Mock mode (no real API calls)
- HITL approval required
- Post history in markdown
- Twitter: 280 char limit validation

---

## 6. Agent Skills

All Claude Code skills are located in `.claude/skills/`:

| Skill | File | Purpose |
|-------|------|---------|
| Email Processor | `email_processor/SKILL.md` | How to process incoming emails |
| HITL Approval | `hitl_approval/SKILL.md` | Approval workflow documentation |
| Email MCP | `email_mcp/SKILL.md` | How to send emails via Gmail |
| Scheduler | `scheduler/SKILL.md` | Cron job management |
| LinkedIn | `linkedin/SKILL.md` | LinkedIn post automation |
| WhatsApp | `whatsapp/SKILL.md` | WhatsApp message monitoring |
| Ralph Wiggum | `ralph_wiggum/SKILL.md` | Autonomous task loop |
| Error Recovery | `error_recovery/SKILL.md` | Graceful degradation |
| Odoo MCP | `odoo_mcp/SKILL.md` | ERP integration |
| CEO Briefing | `ceo_briefing/SKILL.md` | Weekly business audit |
| Social Media | `social_media/SKILL.md` | FB, IG, Twitter posting |

---

## 7. Security & HITL Design

### Human-in-the-Loop (HITL) Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     HITL APPROVAL FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. AI creates action request                                   │
│     └─▶ JSON file in /Pending_Approval/                         │
│                                                                  │
│  2. Human reviews in Obsidian                                   │
│     ├─▶ Move to /Approved/  → Execute action                   │
│     └─▶ Move to /Rejected/  → Cancel action                    │
│                                                                  │
│  3. Expiration (24 hours)                                       │
│     └─▶ Auto-move to /Rejected/ with status: EXPIRED           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Actions Requiring HITL Approval

| Action | Reason |
|--------|--------|
| Send any email | Prevent spam/mistakes |
| Post on social media | Brand protection |
| Create Odoo contacts | Data integrity |
| Create invoices | Financial accuracy |
| Payments over $50 | Financial control |
| Delete files | Data protection |
| Contact new people | Privacy |

### Credential Handling

**Files NEVER committed to Git:**
- `credentials.json` - Gmail OAuth client secrets
- `token.pickle` - Gmail access tokens
- `linkedin_credentials.json` - LinkedIn OAuth
- `whatsapp_session/` - WhatsApp session data
- `.env` - Environment variables

**Storage:**
- All credentials in root directory (gitignored)
- Environment variables for sensitive data
- OAuth tokens stored locally only

### Audit Logging

```
/Logs/audit/YYYY-MM-DD.json
{
    "timestamp": "2026-03-04T21:00:00Z",
    "event_id": "evt_abc123",
    "action_type": "SEND_EMAIL",
    "actor": "approval_watcher",
    "target": {"to": "user@example.com"},
    "result": "success",
    "approval_status": "approved"
}
```

- 90-day retention policy
- Daily audit summaries
- All actions tracked

---

## 8. Lessons Learned

### Challenge 1: WSL2 File System Events

**Problem:** Watchdog's inotify doesn't work reliably in WSL2 for detecting file moves between folders.

**Solution:** Implemented polling fallback every 5 seconds alongside watchdog events.

```python
# WSL2 fix: Polling fallback
while True:
    poll_for_changes()
    time.sleep(5)
```

### Challenge 2: APScheduler Next Run Time

**Problem:** APScheduler's `next_run_time` attribute doesn't exist until scheduler starts.

**Solution:** Use `trigger.get_next_fire_time()` method instead.

```python
next_run = job.trigger.get_next_fire_time(None, datetime.now(tz.utc))
```

### Challenge 3: Odoo Database Initialization

**Problem:** After Docker volume reset, Odoo shows "Internal Server Error".

**Solution:** Initialize database with base modules:
```bash
docker exec odoo-odoo-1 odoo -i base -d odoo --stop-after-init
```

### Challenge 4: Mock Mode for Social Media

**Problem:** Real social media APIs require approved developer accounts (weeks of review).

**Solution:** Implemented Mock Mode that:
- Simulates full workflow
- Creates HITL approval requests
- Saves to history files
- Shows exactly what would be posted

### Challenge 5: Real-Time Communication

**Problem:** Need to monitor WhatsApp without official API.

**Solution:** Playwright browser automation with WhatsApp Web:
- QR code authentication (first run)
- Session persistence
- Keyword-based urgent message detection

---

## 9. How To Run

### Prerequisites

```bash
# Python 3.12+
python3 --version

# Install dependencies
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 \
    google-api-python-client watchdog playwright apscheduler \
    mcp anthropic requests

# Playwright browsers
playwright install chromium
```

### Gmail Setup

1. Create project in Google Cloud Console
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Download as `credentials.json`
5. First run will open browser for authentication

```bash
python3 gmail_watcher.py
# Opens browser, authenticate with Google
# Creates token.pickle for future use
```

### Odoo Setup (Optional)

```bash
# Start Odoo with Docker
cd /mnt/e/Hackathon-0/Odoo
docker compose up -d

# Initialize database (first time only)
docker exec odoo-odoo-1 odoo -i base -d odoo --stop-after-init

# Access at http://localhost:8069
# Login: admin / admin
```

### Start All Services

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

### Demo Commands

```bash
# LinkedIn Demo
python3 linkedin_watcher.py --demo "AI trends"

# WhatsApp Demo
python3 whatsapp_watcher.py --demo

# Facebook/Instagram Demo
python3 facebook_instagram.py --demo

# Twitter Demo
python3 twitter_x.py --demo

# CEO Briefing
python3 ceo_briefing.py --generate

# Odoo Test
python3 odoo_mcp_server.py --test

# Scheduler Status
python3 scheduler.py --status
```

---

## 10. Repository Structure

### GitHub Repository

**URL:** https://github.com/NeelamGhazal/Building-Autonomous-FTEs

**Branch:** main

### Directory Structure

```
AI_Employee_Vault/
├── ARCHITECTURE.md              # This file
├── CLAUDE.md                    # Project guide for Claude Code
├── README.md                    # Public documentation
├── memory.md                    # Project state memory
├── Dashboard.md                 # Obsidian dashboard
├── Company_Handbook.md          # AI rules of engagement
│
├── gmail_watcher.py             # Gmail monitoring
├── orchestrator.py              # Task processing
├── approval_watcher.py          # HITL approval system
├── email_mcp_server.py          # Email MCP server
├── scheduler.py                 # Cron scheduler
├── linkedin_watcher.py          # LinkedIn automation
├── whatsapp_watcher.py          # WhatsApp monitoring
├── ralph_wiggum.py              # Autonomous task loop
├── error_recovery.py            # Error handling
├── audit_logger.py              # Audit logging
├── odoo_mcp_server.py           # Odoo ERP integration
├── ceo_briefing.py              # CEO briefing generator
├── facebook_instagram.py        # FB/IG automation
├── twitter_x.py                 # Twitter automation
│
├── .claude/
│   ├── hooks/
│   │   └── stop_hook.py         # Ralph Wiggum stop hook
│   └── skills/
│       ├── email_processor/SKILL.md
│       ├── hitl_approval/SKILL.md
│       ├── email_mcp/SKILL.md
│       ├── scheduler/SKILL.md
│       ├── linkedin/SKILL.md
│       ├── whatsapp/SKILL.md
│       ├── ralph_wiggum/SKILL.md
│       ├── error_recovery/SKILL.md
│       ├── odoo_mcp/SKILL.md
│       ├── ceo_briefing/SKILL.md
│       └── social_media/SKILL.md
│
├── Needs_Action/                # Pending tasks
├── Done/                        # Completed tasks
├── Plans/                       # Task plans
├── Pending_Approval/            # HITL requests
├── Approved/                    # Approved actions
├── Rejected/                    # Rejected actions
├── Briefings/                   # CEO briefings
├── Social_Media/                # Post history
├── Logs/
│   ├── audit/                   # Daily audit logs
│   ├── orchestrator.log
│   ├── scheduler.log
│   ├── social_media.log
│   └── twitter.log
├── Active_Tasks/                # Running Ralph Wiggum tasks
└── Queue/                       # Graceful degradation queue
```

### Git Commits (Gold Tier)

| Commit | Description |
|--------|-------------|
| `0ad087e` | Ralph Wiggum Loop for autonomous tasks |
| `2ce5500` | Error Recovery and Audit Logging systems |
| `e83b75c` | Odoo ERP Integration via JSON-RPC |
| `db766a4` | Rebuild Odoo MCP Server with JSON-RPC API |
| `f0f8d04` | CEO Briefing + Weekly Business Audit |
| `1ca958d` | Facebook + Instagram Integration |
| `b0b58c6` | Twitter/X Integration |

---

## Summary

The Personal AI Employee system demonstrates a complete autonomous FTE architecture with:

- **24/7 Monitoring**: Gmail, WhatsApp, and scheduled tasks
- **Intelligent Processing**: Claude Code as the reasoning engine
- **Human Control**: HITL approval for all sensitive actions
- **Enterprise Integration**: Odoo ERP, social media platforms
- **Autonomous Execution**: Ralph Wiggum multi-step task loop
- **Observability**: Audit logging, CEO briefings, error recovery

**Gold Tier: 100% Complete**

---

*Generated by Claude Code for Hackathon 0: Building Autonomous FTEs*
*Last Updated: 2026-03-04*
