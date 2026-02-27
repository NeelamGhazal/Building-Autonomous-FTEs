#!/usr/bin/env python3
"""
Ralph Wiggum Stop Hook

This script is invoked by Claude Code after each response to determine
whether to continue working on a task or exit.

Exit Codes:
    0 - Task complete, exit Claude Code
    1 - Continue working, re-inject prompt
    2 - Max iterations reached, force exit
    3 - Error occurred, exit with error

Usage:
    This script is configured as a Claude Code hook in settings:

    {
        "hooks": {
            "stop": ".claude/hooks/stop_hook.py"
        }
    }

Environment Variables:
    RALPH_WIGGUM_TASK_ID - Current task ID being processed
    RALPH_WIGGUM_ITERATION - Current iteration number
    RALPH_WIGGUM_MAX_ITERATIONS - Maximum allowed iterations
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# =============================================================================
# Configuration
# =============================================================================

VAULT_PATH = Path("/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault")
ACTIVE_TASKS = VAULT_PATH / "Active_Tasks"
DONE_FOLDER = VAULT_PATH / "Done"
LOGS_FOLDER = VAULT_PATH / "Logs"
LOG_FILE = LOGS_FOLDER / "ralph_wiggum.log"

COMPLETION_PROMISE = "TASK_COMPLETE"

# Exit codes
EXIT_COMPLETE = 0      # Task done, exit
EXIT_CONTINUE = 1      # Continue working
EXIT_MAX_ITER = 2      # Max iterations reached
EXIT_ERROR = 3         # Error occurred

# =============================================================================
# Logging
# =============================================================================

def log(message: str, level: str = "INFO") -> None:
    """Log message to ralph_wiggum.log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {level:5} | STOP_HOOK | {message}"

    # Ensure log folder exists
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

    # Append to log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

# =============================================================================
# Task Detection
# =============================================================================

def get_current_task() -> tuple:
    """
    Get the current active task being worked on.

    Returns:
        tuple: (task_id, task_path, iteration, max_iterations) or (None, None, 0, 0)
    """

    # First, check environment variables (set by ralph_wiggum.py)
    task_id = os.environ.get("RALPH_WIGGUM_TASK_ID")
    iteration = int(os.environ.get("RALPH_WIGGUM_ITERATION", 0))
    max_iterations = int(os.environ.get("RALPH_WIGGUM_MAX_ITERATIONS", 10))

    if task_id:
        task_path = ACTIVE_TASKS / f"{task_id}.md"
        if task_path.exists():
            return task_id, task_path, iteration, max_iterations

    # Fallback: look for any active task
    if ACTIVE_TASKS.exists():
        for task_file in sorted(ACTIVE_TASKS.glob("TASK_*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            # Parse task file to get iteration info
            content = task_file.read_text(encoding="utf-8")

            task_id = task_file.stem
            iteration = 1
            max_iterations = 10

            # Extract from frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    for line in parts[1].split("\n"):
                        if line.startswith("iteration:"):
                            try:
                                iteration = int(line.split(":", 1)[1].strip())
                            except:
                                pass
                        elif line.startswith("max_iterations:"):
                            try:
                                max_iterations = int(line.split(":", 1)[1].strip())
                            except:
                                pass

            return task_id, task_file, iteration, max_iterations

    return None, None, 0, 0


def is_task_complete(task_id: str) -> bool:
    """
    Check if task is complete.

    A task is complete if:
    1. Task file exists in /Done/ folder
    2. Task file contains TASK_COMPLETE
    """

    # Check if in Done folder
    done_file = DONE_FOLDER / f"{task_id}.md"
    if done_file.exists():
        return True

    # Check if active task contains completion promise
    active_file = ACTIVE_TASKS / f"{task_id}.md"
    if active_file.exists():
        content = active_file.read_text(encoding="utf-8")
        if COMPLETION_PROMISE in content:
            return True

    return False


def check_task_status() -> int:
    """
    Main stop hook logic.

    Returns:
        int: Exit code (0=complete, 1=continue, 2=max_iter, 3=error)
    """

    task_id, task_path, iteration, max_iterations = get_current_task()

    # No active task
    if not task_id:
        log("No active task found, exiting")
        return EXIT_COMPLETE

    log(f"Checking task {task_id} (iteration {iteration}/{max_iterations})")

    # Check if task is complete
    if is_task_complete(task_id):
        log(f"Task {task_id} is COMPLETE!")
        return EXIT_COMPLETE

    # Check max iterations
    if iteration >= max_iterations:
        log(f"Task {task_id} reached max iterations ({max_iterations})", "WARNING")
        return EXIT_MAX_ITER

    # Continue working
    log(f"Task {task_id} not complete, continue (iteration {iteration})")
    return EXIT_CONTINUE


# =============================================================================
# Re-inject Prompt
# =============================================================================

def get_continuation_prompt(task_id: str, task_path: Path, iteration: int, max_iterations: int) -> str:
    """Generate prompt to re-inject for continued work"""

    return f"""
## Ralph Wiggum Loop - Continue Working

**Task ID:** {task_id}
**Current Iteration:** {iteration + 1} of {max_iterations}
**Task File:** {task_path}

Please continue working on this task:
1. Read the task file to see current progress
2. Complete the next steps
3. Update the Progress Log
4. When FULLY complete:
   - Add "{COMPLETION_PROMISE}" to the task file
   - Move the file to /Done/

Keep working until the task is complete or you need HITL approval.
"""


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """
    Stop hook entry point.

    This is called by Claude Code after each response.
    The exit code determines what happens next:
    - 0: Exit Claude Code (task complete)
    - 1: Re-inject prompt and continue
    - 2: Force exit (max iterations)
    - 3: Exit with error
    """

    try:
        exit_code = check_task_status()

        if exit_code == EXIT_CONTINUE:
            # Get task info for continuation prompt
            task_id, task_path, iteration, max_iterations = get_current_task()

            if task_id and task_path:
                # Output continuation prompt to stdout
                # This will be re-injected by the caller
                prompt = get_continuation_prompt(task_id, task_path, iteration, max_iterations)
                print(prompt)

        sys.exit(exit_code)

    except Exception as e:
        log(f"Stop hook error: {e}", "ERROR")
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
