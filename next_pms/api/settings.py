import frappe

from next_pms.api.permissions import is_admin_user, get_user_permissions, get_current_user_feature_permissions


@frappe.whitelist()
def get_pms_settings():
    """Return system settings needed by the PMS frontend."""
    # Get default currency from company
    currency = "USD"
    try:
        company = frappe.db.get_single_value("Global Defaults", "default_company")
        if company:
            currency = (
                frappe.get_cached_value("Company", company, "default_currency")
                or "USD"
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
    is_customer = "PMS Customer" in user_roles

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
        doc = frappe.get_single("PMS AI Settings")
        has_key = bool(doc.ai_api_key)
        return {
            "ai_provider": doc.ai_provider or "OpenAI",
            "ai_api_key_set": has_key,
            "ai_model": doc.ai_model or "gpt-4o",
            "daily_report_enabled": bool(doc.daily_report_enabled),
            "daily_report_recipient": doc.daily_report_recipient or "",
        }
    except Exception:
        return {
            "ai_provider": "OpenAI",
            "ai_api_key_set": False,
            "ai_model": "gpt-4o",
            "daily_report_enabled": False,
            "daily_report_recipient": "",
        }


@frappe.whitelist()
def save_ai_settings(provider=None, api_key=None, model=None, enabled=None, recipient=None):
    """Save AI settings. Admin only."""
    if not is_admin_user():
        frappe.throw("Only administrators can modify AI settings.", frappe.PermissionError)

    doc = frappe.get_single("PMS AI Settings")

    if provider is not None:
        doc.ai_provider = provider

    if api_key is not None and api_key != "":
        doc.ai_api_key = api_key

    if model is not None:
        doc.ai_model = model

    if enabled is not None:
        doc.daily_report_enabled = 1 if enabled in (True, "true", "1", 1) else 0

    if recipient is not None:
        doc.daily_report_recipient = recipient

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "message": "AI settings saved."}
