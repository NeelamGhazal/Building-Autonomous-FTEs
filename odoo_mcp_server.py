#!/usr/bin/env python3
"""
Odoo MCP Server - ERP Integration via JSON-RPC

Connects to Odoo ERP system using JSON-RPC API for managing
customers, invoices, and financial operations.

JSON-RPC Endpoints:
- /web/session/authenticate - Login
- /web/dataset/call_kw - Model operations

Usage:
    python3 odoo_mcp_server.py --test
    python3 odoo_mcp_server.py --get-customers
    python3 odoo_mcp_server.py --get-invoices
    python3 odoo_mcp_server.py --financial-summary
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# =============================================================================
# Configuration
# =============================================================================

VAULT_PATH = Path("/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault")
PENDING_APPROVAL = VAULT_PATH / "Pending_Approval"
LOGS_FOLDER = VAULT_PATH / "Logs"

# Odoo connection settings
ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

# HITL threshold
PAYMENT_APPROVAL_THRESHOLD = 50.00

# =============================================================================
# Logging
# =============================================================================

def log(message: str, level: str = "INFO") -> None:
    """Log message to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{level}] {timestamp} | {message}")

# =============================================================================
# Odoo JSON-RPC Client
# =============================================================================

class OdooJSONRPC:
    """Odoo JSON-RPC client for ERP operations"""

    def __init__(
        self,
        url: str = ODOO_URL,
        db: str = ODOO_DB,
        username: str = ODOO_USER,
        password: str = ODOO_PASSWORD
    ):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.uid = None
        self.session_id = None

    def _jsonrpc(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """Make JSON-RPC call to Odoo"""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": None
        }

        headers = {"Content-Type": "application/json"}

        response = self.session.post(
            f"{self.url}{endpoint}",
            data=json.dumps(payload),
            headers=headers
        )

        result = response.json()

        if "error" in result:
            error = result["error"]
            message = error.get("data", {}).get("message", error.get("message", "Unknown error"))
            raise Exception(f"Odoo Error: {message}")

        return result.get("result")

    def authenticate(self) -> int:
        """Authenticate with Odoo via JSON-RPC"""
        if self.uid is not None:
            return self.uid

        result = self._jsonrpc("/web/session/authenticate", {
            "db": self.db,
            "login": self.username,
            "password": self.password
        })

        if not result or not result.get("uid"):
            raise Exception("Authentication failed - check credentials")

        self.uid = result["uid"]
        self.session_id = result.get("session_id")

        log(f"Authenticated as user ID: {self.uid}")
        return self.uid

    def call_kw(
        self,
        model: str,
        method: str,
        args: List = None,
        kwargs: Dict = None
    ) -> Any:
        """Call Odoo model method via JSON-RPC"""
        self.authenticate()

        return self._jsonrpc("/web/dataset/call_kw", {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {}
        })

    def search_read(
        self,
        model: str,
        domain: List = None,
        fields: List[str] = None,
        limit: int = 100,
        offset: int = 0,
        order: str = None
    ) -> List[Dict]:
        """Search and read records from Odoo"""
        kwargs = {"limit": limit, "offset": offset}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order

        return self.call_kw(
            model,
            "search_read",
            [domain or []],
            kwargs
        )

    def create(self, model: str, values: Dict) -> int:
        """Create a new record"""
        return self.call_kw(model, "create", [values])

    def write(self, model: str, ids: List[int], values: Dict) -> bool:
        """Update existing records"""
        return self.call_kw(model, "write", [ids, values])

    def read(self, model: str, ids: List[int], fields: List[str] = None) -> List[Dict]:
        """Read specific records"""
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
        return self.call_kw(model, "read", [ids], kwargs)

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Odoo"""
        try:
            # Get version info
            version_info = self._jsonrpc("/web/webclient/version_info", {})

            # Authenticate
            uid = self.authenticate()

            return {
                "success": True,
                "version": version_info.get("server_version", "unknown"),
                "uid": uid,
                "url": self.url,
                "db": self.db,
                "username": self.username
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": self.url,
                "db": self.db
            }


# =============================================================================
# MCP Tools Implementation
# =============================================================================

class OdooMCPTools:
    """MCP Tools for Odoo operations"""

    def __init__(self, client: OdooJSONRPC = None):
        self.client = client or OdooJSONRPC()

    # -------------------------------------------------------------------------
    # Tool: get_customers
    # -------------------------------------------------------------------------

    def get_customers(self, limit: int = 100) -> List[Dict]:
        """
        MCP Tool: Get all customers from Odoo

        Returns list of customers with their details.
        """
        customers = self.client.search_read(
            "res.partner",
            domain=[("customer_rank", ">", 0)],
            fields=["id", "name", "email", "phone", "city", "country_id", "customer_rank"],
            limit=limit,
            order="name asc"
        )

        # If no customers with customer_rank, get all partners
        if not customers:
            customers = self.client.search_read(
                "res.partner",
                domain=[("is_company", "=", True)],
                fields=["id", "name", "email", "phone", "city", "country_id"],
                limit=limit,
                order="name asc"
            )

        log(f"Retrieved {len(customers)} customers")
        return customers

    # -------------------------------------------------------------------------
    # Tool: create_customer
    # -------------------------------------------------------------------------

    def create_customer(
        self,
        name: str,
        email: str = None,
        phone: str = None,
        city: str = None,
        is_company: bool = True,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """
        MCP Tool: Add new customer to Odoo

        Creates a new customer record. Requires HITL approval.
        """
        data = {
            "name": name,
            "email": email,
            "phone": phone,
            "city": city,
            "is_company": is_company,
            "customer_rank": 1
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        if require_approval:
            approval_path = create_approval_request(
                "CREATE_CUSTOMER",
                data,
                f"Create customer: {name}"
            )
            return {
                "status": "pending_approval",
                "approval_file": str(approval_path),
                "data": data
            }

        # Direct creation
        customer_id = self.client.create("res.partner", data)
        log(f"Created customer: {name} (ID: {customer_id})")

        return {
            "status": "created",
            "customer_id": customer_id,
            "data": data
        }

    # -------------------------------------------------------------------------
    # Tool: get_invoices
    # -------------------------------------------------------------------------

    def get_invoices(
        self,
        limit: int = 50,
        state: str = None,
        customer_id: int = None
    ) -> List[Dict]:
        """
        MCP Tool: List all invoices with status

        Returns invoices with payment status.
        """
        domain = [("move_type", "=", "out_invoice")]

        if state:
            domain.append(("state", "=", state))

        if customer_id:
            domain.append(("partner_id", "=", customer_id))

        try:
            invoices = self.client.search_read(
                "account.move",
                domain=domain,
                fields=[
                    "id", "name", "partner_id", "invoice_date",
                    "amount_total", "amount_residual", "state", "payment_state"
                ],
                limit=limit,
                order="invoice_date desc"
            )

            # Format results
            formatted = []
            for inv in invoices:
                partner = inv.get("partner_id")
                partner_name = partner[1] if isinstance(partner, list) and len(partner) > 1 else "Unknown"

                formatted.append({
                    "id": inv["id"],
                    "number": inv["name"],
                    "customer": partner_name,
                    "date": inv.get("invoice_date"),
                    "total": inv.get("amount_total", 0),
                    "paid": inv.get("amount_total", 0) - inv.get("amount_residual", 0),
                    "due": inv.get("amount_residual", 0),
                    "state": inv.get("state"),
                    "payment_state": inv.get("payment_state")
                })

            log(f"Retrieved {len(formatted)} invoices")
            return formatted

        except Exception as e:
            log(f"Error getting invoices: {e}", "ERROR")
            return []

    # -------------------------------------------------------------------------
    # Tool: create_invoice
    # -------------------------------------------------------------------------

    def create_invoice(
        self,
        customer_id: int,
        lines: List[Dict],
        invoice_date: str = None,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """
        MCP Tool: Create new invoice for a customer

        Lines format: [{"name": "Service", "quantity": 1, "price_unit": 100.00}]
        Requires HITL approval.
        """
        if invoice_date is None:
            invoice_date = datetime.now().strftime("%Y-%m-%d")

        # Calculate total
        total = sum(
            line.get("quantity", 1) * line.get("price_unit", 0)
            for line in lines
        )

        data = {
            "partner_id": customer_id,
            "move_type": "out_invoice",
            "invoice_date": invoice_date,
            "invoice_line_ids": [
                (0, 0, {
                    "name": line.get("name", "Service"),
                    "quantity": line.get("quantity", 1),
                    "price_unit": line.get("price_unit", 0)
                })
                for line in lines
            ],
            "total": total
        }

        if require_approval:
            approval_path = create_approval_request(
                "CREATE_INVOICE",
                data,
                f"Create invoice for customer {customer_id}, total: ${total:.2f}"
            )
            return {
                "status": "pending_approval",
                "approval_file": str(approval_path),
                "total": total,
                "data": data
            }

        # Direct creation
        invoice_data = {k: v for k, v in data.items() if k != "total"}
        invoice_id = self.client.create("account.move", invoice_data)
        log(f"Created invoice {invoice_id} for ${total:.2f}")

        return {
            "status": "created",
            "invoice_id": invoice_id,
            "total": total
        }

    # -------------------------------------------------------------------------
    # Tool: get_financial_summary
    # -------------------------------------------------------------------------

    def get_financial_summary(self) -> Dict[str, Any]:
        """
        MCP Tool: Get total paid/unpaid amounts

        Returns financial summary including total invoiced,
        total paid, and total outstanding.
        """
        try:
            # Get all invoices
            invoices = self.client.search_read(
                "account.move",
                domain=[("move_type", "=", "out_invoice"), ("state", "=", "posted")],
                fields=["amount_total", "amount_residual", "payment_state"],
                limit=1000
            )

            total_invoiced = sum(inv.get("amount_total", 0) for inv in invoices)
            total_unpaid = sum(inv.get("amount_residual", 0) for inv in invoices)
            total_paid = total_invoiced - total_unpaid

            paid_count = len([inv for inv in invoices if inv.get("payment_state") == "paid"])
            partial_count = len([inv for inv in invoices if inv.get("payment_state") == "partial"])
            unpaid_count = len([inv for inv in invoices if inv.get("payment_state") == "not_paid"])

            summary = {
                "total_invoiced": round(total_invoiced, 2),
                "total_paid": round(total_paid, 2),
                "total_unpaid": round(total_unpaid, 2),
                "invoice_count": len(invoices),
                "paid_invoices": paid_count,
                "partial_invoices": partial_count,
                "unpaid_invoices": unpaid_count,
                "collection_rate": round((total_paid / total_invoiced * 100), 1) if total_invoiced > 0 else 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            log(f"Financial summary: ${total_paid:.2f} paid, ${total_unpaid:.2f} unpaid")
            return summary

        except Exception as e:
            log(f"Error getting financial summary: {e}", "ERROR")
            return {
                "total_invoiced": 0,
                "total_paid": 0,
                "total_unpaid": 0,
                "invoice_count": 0,
                "error": str(e)
            }


# =============================================================================
# HITL Approval
# =============================================================================

def create_approval_request(
    operation: str,
    data: Dict[str, Any],
    description: str
) -> Path:
    """Create HITL approval request for Odoo operation"""

    PENDING_APPROVAL.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ODOO_{operation}_{timestamp}.json"
    file_path = PENDING_APPROVAL / filename

    approval_request = {
        "type": "ODOO_OPERATION",
        "operation": operation,
        "description": description,
        "data": data,
        "requires_approval": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc).replace(hour=23, minute=59)).isoformat(),
        "callback": {
            "module": "odoo_mcp_server",
            "function": f"execute_{operation.lower()}"
        }
    }

    file_path.write_text(json.dumps(approval_request, indent=2, default=str), encoding="utf-8")

    log(f"Created approval request: {filename}")
    return file_path


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Odoo MCP Server - JSON-RPC ERP Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MCP Tools:
  get_customers         List all customers
  create_customer       Add new customer (requires HITL)
  get_invoices          List all invoices with status
  create_invoice        Create new invoice (requires HITL)
  get_financial_summary Total paid/unpaid amounts

Examples:
  python3 odoo_mcp_server.py --test
  python3 odoo_mcp_server.py --get-customers
  python3 odoo_mcp_server.py --get-invoices
  python3 odoo_mcp_server.py --financial-summary
        """
    )

    parser.add_argument("--test", action="store_true", help="Test connection to Odoo")
    parser.add_argument("--get-customers", action="store_true", help="List all customers")
    parser.add_argument("--get-invoices", action="store_true", help="List all invoices")
    parser.add_argument("--financial-summary", action="store_true", help="Get financial summary")
    parser.add_argument("--create-customer", type=str, metavar="NAME", help="Create customer")
    parser.add_argument("--email", type=str, help="Customer email (with --create-customer)")
    parser.add_argument("--limit", type=int, default=50, help="Limit results")

    args = parser.parse_args()

    # Initialize tools
    tools = OdooMCPTools()

    if args.test:
        print("\n" + "=" * 50)
        print("ODOO MCP SERVER - CONNECTION TEST")
        print("=" * 50)

        result = tools.client.test_connection()

        if result["success"]:
            print(f"\n  Status: CONNECTED")
            print(f"  Version: {result['version']}")
            print(f"  URL: {result['url']}")
            print(f"  Database: {result['db']}")
            print(f"  User: {result['username']}")
            print(f"  User ID: {result['uid']}")
            print("\n" + "=" * 50)
        else:
            print(f"\n  Status: FAILED")
            print(f"  Error: {result['error']}")
            print(f"  URL: {result['url']}")
            print("\n" + "=" * 50)
            sys.exit(1)

    elif args.get_customers:
        print("\n" + "=" * 60)
        print("CUSTOMERS")
        print("=" * 60)

        customers = tools.get_customers(limit=args.limit)

        if customers:
            print(f"\n{'ID':6} | {'Name':30} | {'Email':25} | {'Phone':15}")
            print("-" * 80)
            for c in customers:
                print(f"{c['id']:6} | {c['name'][:30]:30} | {(c.get('email') or '-')[:25]:25} | {(c.get('phone') or '-')[:15]}")
        else:
            print("\nNo customers found")

        print(f"\nTotal: {len(customers)} customers")

    elif args.get_invoices:
        print("\n" + "=" * 80)
        print("INVOICES")
        print("=" * 80)

        invoices = tools.get_invoices(limit=args.limit)

        if invoices:
            print(f"\n{'Number':15} | {'Customer':20} | {'Total':>12} | {'Paid':>12} | {'Due':>12} | {'State':10}")
            print("-" * 95)
            for inv in invoices:
                print(f"{inv['number']:15} | {inv['customer'][:20]:20} | ${inv['total']:>10.2f} | ${inv['paid']:>10.2f} | ${inv['due']:>10.2f} | {inv['state']:10}")
        else:
            print("\nNo invoices found (accounting module may not be installed)")

        print(f"\nTotal: {len(invoices)} invoices")

    elif args.financial_summary:
        print("\n" + "=" * 50)
        print("FINANCIAL SUMMARY")
        print("=" * 50)

        summary = tools.get_financial_summary()

        print(f"\n  Total Invoiced:    ${summary['total_invoiced']:>12,.2f}")
        print(f"  Total Paid:        ${summary['total_paid']:>12,.2f}")
        print(f"  Total Unpaid:      ${summary['total_unpaid']:>12,.2f}")
        print(f"\n  Invoice Count:     {summary['invoice_count']:>12}")
        print(f"  - Paid:            {summary.get('paid_invoices', 0):>12}")
        print(f"  - Partial:         {summary.get('partial_invoices', 0):>12}")
        print(f"  - Unpaid:          {summary.get('unpaid_invoices', 0):>12}")
        print(f"\n  Collection Rate:   {summary['collection_rate']:>11.1f}%")
        print("\n" + "=" * 50)

    elif args.create_customer:
        print(f"\nCreating customer: {args.create_customer}")

        result = tools.create_customer(
            name=args.create_customer,
            email=args.email
        )

        print(f"Status: {result['status']}")
        if result['status'] == 'pending_approval':
            print(f"Approval file: {result['approval_file']}")
        elif result['status'] == 'created':
            print(f"Customer ID: {result['customer_id']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
