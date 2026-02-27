# Cron Scheduler Skill

## Overview

Automated task scheduler for the AI Employee system using cron-style scheduling. Runs background jobs at specified intervals without manual intervention.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      APScheduler Daemon                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Daily 8:00 AM  │  │  Sunday 9:00 PM │  │    Every Hour   │  │
│  │  Process Emails │  │  CEO Briefing   │  │  Check Expired  │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │            │
│           ▼                    ▼                    ▼            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  /Needs_Action/ │  │   /Briefings/   │  │/Pending_Approval│  │
│  │  folder         │  │   weekly.md     │  │  expired check  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `process_emails` | Daily 8:00 AM | Process all unread emails in `/Needs_Action/` |
| `generate_ceo_briefing` | Sunday 9:00 PM | Generate weekly CEO briefing in `/Briefings/` |
| `check_expired_approvals` | Every hour | Check `/Pending_Approval/` for expired requests |

## Cron Schedule Reference

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday = 0)
│ │ │ │ │
* * * * *
```

### Examples
- `0 8 * * *` - Every day at 8:00 AM
- `0 21 * * 0` - Every Sunday at 9:00 PM
- `0 * * * *` - Every hour at minute 0
- `*/15 * * * *` - Every 15 minutes
- `0 9-17 * * 1-5` - Every hour from 9 AM to 5 PM, Monday to Friday

## Configuration

### Default Schedules (in scheduler.py)

```python
SCHEDULES = {
    "process_emails": {
        "trigger": "cron",
        "hour": 8,
        "minute": 0,
        "description": "Process unread emails daily at 8 AM"
    },
    "generate_ceo_briefing": {
        "trigger": "cron",
        "day_of_week": "sun",
        "hour": 21,
        "minute": 0,
        "description": "Generate CEO briefing every Sunday at 9 PM"
    },
    "check_expired_approvals": {
        "trigger": "interval",
        "hours": 1,
        "description": "Check for expired approvals every hour"
    }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULER_TIMEZONE` | `UTC` | Timezone for scheduled tasks |
| `VAULT_PATH` | Script directory | Base path for all folders |
| `SCHEDULER_LOG` | `Logs/scheduler.log` | Log file path |

## Usage

### Start the Scheduler

```bash
# Run scheduler daemon
python scheduler.py

# Run in background
python scheduler.py &

# Run with nohup (persistent)
nohup python scheduler.py > /dev/null 2>&1 &
```

### CLI Commands

```bash
# Show all scheduled jobs
python scheduler.py --status

# Run a specific job immediately
python scheduler.py --run process_emails
python scheduler.py --run generate_ceo_briefing
python scheduler.py --run check_expired_approvals

# Add a new job
python scheduler.py --add "my_task" --cron "0 12 * * *"

# Remove a job
python scheduler.py --remove my_task

# List next run times
python scheduler.py --next
```

## Task Details

### 1. Process Emails (Daily 8:00 AM)

Scans `/Needs_Action/` folder for unprocessed email files and:
- Marks emails as "reviewed"
- Creates action items based on email content
- Moves processed emails to `/Done/` if completed
- Logs summary to `/Logs/email_processing.log`

```
Needs_Action/
├── EMAIL_20240115_client_inquiry.md  → Processed
├── EMAIL_20240115_meeting_request.md → Processed
└── EMAIL_20240114_invoice.md         → Moved to Done/
```

### 2. CEO Briefing (Sunday 9:00 PM)

Generates a weekly summary briefing including:
- Emails received and processed this week
- Actions taken by AI Employee
- Pending approvals summary
- Key metrics and statistics

Output: `/Briefings/CEO_Briefing_Week_03_2024.md`

```markdown
# CEO Weekly Briefing
## Week 3, 2024 (Jan 15 - Jan 21)

### Email Summary
- Received: 47 emails
- Processed: 45 emails
- Pending: 2 emails

### Actions Taken
- Replied to 12 client inquiries
- Scheduled 5 meetings
- Processed 8 invoices

### Pending Approvals
- 3 emails awaiting send approval
- 1 payment over $50 pending

### Key Metrics
- Response time: 2.3 hours average
- Automation rate: 78%
```

### 3. Check Expired Approvals (Every Hour)

Monitors `/Pending_Approval/` for requests that have exceeded their 24-hour window:
- Moves expired requests to `/Rejected/`
- Updates status to "EXPIRED"
- Logs expiration events

## Integration with Other Skills

### With HITL Approval System
```python
from approval_watcher import check_expired_requests

def check_expired_approvals():
    check_expired_requests()  # Reuses existing function
```

### With Gmail Watcher
```python
from gmail_watcher import process_pending_emails

def process_emails():
    process_pending_emails()  # If implemented
```

## Logging

All scheduler events are logged to `/Logs/scheduler.log`:

```
2024-01-15 08:00:00 | INFO | JOB_START | process_emails | Starting daily email processing
2024-01-15 08:00:15 | INFO | JOB_END | process_emails | Processed 12 emails, 3 actions created
2024-01-15 09:00:00 | INFO | JOB_START | check_expired_approvals | Checking for expired requests
2024-01-15 09:00:01 | INFO | JOB_END | check_expired_approvals | 1 request expired
2024-01-21 21:00:00 | INFO | JOB_START | generate_ceo_briefing | Generating weekly briefing
2024-01-21 21:00:05 | INFO | JOB_END | generate_ceo_briefing | Briefing saved to Briefings/CEO_Briefing_Week_03_2024.md
```

## Running as a Service

### Using systemd (Linux)

Create `/etc/systemd/system/ai-employee-scheduler.service`:

```ini
[Unit]
Description=AI Employee Scheduler
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/AI_Employee_Vault
ExecStart=/usr/bin/python3 scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ai-employee-scheduler
sudo systemctl start ai-employee-scheduler
```

### Using PM2 (Node.js process manager)

```bash
pm2 start scheduler.py --interpreter python3 --name ai-scheduler
pm2 save
pm2 startup
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Jobs not running | Check timezone settings |
| Missed job | APScheduler runs missed jobs on startup |
| Memory issues | Increase `max_instances` or add job coalescing |
| Duplicate runs | Enable `coalesce=True` in job config |

## Dependencies

```bash
pip install apscheduler
```

## File Structure

```
AI_Employee_Vault/
├── scheduler.py           # Main scheduler script
├── Needs_Action/          # Emails to process
├── Briefings/             # Generated briefings
│   └── CEO_Briefing_Week_XX_YYYY.md
├── Pending_Approval/      # HITL requests
└── Logs/
    └── scheduler.log      # Scheduler logs
```
