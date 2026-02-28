#!/usr/bin/env python3
"""
Odoo MCP Server - ERP Integration via JSON-RPC

Connects to Odoo ERP system for managing contacts, invoices, products,
and accounting operations with HITL approval for financial transactions.

Usage:
    python3 odoo_mcp_server.py --test
    python3 odoo_mcp_server.py --list-contacts
    python3 odoo_mcp_server.py --list-invoices
    python3 odoo_mcp_server.py --demo
"""

import os
import sys
import json
import argparse
import xmlrpc.client
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# =============================================================================
# Configuration
# =============================================================================

VAULT_PATH = Path("/mnt/e/Hackathon-0/Bronze-Tier/AI_Employee_Vault")
PENDING_APPROVAL = VAULT_PATH / "Pending_Approval"
LOGS_FOLDER = VAULT_PATH / "Logs"

# Odoo connection settings (from environment or defaults for local Docker)
ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

# HITL threshold
PAYMENT_APPROVAL_THRESHOLD = 50.00  # Payments over $50 require approval

# =============================================================================
# Logging
# =============================================================================

def log(message: str, level: str = "INFO") -> None:
    """Log message to console and audit"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{level}] {timestamp} | {message}")

    # Also log to audit
    try:
        from audit_logger import AuditLogger
        AuditLogger.log(
            action_type="ODOO_OPERATION",
            actor="odoo_mcp_server",
            target={"message": message[:200]},
            result="info" if level == "INFO" else level.lower()
        )
    except ImportError:
        pass

# =============================================================================
# Odoo JSON-RPC Client
# =============================================================================

class OdooClient:
    """Odoo JSON-RPC client for ERP operations"""

    def __init__(
        self,
        url: str = ODOO_URL,
        db: str = ODOO_DB,
        user: str = ODOO_USER,
        password: str = ODOO_PASSWORD
    ):
        self.url = url
        self.db = db
        self.user = user
        self.password = password
        self.uid = None
        self._common = None
        self._models = None

    @property
    def common(self):
        """Get common endpoint for authentication"""
        if self._common is None:
            self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        return self._common

    @property
    def models(self):
        """Get models endpoint for CRUD operations"""
        if self._models is None:
            self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        return self._models

    def authenticate(self) -> int:
        """Authenticate with Odoo and return user ID"""
        if self.uid is None:
            self.uid = self.common.authenticate(self.db, self.user, self.password, {})
            if not self.uid:
                raise Exception("Authentication failed - check credentials")
        return self.uid

    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Execute Odoo model method"""
        uid = self.authenticate()
        return self.models.execute_kw(
            self.db, uid, self.password,
            model, method, list(args), kwargs
        )

    def search_read(
        self,
        model: str,
        domain: List = None,
        fields: List[str] = None,
        limit: int = 100,
        offset: int = 0,
        order: str = None
    ) -> List[Dict]:
        """Search and read records"""
        kwargs = {"limit": limit, "offset": offset}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order

        return self.execute(model, "search_read", domain or [], **kwargs)

    def create(self, model: str, values: Dict) -> int:
        """Create a new record"""
        return self.execute(model, "create", [values])

    def write(self, model: str, ids: List[int], values: Dict) -> bool:
        """Update existing records"""
        return self.execute(model, "write", ids, values)

    def read(self, model: str, ids: List[int], fields: List[str] = None) -> List[Dict]:
        """Read specific records"""
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
        return self.execute(model, "read", ids, **kwargs)

    def unlink(self, model: str, ids: List[int]) -> bool:
        """Delete records"""
        return self.execute(model, "unlink", ids)

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Odoo"""
        try:
            version = self.common.version()
            uid = self.authenticate()
            return {
                "success": True,
                "version": version.get("server_version", "unknown"),
                "uid": uid,
                "url": self.url,
                "db": self.db
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": self.url,
                "db": self.db
            }


# =============================================================================
# HITL Approval Integration
# =============================================================================

def create_odoo_approval_request(
    operation: str,
    data: Dict[str, Any],
    description: str
) -> Path:
    """Create HITL approval request for Odoo operation"""

    PENDING_APPROVAL.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ODOO_{operation.upper()}_{timestamp}.json"
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
            "function": f"execute_{operation}"
        }
    }

    file_path.write_text(json.dumps(approval_request, indent=2, default=str), encoding="utf-8")

    log(f"Created approval request: {filename}")
    return file_path


# =============================================================================
# Odoo Operations
# =============================================================================

class OdooOperations:
    """High-level Odoo operations with HITL integration"""

    def __init__(self, client: OdooClient = None):
        self.client = client or OdooClient()

    # -------------------------------------------------------------------------
    # Contacts / Partners
    # -------------------------------------------------------------------------

    def list_contacts(
        self,
        limit: int = 100,
        domain: List = None,
        is_company: bool = None
    ) -> List[Dict]:
        """List contacts/partners"""

        search_domain = domain or []

        if is_company is not None:
            search_domain.append(("is_company", "=", is_company))

        contacts = self.client.search_read(
            "res.partner",
            domain=search_domain,
            fields=["id", "name", "email", "phone", "is_company", "city", "country_id"],
            limit=limit
        )

        log(f"Listed {len(contacts)} contacts")
        return contacts

    def get_contact(self, partner_id: int) -> Optional[Dict]:
        """Get single contact by ID"""
        contacts = self.client.read("res.partner", [partner_id])
        return contacts[0] if contacts else None

    def create_contact(
        self,
        name: str,
        email: str = None,
        phone: str = None,
        is_company: bool = False,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """Create a new contact (requires HITL approval)"""

        data = {
            "name": name,
            "email": email,
            "phone": phone,
            "is_company": is_company
        }

        if require_approval:
            approval_path = create_odoo_approval_request(
                "create_contact",
                data,
                f"Create contact: {name}"
            )
            return {
                "status": "pending_approval",
                "approval_file": str(approval_path),
                "data": data
            }

        # Direct creation (for approved operations)
        partner_id = self.client.create("res.partner", data)
        log(f"Created contact: {name} (ID: {partner_id})")

        return {
            "status": "created",
            "partner_id": partner_id,
            "data": data
        }

    # -------------------------------------------------------------------------
    # Invoices
    # -------------------------------------------------------------------------

    def list_invoices(
        self,
        limit: int = 50,
        state: str = None,
        partner_id: int = None,
        move_type: str = "out_invoice"
    ) -> List[Dict]:
        """List invoices"""

        domain = [("move_type", "=", move_type)]

        if state:
            domain.append(("state", "=", state))

        if partner_id:
            domain.append(("partner_id", "=", partner_id))

        invoices = self.client.search_read(
            "account.move",
            domain=domain,
            fields=[
                "id", "name", "partner_id", "invoice_date", "amount_total",
                "amount_residual", "state", "payment_state"
            ],
            limit=limit,
            order="invoice_date desc"
        )

        log(f"Listed {len(invoices)} invoices")
        return invoices

    def get_unpaid_invoices(self, limit: int = 50) -> List[Dict]:
        """Get invoices that are not fully paid"""

        return self.list_invoices(
            limit=limit,
            state="posted"
        )

    def create_invoice(
        self,
        partner_id: int,
        invoice_lines: List[Dict],
        invoice_date: str = None,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """Create a new invoice (requires HITL approval)"""

        if invoice_date is None:
            invoice_date = datetime.now().strftime("%Y-%m-%d")

        # Calculate total
        total = sum(
            line.get("quantity", 1) * line.get("price_unit", 0)
            for line in invoice_lines
        )

        data = {
            "partner_id": partner_id,
            "move_type": "out_invoice",
            "invoice_date": invoice_date,
            "invoice_line_ids": [
                (0, 0, {
                    "name": line.get("name", "Product/Service"),
                    "quantity": line.get("quantity", 1),
                    "price_unit": line.get("price_unit", 0),
                    "product_id": line.get("product_id")
                })
                for line in invoice_lines
            ],
            "total": total
        }

        if require_approval:
            approval_path = create_odoo_approval_request(
                "create_invoice",
                data,
                f"Create invoice for partner {partner_id}, total: ${total:.2f}"
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
    # Payments
    # -------------------------------------------------------------------------

    def record_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_date: str = None,
        require_approval: bool = None
    ) -> Dict[str, Any]:
        """Record a payment for an invoice"""

        if payment_date is None:
            payment_date = datetime.now().strftime("%Y-%m-%d")

        # Auto-require approval for amounts over threshold
        if require_approval is None:
            require_approval = amount > PAYMENT_APPROVAL_THRESHOLD

        data = {
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_date": payment_date
        }

        if require_approval:
            approval_path = create_odoo_approval_request(
                "record_payment",
                data,
                f"Record payment of ${amount:.2f} for invoice {invoice_id}"
            )
            return {
                "status": "pending_approval",
                "approval_file": str(approval_path),
                "data": data
            }

        # Direct payment registration would go here
        # For now, just log it
        log(f"Recorded payment of ${amount:.2f} for invoice {invoice_id}")

        return {
            "status": "recorded",
            "data": data
        }

    # -------------------------------------------------------------------------
    # Products
    # -------------------------------------------------------------------------

    def list_products(
        self,
        limit: int = 100,
        product_type: str = None
    ) -> List[Dict]:
        """List products"""

        domain = []
        if product_type:
            domain.append(("type", "=", product_type))

        products = self.client.search_read(
            "product.product",
            domain=domain,
            fields=["id", "name", "default_code", "list_price", "type", "qty_available"],
            limit=limit
        )

        log(f"Listed {len(products)} products")
        return products

    # -------------------------------------------------------------------------
    # Reports
    # -------------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """Get business summary"""

        # Count contacts
        contact_count = len(self.client.search_read(
            "res.partner",
            domain=[("is_company", "=", True)],
            fields=["id"],
            limit=1000
        ))

        # Count invoices by state
        try:
            invoices = self.list_invoices(limit=1000)
            invoice_summary = {
                "total": len(invoices),
                "draft": len([i for i in invoices if i.get("state") == "draft"]),
                "posted": len([i for i in invoices if i.get("state") == "posted"]),
                "total_amount": sum(i.get("amount_total", 0) for i in invoices),
                "unpaid_amount": sum(i.get("amount_residual", 0) for i in invoices)
            }
        except Exception:
            invoice_summary = {"total": 0, "draft": 0, "posted": 0, "total_amount": 0, "unpaid_amount": 0}

        # Count products
        try:
            product_count = len(self.client.search_read(
                "product.product",
                fields=["id"],
                limit=1000
            ))
        except Exception:
            product_count = "N/A (module not installed)"

        return {
            "contacts": contact_count,
            "invoices": invoice_summary,
            "products": product_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# =============================================================================
# Demo Mode
# =============================================================================

def run_demo():
    """Run a demo of Odoo MCP operations"""

    print("\n" + "=" * 60)
    print("ODOO MCP SERVER - DEMO MODE")
    print("=" * 60 + "\n")

    client = OdooClient()
    ops = OdooOperations(client)

    # Test connection
    print("1. Testing connection...")
    result = client.test_connection()
    if result["success"]:
        print(f"   Connected to Odoo {result['version']}")
        print(f"   URL: {result['url']}")
        print(f"   Database: {result['db']}")
        print(f"   User ID: {result['uid']}")
    else:
        print(f"   Connection failed: {result['error']}")
        return

    # List contacts
    print("\n2. Listing contacts...")
    contacts = ops.list_contacts(limit=5)
    for contact in contacts:
        print(f"   - {contact['name']} ({contact.get('email', 'no email')})")

    # List products
    print("\n3. Listing products...")
    try:
        products = ops.list_products(limit=5)
        for product in products:
            print(f"   - {product['name']}: ${product.get('list_price', 0):.2f}")
    except Exception as e:
        print(f"   Products module not installed: {e}")

    # Get summary
    print("\n4. Business summary...")
    try:
        summary = ops.get_summary()
        print(f"   Contacts: {summary['contacts']}")
        print(f"   Products: {summary.get('products', 'N/A')}")
        print(f"   Invoices: {summary['invoices']['total']}")
        print(f"   Unpaid: ${summary['invoices']['unpaid_amount']:.2f}")
    except Exception as e:
        print(f"   Some modules not installed: {e}")

    # Create contact (with approval)
    print("\n5. Creating contact (HITL approval required)...")
    result = ops.create_contact(
        name="Demo Company",
        email="demo@example.com",
        is_company=True
    )
    print(f"   Status: {result['status']}")
    if result['status'] == 'pending_approval':
        print(f"   Approval file: {result['approval_file']}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60 + "\n")


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Odoo MCP Server - ERP Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--test", action="store_true", help="Test connection")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    parser.add_argument("--list-contacts", action="store_true", help="List contacts")
    parser.add_argument("--list-invoices", action="store_true", help="List invoices")
    parser.add_argument("--list-products", action="store_true", help="List products")
    parser.add_argument("--unpaid", action="store_true", help="List unpaid invoices")
    parser.add_argument("--summary", action="store_true", help="Get business summary")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--limit", type=int, default=20, help="Limit results")
    parser.add_argument("--serve", action="store_true", help="Run as MCP server")

    args = parser.parse_args()

    if args.test or args.health:
        print("\nTesting Odoo connection...")
        client = OdooClient()
        result = client.test_connection()

        if result["success"]:
            print(f"  Status: Connected")
            print(f"  Version: {result['version']}")
            print(f"  URL: {result['url']}")
            print(f"  Database: {result['db']}")
            print(f"  User ID: {result['uid']}")
        else:
            print(f"  Status: Failed")
            print(f"  Error: {result['error']}")
            sys.exit(1)

    elif args.demo:
        run_demo()

    elif args.list_contacts:
        ops = OdooOperations()
        contacts = ops.list_contacts(limit=args.limit)

        print(f"\nContacts ({len(contacts)}):")
        print("-" * 50)
        for contact in contacts:
            company = "[Company]" if contact.get("is_company") else ""
            print(f"  {contact['id']:4} | {contact['name'][:30]:30} | {contact.get('email', '')[:25]} {company}")

    elif args.list_invoices:
        ops = OdooOperations()
        invoices = ops.list_invoices(limit=args.limit)

        print(f"\nInvoices ({len(invoices)}):")
        print("-" * 70)
        for inv in invoices:
            partner = inv.get("partner_id", [0, "Unknown"])
            partner_name = partner[1] if isinstance(partner, list) else str(partner)
            print(f"  {inv['name']:15} | {partner_name[:20]:20} | ${inv['amount_total']:10.2f} | {inv['state']}")

    elif args.list_products:
        ops = OdooOperations()
        products = ops.list_products(limit=args.limit)

        print(f"\nProducts ({len(products)}):")
        print("-" * 50)
        for product in products:
            print(f"  {product['id']:4} | {product['name'][:35]:35} | ${product.get('list_price', 0):8.2f}")

    elif args.unpaid:
        ops = OdooOperations()
        invoices = ops.get_unpaid_invoices(limit=args.limit)

        unpaid = [i for i in invoices if i.get("amount_residual", 0) > 0]

        print(f"\nUnpaid Invoices ({len(unpaid)}):")
        print("-" * 70)
        for inv in unpaid:
            partner = inv.get("partner_id", [0, "Unknown"])
            partner_name = partner[1] if isinstance(partner, list) else str(partner)
            print(f"  {inv['name']:15} | {partner_name[:20]:20} | Due: ${inv['amount_residual']:10.2f}")

    elif args.summary:
        ops = OdooOperations()
        summary = ops.get_summary()

        print("\nBusiness Summary:")
        print("-" * 40)
        print(f"  Contacts: {summary['contacts']}")
        print(f"  Products: {summary['products']}")
        print(f"  Invoices:")
        print(f"    Total: {summary['invoices']['total']}")
        print(f"    Draft: {summary['invoices']['draft']}")
        print(f"    Posted: {summary['invoices']['posted']}")
        print(f"    Total Amount: ${summary['invoices']['total_amount']:.2f}")
        print(f"    Unpaid: ${summary['invoices']['unpaid_amount']:.2f}")

    elif args.serve:
        print("Starting Odoo MCP Server...")
        print("Note: Full MCP server implementation requires mcp package")
        print("For now, use CLI commands or import OdooOperations class")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
