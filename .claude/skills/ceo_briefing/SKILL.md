# CEO Briefing Skill

## Overview

Weekly business audit and executive briefing generator. Collects data from all AI Employee systems and produces a comprehensive CEO briefing report saved to `/Briefings/`.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CEO Briefing Data Flow                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────────┐  │
│  │ Data Sources   │────▶│  ceo_briefing  │────▶│ /Briefings/        │  │
│  │                │     │  .py           │     │ CEO_Brief_*.md     │  │
│  └────────────────┘     └────────────────┘     └────────────────────┘  │
│                                                                          │
│  Data Sources:                                                           │
│  ├─ Odoo ERP (odoo_mcp_server.py)                                       │
│  ├─ Audit Logs (/Logs/audit/)                                           │
│  ├─ Gmail Watcher logs                                                   │
│  ├─ HITL Approvals (/Approved/, /Rejected/, /Pending_Approval/)         │
│  └─ Ralph Wiggum tasks (/Done/, /Active_Tasks/)                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Sources

### 1. Odoo ERP Integration

Uses `odoo_mcp_server.py` JSON-RPC API:
- **Invoices**: Total, paid, unpaid amounts
- **Customers**: New customers this week
- **Financial Summary**: Collection rate, outstanding balances

### 2. Audit Logs

Reads `/Logs/audit/YYYY-MM-DD.json` files:
- Action counts by type (emails, posts, tasks)
- Success/failure rates
- Actor activity breakdown

### 3. HITL Approval System

Scans approval folders:
- `/Pending_Approval/` - Awaiting decisions
- `/Approved/` - Actions executed
- `/Rejected/` - Actions denied
- Calculates approval rate and response times

### 4. Ralph Wiggum Tasks

Reads from `/Done/` and `/Active_Tasks/`:
- Completed task count
- Task completion rate
- Average iterations per task

### 5. Email Activity

Parses email folders:
- `/Needs_Action/` - Pending emails
- `/Done/` - Processed emails
- Email response metrics

## Briefing Format

```markdown
# CEO Weekly Briefing
## Week 09, 2026 (Feb 24 - Mar 01)

## Executive Summary
- 3 bullet points highlighting key business health indicators

## Key Metrics Table
| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Invoices Sent | 4 | 2 | +100% |
| Revenue Collected | $0 | $0 | - |

## Urgent Items
- Unpaid invoices over 30 days
- Pending approvals > 24h old
- Failed tasks

## Weekly Wins
- Successful automations
- Tasks completed
- New customers

## Recommendations
- AI-generated suggestions based on data

## Financial Snapshot from Odoo
- Total Invoiced: $143,175.00
- Collected: $0.00
- Outstanding: $143,175.00
- Collection Rate: 0%
```

## CLI Commands

```bash
# Generate briefing now
python3 ceo_briefing.py --generate

# View last briefing
python3 ceo_briefing.py --last

# List all briefings
python3 ceo_briefing.py --list

# Preview without saving
python3 ceo_briefing.py --preview

# Generate for specific date range
python3 ceo_briefing.py --from 2026-02-21 --to 2026-02-28
```

## Schedule

Configured in `scheduler.py`:
- **Job ID**: `generate_ceo_briefing`
- **Schedule**: Every Sunday at 9:00 PM
- **Timezone**: UTC (configurable via SCHEDULER_TIMEZONE env var)

## Output Location

Briefings saved to: `/Briefings/CEO_Brief_YYYY-MM-DD.md`

Example: `CEO_Brief_2026-02-28.md`

## Integration Points

### Scheduler Integration

```python
# In scheduler.py
from ceo_briefing import generate_briefing

scheduler.add_job(
    generate_briefing,
    CronTrigger(day_of_week='sun', hour=21, minute=0),
    id='generate_ceo_briefing',
    name='CEO Briefing (Sunday 9:00 PM)'
)
```

### Manual Trigger

```bash
# Via scheduler
python3 scheduler.py --run generate_ceo_briefing

# Direct
python3 ceo_briefing.py --generate
```

## Error Handling

- If Odoo unavailable: Financial section shows "Odoo Offline"
- If audit logs empty: Shows "No audit data for period"
- If no emails: Shows "No email activity"
- All errors logged to `/Logs/ceo_briefing.log`

## Configuration

### Environment Variables

```bash
# Optional: Odoo connection (uses defaults from odoo_mcp_server.py)
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=admin
ODOO_PASSWORD=admin

# Optional: Timezone
SCHEDULER_TIMEZONE=UTC
```

## Security

- No sensitive data in briefings (no credentials, tokens)
- Financial data from Odoo is read-only
- Briefings contain aggregated metrics only

## File Structure

```
AI_Employee_Vault/
├── ceo_briefing.py               # Main script
├── Briefings/                    # Output folder
│   ├── CEO_Brief_2026-02-28.md
│   └── CEO_Brief_2026-02-21.md
├── Logs/
│   ├── audit/                    # Input: audit logs
│   └── ceo_briefing.log          # Output: script logs
└── .claude/
    └── skills/
        └── ceo_briefing/
            └── SKILL.md          # This file
```

## Demo Results

```
$ python3 ceo_briefing.py --generate

==================================================
CEO BRIEFING GENERATOR
==================================================
Collecting data from:
  - Odoo ERP...          [OK] 4 invoices, $143,175 total
  - Audit Logs...        [OK] 12 events
  - HITL Approvals...    [OK] 2 approved, 0 rejected
  - Ralph Wiggum...      [OK] 1 task completed
  - Email Activity...    [OK] 24 emails processed

Briefing saved to: Briefings/CEO_Brief_2026-02-28.md
==================================================
```

---

*Last Updated: 2026-02-28*
*Gold Tier Feature - CEO Briefing Complete*
