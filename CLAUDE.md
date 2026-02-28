# AI Employee Project Guide

## 1. PROJECT OVERVIEW

**Hackathon:** Personal AI Employee Hackathon 0 - Building Autonomous FTEs (Full-Time Equivalents)

**Tagline:** Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.

**Vault Path:** `/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault`

**Goal:** Build a Personal AI Employee that monitors Gmail, WhatsApp, and LinkedIn 24/7, automatically processes tasks, sends emails, and posts on LinkedIn - all with human approval for sensitive actions.

**Architecture:**
- Brain: Claude Code (reasoning engine)
- Memory/GUI: Obsidian (local Markdown dashboard)
- Senses: Python Watcher scripts (Gmail, WhatsApp, filesystem)
- Hands: MCP servers (external actions)

---

## 2. COMPLETED WORK

### Bronze Tier - Foundation (DONE)

| Component | File | Status |
|-----------|------|--------|
| Obsidian Vault | Dashboard.md, Company_Handbook.md | Done |
| Gmail Watcher | gmail_watcher.py | Done |
| Orchestrator | orchestrator.py | Done |
| Email Processor Skill | .claude/skills/email_processor/SKILL.md | Done |
| Folder Structure | Needs_Action, Done, Inbox, Plans, Logs | Done |

### Silver Tier - Functional Assistant (DONE)

| Component | File | Status |
|-----------|------|--------|
| HITL Approval System | approval_watcher.py | Done |
| Email MCP Server | email_mcp_server.py | Done |
| Cron Scheduler | scheduler.py | Done |
| LinkedIn Auto Post (Mock) | linkedin_watcher.py | Done |
| WhatsApp Watcher | whatsapp_watcher.py | Done |
| HITL Approval Skill | .claude/skills/hitl_approval/SKILL.md | Done |
| Email MCP Skill | .claude/skills/email_mcp/SKILL.md | Done |
| Scheduler Skill | .claude/skills/scheduler/SKILL.md | Done |
| LinkedIn Skill | .claude/skills/linkedin/SKILL.md | Done |
| WhatsApp Skill | .claude/skills/whatsapp/SKILL.md | Done |

---

## 3. CURRENT TASK: Gold Tier

### Completed:

| Feature | Description | Status |
|---------|-------------|--------|
| Ralph Wiggum Loop | Stop hook for autonomous multi-step task completion | DONE |
| Error Recovery | Graceful degradation + exponential backoff retry | DONE |
| Audit Logging | JSON action logging with 90-day retention | DONE |

### Next to Build:

| Feature | Description | Priority |
|---------|-------------|----------|
| Odoo ERP Integration | Accounting system via MCP + JSON-RPC | Medium |
| CEO Briefing | Weekly autonomous business audit | Medium |
| Facebook/Instagram | Social media integration | Medium |
| Twitter/X Integration | Post and summarize | Medium |
| Architecture Docs | Full documentation of system | Low |

### Gold Tier Requirements:
- Full cross-domain integration (Personal + Business)
- Multiple MCP servers for different action types
- Weekly Business Audit with CEO Briefing generation
- Error recovery and graceful degradation
- Ralph Wiggum loop for autonomous multi-step tasks
- All AI functionality as Agent Skills

---

## 4. HOW TO RUN

### Start All Services (Production)

```bash
# Terminal 1: Gmail Watcher
python3 gmail_watcher.py

# Terminal 2: Approval Watcher (HITL)
python3 approval_watcher.py

# Terminal 3: Orchestrator
python3 orchestrator.py

# Terminal 4: Scheduler
python3 scheduler.py
```

### Demo Commands

```bash
# LinkedIn Auto Post Demo
python3 linkedin_watcher.py --demo "AI automation trends"

# WhatsApp Keyword Detection Demo
python3 whatsapp_watcher.py --demo

# Ralph Wiggum Loop Demo (autonomous tasks)
python3 ralph_wiggum.py --demo "Process all emails in Needs_Action"

# Check Scheduler Status
python3 scheduler.py --status

# Check Pending Approvals
python3 approval_watcher.py --status

# Generate CEO Briefing Now
python3 scheduler.py --run generate_ceo_briefing

# Create Email Approval Request
python3 -c "from email_mcp_server import create_email_approval_request; create_email_approval_request('test@example.com', 'Test Subject', 'Test Body')"
```

### Test Commands

```bash
# Test Gmail Connection
python3 email_mcp_server.py --test

# Test LinkedIn (Mock Mode)
python3 linkedin_watcher.py --test

# Test WhatsApp Keywords
python3 whatsapp_watcher.py --test "urgent help needed with invoice"
```

---

## 5. TECH STACK

| Component | Technology | Purpose |
|-----------|------------|---------|
| AI Brain | Claude Code | Reasoning engine |
| Dashboard | Obsidian | Local Markdown GUI |
| Runtime | Python 3.12 | Watchers & automation |
| Email | Gmail API | Monitor & send emails |
| Browser Automation | Playwright | WhatsApp Web |
| Scheduling | APScheduler | Cron jobs |
| External Actions | MCP Protocol | Email, browser, calendar |
| File Watching | Watchdog | Folder monitoring |

### Dependencies

```bash
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 \
    google-api-python-client watchdog playwright apscheduler mcp anthropic
```

---

## 6. IMPORTANT RULES

### Memory Rule
**MEMORY RULE: Before any conversation compaction or context reset, always save current progress to memory.md. Always read memory.md at the start of each new session.**

### Security Rules
- NEVER store credentials in vault (use .env or environment variables)
- NEVER commit credentials.json, token.pickle, or session files
- All sensitive actions MUST go through HITL approval
- Rotate credentials monthly

### Development Rules
- All AI functionality MUST be implemented as Agent Skills (SKILL.md files)
- Vault path is ALWAYS: `/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault`
- Use polling for WSL2 compatibility (watchdog inotify issues)
- Test with --demo or --dry-run before production

### HITL (Human-in-the-Loop) Requirements
Actions that ALWAYS require approval:
- Sending any email
- Posting on LinkedIn or social media
- Any payment over $50
- Deleting files
- Contacting new people

### Approval Workflow
1. Create approval request in `/Pending_Approval/`
2. Human reviews JSON file
3. Move to `/Approved/` to execute
4. Move to `/Rejected/` to cancel
5. Expires after 24 hours

---

## 7. FOLDER STRUCTURE

```
AI_Employee_Vault/
├── CLAUDE.md                 # This file (project guide)
├── README.md                 # Public documentation
├── Dashboard.md              # Real-time status
├── Company_Handbook.md       # Rules of engagement
├── credentials.json          # Gmail OAuth (gitignored)
├── token.pickle              # Gmail token (gitignored)
│
├── gmail_watcher.py          # Monitor Gmail
├── orchestrator.py           # Process tasks
├── approval_watcher.py       # HITL system
├── email_mcp_server.py       # Send emails
├── scheduler.py              # Cron jobs
├── linkedin_watcher.py       # LinkedIn automation
├── whatsapp_watcher.py       # WhatsApp monitoring
├── ralph_wiggum.py           # Autonomous task loop
│
├── Active_Tasks/             # Currently running Ralph Wiggum tasks
├── Needs_Action/             # Pending tasks
├── Done/                     # Completed tasks
├── Inbox/                    # Incoming items
├── Plans/                    # Task plans
├── Logs/                     # Activity logs
├── Pending_Approval/         # HITL requests
├── Approved/                 # Approved actions
├── Rejected/                 # Rejected actions
├── Briefings/                # CEO briefings
├── whatsapp_session/         # WhatsApp session (gitignored)
│
└── .claude/
    ├── hooks/
    │   └── stop_hook.py          # Ralph Wiggum stop hook
    └── skills/
        ├── email_processor/SKILL.md
        ├── hitl_approval/SKILL.md
        ├── email_mcp/SKILL.md
        ├── scheduler/SKILL.md
        ├── linkedin/SKILL.md
        ├── whatsapp/SKILL.md
        └── ralph_wiggum/SKILL.md
```

---

## 8. AGENT SKILLS REFERENCE

| Skill | Location | Description |
|-------|----------|-------------|
| email_processor | .claude/skills/email_processor/ | Process incoming emails |
| hitl_approval | .claude/skills/hitl_approval/ | Human approval workflow |
| email_mcp | .claude/skills/email_mcp/ | Send emails via Gmail API |
| scheduler | .claude/skills/scheduler/ | Cron job management |
| linkedin | .claude/skills/linkedin/ | LinkedIn auto-posting (mock) |
| whatsapp | .claude/skills/whatsapp/ | WhatsApp message monitoring |
| ralph_wiggum | .claude/skills/ralph_wiggum/ | Autonomous multi-step task loop |
| error_recovery | .claude/skills/error_recovery/ | Error handling + graceful degradation |

---

## 9. SCHEDULED JOBS

| Job | Schedule | Description |
|-----|----------|-------------|
| process_emails | Daily 8:00 AM | Process /Needs_Action/ emails |
| generate_ceo_briefing | Sunday 9:00 PM | Weekly CEO briefing |
| check_expired_approvals | Every hour | Expire old approval requests |

---

## 10. COMMON ISSUES & FIXES

| Issue | Solution |
|-------|----------|
| WSL2 file events not detected | Use polling mode (already implemented) |
| Gmail token expired | Run `python3 email_mcp_server.py --reauth` |
| WhatsApp QR needed | Run without --headless first |
| Approval not executing | Check approval_watcher.py is running |
| LinkedIn auth failed | Mock mode is default, no auth needed |

---

## 11. GIT REPOSITORY

**Repository:** https://github.com/NeelamGhazal/Building-Autonomous-FTEs

**Branches:**
- main: Production code

**Commits:**
- Bronze Tier: Initial foundation
- Silver Tier: HITL, MCP, Scheduler, LinkedIn, WhatsApp

---

## 12. HACKATHON TIERS STATUS

| Tier | Status | Completion |
|------|--------|------------|
| Bronze | DONE | 100% |
| Silver | DONE | 100% |
| Gold | IN PROGRESS | 45% |
| Platinum | NOT STARTED | 0% |

---

*Last Updated: 2026-02-27*
*Generated by Claude Code for Hackathon 0*
