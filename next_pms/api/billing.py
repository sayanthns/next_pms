# apps/next_pms/next_pms/api/billing.py
"""Project expense & client-payment tracking (no accounting entries).

Expenses reduce a project's remaining budget. Client payments are tracked
separately (money-in) and can only be marked Received once an ERPNext Payment
Entry is linked. Manager/Admin only.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def _require_billing_manager():
    """Only PMS Manager / System Manager / Administrator may manage billing."""
    roles = set(frappe.get_roles(frappe.session.user))
    if not ({"System Manager", "Administrator", "PMS Manager"} & roles):
        frappe.throw(
            _("Only managers and administrators can manage project billing."),
            frappe.PermissionError,
        )


def _check_project(project):
    if not project or not frappe.db.exists("PMS Project", project):
        frappe.throw(_("Project not found"))


# ── Expenses ────────────────────────────────────────────────────────────────
@frappe.whitelist()
def add_project_expense(project, amount, expense_date=None, category=None, description=None, attachment=None):
    _require_billing_manager()
    _check_project(project)
    if flt(amount) <= 0:
        frappe.throw(_("Expense amount must be greater than zero."))
    doc = frappe.get_doc({
        "doctype": "PMS Project Expense",
        "project": project,
        "amount": flt(amount),
        "expense_date": getdate(expense_date) if expense_date else today(),
        "category": category or "Other",
        "description": description,
        "attachment": attachment,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def list_project_expenses(project):
    _check_project(project)
    return frappe.get_all(
        "PMS Project Expense",
        filters={"project": project},
        fields=["name", "amount", "expense_date", "category", "description", "attachment", "owner"],
        order_by="expense_date desc, creation desc",
    )


@frappe.whitelist()
def delete_project_expense(name):
    _require_billing_manager()
    if frappe.db.exists("PMS Project Expense", name):
        frappe.delete_doc("PMS Project Expense", name, ignore_permissions=True)
        frappe.db.commit()
    return {"success": True}


# ── Client payments ──────────────────────────────────────────────────────────
@frappe.whitelist()
def add_project_payment(project, amount, payment_date=None, description=None, payment_entry=None):
    _require_billing_manager()
    _check_project(project)
    if flt(amount) <= 0:
        frappe.throw(_("Payment amount must be greater than zero."))
    # If a Payment Entry is supplied up front, mark it Received immediately.
    status = "Received" if payment_entry else "Pending"
    doc = frappe.get_doc({
        "doctype": "PMS Project Payment",
        "project": project,
        "amount": flt(amount),
        "payment_date": getdate(payment_date) if payment_date else today(),
        "description": description,
        "payment_entry": payment_entry or None,
        "status": status,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": doc.name, "status": doc.status}


@frappe.whitelist()
def mark_payment_received(name, payment_entry):
    """Mark a tracked payment as Received — requires an ERPNext Payment Entry link."""
    _require_billing_manager()
    if not payment_entry:
        frappe.throw(_("A Payment Entry is required to mark this payment as Received."))
    if not frappe.db.exists("Payment Entry", payment_entry):
        frappe.throw(_("Payment Entry {0} not found.").format(payment_entry))
    doc = frappe.get_doc("PMS Project Payment", name)
    doc.payment_entry = payment_entry
    doc.status = "Received"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": doc.name, "status": doc.status, "received_on": str(doc.received_on or "")}


@frappe.whitelist()
def list_project_payments(project):
    _check_project(project)
    return frappe.get_all(
        "PMS Project Payment",
        filters={"project": project},
        fields=["name", "amount", "payment_date", "status", "payment_entry", "received_on", "description"],
        order_by="payment_date desc, creation desc",
    )


@frappe.whitelist()
def delete_project_payment(name):
    _require_billing_manager()
    if frappe.db.exists("PMS Project Payment", name):
        frappe.delete_doc("PMS Project Payment", name, ignore_permissions=True)
        frappe.db.commit()
    return {"success": True}


# ── Summary ──────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_project_billing_summary(project):
    _check_project(project)
    p = frappe.db.get_value(
        "PMS Project", project,
        ["total_budget", "calculated_cost", "total_expenses"],
        as_dict=True,
    ) or {}
    budget = flt(p.get("total_budget"))
    labour = flt(p.get("calculated_cost"))
    expenses = flt(p.get("total_expenses"))
    spent = labour + expenses

    pays = frappe.get_all(
        "PMS Project Payment",
        filters={"project": project},
        fields=["amount", "status"],
    )
    received = sum(flt(x.amount) for x in pays if x.status == "Received")
    pending = sum(flt(x.amount) for x in pays if x.status != "Received")

    return {
        "total_budget": budget,
        "labour_cost": labour,
        "expenses": expenses,
        "spent": spent,
        "remaining": budget - spent,
        "utilization_pct": round((spent / budget * 100), 1) if budget else 0,
        "payments_received": received,
        "payments_pending": pending,
        "payments_total": received + pending,
    }
