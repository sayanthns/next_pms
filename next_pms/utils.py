import frappe


def add_sw_headers(response, **kwargs):
    """Add Service-Worker-Allowed header when serving the SW via API."""
    if frappe.request and "next_pms.api.pwa.sw" in (frappe.request.path or ""):
        response.headers["Service-Worker-Allowed"] = "/next-pms/"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def get_pms_url(doctype, name):
    """Return the Vue frontend URL for a PMS document.

    Maps PMS doctypes to their frontend routes under /next-pms/.
    Falls back to the standard Frappe form URL for unknown doctypes.
    """
    base = frappe.utils.get_url()

    route_map = {
        "PMS Task": f"/next-pms/task/{name}",
        "PMS Project": f"/next-pms/project/{name}",
    }

    path = route_map.get(doctype)
    if path:
        return f"{base}{path}"

    # Fallback for other doctypes
    return frappe.utils.get_url_to_form(doctype, name)
