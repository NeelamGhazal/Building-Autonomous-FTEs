# Human-in-the-Loop (HITL) Approval System

## Overview

This skill implements a human approval workflow for sensitive AI actions. Before executing any high-risk operation, the system creates an approval request file and waits for human authorization.

## How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude wants   │────▶│  Creates request │────▶│  Human reviews  │
│  sensitive      │     │  in /Pending_    │     │  and moves to:  │
│  action         │     │  Approval/       │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────────────────────────┐
                        │                                 │                                 │
                        ▼                                 ▼                                 ▼
              ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
              │   /Approved/    │              │   /Rejected/    │              │   Expires       │
              │   Action runs   │              │   Cancelled     │              │   after 24h     │
              └─────────────────┘              └─────────────────┘              └─────────────────┘
```

## Sensitive Actions Requiring Approval

The following actions **ALWAYS** require human approval before execution:

| Action Type | Description | Risk Level |
|-------------|-------------|------------|
| `SEND_EMAIL` | Sending any email to any recipient | HIGH |
| `SOCIAL_MEDIA_POST` | Posting on LinkedIn, Twitter, or any social platform | HIGH |
| `PAYMENT` | Any payment or transaction over $50 | CRITICAL |
| `DELETE_FILE` | Permanently deleting any file | HIGH |
| `CONTACT_NEW_PERSON` | Initiating contact with someone not previously contacted | MEDIUM |

## Folder Structure

```
AI_Employee_Vault/
├── Pending_Approval/     # New approval requests appear here
├── Approved/             # Move files here to approve
├── Rejected/             # Move files here to reject
└── Logs/
    └── approval_history.log  # All approval decisions logged here
```

## Approval Request File Format

Each approval request is a JSON file with the following structure:

```json
{
  "request_id": "uuid-v4-string",
  "action_type": "SEND_EMAIL | SOCIAL_MEDIA_POST | PAYMENT | DELETE_FILE | CONTACT_NEW_PERSON",
  "description": "Human-readable description of what will happen",
  "details": {
    "recipient": "who receives or is affected",
    "subject": "email subject or post title (if applicable)",
    "body_preview": "first 500 chars of content",
    "amount": 0.00,
    "currency": "USD",
    "platform": "gmail | linkedin | etc"
  },
  "who_is_affected": "Description of who this action impacts",
  "amount_if_payment": "$0.00 or null",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-16T10:30:00Z",
  "status": "PENDING",
  "how_to_approve": "Move this file to /Approved/ folder",
  "how_to_reject": "Move this file to /Rejected/ folder",
  "callback_data": {
    "original_task_id": "reference to original task",
    "execution_payload": {}
  }
}
```

## File Naming Convention

Approval files are named for easy identification:

```
{action_type}_{short_description}_{timestamp}.json

Examples:
- SEND_EMAIL_john_quarterly_report_20240115_103000.json
- PAYMENT_aws_invoice_150usd_20240115_143022.json
- LINKEDIN_post_product_launch_20240115_090000.json
```

## How to Use (For Humans)

### To Approve an Action:
1. Navigate to `/Pending_Approval/` folder
2. Open and review the JSON file
3. If approved, **move** (not copy) the file to `/Approved/`
4. The `approval_watcher.py` will detect and execute the action

### To Reject an Action:
1. Navigate to `/Pending_Approval/` folder
2. Open and review the JSON file
3. If rejected, **move** (not copy) the file to `/Rejected/`
4. The action will be cancelled and logged

### Expired Requests:
- Requests expire after 24 hours automatically
- Expired requests are moved to `/Rejected/` with status `EXPIRED`
- No action is taken on expired requests

## How to Use (For Claude)

When you need to perform a sensitive action:

1. **Create the approval request:**
```python
from scripts.approval_watcher import create_approval_request

request_id = create_approval_request(
    action_type="SEND_EMAIL",
    description="Send quarterly report to John Smith",
    details={
        "recipient": "john.smith@company.com",
        "subject": "Q4 2024 Report",
        "body_preview": "Hi John, Please find attached...",
        "platform": "gmail"
    },
    who_is_affected="John Smith (external client)",
    amount_if_payment=None,
    callback_data={"draft_id": "abc123"}
)
```

2. **Wait for approval** (the watcher handles this automatically)

3. **Check status or get notified:**
```python
from scripts.approval_watcher import check_approval_status

status = check_approval_status(request_id)
# Returns: "PENDING", "APPROVED", "REJECTED", or "EXPIRED"
```

## Logging

All approval decisions are logged to `/Logs/approval_history.log`:

```
2024-01-15 10:35:22 | APPROVED | SEND_EMAIL | john_quarterly_report | Executed successfully
2024-01-15 11:00:00 | REJECTED | PAYMENT | vendor_invoice_500usd | User rejected
2024-01-16 10:30:00 | EXPIRED | LINKEDIN | product_launch_post | No response in 24h
```

## Security Considerations

- Approval files contain sensitive data - protect the folders appropriately
- Only the designated human operator should have write access to `/Approved/` and `/Rejected/`
- Claude should only have write access to `/Pending_Approval/`
- All actions are logged for audit purposes
- Payment approvals should be double-checked for amount accuracy

## Emergency Stop

To halt all pending actions:
1. Move all files from `/Pending_Approval/` to `/Rejected/`
2. Or run: `python approval_watcher.py --reject-all`

## Integration with Other Skills

This skill integrates with:
- `gmail_watcher.py` - Email actions routed through approval
- `linkedin_agent.py` - Social posts require approval
- `payment_processor.py` - Payments over $50 require approval

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Action not executing after approval | Check `approval_watcher.py` is running |
| File stuck in Pending | Check if expired (24h limit) |
| Duplicate requests | Check `request_id` - system deduplicates |
| Watcher not detecting files | Ensure file is fully moved, not copied |
