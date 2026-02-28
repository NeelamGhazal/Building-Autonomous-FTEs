# Odoo MCP Integration Skill

## Overview

MCP server for integrating with Odoo ERP via JSON-RPC API. Enables the AI Employee to manage invoices, contacts, and accounting operations with HITL approval for financial transactions.

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
│                         │  (for write    │                              │
│                         │   operations)  │                              │
│                         └────────────────┘                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## JSON-RPC API

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/web/session/authenticate` | Login and get session |
| `/web/dataset/call_kw` | Call model methods |
| `/web/webclient/version_info` | Get Odoo version |

### Request Format

```json
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "model": "res.partner",
        "method": "search_read",
        "args": [[]],
        "kwargs": {"fields": ["name", "email"]}
    },
    "id": null
}
```

## Features

### Read Operations (No Approval Required)
- List customers/partners
- Get invoices and their status
- Financial summary (paid/unpaid totals)

### Write Operations (HITL Required)
- Create invoices
- Create customers

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
ODOO_USER=admin
ODOO_PASSWORD=admin
```

## MCP Tools

### 1. get_customers

List all customers/partners.

```python
{
    "name": "get_customers",
    "description": "List customers from Odoo",
    "parameters": {
        "limit": {"type": "integer", "default": 100}
    }
}
```

**Returns:**
```json
[
    {"id": 10, "name": "Acme Corp", "email": "acme@example.com", "phone": "555-1234"},
    {"id": 14, "name": "Azure Interior", "email": "azure@example.com", "phone": "555-5678"}
]
```

### 2. create_customer

Create a new customer (requires HITL approval).

```python
{
    "name": "create_customer",
    "description": "Create customer in Odoo",
    "parameters": {
        "name": {"type": "string", "required": true},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "is_company": {"type": "boolean", "default": true}
    }
}
```

### 3. get_invoices

Get invoices with optional filters.

```python
{
    "name": "get_invoices",
    "description": "Get invoices from Odoo",
    "parameters": {
        "limit": {"type": "integer", "default": 50},
        "state": {"type": "string", "enum": ["draft", "posted", "cancel"]},
        "customer_id": {"type": "integer"}
    }
}
```

**Returns:**
```json
[
    {
        "id": 1,
        "name": "INV/2026/00001",
        "partner_name": "Acme Corp",
        "amount_total": 1500.00,
        "amount_residual": 1500.00,
        "state": "posted"
    }
]
```

### 4. create_invoice

Create a new invoice (requires HITL approval).

```python
{
    "name": "create_invoice",
    "description": "Create invoice in Odoo",
    "parameters": {
        "customer_id": {"type": "integer", "required": true},
        "lines": {
            "type": "array",
            "items": {
                "name": {"type": "string"},
                "quantity": {"type": "number"},
                "price_unit": {"type": "number"}
            }
        },
        "invoice_date": {"type": "string", "format": "date"}
    }
}
```

### 5. get_financial_summary

Get financial overview with totals.

```python
{
    "name": "get_financial_summary",
    "description": "Get financial summary from Odoo",
    "parameters": {}
}
```

**Returns:**
```json
{
    "total_invoiced": 143175.00,
    "total_paid": 0.00,
    "total_unpaid": 143175.00,
    "invoice_count": 4,
    "paid_count": 0,
    "unpaid_count": 4,
    "collection_rate": 0.0
}
```

## CLI Commands

```bash
# Test connection
python3 odoo_mcp_server.py --test

# List customers
python3 odoo_mcp_server.py --get-customers

# List invoices
python3 odoo_mcp_server.py --get-invoices

# Financial summary
python3 odoo_mcp_server.py --financial-summary

# Create customer (demo)
python3 odoo_mcp_server.py --create-customer "Test Company"
```

## HITL Integration

### Actions Requiring Approval

| Action | Condition | Approval Type |
|--------|-----------|---------------|
| Create Invoice | Always | Standard |
| Create Customer | Always | Standard |

### Approval File Format

```json
{
    "type": "ODOO_OPERATION",
    "operation": "create_invoice",
    "data": {
        "customer_id": 1,
        "lines": [
            {"name": "Service", "quantity": 1, "price_unit": 100.00}
        ]
    },
    "requires_approval": true,
    "created_at": "2026-02-28T10:30:00Z"
}
```

## Error Handling

### Connection Errors
- Automatic retry with exponential backoff
- Logs errors to `/Logs/odoo_mcp.log`

### Authentication Errors
- Re-authenticates on session expiry
- Logs authentication failures

## Security

1. **Credentials**: Use environment variables (never hardcode)
2. **HITL**: All write operations require approval
3. **Logging**: All operations logged
4. **Session**: Session cookies handled automatically

## File Structure

```
AI_Employee_Vault/
├── odoo_mcp_server.py        # MCP server implementation (JSON-RPC)
└── .claude/
    └── skills/
        └── odoo_mcp/
            └── SKILL.md      # This file
```

## Odoo Requirements

For full functionality, Odoo needs these modules:
- `base` - Base system (required)
- `account` - Accounting/Invoicing
- `contacts` - Contact management

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check Docker is running: `docker ps` |
| Authentication failed | Verify admin credentials |
| "Database not found" | Run `docker exec odoo-odoo-1 odoo -i base -d odoo --stop-after-init` |
| Module not found | Install required Odoo module |

## Demo Results (2026-02-28)

```
Connection Test: PASSED
- Version: 17.0-20260217
- User ID: 2

Customers: 2 found
- Acme Corporation
- Azure Interior

Invoices: 4 found
- Total: $143,175.00
- Unpaid: $143,175.00

Financial Summary:
- Collection Rate: 0%
```

---

*Last Updated: 2026-02-28*
*JSON-RPC Implementation Complete*
