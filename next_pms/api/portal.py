import frappe
from frappe.utils import now_datetime, getdate
from frappe import _


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_client_portal_data(token):
    """Validate token and return project summary for client portal.
    NO internal cost data is exposed.
    """
    if not token:
        frappe.throw(_("Access token is required"), frappe.AuthenticationError)

    # Rate limiting: max 60 requests per minute per token
    cache_key = f"portal_rate_{token}"
    request_count = frappe.cache().get_value(cache_key) or 0
    if request_count > 60:
        frappe.throw(_("Too many requests. Please try again later."), frappe.RateLimitExceededError)
    frappe.cache().set_value(cache_key, request_count + 1, expires_in_sec=60)

    # Validate token
    access = frappe.get_all(
        "PMS Client Portal Access",
        filters={"access_token": token, "is_active": 1},
        fields=["name", "project", "client_email"],
        limit=1,
    )

    if not access:
        frappe.throw(_("Invalid or expired access token"), frappe.AuthenticationError)

    access_doc = access[0]

    # Update last login
    frappe.db.set_value(
        "PMS Client Portal Access", access_doc.name, "last_login", now_datetime()
    )

    # Get project data (NO cost/budget info)
    project = frappe.get_doc("PMS Project", access_doc.project)

    # Task list (read-only, no cost data)
    tasks = frappe.get_all(
        "PMS Task",
        filters={"project": project.name},
        fields=[
            "name",
            "task_title",
            "status",
            "priority",
            "due_date",
            "assigned_to",
            "task_type",
            "start_date",
            "sprint",
        ],
        order_by="priority desc, due_date asc",
    )

    # Get full names for assigned users (not emails)
    for task in tasks:
        if task.assigned_to:
            task["assigned_to_name"] = frappe.db.get_value(
                "User", task.assigned_to, "full_name"
            ) or task.assigned_to

    # Task counts
    total_tasks = len(tasks)
    done_tasks = len([t for t in tasks if t.status == "Done"])
    progress = round((done_tasks / total_tasks * 100), 1) if total_tasks else 0

    # Sprint info
    sprints = frappe.get_all(
        "PMS Sprint",
        filters={"project": project.name},
        fields=["name", "sprint_name", "status", "start_date", "end_date"],
        order_by="start_date asc",
    )

    sprint_data = []
    for sprint in sprints:
        sprint_total = frappe.db.count("PMS Task", {"sprint": sprint.name})
        sprint_done = frappe.db.count(
            "PMS Task", {"sprint": sprint.name, "status": "Done"}
        )
        sprint_data.append(
            {
                "name": sprint.name,
                "sprint_name": sprint.sprint_name,
                "status": sprint.status,
                "start_date": str(sprint.start_date) if sprint.start_date else None,
                "end_date": str(sprint.end_date) if sprint.end_date else None,
                "total_tasks": sprint_total,
                "done_tasks": sprint_done,
                "progress": round((sprint_done / sprint_total * 100), 1) if sprint_total else 0,
            }
        )

    # Gantt data for portal (simplified)
    gantt_tasks = []
    for task in tasks:
        if task.start_date and task.due_date:
            gantt_tasks.append(
                {
                    "id": task.name,
                    "name": task.task_title,
                    "start": str(task.start_date),
                    "end": str(task.due_date),
                    "progress": 100 if task.status == "Done" else (50 if task.status == "In Progress" else 0),
                    "status": task.status,
                }
            )

    frappe.db.commit()

    return {
        "project_name": project.project_name,
        "status": project.status,
        "start_date": str(project.start_date) if project.start_date else None,
        "end_date": str(project.end_date) if project.end_date else None,
        "description": project.description,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "progress": progress,
        "tasks": tasks,
        "sprints": sprint_data,
        "gantt_tasks": gantt_tasks,
    }


@frappe.whitelist(allow_guest=True)
def post_client_comment(token, task, comment):
    """Allow client to post a comment on a task via portal."""
    if not token or not task or not comment:
        frappe.throw(_("Token, task, and comment are required"))

    # Validate token
    access = frappe.get_all(
        "PMS Client Portal Access",
        filters={"access_token": token, "is_active": 1},
        fields=["name", "project", "client_email"],
        limit=1,
    )

    if not access:
        frappe.throw(_("Invalid or expired access token"), frappe.AuthenticationError)

    access_doc = access[0]

    # Validate task belongs to the project
    task_project = frappe.db.get_value("PMS Task", task, "project")
    if task_project != access_doc.project:
        frappe.throw(_("Task does not belong to this project"), frappe.PermissionError)

    # Create comment
    comment_doc = frappe.new_doc("PMS Comment")
    comment_doc.task = task
    comment_doc.user = "Guest"
    comment_doc.comment = f"[Client: {access_doc.client_email}] {comment}"
    comment_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    # Notify project manager and task assignee
    task_doc = frappe.get_doc("PMS Task", task)
    project_manager = frappe.db.get_value(
        "PMS Project", access_doc.project, "project_manager"
    )

    notify_users = set()
    if project_manager:
        notify_users.add(project_manager)
    if task_doc.assigned_to:
        notify_users.add(task_doc.assigned_to)

    for user in notify_users:
        frappe.publish_realtime(
            "client_comment",
            {
                "task": task,
                "task_title": task_doc.task_title,
                "client_email": access_doc.client_email,
                "project": access_doc.project,
            },
            user=user,
        )

    return {"success": True, "comment": comment_doc.name}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_portal_task_detail(token, task):
    """Get detailed task information for the client portal view.
    NO internal cost data is exposed.
    """
    if not token or not task:
        frappe.throw(_("Token and task are required"))

    # Rate limiting
    cache_key = f"portal_rate_{token}"
    request_count = frappe.cache().get_value(cache_key) or 0
    if request_count > 60:
        frappe.throw(
            _("Too many requests. Please try again later."),
            frappe.RateLimitExceededError,
        )
    frappe.cache().set_value(cache_key, request_count + 1, expires_in_sec=60)

    # Validate token
    access = frappe.get_all(
        "PMS Client Portal Access",
        filters={"access_token": token, "is_active": 1},
        fields=["name", "project", "client_email"],
        limit=1,
    )

    if not access:
        frappe.throw(_("Invalid or expired access token"), frappe.AuthenticationError)

    access_doc = access[0]

    # Validate task belongs to the project
    task_project = frappe.db.get_value("PMS Task", task, "project")
    if task_project != access_doc.project:
        frappe.throw(_("Task does not belong to this project"), frappe.PermissionError)

    # Get task details (NO cost/budget fields)
    task_doc = frappe.get_doc("PMS Task", task)

    assigned_to_name = ""
    if task_doc.assigned_to:
        assigned_to_name = (
            frappe.db.get_value("User", task_doc.assigned_to, "full_name")
            or task_doc.assigned_to
        )

    # Get sprint name if linked
    sprint_name = ""
    if task_doc.sprint:
        sprint_name = (
            frappe.db.get_value("PMS Sprint", task_doc.sprint, "sprint_name") or ""
        )

    return {
        "name": task_doc.name,
        "task_title": task_doc.task_title,
        "status": task_doc.status,
        "priority": task_doc.priority,
        "task_type": task_doc.task_type,
        "assigned_to_name": assigned_to_name,
        "start_date": str(task_doc.start_date) if task_doc.start_date else None,
        "due_date": str(task_doc.due_date) if task_doc.due_date else None,
        "estimated_hours": task_doc.estimated_hours,
        "description": task_doc.description or "",
        "sprint": task_doc.sprint,
        "sprint_name": sprint_name,
    }


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_portal_comments(token, task):
    """Get all comments for a task visible in the client portal.
    NO internal cost data is exposed.
    """
    if not token or not task:
        frappe.throw(_("Token and task are required"))

    # Rate limiting
    cache_key = f"portal_rate_{token}"
    request_count = frappe.cache().get_value(cache_key) or 0
    if request_count > 60:
        frappe.throw(
            _("Too many requests. Please try again later."),
            frappe.RateLimitExceededError,
        )
    frappe.cache().set_value(cache_key, request_count + 1, expires_in_sec=60)

    # Validate token
    access = frappe.get_all(
        "PMS Client Portal Access",
        filters={"access_token": token, "is_active": 1},
        fields=["name", "project", "client_email"],
        limit=1,
    )

    if not access:
        frappe.throw(_("Invalid or expired access token"), frappe.AuthenticationError)

    access_doc = access[0]

    # Validate task belongs to the project
    task_project = frappe.db.get_value("PMS Task", task, "project")
    if task_project != access_doc.project:
        frappe.throw(_("Task does not belong to this project"), frappe.PermissionError)

    # Get comments for this task
    comments = frappe.get_all(
        "PMS Comment",
        filters={"task": task},
        fields=["name", "user", "comment", "creation"],
        order_by="creation asc",
    )

    # Enrich with user display names
    for comment in comments:
        if comment.user and comment.user != "Guest":
            comment["user_name"] = (
                frappe.db.get_value("User", comment.user, "full_name")
                or comment.user
            )
        elif comment.user == "Guest":
            # Extract client email from the comment prefix if present
            if comment.comment and comment.comment.startswith("[Client:"):
                try:
                    email_part = comment.comment.split("]")[0].replace("[Client: ", "")
                    comment["user_name"] = f"Client ({email_part})"
                except Exception:
                    comment["user_name"] = "Client"
            else:
                comment["user_name"] = "Client"
        else:
            comment["user_name"] = "Unknown"

    return comments
