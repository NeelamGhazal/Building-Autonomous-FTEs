#!/usr/bin/env python3
"""
Email MCP Server for Silver Tier AI Employee

MCP (Model Context Protocol) server that exposes email sending capabilities
via Gmail with mandatory HITL (Human-in-the-Loop) approval.

Usage:
    python email_mcp_server.py              # Run as MCP server (stdio)
    python email_mcp_server.py --test       # Test Gmail connection
    python email_mcp_server.py --reauth     # Re-authenticate Gmail

MCP Tools:
    - send_email: Queue an email for approval and send when approved
    - check_email_status: Check status of a pending email
    - list_pending_emails: List all emails awaiting approval
"""

import os
import sys
import json
import base64
import pickle
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: MCP package not installed. Install with: pip install mcp", file=sys.stderr)

# === Configuration ===
BASE_DIR = Path(__file__).parent
CREDENTIALS_FILE = Path(os.environ.get("GMAIL_CREDENTIALS", BASE_DIR / "credentials.json"))
TOKEN_FILE = Path(os.environ.get("GMAIL_TOKEN", BASE_DIR / "token.pickle"))
PENDING_DIR = BASE_DIR / "Pending_Approval"
APPROVED_DIR = BASE_DIR / "Approved"
REJECTED_DIR = BASE_DIR / "Rejected"
LOGS_DIR = BASE_DIR / "Logs"
EMAIL_LOG = LOGS_DIR / "email_sent.log"

# Gmail scopes - need send permission
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
]

# === Logging Setup ===
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(EMAIL_LOG),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


# === Gmail Service ===
class GmailService:
    """Handles Gmail API authentication and operations."""

    _instance = None
    _service = None

    @classmethod
    def get_service(cls):
        """Get or create Gmail API service (singleton)."""
        if cls._service is not None:
            return cls._service

        creds = None

        # Load existing token
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE, 'rb') as f:
                    creds = pickle.load(f)
            except Exception as e:
                logger.warning(f"Could not load token: {e}")

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}")
                    creds = None

            if not creds:
                if not CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {CREDENTIALS_FILE}. "
                        "Please set up OAuth credentials from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future use
            with open(TOKEN_FILE, 'wb') as f:
                pickle.dump(creds, f)

        cls._service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail service initialized successfully")
        return cls._service

    @classmethod
    def send_email(
        cls,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail API.

        Returns:
            Dict with 'success', 'message_id', and 'error' (if failed)
        """
        try:
            service = cls.get_service()

            # Create message
            if is_html:
                message = MIMEMultipart('alternative')
                message.attach(MIMEText(body, 'html'))
            else:
                message = MIMEText(body)

            message['to'] = to
            message['subject'] = subject

            if cc:
                message['cc'] = cc

            # Handle reply threading
            if reply_to_message_id:
                message['In-Reply-To'] = reply_to_message_id
                message['References'] = reply_to_message_id

            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            # Send
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            message_id = result.get('id', 'unknown')
            logger.info(f"SENT | To: {to} | Subject: {subject} | Message-ID: {message_id}")

            return {
                'success': True,
                'message_id': message_id,
                'thread_id': result.get('threadId')
            }

        except Exception as e:
            logger.error(f"FAILED | To: {to} | Subject: {subject} | Error: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# === HITL Integration ===
def create_email_approval_request(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    reply_to_message_id: Optional[str] = None,
    is_html: bool = False
) -> Dict[str, Any]:
    """
    Create an approval request for sending an email.

    Uses the HITL approval system from approval_watcher.py
    """
    # Import here to avoid circular dependency
    try:
        from approval_watcher import create_approval_request
    except ImportError:
        # Fallback: create approval file directly
        return _create_approval_file_directly(
            to, subject, body, cc, reply_to_message_id, is_html
        )

    # Create preview (first 500 chars)
    body_preview = body[:500] + "..." if len(body) > 500 else body

    # Determine who is affected
    who_affected = to
    if cc:
        who_affected += f" (CC: {cc})"

    # Create the approval request
    request_id = create_approval_request(
        action_type="SEND_EMAIL",
        description=f"Send email to {to}: {subject}",
        details={
            "recipient": to,
            "subject": subject,
            "body_preview": body_preview,
            "cc": cc,
            "platform": "gmail",
            "is_reply": bool(reply_to_message_id),
            "original_message_id": reply_to_message_id,
            "is_html": is_html
        },
        who_is_affected=who_affected,
        amount_if_payment=None,
        callback_data={
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc,
            "reply_to_message_id": reply_to_message_id,
            "is_html": is_html
        }
    )

    return {
        "status": "pending_approval",
        "request_id": request_id,
        "message": f"Email queued for approval. Move file to {APPROVED_DIR}/ to send.",
        "approval_folder": str(PENDING_DIR)
    }


def _create_approval_file_directly(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    reply_to_message_id: Optional[str] = None,
    is_html: bool = False
) -> Dict[str, Any]:
    """Fallback: Create approval file without approval_watcher module."""
    import uuid
    from datetime import timedelta

    PENDING_DIR.mkdir(exist_ok=True)

    request_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(hours=24)

    # Create filename
    safe_to = to.split('@')[0][:20]
    safe_subject = subject[:20].replace(" ", "_")
    safe_subject = "".join(c for c in safe_subject if c.isalnum() or c in "_-")
    timestamp = created_at.strftime("%Y%m%d_%H%M%S")
    filename = f"SEND_EMAIL_{safe_to}_{safe_subject}_{timestamp}.json"

    body_preview = body[:500] + "..." if len(body) > 500 else body

    request_data = {
        "request_id": request_id,
        "action_type": "SEND_EMAIL",
        "description": f"Send email to {to}: {subject}",
        "details": {
            "recipient": to,
            "subject": subject,
            "body_preview": body_preview,
            "cc": cc,
            "platform": "gmail",
            "is_reply": bool(reply_to_message_id),
            "original_message_id": reply_to_message_id,
            "is_html": is_html
        },
        "who_is_affected": to + (f" (CC: {cc})" if cc else ""),
        "amount_if_payment": None,
        "created_at": created_at.isoformat() + "Z",
        "expires_at": expires_at.isoformat() + "Z",
        "status": "PENDING",
        "how_to_approve": f"Move this file to {APPROVED_DIR}/ folder",
        "how_to_reject": f"Move this file to {REJECTED_DIR}/ folder",
        "callback_data": {
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc,
            "reply_to_message_id": reply_to_message_id,
            "is_html": is_html
        }
    }

    filepath = PENDING_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(request_data, f, indent=2)

    logger.info(f"CREATED | SEND_EMAIL | To: {to} | Request ID: {request_id}")

    return {
        "status": "pending_approval",
        "request_id": request_id,
        "message": f"Email queued for approval. Move file to {APPROVED_DIR}/ to send.",
        "approval_file": str(filepath)
    }


def check_email_status(request_id: str) -> Dict[str, Any]:
    """Check the status of an email approval request."""
    try:
        from approval_watcher import check_approval_status
        status = check_approval_status(request_id)
    except ImportError:
        status = _check_status_directly(request_id)

    return {
        "request_id": request_id,
        "status": status
    }


def _check_status_directly(request_id: str) -> str:
    """Fallback status check without approval_watcher."""
    for directory, status in [
        (PENDING_DIR, "PENDING"),
        (APPROVED_DIR, "APPROVED"),
        (REJECTED_DIR, "REJECTED")
    ]:
        if directory.exists():
            for filepath in directory.glob("*.json"):
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    if data.get("request_id") == request_id:
                        # Check for SENT status
                        if data.get("status") == "EXECUTED":
                            return "SENT"
                        return status
                except (json.JSONDecodeError, KeyError):
                    continue
    return "NOT_FOUND"


def list_pending_emails() -> Dict[str, Any]:
    """List all emails pending approval."""
    pending = []

    if PENDING_DIR.exists():
        for filepath in PENDING_DIR.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)

                if data.get("action_type") == "SEND_EMAIL":
                    details = data.get("details", {})
                    pending.append({
                        "request_id": data.get("request_id"),
                        "to": details.get("recipient"),
                        "subject": details.get("subject"),
                        "created_at": data.get("created_at"),
                        "expires_at": data.get("expires_at"),
                        "file": filepath.name
                    })
            except (json.JSONDecodeError, KeyError):
                continue

    return {
        "pending_count": len(pending),
        "emails": pending
    }


# === MCP Server ===
if MCP_AVAILABLE:
    # Create MCP server instance
    mcp_server = Server("email-mcp-server")

    @mcp_server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available MCP tools."""
        return [
            Tool(
                name="send_email",
                description=(
                    "Send an email via Gmail. IMPORTANT: This creates an approval request. "
                    "The email will only be sent after a human approves it by moving the "
                    "request file to the /Approved/ folder."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content (plain text or HTML)"
                        },
                        "cc": {
                            "type": "string",
                            "description": "CC recipients (comma-separated, optional)"
                        },
                        "reply_to_message_id": {
                            "type": "string",
                            "description": "Gmail message ID if this is a reply (optional)"
                        },
                        "is_html": {
                            "type": "boolean",
                            "description": "Set to true if body contains HTML (default: false)"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            ),
            Tool(
                name="check_email_status",
                description="Check the status of a pending email approval request.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "request_id": {
                            "type": "string",
                            "description": "The request ID returned from send_email"
                        }
                    },
                    "required": ["request_id"]
                }
            ),
            Tool(
                name="list_pending_emails",
                description="List all emails currently awaiting approval.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle MCP tool calls."""

        if name == "send_email":
            result = create_email_approval_request(
                to=arguments["to"],
                subject=arguments["subject"],
                body=arguments["body"],
                cc=arguments.get("cc"),
                reply_to_message_id=arguments.get("reply_to_message_id"),
                is_html=arguments.get("is_html", False)
            )

        elif name == "check_email_status":
            result = check_email_status(arguments["request_id"])

        elif name == "list_pending_emails":
            result = list_pending_emails()

        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


# === Register with Approval Watcher ===
def register_email_executor():
    """Register the email sending function with the approval watcher."""
    try:
        from approval_watcher import register_executor

        @register_executor("SEND_EMAIL")
        def execute_send_email(request: Dict[str, Any]) -> bool:
            """Execute email sending when approved."""
            callback_data = request.get("callback_data", {})

            result = GmailService.send_email(
                to=callback_data.get("to"),
                subject=callback_data.get("subject"),
                body=callback_data.get("body"),
                cc=callback_data.get("cc"),
                reply_to_message_id=callback_data.get("reply_to_message_id"),
                is_html=callback_data.get("is_html", False)
            )

            return result.get("success", False)

        logger.info("Email executor registered with approval watcher")

    except ImportError:
        logger.warning("Could not register with approval_watcher - module not found")


# === Main Entry Points ===
async def run_mcp_server():
    """Run the MCP server via stdio."""
    if not MCP_AVAILABLE:
        print("Error: MCP package not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # Register email executor
    register_email_executor()

    logger.info("Starting Email MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )


def test_gmail_connection():
    """Test Gmail API connection."""
    print("Testing Gmail connection...")
    try:
        service = GmailService.get_service()
        profile = service.users().getProfile(userId='me').execute()
        print(f"Connected successfully!")
        print(f"Email: {profile.get('emailAddress')}")
        print(f"Total messages: {profile.get('messagesTotal')}")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


def reauth_gmail():
    """Force re-authentication with Gmail."""
    print("Re-authenticating Gmail...")
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print(f"Removed existing token: {TOKEN_FILE}")

    try:
        GmailService._service = None  # Reset singleton
        service = GmailService.get_service()
        profile = service.users().getProfile(userId='me').execute()
        print(f"Re-authenticated successfully!")
        print(f"Email: {profile.get('emailAddress')}")
        return True
    except Exception as e:
        print(f"Re-authentication failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            test_gmail_connection()
        elif sys.argv[1] == "--reauth":
            reauth_gmail()
        elif sys.argv[1] == "--help":
            print(__doc__)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print(__doc__)
    else:
        # Run as MCP server
        asyncio.run(run_mcp_server())
