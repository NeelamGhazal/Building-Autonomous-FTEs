# Error Recovery & Audit Logging Skill

## Overview

Comprehensive error handling, graceful degradation, and audit logging system for the AI Employee. Ensures system resilience and complete action traceability.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Error Recovery & Audit System                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────────────┐  │
│  │   Any Action   │────▶│  Error Handler │────▶│  Recovery Strategy     │  │
│  │   (API Call,   │     │  (Categorize)  │     │  (Retry/Queue/Alert)   │  │
│  │   File Op)     │     └────────┬───────┘     └────────────┬───────────┘  │
│  └────────────────┘              │                          │              │
│                                  │                          │              │
│                                  ▼                          ▼              │
│                         ┌────────────────┐        ┌────────────────────┐   │
│                         │  Audit Logger  │        │  Graceful Degrade  │   │
│                         │  (JSON Log)    │        │  (Queue Locally)   │   │
│                         └────────┬───────┘        └────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│                    ┌──────────────────────────┐                            │
│                    │  /Logs/audit/YYYY-MM-DD  │                            │
│                    │  .json                   │                            │
│                    └──────────────────────────┘                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Error Categories

### 1. Transient Errors

Temporary failures that can be resolved by retrying.

| Error Type | Examples | Strategy |
|------------|----------|----------|
| Network Timeout | Connection refused, timeout | Exponential backoff retry (max 5) |
| Rate Limit | 429 Too Many Requests | Wait and retry with backoff |
| Temporary Unavailable | 503 Service Unavailable | Retry after delay |

**Retry Configuration:**
```python
RETRY_CONFIG = {
    "max_retries": 5,
    "base_delay": 1.0,  # seconds
    "max_delay": 60.0,  # seconds
    "exponential_base": 2,
    "jitter": True  # Add randomness to prevent thundering herd
}
```

### 2. Authentication Errors

Credential or token issues requiring human intervention.

| Error Type | Examples | Strategy |
|------------|----------|----------|
| Token Expired | Gmail 401, LinkedIn token refresh failed | Alert human, pause operations |
| Invalid Credentials | Wrong API key, revoked access | Create alert in /Needs_Action/ |
| Permission Denied | Insufficient scopes | Alert human with instructions |

**Alert Format:**
```markdown
---
type: auth_error
service: Gmail
error: Token expired
severity: critical
requires_action: true
---

## Authentication Error

The Gmail API token has expired and needs to be refreshed.

### Required Action
1. Run: `python3 email_mcp_server.py --reauth`
2. Complete OAuth flow in browser
3. Restart gmail_watcher.py

### Affected Services
- gmail_watcher.py (PAUSED)
- email_mcp_server.py (PAUSED)
```

### 3. Logic Errors

AI misinterpretation or incorrect processing.

| Error Type | Examples | Strategy |
|------------|----------|----------|
| Misclassification | Email marked wrong priority | Add to human review queue |
| Invalid Action | Tried to send to invalid email | Reject and log |
| Unexpected State | Task in impossible state | Reset to safe state |

**Human Review Queue:** `/Needs_Action/REVIEW_*.md`

### 4. System Errors

Infrastructure failures requiring monitoring.

| Error Type | Examples | Strategy |
|------------|----------|----------|
| Disk Full | No space for logs | Alert + rotate old logs |
| Process Crash | Watcher died | Watchdog auto-restart |
| Memory Exhausted | OOM killer | Restart with limits |

## Graceful Degradation

When services fail, the system continues operating in degraded mode:

### Gmail API Down

```python
DEGRADATION_RULES = {
    "gmail_api_down": {
        "action": "queue_locally",
        "queue_path": "/Queue/emails/",
        "max_queue_size": 100,
        "retry_interval": 300  # 5 minutes
    }
}
```

- Outgoing emails queued to `/Queue/emails/`
- Queue processed when API recovers
- Human notified after 1 hour

### Claude API Unavailable

```python
"claude_unavailable": {
    "action": "continue_collection",
    "description": "Watchers keep collecting, processing paused",
    "alert_after": 1800  # 30 minutes
}
```

- Gmail watcher continues creating files in `/Needs_Action/`
- WhatsApp watcher continues monitoring
- Processing resumes when Claude available

### Vault Locked

```python
"vault_locked": {
    "action": "temp_folder",
    "temp_path": "/tmp/ai_employee_backup/",
    "sync_on_unlock": True
}
```

- Write to temp folder
- Sync back to vault when unlocked
- No data lost

## Usage

### Start Error Recovery Daemon

```bash
# Run error recovery as background service
python3 error_recovery.py --daemon

# Check system health
python3 error_recovery.py --health

# Test error handling
python3 error_recovery.py --test

# Simulate specific error
python3 error_recovery.py --simulate network_timeout
python3 error_recovery.py --simulate auth_expired
python3 error_recovery.py --simulate disk_full
```

### CLI Commands

```bash
# View error statistics
python3 error_recovery.py --stats

# View recent errors
python3 error_recovery.py --recent 10

# Clear error queue
python3 error_recovery.py --clear-queue

# Force retry queued items
python3 error_recovery.py --retry-queue

# Check service status
python3 error_recovery.py --status
```

## Audit Logging

### Log Format

All actions logged to `/Logs/audit/YYYY-MM-DD.json`:

```json
{
    "timestamp": "2024-01-15T10:30:00.123456Z",
    "event_id": "evt_abc123def456",
    "action_type": "SEND_EMAIL",
    "actor": "claude_code",
    "target": {
        "type": "email",
        "to": "user@example.com",
        "subject": "Meeting Reminder"
    },
    "result": "success",
    "approval_status": "approved",
    "approval_id": "APPROVAL_20240115_103000",
    "duration_ms": 1523,
    "metadata": {
        "session_id": "sess_xyz789",
        "task_id": "TASK_20240115_103000_abc123",
        "iteration": 2
    }
}
```

### Action Types

| Type | Description |
|------|-------------|
| `SEND_EMAIL` | Email sent via Gmail API |
| `RECEIVE_EMAIL` | Email received and processed |
| `CREATE_POST` | Social media post created |
| `APPROVE_ACTION` | HITL approval given |
| `REJECT_ACTION` | HITL rejection |
| `CREATE_TASK` | Ralph Wiggum task created |
| `COMPLETE_TASK` | Task completed |
| `ERROR` | Error occurred |
| `RECOVERY` | Error recovery attempted |
| `SYSTEM` | System event (start, stop, restart) |

### Log Retention

- **Daily logs:** `/Logs/audit/YYYY-MM-DD.json`
- **Retention:** 90 days
- **Auto-cleanup:** Daily at midnight
- **Archive:** Compressed after 30 days

### Daily Summary

Generated daily at `/Logs/audit_summary.md`:

```markdown
# Audit Summary - 2024-01-15

## Overview
- Total Actions: 156
- Successful: 148 (94.9%)
- Failed: 8 (5.1%)
- Errors Recovered: 6

## Actions by Type
| Type | Count | Success Rate |
|------|-------|--------------|
| SEND_EMAIL | 45 | 97.8% |
| RECEIVE_EMAIL | 78 | 100% |
| CREATE_POST | 12 | 91.7% |
| APPROVE_ACTION | 21 | 100% |

## Errors
| Time | Type | Error | Recovery |
|------|------|-------|----------|
| 10:30 | SEND_EMAIL | Rate limited | Retried (success) |
| 14:22 | CREATE_POST | Network timeout | Retried (success) |

## Top Actors
1. claude_code: 120 actions
2. gmail_watcher: 78 actions
3. approval_watcher: 21 actions
```

### CLI Commands

```bash
# View today's audit log
python3 audit_logger.py --today

# View specific date
python3 audit_logger.py --date 2024-01-15

# Generate summary
python3 audit_logger.py --summary

# Search logs
python3 audit_logger.py --search "SEND_EMAIL"

# Export to CSV
python3 audit_logger.py --export csv --output audit_export.csv

# Test logging
python3 audit_logger.py --test

# Cleanup old logs
python3 audit_logger.py --cleanup
```

## Integration

### With Other Components

```python
# Import audit logger
from audit_logger import AuditLogger

# Log an action
AuditLogger.log(
    action_type="SEND_EMAIL",
    actor="email_mcp_server",
    target={"to": "user@example.com", "subject": "Test"},
    result="success",
    approval_status="approved"
)
```

### With Error Recovery

```python
# Import error handler
from error_recovery import ErrorHandler, with_retry

# Use decorator for automatic retry
@with_retry(max_retries=3, retry_on=[NetworkError, TimeoutError])
def send_email(to, subject, body):
    # Your code here
    pass

# Manual error handling
try:
    result = api_call()
except Exception as e:
    ErrorHandler.handle(e, context={"action": "api_call"})
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ERROR_RETRY_MAX` | 5 | Maximum retry attempts |
| `ERROR_RETRY_DELAY` | 1.0 | Base retry delay (seconds) |
| `AUDIT_RETENTION_DAYS` | 90 | Log retention period |
| `AUDIT_COMPRESS_AFTER` | 30 | Compress logs after N days |
| `DEGRADATION_ALERT_AFTER` | 3600 | Alert after N seconds |

### Configuration File

`error_config.json`:
```json
{
    "retry": {
        "max_retries": 5,
        "base_delay": 1.0,
        "max_delay": 60.0,
        "exponential_base": 2
    },
    "degradation": {
        "gmail": {
            "queue_path": "/Queue/emails/",
            "max_queue_size": 100
        }
    },
    "audit": {
        "retention_days": 90,
        "compress_after_days": 30,
        "summary_time": "00:00"
    }
}
```

## File Structure

```
AI_Employee_Vault/
├── error_recovery.py           # Error handling system
├── audit_logger.py             # Audit logging system
├── Queue/                      # Queued items during degradation
│   ├── emails/                 # Queued emails
│   └── posts/                  # Queued social media posts
├── Logs/
│   ├── audit/                  # Daily audit logs
│   │   ├── 2024-01-15.json
│   │   ├── 2024-01-14.json
│   │   └── ...
│   ├── audit_summary.md        # Daily summary
│   └── error_recovery.log      # Error recovery log
└── .claude/
    └── skills/
        └── error_recovery/
            └── SKILL.md        # This file
```

## Monitoring Dashboard

View real-time status in `Dashboard.md`:

```markdown
## System Health

| Service | Status | Last Error | Uptime |
|---------|--------|------------|--------|
| Gmail Watcher | ✅ Running | None | 24h |
| Approval Watcher | ✅ Running | None | 24h |
| Orchestrator | ✅ Running | None | 24h |
| Scheduler | ✅ Running | None | 24h |

## Error Summary (Last 24h)
- Total Errors: 8
- Recovered: 6 (75%)
- Pending: 2
- Human Action Required: 0

## Queue Status
- Emails Queued: 0
- Posts Queued: 0
```

## Best Practices

1. **Always use error handlers** for external API calls
2. **Log all actions** for audit trail
3. **Monitor health** regularly with `--health` command
4. **Review summaries** daily for patterns
5. **Test recovery** periodically with `--test`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Too many retries | Reduce max_retries or check root cause |
| Queue growing | Service down, check status |
| Missing audit logs | Check disk space, permissions |
| Recovery failing | Check error_recovery.log for details |
