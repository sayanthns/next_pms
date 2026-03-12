import frappe
from frappe.utils import now_datetime, time_diff_in_seconds, get_datetime, today

from next_pms.api.permissions import is_admin_user, is_manager_user, get_user_projects, get_current_user_feature_permissions


@frappe.whitelist()
def start_timer(task):
    """Start a timer for a task. Creates a new PMS Time Log with is_running=1.
    Validates no other timer is running for the same user.
    Requires the user to be checked in first.
    """
    user = frappe.session.user

    # Check if user is checked in today
    active_checkin = frappe.get_all(
        "PMS Checkin",
        filters={"user": user, "date": today(), "is_active": 1},
        limit=1,
    )
    if not active_checkin:
        frappe.throw("You must check in before starting a timer. Please check in first.")

    # Check for existing running timer
    existing = frappe.get_all(
        "PMS Time Log",
        filters={"user": user, "is_running": 1},
        fields=["name", "task"],
        limit=1,
    )
    if existing:
        task_title = frappe.db.get_value("PMS Task", existing[0].task, "task_title")
        frappe.throw(
            f"You already have a running timer on task '{task_title}' ({existing[0].name}). "
            "Stop it before starting a new one."
        )

    # Validate task exists and is not done
    task_doc = frappe.get_doc("PMS Task", task)
    if task_doc.status == "Done":
        frappe.throw("Cannot start timer on a completed task.")

    # Create time log
    log = frappe.new_doc("PMS Time Log")
    log.task = task
    log.user = user
    log.start_time = now_datetime()
    log.is_running = 1
    log.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "log_name": log.name,
        "task": task,
        "task_title": task_doc.task_title,
        "start_time": str(log.start_time),
        "server_time": str(now_datetime()),
        "user": user,
    }


@frappe.whitelist()
def stop_timer(log_name):
    """Stop a running timer. Sets end_time, calculates duration, triggers recalculation."""
    log = frappe.get_doc("PMS Time Log", log_name)

    if not log.is_running:
        frappe.throw("This timer is not running.")

    # Allow the user who started it, admin, or PM to stop
    user_roles = set(frappe.get_roles())
    can_stop = (
        log.user == frappe.session.user
        or "System Manager" in user_roles
        or "PMS Manager" in user_roles
    )
    if not can_stop:
        frappe.throw("You can only stop your own timers.")

    log.end_time = now_datetime()
    log.is_running = 0

    # Calculate duration
    start = get_datetime(log.start_time)
    end = get_datetime(log.end_time)
    diff_seconds = time_diff_in_seconds(end, start)
    log.duration_minutes = int(diff_seconds / 60)
    log.duration_hours = round(diff_seconds / 3600, 2)

    log.save(ignore_permissions=True)
    frappe.db.commit()

    # Get updated task data
    task = frappe.get_doc("PMS Task", log.task)

    return {
        "log_name": log.name,
        "task": log.task,
        "task_title": task.task_title,
        "duration_minutes": log.duration_minutes,
        "duration_hours": log.duration_hours,
        "actual_hours": task.actual_hours,
        "calculated_cost": task.calculated_cost,
    }


@frappe.whitelist()
def get_running_timer():
    """Get the current user's running timer, if any."""
    user = frappe.session.user

    running = frappe.get_all(
        "PMS Time Log",
        filters={"user": user, "is_running": 1},
        fields=["name", "task", "start_time"],
        limit=1,
    )

    if running:
        log = running[0]
        task_title = frappe.db.get_value("PMS Task", log.task, "task_title")
        # Send server_time so frontend can compute clock offset
        return {
            "log_name": log.name,
            "task": log.task,
            "task_title": task_title,
            "start_time": str(log.start_time),
            "server_time": str(frappe.utils.now_datetime()),
        }

    return None


@frappe.whitelist()
def get_all_timelogs(filters=None, limit=100, offset=0):
    """Get time logs with optional filters.
    Admin sees all, PM sees logs from their allocated projects, Developer sees own logs.
    """
    import json as json_module

    if isinstance(filters, str):
        filters = json_module.loads(filters)
    if not filters:
        filters = {}

    user = frappe.session.user
    is_admin = is_admin_user()
    is_pm = is_manager_user()
    feature_perms = get_current_user_feature_permissions()
    can_view_all_timelogs = feature_perms.get("view_all_timelogs", True)

    # Build filters
    db_filters = {}

    # If feature permission denies viewing all timelogs, force own-user filter
    if not can_view_all_timelogs:
        db_filters["user"] = user
    elif filters.get("user"):
        # Only admin or PM can filter by other users
        if is_admin or is_pm:
            db_filters["user"] = filters["user"]
        else:
            db_filters["user"] = user
    elif not is_admin:
        if is_pm:
            # PM: if no user filter specified, show logs from their projects
            # This is handled by the project filter below or shows all users in their projects
            pass
        else:
            # Developer: only their own logs
            db_filters["user"] = user

    if filters.get("task"):
        db_filters["task"] = filters["task"]

    # Task type filter — find tasks of this type, then filter logs to those tasks
    if filters.get("task_type"):
        tt_filters = {"task_type": filters["task_type"]}
        if filters.get("project"):
            tt_filters["project"] = filters["project"]
        tt_tasks = frappe.get_all("PMS Task", filters=tt_filters, pluck="name", limit_page_length=0)
        if tt_tasks:
            db_filters["task"] = ["in", tt_tasks]
        else:
            return {"logs": [], "total": 0}

    if filters.get("project") and not filters.get("task_type"):
        # Get all tasks for the project, then filter logs by those tasks
        tasks = frappe.get_all(
            "PMS Task",
            filters={"project": filters["project"]},
            fields=["name"],
            limit_page_length=0,
        )
        task_names = [t.name for t in tasks]
        if task_names:
            db_filters["task"] = ["in", task_names]
        else:
            return {"logs": [], "total": 0}
    elif is_pm and not is_admin and "user" not in db_filters:
        # PM without project filter: scope to tasks in their accessible projects
        user_projects = get_user_projects()
        if user_projects and user_projects != ["__none__"]:
            pm_tasks = frappe.get_all(
                "PMS Task",
                filters={"project": ["in", user_projects]},
                pluck="name",
                limit_page_length=0,
            )
            if pm_tasks:
                db_filters["task"] = ["in", pm_tasks]
            else:
                return {"logs": [], "total": 0}
        else:
            return {"logs": [], "total": 0}

    if filters.get("from_date"):
        db_filters["start_time"] = [">=", filters["from_date"]]

    if filters.get("to_date"):
        db_filters["end_time"] = ["<=", filters["to_date"] + " 23:59:59"]

    if filters.get("is_running") is not None:
        db_filters["is_running"] = filters["is_running"]

    total = frappe.db.count("PMS Time Log", db_filters)

    logs = frappe.get_all(
        "PMS Time Log",
        filters=db_filters,
        fields=[
            "name",
            "task",
            "user",
            "start_time",
            "end_time",
            "duration_hours",
            "duration_minutes",
            "is_running",
            "notes",
        ],
        order_by="start_time desc",
        limit_page_length=int(limit),
        limit_start=int(offset),
    )

    # Enrich with task title, project, task_type, user full name
    for log in logs:
        task_data = frappe.db.get_value(
            "PMS Task", log["task"], ["task_title", "project", "task_type"], as_dict=True
        )
        if task_data:
            log["task_title"] = task_data.task_title
            log["project"] = task_data.project
            log["task_type"] = task_data.task_type or ""
        else:
            log["task_title"] = log["task"]
            log["project"] = ""
            log["task_type"] = ""
        log["user_full_name"] = (
            frappe.get_cached_value("User", log["user"], "full_name") or log["user"]
        )
        log["start_time"] = str(log["start_time"]) if log["start_time"] else None
        log["end_time"] = str(log["end_time"]) if log["end_time"] else None

    return {"logs": logs, "total": total}


@frappe.whitelist()
def get_active_timers():
    """Get all currently running timers. Admin sees all, PM sees their project timers."""
    user = frappe.session.user
    is_admin = is_admin_user()
    is_pm = is_manager_user()

    if not is_admin and not is_pm:
        frappe.throw("Only admin and project managers can view all active timers.")

    db_filters = {"is_running": 1}

    # PM: only show timers for tasks in their projects
    if is_pm and not is_admin:
        user_projects = get_user_projects()
        if user_projects and user_projects != ["__none__"]:
            pm_tasks = frappe.get_all(
                "PMS Task",
                filters={"project": ["in", user_projects]},
                pluck="name",
                limit_page_length=0,
            )
            if pm_tasks:
                db_filters["task"] = ["in", pm_tasks]
            else:
                return []
        else:
            return []

    running = frappe.get_all(
        "PMS Time Log",
        filters=db_filters,
        fields=["name", "task", "user", "start_time"],
        order_by="start_time asc",
    )

    for log in running:
        task_data = frappe.db.get_value(
            "PMS Task", log["task"], ["task_title", "project"], as_dict=True
        )
        if task_data:
            log["task_title"] = task_data.task_title
            log["project"] = task_data.project
        else:
            log["task_title"] = log["task"]
            log["project"] = ""
        log["user_full_name"] = (
            frappe.get_cached_value("User", log["user"], "full_name") or log["user"]
        )
        log["start_time"] = str(log["start_time"])
        # Calculate elapsed
        elapsed = time_diff_in_seconds(
            now_datetime(), get_datetime(log["start_time"])
        )
        log["elapsed_seconds"] = int(elapsed)

    return running


@frappe.whitelist()
def get_timelog_filters():
    """Get available filter options for timelogs (users, projects)."""
    user = frappe.session.user
    is_admin = is_admin_user()
    is_pm = is_manager_user()
    feature_perms = get_current_user_feature_permissions()
    can_view_all_timelogs = feature_perms.get("view_all_timelogs", True)

    # If feature permission denies viewing all timelogs, only show self
    if not can_view_all_timelogs:
        users = [
            {
                "user": user,
                "full_name": frappe.get_cached_value("User", user, "full_name")
                or user,
            }
        ]
        # Projects: only those with own timelogs
        projects = frappe.db.sql(
            """
            SELECT DISTINCT t.project, p.project_name
            FROM `tabPMS Time Log` tl
            JOIN `tabPMS Task` t ON t.name = tl.task
            JOIN `tabPMS Project` p ON p.name = t.project
            WHERE tl.user = %s
            ORDER BY p.project_name
        """,
            (user,),
            as_dict=True,
        )
        return {
            "users": users,
            "projects": projects,
            "is_admin": False,
        }

    # Get users with time logs
    if is_admin:
        users = frappe.db.sql(
            """
            SELECT DISTINCT tl.user, u.full_name
            FROM `tabPMS Time Log` tl
            LEFT JOIN `tabUser` u ON u.name = tl.user
            ORDER BY u.full_name
        """,
            as_dict=True,
        )
    elif is_pm:
        # PM sees users from their projects
        user_projects = get_user_projects()
        if user_projects and user_projects != ["__none__"]:
            placeholders = ", ".join(["%s"] * len(user_projects))
            users = frappe.db.sql(
                f"""
                SELECT DISTINCT tl.user, u.full_name
                FROM `tabPMS Time Log` tl
                LEFT JOIN `tabUser` u ON u.name = tl.user
                JOIN `tabPMS Task` t ON t.name = tl.task
                WHERE t.project IN ({placeholders})
                ORDER BY u.full_name
            """,
                tuple(user_projects),
                as_dict=True,
            )
        else:
            users = [
                {
                    "user": user,
                    "full_name": frappe.get_cached_value("User", user, "full_name")
                    or user,
                }
            ]
    else:
        users = [
            {
                "user": user,
                "full_name": frappe.get_cached_value("User", user, "full_name")
                or user,
            }
        ]

    # Get projects with time logs
    if is_admin:
        projects = frappe.db.sql(
            """
            SELECT DISTINCT t.project, p.project_name
            FROM `tabPMS Time Log` tl
            JOIN `tabPMS Task` t ON t.name = tl.task
            JOIN `tabPMS Project` p ON p.name = t.project
            ORDER BY p.project_name
        """,
            as_dict=True,
        )
    elif is_pm:
        user_projects = get_user_projects()
        if user_projects and user_projects != ["__none__"]:
            placeholders = ", ".join(["%s"] * len(user_projects))
            projects = frappe.db.sql(
                f"""
                SELECT DISTINCT t.project, p.project_name
                FROM `tabPMS Time Log` tl
                JOIN `tabPMS Task` t ON t.name = tl.task
                JOIN `tabPMS Project` p ON p.name = t.project
                WHERE t.project IN ({placeholders})
                ORDER BY p.project_name
            """,
                tuple(user_projects),
                as_dict=True,
            )
        else:
            projects = []
    else:
        projects = frappe.db.sql(
            """
            SELECT DISTINCT t.project, p.project_name
            FROM `tabPMS Time Log` tl
            JOIN `tabPMS Task` t ON t.name = tl.task
            JOIN `tabPMS Project` p ON p.name = t.project
            WHERE tl.user = %s
            ORDER BY p.project_name
        """,
            (user,),
            as_dict=True,
        )

    return {
        "users": users,
        "projects": projects,
        "is_admin": is_admin or is_pm,
    }
