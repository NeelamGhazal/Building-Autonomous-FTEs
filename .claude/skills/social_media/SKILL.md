# Social Media Integration Skill

## Overview

Social media posting automation with Mock Mode support for Facebook, Instagram, and Twitter/X. Enables the AI Employee to manage social media presence with HITL approval for all posts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Social Media Integration Flow                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐     ┌────────────────────────────────────────────┐  │
│  │  AI Employee   │────▶│  Social Media Scripts                      │  │
│  │  (Claude)      │     │  - facebook_instagram.py                   │  │
│  └────────────────┘     │  - twitter_x.py                            │  │
│                         └──────────────────┬─────────────────────────┘  │
│                                            │                             │
│                                            ▼                             │
│                         ┌────────────────────────────────────────────┐  │
│                         │  HITL Approval (/Pending_Approval/)        │  │
│                         └──────────────────┬─────────────────────────┘  │
│                                            │                             │
│                                            ▼                             │
│                         ┌────────────────────────────────────────────┐  │
│                         │  Human Approves → /Approved/               │  │
│                         │  Human Rejects  → /Rejected/               │  │
│                         └──────────────────┬─────────────────────────┘  │
│                                            │                             │
│                                            ▼                             │
│                         ┌────────────────────────────────────────────┐  │
│                         │  Mock Publish → /Social_Media/             │  │
│                         │  - facebook_posts.md                       │  │
│                         │  - instagram_posts.md                      │  │
│                         │  - twitter_posts.md                        │  │
│                         └────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Supported Platforms

| Platform | Script | Character Limit | Status |
|----------|--------|-----------------|--------|
| Facebook | facebook_instagram.py | Unlimited | Mock Mode |
| Instagram | facebook_instagram.py | 2,200 | Mock Mode |
| Twitter/X | twitter_x.py | 280 | Mock Mode |

## Mock Mode

**Why Mock Mode?**
- Real APIs require approved developer accounts
- App review processes take weeks
- Mock Mode provides full workflow testing without API access

**What Mock Mode Does:**
- Simulates post creation with full logging
- Creates HITL approval requests (same as production)
- Saves posts to history files when approved
- Shows exactly what would be posted

## CLI Commands

### Facebook & Instagram

```bash
# Post to Facebook
python3 facebook_instagram.py --post-fb "Your message"

# Post to Instagram
python3 facebook_instagram.py --post-ig "Your message"

# View summary
python3 facebook_instagram.py --summary

# Run demo
python3 facebook_instagram.py --demo

# View history
python3 facebook_instagram.py --history fb
python3 facebook_instagram.py --history ig

# Check status
python3 facebook_instagram.py --status
```

### Twitter/X

```bash
# Post a tweet (280 char limit)
python3 twitter_x.py --tweet "Your message"

# View summary
python3 twitter_x.py --summary

# Run demo
python3 twitter_x.py --demo

# View history
python3 twitter_x.py --history

# Check status
python3 twitter_x.py --status
```

## Twitter Character Limit

Twitter has a **280 character limit**. The system:
- Counts characters before submission
- Warns if limit exceeded
- Shows remaining characters
- Includes warning in approval file

```bash
$ python3 twitter_x.py --tweet "Short tweet"
Characters: 12/280
Status: pending_approval

$ python3 twitter_x.py --tweet "Very long tweet..."
WARNING: Tweet is 350 characters (limit: 280)
Exceeds limit by 70 characters
```

## HITL Approval Flow

### 1. Create Post Request
```bash
python3 twitter_x.py --tweet "Excited about AI automation! #AI #Tech"
```

### 2. Approval File Created
```
/Pending_Approval/TWEET_Excited_about_AI_20260304_211500.json
```

### 3. Approval File Format (Twitter)
```json
{
    "action_type": "TWEET",
    "platform": "twitter",
    "tweet_id": "TW_20260304_211500_abc123",
    "content": "Excited about AI automation! #AI #Tech",
    "character_count": 39,
    "character_limit": 280,
    "exceeds_limit": false,
    "hashtags": ["#AI", "#Tech"],
    "mentions": [],
    "mock_mode": true,
    "requires_approval": true,
    "created_at": "2026-03-04T21:15:00Z",
    "expires_at": "2026-03-05T21:15:00Z"
}
```

### 4. Human Approval
- Move to `/Approved/` to publish
- Move to `/Rejected/` to cancel

### 5. Post Published (Mock Mode)
- Logged to `/Social_Media/twitter_posts.md`
- Confirmation logged

## Post History Format

### Twitter Posts (`/Social_Media/twitter_posts.md`)

```markdown
# Twitter/X Post History

## 2026-03-04 21:15:00

**Tweet ID:** TW_20260304_211500_abc123
**Status:** Published (Mock Mode)
**Characters:** 39/280

**Content:**
Excited about AI automation! #AI #Tech

**Hashtags:** #AI #Tech
**Mentions:** None
**Engagement:** 0 likes, 0 retweets, 0 replies (simulated)

---
```

## Configuration

### Environment Variables

```bash
# Twitter (for production mode)
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
TWITTER_MOCK_MODE=true  # Default: true

# Facebook (for production mode)
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_access_token
SOCIAL_MEDIA_MOCK_MODE=true  # Default: true

# Instagram (for production mode)
INSTAGRAM_BUSINESS_ID=your_business_id
INSTAGRAM_ACCESS_TOKEN=your_access_token
```

## Platform Requirements (Production)

### Twitter/X
- Twitter Developer Account
- Approved App with OAuth 2.0
- Read and Write permissions
- API v2 access

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
| Character limit | Warn user, include in approval |

## Security

1. **Credentials**: Never hardcoded (use environment variables)
2. **HITL**: All posts require human approval
3. **Audit**: All posts logged with timestamps
4. **Mock Mode**: Safe testing without API access

## File Structure

```
AI_Employee_Vault/
├── facebook_instagram.py          # FB + IG script
├── twitter_x.py                   # Twitter/X script
├── Social_Media/
│   ├── facebook_posts.md          # FB post history
│   ├── instagram_posts.md         # IG post history
│   └── twitter_posts.md           # Twitter post history
├── Pending_Approval/
│   ├── SOCIAL_MEDIA_POST_*.json   # FB/IG pending posts
│   └── TWEET_*.json               # Twitter pending posts
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
    "platform": "twitter",
    "post_id": "TW_123",
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

### Twitter Demo
```
$ python3 twitter_x.py --demo

============================================================
TWITTER/X INTEGRATION DEMO
============================================================
Mode: MOCK (no real API calls)
Character Limit: 280

[1/4] Creating a valid tweet...
  Content: "Excited to share our latest AI automation features!..."
  Characters: 115/280
  Status: pending_approval

[2/4] Simulating approval...
  Moved to Approved folder
  Tweet published (mock): TW_20260304_211500_abc123

[3/4] Creating tweet with mentions...
  Content: "Great insights from @TechLeader on AI trends!..."
  Mentions: ['@TechLeader']
  Status: published

[4/4] Testing character limit warning...
  Content length: 344 characters
  Limit: 280 characters
  Status: Would be rejected/truncated

Demo completed successfully!
============================================================
```

---

*Last Updated: 2026-03-04*
*Gold Tier Feature - Social Media Integration (FB, IG, Twitter/X)*
