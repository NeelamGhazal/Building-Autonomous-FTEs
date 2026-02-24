#!/usr/bin/env python3
"""
AI Employee Orchestrator
Watches /Needs_Action folder for new EMAIL_*.md files and triggers Claude CLI
to process them using the email_processor skill.
"""

import os
import sys
import time
import subprocess
import fnmatch
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
VAULT_PATH = Path(__file__).parent.resolve()
NEEDS_ACTION_PATH = VAULT_PATH / "Needs_Action"
SKILL_PATH = VAULT_PATH / ".claude" / "skills" / "email_processor" / "SKILL.md"
LOG_FILE = VAULT_PATH / "Logs" / "orchestrator.log"

# Track processed files to avoid duplicates
processed_files = set()


def log(message: str):
    """Log message to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)

    # Append to log file
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")


def is_email_file(filename: str) -> bool:
    """Check if file matches EMAIL_*.md pattern."""
    return fnmatch.fnmatch(filename, "EMAIL_*.md")


def is_already_processed(filepath: Path) -> bool:
    """Check if email file has already been processed."""
    try:
        content = filepath.read_text()
        return "processed: true" in content
    except Exception:
        return False


def trigger_claude_cli(email_file: Path):
    """Trigger Claude CLI to process the email file."""
    log(f"Triggering Claude CLI for: {email_file.name}")

    prompt = f"""Read the SKILL.md file at .claude/skills/email_processor/SKILL.md

Then process this specific email file: Needs_Action/{email_file.name}

Follow ALL steps in the skill:
1. Read the email file and extract sender, subject, content
2. Analyze priority (URGENT if subject contains: urgent, asap, invoice, payment)
3. Create a Plan file in /Plans/ named PLAN_[timestamp].md with the exact format from SKILL.md
4. Update Dashboard.md with the new pending task
5. Tag the original email file with processed: true

Start processing now."""

    try:
        # Run Claude CLI with the prompt
        result = subprocess.run(
            ["claude", "-p", prompt, "--allowedTools", "Edit,Write,Read,Glob"],
            cwd=str(VAULT_PATH),
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode == 0:
            log(f"Successfully processed: {email_file.name}")
            log(f"Claude output: {result.stdout[:500]}...")  # Log first 500 chars
        else:
            log(f"Error processing {email_file.name}: {result.stderr}")

    except subprocess.TimeoutExpired:
        log(f"Timeout processing: {email_file.name}")
    except FileNotFoundError:
        log("ERROR: Claude CLI not found. Make sure 'claude' is installed and in PATH.")
    except Exception as e:
        log(f"Exception processing {email_file.name}: {e}")


class EmailHandler(FileSystemEventHandler):
    """Handle file system events for new email files."""

    def on_created(self, event):
        """Called when a file is created."""
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Check if it's an email file
        if not is_email_file(filepath.name):
            return

        # Avoid processing same file multiple times
        if str(filepath) in processed_files:
            return

        # Check if already processed
        if is_already_processed(filepath):
            log(f"Skipping already processed: {filepath.name}")
            return

        # Small delay to ensure file is fully written
        time.sleep(1)

        log(f"New email detected: {filepath.name}")
        processed_files.add(str(filepath))

        # Trigger Claude CLI
        trigger_claude_cli(filepath)

    def on_modified(self, event):
        """Called when a file is modified (some systems use this instead of created)."""
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Only process email files that haven't been processed
        if not is_email_file(filepath.name):
            return

        if str(filepath) in processed_files:
            return

        if is_already_processed(filepath):
            return

        # Small delay
        time.sleep(1)

        log(f"Email file modified (treating as new): {filepath.name}")
        processed_files.add(str(filepath))

        trigger_claude_cli(filepath)


def scan_existing_unprocessed():
    """Scan for any existing unprocessed emails on startup."""
    log("Scanning for existing unprocessed emails...")

    for email_file in NEEDS_ACTION_PATH.glob("EMAIL_*.md"):
        if not is_already_processed(email_file):
            log(f"Found unprocessed email: {email_file.name}")
            processed_files.add(str(email_file))
            trigger_claude_cli(email_file)


def main():
    """Main entry point."""
    log("=" * 60)
    log("AI Employee Orchestrator Starting")
    log(f"Watching: {NEEDS_ACTION_PATH}")
    log(f"Skill file: {SKILL_PATH}")
    log("=" * 60)

    # Verify paths exist
    if not NEEDS_ACTION_PATH.exists():
        log(f"ERROR: Needs_Action folder not found: {NEEDS_ACTION_PATH}")
        sys.exit(1)

    if not SKILL_PATH.exists():
        log(f"WARNING: Skill file not found: {SKILL_PATH}")

    # Process any existing unprocessed emails
    scan_existing_unprocessed()

    # Set up watchdog observer
    event_handler = EmailHandler()
    observer = Observer()
    observer.schedule(event_handler, str(NEEDS_ACTION_PATH), recursive=False)
    observer.start()

    log("Orchestrator running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Shutting down orchestrator...")
        observer.stop()

    observer.join()
    log("Orchestrator stopped.")


if __name__ == "__main__":
    main()
