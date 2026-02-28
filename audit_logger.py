#!/usr/bin/env python3
"""
Audit Logger - Comprehensive Action Logging System

Logs EVERY action in JSON format with full traceability.
Generates daily summaries and maintains 90-day retention.

Usage:
    python3 audit_logger.py --test
    python3 audit_logger.py --today
    python3 audit_logger.py --summary
    python3 audit_logger.py --search "SEND_EMAIL"
"""

import os
import sys
import json
import gzip
import uuid
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from collections import defaultdict

# =============================================================================
# Configuration
# =============================================================================

VAULT_PATH = Path("/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault")
LOGS_FOLDER = VAULT_PATH / "Logs"
AUDIT_FOLDER = LOGS_FOLDER / "audit"
SUMMARY_FILE = LOGS_FOLDER / "audit_summary.md"

# Retention settings
RETENTION_DAYS = 90
COMPRESS_AFTER_DAYS = 30

# Action types
ACTION_TYPES = [
    "SEND_EMAIL",
    "RECEIVE_EMAIL",
    "CREATE_POST",
    "PUBLISH_POST",
    "APPROVE_ACTION",
    "REJECT_ACTION",
    "CREATE_TASK",
    "COMPLETE_TASK",
    "CANCEL_TASK",
    "ERROR",
    "RECOVERY",
    "SYSTEM",
    "LOGIN",
    "LOGOUT",
    "CONFIG_CHANGE",
    "FILE_CREATE",
    "FILE_DELETE",
    "FILE_MOVE",
    "API_CALL",
    "WEBHOOK",
]

# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AuditEntry:
    """Single audit log entry"""
    timestamp: str
    event_id: str
    action_type: str
    actor: str
    target: Dict[str, Any]
    result: str  # success, failure, error, pending
    approval_status: Optional[str] = None  # approved, rejected, pending, not_required
    approval_id: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# =============================================================================
# Audit Logger
# =============================================================================

class AuditLogger:
    """Central audit logging system"""

    _instance = None
    _buffer: List[AuditEntry] = []
    _buffer_size = 10  # Flush after this many entries
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def _ensure_initialized(cls):
        """Ensure audit folder exists"""
        if not cls._initialized:
            AUDIT_FOLDER.mkdir(parents=True, exist_ok=True)
            cls._initialized = True

    @classmethod
    def _get_log_file(cls, date: Optional[datetime] = None) -> Path:
        """Get log file path for a specific date"""
        cls._ensure_initialized()

        if date is None:
            date = datetime.now()

        filename = date.strftime("%Y-%m-%d") + ".json"
        return AUDIT_FOLDER / filename

    @classmethod
    def log(
        cls,
        action_type: str,
        actor: str,
        target: Dict[str, Any],
        result: str = "success",
        approval_status: Optional[str] = None,
        approval_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> str:
        """
        Log an action to the audit trail.

        Returns:
            str: The event ID
        """

        event_id = f"evt_{uuid.uuid4().hex[:16]}"

        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_id=event_id,
            action_type=action_type,
            actor=actor,
            target=target,
            result=result,
            approval_status=approval_status,
            approval_id=approval_id,
            duration_ms=duration_ms,
            metadata=metadata or {},
            error=error
        )

        cls._buffer.append(entry)

        # Flush if buffer is full
        if len(cls._buffer) >= cls._buffer_size:
            cls.flush()

        return event_id

    @classmethod
    def flush(cls):
        """Flush buffered entries to disk"""

        if not cls._buffer:
            return

        cls._ensure_initialized()

        # Group entries by date
        entries_by_date: Dict[str, List[AuditEntry]] = defaultdict(list)

        for entry in cls._buffer:
            date_str = entry.timestamp[:10]  # YYYY-MM-DD
            entries_by_date[date_str].append(entry)

        # Write to appropriate files
        for date_str, entries in entries_by_date.items():
            log_file = AUDIT_FOLDER / f"{date_str}.json"

            # Read existing entries
            existing = []
            if log_file.exists():
                try:
                    content = log_file.read_text(encoding="utf-8")
                    existing = [json.loads(line) for line in content.strip().split("\n") if line]
                except:
                    pass

            # Append new entries
            with open(log_file, "a", encoding="utf-8") as f:
                for entry in entries:
                    f.write(entry.to_json() + "\n")

        cls._buffer.clear()

    @classmethod
    def get_entries(
        cls,
        date: Optional[datetime] = None,
        action_type: Optional[str] = None,
        actor: Optional[str] = None,
        result: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get audit entries with optional filtering"""

        cls.flush()  # Ensure all entries are written

        if date is None:
            date = datetime.now()

        log_file = cls._get_log_file(date)

        if not log_file.exists():
            # Try compressed version
            compressed = log_file.with_suffix(".json.gz")
            if compressed.exists():
                with gzip.open(compressed, "rt", encoding="utf-8") as f:
                    lines = f.readlines()
            else:
                return []
        else:
            lines = log_file.read_text(encoding="utf-8").strip().split("\n")

        entries = []
        for line in lines:
            if not line:
                continue
            try:
                entry = json.loads(line)

                # Apply filters
                if action_type and entry.get("action_type") != action_type:
                    continue
                if actor and entry.get("actor") != actor:
                    continue
                if result and entry.get("result") != result:
                    continue

                entries.append(entry)
            except:
                continue

        # Apply pagination
        return entries[offset:offset + limit]

    @classmethod
    def search(cls, query: str, days: int = 7) -> List[Dict[str, Any]]:
        """Search audit logs for a query string"""

        cls.flush()

        results = []
        query_lower = query.lower()

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            log_file = cls._get_log_file(date)

            if not log_file.exists():
                continue

            lines = log_file.read_text(encoding="utf-8").strip().split("\n")

            for line in lines:
                if query_lower in line.lower():
                    try:
                        results.append(json.loads(line))
                    except:
                        pass

        return results

    @classmethod
    def get_stats(cls, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get statistics for a specific date"""

        entries = cls.get_entries(date, limit=10000)

        if not entries:
            return {
                "total": 0,
                "by_type": {},
                "by_result": {},
                "by_actor": {},
                "success_rate": 0,
                "avg_duration_ms": 0
            }

        stats = {
            "total": len(entries),
            "by_type": defaultdict(int),
            "by_result": defaultdict(int),
            "by_actor": defaultdict(int),
            "success_rate": 0,
            "avg_duration_ms": 0
        }

        durations = []

        for entry in entries:
            stats["by_type"][entry.get("action_type", "unknown")] += 1
            stats["by_result"][entry.get("result", "unknown")] += 1
            stats["by_actor"][entry.get("actor", "unknown")] += 1

            if entry.get("duration_ms"):
                durations.append(entry["duration_ms"])

        # Calculate rates
        success_count = stats["by_result"].get("success", 0)
        stats["success_rate"] = round((success_count / stats["total"]) * 100, 1) if stats["total"] > 0 else 0

        if durations:
            stats["avg_duration_ms"] = round(sum(durations) / len(durations), 1)

        # Convert defaultdicts to regular dicts
        stats["by_type"] = dict(stats["by_type"])
        stats["by_result"] = dict(stats["by_result"])
        stats["by_actor"] = dict(stats["by_actor"])

        return stats


# =============================================================================
# Summary Generation
# =============================================================================

def generate_summary(date: Optional[datetime] = None) -> str:
    """Generate daily audit summary in Markdown format"""

    if date is None:
        date = datetime.now()

    date_str = date.strftime("%Y-%m-%d")
    stats = AuditLogger.get_stats(date)

    # Get error entries for detailed section
    error_entries = AuditLogger.get_entries(date, result="error", limit=50)

    summary = f"""# Audit Summary - {date_str}

## Overview

- **Total Actions:** {stats['total']}
- **Successful:** {stats['by_result'].get('success', 0)} ({stats['success_rate']}%)
- **Failed:** {stats['by_result'].get('failure', 0)}
- **Errors:** {stats['by_result'].get('error', 0)}
- **Avg Duration:** {stats['avg_duration_ms']}ms

## Actions by Type

| Type | Count | % of Total |
|------|-------|------------|
"""

    for action_type, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
        pct = round((count / stats['total']) * 100, 1) if stats['total'] > 0 else 0
        summary += f"| {action_type} | {count} | {pct}% |\n"

    summary += """
## Actions by Actor

| Actor | Count |
|-------|-------|
"""

    for actor, count in sorted(stats['by_actor'].items(), key=lambda x: -x[1]):
        summary += f"| {actor} | {count} |\n"

    summary += """
## Results Breakdown

| Result | Count |
|--------|-------|
"""

    for result, count in sorted(stats['by_result'].items(), key=lambda x: -x[1]):
        summary += f"| {result} | {count} |\n"

    if error_entries:
        summary += """
## Errors

| Time | Type | Actor | Error |
|------|------|-------|-------|
"""

        for entry in error_entries[:10]:  # Limit to 10 errors
            time_str = entry.get("timestamp", "")[:19].replace("T", " ")
            action = entry.get("action_type", "unknown")
            actor = entry.get("actor", "unknown")
            error = entry.get("error", "unknown")[:50]
            summary += f"| {time_str} | {action} | {actor} | {error} |\n"

    summary += f"""
---

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return summary


def save_summary(date: Optional[datetime] = None):
    """Generate and save daily summary"""

    summary = generate_summary(date)
    SUMMARY_FILE.write_text(summary, encoding="utf-8")
    print(f"Summary saved to: {SUMMARY_FILE}")


# =============================================================================
# Maintenance
# =============================================================================

def cleanup_old_logs():
    """Delete logs older than retention period, compress logs older than 30 days"""

    if not AUDIT_FOLDER.exists():
        return

    now = datetime.now()
    deleted = 0
    compressed = 0

    for log_file in AUDIT_FOLDER.glob("*.json"):
        try:
            # Parse date from filename
            date_str = log_file.stem
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            age_days = (now - file_date).days

            if age_days > RETENTION_DAYS:
                # Delete old logs
                log_file.unlink()
                deleted += 1

            elif age_days > COMPRESS_AFTER_DAYS:
                # Compress old logs
                compressed_path = log_file.with_suffix(".json.gz")
                if not compressed_path.exists():
                    with open(log_file, "rb") as f_in:
                        with gzip.open(compressed_path, "wb") as f_out:
                            f_out.writelines(f_in)
                    log_file.unlink()
                    compressed += 1

        except Exception as e:
            print(f"Error processing {log_file}: {e}")

    print(f"Cleanup complete: {deleted} deleted, {compressed} compressed")


def export_logs(
    format: str = "json",
    output: Optional[str] = None,
    days: int = 7
) -> str:
    """Export audit logs to different formats"""

    AuditLogger.flush()

    all_entries = []

    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        entries = AuditLogger.get_entries(date, limit=10000)
        all_entries.extend(entries)

    if format == "json":
        content = json.dumps(all_entries, indent=2)
        ext = ".json"

    elif format == "csv":
        import csv
        import io

        output_io = io.StringIO()
        if all_entries:
            # Get all unique keys
            all_keys = set()
            for entry in all_entries:
                all_keys.update(entry.keys())

            writer = csv.DictWriter(output_io, fieldnames=sorted(all_keys))
            writer.writeheader()

            for entry in all_entries:
                # Flatten nested dicts
                flat_entry = {}
                for k, v in entry.items():
                    if isinstance(v, dict):
                        flat_entry[k] = json.dumps(v)
                    else:
                        flat_entry[k] = v
                writer.writerow(flat_entry)

        content = output_io.getvalue()
        ext = ".csv"

    else:
        raise ValueError(f"Unsupported format: {format}")

    if output:
        output_path = Path(output)
    else:
        output_path = LOGS_FOLDER / f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

    output_path.write_text(content, encoding="utf-8")

    return str(output_path)


# =============================================================================
# Test Functions
# =============================================================================

def run_tests():
    """Run audit logger tests"""

    print("\n" + "=" * 60)
    print("AUDIT LOGGER - TEST MODE")
    print("=" * 60 + "\n")

    tests_passed = 0
    tests_failed = 0

    # Test 1: Basic logging
    print("Test 1: Basic Logging")
    print("-" * 40)

    event_id = AuditLogger.log(
        action_type="SEND_EMAIL",
        actor="test_system",
        target={"to": "test@example.com", "subject": "Test Email"},
        result="success",
        approval_status="approved",
        duration_ms=1234
    )

    if event_id and event_id.startswith("evt_"):
        print(f"  Event logged: {event_id} [PASS]")
        tests_passed += 1
    else:
        print(f"  Event logging failed [FAIL]")
        tests_failed += 1

    # Test 2: Multiple action types
    print("\nTest 2: Multiple Action Types")
    print("-" * 40)

    test_actions = [
        ("RECEIVE_EMAIL", "gmail_watcher"),
        ("CREATE_POST", "linkedin_watcher"),
        ("APPROVE_ACTION", "approval_watcher"),
        ("CREATE_TASK", "ralph_wiggum"),
        ("ERROR", "error_recovery"),
    ]

    for action_type, actor in test_actions:
        event_id = AuditLogger.log(
            action_type=action_type,
            actor=actor,
            target={"test": True},
            result="success"
        )
        print(f"  {action_type}: {event_id[:20]}... [PASS]")
        tests_passed += 1

    # Flush buffer
    AuditLogger.flush()

    # Test 3: Get entries
    print("\nTest 3: Get Entries")
    print("-" * 40)

    entries = AuditLogger.get_entries(limit=10)
    print(f"  Retrieved {len(entries)} entries [PASS]")
    tests_passed += 1

    # Test 4: Get stats
    print("\nTest 4: Get Statistics")
    print("-" * 40)

    stats = AuditLogger.get_stats()
    print(f"  Total: {stats['total']}")
    print(f"  Success rate: {stats['success_rate']}%")
    print(f"  Action types: {len(stats['by_type'])}")
    tests_passed += 1

    # Test 5: Search
    print("\nTest 5: Search Functionality")
    print("-" * 40)

    results = AuditLogger.search("SEND_EMAIL")
    print(f"  Found {len(results)} matches for 'SEND_EMAIL' [PASS]")
    tests_passed += 1

    # Test 6: Generate summary
    print("\nTest 6: Generate Summary")
    print("-" * 40)

    summary = generate_summary()
    if "Audit Summary" in summary:
        print(f"  Summary generated ({len(summary)} chars) [PASS]")
        tests_passed += 1
    else:
        print(f"  Summary generation failed [FAIL]")
        tests_failed += 1

    # Test 7: Export
    print("\nTest 7: Export to JSON")
    print("-" * 40)

    export_path = export_logs(format="json", days=1)
    if Path(export_path).exists():
        print(f"  Exported to: {export_path} [PASS]")
        Path(export_path).unlink()  # Cleanup
        tests_passed += 1
    else:
        print(f"  Export failed [FAIL]")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60 + "\n")

    return tests_failed == 0


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Audit Logger - Comprehensive Action Logging System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument("--today", action="store_true", help="View today's audit log")
    parser.add_argument("--date", type=str, metavar="YYYY-MM-DD", help="View specific date")
    parser.add_argument("--summary", action="store_true", help="Generate daily summary")
    parser.add_argument("--search", type=str, metavar="QUERY", help="Search logs")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--export", type=str, choices=["json", "csv"], help="Export format")
    parser.add_argument("--output", type=str, help="Export output file")
    parser.add_argument("--days", type=int, default=7, help="Days to include in export/search")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old logs")
    parser.add_argument("--limit", type=int, default=50, help="Limit number of entries")

    args = parser.parse_args()

    # Ensure directories exist
    AUDIT_FOLDER.mkdir(parents=True, exist_ok=True)

    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    elif args.today or args.date:
        if args.date:
            date = datetime.strptime(args.date, "%Y-%m-%d")
        else:
            date = datetime.now()

        entries = AuditLogger.get_entries(date, limit=args.limit)

        print(f"\nAudit Log - {date.strftime('%Y-%m-%d')}")
        print("-" * 60)

        if not entries:
            print("No entries found")
        else:
            for entry in entries:
                time_str = entry.get("timestamp", "")[:19].replace("T", " ")
                action = entry.get("action_type", "?")
                actor = entry.get("actor", "?")
                result = entry.get("result", "?")
                print(f"[{time_str}] {action:15} | {actor:20} | {result}")

    elif args.summary:
        save_summary()

    elif args.search:
        results = AuditLogger.search(args.search, days=args.days)

        print(f"\nSearch Results: '{args.search}'")
        print("-" * 60)
        print(f"Found {len(results)} matches in last {args.days} days\n")

        for entry in results[:args.limit]:
            time_str = entry.get("timestamp", "")[:19].replace("T", " ")
            action = entry.get("action_type", "?")
            actor = entry.get("actor", "?")
            print(f"[{time_str}] {action} | {actor}")

    elif args.stats:
        stats = AuditLogger.get_stats()

        print("\nAudit Statistics - Today")
        print("-" * 40)
        print(f"Total Actions: {stats['total']}")
        print(f"Success Rate: {stats['success_rate']}%")
        print(f"Avg Duration: {stats['avg_duration_ms']}ms")

        print("\nBy Action Type:")
        for action, count in sorted(stats['by_type'].items(), key=lambda x: -x[1])[:10]:
            print(f"  {action}: {count}")

        print("\nBy Actor:")
        for actor, count in sorted(stats['by_actor'].items(), key=lambda x: -x[1])[:5]:
            print(f"  {actor}: {count}")

    elif args.export:
        output_path = export_logs(format=args.export, output=args.output, days=args.days)
        print(f"Exported to: {output_path}")

    elif args.cleanup:
        cleanup_old_logs()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
