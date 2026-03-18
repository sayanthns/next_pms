import frappe
import json
from frappe.utils import now_datetime, getdate
from frappe import _


# ─────────────────────────────────────────────────────────────────────────────
# Token-based login for portal SPA (converts token → session)
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist(allow_guest=True)
def portal_token_login(token):
    """Validate portal access token and log the user in.
    Used by the Vue SPA to convert a token URL into a session.
    Returns user info on success.
    """
    if not token:
        frappe.throw(_("Access token is required"), frappe.AuthenticationError)

    access = frappe.get_all(
        "PMS Client Portal Access",
        filters={"access_token": token, "is_active": 1},
        fields=["name", "project", "client_email"],
        limit=1,
    )
    if not access:
        frappe.throw(_("Invalid or expired access token"), frappe.AuthenticationError)

    client_email = access[0].client_email

    # Check if user exists in Frappe
    if not frappe.db.exists("User", client_email):
        frappe.throw(_("User account not found. Please contact support."), frappe.AuthenticationError)

    # Log the user in
    frappe.local.login_manager.login_as(client_email)

    # Update last login on the access record
    frappe.db.set_value(
        "PMS Client Portal Access", access[0].name, "last_login", now_datetime()
    )
    frappe.db.commit()

    return {
        "user": client_email,
        "full_name": frappe.db.get_value("User", client_email, "full_name") or client_email,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Legacy token-based APIs (allow_guest, used by external/public portal links)
# ─────────────────────────────────────────────────────────────────────────────


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
def get_legacy_portal_task_detail(token, task):
    """Get detailed task information for the client portal view (legacy token-based).
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


# ─────────────────────────────────────────────────────────────────────────────
# Session-based APIs (for logged-in PMS Customer role users)
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_portal_projects():
    """Get projects accessible to the current customer user."""
    user = frappe.session.user

    # Find projects where this user has active client portal access
    access_records = frappe.get_all(
        "PMS Client Portal Access",
        filters={"client_email": user, "is_active": 1},
        pluck="project",
        ignore_permissions=True,
    )

    if not access_records:
        return []

    projects = frappe.get_all(
        "PMS Project",
        filters={"name": ["in", access_records]},
        fields=["name", "project_name", "status", "start_date", "end_date", "description"],
        ignore_permissions=True,
    )

    # Enrich with task stats for each project
    for p in projects:
        tasks = frappe.get_all("PMS Task", filters={"project": p.name}, fields=["status"], ignore_permissions=True)
        total = len(tasks)
        done = len([t for t in tasks if t.status == "Done"])
        p["total_tasks"] = total
        p["completed_tasks"] = done
        p["progress"] = round((done / total * 100) if total > 0 else 0)

        # Get team member names (no cost info)
        members = frappe.get_all(
            "PMS Project Member",
            filters={"parent": p.name},
            fields=["user"],
            ignore_permissions=True,
        )
        member_names = []
        for m in members:
            full_name = frappe.db.get_value("User", m.user, "full_name") or m.user
            member_names.append({"user": m.user, "full_name": full_name})
        p["team_members"] = member_names

        # Get next milestone
        next_sprint = frappe.get_all(
            "PMS Sprint",
            filters={"project": p.name, "status": ["in", ["Planned", "Active"]]},
            fields=["sprint_name", "end_date", "status"],
            order_by="end_date asc",
            limit=1,
            ignore_permissions=True,
        )
        p["next_milestone"] = next_sprint[0] if next_sprint else None

        # Count pending approvals (sprints ready for review)
        p["pending_approvals"] = frappe.db.count("PMS Sprint", {
            "project": p.name, "approval_status": "Ready for Review"
        })

        # Count open tickets
        p["open_tickets"] = frappe.db.count("PMS Task", {
            "project": p.name, "task_type": "Support Ticket",
            "status": ["not in", ["Done", "Cancelled"]]
        })

    return projects


@frappe.whitelist()
def get_portal_project_detail(project):
    """Get detailed project info for portal view."""
    user = frappe.session.user
    _verify_portal_access(user, project)

    p_data = frappe.db.get_value("PMS Project", project,
        ["name", "project_name", "status", "start_date", "end_date", "description"],
        as_dict=True)
    if not p_data:
        frappe.throw(_("Project not found."), frappe.DoesNotExistError)

    # Get milestones/sprints
    sprints = frappe.get_all(
        "PMS Sprint",
        filters={"project": project},
        fields=["name", "sprint_name", "status", "start_date", "end_date", "goal", "approval_status"],
        order_by="start_date asc",
        ignore_permissions=True,
    )

    # Enrich sprints with task counts
    for s in sprints:
        sprint_tasks = frappe.get_all("PMS Task", filters={"sprint": s.name}, fields=["status"], ignore_permissions=True)
        s["total_tasks"] = len(sprint_tasks)
        s["completed_tasks"] = len([t for t in sprint_tasks if t.status == "Done"])

    # Get all tasks (no cost fields, exclude support tickets)
    tasks = frappe.get_all(
        "PMS Task",
        filters={"project": project, "task_type": ["!=", "Support Ticket"]},
        fields=["name", "task_title", "status", "priority", "task_type", "sprint",
                "due_date", "description", "created_by_customer", "creation"],
        order_by="creation desc",
        ignore_permissions=True,
    )

    # Batch load assignee names
    task_names = [t.name for t in tasks]
    assignee_map = {}
    if task_names:
        all_assignees = frappe.get_all(
            "PMS Task Assignee",
            filters={"parent": ["in", task_names]},
            fields=["parent", "user"],
            ignore_permissions=True,
        )
        user_emails = set(a.user for a in all_assignees)
        user_name_map = {}
        if user_emails:
            users = frappe.get_all("User", filters={"name": ["in", list(user_emails)]}, fields=["name", "full_name"], ignore_permissions=True)
            user_name_map = {u.name: u.full_name or u.name for u in users}
        for a in all_assignees:
            assignee_map.setdefault(a.parent, []).append(user_name_map.get(a.user, a.user))

    for t in tasks:
        t["assignee_names"] = assignee_map.get(t.name, [])

    # Team members (no hourly rate)
    members = frappe.get_all(
        "PMS Project Member",
        filters={"parent": project},
        fields=["user"],
        ignore_permissions=True,
    )
    team = []
    for m in members:
        full_name = frappe.db.get_value("User", m.user, "full_name") or m.user
        team.append({"user": m.user, "full_name": full_name})

    # Files
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "PMS Project", "attached_to_name": project, "is_private": 0},
        fields=["name", "file_name", "file_url", "file_size", "creation"],
        order_by="creation desc",
        ignore_permissions=True,
    )

    # Links
    links = []
    try:
        links = frappe.get_all(
            "PMS Link Attachment",
            filters={"project": project},
            fields=["name", "url", "title", "creation"],
            order_by="creation desc",
            ignore_permissions=True,
        )
    except Exception:
        pass

    total_tasks = len(tasks)
    done_tasks = len([t for t in tasks if t["status"] == "Done"])

    return {
        "project": {
            "name": p_data.name,
            "project_name": p_data.project_name,
            "status": p_data.status,
            "start_date": str(p_data.start_date) if p_data.start_date else None,
            "end_date": str(p_data.end_date) if p_data.end_date else None,
            "description": p_data.description,
            "progress": round((done_tasks / total_tasks * 100) if total_tasks > 0 else 0),
            "total_tasks": total_tasks,
            "completed_tasks": done_tasks,
        },
        "milestones": sprints,
        "tasks": tasks,
        "team": team,
        "files": files,
        "links": links,
    }


@frappe.whitelist()
def get_portal_task_detail(task):
    """Get task detail for portal (no cost info). Uses get_all to avoid permission checks."""
    user = frappe.session.user

    # Fetch task data with ignore_permissions (we verify access below)
    task_data = frappe.get_all(
        "PMS Task",
        filters={"name": task},
        fields=["name", "task_title", "project", "sprint", "status", "priority",
                "task_type", "due_date", "description", "created_by_customer", "creation"],
        limit=1,
        ignore_permissions=True,
    )
    if not task_data:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)

    t = task_data[0]
    _verify_portal_access(user, t.project)

    # Get assignee names
    raw_assignees = frappe.get_all(
        "PMS Task Assignee",
        filters={"parent": task},
        fields=["user"],
        ignore_permissions=True,
    )
    assignees = []
    for a in raw_assignees:
        full_name = frappe.db.get_value("User", a.user, "full_name") or a.user
        assignees.append({"user": a.user, "full_name": full_name})

    # Get comments
    comments = frappe.get_all(
        "PMS Comment",
        filters={"task": task},
        fields=["name", "comment", "user", "mentions", "creation"],
        order_by="creation asc",
        ignore_permissions=True,
    )
    for c in comments:
        c["author_name"] = frappe.db.get_value("User", c.user, "full_name") or c.user
        c["content"] = c.pop("comment", "")
        c["author"] = c.pop("user", "")

    # Get attachments (files)
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "PMS Task", "attached_to_name": task, "is_private": 0},
        fields=["name", "file_name", "file_url", "file_size", "creation"],
        order_by="creation desc",
        ignore_permissions=True,
    )

    return {
        "task": {
            "name": t.name,
            "task_title": t.task_title,
            "project": t.project,
            "sprint": t.sprint,
            "status": t.status,
            "priority": t.priority,
            "task_type": t.task_type,
            "due_date": str(t.due_date) if t.due_date else None,
            "description": t.description,
            "created_by_customer": t.get("created_by_customer", 0),
            "creation": str(t.creation),
        },
        "assignees": assignees,
        "comments": comments,
        "files": files,
    }


@frappe.whitelist()
def add_portal_comment(task, content):
    """Customer adds a comment on a task."""
    user = frappe.session.user
    project = frappe.db.get_value("PMS Task", task, "project")
    if not project:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)
    _verify_portal_access(user, project)

    doc = frappe.get_doc({
        "doctype": "PMS Comment",
        "task": task,
        "comment": content,
        "user": user,
    })
    doc.insert(ignore_permissions=True)

    author_name = frappe.db.get_value("User", user, "full_name") or user
    return {
        "name": doc.name,
        "content": doc.comment,
        "author": doc.user,
        "author_name": author_name,
        "creation": str(doc.creation),
    }


@frappe.whitelist()
def create_support_ticket(project, title, description, priority="Medium"):
    """Customer creates a support ticket (PMS Task with type Support Ticket)."""
    user = frappe.session.user
    _verify_portal_access(user, project)

    doc = frappe.get_doc({
        "doctype": "PMS Task",
        "task_title": title,
        "project": project,
        "task_type": "Support Ticket",
        "priority": priority,
        "status": "To Do",
        "description": description,
        "created_by_customer": 1,
    })
    doc.insert(ignore_permissions=True)

    return {
        "name": doc.name,
        "task_title": doc.task_title,
        "status": doc.status,
        "priority": doc.priority,
        "creation": str(doc.creation),
    }


@frappe.whitelist()
def upload_portal_attachment(task):
    """Upload a file attachment to a support ticket. Expects file in request."""
    user = frappe.session.user
    project = frappe.db.get_value("PMS Task", task, "project")
    if not project:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)
    _verify_portal_access(user, project)

    filedata = frappe.request.files.get("file")
    if not filedata:
        frappe.throw(_("No file uploaded."))

    from frappe.utils.file_manager import save_file
    file_doc = save_file(
        fname=filedata.filename,
        content=filedata.read(),
        dt="PMS Task",
        dn=task,
        is_private=0,
    )

    return {
        "name": file_doc.name,
        "file_name": file_doc.file_name,
        "file_url": file_doc.file_url,
    }


@frappe.whitelist()
def get_portal_tickets(project=None):
    """Get support tickets visible to the customer."""
    user = frappe.session.user

    # Get all accessible projects
    access_records = frappe.get_all(
        "PMS Client Portal Access",
        filters={"client_email": user, "is_active": 1},
        pluck="project",
        ignore_permissions=True,
    )
    if not access_records:
        return []

    filters = {
        "project": ["in", access_records],
        "task_type": "Support Ticket",
    }
    if project:
        _verify_portal_access(user, project)
        filters["project"] = project

    tickets = frappe.get_all(
        "PMS Task",
        filters=filters,
        fields=["name", "task_title", "project", "status", "priority", "creation", "modified"],
        order_by="creation desc",
        ignore_permissions=True,
    )

    # Enrich with project names and comment count
    project_name_map = {}
    for t in tickets:
        if t.project not in project_name_map:
            project_name_map[t.project] = frappe.db.get_value("PMS Project", t.project, "project_name") or t.project
        t["project_name"] = project_name_map[t.project]
        t["comment_count"] = frappe.db.count("PMS Comment", {"task": t.name})

    return tickets


@frappe.whitelist()
def approve_milestone(sprint, comment=None):
    """Customer approves a milestone/sprint."""
    user = frappe.session.user

    # Use db methods to avoid permission check, then verify portal access
    sprint_data = frappe.db.get_value(
        "PMS Sprint", sprint,
        ["name", "project", "sprint_name", "approval_status"],
        as_dict=True,
    )
    if not sprint_data:
        frappe.throw(_("Milestone not found."), frappe.DoesNotExistError)

    _verify_portal_access(user, sprint_data.project)

    if sprint_data.approval_status != "Ready for Review":
        frappe.throw("This milestone is not ready for review.")

    frappe.db.set_value("PMS Sprint", sprint, "approval_status", "Approved")
    frappe.db.commit()

    # Log the approval
    _log_approval(sprint, "PMS Sprint", "Approved", user, comment)

    # Notify team
    _notify_team_approval(sprint_data.project, sprint_data.sprint_name, "Approved", user, comment)

    return {"status": "Approved", "sprint": sprint}


@frappe.whitelist()
def request_milestone_changes(sprint, comment):
    """Customer requests changes on a milestone/sprint."""
    user = frappe.session.user

    sprint_data = frappe.db.get_value(
        "PMS Sprint", sprint,
        ["name", "project", "sprint_name", "approval_status"],
        as_dict=True,
    )
    if not sprint_data:
        frappe.throw(_("Milestone not found."), frappe.DoesNotExistError)

    _verify_portal_access(user, sprint_data.project)

    if sprint_data.approval_status != "Ready for Review":
        frappe.throw("This milestone is not ready for review.")

    frappe.db.set_value("PMS Sprint", sprint, {
        "approval_status": "Changes Requested",
        "status": "Active",
    })
    frappe.db.commit()

    _log_approval(sprint, "PMS Sprint", "Changes Requested", user, comment)
    _notify_team_approval(sprint_data.project, sprint_data.sprint_name, "Changes Requested", user, comment)

    return {"status": "Changes Requested", "sprint": sprint}


@frappe.whitelist()
def get_portal_stats():
    """Get dashboard stats for the portal."""
    user = frappe.session.user

    access_records = frappe.get_all(
        "PMS Client Portal Access",
        filters={"client_email": user, "is_active": 1},
        pluck="project",
        ignore_permissions=True,
    )
    if not access_records:
        return {"total_projects": 0, "pending_approvals": 0, "open_tickets": 0}

    pending_approvals = frappe.db.count("PMS Sprint", {
        "project": ["in", access_records],
        "approval_status": "Ready for Review"
    })

    open_tickets = frappe.db.count("PMS Task", {
        "project": ["in", access_records],
        "task_type": "Support Ticket",
        "status": ["not in", ["Done", "Cancelled"]]
    })

    return {
        "total_projects": len(access_records),
        "pending_approvals": pending_approvals,
        "open_tickets": open_tickets,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _verify_portal_access(user, project):
    """Verify the user has active portal access to the project."""
    has_access = frappe.db.exists("PMS Client Portal Access", {
        "client_email": user,
        "project": project,
        "is_active": 1
    })
    if not has_access:
        # Also allow admins and managers
        user_roles = set(frappe.get_roles(user))
        if not ({"System Manager", "Administrator", "PMS Manager"} & user_roles):
            frappe.throw("You do not have access to this project.", frappe.PermissionError)


def _log_approval(reference_name, reference_type, action, user, comment=None):
    """Log an approval action."""
    try:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": reference_type,
            "reference_name": reference_name,
            "content": f"<b>{action}</b> by {frappe.db.get_value('User', user, 'full_name') or user}" + (f": {comment}" if comment else ""),
            "comment_email": user,
        }).insert(ignore_permissions=True)
    except Exception:
        pass


def _notify_team_approval(project, milestone_name, action, user, comment=None):
    """Notify team members about milestone approval/rejection."""
    try:
        from next_pms.api.push import send_push_to_users

        members = frappe.get_all("PMS Project Member", filters={"parent": project}, pluck="user")
        client_name = frappe.db.get_value("User", user, "full_name") or user

        title = f"Milestone {action}: {milestone_name}"
        body = f"{client_name} {action.lower()} the milestone"
        if comment:
            body += f": {comment[:100]}"

        send_push_to_users(members, title, body, url=f"/next-pms/project/{project}")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# PMS-side Portal Management APIs (Admin/Manager only)
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_portal_access_list(project=None):
    """Get all client portal access records. Admin/Manager only."""
    _require_manager_or_admin()

    filters = {}
    if project:
        filters["project"] = project

    records = frappe.get_all(
        "PMS Client Portal Access",
        filters=filters,
        fields=["name", "project", "client_email", "is_active", "last_login", "access_token", "creation"],
        order_by="creation desc",
    )

    # Enrich with project names
    project_names = {}
    for r in records:
        if r.project not in project_names:
            project_names[r.project] = frappe.db.get_value("PMS Project", r.project, "project_name") or r.project
        r["project_name"] = project_names[r.project]
        # Mask token for display (show last 8 chars)
        if r.access_token:
            r["token_preview"] = "..." + r.access_token[-8:]
        else:
            r["token_preview"] = ""

    return records


@frappe.whitelist()
def get_customer_users():
    """Return all Frappe users who have the PMS Customer role. Admin/Manager only."""
    _require_manager_or_admin()

    customer_roles = frappe.get_all(
        "Has Role",
        filters={"role": "PMS Customer", "parenttype": "User"},
        fields=["parent"],
    )
    user_ids = list({r.parent for r in customer_roles})
    if not user_ids:
        return []

    users = frappe.get_all(
        "User",
        filters={"name": ["in", user_ids], "enabled": 1},
        fields=["name", "full_name", "email", "user_image"],
        order_by="full_name asc",
    )
    return users


@frappe.whitelist()
def get_portal_enabled_projects():
    """Return projects that have client_portal_enabled = 1. Admin/Manager only."""
    _require_manager_or_admin()

    projects = frappe.get_all(
        "PMS Project",
        filters={"client_portal_enabled": 1},
        fields=["name", "project_name", "status"],
        order_by="project_name asc",
    )
    return projects


@frappe.whitelist()
def invite_client(project, client_email=None, user=None):
    """Create a client portal access record and generate token. Admin/Manager only.
    Accepts either a Frappe user ID (preferred) or a client_email (legacy).
    """
    _require_manager_or_admin()

    # Resolve email from user ID if provided
    if user:
        if not frappe.db.exists("User", user):
            frappe.throw(_("User not found."))
        # Verify user has PMS Customer role
        has_role = frappe.db.exists("Has Role", {
            "parent": user, "role": "PMS Customer", "parenttype": "User"
        })
        if not has_role:
            frappe.throw(_("User does not have the PMS Customer role."))
        client_email = frappe.db.get_value("User", user, "email") or user

    if not project or not client_email:
        frappe.throw(_("Project and client user are required."))

    # Validate project exists
    if not frappe.db.exists("PMS Project", project):
        frappe.throw(_("Project not found."))

    # Check if access already exists
    existing = frappe.db.exists("PMS Client Portal Access", {
        "project": project,
        "client_email": client_email,
    })
    if existing:
        frappe.throw(_("This user already has access to this project."))

    # Generate unique access token
    import secrets
    token = secrets.token_urlsafe(32)

    doc = frappe.get_doc({
        "doctype": "PMS Client Portal Access",
        "project": project,
        "client_email": client_email,
        "access_token": token,
        "is_active": 1,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    # Send invitation email
    _send_portal_invitation_email(project, client_email, token)

    project_name = frappe.db.get_value("PMS Project", project, "project_name") or project

    return {
        "name": doc.name,
        "project": project,
        "project_name": project_name,
        "client_email": client_email,
        "access_token": token,
        "token_preview": "..." + token[-8:],
        "is_active": 1,
    }


@frappe.whitelist()
def revoke_portal_access(access_name):
    """Deactivate a client portal access record. Admin/Manager only."""
    _require_manager_or_admin()

    if not frappe.db.exists("PMS Client Portal Access", access_name):
        frappe.throw(_("Access record not found."))

    frappe.db.set_value("PMS Client Portal Access", access_name, "is_active", 0)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def reactivate_portal_access(access_name):
    """Reactivate a client portal access record. Admin/Manager only."""
    _require_manager_or_admin()

    if not frappe.db.exists("PMS Client Portal Access", access_name):
        frappe.throw(_("Access record not found."))

    frappe.db.set_value("PMS Client Portal Access", access_name, "is_active", 1)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def regenerate_portal_token(access_name):
    """Generate a new token for an existing portal access record. Admin/Manager only."""
    _require_manager_or_admin()

    doc = frappe.get_doc("PMS Client Portal Access", access_name)
    import secrets
    new_token = secrets.token_urlsafe(32)
    doc.access_token = new_token
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "access_token": new_token,
        "token_preview": "..." + new_token[-8:],
    }


@frappe.whitelist()
def delete_portal_access(access_name):
    """Permanently delete a portal access record. Admin/Manager only."""
    _require_manager_or_admin()

    if not frappe.db.exists("PMS Client Portal Access", access_name):
        frappe.throw(_("Access record not found."))

    frappe.delete_doc("PMS Client Portal Access", access_name, ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# Sprint Approval Management (PMS-side)
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def mark_sprint_ready_for_review(sprint):
    """Manager marks a sprint as ready for client review."""
    _require_manager_or_admin()

    doc = frappe.get_doc("PMS Sprint", sprint)
    if doc.approval_status == "Ready for Review":
        frappe.throw(_("This milestone is already marked for review."))

    doc.approval_status = "Ready for Review"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Notify clients who have portal access to this project
    _notify_clients_review_ready(doc.project, doc.sprint_name)

    return {"success": True, "approval_status": "Ready for Review"}


@frappe.whitelist()
def reset_sprint_approval(sprint):
    """Manager resets sprint approval back to Pending."""
    _require_manager_or_admin()

    doc = frappe.get_doc("PMS Sprint", sprint)
    doc.approval_status = "Pending"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "approval_status": "Pending"}


@frappe.whitelist()
def get_project_portal_summary(project):
    """Get portal-related summary for a project (for managers). Shows clients, tickets, approvals."""
    _require_manager_or_admin()

    # Client access records
    clients = frappe.get_all(
        "PMS Client Portal Access",
        filters={"project": project},
        fields=["name", "client_email", "is_active", "last_login"],
    )

    # Support tickets
    tickets = frappe.get_all(
        "PMS Task",
        filters={"project": project, "task_type": "Support Ticket"},
        fields=["name", "task_title", "status", "priority", "creation", "created_by_customer"],
        order_by="creation desc",
        limit=20,
    )

    # Sprints with approval status
    sprints = frappe.get_all(
        "PMS Sprint",
        filters={"project": project},
        fields=["name", "sprint_name", "status", "approval_status", "start_date", "end_date"],
        order_by="start_date asc",
    )

    return {
        "clients": clients,
        "tickets": tickets,
        "sprints": sprints,
        "active_clients": len([c for c in clients if c.is_active]),
        "open_tickets": len([t for t in tickets if t.status not in ("Done", "Cancelled")]),
        "pending_reviews": len([s for s in sprints if s.approval_status == "Ready for Review"]),
        "approved_milestones": len([s for s in sprints if s.approval_status == "Approved"]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Email notification helpers
# ─────────────────────────────────────────────────────────────────────────────


def _send_portal_invitation_email(project, client_email, token):
    """Send invitation email with portal access link."""
    try:
        project_name = frappe.db.get_value("PMS Project", project, "project_name") or project
        site_url = frappe.utils.get_url()
        portal_link = f"{site_url}/next-pms/portal"
        token_link = f"{site_url}/api/method/next_pms.api.portal.get_client_portal_data?token={token}"

        subject = f"You've been invited to the {project_name} project portal"
        message = f"""
        <h3>Welcome to the Project Portal</h3>
        <p>You have been granted access to view the <b>{project_name}</b> project.</p>
        <p>You can access the portal in two ways:</p>
        <ol>
            <li><b>Log in to the portal:</b> <a href="{portal_link}">{portal_link}</a></li>
            <li><b>Direct access link (no login required):</b> <a href="{token_link}">Click here</a></li>
        </ol>
        <p>If you have a login account, use the portal link. Otherwise, use the direct access link.</p>
        <p>Best regards,<br>Project Team</p>
        """

        frappe.sendmail(
            recipients=[client_email],
            subject=subject,
            message=message,
            now=True,
        )
    except Exception as e:
        frappe.log_error(f"Failed to send portal invitation email: {e}")


def _notify_clients_review_ready(project, sprint_name):
    """Notify all active portal clients that a milestone is ready for review."""
    try:
        clients = frappe.get_all(
            "PMS Client Portal Access",
            filters={"project": project, "is_active": 1},
            pluck="client_email",
        )
        if not clients:
            return

        project_name = frappe.db.get_value("PMS Project", project, "project_name") or project
        site_url = frappe.utils.get_url()
        portal_link = f"{site_url}/next-pms/portal/project/{project}"

        subject = f"Milestone Ready for Review: {sprint_name} - {project_name}"
        message = f"""
        <h3>Milestone Ready for Your Review</h3>
        <p>The milestone <b>{sprint_name}</b> in the <b>{project_name}</b> project is ready for your review.</p>
        <p>Please review the deliverables and approve or request changes:</p>
        <p><a href="{portal_link}">Open Project in Portal</a></p>
        <p>Best regards,<br>Project Team</p>
        """

        frappe.sendmail(
            recipients=clients,
            subject=subject,
            message=message,
            now=True,
        )
    except Exception as e:
        frappe.log_error(f"Failed to send review notification: {e}")


def _send_ticket_response_email(task_name, comment_content):
    """Notify client when their support ticket gets a response."""
    try:
        task = frappe.get_doc("PMS Task", task_name)
        if not task.created_by_customer:
            return

        # Find the client who created this ticket
        clients = frappe.get_all(
            "PMS Client Portal Access",
            filters={"project": task.project, "is_active": 1},
            pluck="client_email",
        )
        if not clients:
            return

        project_name = frappe.db.get_value("PMS Project", task.project, "project_name") or task.project
        site_url = frappe.utils.get_url()
        portal_link = f"{site_url}/next-pms/portal/project/{task.project}"

        subject = f"Response on your ticket: {task.task_title}"
        message = f"""
        <h3>Your Support Ticket Got a Response</h3>
        <p>There's a new response on your ticket <b>{task.task_title}</b> in the <b>{project_name}</b> project:</p>
        <blockquote style="border-left: 3px solid #2563eb; padding: 8px 16px; margin: 12px 0; color: #334155;">
            {comment_content[:500]}
        </blockquote>
        <p><a href="{portal_link}">View in Portal</a></p>
        """

        frappe.sendmail(
            recipients=clients,
            subject=subject,
            message=message,
            now=True,
        )
    except Exception as e:
        frappe.log_error(f"Failed to send ticket response email: {e}")


def _require_manager_or_admin():
    """Check that the current user is a PMS Manager or Admin."""
    user_roles = set(frappe.get_roles())
    if not ({"System Manager", "Administrator", "PMS Manager"} & user_roles):
        frappe.throw(_("Only managers and administrators can perform this action."), frappe.PermissionError)


# ─────────────────────────────────────────────────────────────────────────────
# Portal Analytics & Activity APIs (Admin/Manager only)
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_portal_project_report(period="weekly"):
    """Get project progress report for portal customers."""
    user = frappe.session.user

    # Get accessible projects
    access_records = frappe.get_all(
        "PMS Client Portal Access",
        filters={"client_email": user, "is_active": 1},
        fields=["project"],
        ignore_permissions=True,
    )
    project_ids = [a.project for a in access_records]
    if not project_ids:
        return {"projects": []}

    from frappe.utils import add_days, get_first_day, getdate
    today = getdate()
    if period == "weekly":
        # Monday of this week
        period_start = add_days(today, -today.weekday())
    else:
        period_start = get_first_day(today)

    results = []
    for pid in project_ids:
        p = frappe.db.get_value("PMS Project", pid, ["name", "project_name", "status"], as_dict=True)
        if not p:
            continue

        # All tasks (exclude support tickets)
        tasks = frappe.get_all(
            "PMS Task",
            filters={"project": pid, "task_type": ["!=", "Support Ticket"]},
            fields=["name", "status", "creation", "modified"],
            ignore_permissions=True,
        )

        total = len(tasks)
        completed = len([t for t in tasks if t.status == "Done"])
        in_progress = len([t for t in tasks if t.status in ("In Progress", "In Review")])
        open_tasks = total - completed - in_progress
        progress = round((completed / total * 100) if total else 0)

        # Period activity
        period_completed = len([t for t in tasks if t.status == "Done" and getdate(t.modified) >= period_start])
        period_created = len([t for t in tasks if getdate(t.creation) >= period_start])

        # Milestones
        sprints = frappe.get_all(
            "PMS Sprint",
            filters={"project": pid},
            fields=["name", "sprint_name", "status", "approval_status"],
            order_by="start_date asc",
            ignore_permissions=True,
        )
        for s in sprints:
            st = frappe.get_all("PMS Task", filters={"sprint": s.name, "task_type": ["!=", "Support Ticket"]}, fields=["status"], ignore_permissions=True)
            s_total = len(st)
            s_done = len([t for t in st if t.status == "Done"])
            s["progress"] = round((s_done / s_total * 100) if s_total else 0)

        results.append({
            "project": pid,
            "project_name": p.project_name,
            "status": p.status,
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress": in_progress,
            "open_tasks": open_tasks,
            "progress": progress,
            "period_completed": period_completed,
            "period_created": period_created,
            "milestones": sprints,
        })

    return {"projects": results}


@frappe.whitelist()
def get_all_support_tickets():
    """Get all support tickets across projects. Admin/Manager only."""
    _require_manager_or_admin()

    tickets = frappe.get_all(
        "PMS Task",
        filters={"task_type": "Support Ticket"},
        fields=["name", "task_title", "project", "status", "priority",
                "created_by_customer", "creation", "modified"],
        order_by="creation desc",
        ignore_permissions=True,
    )

    project_name_map = {}
    for t in tickets:
        if t.project not in project_name_map:
            project_name_map[t.project] = frappe.db.get_value("PMS Project", t.project, "project_name") or t.project
        t["project_name"] = project_name_map[t.project]
        t["comment_count"] = frappe.db.count("PMS Comment", {"task": t.name})
        t["customer_created"] = t.get("created_by_customer", 0)

    return tickets


@frappe.whitelist()
def get_portal_analytics():
    """Get comprehensive portal analytics for admin/manager dashboard."""
    _require_manager_or_admin()

    # Overall stats
    total_access = frappe.db.count("PMS Client Portal Access")
    active_access = frappe.db.count("PMS Client Portal Access", {"is_active": 1})
    revoked_access = total_access - active_access

    # Unique client emails
    unique_clients = len(set(
        frappe.get_all("PMS Client Portal Access", pluck="client_email")
    ))

    # Projects with portal
    projects_with_portal = len(set(
        frappe.get_all("PMS Client Portal Access", {"is_active": 1}, pluck="project")
    ))

    # Support tickets overview
    total_tickets = frappe.db.count("PMS Task", {"task_type": "Support Ticket"})
    open_tickets = frappe.db.count("PMS Task", {
        "task_type": "Support Ticket",
        "status": ["not in", ["Done", "Cancelled"]],
    })
    customer_created_tickets = frappe.db.count("PMS Task", {
        "task_type": "Support Ticket",
        "created_by_customer": 1,
    })

    # Milestone approval stats
    total_sprints_with_approval = frappe.db.count("PMS Sprint", {
        "approval_status": ["!=", "Pending"],
    })
    pending_reviews = frappe.db.count("PMS Sprint", {"approval_status": "Ready for Review"})
    approved_milestones = frappe.db.count("PMS Sprint", {"approval_status": "Approved"})
    changes_requested = frappe.db.count("PMS Sprint", {"approval_status": "Changes Requested"})

    # Recent portal logins (last 30 days)
    thirty_days_ago = frappe.utils.add_days(frappe.utils.getdate(), -30)
    recent_logins = frappe.get_all(
        "PMS Client Portal Access",
        filters={"last_login": [">=", thirty_days_ago], "is_active": 1},
        fields=["client_email", "project", "last_login"],
        order_by="last_login desc",
        limit=20,
    )
    for r in recent_logins:
        r["project_name"] = frappe.db.get_value("PMS Project", r.project, "project_name") or r.project

    # Tickets by priority (for chart)
    ticket_by_priority = {}
    for p in ["Low", "Medium", "High", "Critical"]:
        ticket_by_priority[p] = frappe.db.count("PMS Task", {
            "task_type": "Support Ticket",
            "priority": p,
            "status": ["not in", ["Done", "Cancelled"]],
        })

    # Recent tickets (last 10)
    recent_tickets = frappe.get_all(
        "PMS Task",
        filters={"task_type": "Support Ticket"},
        fields=["name", "task_title", "project", "status", "priority", "creation", "created_by_customer"],
        order_by="creation desc",
        limit=10,
    )
    for t in recent_tickets:
        t["project_name"] = frappe.db.get_value("PMS Project", t.project, "project_name") or t.project

    # Per-project portal summary
    portal_projects = frappe.get_all(
        "PMS Client Portal Access",
        filters={"is_active": 1},
        fields=["project"],
        group_by="project",
    )
    project_summaries = []
    for pp in portal_projects:
        proj = pp.project
        proj_name = frappe.db.get_value("PMS Project", proj, "project_name") or proj
        client_count = frappe.db.count("PMS Client Portal Access", {"project": proj, "is_active": 1})
        proj_open_tickets = frappe.db.count("PMS Task", {
            "project": proj, "task_type": "Support Ticket",
            "status": ["not in", ["Done", "Cancelled"]],
        })
        proj_pending_reviews = frappe.db.count("PMS Sprint", {
            "project": proj, "approval_status": "Ready for Review",
        })
        project_summaries.append({
            "project": proj,
            "project_name": proj_name,
            "active_clients": client_count,
            "open_tickets": proj_open_tickets,
            "pending_reviews": proj_pending_reviews,
        })

    return {
        "overview": {
            "total_access": total_access,
            "active_access": active_access,
            "revoked_access": revoked_access,
            "unique_clients": unique_clients,
            "projects_with_portal": projects_with_portal,
        },
        "tickets": {
            "total": total_tickets,
            "open": open_tickets,
            "customer_created": customer_created_tickets,
            "by_priority": ticket_by_priority,
        },
        "approvals": {
            "total_reviewed": total_sprints_with_approval,
            "pending_reviews": pending_reviews,
            "approved": approved_milestones,
            "changes_requested": changes_requested,
        },
        "recent_logins": recent_logins,
        "recent_tickets": recent_tickets,
        "project_summaries": project_summaries,
    }


@frappe.whitelist()
def get_portal_notifications():
    """Get notification indicators for the portal layout (for logged-in customers)."""
    user = frappe.session.user

    access_records = frappe.get_all(
        "PMS Client Portal Access",
        filters={"client_email": user, "is_active": 1},
        pluck="project",
        ignore_permissions=True,
    )
    if not access_records:
        return {"pending_approvals": 0, "unread_responses": 0, "total": 0}

    # Milestones ready for review
    pending_approvals = frappe.db.count("PMS Sprint", {
        "project": ["in", access_records],
        "approval_status": "Ready for Review",
    })

    # Support tickets with recent activity (modified in last 7 days, not by customer)
    seven_days_ago = frappe.utils.add_days(frappe.utils.getdate(), -7)
    recent_ticket_activity = frappe.db.count("PMS Task", {
        "project": ["in", access_records],
        "task_type": "Support Ticket",
        "created_by_customer": 1,
        "modified": [">=", seven_days_ago],
        "status": ["not in", ["Done", "Cancelled"]],
    })

    total = pending_approvals + recent_ticket_activity

    return {
        "pending_approvals": pending_approvals,
        "unread_responses": recent_ticket_activity,
        "total": total,
    }


def notify_client_on_ticket_response(task_name, comment_content, commenter):
    """Called from PMS Comment after_insert to notify clients about ticket responses.
    This is the wiring that connects the existing _send_ticket_response_email helper."""
    try:
        task = frappe.get_doc("PMS Task", task_name)
        # Only for Support Tickets created by customer
        if task.task_type != "Support Ticket" or not task.created_by_customer:
            return

        # Don't notify if the commenter is a client themselves
        user_roles = set(frappe.get_roles(commenter))
        if "PMS Customer" in user_roles and {"System Manager", "Administrator", "PMS Manager", "PMS Developer"} - user_roles == {"System Manager", "Administrator", "PMS Manager", "PMS Developer"}:
            return

        _send_ticket_response_email(task_name, comment_content)
    except Exception:
        frappe.log_error("PMS: Failed to notify client on ticket response")
