import frappe
import os
import glob
import json

no_cache = 1


def get_context(context):
    csrf_token = frappe.sessions.get_csrf_token()
    context.csrf_token = csrf_token
    context.no_cache = 1
    context.show_sidebar = False
    context.full_width = True
    context.title = "Next PMS"

    # Check if user has access
    user_roles = frappe.get_roles()
    allowed_roles = ["PMS Manager", "PMS Developer", "PMS Viewer", "PMS Customer", "System Manager", "Administrator"]
    has_access = any(role in user_roles for role in allowed_roles)

    if not has_access and frappe.session.user != "Administrator":
        frappe.throw("You do not have permission to access Next PMS", frappe.PermissionError)

    # Boot data for the SPA
    context.boot_data = json.dumps({
        "user": frappe.session.user,
        "user_fullname": frappe.db.get_value("User", frappe.session.user, "full_name"),
        "roles": user_roles,
        "csrf_token": csrf_token,
    })

    # Find built frontend assets (hashed filenames)
    assets_path = os.path.join(
        frappe.get_app_path("next_pms"), "public", "frontend", "assets"
    )
    context.has_frontend = os.path.isdir(assets_path)

    if context.has_frontend:
        # Find the main JS and CSS files (largest ones are the app bundles)
        js_files = sorted(
            glob.glob(os.path.join(assets_path, "index-*.js")),
            key=os.path.getsize,
            reverse=True,
        )
        css_files = sorted(
            glob.glob(os.path.join(assets_path, "index-*.css")),
            key=os.path.getsize,
            reverse=True,
        )
        context.js_file = os.path.basename(js_files[0]) if js_files else ""
        context.css_file = os.path.basename(css_files[0]) if css_files else ""
        # Include smaller CSS too (component styles)
        context.css_files = [os.path.basename(f) for f in css_files]
