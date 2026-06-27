import frappe
import json
import random
from frappe.utils import today, now_datetime, add_to_date, flt, cint

from next_pms.api.permissions import is_admin_user, get_current_user_feature_permissions

# OTP recipient for project deletion
PROJECT_DELETE_OTP_EMAIL = "sayanth@enfono.in"


def can_modify_document(doctype, name):
    """Check if current user can edit/delete a document.
    Admin, document owner, or project manager can modify.
    """
    if is_admin_user():
        return True

    user = frappe.session.user
    doc = frappe.get_doc(doctype, name)

    # Document owner can modify
    if doc.owner == user:
        return True

    # For tasks, the project manager can modify
    if doctype == "PMS Task" and doc.project:
        pm = frappe.db.get_value("PMS Project", doc.project, "project_manager")
        if pm == user:
            return True

    # For projects, the project manager can modify
    if doctype == "PMS Project" and doc.project_manager == user:
        return True

    # For time logs, the log owner (user field) can modify
    if doctype == "PMS Time Log" and doc.user == user:
        return True

    return False


@frappe.whitelist()
def get_delete_preview(doctype, name):
    """Preview what will be deleted in a cascade delete."""
    if doctype not in ("PMS Project", "PMS Task"):
        frappe.throw("Invalid doctype for delete preview.")

    if not can_modify_document(doctype, name):
        frappe.throw("You do not have permission to delete this document.", frappe.PermissionError)

    result = {"doctype": doctype, "name": name}

    if doctype == "PMS Project":
        tasks = frappe.get_all("PMS Task", filters={"project": name}, pluck="name")
        timelogs = 0
        comments = 0
        files_count = frappe.db.count("File", {"attached_to_doctype": "PMS Project", "attached_to_name": name})
        for t in tasks:
            timelogs += frappe.db.count("PMS Time Log", {"task": t})
            comments += frappe.db.count("PMS Comment", {"task": t})
            files_count += frappe.db.count("File", {"attached_to_doctype": "PMS Task", "attached_to_name": t})
        result["tasks"] = len(tasks)
        result["timelogs"] = timelogs
        result["comments"] = comments
        result["files"] = files_count

    elif doctype == "PMS Task":
        timelogs = frappe.db.count("PMS Time Log", {"task": name})
        comments = frappe.db.count("PMS Comment", {"task": name})
        files_count = frappe.db.count("File", {"attached_to_doctype": "PMS Task", "attached_to_name": name})
        result["timelogs"] = timelogs
        result["comments"] = comments
        result["files"] = files_count

    return result


@frappe.whitelist()
def request_project_delete_otp(project):
    """Generate a 6-digit OTP and email it for project deletion verification."""
    if not can_modify_document("PMS Project", project):
        frappe.throw("You do not have permission to delete this project.", frappe.PermissionError)

    otp = str(random.randint(100000, 999999))
    expires_at = add_to_date(now_datetime(), minutes=5)

    # Store OTP in cache with 5-minute TTL
    cache_key = f"pms_delete_otp:{project}:{frappe.session.user}"
    frappe.cache.set_value(cache_key, otp, expires_in_sec=300)

    project_name = frappe.db.get_value("PMS Project", project, "project_name") or project
    requester = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

    # Send OTP email
    frappe.sendmail(
        recipients=[PROJECT_DELETE_OTP_EMAIL],
        subject=f"OTP for Project Deletion: {project_name}",
        message=f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
            <h2 style="color: #dc2626; margin: 0 0 16px;">Project Deletion Request</h2>
            <p style="color: #374151; line-height: 1.6;">
                <strong>{requester}</strong> has requested to delete the project
                <strong>{project_name}</strong> ({project}).
            </p>
            <div style="background: #fef2f2; border: 2px solid #dc2626; border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0;">
                <p style="color: #991b1b; font-size: 14px; margin: 0 0 8px;">Your OTP Code</p>
                <p style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #dc2626; margin: 0;">{otp}</p>
            </div>
            <p style="color: #6b7280; font-size: 13px;">
                This OTP expires in <strong>5 minutes</strong>. This action will permanently delete the project and all associated tasks, time logs, comments, sprints, and files.
            </p>
        </div>
        """,
        now=True,
    )

    return {"success": True, "message": f"OTP sent to authorized email."}


@frappe.whitelist()
def delete_project(project, otp=None):
    """Cascade delete a project and all its children. Requires OTP verification."""
    if not can_modify_document("PMS Project", project):
        frappe.throw("You do not have permission to delete this project.", frappe.PermissionError)

    # Verify OTP
    if not otp:
        frappe.throw("OTP is required to delete a project.")

    cache_key = f"pms_delete_otp:{project}:{frappe.session.user}"
    stored_otp = frappe.cache.get_value(cache_key)

    if not stored_otp:
        frappe.throw("OTP has expired. Please request a new one.")

    if str(otp).strip() != str(stored_otp).strip():
        frappe.throw("Invalid OTP. Please try again.")

    # Clear OTP after successful verification
    frappe.cache.delete_value(cache_key)

    # Get all tasks in this project
    tasks = frappe.get_all("PMS Task", filters={"project": project}, pluck="name")

    # Delete timelogs, comments, files for each task, then the tasks
    for task_name in tasks:
        _delete_task_children(task_name)
        frappe.delete_doc("PMS Task", task_name, force=True, ignore_permissions=True)

    # Delete project files
    project_files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "PMS Project", "attached_to_name": project},
        pluck="name",
    )
    for f in project_files:
        frappe.delete_doc("File", f, force=True, ignore_permissions=True)

    # Delete sprints
    sprints = frappe.get_all("PMS Sprint", filters={"project": project}, pluck="name")
    for s in sprints:
        frappe.delete_doc("PMS Sprint", s, force=True, ignore_permissions=True)

    # Delete the project itself
    frappe.delete_doc("PMS Project", project, force=True, ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "message": f"Project {project} and all related data deleted."}


@frappe.whitelist()
def delete_task(task):
    """Cascade delete a task and all its children (timelogs, comments, files)."""
    if not can_modify_document("PMS Task", task):
        frappe.throw("You do not have permission to delete this task.", frappe.PermissionError)

    _delete_task_children(task)

    # Delete subtasks
    subtasks = frappe.get_all("PMS Task", filters={"parent_task": task}, pluck="name")
    for sub in subtasks:
        _delete_task_children(sub)
        frappe.delete_doc("PMS Task", sub, force=True, ignore_permissions=True)

    frappe.delete_doc("PMS Task", task, force=True, ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "message": f"Task {task} and all related data deleted."}


def _delete_task_children(task_name):
    """Delete timelogs, comments, and files belonging to a task."""
    # Delete timelogs
    timelogs = frappe.get_all("PMS Time Log", filters={"task": task_name}, pluck="name")
    for tl in timelogs:
        frappe.delete_doc("PMS Time Log", tl, force=True, ignore_permissions=True)

    # Delete comments
    comments = frappe.get_all("PMS Comment", filters={"task": task_name}, pluck="name")
    for c in comments:
        frappe.delete_doc("PMS Comment", c, force=True, ignore_permissions=True)

    # Delete files
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "PMS Task", "attached_to_name": task_name},
        pluck="name",
    )
    for f in files:
        frappe.delete_doc("File", f, force=True, ignore_permissions=True)


@frappe.whitelist()
def delete_timelog(timelog):
    """Delete a single time log. Admin or log owner can delete."""
    if not can_modify_document("PMS Time Log", timelog):
        frappe.throw("You do not have permission to delete this time log.", frappe.PermissionError)

    frappe.delete_doc("PMS Time Log", timelog, force=True, ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "message": f"Time log {timelog} deleted."}


@frappe.whitelist()
def update_project(project, fields, budget_otp=None, status_otp=None):
    """Update allowed project fields. Admin, owner, or PM can update.
    Raising total_budget requires an approver OTP unless the current user is a
    configured budget approver. Reopening a Completed project (status leaving
    'Completed') likewise needs an approver OTP for non-approvers."""
    if not can_modify_document("PMS Project", project):
        frappe.throw("You do not have permission to edit this project.", frappe.PermissionError)

    if isinstance(fields, str):
        fields = json.loads(fields)

    allowed_fields = {
        "project_name", "status", "start_date", "end_date",
        "total_budget", "description", "client", "client_portal_enabled",
        "department", "auto_send_report", "report_recipients", "sales_order",
    }

    doc = frappe.get_doc("PMS Project", project)

    # Budget-increase gate: a non-approver raising Total Budget must supply an OTP
    # that an approver received by email.
    if "total_budget" in fields:
        from next_pms.api.budget import is_budget_approver, verify_budget_otp

        old_budget = flt(doc.total_budget)
        new_budget = flt(fields.get("total_budget"))
        if new_budget > old_budget and not is_budget_approver():
            verify_budget_otp(project, budget_otp)

    # Reopen gate: leaving 'Completed' (reopen / move to Active etc.) needs an
    # approver OTP for non-approvers. On Hold and all other transitions are free.
    if "status" in fields:
        from next_pms.api.budget import is_budget_approver, verify_status_change_otp

        new_status = fields.get("status")
        if doc.status == "Completed" and new_status != "Completed" and not is_budget_approver():
            verify_status_change_otp(project, status_otp)

    for key, value in fields.items():
        if key in allowed_fields:
            doc.set(key, value)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "name": doc.name, "project_name": doc.project_name}


@frappe.whitelist()
def update_task_status(task, status):
    """Update task status using doc.save() to trigger hooks (notifications, etc.)."""
    valid_statuses = {"Backlog", "To Do", "In Progress", "In Review", "Done", "Cancelled"}
    if status not in valid_statuses:
        frappe.throw(f"Invalid status: {status}")

    doc = frappe.get_doc("PMS Task", task)

    # Permission check: admin, manager, owner, or assigned user
    user = frappe.session.user
    user_roles = set(frappe.get_roles(user))
    is_admin = bool({"System Manager", "Administrator"} & user_roles)
    is_manager = "PMS Manager" in user_roles
    is_assigned = doc.assigned_to == user or any(
        a.user == user for a in doc.get("assignees", [])
    )
    is_owner = doc.owner == user

    if not (is_admin or is_manager or is_assigned or is_owner):
        frappe.throw("You do not have permission to change this task's status.", frappe.PermissionError)

    doc.status = status
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "name": doc.name, "status": doc.status}


@frappe.whitelist()
def update_task(task, fields):
    """Update allowed task fields. Admin, owner, or PM/assignee can update."""
    if not can_modify_document("PMS Task", task):
        frappe.throw("You do not have permission to edit this task.", frappe.PermissionError)

    if isinstance(fields, str):
        fields = json.loads(fields)

    allowed_fields = {
        "task_title", "priority", "status", "due_date",
        "estimated_hours", "task_type", "description", "is_billable",
        "reviewer", "sprint",
    }

    doc = frappe.get_doc("PMS Task", task)
    for key, value in fields.items():
        if key in allowed_fields:
            doc.set(key, value)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "name": doc.name, "task_title": doc.task_title}


@frappe.whitelist()
def get_customers():
    """Return list of Customer names for dropdowns."""
    return frappe.get_all(
        "Customer",
        fields=["name", "customer_name"],
        order_by="customer_name asc",
        limit_page_length=0,
    )


@frappe.whitelist()
def get_project_members(project):
    """Return team members of a project for the assignee picker."""
    project_doc = frappe.get_doc("PMS Project", project)
    members = []
    for m in project_doc.team_members:
        user_doc = frappe.get_doc("User", m.user)
        members.append({
            "user": m.user,
            "full_name": user_doc.full_name or m.user,
            "role": m.role,
            "user_image": user_doc.user_image,
        })
    # Also include the project manager if not already in members
    pm = project_doc.project_manager
    if pm and not any(m["user"] == pm for m in members):
        pm_doc = frappe.get_doc("User", pm)
        members.insert(0, {
            "user": pm,
            "full_name": pm_doc.full_name or pm,
            "role": "Manager",
            "user_image": pm_doc.user_image,
        })
    return members


@frappe.whitelist()
def get_all_users():
    """Return only active users who have the 'Next PMS' role."""
    pms_user_emails = set(
        r.parent for r in frappe.get_all(
            "Has Role",
            filters={"role": "Next PMS", "parenttype": "User"},
            fields=["parent"],
            limit_page_length=0,
        )
    )
    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User", "name": ("in", list(pms_user_emails))},
        fields=["name", "full_name", "user_image"],
        order_by="full_name asc",
        limit_page_length=0,
    )
    return [u for u in users if u.name not in ("Administrator", "Guest")]


@frappe.whitelist()
def add_project_member(project, user, role=None, hourly_rate=None):
    """Add a team member to a project."""
    doc = frappe.get_doc("PMS Project", project)
    # Check if already a member
    for m in doc.team_members:
        if m.user == user:
            frappe.throw(f"{user} is already a member of this project.")

    # Use the user's global hourly rate if not explicitly provided
    if hourly_rate is None:
        rate = frappe.db.get_default("pms_hourly_rate", parent=user)
        hourly_rate = float(rate or 0)

    doc.append("team_members", {
        "user": user,
        "role": role or "Developer",
        "hourly_rate": hourly_rate,
    })
    doc.save()
    frappe.db.commit()

    # Send email notification to the added user
    try:
        from next_pms.utils import get_pms_url

        added_by_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
        project_name = doc.project_name
        project_url = get_pms_url("PMS Project", project)

        message = frappe.render_template(
            "next_pms/templates/emails/member_added.html",
            {
                "project_name": project_name,
                "role": role or "Developer",
                "added_by": added_by_name,
                "project_url": project_url,
            },
        )

        frappe.sendmail(
            recipients=[user],
            subject=f"You've been added to project: {project_name}",
            message=message,
            now=False,
        )

        # Create Notification Log
        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "for_user": user,
                "type": "Alert",
                "document_type": "PMS Project",
                "document_name": project,
                "subject": f"Added to project: {project_name}",
                "from_user": frappe.session.user,
            }
        ).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error("PMS: Failed to send member added notification")

    return {"success": True, "message": f"{user} added to project."}


@frappe.whitelist()
def remove_project_member(project, user):
    """Remove a team member from a project."""
    doc = frappe.get_doc("PMS Project", project)
    doc.team_members = [m for m in doc.team_members if m.user != user]
    doc.save()
    frappe.db.commit()
    return {"success": True, "message": f"{user} removed from project."}


@frappe.whitelist()
def update_project_member(project, user, role=None, hourly_rate=None):
    """Update a team member's role or hourly rate."""
    doc = frappe.get_doc("PMS Project", project)
    for m in doc.team_members:
        if m.user == user:
            if role is not None:
                m.role = role
            if hourly_rate is not None:
                m.hourly_rate = float(hourly_rate)
            break
    else:
        frappe.throw(f"{user} is not a member of this project.")
    doc.save()
    frappe.db.commit()
    return {"success": True, "message": f"{user} updated."}


@frappe.whitelist()
def create_project(
    project_name,
    client=None,
    status="Planning",
    start_date=None,
    end_date=None,
    description=None,
    total_budget=0,
    project_manager=None,
    department=None,
    sales_order=None,
    is_internal=0,
):
    """Create a new PMS Project and return its name.
    Internal projects (is_internal) skip client/sales-order/budget requirements."""
    feature_perms = get_current_user_feature_permissions()
    if feature_perms.get("create_project") is False:
        frappe.throw("You do not have permission to create projects.", frappe.PermissionError)

    doc = frappe.get_doc(
        {
            "doctype": "PMS Project",
            "project_name": project_name,
            "is_internal": cint(is_internal),
            "client": client or None,
            "status": status,
            "start_date": start_date or today(),
            "end_date": end_date,
            "description": description,
            "total_budget": total_budget or 0,
            "project_manager": project_manager or frappe.session.user,
            "department": department,
            "sales_order": sales_order or None,
        }
    )
    doc.insert()
    frappe.db.commit()

    return {
        "name": doc.name,
        "project_name": doc.project_name,
    }


@frappe.whitelist()
def create_task(
    project,
    task_title,
    priority="Medium",
    status="Backlog",
    assigned_to=None,
    assignees=None,
    sprint=None,
    estimated_hours=0,
    due_date=None,
    task_type=None,
    reviewer=None,
    start_date=None,
    description=None,
):
    """Create a new PMS Task in the given project with multiple assignees."""
    feature_perms = get_current_user_feature_permissions()
    if feature_perms.get("create_task") is False:
        frappe.throw("You do not have permission to create tasks.", frappe.PermissionError)

    task_data = {
        "doctype": "PMS Task",
        "project": project,
        "task_title": task_title,
        "priority": priority,
        "status": status,
        "sprint": sprint,
        "estimated_hours": estimated_hours or 0,
        "due_date": due_date,
        "task_type": task_type,
        "reviewer": reviewer,
        "start_date": start_date or (min(today(), due_date) if due_date else today()),
        "description": description or "",
        "assignees": [],
    }

    # Handle assignees - can be a JSON string or list
    assignee_list = []
    if assignees:
        if isinstance(assignees, str):
            try:
                assignee_list = json.loads(assignees)
            except (json.JSONDecodeError, ValueError):
                assignee_list = [assignees]
        elif isinstance(assignees, list):
            assignee_list = assignees

    # Also support legacy single assigned_to
    if assigned_to and assigned_to not in assignee_list:
        assignee_list.append(assigned_to)

    for user in assignee_list:
        if user:
            task_data["assignees"].append({"user": user})

    # Set the legacy assigned_to to the first assignee for backward compat
    if assignee_list:
        task_data["assigned_to"] = assignee_list[0]

    doc = frappe.get_doc(task_data)
    doc.insert()
    frappe.db.commit()

    return {
        "name": doc.name,
        "task_title": doc.task_title,
        "status": doc.status,
        "project": doc.project,
        "assignees": [{"user": a.user, "full_name": a.full_name} for a in doc.assignees],
    }


@frappe.whitelist()
def update_task_assignees(task, assignees):
    """Update the assignees of a task."""
    if isinstance(assignees, str):
        assignees = json.loads(assignees)

    doc = frappe.get_doc("PMS Task", task)
    doc.assignees = []
    for user in assignees:
        if user:
            doc.append("assignees", {"user": user})

    # Update legacy field
    if assignees:
        doc.assigned_to = assignees[0]
    else:
        doc.assigned_to = None

    doc.save()
    frappe.db.commit()

    return {
        "name": doc.name,
        "assignees": [{"user": a.user, "full_name": a.full_name} for a in doc.assignees],
    }


@frappe.whitelist()
def get_task_assignees(task):
    """Get all assignees for a task."""
    assignees = frappe.get_all(
        "PMS Task Assignee",
        filters={"parent": task, "parenttype": "PMS Task"},
        fields=["user", "full_name"],
        order_by="idx asc",
    )
    return assignees


@frappe.whitelist()
def get_bulk_task_assignees(task_names):
    """Get assignees for multiple tasks at once. Returns dict keyed by task name."""
    if isinstance(task_names, str):
        task_names = json.loads(task_names)

    if not task_names:
        return {}

    assignees = frappe.get_all(
        "PMS Task Assignee",
        filters={"parent": ["in", task_names], "parenttype": "PMS Task"},
        fields=["parent", "user", "full_name"],
        order_by="idx asc",
        limit_page_length=0,
    )

    result = {}
    for a in assignees:
        if a.parent not in result:
            result[a.parent] = []
        result[a.parent].append({"user": a.user, "full_name": a.full_name})

    return result


@frappe.whitelist()
def create_sprint(
    project,
    sprint_name,
    start_date=None,
    end_date=None,
    goal=None,
):
    """Create a new PMS Sprint in the given project."""
    doc = frappe.get_doc(
        {
            "doctype": "PMS Sprint",
            "project": project,
            "sprint_name": sprint_name,
            "start_date": start_date,
            "end_date": end_date,
            "goal": goal,
            "status": "Planned",
        }
    )
    doc.insert()
    frappe.db.commit()

    return {
        "name": doc.name,
        "sprint_name": doc.sprint_name,
        "project": doc.project,
    }


@frappe.whitelist()
def get_user_project_memberships(user):
    """Get all project memberships for a user with role and hourly rate."""
    memberships = frappe.db.sql("""
        SELECT
            ptm.parent as project,
            p.project_name,
            p.status as project_status,
            ptm.role,
            ptm.hourly_rate
        FROM `tabPMS Project Member` ptm
        JOIN `tabPMS Project` p ON p.name = ptm.parent
        WHERE ptm.user = %s
        ORDER BY p.modified DESC
    """, (user,), as_dict=True)

    # Also include projects where user is project manager
    existing = [m.project for m in memberships]
    pm_projects = frappe.get_all(
        "PMS Project",
        filters={
            "project_manager": user,
            "name": ["not in", existing] if existing else [],
        },
        fields=["name as project", "project_name", "status as project_status"],
        order_by="modified desc",
        limit_page_length=0,
    )
    for pm in pm_projects:
        pm["role"] = "Manager"
        pm["hourly_rate"] = 0
        memberships.append(pm)

    return memberships


@frappe.whitelist()
def get_my_tasks(status_filter=None, limit=100):
    """Get tasks assigned to the current user via both the assignees
    child table and the legacy assigned_to field."""
    user = frappe.session.user

    # Tasks where user is in assignees child table
    assigned_via_table = frappe.get_all(
        "PMS Task Assignee",
        filters={"user": user},
        pluck="parent",
    )

    # Tasks where user is in legacy assigned_to field
    assigned_via_field = frappe.get_all(
        "PMS Task",
        filters={"assigned_to": user},
        pluck="name",
    )

    all_task_names = list(set(assigned_via_table + assigned_via_field))
    if not all_task_names:
        return []

    filters = {"name": ["in", all_task_names]}
    if status_filter:
        if isinstance(status_filter, str):
            import json as json_mod
            try:
                status_filter = json_mod.loads(status_filter)
            except (json_mod.JSONDecodeError, ValueError):
                pass
        filters["status"] = status_filter
    else:
        filters["status"] = ["not in", ["Cancelled"]]

    return frappe.get_all(
        "PMS Task",
        filters=filters,
        fields=[
            "name", "task_title", "status", "priority", "project",
            "due_date", "estimated_hours", "task_type", "assigned_to",
        ],
        order_by="modified desc",
        limit_page_length=int(limit),
    )


# ═══════════════════════════════════════════════════════════════
# Team Overview APIs
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_team_overview():
    """Return all PMS team members with hourly rate and today's checkin status."""
    from next_pms.api.users import PMS_SPECIFIC_ROLES

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

    today_date = today()
    result = []

    for user in users:
        user_roles = set(frappe.get_roles(user.name))
        # Only include users with the "Next PMS" base role
        if "Next PMS" not in user_roles:
            continue

        # Determine PMS role
        pms_role = ""
        if "PMS Manager" in user_roles:
            pms_role = "manager"
        elif "PMS Developer" in user_roles:
            pms_role = "developer"
        elif "PMS Viewer" in user_roles:
            pms_role = "viewer"
        elif "PMS Customer" in user_roles:
            pms_role = "customer"

        # Get global hourly rate
        rate = frappe.db.get_default("pms_hourly_rate", parent=user.name)

        # Get today's checkin
        checkin = frappe.db.get_value(
            "PMS Checkin",
            {"user": user.name, "date": today_date},
            ["name", "checkin_time", "checkout_time", "is_active", "total_hours"],
            as_dict=True,
            order_by="checkin_time desc",
        )
        if checkin:
            checkin["checkin_time"] = str(checkin["checkin_time"]) if checkin["checkin_time"] else None
            checkin["checkout_time"] = str(checkin["checkout_time"]) if checkin["checkout_time"] else None
            checkin["is_active"] = bool(checkin.get("is_active"))

        result.append({
            "email": user.name,
            "full_name": user.full_name or user.name,
            "user_image": user.user_image,
            "pms_role": pms_role,
            "hourly_rate": float(rate or 0),
            "today_checkin": checkin,
        })

    return result


@frappe.whitelist()
def get_user_hourly_rate(user):
    """Get a user's global hourly rate."""
    rate = frappe.db.get_default("pms_hourly_rate", parent=user)
    return float(rate or 0)


@frappe.whitelist()
def get_user_detail(user):
    """Get complete detail for a single user. Admin or self can view."""
    from next_pms.api.users import ALL_PMS_ROLES
    from next_pms.api.permissions import get_user_permissions

    if user != frappe.session.user and not is_admin_user():
        frappe.throw("Not permitted", frappe.PermissionError)

    user_doc = frappe.get_cached_doc("User", user)
    user_roles = set(frappe.get_roles(user))
    pms_roles = user_roles & ALL_PMS_ROLES
    has_pms_access = bool(pms_roles)

    pms_role = ""
    if "PMS Manager" in pms_roles:
        pms_role = "manager"
    elif "PMS Developer" in pms_roles:
        pms_role = "developer"
    elif "PMS Viewer" in pms_roles:
        pms_role = "viewer"
    elif "PMS Customer" in pms_roles:
        pms_role = "customer"

    rate = frappe.db.get_default("pms_hourly_rate", parent=user)
    department = frappe.db.get_default("pms_department", parent=user) or ""

    today_date = today()
    checkin = frappe.db.get_value(
        "PMS Checkin",
        {"user": user, "date": today_date},
        ["name", "checkin_time", "checkout_time", "is_active", "total_hours"],
        as_dict=True,
        order_by="checkin_time desc",
    )
    if checkin:
        checkin["checkin_time"] = str(checkin["checkin_time"]) if checkin["checkin_time"] else None
        checkin["checkout_time"] = str(checkin["checkout_time"]) if checkin["checkout_time"] else None
        checkin["is_active"] = bool(checkin.get("is_active"))

    perms = get_user_permissions(user)

    return {
        "email": user,
        "full_name": user_doc.full_name or user,
        "user_image": user_doc.user_image,
        "pms_role": pms_role,
        "has_pms_access": has_pms_access,
        "hourly_rate": float(rate or 0),
        "department": department,
        "today_checkin": checkin,
        "sidebar_permissions": perms.get("sidebar_permissions", {}),
        "project_tab_permissions": perms.get("project_tab_permissions", {}),
        "feature_permissions": perms.get("feature_permissions", {}),
    }


@frappe.whitelist()
def set_user_hourly_rate(user, rate):
    """Set a user's global hourly rate. Admin, PM, or self can set."""
    if not is_admin_user() and frappe.session.user != user:
        frappe.throw("Not permitted", frappe.PermissionError)
    frappe.db.set_default("pms_hourly_rate", float(rate or 0), parent=user)
    frappe.db.commit()
    return {"success": True, "rate": float(rate or 0)}


@frappe.whitelist()
def set_user_department(user, department):
    """Set a user's PMS department. Admin only."""
    if not is_admin_user():
        frappe.throw("Only administrators can set departments.", frappe.PermissionError)
    frappe.db.set_default("pms_department", department or "", parent=user)
    frappe.db.commit()
    return {"success": True, "department": department or ""}


# ═══════════════════════════════════════════════════════════════
# Task Activity Log
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_task_activity(task):
    """Return activity log for a task: creation, status changes, assignment changes."""
    from frappe.utils import get_datetime

    doc = frappe.get_doc("PMS Task", task)
    activities = []

    # 1. Task created
    owner_name = frappe.get_cached_value("User", doc.owner, "full_name") or doc.owner
    activities.append({
        "type": "created",
        "user": doc.owner,
        "user_name": owner_name,
        "timestamp": str(doc.creation),
        "detail": f"created this task",
    })

    # 2. Get status/assignment changes from Version log
    versions = frappe.get_all(
        "Version",
        filters={"ref_doctype": "PMS Task", "docname": task},
        fields=["data", "owner", "creation"],
        order_by="creation asc",
        limit_page_length=0,
    )

    for ver in versions:
        try:
            data = json.loads(ver.data) if isinstance(ver.data, str) else ver.data
            changed = data.get("changed", [])
            ver_user = frappe.get_cached_value("User", ver.owner, "full_name") or ver.owner

            for change in changed:
                if len(change) >= 3:
                    field, old_val, new_val = change[0], change[1], change[2]

                    # Resolve user-type fields to full names
                    user_fields = {"assigned_to", "reviewer"}

                    if field == "status":
                        activities.append({
                            "type": "status_change",
                            "user": ver.owner,
                            "user_name": ver_user,
                            "timestamp": str(ver.creation),
                            "detail": f"changed status from {old_val} to {new_val}",
                            "old_value": old_val,
                            "new_value": new_val,
                        })
                    elif field in user_fields:
                        new_name = frappe.get_cached_value("User", new_val, "full_name") if new_val else "nobody"
                        label = field.replace("_", " ")
                        activities.append({
                            "type": "assignment" if field == "assigned_to" else f"{field}_change",
                            "user": ver.owner,
                            "user_name": ver_user,
                            "timestamp": str(ver.creation),
                            "detail": f"set {label} to {new_name}",
                        })
                    elif field == "sprint":
                        activities.append({
                            "type": "sprint_change",
                            "user": ver.owner,
                            "user_name": ver_user,
                            "timestamp": str(ver.creation),
                            "detail": f"moved to sprint {new_val or 'None'}",
                        })
                    elif field in ("priority", "due_date", "start_date", "task_type",
                                   "estimated_hours", "task_title", "description"):
                        label = field.replace("_", " ")
                        old_display = old_val if old_val else "empty"
                        new_display = new_val if new_val else "empty"
                        activities.append({
                            "type": "field_change",
                            "user": ver.owner,
                            "user_name": ver_user,
                            "timestamp": str(ver.creation),
                            "detail": f"changed {label} from {old_display} to {new_display}",
                            "field": field,
                        })
        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    # 3. Add last modified info if no version records found (fallback)
    if len(activities) <= 1 and doc.modified_by:
        modified_name = frappe.get_cached_value("User", doc.modified_by, "full_name") or doc.modified_by
        activities.append({
            "type": "modified",
            "user": doc.modified_by,
            "user_name": modified_name,
            "timestamp": str(doc.modified),
            "detail": f"last modified (status: {doc.status})",
        })

    # Sort by timestamp descending (newest first)
    activities.sort(key=lambda a: a["timestamp"], reverse=True)
    return activities


@frappe.whitelist()
def get_task_overtime_hours(task):
    """Calculate hours spent after the due date for a task."""
    from frappe.utils import get_datetime, getdate

    doc = frappe.get_doc("PMS Task", task)
    if not doc.due_date:
        return {"overtime_hours": 0, "has_due_date": False}

    due_date_end = get_datetime(str(doc.due_date) + " 23:59:59")

    logs = frappe.get_all(
        "PMS Time Log",
        filters={"task": task, "is_running": 0},
        fields=["start_time", "end_time", "duration_hours"],
    )

    overtime_seconds = 0
    for log in logs:
        if not log.end_time:
            continue
        start = get_datetime(log.start_time)
        end = get_datetime(log.end_time)

        if end > due_date_end:
            # If the log started before due date, only count the part after
            overtime_start = max(start, due_date_end)
            overtime_seconds += (end - overtime_start).total_seconds()

    overtime_hours = round(overtime_seconds / 3600, 2)
    return {
        "overtime_hours": overtime_hours,
        "has_due_date": True,
        "due_date": str(doc.due_date),
    }


# ═══════════════════════════════════════════════════════════════
# Task Report
# ═══════════════════════════════════════════════════════════════

def _aggregate_window_hours(logs):
    """Sum duration_hours per task from a list of time-log rows.
    Returns {task_name: hours}. Pure — no DB access."""
    window_hours = {}
    for log in logs:
        task = log.get("task")
        if task:
            window_hours[task] = window_hours.get(task, 0) + (log.get("duration_hours") or 0)
    return window_hours


def _apply_window_to_tasks(tasks, window_hours):
    """Keep only tasks with logs in the window and override actual_hours /
    calculated_cost with the in-window totals. Pure — no DB access."""
    out = [t for t in tasks if t["name"] in window_hours]
    for t in out:
        t["actual_hours"] = round(window_hours.get(t["name"], 0), 2)
        if t.get("hourly_rate") is not None:
            t["calculated_cost"] = round(t["actual_hours"] * (t.get("hourly_rate") or 0), 2)
    return out


@frappe.whitelist()
def get_task_report(filters=None):
    """Get comprehensive task report with filters.
    Filters: project, user, from_date, to_date, priority, task_type, status
    Role-based: Developers see only their own tasks. Managers/Admins see all.
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    filters = filters or {}

    # Role-based access: developers only see their own tasks
    current_user = frappe.session.user
    user_roles = set(frappe.get_roles(current_user))
    is_admin = bool({"System Manager", "Administrator"} & user_roles)
    is_manager = "PMS Manager" in user_roles
    is_developer_only = "PMS Developer" in user_roles and not is_manager and not is_admin

    db_filters = {}

    if filters.get("search"):
        db_filters["task_title"] = ["like", f"%{filters['search']}%"]
    if filters.get("project"):
        db_filters["project"] = filters["project"]
    if filters.get("priority"):
        db_filters["priority"] = filters["priority"]
    if filters.get("task_type"):
        db_filters["task_type"] = filters["task_type"]
    if filters.get("status"):
        db_filters["status"] = filters["status"]

    # Date range — defines the time-log WINDOW for effort reporting.
    # Standard effort/timesheet behaviour: filter by when work was LOGGED, not when the
    # task was created. Window mode engages when both dates are present (the normal case
    # — the UI defaults both to today). With a partial/empty range we fall back to the
    # legacy creation-date filter + lifetime hours for backward compatibility.
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    window_mode = bool(from_date and to_date)

    # "User" filter means whoever LOGGED the time (PMS Time Log.user) in window mode,
    # matching the Time Logs view; in legacy mode it means the task assignee.
    user_filter = filters.get("user")

    log_window_filters = None
    if window_mode:
        log_window_filters = {
            "is_running": 0,
            "start_time": ["between", [from_date + " 00:00:00", to_date + " 23:59:59"]],
        }
        effective_log_user = current_user if is_developer_only else user_filter
        if effective_log_user:
            log_window_filters["user"] = effective_log_user
    else:
        # For developers, force filter to only their assigned tasks
        if is_developer_only:
            db_filters["assigned_to"] = current_user
        if from_date:
            db_filters["creation"] = [">=", from_date]
        elif to_date:
            db_filters["creation"] = ["<=", to_date + " 23:59:59"]

    # Build safe field list — only include fields that exist in the DB
    base_fields = [
        "name", "task_title", "project", "status", "priority",
        "task_type", "assigned_to", "due_date", "start_date",
        "estimated_hours", "actual_hours",
        "owner", "creation", "modified",
    ]
    optional_fields = ["is_billable", "hourly_rate", "calculated_cost", "sprint", "reviewer"]
    meta = frappe.get_meta("PMS Task")
    existing_fieldnames = {f.fieldname for f in meta.fields}
    safe_fields = base_fields + [f for f in optional_fields if f in existing_fieldnames]

    try:
        tasks = frappe.get_all(
            "PMS Task",
            filters=db_filters,
            fields=safe_fields,
            order_by="creation desc",
            limit_page_length=0,
        )
    except Exception as e:
        frappe.log_error(f"Task report query failed: {str(e)}", "Task Report Error")
        frappe.throw("Failed to fetch task report. Please try again.")

    # For developer-only users, also include tasks from the assignees child table
    # (legacy mode only — in window mode the log-user filter governs the task set).
    if is_developer_only and not window_mode:
        child_assigned = set(frappe.get_all(
            "PMS Task Assignee",
            filters={"user": current_user},
            pluck="parent",
        ))
        if child_assigned:
            # Re-fetch tasks from child table that weren't caught by assigned_to filter
            extra_filters = {k: v for k, v in db_filters.items() if k != "assigned_to"}
            extra_filters["name"] = ["in", list(child_assigned)]
            try:
                extra_tasks = frappe.get_all(
                    "PMS Task", filters=extra_filters, fields=safe_fields,
                    order_by="creation desc", limit_page_length=0,
                )
                existing_names = {t.name for t in tasks}
                for t in extra_tasks:
                    if t.name not in existing_names:
                        tasks.append(t)
            except Exception:
                pass

    # If user filter (explicit from UI dropdown), find tasks assigned to this user
    # (legacy mode only — window mode filters by who logged the time instead).
    if user_filter and not window_mode:
        assigned_tasks = set(frappe.get_all(
            "PMS Task Assignee",
            filters={"user": user_filter},
            pluck="parent",
        ))
        tasks = [t for t in tasks if t.name in assigned_tasks or t.assigned_to == user_filter]

    # Window mode: restrict to tasks with logs in range and override hours/cost with the
    # in-window totals so the report reconciles with the Time Logs view. Estimated hours
    # stay lifetime per task (an estimate is not time-phased).
    if window_mode:
        logs = frappe.get_all(
            "PMS Time Log",
            filters=log_window_filters,
            fields=["task", "duration_hours"],
        )
        tasks = _apply_window_to_tasks(tasks, _aggregate_window_hours(logs))

    # Batch-load user full names and project names to avoid N+1 queries
    user_emails = set()
    project_ids = set()
    for task in tasks:
        if task.get("owner"):
            user_emails.add(task["owner"])
        if task.get("assigned_to"):
            user_emails.add(task["assigned_to"])
        if task.get("project"):
            project_ids.add(task["project"])

    # Load all user names at once
    user_name_map = {}
    if user_emails:
        users = frappe.get_all(
            "User",
            filters={"name": ["in", list(user_emails)]},
            fields=["name", "full_name"],
        )
        user_name_map = {u.name: u.full_name or u.name for u in users}

    # Load all project names at once
    project_name_map = {}
    if project_ids:
        projects = frappe.get_all(
            "PMS Project",
            filters={"name": ["in", list(project_ids)]},
            fields=["name", "project_name"],
        )
        project_name_map = {p.name: p.project_name or p.name for p in projects}

    # Load all assignees at once
    task_names = [t["name"] for t in tasks]
    assignee_map = {}
    if task_names:
        all_assignees = frappe.get_all(
            "PMS Task Assignee",
            filters={"parent": ["in", task_names]},
            fields=["parent", "user"],
        )
        for a in all_assignees:
            assignee_map.setdefault(a.parent, []).append(a.user)
            user_emails.add(a.user)

        # Re-fetch any new user names from assignees
        missing_users = user_emails - set(user_name_map.keys())
        if missing_users:
            extra_users = frappe.get_all(
                "User",
                filters={"name": ["in", list(missing_users)]},
                fields=["name", "full_name"],
            )
            for u in extra_users:
                user_name_map[u.name] = u.full_name or u.name

    # Determine if current user can view finance data
    can_view_finance = is_admin or is_manager

    # Enrich tasks
    for task in tasks:
        task["owner_name"] = user_name_map.get(task["owner"], task["owner"])
        task["assigned_to_name"] = user_name_map.get(task.get("assigned_to", ""), "")

        # Get assignee names from batch-loaded map
        task_assignees = assignee_map.get(task["name"], [])
        if task_assignees:
            task["assignee_names"] = ", ".join(
                user_name_map.get(u, u) for u in task_assignees
            )
        else:
            task["assignee_names"] = task.get("assigned_to_name", "")

        task["project_name"] = project_name_map.get(task.get("project", ""), "")
        task["creation"] = str(task["creation"])
        task["modified"] = str(task["modified"])

        # Strip finance fields for non-finance users
        if not can_view_finance:
            task.pop("hourly_rate", None)
            task.pop("calculated_cost", None)
            task.pop("is_billable", None)

    # Summary stats
    total_tasks = len(tasks)
    total_estimated = sum(t.get("estimated_hours") or 0 for t in tasks)
    total_actual = sum(t.get("actual_hours") or 0 for t in tasks)
    total_cost = sum(t.get("calculated_cost") or 0 for t in tasks) if can_view_finance else 0

    status_summary = {}
    for t in tasks:
        s = t.get("status", "Unknown")
        status_summary[s] = status_summary.get(s, 0) + 1

    return {
        "tasks": tasks,
        "summary": {
            "total_tasks": total_tasks,
            "total_estimated_hours": round(total_estimated, 2),
            "total_actual_hours": round(total_actual, 2),
            "total_cost": round(total_cost, 2),
            "status_breakdown": status_summary,
        },
    }


@frappe.whitelist()
def get_departments():
    """Return only enabled, non-group departments for dropdown."""
    return frappe.get_all(
        "Department",
        fields=["name", "department_name"],
        filters={"disabled": 0, "is_group": 0},
        order_by="department_name asc",
        ignore_permissions=True,
    )


@frappe.whitelist()
def toggle_favorite_project(project):
    """Add or remove a project from the current user's favorites.
    Returns {"is_favorite": True/False}.
    """
    user = frappe.session.user
    existing = frappe.db.exists(
        "PMS Favorite Project", {"user": user, "project": project}
    )
    if existing:
        frappe.delete_doc("PMS Favorite Project", existing, ignore_permissions=True)
        frappe.db.commit()
        return {"is_favorite": False}
    else:
        doc = frappe.get_doc({
            "doctype": "PMS Favorite Project",
            "user": user,
            "project": project,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"is_favorite": True}


@frappe.whitelist()
def get_favorite_projects():
    """Return list of project names favorited by the current user."""
    return frappe.get_all(
        "PMS Favorite Project",
        filters={"user": frappe.session.user},
        pluck="project",
        ignore_permissions=True,
    )
