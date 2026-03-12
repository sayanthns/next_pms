import frappe


def after_install():
    create_roles()


def create_roles():
    roles = [
        {"role_name": "Next PMS", "desk_access": 1},
        {"role_name": "PMS Manager", "desk_access": 1},
        {"role_name": "PMS Developer", "desk_access": 1},
        {"role_name": "PMS Viewer", "desk_access": 1},
    ]
    for role_data in roles:
        if not frappe.db.exists("Role", role_data["role_name"]):
            role = frappe.new_doc("Role")
            role.role_name = role_data["role_name"]
            role.desk_access = role_data.get("desk_access", 1)
            role.insert(ignore_permissions=True)
            frappe.db.commit()
