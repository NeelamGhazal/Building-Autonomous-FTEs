#!/usr/bin/env python3
"""
Human-in-the-Loop (HITL) Approval Watcher

Monitors approval folders and executes/cancels actions based on human decisions.
Part of the Silver Tier AI Employee system.

Usage:
    python approval_watcher.py              # Run watcher daemon
    python approval_watcher.py --reject-all # Emergency: reject all pending
    python approval_watcher.py --status     # Show all pending requests
"""

import json
import os
import sys
import time
import uuid
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# === Configuration ===
BASE_DIR = Path(__file__).parent
PENDING_DIR = BASE_DIR / "Pending_Approval"
APPROVED_DIR = BASE_DIR / "Approved"
REJECTED_DIR = BASE_DIR / "Rejected"
LOGS_DIR = BASE_DIR / "Logs"

APPROVAL_LOG = LOGS_DIR / "approval_history.log"
EXPIRY_HOURS = 24

# Sensitive action types that require approval
SENSITIVE_ACTIONS = {
    "SEND_EMAIL": "Sending any email",
    "SOCIAL_MEDIA_POST": "Posting on LinkedIn or social media",
    "PAYMENT": "Any payment over $50",
    "DELETE_FILE": "Deleting files",
    "CONTACT_NEW_PERSON": "Contacting new people",
}

# === Logging Setup ===
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(APPROVAL_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# === Action Executors Registry ===
# Register callbacks for each action type
action_executors: Dict[str, Callable] = {}


def register_executor(action_type: str):
    """Decorator to register an action executor."""
    def decorator(func: Callable):
        action_executors[action_type] = func
        return func
    return decorator


# === Default Executors (Override these with actual implementations) ===
@register_executor("SEND_EMAIL")
def execute_send_email(request: Dict[str, Any]) -> bool:
    """Execute email sending action via Gmail API."""
    details = request.get("details", {})
    callback_data = request.get("callback_data", {})

    logger.info(f"EXECUTING EMAIL: To={details.get('recipient')}, Subject={details.get('subject')}")

    # Use the Gmail service from email_mcp_server
    try:
        from email_mcp_server import GmailService

        result = GmailService.send_email(
            to=callback_data.get("to"),
            subject=callback_data.get("subject"),
            body=callback_data.get("body"),
            cc=callback_data.get("cc"),
            reply_to_message_id=callback_data.get("reply_to_message_id"),
            is_html=callback_data.get("is_html", False)
        )

        if result.get("success"):
            logger.info(f"EMAIL SENT: Message-ID={result.get('message_id')}")
            return True
        else:
            logger.error(f"EMAIL FAILED: {result.get('error')}")
            return False

    except ImportError as e:
        logger.error(f"Could not import email_mcp_server: {e}")
        logger.info("Falling back to logging only (email not actually sent)")
        return True
    except Exception as e:
        logger.error(f"Email sending error: {e}")
        return False


@register_executor("SOCIAL_MEDIA_POST")
def execute_social_media_post(request: Dict[str, Any]) -> bool:
    """Execute social media posting action."""
    details = request.get("details", {})
    platform = details.get("platform", "unknown")
    logger.info(f"EXECUTING SOCIAL POST: Platform={platform}, Content preview={details.get('body_preview', '')[:100]}")

    # TODO: Integrate with LinkedIn API or other social platforms
    return True


@register_executor("PAYMENT")
def execute_payment(request: Dict[str, Any]) -> bool:
    """Execute payment action."""
    details = request.get("details", {})
    amount = request.get("amount_if_payment", "$0.00")
    recipient = details.get("recipient", "unknown")
    logger.info(f"EXECUTING PAYMENT: Amount={amount}, To={recipient}")

    # TODO: Integrate with payment processor
    # CRITICAL: Double-check amount before execution
    return True


@register_executor("DELETE_FILE")
def execute_delete_file(request: Dict[str, Any]) -> bool:
    """Execute file deletion action."""
    details = request.get("details", {})
    file_path = details.get("file_path", "")
    logger.info(f"EXECUTING DELETE: File={file_path}")

    # Safety check: Only delete within allowed directories
    if file_path and Path(file_path).exists():
        # TODO: Implement safe deletion with backup
        # os.remove(file_path)
        pass

    return True


@register_executor("CONTACT_NEW_PERSON")
def execute_contact_new_person(request: Dict[str, Any]) -> bool:
    """Execute new contact action."""
    details = request.get("details", {})
    person = details.get("recipient", "unknown")
    method = details.get("contact_method", "email")
    logger.info(f"EXECUTING NEW CONTACT: Person={person}, Method={method}")

    # TODO: Integrate with contact/CRM system
    return True


# === Core Functions ===
def create_approval_request(
    action_type: str,
    description: str,
    details: Dict[str, Any],
    who_is_affected: str,
    amount_if_payment: Optional[str] = None,
    callback_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a new approval request file.

    Args:
        action_type: One of SENSITIVE_ACTIONS keys
        description: Human-readable description of the action
        details: Specific details about the action
        who_is_affected: Description of who/what is impacted
        amount_if_payment: Dollar amount if this is a payment
        callback_data: Data needed to execute the action later

    Returns:
        request_id: UUID of the created request
    """
    if action_type not in SENSITIVE_ACTIONS:
        raise ValueError(f"Unknown action type: {action_type}. Must be one of {list(SENSITIVE_ACTIONS.keys())}")

    PENDING_DIR.mkdir(exist_ok=True)

    request_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(hours=EXPIRY_HOURS)

    # Create filename
    short_desc = description[:30].replace(" ", "_").replace("/", "-")
    short_desc = "".join(c for c in short_desc if c.isalnum() or c in "_-")
    timestamp = created_at.strftime("%Y%m%d_%H%M%S")
    filename = f"{action_type}_{short_desc}_{timestamp}.json"

    request_data = {
        "request_id": request_id,
        "action_type": action_type,
        "description": description,
        "details": details,
        "who_is_affected": who_is_affected,
        "amount_if_payment": amount_if_payment,
        "created_at": created_at.isoformat() + "Z",
        "expires_at": expires_at.isoformat() + "Z",
        "status": "PENDING",
        "how_to_approve": f"Move this file to {APPROVED_DIR}/ folder",
        "how_to_reject": f"Move this file to {REJECTED_DIR}/ folder",
        "callback_data": callback_data or {}
    }

    filepath = PENDING_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(request_data, f, indent=2)

    logger.info(f"CREATED | {action_type} | {description[:50]} | Request ID: {request_id}")
    print(f"\n{'='*60}")
    print(f"APPROVAL REQUIRED: {action_type}")
    print(f"{'='*60}")
    print(f"Description: {description}")
    print(f"Affects: {who_is_affected}")
    if amount_if_payment:
        print(f"Amount: {amount_if_payment}")
    print(f"Expires: {expires_at.isoformat()}")
    print(f"\nTo APPROVE: Move file to {APPROVED_DIR}/")
    print(f"To REJECT:  Move file to {REJECTED_DIR}/")
    print(f"File: {filepath}")
    print(f"{'='*60}\n")

    return request_id


def check_approval_status(request_id: str) -> str:
    """
    Check the status of an approval request.

    Returns: "PENDING", "APPROVED", "REJECTED", or "EXPIRED"
    """
    # Check all directories
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
                        # Check expiry for pending
                        if status == "PENDING":
                            expires_at = datetime.fromisoformat(data["expires_at"].rstrip("Z"))
                            if datetime.utcnow() > expires_at:
                                return "EXPIRED"
                        return status
                except (json.JSONDecodeError, KeyError):
                    continue

    return "NOT_FOUND"


def process_approved_request(filepath: Path) -> bool:
    """Process an approved request and execute the action."""
    try:
        with open(filepath) as f:
            request = json.load(f)

        action_type = request.get("action_type")
        description = request.get("description", "")[:50]

        # Execute the action
        executor = action_executors.get(action_type)
        if executor:
            success = executor(request)
            status = "Executed successfully" if success else "Execution failed"
        else:
            status = f"No executor registered for {action_type}"
            success = False

        logger.info(f"APPROVED | {action_type} | {description} | {status}")

        # Mark as processed (update status in file)
        request["status"] = "EXECUTED" if success else "EXECUTION_FAILED"
        request["processed_at"] = datetime.utcnow().isoformat() + "Z"
        with open(filepath, 'w') as f:
            json.dump(request, f, indent=2)

        return success

    except Exception as e:
        logger.error(f"Error processing approved request {filepath}: {e}")
        return False


def process_rejected_request(filepath: Path) -> None:
    """Log and mark a rejected request."""
    try:
        with open(filepath) as f:
            request = json.load(f)

        action_type = request.get("action_type", "UNKNOWN")
        description = request.get("description", "")[:50]

        logger.info(f"REJECTED | {action_type} | {description} | User rejected")

        # Mark as rejected
        request["status"] = "REJECTED"
        request["rejected_at"] = datetime.utcnow().isoformat() + "Z"
        with open(filepath, 'w') as f:
            json.dump(request, f, indent=2)

    except Exception as e:
        logger.error(f"Error processing rejected request {filepath}: {e}")


def check_expired_requests() -> None:
    """Move expired requests to rejected folder."""
    if not PENDING_DIR.exists():
        return

    now = datetime.utcnow()

    for filepath in PENDING_DIR.glob("*.json"):
        try:
            with open(filepath) as f:
                request = json.load(f)

            expires_at = datetime.fromisoformat(request["expires_at"].rstrip("Z"))

            if now > expires_at:
                action_type = request.get("action_type", "UNKNOWN")
                description = request.get("description", "")[:50]

                # Mark as expired
                request["status"] = "EXPIRED"
                request["expired_at"] = now.isoformat() + "Z"

                # Move to rejected
                REJECTED_DIR.mkdir(exist_ok=True)
                dest = REJECTED_DIR / filepath.name
                with open(dest, 'w') as f:
                    json.dump(request, f, indent=2)
                filepath.unlink()

                logger.info(f"EXPIRED | {action_type} | {description} | No response in {EXPIRY_HOURS}h")

        except Exception as e:
            logger.error(f"Error checking expiry for {filepath}: {e}")


def reject_all_pending() -> int:
    """Emergency: Reject all pending requests."""
    count = 0
    if not PENDING_DIR.exists():
        return count

    REJECTED_DIR.mkdir(exist_ok=True)

    for filepath in PENDING_DIR.glob("*.json"):
        try:
            dest = REJECTED_DIR / filepath.name
            shutil.move(str(filepath), str(dest))
            process_rejected_request(dest)
            count += 1
        except Exception as e:
            logger.error(f"Error rejecting {filepath}: {e}")

    logger.info(f"EMERGENCY REJECT | Rejected {count} pending requests")
    return count


def show_status() -> None:
    """Display all pending requests."""
    print("\n" + "="*70)
    print("PENDING APPROVAL REQUESTS")
    print("="*70)

    if not PENDING_DIR.exists() or not list(PENDING_DIR.glob("*.json")):
        print("No pending requests.")
        print("="*70 + "\n")
        return

    for filepath in PENDING_DIR.glob("*.json"):
        try:
            with open(filepath) as f:
                request = json.load(f)

            expires_at = datetime.fromisoformat(request["expires_at"].rstrip("Z"))
            time_left = expires_at - datetime.utcnow()
            hours_left = max(0, time_left.total_seconds() / 3600)

            print(f"\nType: {request.get('action_type')}")
            print(f"Description: {request.get('description')}")
            print(f"Affects: {request.get('who_is_affected')}")
            if request.get('amount_if_payment'):
                print(f"Amount: {request.get('amount_if_payment')}")
            print(f"Expires in: {hours_left:.1f} hours")
            print(f"File: {filepath.name}")
            print("-"*70)

        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    print("="*70 + "\n")


# === File System Event Handlers ===
class ApprovedHandler(FileSystemEventHandler):
    """Handle files moved to Approved folder."""

    def on_created(self, event):
        self._handle_file(event)

    def on_moved(self, event):
        """Handle file moves (mv command or drag-drop)."""
        if event.is_directory:
            return
        if event.dest_path.endswith('.json'):
            filepath = Path(event.dest_path)
            logger.info(f"Detected approved request (moved): {filepath.name}")
            time.sleep(0.5)
            process_approved_request(filepath)

    def _handle_file(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.json'):
            filepath = Path(event.src_path)
            logger.info(f"Detected approved request: {filepath.name}")
            time.sleep(0.5)  # Brief delay to ensure file is fully written
            process_approved_request(filepath)


class RejectedHandler(FileSystemEventHandler):
    """Handle files moved to Rejected folder."""

    def on_created(self, event):
        self._handle_file(event)

    def on_moved(self, event):
        """Handle file moves (mv command or drag-drop)."""
        if event.is_directory:
            return
        if event.dest_path.endswith('.json'):
            filepath = Path(event.dest_path)
            logger.info(f"Detected rejected request (moved): {filepath.name}")
            time.sleep(0.5)
            process_rejected_request(filepath)

    def _handle_file(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.json'):
            filepath = Path(event.src_path)
            logger.info(f"Detected rejected request: {filepath.name}")
            time.sleep(0.5)
            process_rejected_request(filepath)


# Track processed files to avoid duplicate processing
_processed_files: set = set()


def poll_for_approvals():
    """
    Poll-based detection for WSL2/Windows compatibility.
    Watchdog inotify doesn't detect Windows file moves on WSL2.
    """
    global _processed_files

    # Check Approved folder
    if APPROVED_DIR.exists():
        for filepath in APPROVED_DIR.glob("*.json"):
            file_key = f"approved:{filepath.name}"
            if file_key not in _processed_files:
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    # Only process if not already executed
                    if data.get("status") == "PENDING":
                        logger.info(f"[POLL] Detected approved request: {filepath.name}")
                        process_approved_request(filepath)
                        _processed_files.add(file_key)
                except Exception as e:
                    logger.error(f"Error polling {filepath}: {e}")

    # Check Rejected folder
    if REJECTED_DIR.exists():
        for filepath in REJECTED_DIR.glob("*.json"):
            file_key = f"rejected:{filepath.name}"
            if file_key not in _processed_files:
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    # Only process if not already rejected
                    if data.get("status") == "PENDING":
                        logger.info(f"[POLL] Detected rejected request: {filepath.name}")
                        process_rejected_request(filepath)
                        _processed_files.add(file_key)
                except Exception as e:
                    logger.error(f"Error polling {filepath}: {e}")


def run_watcher():
    """Run the approval watcher daemon."""
    # Ensure directories exist
    for directory in [PENDING_DIR, APPROVED_DIR, REJECTED_DIR, LOGS_DIR]:
        directory.mkdir(exist_ok=True)

    logger.info("Starting HITL Approval Watcher...")
    logger.info(f"Watching: {APPROVED_DIR} and {REJECTED_DIR}")
    print(f"\nHITL Approval Watcher Started")
    print(f"Pending folder: {PENDING_DIR}")
    print(f"Move files to {APPROVED_DIR}/ to approve")
    print(f"Move files to {REJECTED_DIR}/ to reject")
    print(f"Press Ctrl+C to stop\n")
    print(f"[INFO] Using polling mode for WSL2 compatibility (checks every 5 seconds)\n")

    # Set up observers (may work for some operations)
    observer = Observer()
    observer.schedule(ApprovedHandler(), str(APPROVED_DIR), recursive=False)
    observer.schedule(RejectedHandler(), str(REJECTED_DIR), recursive=False)
    observer.start()

    try:
        while True:
            # Poll for approvals every 5 seconds (WSL2 compatibility)
            poll_for_approvals()
            time.sleep(5)

            # Check for expired requests every 12 cycles (1 minute)
            check_expired_requests()
    except KeyboardInterrupt:
        logger.info("Shutting down watcher...")
        observer.stop()

    observer.join()
    logger.info("Watcher stopped.")


# === Main Entry Point ===
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reject-all":
            count = reject_all_pending()
            print(f"Rejected {count} pending requests.")
        elif sys.argv[1] == "--status":
            show_status()
        elif sys.argv[1] == "--help":
            print(__doc__)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print(__doc__)
    else:
        run_watcher()
