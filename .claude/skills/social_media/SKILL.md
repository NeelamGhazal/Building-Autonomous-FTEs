# Social Media Integration Skill

## Overview

Facebook and Instagram posting automation with Mock Mode support. Enables the AI Employee to manage social media presence with HITL approval for all posts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Social Media Integration Flow                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────────┐  │
│  │  AI Employee   │────▶│ facebook_      │────▶│  HITL Approval     │  │
│  │  (Claude)      │     │ instagram.py   │     │  /Pending_Approval │  │
│  └────────────────┘     └────────┬───────┘     └─────────┬──────────┘  │
│                                  │                       │              │
│                                  ▼                       ▼              │
│                         ┌────────────────┐     ┌────────────────────┐  │
│                         │  Mock Mode     │     │  /Approved/        │  │
│                         │  (Simulated)   │◀────│  Human approves    │  │
│                         └────────┬───────┘     └────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│                         ┌────────────────────────────────────────────┐ │
│                         │  /Social_Media/facebook_posts.md          │ │
│                         │  /Social_Media/instagram_posts.md         │ │
│                         └────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Mock Mode

**Why Mock Mode?**
- Real Facebook/Instagram API requires approved Facebook App
- App review process takes weeks
- Mock Mode provides full workflow testing without API access

**What Mock Mode Does:**
- Simulates post creation with full logging
- Creates HITL approval requests (same as production)
- Saves posts to history files when approved
- Shows exactly what would be posted

## Features

### Facebook Page Posting
- Text posts to Facebook Page
- HITL approval required
- Post history saved to `/Social_Media/facebook_posts.md`

### Instagram Posting
- Text/caption posts to Instagram
- HITL approval required
- Post history saved to `/Social_Media/instagram_posts.md`

### Weekly Summary
- Aggregates all posts from the week
- Shows engagement metrics (simulated in Mock Mode)
- Platform breakdown

## CLI Commands

```bash
# Post to Facebook (creates HITL approval request)
python3 facebook_instagram.py --post-fb "Your message here"

# Post to Instagram (creates HITL approval request)
python3 facebook_instagram.py --post-ig "Your message here"

# View weekly summary
python3 facebook_instagram.py --summary

# Run full demo
python3 facebook_instagram.py --demo

# View post history
python3 facebook_instagram.py --history fb
python3 facebook_instagram.py --history ig

# Check status
python3 facebook_instagram.py --status
```

## HITL Approval Flow

### 1. Create Post Request
```bash
python3 facebook_instagram.py --post-fb "Excited to announce our new AI features!"
```

### 2. Approval File Created
```
/Pending_Approval/SOCIAL_MEDIA_POST_Facebook_20260228_230000.json
```

### 3. Approval File Format
```json
{
    "action_type": "SOCIAL_MEDIA_POST",
    "platform": "facebook",
    "post_type": "text_post",
    "content": "Excited to announce our new AI features!",
    "hashtags": ["#AI", "#Innovation"],
    "scheduled_time": null,
    "requires_approval": true,
    "created_at": "2026-02-28T23:00:00Z",
    "expires_at": "2026-03-01T23:00:00Z",
    "description": "Facebook post: Excited to announce our new AI features!"
}
```

### 4. Human Approval
- Move to `/Approved/` to publish
- Move to `/Rejected/` to cancel

### 5. Post Published (Mock Mode)
- Logged to `/Social_Media/facebook_posts.md`
- Confirmation logged

## Post History Format

### Facebook Posts (`/Social_Media/facebook_posts.md`)

```markdown
# Facebook Post History

## 2026-02-28 23:00:00

**Post ID:** FB_20260228_230000_abc123
**Status:** Published (Mock Mode)
**Content:**
Excited to announce our new AI features!

**Hashtags:** #AI #Innovation
**Engagement:** 0 likes, 0 comments, 0 shares (simulated)

---
```

### Instagram Posts (`/Social_Media/instagram_posts.md`)

```markdown
# Instagram Post History

## 2026-02-28 23:15:00

**Post ID:** IG_20260228_231500_def456
**Status:** Published (Mock Mode)
**Caption:**
Building the future of automation one line of code at a time.

**Hashtags:** #Coding #Automation #Tech
**Engagement:** 0 likes, 0 comments (simulated)

---
```

## Configuration

### Environment Variables (Future Use)

```bash
# Facebook (for production mode)
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_access_token

# Instagram (for production mode)
INSTAGRAM_BUSINESS_ID=your_business_id
INSTAGRAM_ACCESS_TOKEN=your_access_token

# Mode
SOCIAL_MEDIA_MOCK_MODE=true  # Default: true
```

## Platform Requirements (Production)

### Facebook
- Facebook Developer Account
- Approved Facebook App with `pages_manage_posts` permission
- Facebook Page (not personal profile)
- Page Access Token

### Instagram
- Instagram Business or Creator Account
- Connected to Facebook Page
- Facebook App with Instagram Graph API access

## Error Handling

| Error | Handling |
|-------|----------|
| API rate limit | Queue post, retry with backoff |
| Auth failure | Alert human, pause posting |
| Content policy | Log rejection, notify human |
| Network error | Retry 3 times with backoff |

## Security

1. **Credentials**: Never hardcoded (use environment variables)
2. **HITL**: All posts require human approval
3. **Audit**: All posts logged with timestamps
4. **Mock Mode**: Safe testing without API access

## File Structure

```
AI_Employee_Vault/
├── facebook_instagram.py          # Main script
├── Social_Media/
│   ├── facebook_posts.md          # FB post history
│   └── instagram_posts.md         # IG post history
├── Pending_Approval/
│   └── SOCIAL_MEDIA_POST_*.json   # Pending posts
└── .claude/
    └── skills/
        └── social_media/
            └── SKILL.md           # This file
```

## Integration with Other Components

### Audit Logger
All posts logged via `audit_logger.py`:
```python
log_action("CREATE_POST", "social_media", {
    "platform": "facebook",
    "post_id": "FB_123",
    "status": "published"
})
```

### CEO Briefing
Weekly briefing includes social media stats:
- Posts published this week
- Platform breakdown
- Engagement summary (when available)

### Scheduler
Can schedule recurring posts:
```python
scheduler.add_job(
    post_weekly_update,
    CronTrigger(day_of_week='fri', hour=10),
    id='weekly_social_post'
)
```

## Demo Output

```
$ python3 facebook_instagram.py --demo

============================================================
FACEBOOK + INSTAGRAM INTEGRATION DEMO
============================================================
Mode: MOCK (no real API calls)

[1/4] Creating Facebook post...
  Content: "AI automation is transforming how we work..."
  Approval request created: Pending_Approval/SOCIAL_MEDIA_POST_Facebook_20260228_230000.json

[2/4] Simulating approval...
  Moving to Approved folder...
  Post published (mock): FB_20260228_230000_abc123

[3/4] Creating Instagram post...
  Content: "Building intelligent systems..."
  Approval request created

[4/4] Generating weekly summary...

WEEKLY SUMMARY
--------------
Facebook: 1 post
Instagram: 1 post
Total engagement: 0 (mock mode)

Demo completed successfully!
============================================================
```

---

*Last Updated: 2026-02-28*
*Gold Tier Feature - Social Media Integration*
