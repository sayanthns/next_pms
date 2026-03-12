import frappe
from next_pms.api.permissions import is_admin_user


# Mapping from simple role keys to Frappe role names
PMS_ROLE_MAP = {
    "developer": "PMS Developer",
    "manager": "PMS Manager",
    "viewer": "PMS Viewer",
    "customer": "PMS Customer",
}

ALL_PMS_ROLES = {"Next PMS", "PMS Developer", "PMS Manager", "PMS Viewer", "PMS Customer"}
# The 4 specific PMS roles (excluding the base "Next PMS" role)
PMS_SPECIFIC_ROLES = {"PMS Developer", "PMS Manager", "PMS Viewer", "PMS Customer"}


@frappe.whitelist()
def get_pms_users():
    """Return all ERPNext users with their PMS access status and role.
    Admin-only endpoint.
    """
    if not is_admin_user():
        frappe.throw("Only administrators can manage users.", frappe.PermissionError)

    # Get all active users except system accounts
    users = frappe.get_all(
        "User",
        filters={
            "enabled": 1,
            "user_type": "System User",
            "name": ["not in", ["Administrator", "Guest"]],
        },
        fields=["name", "full_name", "email", "user_image", "last_active"],
        order_by="full_name asc",
        limit_page_length=0,
    )

    # For each user, determine their PMS role
    for user in users:
        user_roles = frappe.get_roles(user.name)
        user["has_pms_access"] = "Next PMS" in user_roles
        user["pms_role"] = ""
        # Find which PMS role they have (first match wins in priority order)
        for key, role_name in [
            ("manager", "PMS Manager"),
            ("developer", "PMS Developer"),
            ("viewer", "PMS Viewer"),
            ("customer", "PMS Customer"),
        ]:
            if role_name in user_roles:
                user["pms_role"] = key
                break

    return users


@frappe.whitelist()
def set_pms_role(user, role):
    """Set a user's PMS role. Removes all existing PMS roles and adds the new one.
    Admin-only endpoint.
    """
    if not is_admin_user():
        frappe.throw("Only administrators can manage user roles.", frappe.PermissionError)

    if not user or not frappe.db.exists("User", user):
        frappe.throw("Invalid user.")

    role_name = PMS_ROLE_MAP.get(role)
    if not role_name:
        frappe.throw(f"Invalid role: {role}. Valid roles: {', '.join(PMS_ROLE_MAP.keys())}")

    user_doc = frappe.get_doc("User", user)

    # Remove specific PMS roles (keep "Next PMS" base role)
    user_doc.roles = [r for r in user_doc.roles if r.role not in PMS_SPECIFIC_ROLES]

    # Add the new role
    user_doc.append("roles", {"role": role_name})
    user_doc.save(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True, "user": user, "role": role}


@frappe.whitelist()
def toggle_pms_access(user, enable):
    """Enable or disable PMS access for a user.
    Enable: adds PMS Developer role (default starting role).
    Disable: removes all PMS roles.
    Admin-only endpoint.
    """
    if not is_admin_user():
        frappe.throw("Only administrators can manage user access.", frappe.PermissionError)

    if not user or not frappe.db.exists("User", user):
        frappe.throw("Invalid user.")

    # Handle string "true"/"false" from frontend
    if isinstance(enable, str):
        enable = enable.lower() in ("true", "1", "yes")

    user_doc = frappe.get_doc("User", user)

    if enable:
        # Check if user already has a PMS role
        current_roles = {r.role for r in user_doc.roles}
        has_pms_role = bool(ALL_PMS_ROLES & current_roles)

        if not has_pms_role:
            # Add "Next PMS" base role + "PMS Developer" as the default role
            user_doc.append("roles", {"role": "Next PMS"})
            user_doc.append("roles", {"role": "PMS Developer"})
            user_doc.save(ignore_permissions=True)
    else:
        # Remove all PMS roles
        user_doc.roles = [r for r in user_doc.roles if r.role not in ALL_PMS_ROLES]
        user_doc.save(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True, "user": user, "enabled": bool(enable)}
