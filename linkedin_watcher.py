#!/usr/bin/env python3
"""
LinkedIn Watcher & Auto Post for Silver Tier AI Employee

Monitors LinkedIn, generates AI-powered posts, and publishes with HITL approval.
Uses MOCK MODE by default - no real LinkedIn API calls.

Usage:
    python linkedin_watcher.py                      # Show help
    python linkedin_watcher.py --demo "topic"       # Run complete demo flow
    python linkedin_watcher.py --generate "topic"   # Generate post + approval request
    python linkedin_watcher.py --pending            # Show pending posts
    python linkedin_watcher.py --analytics          # View post analytics
    python linkedin_watcher.py --history            # View published posts history
    python linkedin_watcher.py --auth               # Authenticate with real LinkedIn API
    python linkedin_watcher.py --test               # Test connection

All posts REQUIRE human approval before publishing.
MOCK MODE: Posts are saved to /Logs/linkedin_posts.md instead of real LinkedIn.
"""

import os
import sys
import json
import logging
import requests
import webbrowser
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# === Configuration ===
BASE_DIR = Path(__file__).parent
CREDENTIALS_FILE = Path(os.environ.get("LINKEDIN_CREDENTIALS", BASE_DIR / "linkedin_credentials.json"))
TOKEN_FILE = Path(os.environ.get("LINKEDIN_TOKEN", BASE_DIR / "linkedin_token.json"))
TEMPLATES_FILE = BASE_DIR / "linkedin_templates.json"
PENDING_DIR = BASE_DIR / "Pending_Approval"
APPROVED_DIR = BASE_DIR / "Approved"
LOGS_DIR = BASE_DIR / "Logs"

LINKEDIN_LOG = LOGS_DIR / "linkedin_log.md"
LINKEDIN_POSTS = LOGS_DIR / "linkedin_posts.md"  # Published posts in mock mode
LINKEDIN_METRICS = LOGS_DIR / "linkedin_metrics.json"

# Mock mode - set to False to use real LinkedIn API
MOCK_MODE = True

# LinkedIn API endpoints
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"

# Default scopes
DEFAULT_SCOPES = ["openid", "profile", "email", "w_member_social"]

# === Logging Setup ===
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# === OAuth Callback Handler ===
class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from LinkedIn."""

    auth_code = None

    def do_GET(self):
        """Handle GET request with auth code."""
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if 'code' in params:
            OAuthCallbackHandler.auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>LinkedIn Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            """)
        else:
            error = params.get('error', ['Unknown error'])[0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"<h1>Error: {error}</h1>".encode())

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


# === LinkedIn Service ===
class LinkedInService:
    """Handles LinkedIn API authentication and operations."""

    _instance = None
    _access_token = None
    _user_id = None

    @classmethod
    def load_credentials(cls) -> Dict[str, Any]:
        """Load OAuth credentials."""
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"LinkedIn credentials not found at {CREDENTIALS_FILE}. "
                "Create this file with your LinkedIn app credentials."
            )

        with open(CREDENTIALS_FILE) as f:
            return json.load(f)

    @classmethod
    def load_token(cls) -> Optional[Dict[str, Any]]:
        """Load saved access token."""
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE) as f:
                    return json.load(f)
            except:
                return None
        return None

    @classmethod
    def save_token(cls, token_data: Dict[str, Any]):
        """Save access token."""
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        logger.info(f"Token saved to {TOKEN_FILE}")

    @classmethod
    def authenticate(cls, port: int = 8000) -> bool:
        """
        Run OAuth flow to authenticate with LinkedIn.
        Opens browser for user authorization.
        """
        try:
            creds = cls.load_credentials()
        except FileNotFoundError as e:
            print(f"\nError: {e}")
            print("\nCreate linkedin_credentials.json with:")
            print(json.dumps({
                "client_id": "YOUR_CLIENT_ID",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uri": f"http://localhost:{port}/callback"
            }, indent=2))
            return False

        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")
        redirect_uri = creds.get("redirect_uri", f"http://localhost:{port}/callback")
        scopes = creds.get("scopes", DEFAULT_SCOPES)

        # Build authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": "linkedin_auth_state"
        }
        auth_url = f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

        print(f"\nOpening browser for LinkedIn authorization...")
        print(f"If browser doesn't open, visit:\n{auth_url}\n")

        # Start local server to receive callback
        server = HTTPServer(('localhost', port), OAuthCallbackHandler)
        server.timeout = 120  # 2 minute timeout

        # Open browser
        webbrowser.open(auth_url)

        # Wait for callback
        print("Waiting for authorization...")
        server.handle_request()

        auth_code = OAuthCallbackHandler.auth_code
        if not auth_code:
            print("Authorization failed or timed out.")
            return False

        # Exchange code for token
        print("Exchanging code for access token...")
        token_response = requests.post(LINKEDIN_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret
        })

        if token_response.status_code != 200:
            print(f"Token exchange failed: {token_response.text}")
            return False

        token_data = token_response.json()
        token_data["obtained_at"] = datetime.utcnow().isoformat()
        token_data["expires_at"] = (
            datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
        ).isoformat()

        cls.save_token(token_data)
        cls._access_token = token_data.get("access_token")

        print("\nLinkedIn authentication successful!")

        # Get user profile
        profile = cls.get_profile()
        if profile:
            print(f"Logged in as: {profile.get('name', 'Unknown')}")

        return True

    @classmethod
    def get_access_token(cls) -> Optional[str]:
        """Get valid access token, refreshing if needed."""
        if cls._access_token:
            return cls._access_token

        token_data = cls.load_token()
        if not token_data:
            logger.warning("No LinkedIn token found. Run --auth to authenticate.")
            return None

        # Check expiry
        expires_at = token_data.get("expires_at")
        if expires_at:
            exp_time = datetime.fromisoformat(expires_at)
            if datetime.utcnow() > exp_time:
                logger.warning("LinkedIn token expired. Run --auth to re-authenticate.")
                return None

        cls._access_token = token_data.get("access_token")
        return cls._access_token

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """Get API request headers."""
        token = cls.get_access_token()
        if not token:
            raise ValueError("No valid access token")

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401"
        }

    @classmethod
    def get_profile(cls) -> Optional[Dict[str, Any]]:
        """Get current user's profile."""
        try:
            headers = cls.get_headers()

            # Get user info using OpenID userinfo endpoint
            response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                cls._user_id = data.get("sub")
                return {
                    "id": data.get("sub"),
                    "name": data.get("name"),
                    "email": data.get("email"),
                    "picture": data.get("picture")
                }
            else:
                logger.error(f"Profile fetch failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Profile fetch error: {e}")
            return None

    @classmethod
    def get_user_id(cls) -> Optional[str]:
        """Get current user's LinkedIn ID."""
        if cls._user_id:
            return cls._user_id

        profile = cls.get_profile()
        return profile.get("id") if profile else None

    @classmethod
    def create_post(
        cls,
        content: str,
        visibility: str = "PUBLIC",
        article_url: Optional[str] = None,
        article_title: Optional[str] = None,
        article_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a post on LinkedIn.

        Args:
            content: Post text content
            visibility: PUBLIC, CONNECTIONS, or LOGGED_IN
            article_url: URL to share (optional)
            article_title: Title for shared article (optional)
            article_description: Description for shared article (optional)

        Returns:
            Dict with 'success', 'post_id', and 'error' (if failed)
        """
        try:
            headers = cls.get_headers()
            user_id = cls.get_user_id()

            if not user_id:
                return {"success": False, "error": "Could not get user ID"}

            # Build post payload
            post_data = {
                "author": f"urn:li:person:{user_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility
                }
            }

            # Add article if provided
            if article_url:
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                    "status": "READY",
                    "originalUrl": article_url,
                    "title": {
                        "text": article_title or ""
                    },
                    "description": {
                        "text": article_description or ""
                    }
                }]

            # Create post
            response = requests.post(
                f"{LINKEDIN_API_BASE}/ugcPosts",
                headers=headers,
                json=post_data
            )

            if response.status_code in [200, 201]:
                post_id = response.headers.get("X-RestLi-Id", "unknown")
                logger.info(f"Post created successfully: {post_id}")
                log_post_activity("PUBLISHED", content[:50], post_id)
                return {
                    "success": True,
                    "post_id": post_id
                }
            else:
                error_msg = f"{response.status_code}: {response.text}"
                logger.error(f"Post creation failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"Post creation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# === AI Content Generation ===
def generate_post_with_ai(
    topic: str,
    post_type: str = "text",
    company_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate LinkedIn post content using Claude.

    Args:
        topic: Topic or theme for the post
        post_type: Type of post (text, thought_leadership, announcement)
        company_context: Optional company information for context

    Returns:
        Dict with 'content', 'hashtags', and 'suggested_time'
    """
    try:
        import anthropic

        client = anthropic.Anthropic()

        prompt = f"""Generate a professional LinkedIn post about: {topic}

Requirements:
- Professional but authentic tone
- 150-250 words optimal length
- Include a clear call-to-action
- Engaging opening line (hook)
- Add line breaks for readability
- Suggest 3-5 relevant hashtags

Post Type: {post_type}
{f'Company Context: {company_context}' if company_context else ''}

Return your response in this exact JSON format:
{{
    "content": "The full post content here...",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "hook": "The opening line",
    "cta": "The call to action",
    "suggested_time": "09:00"
}}
"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response_text = response.content[0].text

        # Try to extract JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
            result["ai_generated"] = True
            result["topic"] = topic
            return result
        else:
            # Fallback: use response as content
            return {
                "content": response_text,
                "hashtags": ["#business", "#linkedin"],
                "ai_generated": True,
                "topic": topic
            }

    except ImportError:
        logger.warning("anthropic package not installed. Using template.")
        return generate_post_from_template(topic, post_type)
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        return generate_post_from_template(topic, post_type)


def generate_post_from_template(topic: str, post_type: str = "text") -> Dict[str, Any]:
    """Generate post from templates (fallback)."""
    templates = {
        "text": f"""🚀 Thoughts on {topic}

In today's fast-paced business environment, staying ahead means constantly evolving.

Here's what I've learned:

1️⃣ Embrace change as opportunity
2️⃣ Focus on delivering value
3️⃣ Build genuine connections

What's your take on this? I'd love to hear your perspective in the comments!

""",
        "announcement": f"""📢 Exciting News: {topic}

We're thrilled to share this update with our community.

Stay tuned for more details coming soon!

""",
        "thought_leadership": f"""💡 {topic}: A Different Perspective

After years in this industry, here's what I've realized...

The key insight that changed everything for me was understanding that success isn't just about what you do—it's about why you do it.

What insights have shaped your journey?

"""
    }

    content = templates.get(post_type, templates["text"])

    return {
        "content": content,
        "hashtags": ["#business", "#leadership", "#growth"],
        "ai_generated": False,
        "topic": topic
    }


# === HITL Integration ===
def create_post_approval(
    content: str,
    hashtags: List[str],
    post_type: str = "text",
    visibility: str = "PUBLIC",
    article_url: Optional[str] = None,
    article_title: Optional[str] = None,
    ai_generated: bool = False,
    topic: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create HITL approval request for LinkedIn post.
    """
    try:
        from approval_watcher import create_approval_request
    except ImportError:
        return _create_approval_directly(
            content, hashtags, post_type, visibility,
            article_url, article_title, ai_generated, topic
        )

    # Format content with hashtags
    full_content = content
    if hashtags:
        full_content += "\n\n" + " ".join(hashtags)

    # Create approval request
    request_id = create_approval_request(
        action_type="SOCIAL_MEDIA_POST",
        description=f"LinkedIn {post_type} post: {topic or content[:30]}...",
        details={
            "platform": "linkedin",
            "post_type": post_type,
            "content": full_content,
            "content_preview": content[:200] + "..." if len(content) > 200 else content,
            "hashtags": hashtags,
            "visibility": visibility,
            "article_url": article_url,
            "article_title": article_title,
            "ai_generated": ai_generated,
            "topic": topic
        },
        who_is_affected="LinkedIn followers/connections",
        amount_if_payment=None,
        callback_data={
            "content": full_content,
            "visibility": visibility,
            "article_url": article_url,
            "article_title": article_title
        }
    )

    return {
        "status": "pending_approval",
        "request_id": request_id,
        "content_preview": content[:100] + "...",
        "message": f"Post queued for approval. Move file to {APPROVED_DIR}/ to publish."
    }


def _create_approval_directly(
    content: str,
    hashtags: List[str],
    post_type: str,
    visibility: str,
    article_url: Optional[str],
    article_title: Optional[str],
    ai_generated: bool,
    topic: Optional[str]
) -> Dict[str, Any]:
    """Create approval file directly (fallback)."""
    import uuid

    PENDING_DIR.mkdir(exist_ok=True)

    request_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(hours=24)

    full_content = content + "\n\n" + " ".join(hashtags) if hashtags else content

    timestamp = created_at.strftime("%Y%m%d_%H%M%S")
    safe_topic = (topic or "post")[:20].replace(" ", "_")
    filename = f"SOCIAL_MEDIA_POST_linkedin_{safe_topic}_{timestamp}.json"

    request_data = {
        "request_id": request_id,
        "action_type": "SOCIAL_MEDIA_POST",
        "description": f"LinkedIn {post_type} post: {topic or content[:30]}",
        "details": {
            "platform": "linkedin",
            "post_type": post_type,
            "content": full_content,
            "content_preview": content[:200],
            "hashtags": hashtags,
            "visibility": visibility,
            "ai_generated": ai_generated
        },
        "who_is_affected": "LinkedIn followers/connections",
        "amount_if_payment": None,
        "created_at": created_at.isoformat() + "Z",
        "expires_at": expires_at.isoformat() + "Z",
        "status": "PENDING",
        "how_to_approve": f"Move this file to {APPROVED_DIR}/ folder",
        "how_to_reject": f"Move this file to {BASE_DIR}/Rejected/ folder",
        "callback_data": {
            "content": full_content,
            "visibility": visibility,
            "article_url": article_url,
            "article_title": article_title
        }
    }

    filepath = PENDING_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(request_data, f, indent=2)

    logger.info(f"Post approval request created: {filename}")

    return {
        "status": "pending_approval",
        "request_id": request_id,
        "content_preview": content[:100],
        "approval_file": str(filepath)
    }


# === Logging ===
def log_post_activity(action: str, content_preview: str, post_id: Optional[str] = None):
    """Log post activity to markdown file."""
    LOGS_DIR.mkdir(exist_ok=True)

    now = datetime.now()
    date_header = now.strftime("## %Y-%m-%d")

    # Read existing log
    if LINKEDIN_LOG.exists():
        log_content = LINKEDIN_LOG.read_text()
    else:
        log_content = "# LinkedIn Activity Log\n\n"

    # Add date header if not present
    if date_header not in log_content:
        log_content += f"\n{date_header}\n\n"

    # Add entry
    entry = f"""### {action}: {now.strftime('%H:%M')}
- **Content:** {content_preview}...
- **Post ID:** {post_id or 'N/A'}
- **Status:** {'✅ Published' if action == 'PUBLISHED' else '⏳ Pending'}

---

"""

    log_content += entry
    LINKEDIN_LOG.write_text(log_content)


def save_post_metrics(post_id: str, metrics: Dict[str, Any]):
    """Save post metrics to JSON file."""
    LOGS_DIR.mkdir(exist_ok=True)

    # Load existing metrics
    if LINKEDIN_METRICS.exists():
        data = json.loads(LINKEDIN_METRICS.read_text())
    else:
        data = {"posts": []}

    # Update or add metrics
    for post in data["posts"]:
        if post.get("post_id") == post_id:
            post["metrics"] = metrics
            post["last_updated"] = datetime.utcnow().isoformat()
            break
    else:
        data["posts"].append({
            "post_id": post_id,
            "metrics": metrics,
            "last_updated": datetime.utcnow().isoformat()
        })

    LINKEDIN_METRICS.write_text(json.dumps(data, indent=2))


# === Mock Mode Publishing ===
def mock_publish_post(
    content: str,
    visibility: str = "PUBLIC",
    article_url: Optional[str] = None,
    article_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mock publish - saves post to /Logs/linkedin_posts.md instead of real LinkedIn.
    """
    import uuid

    LOGS_DIR.mkdir(exist_ok=True)

    # Generate mock post ID
    post_id = f"mock_urn:li:share:{uuid.uuid4().hex[:12]}"
    now = datetime.now()

    # Create/update posts log
    if LINKEDIN_POSTS.exists():
        posts_content = LINKEDIN_POSTS.read_text()
    else:
        posts_content = """# LinkedIn Posts (Mock Mode)

This file contains all posts that would have been published to LinkedIn.
In production mode, these would be real LinkedIn posts.

---

"""

    # Add new post entry
    post_entry = f"""## Post Published: {now.strftime('%Y-%m-%d %H:%M:%S')}

**Post ID:** `{post_id}`
**Visibility:** {visibility}
**Mode:** MOCK (not sent to real LinkedIn)

### Content:

```
{content}
```

"""

    if article_url:
        post_entry += f"""### Shared Article:
- **URL:** {article_url}
- **Title:** {article_title or 'N/A'}

"""

    post_entry += """### Mock Engagement (Simulated):
- Impressions: ~500-2000
- Likes: ~20-50
- Comments: ~5-15
- Shares: ~2-8

---

"""

    posts_content += post_entry
    LINKEDIN_POSTS.write_text(posts_content)

    # Also log to activity log
    log_post_activity("PUBLISHED (Mock)", content[:50], post_id)

    # Print success message
    print("\n" + "="*60)
    print("✅ POST PUBLISHED TO LINKEDIN (Mock Mode)")
    print("="*60)
    print(f"\nPost ID: {post_id}")
    print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Visibility: {visibility}")
    print("\n--- POST CONTENT ---")
    print(content)
    print("--- END CONTENT ---")
    print(f"\nSaved to: {LINKEDIN_POSTS}")
    print("="*60 + "\n")

    return {
        "success": True,
        "post_id": post_id,
        "mock_mode": True
    }


# === Register with Approval Watcher ===
def register_linkedin_executor():
    """Register LinkedIn post executor with approval watcher."""
    try:
        from approval_watcher import register_executor

        @register_executor("SOCIAL_MEDIA_POST")
        def execute_social_post(request: Dict[str, Any]) -> bool:
            """Execute social media post when approved."""
            details = request.get("details", {})
            callback_data = request.get("callback_data", {})

            platform = details.get("platform", "").lower()

            if platform != "linkedin":
                logger.info(f"Skipping non-LinkedIn platform: {platform}")
                return True  # Not our concern

            # Use mock mode or real API
            if MOCK_MODE:
                result = mock_publish_post(
                    content=callback_data.get("content", ""),
                    visibility=callback_data.get("visibility", "PUBLIC"),
                    article_url=callback_data.get("article_url"),
                    article_title=callback_data.get("article_title")
                )
            else:
                result = LinkedInService.create_post(
                    content=callback_data.get("content", ""),
                    visibility=callback_data.get("visibility", "PUBLIC"),
                    article_url=callback_data.get("article_url"),
                    article_title=callback_data.get("article_title")
                )

            return result.get("success", False)

        logger.info(f"LinkedIn executor registered (Mock Mode: {MOCK_MODE})")

    except ImportError:
        logger.warning("Could not register with approval_watcher")


# === CLI Functions ===
def show_analytics():
    """Display post analytics."""
    print("\n" + "="*60)
    print("LINKEDIN POST ANALYTICS")
    print("="*60)

    if not LINKEDIN_METRICS.exists():
        print("No analytics data available yet.")
        print("="*60 + "\n")
        return

    data = json.loads(LINKEDIN_METRICS.read_text())

    for post in data.get("posts", [])[:10]:  # Show last 10
        print(f"\nPost ID: {post.get('post_id', 'N/A')}")
        metrics = post.get("metrics", {})
        print(f"  Impressions: {metrics.get('impressions', 'N/A')}")
        print(f"  Likes: {metrics.get('likes', 'N/A')}")
        print(f"  Comments: {metrics.get('comments', 'N/A')}")
        print(f"  Shares: {metrics.get('shares', 'N/A')}")

    print("\n" + "="*60)


def show_pending():
    """Show pending LinkedIn posts."""
    print("\n" + "="*60)
    print("PENDING LINKEDIN POSTS")
    print("="*60)

    if not PENDING_DIR.exists():
        print("No pending posts.")
        print("="*60 + "\n")
        return

    found = False
    for filepath in PENDING_DIR.glob("SOCIAL_MEDIA_POST_linkedin_*.json"):
        found = True
        try:
            data = json.loads(filepath.read_text())
            details = data.get("details", {})
            print(f"\nFile: {filepath.name}")
            print(f"Topic: {details.get('topic', 'N/A')}")
            print(f"Preview: {details.get('content_preview', '')[:100]}...")
            print(f"Expires: {data.get('expires_at', 'N/A')}")
        except:
            print(f"\nFile: {filepath.name} (error reading)")

    if not found:
        print("No pending posts.")

    print("\n" + "="*60)


def test_connection():
    """Test LinkedIn API connection."""
    print("\nTesting LinkedIn connection...")

    if MOCK_MODE:
        print("✅ Running in MOCK MODE - no real LinkedIn connection needed")
        print("   Posts will be saved to /Logs/linkedin_posts.md")
        return

    profile = LinkedInService.get_profile()
    if profile:
        print(f"✅ Connected successfully!")
        print(f"   Name: {profile.get('name')}")
        print(f"   Email: {profile.get('email')}")
        print(f"   ID: {profile.get('id')}")
    else:
        print("❌ Connection failed. Run --auth to authenticate.")


def show_history():
    """Show published posts history."""
    print("\n" + "="*60)
    print("LINKEDIN POSTS HISTORY (Mock Mode)")
    print("="*60)

    if not LINKEDIN_POSTS.exists():
        print("\nNo posts published yet.")
        print("Use --demo or --generate to create posts.")
        print("="*60 + "\n")
        return

    content = LINKEDIN_POSTS.read_text()
    print(content)


def run_demo(topic: str):
    """
    Run complete demo flow:
    1. Generate AI post
    2. Create approval request
    3. Auto-approve
    4. Publish (mock mode)
    """
    import shutil
    import time

    print("\n" + "="*70)
    print("🎬 LINKEDIN AUTO-POST DEMO")
    print("="*70)
    print(f"\nTopic: {topic}")
    print(f"Mode: {'MOCK' if MOCK_MODE else 'LIVE'}")
    print("\n" + "-"*70)

    # Step 1: Generate post
    print("\n📝 STEP 1: Generating AI-powered post content...")
    print("-"*70)
    time.sleep(1)

    post_data = generate_post_with_ai(topic)
    content = post_data.get("content", "")
    hashtags = post_data.get("hashtags", [])

    print("\nGenerated Content:")
    print("-"*40)
    print(content)
    print("\nHashtags:", " ".join(hashtags))
    print("-"*70)

    # Step 2: Create approval request
    print("\n📋 STEP 2: Creating HITL approval request...")
    print("-"*70)
    time.sleep(1)

    result = create_post_approval(
        content=content,
        hashtags=hashtags,
        post_type="text",
        ai_generated=post_data.get("ai_generated", False),
        topic=topic
    )

    request_id = result.get("request_id")
    print(f"\nApproval request created!")
    print(f"Request ID: {request_id}")

    # Find the approval file
    approval_file = None
    for f in PENDING_DIR.glob("SOCIAL_MEDIA_POST_*.json"):
        try:
            data = json.loads(f.read_text())
            if data.get("request_id") == request_id:
                approval_file = f
                break
        except:
            pass

    if not approval_file:
        print("Error: Could not find approval file")
        return

    print(f"File: {approval_file.name}")
    print("-"*70)

    # Step 3: Simulate human approval
    print("\n✋ STEP 3: Simulating human approval...")
    print("-"*70)
    print("\nIn production, you would:")
    print(f"  1. Review the file in /Pending_Approval/")
    print(f"  2. Move it to /Approved/ to publish")
    print(f"\nFor demo, auto-approving in 3 seconds...")

    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    # Move file to Approved
    APPROVED_DIR.mkdir(exist_ok=True)
    approved_file = APPROVED_DIR / approval_file.name
    shutil.move(str(approval_file), str(approved_file))
    print(f"\n✅ File moved to /Approved/")
    print("-"*70)

    # Step 4: Execute (mock publish)
    print("\n🚀 STEP 4: Publishing to LinkedIn...")
    print("-"*70)
    time.sleep(1)

    # Read the approved request and execute
    with open(approved_file) as f:
        request_data = json.load(f)

    callback_data = request_data.get("callback_data", {})

    # Publish
    pub_result = mock_publish_post(
        content=callback_data.get("content", ""),
        visibility=callback_data.get("visibility", "PUBLIC"),
        article_url=callback_data.get("article_url"),
        article_title=callback_data.get("article_title")
    )

    # Update file status
    request_data["status"] = "EXECUTED"
    request_data["executed_at"] = datetime.utcnow().isoformat() + "Z"
    request_data["post_id"] = pub_result.get("post_id")
    with open(approved_file, 'w') as f:
        json.dump(request_data, f, indent=2)

    # Final summary
    print("\n" + "="*70)
    print("🎉 DEMO COMPLETE!")
    print("="*70)
    print(f"\n✅ Post generated with AI")
    print(f"✅ HITL approval request created")
    print(f"✅ Human approval simulated")
    print(f"✅ Post published (Mock Mode)")
    print(f"\nPost ID: {pub_result.get('post_id')}")
    print(f"\nView published posts: python linkedin_watcher.py --history")
    print(f"View activity log: {LINKEDIN_LOG}")
    print("="*70 + "\n")


# === Main Entry Point ===
if __name__ == "__main__":
    # Register executor on import
    register_linkedin_executor()

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--demo":
            if len(sys.argv) > 2:
                topic = " ".join(sys.argv[2:])
            else:
                topic = "AI automation is transforming modern business"
            run_demo(topic)

        elif arg == "--auth":
            LinkedInService.authenticate()

        elif arg == "--generate":
            if len(sys.argv) > 2:
                topic = " ".join(sys.argv[2:])
            else:
                topic = input("Enter topic for post: ")

            print(f"\nGenerating post about: {topic}")
            post_data = generate_post_with_ai(topic)

            print("\n" + "="*50)
            print("GENERATED POST CONTENT")
            print("="*50)
            print(post_data.get("content", ""))
            print("\nHashtags:", " ".join(post_data.get("hashtags", [])))
            print("="*50)

            confirm = input("\nCreate approval request? (y/n): ")
            if confirm.lower() == 'y':
                result = create_post_approval(
                    content=post_data.get("content", ""),
                    hashtags=post_data.get("hashtags", []),
                    post_type="text",
                    ai_generated=post_data.get("ai_generated", False),
                    topic=topic
                )
                print(f"\n✅ Approval request created!")
                print(f"Request ID: {result.get('request_id')}")
                print(f"Move file from Pending_Approval/ to Approved/ to publish.")

        elif arg == "--analytics":
            show_analytics()

        elif arg == "--pending":
            show_pending()

        elif arg == "--history":
            show_history()

        elif arg == "--test":
            test_connection()

        elif arg == "--help":
            print(__doc__)

        else:
            print(f"Unknown option: {arg}")
            print(__doc__)

    else:
        print(__doc__)
        print(f"\nMode: {'MOCK' if MOCK_MODE else 'LIVE'}")
        print("\nQuick start:")
        print("  python linkedin_watcher.py --demo \"AI in business\"")
        print("  python linkedin_watcher.py --generate \"your topic here\"")
