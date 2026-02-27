# Ralph Wiggum Loop Skill

## Overview

The Ralph Wiggum Loop is an autonomous multi-step task completion system using a Stop Hook pattern. Named after the Simpsons character who famously says "I'm helping!", this pattern allows Claude to work autonomously on complex tasks while maintaining control through iteration limits and completion checks.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Ralph Wiggum Loop Flow                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │  Task File   │───▶│  Claude Code │───▶│  Work on Task            │  │
│  │  Created     │    │  Triggered   │    │  (Execute Steps)         │  │
│  └──────────────┘    └──────────────┘    └──────────┬───────────────┘  │
│                                                      │                   │
│                                          ┌───────────▼───────────┐      │
│                                          │     Stop Hook         │      │
│                                          │     Triggered         │      │
│                                          └───────────┬───────────┘      │
│                                                      │                   │
│                              ┌───────────────────────┴────────────┐     │
│                              │                                    │     │
│                              ▼                                    ▼     │
│                     ┌────────────────┐                  ┌──────────────┐│
│                     │ Task in /Done/?│                  │ Max Iterations│
│                     │                │                  │ Reached?      │
│                     └───────┬────────┘                  └───────┬──────┘│
│                             │                                   │       │
│              ┌──────────────┴──────────────┐                   │       │
│              │                             │                   │       │
│              ▼                             ▼                   ▼       │
│     ┌────────────┐               ┌────────────┐      ┌──────────────┐  │
│     │    YES     │               │     NO     │      │ Force Exit   │  │
│     │ Exit OK    │               │ Re-inject  │      │ Log Warning  │  │
│     │            │               │ Continue   │      │              │  │
│     └────────────┘               └─────┬──────┘      └──────────────┘  │
│                                        │                                │
│                                        ▼                                │
│                               ┌────────────────┐                        │
│                               │ Increment      │                        │
│                               │ Iteration      │                        │
│                               │ Update Task    │                        │
│                               └────────┬───────┘                        │
│                                        │                                │
│                                        ▼                                │
│                               ┌────────────────┐                        │
│                               │ Loop Back to   │                        │
│                               │ Claude Work    │                        │
│                               └────────────────┘                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Task File Format

Tasks are created in `/Active_Tasks/` with this YAML frontmatter:

```markdown
---
task_id: TASK_20240115_103000_abc123
prompt: Process all unread emails in Needs_Action folder
status: in_progress
iteration: 1
max_iterations: 10
completion_promise: TASK_COMPLETE
created: 2024-01-15T10:30:00
---

## Task Details

[Full task description here]

## Progress Log

### Iteration 1 - 2024-01-15 10:30:05
- Started processing emails
- Found 5 emails in Needs_Action

### Iteration 2 - 2024-01-15 10:30:45
- Processed 3 emails
- 2 remaining
```

## File Naming Convention

```
TASK_{timestamp}_{short_id}.md

Examples:
- TASK_20240115_103000_abc123.md
- TASK_20240115_143022_process_emails.md
```

## Components

### 1. ralph_wiggum.py

Main orchestrator script that:
- Creates task files in `/Active_Tasks/`
- Invokes Claude Code with the task
- Manages the iteration loop
- Handles completion detection

### 2. stop_hook.py

Stop hook script (`.claude/hooks/stop_hook.py`) that:
- Checks if task is complete (file moved to `/Done/`)
- Returns exit code to signal continuation or completion
- Logs each iteration

### 3. Task States

| State | Description |
|-------|-------------|
| `pending` | Task created, not started |
| `in_progress` | Claude actively working |
| `waiting_approval` | Paused for HITL approval |
| `completed` | Task finished successfully |
| `failed` | Task failed after max iterations |
| `cancelled` | Task manually cancelled |

## Usage

### Create and Run a Task

```bash
# Start autonomous task
python3 ralph_wiggum.py --task "Process all emails in Needs_Action"

# With custom max iterations
python3 ralph_wiggum.py --task "Generate weekly report" --max-iterations 5

# Demo mode
python3 ralph_wiggum.py --demo "Process all emails in Needs_Action"
```

### CLI Commands

```bash
# List active tasks
python3 ralph_wiggum.py --list

# Check task status
python3 ralph_wiggum.py --status TASK_20240115_103000_abc123

# Cancel a task
python3 ralph_wiggum.py --cancel TASK_20240115_103000_abc123

# View task log
python3 ralph_wiggum.py --log TASK_20240115_103000_abc123

# Resume a paused task
python3 ralph_wiggum.py --resume TASK_20240115_103000_abc123
```

## Stop Hook Configuration

The stop hook is configured in Claude Code settings:

```json
{
  "hooks": {
    "stop": ".claude/hooks/stop_hook.py"
  }
}
```

### Stop Hook Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Task complete | Exit Claude Code |
| 1 | Continue working | Re-inject prompt |
| 2 | Max iterations reached | Force exit with warning |
| 3 | Error occurred | Exit with error |

## Integration with HITL

When a task requires HITL approval:

1. Task status changes to `waiting_approval`
2. Approval request created in `/Pending_Approval/`
3. Stop hook detects and pauses iteration
4. After approval, task resumes automatically
5. Iteration continues from where it left off

## Logging

All iterations are logged to `/Logs/ralph_wiggum.log`:

```
2024-01-15 10:30:00 | INFO | Task TASK_abc123 started
2024-01-15 10:30:05 | INFO | Iteration 1: Working on task
2024-01-15 10:30:45 | INFO | Iteration 2: Continuing work
2024-01-15 10:31:20 | INFO | Task TASK_abc123 completed after 3 iterations
```

## Completion Detection

A task is considered complete when:

1. **File moved to /Done/**: Task file moved from `/Active_Tasks/` to `/Done/`
2. **Status updated**: Task status changed to `completed` in frontmatter
3. **Completion promise**: The string `TASK_COMPLETE` appears in the task file
4. **All subtasks done**: All checklist items marked as complete

## Error Handling

| Error | Response |
|-------|----------|
| Task file deleted | Log error, exit |
| Max iterations reached | Mark as failed, notify user |
| HITL timeout | Pause task, wait for approval |
| Claude error | Retry once, then fail |

## Security Considerations

1. **Iteration limit**: Always enforced to prevent infinite loops
2. **HITL integration**: Sensitive actions still require approval
3. **Logging**: All iterations logged for audit
4. **Cancellation**: Tasks can be cancelled at any time

## Best Practices

1. **Clear task descriptions**: Be specific about what needs to be done
2. **Reasonable iteration limits**: Default 10 is good for most tasks
3. **Monitor logs**: Check ralph_wiggum.log for progress
4. **Use completion promises**: Include `TASK_COMPLETE` when done

## File Structure

```
AI_Employee_Vault/
├── ralph_wiggum.py              # Main orchestrator
├── Active_Tasks/                 # Currently running tasks
│   └── TASK_*.md
├── Done/                         # Completed tasks
│   └── TASK_*.md
├── Logs/
│   └── ralph_wiggum.log         # Iteration logs
└── .claude/
    ├── hooks/
    │   └── stop_hook.py         # Stop hook script
    └── skills/
        └── ralph_wiggum/
            └── SKILL.md         # This file
```

## Example Task Flow

1. User: `python3 ralph_wiggum.py --task "Process 10 emails"`
2. Script creates `TASK_20240115_103000_emails.md` in `/Active_Tasks/`
3. Claude Code is invoked with task prompt
4. Claude processes 3 emails, stop hook triggers
5. Stop hook: Task not in /Done/? Continue. Iteration 2.
6. Claude processes 4 more emails, stop hook triggers
7. Stop hook: Task not in /Done/? Continue. Iteration 3.
8. Claude processes remaining 3 emails, marks task complete
9. Claude moves task file to `/Done/`
10. Stop hook: Task in /Done/? Exit successfully.
11. Total: 3 iterations, 10 emails processed

## Limitations

- Max 10 iterations by default (configurable)
- HITL actions pause the loop
- Requires Claude Code CLI
- Task files must follow exact format
