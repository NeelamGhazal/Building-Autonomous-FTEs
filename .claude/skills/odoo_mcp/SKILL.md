# Odoo MCP Integration Skill

## Overview

MCP server for integrating with Odoo ERP via JSON-RPC API. Enables the AI Employee to manage invoices, contacts, products, and accounting operations with HITL approval for financial transactions.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Odoo MCP Integration Flow                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────────┐  │
│  │  AI Employee   │────▶│  odoo_mcp      │────▶│  Odoo JSON-RPC     │  │
│  │  (Claude)      │     │  _server.py    │     │  API (8069)        │  │
│  └────────────────┘     └────────┬───────┘     └────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│                         ┌────────────────┐                              │
│                         │  HITL Approval │                              │
│                         │  (if payment   │                              │
│                         │   > $50)       │                              │
│                         └────────────────┘                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

### Read Operations (No Approval Required)
- List contacts/partners
- Get invoices and their status
- View products and inventory
- Read accounting entries
- Generate reports

### Write Operations (HITL Required)
- Create/update invoices
- Create/update contacts
- Record payments (> $50)
- Create journal entries
- Update product prices

## Configuration

### Environment Variables

```bash
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=admin
ODOO_PASSWORD=admin
```

### Docker Connection

```yaml
# Odoo running on Docker
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=odoo
ODOO_PASSWORD=odoo123
```

## MCP Tools

### 1. odoo_list_contacts

List all contacts/partners.

```python
{
    "name": "odoo_list_contacts",
    "description": "List contacts from Odoo",
    "parameters": {
        "limit": {"type": "integer", "default": 100},
        "domain": {"type": "array", "description": "Odoo domain filter"}
    }
}
```

### 2. odoo_get_invoices

Get invoices with optional filters.

```python
{
    "name": "odoo_get_invoices",
    "description": "Get invoices from Odoo",
    "parameters": {
        "state": {"type": "string", "enum": ["draft", "posted", "cancel"]},
        "partner_id": {"type": "integer"},
        "limit": {"type": "integer", "default": 50}
    }
}
```

### 3. odoo_create_invoice

Create a new invoice (requires HITL approval).

```python
{
    "name": "odoo_create_invoice",
    "description": "Create invoice in Odoo",
    "parameters": {
        "partner_id": {"type": "integer", "required": true},
        "invoice_lines": {"type": "array", "required": true},
        "invoice_date": {"type": "string", "format": "date"}
    }
}
```

### 4. odoo_record_payment

Record a payment (requires HITL approval if > $50).

```python
{
    "name": "odoo_record_payment",
    "description": "Record payment for invoice",
    "parameters": {
        "invoice_id": {"type": "integer", "required": true},
        "amount": {"type": "number", "required": true},
        "payment_date": {"type": "string", "format": "date"}
    }
}
```

### 5. odoo_get_products

Get products/services list.

```python
{
    "name": "odoo_get_products",
    "description": "List products from Odoo",
    "parameters": {
        "type": {"type": "string", "enum": ["product", "service", "consu"]},
        "limit": {"type": "integer", "default": 100}
    }
}
```

### 6. odoo_create_contact

Create a new contact (requires HITL approval).

```python
{
    "name": "odoo_create_contact",
    "description": "Create contact in Odoo",
    "parameters": {
        "name": {"type": "string", "required": true},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "is_company": {"type": "boolean", "default": false}
    }
}
```

## Usage

### CLI Commands

```bash
# Test connection
python3 odoo_mcp_server.py --test

# List contacts
python3 odoo_mcp_server.py --list-contacts

# List invoices
python3 odoo_mcp_server.py --list-invoices

# Get unpaid invoices
python3 odoo_mcp_server.py --unpaid

# Run as MCP server
python3 odoo_mcp_server.py --serve
```

### From Claude Code

```python
# List contacts
result = await mcp.call_tool("odoo_list_contacts", {"limit": 10})

# Get unpaid invoices
result = await mcp.call_tool("odoo_get_invoices", {"state": "posted"})

# Create invoice (triggers HITL)
result = await mcp.call_tool("odoo_create_invoice", {
    "partner_id": 1,
    "invoice_lines": [
        {"product_id": 1, "quantity": 1, "price_unit": 100.00}
    ]
})
```

## HITL Integration

### Actions Requiring Approval

| Action | Condition | Approval Type |
|--------|-----------|---------------|
| Create Invoice | Always | Standard |
| Record Payment | Amount > $50 | Financial |
| Create Contact | Always | Standard |
| Update Prices | Always | Financial |

### Approval File Format

```json
{
    "type": "ODOO_OPERATION",
    "operation": "create_invoice",
    "data": {
        "partner_id": 1,
        "total": 500.00,
        "lines": [...]
    },
    "requires_approval": true,
    "created_at": "2024-01-15T10:30:00Z"
}
```

## Error Handling

### Connection Errors
- Automatic retry with exponential backoff
- Queue operations when Odoo is down
- Alert after 5 failed attempts

### Authentication Errors
- Alert human for credential refresh
- Pause all Odoo operations

### Data Validation
- Validate invoice totals before submission
- Check partner existence before operations

## Security

1. **Credentials**: Never stored in vault (use environment variables)
2. **HITL**: All financial operations require approval
3. **Logging**: All operations logged to audit trail
4. **Limits**: Payment limits enforced ($50 default)

## File Structure

```
AI_Employee_Vault/
├── odoo_mcp_server.py        # MCP server implementation
└── .claude/
    └── skills/
        └── odoo_mcp/
            └── SKILL.md      # This file
```

## Odoo Modules Required

For full functionality, install these Odoo modules:
- `account` - Accounting
- `contacts` - Contact management
- `sale` - Sales
- `purchase` - Purchasing (optional)
- `stock` - Inventory (optional)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check Docker is running |
| Authentication failed | Verify credentials in .env |
| Module not found | Install required Odoo module |
| Permission denied | Check user has admin rights |

## Demo Commands

```bash
# Full demo flow
python3 odoo_mcp_server.py --demo

# Test specific operation
python3 odoo_mcp_server.py --test-create-contact "Test Company"

# Check Odoo health
python3 odoo_mcp_server.py --health
```
