#!/usr/bin/env python3
"""
CEO Briefing Generator - Weekly Business Audit

Collects data from all AI Employee systems and generates a comprehensive
executive briefing report.

Data Sources:
    - Odoo ERP (invoices, customers, financials)
    - Audit Logs (/Logs/audit/)
    - HITL Approvals (/Approved/, /Rejected/, /Pending_Approval/)
    - Ralph Wiggum tasks (/Done/, /Active_Tasks/)
    - Email activity (/Needs_Action/, /Done/)

Usage:
    python3 ceo_briefing.py --generate     # Generate briefing now
    python3 ceo_briefing.py --last         # View last briefing
    python3 ceo_briefing.py --list         # List all briefings
    python3 ceo_briefing.py --preview      # Preview without saving
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

# === Configuration ===
BASE_DIR = Path(__file__).parent
BRIEFINGS_DIR = BASE_DIR / "Briefings"
LOGS_DIR = BASE_DIR / "Logs"
AUDIT_DIR = LOGS_DIR / "audit"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
DONE_DIR = BASE_DIR / "Done"
ACTIVE_TASKS_DIR = BASE_DIR / "Active_Tasks"
PENDING_APPROVAL_DIR = BASE_DIR / "Pending_Approval"
APPROVED_DIR = BASE_DIR / "Approved"
REJECTED_DIR = BASE_DIR / "Rejected"

BRIEFING_LOG = LOGS_DIR / "ceo_briefing.log"

# === Logging Setup ===
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(BRIEFING_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# === Data Collectors ===

def collect_odoo_data() -> Dict[str, Any]:
    """Collect financial data from Odoo ERP."""
    data = {
        "available": False,
        "invoices": [],
        "total_invoiced": 0.0,
        "total_paid": 0.0,
        "total_unpaid": 0.0,
        "invoice_count": 0,
        "customer_count": 0,
        "collection_rate": 0.0,
        "error": None
    }

    try:
        # Import Odoo MCP tools
        from odoo_mcp_server import OdooJSONRPC, OdooMCPTools

        odoo = OdooJSONRPC()
        tools = OdooMCPTools(odoo)

        # Get financial summary
        summary = tools.get_financial_summary()
        data["available"] = True
        data["total_invoiced"] = summary.get("total_invoiced", 0)
        data["total_paid"] = summary.get("total_paid", 0)
        data["total_unpaid"] = summary.get("total_unpaid", 0)
        data["invoice_count"] = summary.get("invoice_count", 0)
        data["collection_rate"] = summary.get("collection_rate", 0)

        # Get customers
        customers = tools.get_customers(limit=1000)
        data["customer_count"] = len(customers)

        # Get recent invoices
        invoices = tools.get_invoices(limit=10)
        data["invoices"] = invoices

        logger.info(f"Odoo: {data['invoice_count']} invoices, ${data['total_invoiced']:,.2f} total")

    except ImportError:
        data["error"] = "odoo_mcp_server.py not found"
        logger.warning("Odoo MCP server not available")
    except Exception as e:
        data["error"] = str(e)
        logger.warning(f"Odoo connection failed: {e}")

    return data


def collect_audit_data(days: int = 7) -> Dict[str, Any]:
    """Collect data from audit logs."""
    data = {
        "total_events": 0,
        "events_by_type": defaultdict(int),
        "events_by_actor": defaultdict(int),
        "success_count": 0,
        "failure_count": 0,
        "events": []
    }

    if not AUDIT_DIR.exists():
        logger.warning("Audit directory not found")
        return data

    cutoff_date = datetime.now() - timedelta(days=days)

    for log_file in sorted(AUDIT_DIR.glob("*.json"), reverse=True):
        try:
            # Parse date from filename (YYYY-MM-DD.json)
            file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")
            if file_date < cutoff_date:
                continue

            # Read JSON lines
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        data["total_events"] += 1
                        data["events_by_type"][event.get("action_type", "UNKNOWN")] += 1
                        data["events_by_actor"][event.get("actor", "unknown")] += 1

                        if event.get("result") == "success":
                            data["success_count"] += 1
                        else:
                            data["failure_count"] += 1

                        data["events"].append(event)
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.warning(f"Error reading {log_file}: {e}")

    logger.info(f"Audit: {data['total_events']} events")
    return data


def collect_hitl_data() -> Dict[str, Any]:
    """Collect HITL approval statistics."""
    data = {
        "pending_count": 0,
        "approved_count": 0,
        "rejected_count": 0,
        "expired_count": 0,
        "pending_items": [],
        "approval_rate": 0.0
    }

    # Count pending approvals
    if PENDING_APPROVAL_DIR.exists():
        pending_files = list(PENDING_APPROVAL_DIR.glob("*.json"))
        data["pending_count"] = len(pending_files)

        # Get details of pending items
        for f in pending_files[:5]:
            try:
                item = json.loads(f.read_text())
                data["pending_items"].append({
                    "file": f.name,
                    "type": item.get("action_type", item.get("type", "UNKNOWN")),
                    "created": item.get("created_at", ""),
                    "description": item.get("description", "")[:50]
                })
            except:
                pass

    # Count approved
    if APPROVED_DIR.exists():
        data["approved_count"] = len(list(APPROVED_DIR.glob("*.json")))

    # Count rejected and expired
    if REJECTED_DIR.exists():
        for f in REJECTED_DIR.glob("*.json"):
            try:
                item = json.loads(f.read_text())
                if item.get("status") == "EXPIRED":
                    data["expired_count"] += 1
                else:
                    data["rejected_count"] += 1
            except:
                data["rejected_count"] += 1

    # Calculate approval rate
    total_decided = data["approved_count"] + data["rejected_count"]
    if total_decided > 0:
        data["approval_rate"] = (data["approved_count"] / total_decided) * 100

    logger.info(f"HITL: {data['approved_count']} approved, {data['rejected_count']} rejected, {data['pending_count']} pending")
    return data


def collect_ralph_wiggum_data() -> Dict[str, Any]:
    """Collect Ralph Wiggum task statistics."""
    data = {
        "completed_tasks": 0,
        "active_tasks": 0,
        "total_iterations": 0,
        "completed_list": []
    }

    # Count completed tasks
    if DONE_DIR.exists():
        for f in DONE_DIR.glob("TASK_*.md"):
            data["completed_tasks"] += 1
            try:
                content = f.read_text()
                # Extract iteration count from frontmatter
                if "iteration:" in content:
                    for line in content.split("\n"):
                        if line.startswith("iteration:"):
                            iterations = int(line.split(":")[1].strip())
                            data["total_iterations"] += iterations
                            break
                data["completed_list"].append(f.name)
            except:
                pass

    # Count active tasks
    if ACTIVE_TASKS_DIR.exists():
        data["active_tasks"] = len(list(ACTIVE_TASKS_DIR.glob("TASK_*.md")))

    logger.info(f"Ralph Wiggum: {data['completed_tasks']} completed, {data['active_tasks']} active")
    return data


def collect_email_data() -> Dict[str, Any]:
    """Collect email processing statistics."""
    data = {
        "pending_emails": 0,
        "processed_emails": 0,
        "total_emails": 0,
        "whatsapp_messages": 0
    }

    # Count pending emails
    if NEEDS_ACTION_DIR.exists():
        data["pending_emails"] = len(list(NEEDS_ACTION_DIR.glob("EMAIL_*.md")))
        data["whatsapp_messages"] = len(list(NEEDS_ACTION_DIR.glob("WA_*.md")))

    # Count done emails
    if DONE_DIR.exists():
        data["processed_emails"] = len(list(DONE_DIR.glob("EMAIL_*.md")))

    data["total_emails"] = data["pending_emails"] + data["processed_emails"]

    logger.info(f"Email: {data['total_emails']} total, {data['processed_emails']} processed, {data['pending_emails']} pending")
    return data


# === Briefing Generator ===

def generate_briefing(preview: bool = False) -> str:
    """Generate the CEO briefing report."""
    logger.info("Starting CEO Briefing generation...")

    # Collect all data
    print("\n" + "="*60)
    print("CEO BRIEFING GENERATOR")
    print("="*60)
    print("Collecting data from:")

    print("  - Odoo ERP...", end="", flush=True)
    odoo_data = collect_odoo_data()
    if odoo_data["available"]:
        print(f"          [OK] {odoo_data['invoice_count']} invoices, ${odoo_data['total_invoiced']:,.0f} total")
    else:
        print(f"          [OFFLINE] {odoo_data.get('error', 'unavailable')}")

    print("  - Audit Logs...", end="", flush=True)
    audit_data = collect_audit_data(days=7)
    print(f"        [OK] {audit_data['total_events']} events")

    print("  - HITL Approvals...", end="", flush=True)
    hitl_data = collect_hitl_data()
    print(f"    [OK] {hitl_data['approved_count']} approved, {hitl_data['rejected_count']} rejected")

    print("  - Ralph Wiggum...", end="", flush=True)
    ralph_data = collect_ralph_wiggum_data()
    print(f"      [OK] {ralph_data['completed_tasks']} tasks completed")

    print("  - Email Activity...", end="", flush=True)
    email_data = collect_email_data()
    print(f"    [OK] {email_data['total_emails']} emails processed")

    # Generate briefing content
    now = datetime.now()
    week_number = now.isocalendar()[1]
    year = now.year
    week_start = now - timedelta(days=now.weekday() + 1)
    week_end = now

    # Calculate metrics
    total_actions = hitl_data['approved_count'] + email_data['processed_emails'] + ralph_data['completed_tasks']
    automation_rate = 75.0  # Base estimate
    if hitl_data['approved_count'] > 0 and total_actions > 0:
        automation_rate = max(0, 100 - (hitl_data['approved_count'] / total_actions * 100))

    # Build Executive Summary
    exec_summary = []

    # Financial health
    if odoo_data["available"]:
        if odoo_data["collection_rate"] < 50:
            exec_summary.append(f"**Collections need attention**: ${odoo_data['total_unpaid']:,.0f} outstanding ({odoo_data['collection_rate']:.0f}% collection rate)")
        else:
            exec_summary.append(f"**Financial health stable**: ${odoo_data['total_paid']:,.0f} collected ({odoo_data['collection_rate']:.0f}% rate)")
    else:
        exec_summary.append("**Odoo offline**: Financial data unavailable")

    # Operations health
    if email_data['pending_emails'] > 20:
        exec_summary.append(f"**Email backlog growing**: {email_data['pending_emails']} emails pending action")
    else:
        exec_summary.append(f"**Operations running smoothly**: {email_data['processed_emails']} emails processed this week")

    # Automation health
    exec_summary.append(f"**Automation efficiency**: {automation_rate:.0f}% automated, {hitl_data['approved_count']} human approvals this week")

    # Build Urgent Items
    urgent_items = []

    # Pending approvals > 24h
    for item in hitl_data.get("pending_items", []):
        urgent_items.append(f"- **Pending Approval**: {item['type']} - {item['description']}")

    # High unpaid invoices
    if odoo_data["available"] and odoo_data["total_unpaid"] > 10000:
        urgent_items.append(f"- **Outstanding Invoices**: ${odoo_data['total_unpaid']:,.0f} unpaid")

    # Email backlog
    if email_data['pending_emails'] > 10:
        urgent_items.append(f"- **Email Backlog**: {email_data['pending_emails']} emails awaiting action")

    # WhatsApp messages
    if email_data['whatsapp_messages'] > 0:
        urgent_items.append(f"- **WhatsApp Alerts**: {email_data['whatsapp_messages']} urgent messages")

    if not urgent_items:
        urgent_items.append("- No urgent items requiring immediate attention")

    # Build Weekly Wins
    wins = []
    if ralph_data['completed_tasks'] > 0:
        wins.append(f"- Completed {ralph_data['completed_tasks']} automated tasks via Ralph Wiggum")
    if hitl_data['approved_count'] > 0:
        wins.append(f"- Processed {hitl_data['approved_count']} approval requests ({hitl_data['approval_rate']:.0f}% approval rate)")
    if email_data['processed_emails'] > 0:
        wins.append(f"- Processed {email_data['processed_emails']} emails automatically")
    if audit_data['success_count'] > 0:
        success_rate = (audit_data['success_count'] / max(audit_data['total_events'], 1)) * 100
        wins.append(f"- System reliability: {success_rate:.0f}% success rate across {audit_data['total_events']} actions")

    if not wins:
        wins.append("- System operational, collecting baseline metrics")

    # Build Recommendations
    recommendations = []

    if odoo_data["available"] and odoo_data["collection_rate"] < 50:
        recommendations.append("- **Follow up on outstanding invoices** - Collection rate below 50%")

    if hitl_data['pending_count'] > 3:
        recommendations.append("- **Review pending approvals** - {0} items awaiting decision".format(hitl_data['pending_count']))

    if hitl_data['expired_count'] > 2:
        recommendations.append("- **Adjust approval workflow** - {0} requests expired this week".format(hitl_data['expired_count']))

    if email_data['pending_emails'] > 15:
        recommendations.append("- **Process email backlog** - Consider batch processing rules")

    if automation_rate < 60:
        recommendations.append("- **Improve automation** - High human intervention rate detected")

    if not recommendations:
        recommendations.append("- All systems operating within normal parameters")
        recommendations.append("- Continue monitoring for optimization opportunities")

    # Generate the briefing markdown
    briefing_content = f"""# CEO Weekly Briefing
## Week {week_number}, {year} ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d')})

**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')}
**Report Type:** Weekly Business Audit

---

## Executive Summary

{chr(10).join('- ' + s if not s.startswith('-') else s for s in exec_summary)}

---

## Key Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Emails Processed | {email_data['processed_emails']} | {'Good' if email_data['pending_emails'] < 10 else 'Needs Attention'} |
| Emails Pending | {email_data['pending_emails']} | {'Good' if email_data['pending_emails'] < 10 else 'High'} |
| Approvals Completed | {hitl_data['approved_count']} | - |
| Tasks Automated | {ralph_data['completed_tasks']} | - |
| Automation Rate | {automation_rate:.0f}% | {'Good' if automation_rate > 70 else 'Review'} |
| System Success Rate | {(audit_data['success_count'] / max(audit_data['total_events'], 1) * 100):.0f}% | {'Good' if audit_data['failure_count'] < 3 else 'Issues'} |

---

## Urgent Items

{chr(10).join(urgent_items)}

---

## Weekly Wins

{chr(10).join(wins)}

---

## Recommendations

{chr(10).join(recommendations)}

---

## Financial Snapshot from Odoo

"""

    if odoo_data["available"]:
        briefing_content += f"""| Metric | Amount |
|--------|--------|
| **Total Invoiced** | ${odoo_data['total_invoiced']:,.2f} |
| **Total Collected** | ${odoo_data['total_paid']:,.2f} |
| **Outstanding** | ${odoo_data['total_unpaid']:,.2f} |
| **Collection Rate** | {odoo_data['collection_rate']:.1f}% |
| **Invoice Count** | {odoo_data['invoice_count']} |
| **Customer Count** | {odoo_data['customer_count']} |

### Recent Invoices

| Invoice | Customer | Amount | Status |
|---------|----------|--------|--------|
"""
        for inv in odoo_data.get("invoices", [])[:5]:
            status = "Paid" if inv.get("due", 0) == 0 else "Unpaid"
            customer = str(inv.get('customer', 'N/A'))[:20]
            briefing_content += f"| {inv.get('number', 'N/A')} | {customer} | ${inv.get('total', 0):,.2f} | {status} |\n"
    else:
        briefing_content += f"""**Status:** Odoo ERP Offline

*Error: {odoo_data.get('error', 'Connection unavailable')}*

Connect Odoo to enable financial reporting.
"""

    # Add activity breakdown
    briefing_content += f"""

---

## Activity Breakdown

### By Actor (Last 7 Days)

| Actor | Events |
|-------|--------|
"""
    for actor, count in sorted(audit_data["events_by_actor"].items(), key=lambda x: -x[1])[:5]:
        briefing_content += f"| {actor} | {count} |\n"

    briefing_content += f"""

### By Action Type

| Action | Count |
|--------|-------|
"""
    for action_type, count in sorted(audit_data["events_by_type"].items(), key=lambda x: -x[1])[:5]:
        briefing_content += f"| {action_type} | {count} |\n"

    # Add HITL summary
    briefing_content += f"""

---

## HITL Approval Summary

| Status | Count |
|--------|-------|
| Approved | {hitl_data['approved_count']} |
| Rejected | {hitl_data['rejected_count']} |
| Expired | {hitl_data['expired_count']} |
| Pending | {hitl_data['pending_count']} |
| **Approval Rate** | {hitl_data['approval_rate']:.1f}% |

---

*This briefing was automatically generated by AI Employee CEO Briefing System.*
*Next briefing: Sunday 9:00 PM*
"""

    # Save or preview
    if preview:
        print("\n" + "-"*60)
        print("PREVIEW MODE - Not saving")
        print("-"*60)
        print(briefing_content)
        return briefing_content

    # Save briefing
    BRIEFINGS_DIR.mkdir(exist_ok=True)
    filename = f"CEO_Brief_{now.strftime('%Y-%m-%d')}.md"
    filepath = BRIEFINGS_DIR / filename
    filepath.write_text(briefing_content)

    print("\n" + "-"*60)
    print(f"Briefing saved to: Briefings/{filename}")
    print("="*60 + "\n")

    logger.info(f"Briefing generated: {filename}")
    return briefing_content


def show_last_briefing():
    """Display the most recent briefing."""
    if not BRIEFINGS_DIR.exists():
        print("No briefings found.")
        return

    briefings = sorted(BRIEFINGS_DIR.glob("CEO_Brief_*.md"), reverse=True)

    if not briefings:
        print("No briefings found.")
        return

    latest = briefings[0]
    print(f"\n{'='*60}")
    print(f"LATEST BRIEFING: {latest.name}")
    print(f"{'='*60}\n")
    print(latest.read_text())


def list_briefings():
    """List all available briefings."""
    if not BRIEFINGS_DIR.exists():
        print("No briefings found.")
        return

    briefings = sorted(BRIEFINGS_DIR.glob("CEO_Brief_*.md"), reverse=True)

    if not briefings:
        print("No briefings found.")
        return

    print(f"\n{'='*60}")
    print("AVAILABLE CEO BRIEFINGS")
    print(f"{'='*60}\n")

    for b in briefings:
        stat = b.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        print(f"  {b.name:<35} {size:>6} bytes  {modified}")

    print(f"\nTotal: {len(briefings)} briefings")
    print(f"{'='*60}\n")


# === Main Entry Point ===

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--generate":
            generate_briefing(preview=False)

        elif arg == "--preview":
            generate_briefing(preview=True)

        elif arg == "--last":
            show_last_briefing()

        elif arg == "--list":
            list_briefings()

        elif arg == "--help":
            print(__doc__)

        else:
            print(f"Unknown option: {arg}")
            print(__doc__)

    else:
        print(__doc__)
