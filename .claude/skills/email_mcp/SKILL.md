# Email MCP Server

## Overview

MCP (Model Context Protocol) server that enables Claude to send emails via Gmail with mandatory human approval. This server exposes email sending capabilities while ensuring all outgoing emails go through the HITL approval workflow.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude Code    │────▶│  Email MCP       │────▶│  HITL Approval  │
│  (MCP Client)   │     │  Server          │     │  System         │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┼───────────────┐
                        │                                 │               │
                        ▼                                 ▼               ▼
              ┌─────────────────┐              ┌─────────────────┐   ┌─────────┐
              │   /Approved/    │              │   /Rejected/    │   │ Expired │
              │   Gmail sends   │              │   Cancelled     │   │ 24h     │
              └─────────────────┘              └─────────────────┘   └─────────┘
```

## Flow Diagram

```
Gmail Watcher detects email
         │
         ▼
Claude reads email content
         │
         ▼
Claude decides to reply
         │
         ▼
Calls MCP send_email tool
         │
         ▼
┌─────────────────────────────────┐
│  Email MCP Server creates       │
│  approval request in            │
│  /Pending_Approval/             │
└─────────────────────────────────┘
         │
         ▼
Human reviews request file
         │
    ┌────┴────┐
    │         │
    ▼         ▼
Approved   Rejected
    │         │
    ▼         ▼
Gmail      Logged &
sends      cancelled
    │
    ▼
Logged to /Logs/email_sent.log
```

## MCP Tools Exposed

### `send_email`

Send an email via Gmail (requires HITL approval).

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `to` | string | Yes | Recipient email address |
| `subject` | string | Yes | Email subject line |
| `body` | string | Yes | Email body content (plain text or HTML) |
| `cc` | string | No | CC recipients (comma-separated) |
| `reply_to_message_id` | string | No | Message ID if replying to existing email |
| `is_html` | boolean | No | Set true if body is HTML (default: false) |

**Returns:**
```json
{
  "status": "pending_approval",
  "request_id": "uuid-v4",
  "message": "Email queued for approval. Move file to /Approved/ to send.",
  "approval_file": "/path/to/Pending_Approval/SEND_EMAIL_xxx.json"
}
```

### `check_email_status`

Check the status of a pending email.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | string | Yes | The request ID from send_email |

**Returns:**
```json
{
  "status": "PENDING | APPROVED | REJECTED | EXPIRED | SENT",
  "request_id": "uuid-v4",
  "details": {}
}
```

### `list_pending_emails`

List all emails pending approval.

**Returns:**
```json
{
  "pending_count": 2,
  "emails": [
    {
      "request_id": "uuid-1",
      "to": "client@example.com",
      "subject": "Re: Project Update",
      "created_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-01-16T10:30:00Z"
    }
  ]
}
```

## Configuration

### Claude Desktop MCP Config

Add to `~/.config/claude-code/settings.json` or Claude Desktop config:

```json
{
  "mcpServers": {
    "email": {
      "command": "python",
      "args": ["/path/to/AI_Employee_Vault/email_mcp_server.py"],
      "env": {
        "GMAIL_CREDENTIALS": "/path/to/credentials.json",
        "GMAIL_TOKEN": "/path/to/token.pickle"
      }
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GMAIL_CREDENTIALS` | `./credentials.json` | Path to Gmail OAuth credentials |
| `GMAIL_TOKEN` | `./token.pickle` | Path to cached OAuth token |
| `APPROVAL_TIMEOUT` | `86400` | Approval expiry in seconds (24h) |
| `VAULT_PATH` | Script directory | Base path for approval folders |

## Gmail Scopes Required

The MCP server requires Gmail send scope. Update your OAuth consent:

```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # Existing
    'https://www.googleapis.com/auth/gmail.send',       # NEW - for sending
    'https://www.googleapis.com/auth/gmail.compose',    # NEW - for drafts
]
```

**Note:** You may need to re-authenticate after adding scopes. Delete `token.pickle` and restart.

## Approval Request Format

When `send_email` is called, this file is created in `/Pending_Approval/`:

```json
{
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "action_type": "SEND_EMAIL",
  "description": "Send email to client@example.com: Re: Project Update",
  "details": {
    "recipient": "client@example.com",
    "subject": "Re: Project Update",
    "body_preview": "Hi John, Thank you for your email...",
    "cc": "manager@company.com",
    "platform": "gmail",
    "is_reply": true,
    "original_message_id": "msg-id-123"
  },
  "who_is_affected": "client@example.com (external)",
  "amount_if_payment": null,
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-16T10:30:00Z",
  "status": "PENDING",
  "how_to_approve": "Move this file to /Approved/ folder",
  "how_to_reject": "Move this file to /Rejected/ folder",
  "callback_data": {
    "to": "client@example.com",
    "subject": "Re: Project Update",
    "body": "Full email body here...",
    "cc": "manager@company.com",
    "reply_to_message_id": "msg-id-123"
  }
}
```

## Logging

All sent emails are logged to `/Logs/email_sent.log`:

```
2024-01-15 10:45:22 | SENT | To: client@example.com | Subject: Re: Project Update | Message-ID: abc123
2024-01-15 11:00:00 | REJECTED | To: vendor@example.com | Subject: Invoice Payment | Reason: User rejected
2024-01-15 12:30:00 | EXPIRED | To: partner@example.com | Subject: Meeting Request | No approval in 24h
```

## Usage Examples

### From Claude Code

```
User: Reply to John's email about the project update

Claude: I'll compose a reply to John. Since this involves sending an email,
it requires your approval first.

[Calls send_email MCP tool]

The email has been queued for approval:
- To: john@example.com
- Subject: Re: Project Update
- Body preview: "Hi John, Thank you for reaching out..."

To approve: Move the file from /Pending_Approval/ to /Approved/
To reject: Move to /Rejected/

The email will be sent automatically once approved.
```

### Programmatic Usage

```python
# This is handled by the MCP protocol, but conceptually:
result = await mcp_client.call_tool("send_email", {
    "to": "client@example.com",
    "subject": "Q4 Report",
    "body": "Please find attached the quarterly report...",
    "cc": "manager@company.com"
})

print(f"Approval pending: {result['request_id']}")
```

## Security Considerations

1. **All emails require approval** - No exceptions, even for replies
2. **Full body visible** - Approver sees complete email content before sending
3. **24-hour expiry** - Stale requests auto-expire
4. **Audit trail** - All actions logged with timestamps
5. **Credential isolation** - OAuth tokens stored securely

## Integration with HITL System

This MCP server uses the HITL approval system (`approval_watcher.py`):

1. Server creates approval request via `create_approval_request()`
2. Watcher monitors `/Approved/` folder
3. When file is moved, watcher calls the registered `SEND_EMAIL` executor
4. Email is sent via Gmail API
5. Result logged to both approval and email logs

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Token expired" | Delete `token.pickle`, restart server |
| "Insufficient scope" | Re-authenticate with send scope |
| Email not sending after approval | Check `approval_watcher.py` is running |
| "Rate limited" | Gmail has sending limits, wait and retry |
| MCP connection failed | Check server path in config |

## Dependencies

```
pip install google-auth google-auth-oauthlib google-api-python-client mcp
```

## Starting the Server

The MCP server is started automatically by Claude Code/Desktop when configured. For manual testing:

```bash
python email_mcp_server.py
```

This starts the server in stdio mode for MCP communication.
