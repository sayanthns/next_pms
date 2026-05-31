import frappe
from frappe import _
from frappe.utils import now_datetime, add_days, getdate, date_diff, get_datetime
from next_pms.utils import get_pms_url


def send_deadline_reminders():
    """Send notifications for tasks with deadlines approaching within 1 day."""
    tomorrow = add_days(getdate(), 1)
    tasks = frappe.get_all(
        "PMS Task",
        filters={
            "due_date": tomorrow,
            "status": ["not in", ["Done", "Cancelled"]],
            "assigned_to": ["is", "set"],
        },
        fields=["name", "task_title", "assigned_to", "project", "due_date", "status"],
    )

    for task in tasks:
        assigned_to_name = frappe.db.get_value("User", task.assigned_to, "full_name") or task.assigned_to
        project_name = frappe.db.get_value("PMS Project", task.project, "project_name") or task.project
        task_url = get_pms_url("PMS Task", task.name)

        message = frappe.render_template(
            "next_pms/templates/emails/deadline_reminder.html",
            {
                "task_title": task.task_title,
                "assigned_to_name": assigned_to_name,
                "project_name": project_name,
                "due_date": task.due_date,
                "status": task.status,
                "task_url": task_url,
            },
        )

        frappe.sendmail(
            recipients=[task.assigned_to],
            subject=f"Task Due Tomorrow: {task.task_title}",
            message=message,
            now=True,
        )

        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "for_user": task.assigned_to,
                "type": "Alert",
                "document_type": "PMS Task",
                "document_name": task.name,
                "subject": f"Task Due Tomorrow: {task.task_title}",
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()


def check_long_running_timers():
    """Alert users with timers running for more than 4 hours."""
    four_hours_ago = frappe.utils.add_to_date(now_datetime(), hours=-4)

    running_logs = frappe.get_all(
        "PMS Time Log",
        filters={
            "is_running": 1,
            "start_time": ["<", four_hours_ago],
        },
        fields=["name", "user", "task", "start_time"],
    )

    for log in running_logs:
        task_title = frappe.db.get_value("PMS Task", log.task, "task_title")
        hours_running = (now_datetime() - get_datetime(log.start_time)).total_seconds() / 3600
        user_name = frappe.db.get_value("User", log.user, "full_name") or log.user
        task_url = get_pms_url("PMS Task", log.task)

        message = frappe.render_template(
            "next_pms/templates/emails/timer_reminder.html",
            {
                "user_name": user_name,
                "task_title": task_title,
                "hours_running": f"{hours_running:.1f}",
                "task_url": task_url,
            },
        )

        frappe.sendmail(
            recipients=[log.user],
            subject=f"Timer Running: {task_title} ({hours_running:.1f}h)",
            message=message,
            now=True,
        )

        # Create Notification Log entry
        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "for_user": log.user,
                "type": "Alert",
                "document_type": "PMS Time Log",
                "document_name": log.name,
                "subject": f"Timer Running: {task_title} ({hours_running:.1f}h)",
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()


def check_budget_alerts():
    """Check projects exceeding 80% budget utilization."""
    projects = frappe.get_all(
        "PMS Project",
        filters={
            "status": "Active",
            "total_budget": [">", 0],
        },
        fields=[
            "name", "project_name", "project_manager",
            "budget_utilization", "total_budget", "calculated_cost",
        ],
    )

    for project in projects:
        if project.budget_utilization and project.budget_utilization >= 80:
            manager_name = (
                frappe.db.get_value("User", project.project_manager, "full_name")
                or project.project_manager
            )
            used_budget = project.calculated_cost or 0
            remaining = (project.total_budget or 0) - used_budget
            project_url = get_pms_url("PMS Project", project.name)

            message = frappe.render_template(
                "next_pms/templates/emails/budget_alert.html",
                {
                    "project_name": project.project_name,
                    "manager_name": manager_name,
                    "utilization": f"{project.budget_utilization:.0f}",
                    "total_budget": f"{project.total_budget:,.2f}",
                    "used_budget": f"{used_budget:,.2f}",
                    "remaining": f"{remaining:,.2f}",
                    "project_url": project_url,
                },
            )

            frappe.sendmail(
                recipients=[project.project_manager],
                subject=f"Budget Alert: {project.project_name} at {project.budget_utilization:.0f}%",
                message=message,
                now=True,
            )

            # Create Notification Log entry
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": project.project_manager,
                    "type": "Alert",
                    "document_type": "PMS Project",
                    "document_name": project.name,
                    "subject": f"Budget Alert: {project.project_name} at {project.budget_utilization:.0f}%",
                }
            ).insert(ignore_permissions=True)

    frappe.db.commit()


def get_week_start(d):
    """Monday of the week containing date d."""
    d = getdate(d)
    return add_days(d, -d.weekday())  # weekday(): Monday=0


def _get_active_members(from_dt, to_dt):
    """Enabled users who logged time this week OR are members of an Active project."""
    logged = frappe.get_all(
        "PMS Time Log",
        filters={"start_time": ["between", [from_dt, to_dt]], "is_running": 0},
        fields=["user"],
        group_by="user",
    )
    members = {l.user for l in logged if l.user}

    active_projects = frappe.get_all("PMS Project", filters={"status": "Active"}, fields=["name"])
    active_proj_names = [p.name for p in active_projects]
    if active_proj_names:
        project_members = frappe.get_all(
            "PMS Project Member",
            filters={"parenttype": "PMS Project", "parent": ["in", active_proj_names]},
            fields=["user"],
        )
        members |= {m.user for m in project_members if m.user}

    if not members:
        return []
    enabled = frappe.get_all(
        "User",
        filters={"name": ["in", list(members)], "enabled": 1},
        fields=["name"],
    )
    return [u.name for u in enabled]


def _member_week_stats(user, week_start, week_end, from_dt, to_dt):
    """Per-member weekly stats dict (no email). Uses shared 8h-baseline target."""
    from next_pms.api._hours import compute_target_hours, compute_utilization

    full_name = frappe.db.get_value("User", user, "full_name") or user

    logs = frappe.get_all(
        "PMS Time Log",
        filters={"user": user, "start_time": ["between", [from_dt, to_dt]], "is_running": 0},
        fields=["duration_hours", "task"],
    )
    logged_hours = round(sum(l.duration_hours or 0 for l in logs), 2)
    target_hours = compute_target_hours(user, week_start, week_end)
    utilization = compute_utilization(logged_hours, target_hours)

    tasks_completed = frappe.db.sql(
        """
        SELECT COUNT(*) FROM `tabPMS Task`
        WHERE assigned_to = %s AND status = 'Done'
          AND DATE(modified) BETWEEN %s AND %s
        """,
        (user, str(week_start), str(week_end)),
    )[0][0] or 0
    tasks_in_progress = frappe.db.count(
        "PMS Task", {"assigned_to": user, "status": ["in", ["In Progress", "In Review"]]}
    )

    task_names = list({l.task for l in logs if l.task})
    projects_touched = set()
    if task_names:
        for row in frappe.get_all(
            "PMS Task", filters={"name": ["in", task_names]}, fields=["project"]
        ):
            if row.project:
                projects_touched.add(row.project)

    return {
        "user": user,
        "full_name": full_name,
        "logged_hours": logged_hours,
        "target_hours": target_hours,
        "utilization": utilization,
        "tasks_completed": tasks_completed,
        "tasks_in_progress": tasks_in_progress,
        "project_count": len(projects_touched),
    }


def send_weekly_summary():
    """Saturday 07:00 - per active member: own weekly stats email.
    Configured recipient (default sayanth@enfono.in): all-members table.
    """
    week_end = getdate()
    week_start = get_week_start(week_end)
    from_dt = str(week_start) + " 00:00:00"
    to_dt = str(week_end) + " 23:59:59"

    members = _get_active_members(from_dt, to_dt)
    team_rows = []

    for user in members:
        stats = _member_week_stats(user, week_start, week_end, from_dt, to_dt)
        team_rows.append(stats)
        frappe.sendmail(
            recipients=[user],
            subject=_("Your Weekly Work Summary"),
            message=_build_member_weekly_html(stats, str(week_start), str(week_end)),
            now=True,
        )

    recipient = (
        frappe.db.get_single_value("PMS AI Settings", "weekly_summary_recipient")
        or "sayanth@enfono.in"
    )
    if team_rows:
        frappe.sendmail(
            recipients=[recipient],
            subject=_("Team Weekly Work Summary"),
            message=_build_team_weekly_html(team_rows, str(week_start), str(week_end)),
            now=True,
        )

    frappe.db.commit()


def _util_color(util):
    if util >= 90:
        return "#10B981"
    if util >= 60:
        return "#F59E0B"
    return "#EF4444"


def _build_member_weekly_html(stats, from_str, to_str):
    color = _util_color(stats["utilization"])
    return f"""
    <h3>Your Weekly Work Summary</h3>
    <p>Hi {stats['full_name']},</p>
    <p>Summary for <strong>{from_str}</strong> to <strong>{to_str}</strong>:</p>
    <table style="border-collapse:collapse; max-width:520px;">
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Hours Logged</td>
            <td style="padding:8px; border:1px solid #e5e7eb;"><strong>{stats['logged_hours']:.1f}h</strong></td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Target Hours</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{stats['target_hours']:.1f}h</td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Utilization</td>
            <td style="padding:8px; border:1px solid #e5e7eb; color:{color}; font-weight:600;">{stats['utilization']:.0f}%</td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Tasks Completed</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{stats['tasks_completed']}</td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Tasks In Progress</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{stats['tasks_in_progress']}</td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Projects Worked On</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{stats['project_count']}</td></tr>
    </table>
    <p style="margin-top:16px; color:#6b7280; font-size:13px;">
        Target = 8h x working days (excludes Sundays, holidays, approved leave).
        Automated weekly summary from Next PMS.
    </p>
    """


def _build_team_weekly_html(team_rows, from_str, to_str):
    rows = ""
    for s in sorted(team_rows, key=lambda x: x["utilization"], reverse=True):
        color = _util_color(s["utilization"])
        rows += f"""
        <tr>
            <td style="padding:10px; border:1px solid #e5e7eb;">{s['full_name']}</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['logged_hours']:.1f}h</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['target_hours']:.1f}h</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center; color:{color}; font-weight:600;">{s['utilization']:.0f}%</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['tasks_completed']}</td>
        </tr>
        """
    return f"""
    <h3>Team Weekly Work Summary</h3>
    <p>Week <strong>{from_str}</strong> to <strong>{to_str}</strong> - {len(team_rows)} active member(s):</p>
    <table style="border-collapse:collapse; width:100%; max-width:760px;">
        <thead>
            <tr style="background:#f3f4f6;">
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:left;">Member</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Logged</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Target</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Utilization</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Tasks Done</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:16px; color:#6b7280; font-size:13px;">
        Target = 8h x working days (excludes Sundays, holidays, approved leave).
        Automated weekly summary from Next PMS.
    </p>
    """
