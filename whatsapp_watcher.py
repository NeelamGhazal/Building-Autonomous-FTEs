#!/usr/bin/env python3
"""
WhatsApp Watcher for Silver Tier AI Employee

Monitors WhatsApp Web using Playwright for messages containing priority keywords.
Creates action items in /Needs_Action/ for the orchestrator to process.

Usage:
    python whatsapp_watcher.py                  # Start watcher (first run: scan QR)
    python whatsapp_watcher.py --headless       # Run in headless mode
    python whatsapp_watcher.py --keywords "urgent,help"  # Custom keywords
    python whatsapp_watcher.py --status         # Show watcher status
    python whatsapp_watcher.py --logout         # Clear session
    python whatsapp_watcher.py --test "message" # Test keyword detection
    python whatsapp_watcher.py --demo           # Run demo mode (mock messages)

First run requires visible browser to scan WhatsApp QR code.
Session is saved for subsequent headless runs.
"""

import os
import sys
import re
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

# === Configuration ===
BASE_DIR = Path(__file__).parent
SESSION_DIR = BASE_DIR / "whatsapp_session"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
LOGS_DIR = BASE_DIR / "Logs"
HANDBOOK_FILE = BASE_DIR / "Company_Handbook.md"

WHATSAPP_LOG = LOGS_DIR / "whatsapp_log.md"
WHATSAPP_URL = "https://web.whatsapp.com"

# Default check interval (seconds)
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "30"))

# Default priority keywords
DEFAULT_KEYWORDS = [
    "urgent",
    "invoice",
    "payment",
    "help",
    "asap",
    "emergency",
    "deadline",
    "important",
    "critical",
    "immediately",
    "issue",
    "problem",
    "meeting",
    "call"
]

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


# === Keyword Management ===
def load_keywords_from_handbook() -> List[str]:
    """Load keywords from Company_Handbook.md if available."""
    if not HANDBOOK_FILE.exists():
        return DEFAULT_KEYWORDS

    try:
        content = HANDBOOK_FILE.read_text()

        # Look for WhatsApp Keywords section
        if "## WhatsApp Keywords" in content or "## whatsapp keywords" in content.lower():
            # Extract keywords from list items
            keywords = []
            in_section = False

            for line in content.split('\n'):
                if 'whatsapp keywords' in line.lower():
                    in_section = True
                    continue
                if in_section:
                    if line.startswith('## '):
                        break  # Next section
                    if line.startswith('- '):
                        # Parse comma-separated keywords
                        items = line[2:].split(',')
                        keywords.extend([k.strip().lower() for k in items if k.strip()])

            if keywords:
                logger.info(f"Loaded {len(keywords)} keywords from handbook")
                return keywords

    except Exception as e:
        logger.warning(f"Could not load keywords from handbook: {e}")

    return DEFAULT_KEYWORDS


def detect_keywords(message: str, keywords: List[str]) -> List[str]:
    """Detect which keywords are present in a message."""
    message_lower = message.lower()
    found = []

    for keyword in keywords:
        if keyword.lower() in message_lower:
            found.append(keyword)

    return found


# === Action Item Creation ===
def create_action_item(
    sender: str,
    chat_name: str,
    message: str,
    keywords: List[str],
    timestamp: Optional[datetime] = None
) -> Path:
    """Create an action item file in /Needs_Action/."""
    NEEDS_ACTION_DIR.mkdir(exist_ok=True)

    if timestamp is None:
        timestamp = datetime.now()

    # Create filename
    safe_sender = re.sub(r'[^\w\-]', '', sender.replace(' ', ''))[:20]
    primary_keyword = keywords[0] if keywords else "message"
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
    filename = f"WA_{ts_str}_{safe_sender}_{primary_keyword}.md"

    # Create suggested actions based on keywords
    suggested_actions = ["- [ ] Review message priority"]

    if any(k in keywords for k in ["urgent", "asap", "emergency", "immediately", "critical"]):
        suggested_actions.append("- [ ] Respond urgently")

    if any(k in keywords for k in ["invoice", "payment"]):
        suggested_actions.append("- [ ] Check payment/invoice status")
        suggested_actions.append("- [ ] Update financial records")

    if any(k in keywords for k in ["help", "issue", "problem"]):
        suggested_actions.append("- [ ] Investigate the issue")
        suggested_actions.append("- [ ] Provide assistance")

    if any(k in keywords for k in ["meeting", "call"]):
        suggested_actions.append("- [ ] Check calendar availability")
        suggested_actions.append("- [ ] Schedule or confirm meeting")

    suggested_actions.append("- [ ] Archive after processing")

    # Create content
    content = f"""---
type: whatsapp
from: {sender}
chat: {chat_name}
received: {timestamp.isoformat()}
keywords: {json.dumps(keywords)}
status: pending
---

## WhatsApp Message

**From:** {sender}
**Chat:** {chat_name}
**Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

### Message Content

{message}

## Detected Keywords

{chr(10).join(f'- {k}' for k in keywords)}

## Suggested Actions

{chr(10).join(suggested_actions)}
"""

    filepath = NEEDS_ACTION_DIR / filename
    filepath.write_text(content)

    logger.info(f"Created action item: {filename}")
    log_activity("MESSAGE_DETECTED", sender, keywords)

    return filepath


def log_activity(action: str, sender: str, keywords: List[str]):
    """Log WhatsApp activity."""
    LOGS_DIR.mkdir(exist_ok=True)

    now = datetime.now()
    date_header = now.strftime("## %Y-%m-%d")

    if WHATSAPP_LOG.exists():
        log_content = WHATSAPP_LOG.read_text()
    else:
        log_content = "# WhatsApp Watcher Log\n\n"

    if date_header not in log_content:
        log_content += f"\n{date_header}\n\n"

    entry = f"- **{now.strftime('%H:%M:%S')}** | {action} | From: {sender} | Keywords: {', '.join(keywords)}\n"
    log_content += entry

    WHATSAPP_LOG.write_text(log_content)


# === WhatsApp Web Automation ===
class WhatsAppWatcher:
    """Playwright-based WhatsApp Web watcher."""

    def __init__(self, headless: bool = False, keywords: Optional[List[str]] = None):
        self.headless = headless
        self.keywords = keywords or load_keywords_from_handbook()
        self.browser = None
        self.context = None
        self.page = None
        self.processed_messages: Set[str] = set()
        self.running = False

    async def initialize(self):
        """Initialize Playwright browser."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            sys.exit(1)

        SESSION_DIR.mkdir(exist_ok=True)

        self.playwright = await async_playwright().start()

        # Launch browser with persistent context for session
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        self.page = await self.context.new_page()
        logger.info(f"Browser initialized (headless: {self.headless})")

    async def login(self) -> bool:
        """Navigate to WhatsApp Web and wait for login."""
        logger.info("Opening WhatsApp Web...")
        await self.page.goto(WHATSAPP_URL)

        # Wait for either QR code or chat list
        try:
            # Wait for main chat pane (indicates logged in)
            await self.page.wait_for_selector(
                'div[data-tab="3"]',  # Chat list pane
                timeout=120000  # 2 minutes for QR scan
            )
            logger.info("WhatsApp Web logged in successfully!")
            return True

        except Exception as e:
            # Check if QR code is still showing
            qr_element = await self.page.query_selector('canvas')
            if qr_element:
                logger.warning("QR code timeout. Please scan the QR code with your phone.")
                return False
            logger.error(f"Login error: {e}")
            return False

    async def get_unread_chats(self) -> List[Dict[str, Any]]:
        """Get list of chats with unread messages."""
        chats = []

        try:
            # Find chat list items with unread badges
            chat_elements = await self.page.query_selector_all(
                'div[data-tab="3"] > div > div > div'
            )

            for chat_el in chat_elements[:20]:  # Limit to first 20 chats
                try:
                    # Check for unread badge
                    unread_badge = await chat_el.query_selector('span[data-icon="unread-count"]')
                    if not unread_badge:
                        # Also check for number badge
                        unread_badge = await chat_el.query_selector('span.aumms1qt')

                    if unread_badge:
                        # Get chat name
                        name_el = await chat_el.query_selector('span[dir="auto"]')
                        if name_el:
                            chat_name = await name_el.inner_text()
                            chats.append({
                                "name": chat_name,
                                "element": chat_el
                            })

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error getting unread chats: {e}")

        return chats

    async def get_latest_messages(self, chat_name: str) -> List[Dict[str, Any]]:
        """Get latest messages from a specific chat."""
        messages = []

        try:
            # Click on chat to open it
            chat_selector = f'span[title="{chat_name}"]'
            chat_element = await self.page.query_selector(chat_selector)

            if chat_element:
                await chat_element.click()
                await asyncio.sleep(1)  # Wait for messages to load

            # Get message elements
            message_elements = await self.page.query_selector_all(
                'div.message-in, div.message-out'
            )

            for msg_el in message_elements[-10:]:  # Last 10 messages
                try:
                    # Get message text
                    text_el = await msg_el.query_selector('span.selectable-text')
                    if text_el:
                        message_text = await text_el.inner_text()

                        # Get sender (for group chats)
                        sender_el = await msg_el.query_selector('span[data-pre-plain-text]')
                        if sender_el:
                            sender_info = await sender_el.get_attribute('data-pre-plain-text')
                            # Parse "[time] sender:"
                            sender = sender_info.split(']')[-1].strip().rstrip(':') if sender_info else chat_name
                        else:
                            sender = chat_name

                        # Get timestamp
                        time_el = await msg_el.query_selector('span[data-testid="msg-time"]')
                        time_str = await time_el.inner_text() if time_el else ""

                        # Create unique message ID
                        msg_id = f"{chat_name}:{sender}:{message_text[:50]}:{time_str}"

                        messages.append({
                            "id": msg_id,
                            "sender": sender,
                            "chat": chat_name,
                            "text": message_text,
                            "time": time_str
                        })

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error getting messages from {chat_name}: {e}")

        return messages

    async def scan_for_keywords(self):
        """Scan recent messages for keywords."""
        try:
            # Get all visible message bubbles
            message_elements = await self.page.query_selector_all(
                'div[data-tab="8"] span.selectable-text'
            )

            for msg_el in message_elements:
                try:
                    message_text = await msg_el.inner_text()

                    # Check for keywords
                    found_keywords = detect_keywords(message_text, self.keywords)

                    if found_keywords:
                        # Create unique ID for this message
                        msg_id = f"{message_text[:100]}"

                        if msg_id not in self.processed_messages:
                            self.processed_messages.add(msg_id)

                            # Try to get sender info
                            parent = await msg_el.evaluate_handle('el => el.closest(".message-in, .message-out")')
                            sender = "Unknown"
                            chat_name = "WhatsApp"

                            logger.info(f"Keyword match found: {found_keywords}")

                            # Create action item
                            create_action_item(
                                sender=sender,
                                chat_name=chat_name,
                                message=message_text,
                                keywords=found_keywords
                            )

                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Scan error (may be normal): {e}")

    async def run(self):
        """Main watcher loop."""
        await self.initialize()

        if not await self.login():
            logger.error("Failed to login to WhatsApp Web")
            await self.close()
            return

        self.running = True
        logger.info(f"Starting message monitor (interval: {CHECK_INTERVAL}s)")
        logger.info(f"Watching for keywords: {', '.join(self.keywords)}")

        print("\n" + "="*60)
        print("WHATSAPP WATCHER ACTIVE")
        print("="*60)
        print(f"Keywords: {', '.join(self.keywords[:5])}...")
        print(f"Check interval: {CHECK_INTERVAL} seconds")
        print(f"Action items: {NEEDS_ACTION_DIR}/")
        print("Press Ctrl+C to stop")
        print("="*60 + "\n")

        try:
            while self.running:
                await self.scan_for_keywords()
                await asyncio.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Stopping watcher...")

        finally:
            await self.close()

    async def close(self):
        """Close browser and cleanup."""
        self.running = False
        if self.context:
            await self.context.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("Browser closed")


# === Demo Mode ===
def run_demo():
    """Run demo mode with mock messages."""
    print("\n" + "="*60)
    print("WHATSAPP WATCHER DEMO")
    print("="*60)

    keywords = load_keywords_from_handbook()
    print(f"\nLoaded keywords: {', '.join(keywords[:10])}...")

    # Mock messages
    mock_messages = [
        {
            "sender": "John Client",
            "chat": "Project Alpha",
            "message": "Hey, this is URGENT! We need the invoice ASAP. The payment is due today.",
            "time": datetime.now()
        },
        {
            "sender": "Sarah Team",
            "chat": "Dev Team",
            "message": "Can someone help me with the deployment? Having some issues.",
            "time": datetime.now()
        },
        {
            "sender": "Mike Partner",
            "chat": "Business Chat",
            "message": "Important: Need to schedule a meeting for next week's deadline.",
            "time": datetime.now()
        },
        {
            "sender": "Regular Contact",
            "chat": "Friends",
            "message": "Hey, how are you? Let's catch up sometime!",
            "time": datetime.now()
        }
    ]

    print("\n--- Processing Mock Messages ---\n")

    created_files = []
    for msg in mock_messages:
        found_keywords = detect_keywords(msg["message"], keywords)

        print(f"Message from {msg['sender']}:")
        print(f"  \"{msg['message'][:60]}...\"")

        if found_keywords:
            print(f"  MATCH! Keywords: {', '.join(found_keywords)}")
            filepath = create_action_item(
                sender=msg["sender"],
                chat_name=msg["chat"],
                message=msg["message"],
                keywords=found_keywords,
                timestamp=msg["time"]
            )
            created_files.append(filepath)
            print(f"  Created: {filepath.name}")
        else:
            print(f"  No keywords detected - skipped")

        print()

    print("="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print(f"\nCreated {len(created_files)} action items in /Needs_Action/")

    if created_files:
        print("\nFiles created:")
        for f in created_files:
            print(f"  - {f.name}")

    print("\nView files with: ls Needs_Action/WA_*.md")
    print("="*60 + "\n")


def test_keywords(message: str):
    """Test keyword detection on a message."""
    keywords = load_keywords_from_handbook()

    print("\n" + "="*50)
    print("KEYWORD DETECTION TEST")
    print("="*50)
    print(f"\nMessage: \"{message}\"")
    print(f"\nKeywords being checked: {', '.join(keywords)}")

    found = detect_keywords(message, keywords)

    if found:
        print(f"\n✅ MATCH! Found keywords: {', '.join(found)}")
    else:
        print(f"\n❌ No keywords detected")

    print("="*50 + "\n")


def show_status():
    """Show watcher status."""
    print("\n" + "="*50)
    print("WHATSAPP WATCHER STATUS")
    print("="*50)

    # Check session
    if SESSION_DIR.exists() and list(SESSION_DIR.glob("*")):
        print("\n✅ Session: Found (may be logged in)")
    else:
        print("\n❌ Session: Not found (QR login required)")

    # Check keywords
    keywords = load_keywords_from_handbook()
    print(f"\n📝 Keywords loaded: {len(keywords)}")
    print(f"   {', '.join(keywords[:5])}...")

    # Check action items
    if NEEDS_ACTION_DIR.exists():
        wa_files = list(NEEDS_ACTION_DIR.glob("WA_*.md"))
        print(f"\n📋 WhatsApp action items: {len(wa_files)}")
    else:
        print("\n📋 WhatsApp action items: 0")

    # Check log
    if WHATSAPP_LOG.exists():
        print(f"\n📊 Log file: {WHATSAPP_LOG}")
    else:
        print("\n📊 Log file: Not created yet")

    print("\n" + "="*50 + "\n")


def clear_session():
    """Clear WhatsApp session."""
    import shutil

    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR)
        print("✅ Session cleared. QR code login required on next run.")
    else:
        print("No session to clear.")


# === Main Entry Point ===
async def main():
    """Main async entry point."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--demo":
            run_demo()

        elif arg == "--test":
            if len(sys.argv) > 2:
                message = " ".join(sys.argv[2:])
            else:
                message = input("Enter message to test: ")
            test_keywords(message)

        elif arg == "--status":
            show_status()

        elif arg == "--logout":
            clear_session()

        elif arg == "--headless":
            watcher = WhatsAppWatcher(headless=True)
            await watcher.run()

        elif arg == "--keywords":
            if len(sys.argv) > 2:
                keywords = sys.argv[2].split(",")
                watcher = WhatsAppWatcher(keywords=keywords)
                await watcher.run()
            else:
                print("Usage: --keywords \"urgent,help,invoice\"")

        elif arg == "--help":
            print(__doc__)

        else:
            print(f"Unknown option: {arg}")
            print(__doc__)

    else:
        # Default: run watcher
        watcher = WhatsAppWatcher(headless=False)
        await watcher.run()


if __name__ == "__main__":
    asyncio.run(main())
