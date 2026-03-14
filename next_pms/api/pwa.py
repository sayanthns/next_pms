import frappe
import os


@frappe.whitelist(allow_guest=True)
def sw():
    """Serve the PWA service worker with correct scope header.

    The SW file lives in public/js/sw.js but needs to control the /next-pms/ scope.
    Serving through this API endpoint lets us add the Service-Worker-Allowed header,
    which Nginx can't do for static /assets/ files without extra config.
    """
    sw_path = frappe.get_app_path("next_pms", "public", "js", "sw.js")

    if not os.path.exists(sw_path):
        frappe.throw("Service worker not found", frappe.DoesNotExistError)

    with open(sw_path, "r") as f:
        sw_content = f.read()

    frappe.local.response.update(
        {
            "type": "download",
            "filename": "sw.js",
            "filecontent": sw_content.encode("utf-8"),
            "content_type": "application/javascript",
            "display_content_as": "inline",
        }
    )
