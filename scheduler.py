#!/usr/bin/env python3
"""
AI Employee Cron Scheduler

Automated task scheduler using APScheduler for cron-style job scheduling.
Part of the Silver Tier AI Employee system.

Usage:
    python scheduler.py              # Run scheduler daemon
    python scheduler.py --status     # Show all scheduled jobs
    python scheduler.py --run <job>  # Run a specific job immediately
    python scheduler.py --next       # Show next run times

Scheduled Tasks:
    - process_emails: Daily at 8:00 AM
    - generate_ceo_briefing: Every Sunday at 9:00 PM
    - check_expired_approvals: Every hour
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# APScheduler imports
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

# === Configuration ===
BASE_DIR = Path(__file__).parent
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
BRIEFINGS_DIR = BASE_DIR / "Briefings"
PENDING_APPROVAL_DIR = BASE_DIR / "Pending_Approval"
DONE_DIR = BASE_DIR / "Done"
LOGS_DIR = BASE_DIR / "Logs"

SCHEDULER_LOG = LOGS_DIR / "scheduler.log"
TIMEZONE = os.environ.get("SCHEDULER_TIMEZONE", "UTC")

# === Logging Setup ===
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(SCHEDULER_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Reduce APScheduler noise
logging.getLogger('apscheduler').setLevel(logging.WARNING)


# === Scheduled Task Functions ===

def process_emails():
    """
    Process all unread emails in /Needs_Action/ folder.
    Runs daily at 8:00 AM.
    """
    logger.info("JOB_START | process_emails | Starting daily email processing")

    NEEDS_ACTION_DIR.mkdir(exist_ok=True)
    DONE_DIR.mkdir(exist_ok=True)

    processed_count = 0
    action_count = 0

    try:
        # Find all email files in Needs_Action
        email_files = list(NEEDS_ACTION_DIR.glob("EMAIL_*.md"))

        for email_file in email_files:
            try:
                content = email_file.read_text()

                # Check if already processed
                if "status: processed" in content.lower():
                    continue

                # Mark as processed
                if "status: pending" in content:
                    new_content = content.replace("status: pending", "status: processed")
                    email_file.write_text(new_content)
                    processed_count += 1

                # Check if action items are completed (all checkboxes checked)
                if "- [x]" in content and "- [ ]" not in content:
                    # Move to Done folder
                    dest = DONE_DIR / email_file.name
                    email_file.rename(dest)
                    action_count += 1
                    logger.info(f"Moved completed email to Done: {email_file.name}")

            except Exception as e:
                logger.error(f"Error processing {email_file.name}: {e}")

        logger.info(f"JOB_END | process_emails | Processed {processed_count} emails, {action_count} moved to Done")

    except Exception as e:
        logger.error(f"JOB_ERROR | process_emails | {e}")


def generate_ceo_briefing():
    """
    Generate weekly CEO briefing in /Briefings/ folder.
    Runs every Sunday at 9:00 PM.
    """
    logger.info("JOB_START | generate_ceo_briefing | Generating weekly briefing")

    BRIEFINGS_DIR.mkdir(exist_ok=True)

    try:
        now = datetime.now()
        week_number = now.isocalendar()[1]
        year = now.year

        # Calculate week date range
        week_start = now - timedelta(days=now.weekday() + 1)  # Last Monday
        week_end = now

        # Gather statistics
        stats = gather_weekly_stats(week_start, week_end)

        # Generate briefing content
        briefing_content = f"""# CEO Weekly Briefing
## Week {week_number}, {year} ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d')})

Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}

---

### Email Summary
- **Received:** {stats['emails_received']} emails
- **Processed:** {stats['emails_processed']} emails
- **Pending:** {stats['emails_pending']} emails
- **Completion Rate:** {stats['completion_rate']:.1f}%

### Actions Taken
- Emails processed: {stats['emails_processed']}
- Approvals requested: {stats['approvals_requested']}
- Approvals completed: {stats['approvals_completed']}
- Approvals rejected: {stats['approvals_rejected']}

### Pending Approvals
{generate_pending_summary()}

### HITL Activity
- Total approval requests this week: {stats['approvals_requested']}
- Approved: {stats['approvals_completed']}
- Rejected: {stats['approvals_rejected']}
- Expired: {stats['approvals_expired']}

### Key Metrics
- Average response time: {stats['avg_response_time']}
- Automation rate: {stats['automation_rate']:.1f}%
- Human intervention rate: {stats['human_intervention_rate']:.1f}%

---

### Recommendations
{generate_recommendations(stats)}

---

*This briefing was automatically generated by AI Employee Scheduler.*
"""

        # Save briefing
        filename = f"CEO_Briefing_Week_{week_number:02d}_{year}.md"
        filepath = BRIEFINGS_DIR / filename
        filepath.write_text(briefing_content)

        logger.info(f"JOB_END | generate_ceo_briefing | Briefing saved to {filename}")

    except Exception as e:
        logger.error(f"JOB_ERROR | generate_ceo_briefing | {e}")


def gather_weekly_stats(week_start: datetime, week_end: datetime) -> Dict[str, Any]:
    """Gather statistics for the weekly briefing."""
    stats = {
        'emails_received': 0,
        'emails_processed': 0,
        'emails_pending': 0,
        'completion_rate': 0.0,
        'approvals_requested': 0,
        'approvals_completed': 0,
        'approvals_rejected': 0,
        'approvals_expired': 0,
        'avg_response_time': 'N/A',
        'automation_rate': 75.0,  # Default estimate
        'human_intervention_rate': 25.0,
    }

    # Count emails in Needs_Action
    if NEEDS_ACTION_DIR.exists():
        for f in NEEDS_ACTION_DIR.glob("EMAIL_*.md"):
            stats['emails_received'] += 1
            content = f.read_text()
            if "status: processed" in content.lower():
                stats['emails_processed'] += 1
            else:
                stats['emails_pending'] += 1

    # Count emails in Done
    if DONE_DIR.exists():
        for f in DONE_DIR.glob("EMAIL_*.md"):
            stats['emails_received'] += 1
            stats['emails_processed'] += 1

    # Calculate completion rate
    if stats['emails_received'] > 0:
        stats['completion_rate'] = (stats['emails_processed'] / stats['emails_received']) * 100

    # Count approvals
    approved_dir = BASE_DIR / "Approved"
    rejected_dir = BASE_DIR / "Rejected"

    if approved_dir.exists():
        stats['approvals_completed'] = len(list(approved_dir.glob("*.json")))

    if rejected_dir.exists():
        for f in rejected_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("status") == "EXPIRED":
                    stats['approvals_expired'] += 1
                else:
                    stats['approvals_rejected'] += 1
            except:
                stats['approvals_rejected'] += 1

    if PENDING_APPROVAL_DIR.exists():
        stats['approvals_requested'] = len(list(PENDING_APPROVAL_DIR.glob("*.json")))

    stats['approvals_requested'] += stats['approvals_completed'] + stats['approvals_rejected'] + stats['approvals_expired']

    # Calculate intervention rate
    total_actions = stats['emails_processed'] + stats['approvals_completed']
    if total_actions > 0:
        stats['human_intervention_rate'] = (stats['approvals_requested'] / max(total_actions, 1)) * 100
        stats['automation_rate'] = 100 - stats['human_intervention_rate']

    return stats


def generate_pending_summary() -> str:
    """Generate summary of pending approvals."""
    if not PENDING_APPROVAL_DIR.exists():
        return "- No pending approvals"

    pending_files = list(PENDING_APPROVAL_DIR.glob("*.json"))
    if not pending_files:
        return "- No pending approvals"

    summary_lines = []
    for f in pending_files[:5]:  # Limit to 5
        try:
            data = json.loads(f.read_text())
            action_type = data.get("action_type", "UNKNOWN")
            description = data.get("description", "")[:50]
            summary_lines.append(f"- **{action_type}**: {description}")
        except:
            summary_lines.append(f"- {f.name}")

    if len(pending_files) > 5:
        summary_lines.append(f"- ... and {len(pending_files) - 5} more")

    return "\n".join(summary_lines) if summary_lines else "- No pending approvals"


def generate_recommendations(stats: Dict[str, Any]) -> str:
    """Generate recommendations based on stats."""
    recommendations = []

    if stats['emails_pending'] > 10:
        recommendations.append("- High number of pending emails. Consider reviewing email processing rules.")

    if stats['approvals_expired'] > 3:
        recommendations.append("- Multiple approvals expired this week. Consider shorter expiry or notification system.")

    if stats['human_intervention_rate'] > 50:
        recommendations.append("- High human intervention rate. Review automation rules for common tasks.")

    if stats['completion_rate'] < 80:
        recommendations.append("- Email completion rate below 80%. Review processing priorities.")

    if not recommendations:
        recommendations.append("- All metrics within normal ranges. System operating efficiently.")

    return "\n".join(recommendations)


def check_expired_approvals():
    """
    Check /Pending_Approval/ for expired requests.
    Runs every hour.
    """
    logger.info("JOB_START | check_expired_approvals | Checking for expired requests")

    try:
        # Use the function from approval_watcher if available
        try:
            from approval_watcher import check_expired_requests
            check_expired_requests()
            logger.info("JOB_END | check_expired_approvals | Used approval_watcher.check_expired_requests()")
            return
        except ImportError:
            pass

        # Fallback: manual check
        if not PENDING_APPROVAL_DIR.exists():
            logger.info("JOB_END | check_expired_approvals | No pending approval folder")
            return

        expired_count = 0
        now = datetime.utcnow()
        rejected_dir = BASE_DIR / "Rejected"
        rejected_dir.mkdir(exist_ok=True)

        for filepath in PENDING_APPROVAL_DIR.glob("*.json"):
            try:
                data = json.loads(filepath.read_text())
                expires_at_str = data.get("expires_at", "")

                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str.rstrip("Z"))

                    if now > expires_at:
                        # Mark as expired
                        data["status"] = "EXPIRED"
                        data["expired_at"] = now.isoformat() + "Z"

                        # Move to rejected
                        dest = rejected_dir / filepath.name
                        dest.write_text(json.dumps(data, indent=2))
                        filepath.unlink()

                        expired_count += 1
                        logger.info(f"Expired request: {filepath.name}")

            except Exception as e:
                logger.error(f"Error checking {filepath.name}: {e}")

        logger.info(f"JOB_END | check_expired_approvals | {expired_count} requests expired")

    except Exception as e:
        logger.error(f"JOB_ERROR | check_expired_approvals | {e}")


# === Scheduler Setup ===

def create_scheduler() -> BlockingScheduler:
    """Create and configure the scheduler."""
    jobstores = {
        'default': MemoryJobStore()
    }

    executors = {
        'default': ThreadPoolExecutor(max_workers=3)
    }

    job_defaults = {
        'coalesce': True,  # Combine missed runs into one
        'max_instances': 1,  # Only one instance per job
        'misfire_grace_time': 3600  # 1 hour grace for missed jobs
    }

    scheduler = BlockingScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=TIMEZONE
    )

    # Add scheduled jobs
    scheduler.add_job(
        process_emails,
        CronTrigger(hour=8, minute=0),
        id='process_emails',
        name='Process Emails (Daily 8:00 AM)',
        replace_existing=True
    )

    scheduler.add_job(
        generate_ceo_briefing,
        CronTrigger(day_of_week='sun', hour=21, minute=0),
        id='generate_ceo_briefing',
        name='CEO Briefing (Sunday 9:00 PM)',
        replace_existing=True
    )

    scheduler.add_job(
        check_expired_approvals,
        IntervalTrigger(hours=1),
        id='check_expired_approvals',
        name='Check Expired Approvals (Hourly)',
        replace_existing=True
    )

    return scheduler


def show_status(scheduler: Optional[BlockingScheduler] = None):
    """Show all scheduled jobs and their next run times."""
    print("\n" + "="*70)
    print("AI EMPLOYEE SCHEDULER - JOB STATUS")
    print("="*70)

    if scheduler is None:
        scheduler = create_scheduler()

    jobs = scheduler.get_jobs()

    if not jobs:
        print("No jobs scheduled.")
    else:
        for job in jobs:
            # Get next run time - handle different APScheduler versions
            try:
                next_run = getattr(job, 'next_run_time', None)
                if next_run is None:
                    # Try to calculate from trigger
                    from datetime import datetime, timezone
                    next_run = job.trigger.get_next_fire_time(None, datetime.now(timezone.utc))
            except Exception:
                next_run = None

            if next_run:
                next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S %Z')
            else:
                next_run_str = "Will be scheduled on start"

            print(f"\nJob: {job.id}")
            print(f"  Name: {job.name}")
            print(f"  Trigger: {job.trigger}")
            print(f"  Next Run: {next_run_str}")

    print("\n" + "="*70)


def run_job_immediately(job_name: str):
    """Run a specific job immediately."""
    jobs = {
        'process_emails': process_emails,
        'generate_ceo_briefing': generate_ceo_briefing,
        'check_expired_approvals': check_expired_approvals,
    }

    if job_name not in jobs:
        print(f"Unknown job: {job_name}")
        print(f"Available jobs: {', '.join(jobs.keys())}")
        return

    print(f"Running {job_name} immediately...")
    jobs[job_name]()
    print(f"Job {job_name} completed.")


def show_next_runs():
    """Show next run times for all jobs."""
    from datetime import timezone as tz

    scheduler = create_scheduler()
    jobs = scheduler.get_jobs()

    print("\n" + "="*50)
    print("NEXT SCHEDULED RUNS")
    print("="*50)

    job_times = []
    for job in jobs:
        try:
            next_run = job.trigger.get_next_fire_time(None, datetime.now(tz.utc))
            job_times.append((job, next_run))
        except Exception:
            job_times.append((job, None))

    for job, next_run in sorted(job_times, key=lambda x: x[1] or datetime.max.replace(tzinfo=tz.utc)):
        if next_run:
            now = datetime.now(tz.utc)
            time_until = next_run - now
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            print(f"{job.id}: {next_run.strftime('%Y-%m-%d %H:%M')} (in {hours}h {minutes}m)")
        else:
            print(f"{job.id}: Not scheduled")

    print("="*50 + "\n")


def run_scheduler():
    """Run the scheduler daemon."""
    # Ensure directories exist
    for directory in [NEEDS_ACTION_DIR, BRIEFINGS_DIR, PENDING_APPROVAL_DIR, DONE_DIR, LOGS_DIR]:
        directory.mkdir(exist_ok=True)

    logger.info("Starting AI Employee Scheduler...")

    print("\n" + "="*60)
    print("AI EMPLOYEE SCHEDULER")
    print("="*60)
    print(f"Timezone: {TIMEZONE}")
    print(f"Log file: {SCHEDULER_LOG}")
    print("\nScheduled Jobs:")
    print("  - process_emails: Daily at 8:00 AM")
    print("  - generate_ceo_briefing: Sunday at 9:00 PM")
    print("  - check_expired_approvals: Every hour")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

    scheduler = create_scheduler()

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        print("\nScheduler stopped.")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise


# === Main Entry Point ===

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--status":
            show_status()

        elif arg == "--run" and len(sys.argv) > 2:
            run_job_immediately(sys.argv[2])

        elif arg == "--next":
            show_next_runs()

        elif arg == "--help":
            print(__doc__)

        else:
            print(f"Unknown option: {arg}")
            print(__doc__)

    else:
        run_scheduler()
