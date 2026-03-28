import frappe


def is_admin_user():
    """Check if current user has system admin-level PMS access.
    Only System Manager and Administrator bypass all project filters.
    PMS Manager is NOT included — they only see their allocated projects.
    """
    admin_roles = {"System Manager", "Administrator"}
    user_roles = set(frappe.get_roles())
    return bool(admin_roles & user_roles)


def is_manager_user():
    """Check if current user is a PMS Manager (project-scoped full access)."""
    return "PMS Manager" in set(frappe.get_roles())


def get_user_projects():
    """Return list of project names user has access to.
    Returns None if user is admin (no filter needed).
    For PMS Manager: projects where user is PM, team member, OR project's
    department matches user's department.
    """
    if is_admin_user():
        return None

    user = frappe.session.user

    # Projects where user is the project manager
    manager_projects = frappe.get_all(
        "PMS Project",
        filters={"project_manager": user},
        pluck="name",
    )

    # Projects where user is a team member
    member_projects = frappe.db.get_all(
        "PMS Project Member",
        filters={"user": user},
        pluck="parent",
    )

    # For PMS Manager: also include projects matching their department
    dept_projects = []
    if is_manager_user():
        user_dept = frappe.db.get_value("User", user, "department")
        if user_dept:
            dept_projects = frappe.get_all(
                "PMS Project",
                filters={"department": user_dept},
                pluck="name",
            )

    allowed = list(set(manager_projects + member_projects + dept_projects))

    # Return a sentinel value if no projects found so filters don't return all
    return allowed if allowed else ["__none__"]


def check_project_access(project):
    """Raise PermissionError if user doesn't have access to the project."""
    allowed = get_user_projects()
    if allowed is None:
        return  # admin, allow all

    if project not in allowed:
        frappe.throw(
            "You do not have access to this project.",
            frappe.PermissionError,
        )


def project_query_conditions(user):
    """Permission query conditions for PMS Project list."""
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    roles = set(frappe.get_roles(user))
    if "System Manager" in roles:
        return ""

    escaped_user = frappe.db.escape(user)

    # Base conditions: PM or team member
    conditions = [
        f"`tabPMS Project`.project_manager = {escaped_user}",
        f"""`tabPMS Project`.name IN (
            SELECT parent FROM `tabPMS Project Member`
            WHERE user = {escaped_user}
        )""",
    ]

    # PMS Manager: also sees projects in their department
    if "PMS Manager" in roles:
        user_dept = frappe.db.get_value("User", user, "department")
        if user_dept:
            escaped_dept = frappe.db.escape(user_dept)
            conditions.append(
                f"`tabPMS Project`.department = {escaped_dept}"
            )
        # Also include projects with no department set
        conditions.append(
            "`tabPMS Project`.department IS NULL OR `tabPMS Project`.department = ''"
        )

    return "(" + " OR ".join(conditions) + ")"


def task_query_conditions(user):
    """Permission query conditions for PMS Task list."""
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    roles = set(frappe.get_roles(user))
    # Only System Manager bypasses all filters
    if "System Manager" in roles:
        return ""

    escaped_user = frappe.db.escape(user)
    return """(
        `tabPMS Task`.assigned_to = {user}
        OR `tabPMS Task`.name IN (
            SELECT parent FROM `tabPMS Task Assignee`
            WHERE user = {user}
        )
        OR `tabPMS Task`.project IN (
            SELECT name FROM `tabPMS Project`
            WHERE project_manager = {user}
        )
        OR `tabPMS Task`.project IN (
            SELECT parent FROM `tabPMS Project Member`
            WHERE user = {user}
        )
    )""".format(user=escaped_user)


def has_project_permission(doc, user=None, permission_type=None):
    """Has permission check for individual PMS Project document."""
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return True

    roles = set(frappe.get_roles(user))
    # Only System Manager gets blanket access
    if "System Manager" in roles:
        return True

    # Check if user is project manager
    if doc.project_manager == user:
        return True

    # Check if user is a team member
    for member in doc.team_members:
        if member.user == user:
            return True

    # Check PMS Customer role - customers can read their assigned projects
    if "PMS Customer" in roles and permission_type == "read":
        if doc.client and frappe.db.exists(
            "PMS Project Member", {"parent": doc.name, "user": user}
        ):
            return True

    return False


DEFAULT_SIDEBAR_PERMISSIONS = {
    "dashboard": True,
    "projects": True,
    "my_tasks": True,
    "settings": True,
    "timelogs": True,
    "reports": True,
}

DEFAULT_PROJECT_TAB_PERMISSIONS = {
    "overview": True,
    "tasks": True,
    "backlog": True,
    "team": True,
    "files": True,
    "timelogs": True,
    "analytics": True,
}

# Developer role gets restricted defaults
DEVELOPER_SIDEBAR_PERMISSIONS = {
    "dashboard": True,
    "projects": True,
    "my_tasks": True,
    "settings": False,
    "timelogs": True,
    "reports": False,
}

DEVELOPER_PROJECT_TAB_PERMISSIONS = {
    "overview": True,
    "tasks": True,
    "backlog": True,
    "team": False,
    "files": True,
    "timelogs": False,
    "analytics": False,
}

def get_current_user_feature_permissions():
    """Get feature permissions for the current session user.
    Returns a dict like {"view_all_timelogs": True/False, ...}.
    """
    import json

    user = frappe.session.user
    user_roles = set(frappe.get_roles(user))
    is_developer = "PMS Developer" in user_roles and not (
        {"System Manager", "Administrator", "PMS Manager"} & user_roles
    )
    default_features = DEVELOPER_FEATURE_PERMISSIONS if is_developer else DEFAULT_FEATURE_PERMISSIONS

    feature_raw = frappe.db.get_default("pms_feature_permissions", parent=user)
    try:
        return json.loads(feature_raw) if feature_raw else dict(default_features)
    except (json.JSONDecodeError, TypeError):
        return dict(default_features)


DEFAULT_FEATURE_PERMISSIONS = {
    "view_all_timelogs": True,
    "view_all_projects": True,
    "edit_project": True,
    "edit_task": True,
    "create_project": True,
    "create_task": True,
}

DEVELOPER_FEATURE_PERMISSIONS = {
    "view_all_timelogs": False,
    "view_all_projects": False,
    "edit_project": False,
    "edit_task": False,
    "create_project": False,
    "create_task": False,
}


@frappe.whitelist()
def get_user_permissions(user=None):
    """Get a user's PMS UI permissions (sidebar + project tabs).
    Admin can view any user; others can only view their own.
    """
    if not user:
        user = frappe.session.user

    if user != frappe.session.user and not is_admin_user():
        frappe.throw("Not permitted", frappe.PermissionError)

    import json

    # Determine role-appropriate defaults
    user_roles = set(frappe.get_roles(user))
    is_developer = "PMS Developer" in user_roles and not (
        {"System Manager", "Administrator", "PMS Manager"} & user_roles
    )

    default_sidebar = DEVELOPER_SIDEBAR_PERMISSIONS if is_developer else DEFAULT_SIDEBAR_PERMISSIONS
    default_tabs = DEVELOPER_PROJECT_TAB_PERMISSIONS if is_developer else DEFAULT_PROJECT_TAB_PERMISSIONS
    default_features = DEVELOPER_FEATURE_PERMISSIONS if is_developer else DEFAULT_FEATURE_PERMISSIONS

    sidebar_raw = frappe.db.get_default("pms_sidebar_permissions", parent=user)
    project_tab_raw = frappe.db.get_default("pms_project_tab_permissions", parent=user)
    feature_raw = frappe.db.get_default("pms_feature_permissions", parent=user)

    try:
        sidebar = json.loads(sidebar_raw) if sidebar_raw else dict(default_sidebar)
    except (json.JSONDecodeError, TypeError):
        sidebar = dict(default_sidebar)

    try:
        project_tabs = json.loads(project_tab_raw) if project_tab_raw else dict(default_tabs)
    except (json.JSONDecodeError, TypeError):
        project_tabs = dict(default_tabs)

    try:
        features = json.loads(feature_raw) if feature_raw else dict(default_features)
    except (json.JSONDecodeError, TypeError):
        features = dict(default_features)

    return {
        "sidebar_permissions": sidebar,
        "project_tab_permissions": project_tabs,
        "feature_permissions": features,
    }


@frappe.whitelist()
def save_user_permissions(user, sidebar_permissions=None, project_tab_permissions=None, feature_permissions=None):
    """Save a user's PMS UI permissions. Admin only."""
    if not is_admin_user():
        frappe.throw("Only administrators can manage permissions.", frappe.PermissionError)

    if not user or not frappe.db.exists("User", user):
        frappe.throw("Invalid user.")

    import json

    if sidebar_permissions is not None:
        if isinstance(sidebar_permissions, str):
            sidebar_permissions = json.loads(sidebar_permissions)
        frappe.db.set_default(
            "pms_sidebar_permissions",
            json.dumps(sidebar_permissions),
            parent=user,
        )

    if project_tab_permissions is not None:
        if isinstance(project_tab_permissions, str):
            project_tab_permissions = json.loads(project_tab_permissions)
        frappe.db.set_default(
            "pms_project_tab_permissions",
            json.dumps(project_tab_permissions),
            parent=user,
        )

    if feature_permissions is not None:
        if isinstance(feature_permissions, str):
            feature_permissions = json.loads(feature_permissions)
        frappe.db.set_default(
            "pms_feature_permissions",
            json.dumps(feature_permissions),
            parent=user,
        )

    frappe.db.commit()
    return {"success": True}


def has_task_permission(doc, user=None, permission_type=None):
    """Has permission check for individual PMS Task document."""
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return True

    roles = set(frappe.get_roles(user))
    # Only System Manager gets blanket access
    if "System Manager" in roles:
        return True

    # Check if user is assigned to task (legacy field)
    if doc.assigned_to == user:
        return True

    # Check if user is in assignees child table
    for assignee in doc.get("assignees", []):
        if assignee.user == user:
            return True

    # Check if user has access to the task's project
    if doc.project:
        try:
            project_doc = frappe.get_cached_doc("PMS Project", doc.project)
            if project_doc.project_manager == user:
                return True
            for member in project_doc.team_members:
                if member.user == user:
                    return True
        except frappe.DoesNotExistError:
            pass

    return False
