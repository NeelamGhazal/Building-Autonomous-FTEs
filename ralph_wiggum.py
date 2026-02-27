#!/usr/bin/env python3
"""
Ralph Wiggum Loop - Autonomous Multi-Step Task Completion

Named after Ralph Wiggum's "I'm helping!" - this system allows Claude
to work autonomously on complex tasks with iteration control and
completion detection via stop hooks.

Usage:
    python3 ralph_wiggum.py --task "Process all emails in Needs_Action"
    python3 ralph_wiggum.py --demo "Process all emails in Needs_Action"
    python3 ralph_wiggum.py --list
    python3 ralph_wiggum.py --status TASK_ID
"""

import os
import sys
import json
import uuid
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# =============================================================================
# Configuration
# =============================================================================

VAULT_PATH = Path("/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault")
ACTIVE_TASKS = VAULT_PATH / "Active_Tasks"
DONE_FOLDER = VAULT_PATH / "Done"
LOGS_FOLDER = VAULT_PATH / "Logs"
LOG_FILE = LOGS_FOLDER / "ralph_wiggum.log"

DEFAULT_MAX_ITERATIONS = 10
COMPLETION_PROMISE = "TASK_COMPLETE"

# =============================================================================
# Logging
# =============================================================================

def log(message: str, level: str = "INFO") -> None:
    """Log message to ralph_wiggum.log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {level:5} | {message}"

    # Ensure log folder exists
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

    # Append to log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

    # Also print to console
    print(f"[{level}] {message}")

# =============================================================================
# Task Management
# =============================================================================

def generate_task_id() -> str:
    """Generate unique task ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    return f"TASK_{timestamp}_{short_id}"


def create_task_file(prompt: str, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> Path:
    """Create a new task file in Active_Tasks folder"""

    # Ensure folder exists
    ACTIVE_TASKS.mkdir(parents=True, exist_ok=True)

    task_id = generate_task_id()
    timestamp = datetime.now().isoformat()

    content = f"""---
task_id: {task_id}
prompt: {prompt}
status: in_progress
iteration: 1
max_iterations: {max_iterations}
completion_promise: {COMPLETION_PROMISE}
created: {timestamp}
---

## Task Details

{prompt}

## Instructions for Claude

1. Work on this task step by step
2. Update the Progress Log below after each significant action
3. When fully complete, add "{COMPLETION_PROMISE}" to this file
4. Then move this file to /Done/ folder

## Progress Log

### Iteration 1 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Task started
- Working on: {prompt}

"""

    task_file = ACTIVE_TASKS / f"{task_id}.md"
    task_file.write_text(content, encoding="utf-8")

    log(f"Task {task_id} created: {prompt[:50]}...")

    return task_file


def parse_task_file(task_path: Path) -> Dict[str, Any]:
    """Parse task file frontmatter"""
    content = task_path.read_text(encoding="utf-8")

    # Extract frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = parts[2].strip()

            # Parse YAML-like frontmatter
            data = {}
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip()] = value.strip()

            data["body"] = body
            data["full_content"] = content
            return data

    return {"body": content, "full_content": content}


def update_task_iteration(task_path: Path, iteration: int) -> None:
    """Update task file with new iteration"""
    content = task_path.read_text(encoding="utf-8")

    # Update iteration in frontmatter
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("iteration:"):
            lines[i] = f"iteration: {iteration}"
            break

    # Add iteration log entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    iteration_entry = f"\n### Iteration {iteration} - {timestamp}\n- Continuing work on task\n"

    updated_content = "\n".join(lines) + iteration_entry
    task_path.write_text(updated_content, encoding="utf-8")

    log(f"Task {task_path.stem} updated to iteration {iteration}")


def is_task_complete(task_id: str) -> bool:
    """Check if task is complete (moved to Done folder)"""
    done_file = DONE_FOLDER / f"{task_id}.md"
    return done_file.exists()


def list_active_tasks() -> List[Dict[str, Any]]:
    """List all active tasks"""
    tasks = []

    if not ACTIVE_TASKS.exists():
        return tasks

    for task_file in ACTIVE_TASKS.glob("TASK_*.md"):
        task_data = parse_task_file(task_file)
        task_data["file"] = str(task_file)
        tasks.append(task_data)

    return tasks


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a specific task"""

    # Check Active_Tasks
    active_file = ACTIVE_TASKS / f"{task_id}.md"
    if active_file.exists():
        data = parse_task_file(active_file)
        data["location"] = "Active_Tasks"
        return data

    # Check Done
    done_file = DONE_FOLDER / f"{task_id}.md"
    if done_file.exists():
        data = parse_task_file(done_file)
        data["location"] = "Done"
        data["status"] = "completed"
        return data

    return None


def cancel_task(task_id: str) -> bool:
    """Cancel an active task"""
    active_file = ACTIVE_TASKS / f"{task_id}.md"

    if not active_file.exists():
        log(f"Task {task_id} not found in Active_Tasks", "ERROR")
        return False

    # Update status to cancelled
    content = active_file.read_text(encoding="utf-8")
    content = content.replace("status: in_progress", "status: cancelled")

    # Move to Done
    DONE_FOLDER.mkdir(parents=True, exist_ok=True)
    done_file = DONE_FOLDER / f"{task_id}.md"
    done_file.write_text(content, encoding="utf-8")
    active_file.unlink()

    log(f"Task {task_id} cancelled and moved to Done")
    return True


# =============================================================================
# Claude Code Integration
# =============================================================================

def invoke_claude(task_path: Path, iteration: int) -> int:
    """Invoke Claude Code with the task"""

    task_data = parse_task_file(task_path)
    task_id = task_data.get("task_id", task_path.stem)
    prompt = task_data.get("prompt", "Continue working on the task")
    max_iterations = int(task_data.get("max_iterations", DEFAULT_MAX_ITERATIONS))

    # Build the prompt for Claude
    claude_prompt = f"""
## Ralph Wiggum Loop - Iteration {iteration}/{max_iterations}

**Task ID:** {task_id}
**Task File:** {task_path}

**Your Task:**
{prompt}

**Instructions:**
1. Read the task file at {task_path}
2. Work on the task step by step
3. Update the Progress Log in the task file
4. When FULLY complete:
   - Add the line "{COMPLETION_PROMISE}" to the task file
   - Move the task file from /Active_Tasks/ to /Done/
5. If you need HITL approval for any action, create the approval request and note it in the task

**Current Iteration:** {iteration} of {max_iterations}
**Completion Signal:** Move task file to /Done/ when done
"""

    log(f"Invoking Claude Code for {task_id} (iteration {iteration})")

    # Note: In real implementation, this would invoke claude CLI
    # For demo, we simulate the behavior
    print(f"\n{'='*60}")
    print(f"RALPH WIGGUM LOOP - Iteration {iteration}")
    print(f"{'='*60}")
    print(f"Task: {prompt}")
    print(f"File: {task_path}")
    print(f"{'='*60}\n")

    return 0


def run_autonomous_loop(task_path: Path, demo_mode: bool = False) -> bool:
    """Run the autonomous task completion loop"""

    task_data = parse_task_file(task_path)
    task_id = task_data.get("task_id", task_path.stem)
    max_iterations = int(task_data.get("max_iterations", DEFAULT_MAX_ITERATIONS))

    log(f"Starting Ralph Wiggum Loop for {task_id}")

    iteration = 1

    while iteration <= max_iterations:
        # Check if task is already complete
        if is_task_complete(task_id):
            log(f"Task {task_id} completed successfully after {iteration-1} iterations")
            print(f"\n{'='*60}")
            print(f"TASK COMPLETE!")
            print(f"Task {task_id} finished in {iteration-1} iterations")
            print(f"{'='*60}\n")
            return True

        # Check if task file still exists
        if not task_path.exists():
            log(f"Task file {task_path} no longer exists", "WARNING")
            return False

        # Update iteration in task file
        update_task_iteration(task_path, iteration)

        if demo_mode:
            # Demo mode: simulate work
            print(f"\n[DEMO] Iteration {iteration}: Simulating work...")

            # Simulate progress
            if iteration >= 3:
                # After 3 iterations, mark as complete
                content = task_path.read_text(encoding="utf-8")
                content = content.replace("status: in_progress", "status: completed")
                content += f"\n\n## Completion\n\n{COMPLETION_PROMISE}\n\nTask completed successfully after {iteration} iterations.\n"
                task_path.write_text(content, encoding="utf-8")

                # Move to Done
                DONE_FOLDER.mkdir(parents=True, exist_ok=True)
                done_file = DONE_FOLDER / f"{task_id}.md"
                shutil.move(str(task_path), str(done_file))

                log(f"[DEMO] Task {task_id} completed and moved to Done")
                print(f"\n[DEMO] Task completed after {iteration} iterations!")
                return True

            print(f"[DEMO] Working... (will complete at iteration 3)")
        else:
            # Real mode: invoke Claude Code
            result = invoke_claude(task_path, iteration)

            # Check stop hook result
            # In real implementation, this would be handled by the stop hook
            # For now, we check if task was moved to Done
            if is_task_complete(task_id):
                log(f"Task {task_id} completed after {iteration} iterations")
                return True

        iteration += 1
        log(f"Iteration {iteration-1} complete, continuing...")

    # Max iterations reached
    log(f"Task {task_id} reached max iterations ({max_iterations})", "WARNING")

    # Mark as failed
    if task_path.exists():
        content = task_path.read_text(encoding="utf-8")
        content = content.replace("status: in_progress", "status: failed")
        content += f"\n\n## Failed\n\nMax iterations ({max_iterations}) reached without completion.\n"
        task_path.write_text(content, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"TASK FAILED - Max iterations reached")
    print(f"Task {task_id} did not complete after {max_iterations} iterations")
    print(f"{'='*60}\n")

    return False


# =============================================================================
# Demo Mode
# =============================================================================

def run_demo(prompt: str) -> None:
    """Run a demo of the Ralph Wiggum Loop"""

    print("\n" + "="*60)
    print("RALPH WIGGUM LOOP - DEMO MODE")
    print("="*60)
    print(f"\nTask: {prompt}")
    print("\nThis demo will:")
    print("1. Create a task file in /Active_Tasks/")
    print("2. Simulate 3 iterations of autonomous work")
    print("3. Mark task complete and move to /Done/")
    print("4. Log all activity to /Logs/ralph_wiggum.log")
    print("\n" + "-"*60 + "\n")

    # Create task
    task_path = create_task_file(prompt, max_iterations=5)
    print(f"Created task file: {task_path}")

    # Run autonomous loop in demo mode
    success = run_autonomous_loop(task_path, demo_mode=True)

    print("\n" + "-"*60)
    print("DEMO COMPLETE")
    print("-"*60)

    if success:
        task_id = task_path.stem
        done_file = DONE_FOLDER / f"{task_id}.md"
        print(f"\nTask completed successfully!")
        print(f"Task file moved to: {done_file}")
    else:
        print(f"\nTask failed or was cancelled")

    print(f"Log file: {LOG_FILE}")
    print("="*60 + "\n")


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum Loop - Autonomous Multi-Step Task Completion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 ralph_wiggum.py --task "Process all emails"
  python3 ralph_wiggum.py --demo "Process all emails in Needs_Action"
  python3 ralph_wiggum.py --list
  python3 ralph_wiggum.py --status TASK_20240115_103000_abc123
  python3 ralph_wiggum.py --cancel TASK_20240115_103000_abc123
        """
    )

    parser.add_argument("--task", "-t", type=str, help="Create and run a new task")
    parser.add_argument("--demo", type=str, help="Run demo mode with specified task")
    parser.add_argument("--max-iterations", "-m", type=int, default=DEFAULT_MAX_ITERATIONS,
                        help=f"Maximum iterations (default: {DEFAULT_MAX_ITERATIONS})")
    parser.add_argument("--list", "-l", action="store_true", help="List active tasks")
    parser.add_argument("--status", "-s", type=str, help="Get status of a task")
    parser.add_argument("--cancel", "-c", type=str, help="Cancel an active task")
    parser.add_argument("--log", type=str, help="View log for a task")
    parser.add_argument("--resume", "-r", type=str, help="Resume a paused task")

    args = parser.parse_args()

    # Ensure required folders exist
    ACTIVE_TASKS.mkdir(parents=True, exist_ok=True)
    DONE_FOLDER.mkdir(parents=True, exist_ok=True)
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

    if args.demo:
        run_demo(args.demo)

    elif args.task:
        task_path = create_task_file(args.task, args.max_iterations)
        print(f"Created task: {task_path}")
        print(f"Starting autonomous loop...")
        success = run_autonomous_loop(task_path)
        sys.exit(0 if success else 1)

    elif args.list:
        tasks = list_active_tasks()
        if not tasks:
            print("No active tasks")
        else:
            print(f"\nActive Tasks ({len(tasks)}):")
            print("-" * 60)
            for task in tasks:
                task_id = task.get("task_id", "unknown")
                prompt = task.get("prompt", "")[:40]
                iteration = task.get("iteration", "?")
                max_iter = task.get("max_iterations", "?")
                status = task.get("status", "unknown")
                print(f"  {task_id}")
                print(f"    Prompt: {prompt}...")
                print(f"    Status: {status} (iteration {iteration}/{max_iter})")
                print()

    elif args.status:
        status = get_task_status(args.status)
        if not status:
            print(f"Task {args.status} not found")
            sys.exit(1)
        else:
            print(f"\nTask Status: {args.status}")
            print("-" * 40)
            print(f"  Location: {status.get('location', 'unknown')}")
            print(f"  Status: {status.get('status', 'unknown')}")
            print(f"  Iteration: {status.get('iteration', '?')}/{status.get('max_iterations', '?')}")
            print(f"  Prompt: {status.get('prompt', 'N/A')}")
            print()

    elif args.cancel:
        if cancel_task(args.cancel):
            print(f"Task {args.cancel} cancelled")
        else:
            print(f"Failed to cancel task {args.cancel}")
            sys.exit(1)

    elif args.log:
        # Show log entries for this task
        if LOG_FILE.exists():
            content = LOG_FILE.read_text(encoding="utf-8")
            relevant_lines = [line for line in content.split("\n") if args.log in line]
            if relevant_lines:
                print(f"\nLog entries for {args.log}:")
                print("-" * 60)
                for line in relevant_lines:
                    print(line)
            else:
                print(f"No log entries found for {args.log}")
        else:
            print("No log file found")

    elif args.resume:
        task_path = ACTIVE_TASKS / f"{args.resume}.md"
        if not task_path.exists():
            print(f"Task {args.resume} not found in Active_Tasks")
            sys.exit(1)

        print(f"Resuming task: {args.resume}")
        success = run_autonomous_loop(task_path)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
