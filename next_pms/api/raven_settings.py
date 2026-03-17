import frappe


@frappe.whitelist()
def get_raven_integration_status():
    """Check if Raven is installed and available."""
    try:
        raven_installed = "raven" in frappe.get_installed_apps()
        return {"raven_enabled": raven_installed}
    except Exception:
        return {"raven_enabled": False}
