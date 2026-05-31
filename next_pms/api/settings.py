import frappe
from frappe.utils import flt

from next_pms.api.permissions import is_admin_user, get_user_permissions, get_current_user_feature_permissions


@frappe.whitelist()
def get_pms_settings():
    """Return system settings needed by the PMS frontend."""
    # Get default currency from company
    currency = "INR"
    try:
        company = frappe.db.get_single_value("Global Defaults", "default_company")
        if company:
            currency = (
                frappe.get_cached_value("Company", company, "default_currency")
                or "INR"
            )
    except Exception:
        pass

    # Get user roles relevant to PMS
    user_roles = frappe.get_roles()
    pms_roles = [
        r
        for r in user_roles
        if r.startswith("PMS") or r in ("System Manager", "Administrator")
    ]

    # Determine access level
    # Admin = System Manager or Administrator (full access to everything)
    is_admin = "System Manager" in user_roles or "Administrator" in user_roles
    # Manager = PMS Manager (project-scoped full access, NOT admin-level)
    is_manager = "PMS Manager" in user_roles
    is_developer = "PMS Developer" in user_roles
    is_customer = "PMS Customer" in user_roles and not (is_admin or is_manager or is_developer)

    # Get user's UI permissions
    perms = get_user_permissions(frappe.session.user)
    feature_perms = perms.get("feature_permissions", {})

    return {
        "currency": currency,
        "roles": pms_roles,
        "is_admin": is_admin,
        "is_manager": is_manager,
        "is_developer": is_developer,
        "is_customer": is_customer,
        "can_view_finance": is_admin or is_manager,
        "can_view_analytics": is_admin or is_manager,
        "can_create_project": (is_admin or is_manager) and feature_perms.get("create_project", True) is not False,
        "can_manage_team": is_admin or is_manager,
        "can_manage_users": is_admin,
        "sidebar_permissions": perms.get("sidebar_permissions", {}),
        "project_tab_permissions": perms.get("project_tab_permissions", {}),
        "feature_permissions": feature_perms,
    }


@frappe.whitelist()
def get_ai_settings():
    """Return AI settings for the admin frontend. Masks the API key."""
    if not is_admin_user():
        frappe.throw("Only administrators can view AI settings.", frappe.PermissionError)

    try:
        # Clear singleton cache to get fresh data
        frappe.clear_document_cache("PMS AI Settings", "PMS AI Settings")
        doc = frappe.get_doc("PMS AI Settings")
        has_key = bool(doc.ai_api_key)
        return {
            "ai_provider": doc.ai_provider or "Claude",
            "ai_api_key_set": has_key,
            "ai_model": doc.ai_model or "claude-sonnet-4-20250514",
            "daily_report_enabled": bool(doc.daily_report_enabled),
            "daily_report_recipient": doc.daily_report_recipient or "",
            "daily_report_recipients": getattr(doc, "daily_report_recipients", "") or "",
            "report_detail_level": getattr(doc, "report_detail_level", "Detailed") or "Detailed",
            "working_hours_per_day": flt(getattr(doc, "working_hours_per_day", 8)) or 8,
            "weekly_summary_recipient": getattr(doc, "weekly_summary_recipient", "") or "sayanth@enfono.in",
        }
    except Exception:
        return {
            "ai_provider": "Claude",
            "ai_api_key_set": False,
            "ai_model": "claude-sonnet-4-20250514",
            "daily_report_enabled": False,
            "daily_report_recipient": "",
            "daily_report_recipients": "",
            "report_detail_level": "Detailed",
            "working_hours_per_day": 8,
            "weekly_summary_recipient": "sayanth@enfono.in",
        }


@frappe.whitelist()
def save_ai_settings(provider=None, api_key=None, model=None, enabled=None,
                      recipient=None, additional_recipients=None, detail_level=None,
                      working_hours_per_day=None, weekly_summary_recipient=None):
    """Save AI settings. Admin only."""
    if not is_admin_user():
        frappe.throw("Only administrators can modify AI settings.", frappe.PermissionError)

    frappe.clear_document_cache("PMS AI Settings", "PMS AI Settings")
    doc = frappe.get_doc("PMS AI Settings")

    if provider is not None:
        doc.ai_provider = provider

    if api_key is not None and api_key != "":
        doc.ai_api_key = api_key

    if model is not None:
        doc.ai_model = model

    if enabled is not None:
        doc.daily_report_enabled = 1 if str(enabled).lower() in ("true", "1", "yes") else 0

    if recipient is not None:
        doc.daily_report_recipient = recipient

    if additional_recipients is not None:
        if hasattr(doc, "daily_report_recipients"):
            doc.daily_report_recipients = additional_recipients

    if detail_level is not None:
        if hasattr(doc, "report_detail_level"):
            doc.report_detail_level = detail_level

    if working_hours_per_day is not None and hasattr(doc, "working_hours_per_day"):
        doc.working_hours_per_day = flt(working_hours_per_day) or 8
    if weekly_summary_recipient is not None and hasattr(doc, "weekly_summary_recipient"):
        doc.weekly_summary_recipient = weekly_summary_recipient

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_document_cache("PMS AI Settings", "PMS AI Settings")

    return {"success": True, "message": "AI settings saved."}
