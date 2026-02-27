# LinkedIn Watcher & Auto Post Skill

## Overview

Automated LinkedIn management system that monitors notifications, generates AI-powered business posts, and publishes content with mandatory human approval. Part of the Silver Tier AI Employee system.

**Default Mode: MOCK** - Posts are saved to `/Logs/linkedin_posts.md` instead of real LinkedIn API. No LinkedIn credentials required for testing.

## Quick Start (Mock Mode)

```bash
# Run complete demo flow
python linkedin_watcher.py --demo "AI automation in business"

# Generate post with approval request
python linkedin_watcher.py --generate "your topic here"

# View published posts (mock)
python linkedin_watcher.py --history
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LinkedIn Automation Flow                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │  Scheduler   │───▶│   Claude     │───▶│  HITL Approval       │   │
│  │  Triggers    │    │  Generates   │    │  /Pending_Approval/  │   │
│  └──────────────┘    │  Post        │    └──────────┬───────────┘   │
│                      └──────────────┘               │               │
│                                                     │               │
│                           ┌─────────────────────────┼───────┐       │
│                           │                         │       │       │
│                           ▼                         ▼       ▼       │
│                    ┌────────────┐           ┌────────┐ ┌────────┐   │
│                    │  Approved  │           │Rejected│ │Expired │   │
│                    └─────┬──────┘           └────────┘ └────────┘   │
│                          │                                          │
│                          ▼                                          │
│                    ┌──────────────┐                                 │
│                    │ LinkedIn API │                                 │
│                    │  Publishes   │                                 │
│                    └──────┬───────┘                                 │
│                          │                                          │
│                          ▼                                          │
│                    ┌──────────────┐                                 │
│                    │ Performance  │                                 │
│                    │ Logged       │                                 │
│                    └──────────────┘                                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

### 1. Post Generation
- AI-generated business posts using Claude
- Multiple post types: text, article shares, polls
- Industry-specific content templates
- Hashtag suggestions
- Optimal posting time recommendations

### 2. HITL Approval
- All posts require human approval before publishing
- Full preview of post content
- Edit capability before approval
- 24-hour expiry on pending posts

### 3. Performance Tracking
- Engagement metrics (likes, comments, shares)
- Reach and impressions
- Historical performance data
- Weekly analytics reports

## Mock Mode (Default)

Mock mode allows you to test the entire flow without LinkedIn API credentials.

### What Mock Mode Does:
1. **Generates posts** using Claude AI (or templates)
2. **Creates HITL approval requests** in `/Pending_Approval/`
3. **Saves posts to file** instead of real LinkedIn
4. **Logs all activity** for review

### Mock Mode Files:
- `/Logs/linkedin_posts.md` - All "published" posts
- `/Logs/linkedin_log.md` - Activity log

### Demo Command

Run the complete flow in one command:

```bash
python linkedin_watcher.py --demo "AI automation in business"
```

This will:
1. Generate AI-powered post content
2. Create HITL approval request
3. Auto-approve after 3 seconds (simulating human)
4. Publish post (to mock file)
5. Show complete results

### Switching to Live Mode

To use real LinkedIn API, edit `linkedin_watcher.py`:
```python
MOCK_MODE = False  # Change from True to False
```

Then set up LinkedIn API credentials (see below).

## LinkedIn API Setup (Live Mode)

### Step 1: Create LinkedIn App

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Create a new app
3. Request the following products:
   - **Share on LinkedIn** (for posting)
   - **Sign In with LinkedIn using OpenID Connect**

### Step 2: Get OAuth Credentials

Required permissions (scopes):
```
openid
profile
email
w_member_social    # Required for posting
```

### Step 3: Configure Environment

Create `linkedin_credentials.json`:
```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8000/callback",
  "scopes": ["openid", "profile", "email", "w_member_social"]
}
```

### Step 4: Authenticate

```bash
python linkedin_watcher.py --auth
```

This will:
1. Open browser for LinkedIn OAuth
2. Get authorization code
3. Exchange for access token
4. Save token to `linkedin_token.json`

## Post Types

### Text Post
```json
{
  "type": "text",
  "content": "Excited to announce our new product launch! 🚀\n\nAfter months of development...",
  "hashtags": ["#startup", "#innovation", "#tech"],
  "visibility": "PUBLIC"
}
```

### Article Share
```json
{
  "type": "article",
  "content": "Great insights on AI in business:",
  "article_url": "https://example.com/article",
  "article_title": "AI Revolution in 2024",
  "article_description": "How AI is transforming...",
  "hashtags": ["#AI", "#business"]
}
```

### Poll (Future)
```json
{
  "type": "poll",
  "question": "What's your biggest challenge?",
  "options": ["Hiring", "Funding", "Growth", "Technology"],
  "duration_days": 7
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_CREDENTIALS` | `linkedin_credentials.json` | OAuth credentials file |
| `LINKEDIN_TOKEN` | `linkedin_token.json` | Access token file |
| `POST_SCHEDULE` | `0 9 * * 1-5` | Default posting schedule |
| `MAX_DAILY_POSTS` | `2` | Maximum posts per day |

### Post Templates

Configure in `linkedin_templates.json`:
```json
{
  "product_launch": {
    "template": "🚀 Exciting news! We're launching {product_name}...",
    "hashtags": ["#launch", "#innovation"],
    "best_time": "09:00"
  },
  "thought_leadership": {
    "template": "Here's what I've learned about {topic}...",
    "hashtags": ["#leadership", "#insights"],
    "best_time": "08:00"
  },
  "company_update": {
    "template": "Quick update from {company_name}...",
    "hashtags": ["#update", "#business"],
    "best_time": "12:00"
  }
}
```

## Usage

### CLI Commands

```bash
# Start the watcher daemon
python linkedin_watcher.py

# Authenticate with LinkedIn
python linkedin_watcher.py --auth

# Generate a new post (creates approval request)
python linkedin_watcher.py --generate "product launch announcement"

# Check post status
python linkedin_watcher.py --status <request_id>

# View analytics
python linkedin_watcher.py --analytics

# List pending posts
python linkedin_watcher.py --pending

# Test API connection
python linkedin_watcher.py --test
```

### Programmatic Usage

```python
from linkedin_watcher import LinkedInService, create_post_approval

# Generate and queue post for approval
result = create_post_approval(
    post_type="text",
    content="Excited to share our Q4 results!",
    hashtags=["#business", "#growth"],
    generate_with_ai=True,  # Let Claude enhance the content
    topic="quarterly business update"
)

print(f"Approval request: {result['request_id']}")
```

## HITL Approval Format

When a post is generated, this file is created in `/Pending_Approval/`:

```json
{
  "request_id": "uuid-v4",
  "action_type": "SOCIAL_MEDIA_POST",
  "description": "LinkedIn post: Product Launch Announcement",
  "details": {
    "platform": "linkedin",
    "post_type": "text",
    "content": "Full post content here...",
    "hashtags": ["#launch", "#tech"],
    "visibility": "PUBLIC",
    "scheduled_time": null,
    "ai_generated": true,
    "topic": "product launch"
  },
  "who_is_affected": "LinkedIn followers (5,000+)",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-16T10:30:00Z",
  "status": "PENDING",
  "how_to_approve": "Move this file to /Approved/ folder",
  "how_to_reject": "Move this file to /Rejected/ folder",
  "callback_data": {
    "post_type": "text",
    "content": "...",
    "hashtags": [...],
    "visibility": "PUBLIC"
  }
}
```

## Logging

### Post Log (`/Logs/linkedin_log.md`)

```markdown
# LinkedIn Activity Log

## 2024-01-15

### Post Published: Product Launch
- **Time:** 09:30 AM
- **Type:** Text Post
- **Status:** Published ✅
- **Post ID:** urn:li:share:123456789

### Performance (24h)
- Impressions: 1,234
- Likes: 45
- Comments: 12
- Shares: 8
- Engagement Rate: 5.3%

---
```

### Detailed Metrics (`/Logs/linkedin_metrics.json`)

```json
{
  "posts": [
    {
      "post_id": "urn:li:share:123456789",
      "published_at": "2024-01-15T09:30:00Z",
      "content_preview": "Excited to announce...",
      "metrics": {
        "impressions": 1234,
        "likes": 45,
        "comments": 12,
        "shares": 8,
        "engagement_rate": 5.3
      },
      "last_updated": "2024-01-16T09:30:00Z"
    }
  ]
}
```

## AI Content Generation

The system uses Claude to generate engaging posts:

```python
# Example prompt sent to Claude
prompt = """
Generate a LinkedIn post about: {topic}

Requirements:
- Professional tone
- 150-300 words
- Include a call-to-action
- Suggest 3-5 relevant hashtags
- Make it engaging and authentic

Company context:
{company_info}

Recent posts to avoid repetition:
{recent_posts}
"""
```

## Integration with Scheduler

Add to `scheduler.py` for automated posting:

```python
# Daily thought leadership post (9 AM weekdays)
scheduler.add_job(
    generate_daily_post,
    CronTrigger(hour=9, minute=0, day_of_week='mon-fri'),
    id='linkedin_daily_post',
    name='Generate LinkedIn Post'
)

# Weekly analytics update (Monday 8 AM)
scheduler.add_job(
    fetch_post_analytics,
    CronTrigger(hour=8, minute=0, day_of_week='mon'),
    id='linkedin_analytics',
    name='Fetch LinkedIn Analytics'
)
```

## Security Considerations

1. **Token Storage**: Access tokens stored securely, never committed to git
2. **HITL Required**: No automated posting without human approval
3. **Rate Limiting**: Respects LinkedIn API limits (100 requests/day)
4. **Audit Trail**: All posts logged with timestamps and content

## Rate Limits

LinkedIn API limits:
- **Share API**: 100 calls per day per member
- **UGC Posts**: 25 posts per day
- **Profile API**: 100 calls per day

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Token expired | Run `--auth` to re-authenticate |
| Post not publishing | Check approval status and API limits |
| Low engagement | Review posting times and content |
| API errors | Check credentials and permissions |

## Dependencies

```bash
pip install requests anthropic
```

## File Structure

```
AI_Employee_Vault/
├── linkedin_watcher.py         # Main script
├── linkedin_credentials.json   # OAuth credentials (gitignored)
├── linkedin_token.json         # Access token (gitignored)
├── linkedin_templates.json     # Post templates
├── Pending_Approval/           # Posts awaiting approval
├── Logs/
│   ├── linkedin_log.md         # Human-readable log
│   └── linkedin_metrics.json   # Detailed metrics
└── .gitignore                  # Exclude credentials
```
