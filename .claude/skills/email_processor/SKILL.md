# Email Processor Skill

## Purpose
Process incoming email files from /Needs_Action folder and create action plans.

## Trigger
When a new EMAIL_*.md file appears in /Needs_Action/

## Steps to Follow

### 1. Read the Email File
- Open the EMAIL_*.md file
- Extract: sender, subject, content

### 2. Analyze Priority
- URGENT if subject contains: urgent, asap, invoice, payment
- NORMAL for everything else

### 3. Create Plan File
Create a file in /Plans/ named PLAN_[timestamp].md with:
- Objective
- Suggested reply
- Action items with checkboxes

### 4. Update Dashboard
Update Dashboard.md Pending Tasks count and Needs Action section

### 5. Tag Original File
Add processed: true to the email file when done

## Plan File Format
---
created: TIMESTAMP
email_ref: FILENAME
priority: urgent or normal
status: pending
---

## Objective
What needs to be done

## Suggested Reply
Draft reply to sender

## Action Items
- [ ] Review email
- [ ] Send reply
- [ ] Archive original
