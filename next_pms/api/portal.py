import frappe
import json
from frappe.utils import now_datetime, getdate
from frappe import _


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
        pluck="project"
    )

    if not access_records:
        return []

    projects = frappe.get_all(
        "PMS Project",
        filters={"name": ["in", access_records]},
        fields=["name", "project_name", "status", "start_date", "end_date", "description"]
    )

    # Enrich with task stats for each project
    for p in projects:
        tasks = frappe.get_all("PMS Task", filters={"project": p.name}, fields=["status"])
        total = len(tasks)
        done = len([t for t in tasks if t.status == "Done"])
        p["total_tasks"] = total
        p["completed_tasks"] = done
        p["progress"] = round((done / total * 100) if total > 0 else 0)

        # Get team member names (no cost info)
        members = frappe.get_all(
            "PMS Project Member",
            filters={"parent": p.name},
            fields=["user"]
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
            limit=1
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

    p = frappe.get_doc("PMS Project", project)

    # Get milestones/sprints
    sprints = frappe.get_all(
        "PMS Sprint",
        filters={"project": project},
        fields=["name", "sprint_name", "status", "start_date", "end_date", "goal", "approval_status"],
        order_by="start_date asc"
    )

    # Enrich sprints with task counts
    for s in sprints:
        sprint_tasks = frappe.get_all("PMS Task", filters={"sprint": s.name}, fields=["status"])
        s["total_tasks"] = len(sprint_tasks)
        s["completed_tasks"] = len([t for t in sprint_tasks if t.status == "Done"])

    # Get all tasks (no cost fields)
    tasks = frappe.get_all(
        "PMS Task",
        filters={"project": project},
        fields=["name", "task_title", "status", "priority", "task_type", "sprint",
                "due_date", "description", "created_by_customer", "creation"],
        order_by="creation desc"
    )

    # Batch load assignee names
    task_names = [t.name for t in tasks]
    assignee_map = {}
    if task_names:
        all_assignees = frappe.get_all(
            "PMS Task Assignee",
            filters={"parent": ["in", task_names]},
            fields=["parent", "user"]
        )
        user_emails = set(a.user for a in all_assignees)
        user_name_map = {}
        if user_emails:
            users = frappe.get_all("User", filters={"name": ["in", list(user_emails)]}, fields=["name", "full_name"])
            user_name_map = {u.name: u.full_name or u.name for u in users}
        for a in all_assignees:
            assignee_map.setdefault(a.parent, []).append(user_name_map.get(a.user, a.user))

    for t in tasks:
        t["assignee_names"] = assignee_map.get(t.name, [])

    # Team members (no hourly rate)
    members = frappe.get_all(
        "PMS Project Member",
        filters={"parent": project},
        fields=["user"]
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
        order_by="creation desc"
    )

    # Links
    links = []
    try:
        links = frappe.get_all(
            "PMS Link Attachment",
            filters={"project": project},
            fields=["name", "url", "title", "creation"],
            order_by="creation desc"
        )
    except Exception:
        pass

    total_tasks = len(tasks)
    done_tasks = len([t for t in tasks if t["status"] == "Done"])

    return {
        "project": {
            "name": p.name,
            "project_name": p.project_name,
            "status": p.status,
            "start_date": str(p.start_date) if p.start_date else None,
            "end_date": str(p.end_date) if p.end_date else None,
            "description": p.description,
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
    """Get task detail for portal (no cost info)."""
    user = frappe.session.user

    t = frappe.get_doc("PMS Task", task)
    _verify_portal_access(user, t.project)

    # Get assignee names
    assignees = []
    for a in t.assignees:
        full_name = frappe.db.get_value("User", a.user, "full_name") or a.user
        assignees.append({"user": a.user, "full_name": full_name})

    # Get comments
    comments = frappe.get_all(
        "PMS Comment",
        filters={"task": task},
        fields=["name", "content", "author", "mentions", "creation"],
        order_by="creation asc"
    )
    for c in comments:
        c["author_name"] = frappe.db.get_value("User", c.author, "full_name") or c.author

    # Get attachments (files)
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "PMS Task", "attached_to_name": task, "is_private": 0},
        fields=["name", "file_name", "file_url", "file_size", "creation"],
        order_by="creation desc"
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
            "created_by_customer": t.created_by_customer if hasattr(t, 'created_by_customer') else 0,
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
    t = frappe.get_doc("PMS Task", task)
    _verify_portal_access(user, t.project)

    doc = frappe.get_doc({
        "doctype": "PMS Comment",
        "task": task,
        "content": content,
        "author": user,
    })
    doc.insert(ignore_permissions=True)

    author_name = frappe.db.get_value("User", user, "full_name") or user
    return {
        "name": doc.name,
        "content": doc.content,
        "author": doc.author,
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
def get_portal_tickets(project=None):
    """Get support tickets visible to the customer."""
    user = frappe.session.user

    # Get all accessible projects
    access_records = frappe.get_all(
        "PMS Client Portal Access",
        filters={"client_email": user, "is_active": 1},
        pluck="project"
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
        order_by="creation desc"
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
    sprint_doc = frappe.get_doc("PMS Sprint", sprint)
    _verify_portal_access(user, sprint_doc.project)

    if sprint_doc.approval_status != "Ready for Review":
        frappe.throw("This milestone is not ready for review.")

    sprint_doc.approval_status = "Approved"
    sprint_doc.save(ignore_permissions=True)

    # Log the approval
    _log_approval(sprint, "PMS Sprint", "Approved", user, comment)

    # Notify team
    _notify_team_approval(sprint_doc.project, sprint_doc.sprint_name, "Approved", user, comment)

    return {"status": "Approved", "sprint": sprint}


@frappe.whitelist()
def request_milestone_changes(sprint, comment):
    """Customer requests changes on a milestone/sprint."""
    user = frappe.session.user
    sprint_doc = frappe.get_doc("PMS Sprint", sprint)
    _verify_portal_access(user, sprint_doc.project)

    if sprint_doc.approval_status != "Ready for Review":
        frappe.throw("This milestone is not ready for review.")

    sprint_doc.approval_status = "Changes Requested"
    sprint_doc.status = "Active"  # Send back to active
    sprint_doc.save(ignore_permissions=True)

    _log_approval(sprint, "PMS Sprint", "Changes Requested", user, comment)
    _notify_team_approval(sprint_doc.project, sprint_doc.sprint_name, "Changes Requested", user, comment)

    return {"status": "Changes Requested", "sprint": sprint}


@frappe.whitelist()
def get_portal_stats():
    """Get dashboard stats for the portal."""
    user = frappe.session.user

    access_records = frappe.get_all(
        "PMS Client Portal Access",
        filters={"client_email": user, "is_active": 1},
        pluck="project"
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
