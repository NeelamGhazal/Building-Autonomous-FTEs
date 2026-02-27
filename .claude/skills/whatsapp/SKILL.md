# WhatsApp Watcher Skill

## Overview

Monitors WhatsApp Web for important messages using Playwright browser automation. Detects messages containing priority keywords and creates action items for the AI Employee system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WhatsApp Watcher Flow                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │  WhatsApp    │───▶│  Playwright  │───▶│  Keyword Detection   │   │
│  │  Web         │    │  Browser     │    │  Engine              │   │
│  └──────────────┘    └──────────────┘    └──────────┬───────────┘   │
│                                                      │               │
│                                          ┌───────────┴───────────┐   │
│                                          │                       │   │
│                                          ▼                       ▼   │
│                                   ┌────────────┐          ┌──────────┐
│                                   │  Match!    │          │ No Match │
│                                   │  Create    │          │ Skip     │
│                                   │  .md file  │          │          │
│                                   └─────┬──────┘          └──────────┘
│                                         │                            │
│                                         ▼                            │
│                                   ┌──────────────┐                   │
│                                   │ /Needs_Action│                   │
│                                   │ WA_*.md      │                   │
│                                   └──────┬───────┘                   │
│                                         │                            │
│                                         ▼                            │
│                                   ┌──────────────┐                   │
│                                   │ Orchestrator │                   │
│                                   │ + Claude     │                   │
│                                   └──────────────┘                   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

### 1. Message Monitoring
- Real-time WhatsApp Web monitoring
- Session persistence (no QR scan every time)
- Headless mode for background operation
- Multiple chat support

### 2. Keyword Detection
- Configurable priority keywords
- Case-insensitive matching
- Partial word matching support
- Custom keyword lists per category

### 3. Action Item Creation
- Auto-creates `.md` files in `/Needs_Action/`
- Includes sender, timestamp, full message
- Suggested actions based on keywords
- Links to original conversation

## Default Keywords

```python
PRIORITY_KEYWORDS = [
    "urgent",
    "invoice",
    "payment",
    "help",
    "asap",
    "emergency",
    "deadline",
    "important",
    "critical",
    "immediately"
]
```

## Configuration

### Keywords in Company_Handbook.md

Add to your `Company_Handbook.md`:

```markdown
## WhatsApp Keywords

Priority keywords that trigger action items:
- urgent, asap, immediately, emergency
- invoice, payment, billing, receipt
- help, support, issue, problem
- deadline, due, overdue
- meeting, call, schedule
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHATSAPP_HEADLESS` | `false` | Run browser in headless mode |
| `WHATSAPP_SESSION` | `./whatsapp_session` | Session storage path |
| `CHECK_INTERVAL` | `30` | Seconds between checks |
| `KEYWORDS` | See defaults | Comma-separated keywords |

## Usage

### First Run (QR Code Login)

```bash
# Run with visible browser to scan QR code
python whatsapp_watcher.py

# Browser opens → Scan QR code → Session saved
```

### Subsequent Runs

```bash
# Normal mode (visible browser)
python whatsapp_watcher.py

# Headless mode (background)
python whatsapp_watcher.py --headless

# Custom keywords
python whatsapp_watcher.py --keywords "urgent,invoice,help"

# Check specific chat
python whatsapp_watcher.py --chat "Client Name"
```

### CLI Commands

```bash
# Start watcher
python whatsapp_watcher.py

# Show status
python whatsapp_watcher.py --status

# Clear session (re-login required)
python whatsapp_watcher.py --logout

# Test keyword detection
python whatsapp_watcher.py --test "This is an urgent message"

# List detected messages
python whatsapp_watcher.py --list
```

## Session Management

Sessions are stored in `/whatsapp_session/`:

```
whatsapp_session/
├── context.json       # Browser context
├── cookies.json       # Session cookies
└── storage/           # Local storage data
```

**Note:** Keep this folder secure - it contains your WhatsApp session!

## Action Item Format

When a keyword is detected, a file is created in `/Needs_Action/`:

```markdown
---
type: whatsapp
from: John Smith
chat: Project Team
received: 2024-01-15T10:30:00
keywords: [urgent, help]
status: pending
---

## WhatsApp Message

**From:** John Smith
**Chat:** Project Team
**Time:** 2024-01-15 10:30:00

### Message Content

Hey, this is URGENT! We need help with the invoice ASAP.
The client is asking about the payment status.

## Detected Keywords

- urgent
- help
- invoice
- asap

## Suggested Actions

- [ ] Review message priority
- [ ] Respond to sender
- [ ] Check invoice status
- [ ] Update client
```

## File Naming

Files are named for easy identification:

```
WA_{timestamp}_{sender}_{keyword}.md

Examples:
- WA_20240115_103000_JohnSmith_urgent.md
- WA_20240115_143022_ClientTeam_invoice.md
```

## Integration with Orchestrator

The Orchestrator automatically picks up WhatsApp action items:

```python
# orchestrator.py integration
def process_whatsapp_items():
    for file in NEEDS_ACTION.glob("WA_*.md"):
        # Parse message
        # Trigger Claude analysis
        # Create response plan
```

## Headless Mode

For server/background operation:

```bash
# Start in headless mode
python whatsapp_watcher.py --headless

# Note: First run must be with visible browser for QR scan
```

### Running as Service

```bash
# Using nohup
nohup python whatsapp_watcher.py --headless > /dev/null 2>&1 &

# Using screen
screen -dmS whatsapp python whatsapp_watcher.py --headless
```

## Security Considerations

1. **Session Security**: `/whatsapp_session/` contains sensitive data
2. **Add to .gitignore**: Never commit session data
3. **Encryption**: Consider encrypting session folder
4. **Access Control**: Limit who can access the watcher machine

## Troubleshooting

| Issue | Solution |
|-------|----------|
| QR code not showing | Run without `--headless` first |
| Session expired | Delete `whatsapp_session/` and re-login |
| Messages not detected | Check keyword list and chat visibility |
| Browser crash | Update Playwright: `playwright install` |
| Slow detection | Reduce `CHECK_INTERVAL` |

## Dependencies

```bash
pip install playwright
playwright install chromium
```

## Limitations

- WhatsApp Web must stay connected
- Phone needs internet connection
- Rate limits on frequent checks
- Cannot read encrypted media directly

## File Structure

```
AI_Employee_Vault/
├── whatsapp_watcher.py      # Main script
├── whatsapp_session/        # Browser session (gitignored)
│   ├── context.json
│   └── storage/
├── Needs_Action/
│   └── WA_*.md              # Detected messages
├── Logs/
│   └── whatsapp_log.md      # Activity log
└── Company_Handbook.md      # Keywords config
```
