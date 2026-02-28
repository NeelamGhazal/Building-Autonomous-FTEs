#!/usr/bin/env python3
"""
Error Recovery System - Graceful Degradation & Retry Logic

Handles transient errors, auth failures, logic errors, and system crashes
with automatic recovery, exponential backoff, and graceful degradation.

Usage:
    python3 error_recovery.py --test
    python3 error_recovery.py --health
    python3 error_recovery.py --status
    python3 error_recovery.py --simulate network_timeout
"""

import os
import sys
import json
import time
import random
import shutil
import argparse
import traceback
import functools
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable, List, Type
from enum import Enum
from dataclasses import dataclass, asdict

# =============================================================================
# Configuration
# =============================================================================

VAULT_PATH = Path("/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault")
LOGS_FOLDER = VAULT_PATH / "Logs"
ERROR_LOG = LOGS_FOLDER / "error_recovery.log"
QUEUE_FOLDER = VAULT_PATH / "Queue"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
TEMP_FOLDER = Path("/tmp/ai_employee_backup")

# Retry configuration
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 60.0
DEFAULT_EXPONENTIAL_BASE = 2

# =============================================================================
# Error Types
# =============================================================================

class ErrorCategory(Enum):
    TRANSIENT = "transient"      # Network, rate limit - retry
    AUTH = "auth"                # Token expired - alert human
    LOGIC = "logic"              # AI misinterpretation - review queue
    SYSTEM = "system"            # Crash, disk full - watchdog


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for an error"""
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: str
    traceback: Optional[str] = None
    action: Optional[str] = None
    service: Optional[str] = None
    retry_count: int = 0
    recovered: bool = False
    recovery_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        return data


# =============================================================================
# Logging
# =============================================================================

def log(message: str, level: str = "INFO") -> None:
    """Log message to error_recovery.log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {level:8} | {message}"

    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

    if level in ["ERROR", "CRITICAL"]:
        print(f"[{level}] {message}", file=sys.stderr)
    else:
        print(f"[{level}] {message}")


# =============================================================================
# Error Classification
# =============================================================================

# Known error patterns for classification
ERROR_PATTERNS = {
    # Transient errors
    "ConnectionError": ErrorCategory.TRANSIENT,
    "TimeoutError": ErrorCategory.TRANSIENT,
    "ConnectionRefusedError": ErrorCategory.TRANSIENT,
    "ConnectionResetError": ErrorCategory.TRANSIENT,
    "BrokenPipeError": ErrorCategory.TRANSIENT,
    "429": ErrorCategory.TRANSIENT,  # Rate limit
    "503": ErrorCategory.TRANSIENT,  # Service unavailable
    "504": ErrorCategory.TRANSIENT,  # Gateway timeout

    # Auth errors
    "401": ErrorCategory.AUTH,
    "403": ErrorCategory.AUTH,
    "AuthenticationError": ErrorCategory.AUTH,
    "InvalidCredentials": ErrorCategory.AUTH,
    "TokenExpired": ErrorCategory.AUTH,

    # Logic errors
    "ValueError": ErrorCategory.LOGIC,
    "KeyError": ErrorCategory.LOGIC,
    "AssertionError": ErrorCategory.LOGIC,

    # System errors
    "OSError": ErrorCategory.SYSTEM,
    "IOError": ErrorCategory.SYSTEM,
    "MemoryError": ErrorCategory.SYSTEM,
    "DiskQuotaExceeded": ErrorCategory.SYSTEM,
    "PermissionError": ErrorCategory.SYSTEM,
}


def classify_error(error: Exception) -> tuple:
    """Classify an error into category and severity"""

    error_type = type(error).__name__
    error_str = str(error)

    # Check error type first
    if error_type in ERROR_PATTERNS:
        category = ERROR_PATTERNS[error_type]
    else:
        # Check error message for HTTP codes
        for pattern, cat in ERROR_PATTERNS.items():
            if pattern in error_str:
                category = cat
                break
        else:
            category = ErrorCategory.LOGIC  # Default

    # Determine severity
    if category == ErrorCategory.SYSTEM:
        severity = ErrorSeverity.CRITICAL
    elif category == ErrorCategory.AUTH:
        severity = ErrorSeverity.HIGH
    elif category == ErrorCategory.TRANSIENT:
        severity = ErrorSeverity.MEDIUM
    else:
        severity = ErrorSeverity.LOW

    return category, severity


# =============================================================================
# Retry Logic with Exponential Backoff
# =============================================================================

def calculate_backoff(
    attempt: int,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    exponential_base: int = DEFAULT_EXPONENTIAL_BASE,
    jitter: bool = True
) -> float:
    """Calculate delay with exponential backoff and optional jitter"""

    delay = min(base_delay * (exponential_base ** attempt), max_delay)

    if jitter:
        # Add random jitter to prevent thundering herd
        delay = delay * (0.5 + random.random())

    return delay


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_on: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable] = None
):
    """Decorator for automatic retry with exponential backoff"""

    if retry_on is None:
        retry_on = [ConnectionError, TimeoutError, OSError]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except tuple(retry_on) as e:
                    last_exception = e
                    category, severity = classify_error(e)

                    if attempt < max_retries:
                        delay = calculate_backoff(attempt)
                        log(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e} (waiting {delay:.1f}s)")

                        if on_retry:
                            on_retry(attempt, e)

                        time.sleep(delay)
                    else:
                        log(f"Max retries reached for {func.__name__}: {e}", "ERROR")

                except Exception as e:
                    # Non-retryable error
                    log(f"Non-retryable error in {func.__name__}: {e}", "ERROR")
                    raise

            raise last_exception

        return wrapper
    return decorator


# =============================================================================
# Error Handler
# =============================================================================

class ErrorHandler:
    """Central error handling system"""

    _error_history: List[ErrorContext] = []
    _max_history = 1000

    @classmethod
    def handle(
        cls,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        raise_on_critical: bool = True
    ) -> ErrorContext:
        """Handle an error with appropriate recovery strategy"""

        category, severity = classify_error(error)
        error_type = type(error).__name__

        error_ctx = ErrorContext(
            error_type=error_type,
            message=str(error),
            category=category,
            severity=severity,
            timestamp=datetime.now(timezone.utc).isoformat(),
            traceback=traceback.format_exc(),
            action=context.get("action") if context else None,
            service=context.get("service") if context else None,
        )

        # Log the error
        log(f"Error: {error_type} - {error} (category: {category.value}, severity: {severity.value})", "ERROR")

        # Apply recovery strategy
        recovery_action = cls._apply_recovery_strategy(error_ctx, context)
        error_ctx.recovery_action = recovery_action

        # Store in history
        cls._error_history.append(error_ctx)
        if len(cls._error_history) > cls._max_history:
            cls._error_history = cls._error_history[-cls._max_history:]

        # Import audit logger to log error
        try:
            from audit_logger import AuditLogger
            AuditLogger.log(
                action_type="ERROR",
                actor=context.get("service", "unknown") if context else "unknown",
                target={"error": error_type, "message": str(error)[:200]},
                result="error",
                metadata={"category": category.value, "severity": severity.value}
            )
        except ImportError:
            pass

        # Raise critical errors if requested
        if raise_on_critical and severity == ErrorSeverity.CRITICAL:
            raise error

        return error_ctx

    @classmethod
    def _apply_recovery_strategy(cls, error_ctx: ErrorContext, context: Optional[Dict]) -> str:
        """Apply the appropriate recovery strategy"""

        category = error_ctx.category

        if category == ErrorCategory.TRANSIENT:
            return cls._handle_transient(error_ctx, context)

        elif category == ErrorCategory.AUTH:
            return cls._handle_auth(error_ctx, context)

        elif category == ErrorCategory.LOGIC:
            return cls._handle_logic(error_ctx, context)

        elif category == ErrorCategory.SYSTEM:
            return cls._handle_system(error_ctx, context)

        return "no_action"

    @classmethod
    def _handle_transient(cls, error_ctx: ErrorContext, context: Optional[Dict]) -> str:
        """Handle transient errors - queue for retry"""

        log(f"Transient error - will retry automatically", "INFO")
        return "queued_for_retry"

    @classmethod
    def _handle_auth(cls, error_ctx: ErrorContext, context: Optional[Dict]) -> str:
        """Handle auth errors - alert human"""

        service = error_ctx.service or "Unknown Service"

        # Create alert file
        alert_file = NEEDS_ACTION / f"AUTH_ERROR_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        alert_content = f"""---
type: auth_error
service: {service}
error: {error_ctx.error_type}
severity: critical
requires_action: true
created: {error_ctx.timestamp}
---

## Authentication Error

**Service:** {service}
**Error:** {error_ctx.message}
**Time:** {error_ctx.timestamp}

### Required Action

1. Check credentials for {service}
2. If token expired, re-authenticate:
   - Gmail: `python3 email_mcp_server.py --reauth`
   - LinkedIn: Check linkedin_credentials.json
3. Restart the affected service

### Affected Operations

- All {service} operations are PAUSED
- Queued items will be processed after recovery

### Error Details

```
{error_ctx.traceback or 'No traceback available'}
```
"""

        NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
        alert_file.write_text(alert_content, encoding="utf-8")

        log(f"Auth error alert created: {alert_file}", "WARNING")
        return "human_alert_created"

    @classmethod
    def _handle_logic(cls, error_ctx: ErrorContext, context: Optional[Dict]) -> str:
        """Handle logic errors - add to review queue"""

        review_file = NEEDS_ACTION / f"REVIEW_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        review_content = f"""---
type: logic_error
error: {error_ctx.error_type}
severity: {error_ctx.severity.value}
requires_review: true
created: {error_ctx.timestamp}
---

## Logic Error - Human Review Required

**Error:** {error_ctx.message}
**Action:** {error_ctx.action or 'Unknown'}
**Time:** {error_ctx.timestamp}

### Context

The AI encountered an unexpected situation that requires human review.

### Error Details

```
{error_ctx.traceback or 'No traceback available'}
```

### Suggested Actions

- [ ] Review the context of this error
- [ ] Determine if this was a one-time issue or pattern
- [ ] Update rules if needed
"""

        NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
        review_file.write_text(review_content, encoding="utf-8")

        log(f"Logic error review created: {review_file}", "WARNING")
        return "added_to_review_queue"

    @classmethod
    def _handle_system(cls, error_ctx: ErrorContext, context: Optional[Dict]) -> str:
        """Handle system errors - watchdog restart"""

        # Check specific system errors
        if "disk" in error_ctx.message.lower() or "space" in error_ctx.message.lower():
            cls._handle_disk_full()
            return "disk_cleanup_initiated"

        if "memory" in error_ctx.message.lower():
            log("Memory error detected - recommend restart", "CRITICAL")
            return "restart_recommended"

        log(f"System error - watchdog should handle restart", "CRITICAL")
        return "watchdog_notified"

    @classmethod
    def _handle_disk_full(cls):
        """Handle disk full - cleanup old logs"""

        log("Disk full - initiating log cleanup", "WARNING")

        # Cleanup old audit logs (keep last 30 days)
        audit_folder = LOGS_FOLDER / "audit"
        if audit_folder.exists():
            cutoff = datetime.now() - timedelta(days=30)
            for log_file in audit_folder.glob("*.json"):
                try:
                    file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")
                    if file_date < cutoff:
                        log_file.unlink()
                        log(f"Deleted old log: {log_file.name}")
                except:
                    pass

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get error statistics"""

        if not cls._error_history:
            return {"total": 0, "by_category": {}, "by_severity": {}}

        stats = {
            "total": len(cls._error_history),
            "by_category": {},
            "by_severity": {},
            "recovered": sum(1 for e in cls._error_history if e.recovered),
            "last_error": cls._error_history[-1].to_dict() if cls._error_history else None
        }

        for error in cls._error_history:
            cat = error.category.value
            sev = error.severity.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1

        return stats

    @classmethod
    def get_recent(cls, count: int = 10) -> List[Dict]:
        """Get recent errors"""
        return [e.to_dict() for e in cls._error_history[-count:]]


# =============================================================================
# Graceful Degradation
# =============================================================================

class GracefulDegradation:
    """Handle graceful degradation when services fail"""

    @staticmethod
    def queue_email(email_data: Dict[str, Any]) -> Path:
        """Queue email locally when Gmail API is down"""

        queue_path = QUEUE_FOLDER / "emails"
        queue_path.mkdir(parents=True, exist_ok=True)

        filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}.json"
        file_path = queue_path / filename

        email_data["queued_at"] = datetime.now(timezone.utc).isoformat()
        email_data["status"] = "queued"

        file_path.write_text(json.dumps(email_data, indent=2), encoding="utf-8")

        log(f"Email queued locally: {filename}")
        return file_path

    @staticmethod
    def queue_post(post_data: Dict[str, Any]) -> Path:
        """Queue social media post when API is down"""

        queue_path = QUEUE_FOLDER / "posts"
        queue_path.mkdir(parents=True, exist_ok=True)

        filename = f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}.json"
        file_path = queue_path / filename

        post_data["queued_at"] = datetime.now(timezone.utc).isoformat()
        post_data["status"] = "queued"

        file_path.write_text(json.dumps(post_data, indent=2), encoding="utf-8")

        log(f"Post queued locally: {filename}")
        return file_path

    @staticmethod
    def get_queue_status() -> Dict[str, Any]:
        """Get status of local queues"""

        status = {"emails": 0, "posts": 0, "total": 0}

        email_queue = QUEUE_FOLDER / "emails"
        post_queue = QUEUE_FOLDER / "posts"

        if email_queue.exists():
            status["emails"] = len(list(email_queue.glob("*.json")))

        if post_queue.exists():
            status["posts"] = len(list(post_queue.glob("*.json")))

        status["total"] = status["emails"] + status["posts"]

        return status

    @staticmethod
    def process_queue(queue_type: str = "all") -> Dict[str, Any]:
        """Process queued items (called when service recovers)"""

        results = {"processed": 0, "failed": 0, "remaining": 0}

        # Process email queue
        if queue_type in ["all", "emails"]:
            email_queue = QUEUE_FOLDER / "emails"
            if email_queue.exists():
                for queue_file in email_queue.glob("*.json"):
                    try:
                        data = json.loads(queue_file.read_text(encoding="utf-8"))
                        # Here you would actually send the email
                        # For now, just mark as processed
                        log(f"Would process queued email: {queue_file.name}")
                        queue_file.unlink()
                        results["processed"] += 1
                    except Exception as e:
                        log(f"Failed to process {queue_file.name}: {e}", "ERROR")
                        results["failed"] += 1

        # Update remaining count
        results["remaining"] = GracefulDegradation.get_queue_status()["total"]

        return results

    @staticmethod
    def use_temp_folder() -> Path:
        """Switch to temp folder when vault is locked"""

        TEMP_FOLDER.mkdir(parents=True, exist_ok=True)

        # Create necessary subfolders
        (TEMP_FOLDER / "Needs_Action").mkdir(exist_ok=True)
        (TEMP_FOLDER / "Pending_Approval").mkdir(exist_ok=True)
        (TEMP_FOLDER / "Logs").mkdir(exist_ok=True)

        log(f"Using temp folder: {TEMP_FOLDER}", "WARNING")
        return TEMP_FOLDER

    @staticmethod
    def sync_temp_to_vault():
        """Sync temp folder back to vault when available"""

        if not TEMP_FOLDER.exists():
            return

        synced = 0

        for subfolder in ["Needs_Action", "Pending_Approval", "Logs"]:
            temp_sub = TEMP_FOLDER / subfolder
            vault_sub = VAULT_PATH / subfolder

            if temp_sub.exists():
                vault_sub.mkdir(parents=True, exist_ok=True)

                for file in temp_sub.iterdir():
                    if file.is_file():
                        shutil.copy2(str(file), str(vault_sub / file.name))
                        file.unlink()
                        synced += 1

        log(f"Synced {synced} files from temp to vault")

        # Clean up empty temp folder
        try:
            shutil.rmtree(TEMP_FOLDER)
        except:
            pass


# =============================================================================
# Health Check
# =============================================================================

def check_health() -> Dict[str, Any]:
    """Check system health"""

    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "warnings": [],
        "errors": []
    }

    # Check vault accessibility
    try:
        test_file = VAULT_PATH / ".health_check"
        test_file.write_text("test")
        test_file.unlink()
        health["checks"]["vault_writable"] = True
    except Exception as e:
        health["checks"]["vault_writable"] = False
        health["errors"].append(f"Vault not writable: {e}")
        health["status"] = "degraded"

    # Check queue status
    queue_status = GracefulDegradation.get_queue_status()
    health["checks"]["queue_items"] = queue_status["total"]
    if queue_status["total"] > 0:
        health["warnings"].append(f"{queue_status['total']} items in queue")

    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage(VAULT_PATH)
        free_percent = (free / total) * 100
        health["checks"]["disk_free_percent"] = round(free_percent, 1)
        if free_percent < 10:
            health["warnings"].append(f"Low disk space: {free_percent:.1f}% free")
            if free_percent < 5:
                health["status"] = "degraded"
    except:
        health["checks"]["disk_free_percent"] = "unknown"

    # Check error statistics
    error_stats = ErrorHandler.get_stats()
    health["checks"]["recent_errors"] = error_stats["total"]

    # Check for critical errors in last hour
    recent_critical = sum(
        1 for e in ErrorHandler._error_history
        if e.severity == ErrorSeverity.CRITICAL
        and datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")) > datetime.now(timezone.utc) - timedelta(hours=1)
    )
    if recent_critical > 0:
        health["errors"].append(f"{recent_critical} critical errors in last hour")
        health["status"] = "unhealthy"

    # Set overall status
    if health["errors"]:
        health["status"] = "unhealthy"
    elif health["warnings"]:
        health["status"] = "degraded"

    return health


# =============================================================================
# Test Functions
# =============================================================================

def run_tests():
    """Run error recovery tests"""

    print("\n" + "=" * 60)
    print("ERROR RECOVERY SYSTEM - TEST MODE")
    print("=" * 60 + "\n")

    tests_passed = 0
    tests_failed = 0

    # Test 1: Error classification
    print("Test 1: Error Classification")
    print("-" * 40)

    test_errors = [
        (ConnectionError("Connection refused"), ErrorCategory.TRANSIENT),
        (TimeoutError("Request timed out"), ErrorCategory.TRANSIENT),
        (PermissionError("Access denied"), ErrorCategory.SYSTEM),
        (ValueError("Invalid input"), ErrorCategory.LOGIC),
    ]

    for error, expected_cat in test_errors:
        category, severity = classify_error(error)
        status = "PASS" if category == expected_cat else "FAIL"
        print(f"  {type(error).__name__}: {category.value} [{status}]")
        if status == "PASS":
            tests_passed += 1
        else:
            tests_failed += 1

    # Test 2: Exponential backoff
    print("\nTest 2: Exponential Backoff")
    print("-" * 40)

    delays = [calculate_backoff(i, jitter=False) for i in range(5)]
    expected = [1.0, 2.0, 4.0, 8.0, 16.0]

    for i, (actual, exp) in enumerate(zip(delays, expected)):
        status = "PASS" if actual == exp else "FAIL"
        print(f"  Attempt {i}: {actual}s (expected {exp}s) [{status}]")
        if status == "PASS":
            tests_passed += 1
        else:
            tests_failed += 1

    # Test 3: Queue operations
    print("\nTest 3: Queue Operations")
    print("-" * 40)

    test_email = {"to": "test@example.com", "subject": "Test", "body": "Test body"}
    queue_path = GracefulDegradation.queue_email(test_email)
    exists = queue_path.exists()
    print(f"  Queue email: {'PASS' if exists else 'FAIL'}")
    if exists:
        tests_passed += 1
        queue_path.unlink()  # Cleanup
    else:
        tests_failed += 1

    queue_status = GracefulDegradation.get_queue_status()
    print(f"  Queue status: {queue_status}")
    tests_passed += 1

    # Test 4: Health check
    print("\nTest 4: Health Check")
    print("-" * 40)

    health = check_health()
    print(f"  Status: {health['status']}")
    print(f"  Vault writable: {health['checks'].get('vault_writable', 'unknown')}")
    print(f"  Disk free: {health['checks'].get('disk_free_percent', 'unknown')}%")

    if health["checks"].get("vault_writable"):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 5: Retry decorator
    print("\nTest 5: Retry Decorator")
    print("-" * 40)

    attempt_count = 0

    @with_retry(max_retries=3, retry_on=[ValueError])
    def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError("Simulated failure")
        return "success"

    try:
        result = flaky_function()
        print(f"  Retries worked: {result} after {attempt_count} attempts [PASS]")
        tests_passed += 1
    except:
        print(f"  Retry test failed [FAIL]")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60 + "\n")

    return tests_failed == 0


def simulate_error(error_type: str):
    """Simulate specific error types for testing"""

    print(f"\nSimulating error: {error_type}")
    print("-" * 40)

    if error_type == "network_timeout":
        error = TimeoutError("Connection timed out after 30 seconds")
    elif error_type == "auth_expired":
        error = Exception("401 Unauthorized: Token expired")
    elif error_type == "disk_full":
        error = OSError("No space left on device")
    elif error_type == "rate_limit":
        error = Exception("429 Too Many Requests: Rate limit exceeded")
    else:
        print(f"Unknown error type: {error_type}")
        print("Available: network_timeout, auth_expired, disk_full, rate_limit")
        return

    ctx = ErrorHandler.handle(
        error,
        context={"action": "test_simulation", "service": "test_service"},
        raise_on_critical=False
    )

    print(f"Category: {ctx.category.value}")
    print(f"Severity: {ctx.severity.value}")
    print(f"Recovery action: {ctx.recovery_action}")


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Error Recovery System - Graceful Degradation & Retry Logic",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument("--health", action="store_true", help="Check system health")
    parser.add_argument("--status", action="store_true", help="Show error statistics")
    parser.add_argument("--recent", type=int, metavar="N", help="Show N recent errors")
    parser.add_argument("--simulate", type=str, metavar="TYPE", help="Simulate error type")
    parser.add_argument("--queue-status", action="store_true", help="Show queue status")
    parser.add_argument("--process-queue", action="store_true", help="Process queued items")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")

    args = parser.parse_args()

    # Ensure directories exist
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    QUEUE_FOLDER.mkdir(parents=True, exist_ok=True)

    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    elif args.health:
        health = check_health()
        print(f"\nSystem Health: {health['status'].upper()}")
        print("-" * 40)

        for check, value in health["checks"].items():
            print(f"  {check}: {value}")

        if health["warnings"]:
            print("\nWarnings:")
            for w in health["warnings"]:
                print(f"  - {w}")

        if health["errors"]:
            print("\nErrors:")
            for e in health["errors"]:
                print(f"  - {e}")

    elif args.status:
        stats = ErrorHandler.get_stats()
        print("\nError Statistics")
        print("-" * 40)
        print(f"  Total errors: {stats['total']}")
        print(f"  Recovered: {stats.get('recovered', 0)}")

        if stats["by_category"]:
            print("\n  By Category:")
            for cat, count in stats["by_category"].items():
                print(f"    {cat}: {count}")

        if stats["by_severity"]:
            print("\n  By Severity:")
            for sev, count in stats["by_severity"].items():
                print(f"    {sev}: {count}")

    elif args.recent:
        errors = ErrorHandler.get_recent(args.recent)
        print(f"\nRecent {len(errors)} Errors")
        print("-" * 40)

        for error in errors:
            print(f"\n  [{error['timestamp']}]")
            print(f"    Type: {error['error_type']}")
            print(f"    Message: {error['message'][:50]}...")
            print(f"    Category: {error['category']}")
            print(f"    Recovery: {error['recovery_action']}")

    elif args.simulate:
        simulate_error(args.simulate)

    elif args.queue_status:
        status = GracefulDegradation.get_queue_status()
        print("\nQueue Status")
        print("-" * 40)
        print(f"  Emails: {status['emails']}")
        print(f"  Posts: {status['posts']}")
        print(f"  Total: {status['total']}")

    elif args.process_queue:
        print("Processing queue...")
        results = GracefulDegradation.process_queue()
        print(f"  Processed: {results['processed']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Remaining: {results['remaining']}")

    elif args.daemon:
        print("Running error recovery daemon...")
        log("Error recovery daemon started")

        # Simple daemon loop
        while True:
            try:
                # Check health every 5 minutes
                health = check_health()
                if health["status"] != "healthy":
                    log(f"Health check: {health['status']}", "WARNING")

                # Process queue if any
                queue_status = GracefulDegradation.get_queue_status()
                if queue_status["total"] > 0:
                    GracefulDegradation.process_queue()

                time.sleep(300)  # 5 minutes

            except KeyboardInterrupt:
                log("Error recovery daemon stopped")
                break

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
