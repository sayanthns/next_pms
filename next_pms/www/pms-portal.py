import frappe

no_cache = 1


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = False
    context.title = "Project Portal"
    context.csrf_token = frappe.sessions.get_csrf_token()
