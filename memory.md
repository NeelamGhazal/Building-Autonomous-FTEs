# AI Employee Project Memory

> **Last Updated:** 2026-02-28
> **Session:** Gold Tier - Error Recovery + Audit Logging COMPLETE
> **Next Task:** Odoo ERP Integration (Gold Tier)

---

## PROJECT OVERVIEW

**Project:** Personal AI Employee for Hackathon 0 - Building Autonomous FTEs
**Vault Path:** `/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault`
**Repository:** https://github.com/NeelamGhazal/Building-Autonomous-FTEs

**Goal:** Build an AI Employee that monitors Gmail, WhatsApp, and LinkedIn 24/7, automatically processes tasks, sends emails, and posts on LinkedIn - all with human approval for sensitive actions.

---

## BRONZE TIER - FOUNDATION (100% COMPLETE)

### What Was Built

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| Obsidian Dashboard | `Dashboard.md` | Real-time status display | Working |
| Company Handbook | `Company_Handbook.md` | Rules of engagement for AI | Working |
| Gmail Watcher | `gmail_watcher.py` | Monitors unread emails via Gmail API | Working |
| Orchestrator | `orchestrator.py` | Processes tasks from /Needs_Action/ | Working |
| Email Processor Skill | `.claude/skills/email_processor/SKILL.md` | Email handling instructions | Working |

### How It Works

1. `gmail_watcher.py` polls Gmail API every 30 seconds
2. New emails create `.md` files in `/Needs_Action/`
3. `orchestrator.py` detects new files and triggers Claude
4. Claude reads the email and creates a plan in `/Plans/`
5. Human reviews and approves actions

### Issues/Notes

- Gmail API requires `credentials.json` and OAuth setup
- First run requires browser authentication to get `token.pickle`
- VAULT_PATH was fixed from wrong path to: `/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault`

---

## SILVER TIER - FUNCTIONAL ASSISTANT (100% COMPLETE)

### What Was Built

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| HITL Approval System | `approval_watcher.py` | Watches /Approved/ and /Rejected/ folders | Working |
| Email MCP Server | `email_mcp_server.py` | MCP server for sending emails via Gmail | Working |
| Cron Scheduler | `scheduler.py` | APScheduler for daily/weekly tasks | Working |
| LinkedIn Watcher | `linkedin_watcher.py` | Auto-generate LinkedIn posts (Mock Mode) | Working |
| WhatsApp Watcher | `whatsapp_watcher.py` | Playwright-based WhatsApp monitoring | Working |
| HITL Skill | `.claude/skills/hitl_approval/SKILL.md` | Approval workflow documentation | Working |
| Email MCP Skill | `.claude/skills/email_mcp/SKILL.md` | Email sending documentation | Working |
| Scheduler Skill | `.claude/skills/scheduler/SKILL.md` | Cron job documentation | Working |
| LinkedIn Skill | `.claude/skills/linkedin/SKILL.md` | LinkedIn posting documentation | Working |
| WhatsApp Skill | `.claude/skills/whatsapp/SKILL.md` | WhatsApp monitoring documentation | Working |

### HITL Approval System Details

**File:** `approval_watcher.py`

**How It Works:**
1. Claude creates approval request JSON in `/Pending_Approval/`
2. Human moves file to `/Approved/` or `/Rejected/`
3. `approval_watcher.py` detects the move and executes/cancels
4. Uses both watchdog AND polling (5 sec) for WSL2 compatibility

**Actions Requiring Approval:**
- Sending any email
- Posting on LinkedIn/social media
- Payments over $50
- Deleting files
- Contacting new people

**Key Functions:**
- `execute_approved_action()` - Routes to appropriate executor
- `execute_send_email()` - Calls GmailService.send_email()
- Polling fallback every 5 seconds (WSL2 fix)

### Email MCP Server Details

**File:** `email_mcp_server.py`

**Exposed Tools:**
- `send_email` - Send email via Gmail API (requires HITL approval)
- `check_email_status` - Check status of pending emails
- `list_pending_emails` - List all pending email approvals

**Key Functions:**
- `GmailService.send_email()` - Actual Gmail API call
- `create_email_approval_request()` - Creates approval JSON

### Scheduler Details

**File:** `scheduler.py`

**Scheduled Jobs:**
| Job ID | Schedule | Description |
|--------|----------|-------------|
| `process_emails` | Daily 8:00 AM | Process /Needs_Action/ emails |
| `generate_ceo_briefing` | Sunday 9:00 PM | Weekly CEO briefing |
| `check_expired_approvals` | Every hour | Expire old requests (24h) |

**CLI Commands:**
- `--status` - Show job status
- `--run <job_id>` - Run job immediately

### LinkedIn Watcher Details

**File:** `linkedin_watcher.py`

**Mode:** Mock Mode (MOCK_MODE = True)
- Does NOT require real LinkedIn API credentials
- Saves posts to `/Logs/linkedin_posts.md`
- Creates approval request in `/Pending_Approval/`

**CLI Commands:**
- `--demo "topic"` - Full demo flow
- `--history` - View published posts
- `--test` - Test authentication

**Key Functions:**
- `generate_post_content()` - AI generates post
- `mock_publish_post()` - Saves to file instead of LinkedIn
- `create_linkedin_approval_request()` - Creates HITL request

### WhatsApp Watcher Details

**File:** `whatsapp_watcher.py`

**Keywords Monitored:**
`urgent, invoice, payment, help, asap, emergency, deadline, important, critical, immediately`

**How It Works:**
1. Playwright opens WhatsApp Web
2. Scans messages for keywords
3. Creates `WA_*.md` files in `/Needs_Action/`
4. First run requires QR code scan (session saved)

**CLI Commands:**
- `--demo` - Demo with mock messages
- `--test "message"` - Test keyword detection
- `--headless` - Run without browser window
- `--logout` - Clear session

---

## ALL FILES AND PURPOSES

### Python Scripts

| File | Purpose | Dependencies |
|------|---------|--------------|
| `gmail_watcher.py` | Monitor Gmail for new emails | google-api-python-client |
| `orchestrator.py` | Process tasks, trigger Claude | watchdog |
| `approval_watcher.py` | HITL approval system | watchdog, email_mcp_server |
| `email_mcp_server.py` | Send emails via Gmail | google-api-python-client, mcp |
| `scheduler.py` | Cron job scheduling | apscheduler |
| `linkedin_watcher.py` | LinkedIn auto-posting (mock) | - |
| `whatsapp_watcher.py` | WhatsApp message monitoring | playwright |
| `ralph_wiggum.py` | Autonomous multi-step task loop | - |

### Skill Files

| File | Purpose |
|------|---------|
| `.claude/skills/email_processor/SKILL.md` | Email processing instructions |
| `.claude/skills/hitl_approval/SKILL.md` | Approval workflow documentation |
| `.claude/skills/email_mcp/SKILL.md` | Email sending via MCP |
| `.claude/skills/scheduler/SKILL.md` | Cron scheduling documentation |
| `.claude/skills/linkedin/SKILL.md` | LinkedIn posting documentation |
| `.claude/skills/whatsapp/SKILL.md` | WhatsApp monitoring documentation |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Public documentation |
| `CLAUDE.md` | Project guide for Claude Code |
| `memory.md` | This file - project state memory |
| `Dashboard.md` | Obsidian dashboard |
| `Company_Handbook.md` | AI rules of engagement |

### Folders

| Folder | Purpose |
|--------|---------|
| `Needs_Action/` | Pending tasks (emails, WhatsApp messages) |
| `Done/` | Completed tasks |
| `Inbox/` | Incoming items |
| `Plans/` | Task plans created by Claude |
| `Logs/` | Activity logs |
| `Pending_Approval/` | HITL requests awaiting approval |
| `Approved/` | Approved actions (triggers execution) |
| `Rejected/` | Rejected actions |
| `Briefings/` | CEO briefings |
| `whatsapp_session/` | WhatsApp Playwright session (gitignored) |
| `Active_Tasks/` | Running Ralph Wiggum tasks |

---

## ISSUES FIXED

| Issue | Solution | File |
|-------|----------|------|
| WSL2 watchdog not detecting file moves | Added polling fallback (5 sec) | approval_watcher.py |
| Wrong event handler (on_created vs on_moved) | Added on_moved() handlers | approval_watcher.py |
| Stub executor not sending emails | Integrated real GmailService | approval_watcher.py |
| APScheduler next_run_time error | Used trigger.get_next_fire_time() | scheduler.py |
| LinkedIn demo file not found | Fixed glob pattern | linkedin_watcher.py |
| Gmail watcher wrong VAULT_PATH | Fixed path constant | gmail_watcher.py |

---

## CURRENT STATUS

| Component | Running | Last Tested |
|-----------|---------|-------------|
| gmail_watcher.py | Manual start | 2026-02-27 |
| orchestrator.py | Manual start | 2026-02-27 |
| approval_watcher.py | Manual start | 2026-02-27 |
| scheduler.py | Manual start | 2026-02-27 |
| linkedin_watcher.py | Demo tested | 2026-02-27 |
| whatsapp_watcher.py | Demo tested | 2026-02-27 |
| ralph_wiggum.py | Demo tested | 2026-02-28 |

---

## GOLD TIER - IN PROGRESS (45%)

### Completed: Ralph Wiggum Loop

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| Ralph Wiggum Script | `ralph_wiggum.py` | Autonomous multi-step task loop | Working |
| Stop Hook | `.claude/hooks/stop_hook.py` | Iteration control and completion check | Working |
| Ralph Wiggum Skill | `.claude/skills/ralph_wiggum/SKILL.md` | Documentation | Working |
| Active_Tasks Folder | `Active_Tasks/` | Running task storage | Created |

**How It Works:**
1. Task file created in `/Active_Tasks/` with YAML frontmatter
2. Claude works on the task step by step
3. Stop hook checks after each response: task in `/Done/`?
   - NO → Re-inject prompt, continue (max 10 iterations)
   - YES → Exit successfully
4. All iterations logged to `/Logs/ralph_wiggum.log`

**Task File Format:**
```yaml
---
task_id: TASK_20240115_103000_abc123
prompt: what needs to be done
status: in_progress
iteration: 1
max_iterations: 10
completion_promise: TASK_COMPLETE
---
```

**CLI Commands:**
- `--demo "task"` - Run demo simulation
- `--task "task"` - Create and run real task
- `--list` - List active tasks
- `--status TASK_ID` - Check task status
- `--cancel TASK_ID` - Cancel a task

**Demo Tested:** 2026-02-28 (3 iterations, completed successfully)

---

### Completed: Error Recovery + Audit Logging

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| Error Recovery Script | `error_recovery.py` | Graceful degradation + retry | Working |
| Audit Logger | `audit_logger.py` | JSON action logging | Working |
| Error Recovery Skill | `.claude/skills/error_recovery/SKILL.md` | Documentation | Working |
| Queue Folder | `Queue/` | Local queue for graceful degradation | Created |
| Audit Folder | `Logs/audit/` | Daily JSON logs | Created |

**Error Recovery Features:**
- Transient errors → Exponential backoff retry (max 5 attempts)
- Auth errors → Alert human, pause operations
- Logic errors → Human review queue
- System errors → Watchdog + auto-restart
- Graceful degradation: Gmail down → queue locally; Vault locked → temp folder

**Audit Logger Features:**
- JSON logs: `/Logs/audit/YYYY-MM-DD.json`
- Fields: timestamp, event_id, action_type, actor, target, result, approval_status
- 90-day retention with auto-cleanup
- Daily summary: `/Logs/audit_summary.md`

**CLI Commands:**
- `python3 error_recovery.py --test` - Run tests
- `python3 error_recovery.py --health` - Check system health
- `python3 error_recovery.py --simulate auth_expired` - Simulate error
- `python3 audit_logger.py --test` - Run tests
- `python3 audit_logger.py --today` - View today's log
- `python3 audit_logger.py --summary` - Generate summary

**Demo Tested:** 2026-02-28 (13 error tests, 11 audit tests - all passed)

---

## NEXT TASK: GOLD TIER

### Gold Tier Full List

| Feature | Description | Priority |
|---------|-------------|----------|
| Ralph Wiggum Loop | Autonomous multi-step tasks | DONE |
| Error Recovery | Graceful degradation + retry | DONE |
| Audit Logging | JSON action logging | DONE |
| Odoo ERP | Accounting integration | Medium |
| CEO Briefing | Weekly business audit | Medium |
| Facebook/Instagram | Social media expansion | Medium |
| Twitter/X | Social media expansion | Medium |

---

## CREDENTIALS & SECURITY

**Files to NEVER commit:**
- `credentials.json` - Gmail OAuth client
- `token.pickle` - Gmail access token
- `linkedin_credentials.json` - LinkedIn OAuth
- `whatsapp_session/` - WhatsApp session data
- `.env` - Environment variables

**All in .gitignore:** Yes

---

## HOW TO START SERVICES

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

---

## DEMO COMMANDS

```bash
# LinkedIn Demo
python3 linkedin_watcher.py --demo "AI trends"

# WhatsApp Demo
python3 whatsapp_watcher.py --demo

# Scheduler Status
python3 scheduler.py --status

# Approval Status
python3 approval_watcher.py --status
```

---

*This file is the project memory. Update it before context resets.*
