import frappe
from frappe.utils import now_datetime, add_days, getdate, date_diff, get_datetime, get_url_to_form


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
        task_url = get_url_to_form("PMS Task", task.name)

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
        task_url = get_url_to_form("PMS Task", log.task)

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
            project_url = get_url_to_form("PMS Project", project.name)

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


def send_weekly_summary():
    """Email project managers a weekly summary of their active projects.

    This job is intended to run once a week (e.g. every Monday morning).
    It aggregates task counts, hours logged, and budget status for each
    active project and sends a single summary email per manager.
    """
    managers = frappe.get_all(
        "PMS Project",
        filters={"status": "Active", "project_manager": ["is", "set"]},
        fields=["project_manager"],
        group_by="project_manager",
    )

    for row in managers:
        manager = row.project_manager
        manager_name = frappe.db.get_value("User", manager, "full_name") or manager

        projects = frappe.get_all(
            "PMS Project",
            filters={"status": "Active", "project_manager": manager},
            fields=[
                "name", "project_name", "total_budget",
                "calculated_cost", "budget_utilization",
            ],
        )

        if not projects:
            continue

        one_week_ago = add_days(getdate(), -7)

        project_summaries = []
        for proj in projects:
            # Task counts
            total_tasks = frappe.db.count("PMS Task", {"project": proj.name})
            completed_tasks = frappe.db.count(
                "PMS Task", {"project": proj.name, "status": "Done"}
            )
            overdue_tasks = frappe.db.count(
                "PMS Task",
                {
                    "project": proj.name,
                    "due_date": ["<", getdate()],
                    "status": ["not in", ["Done", "Cancelled"]],
                },
            )

            # Hours logged this week
            week_logs = frappe.get_all(
                "PMS Time Log",
                filters={
                    "task": ["in",
                        [t.name for t in frappe.get_all("PMS Task", filters={"project": proj.name}, fields=["name"])]
                        or ["__none__"]
                    ],
                    "start_time": [">=", one_week_ago],
                    "is_running": 0,
                },
                fields=["duration_hours"],
            )
            hours_this_week = sum(l.duration_hours or 0 for l in week_logs)

            project_summaries.append({
                "project_name": proj.project_name,
                "project_url": get_url_to_form("PMS Project", proj.name),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "overdue_tasks": overdue_tasks,
                "hours_this_week": f"{hours_this_week:.1f}",
                "budget_utilization": f"{proj.budget_utilization or 0:.0f}",
                "total_budget": f"{proj.total_budget or 0:,.2f}",
                "calculated_cost": f"{proj.calculated_cost or 0:,.2f}",
            })

        # Build email body
        email_body = _build_weekly_summary_html(manager_name, project_summaries)

        frappe.sendmail(
            recipients=[manager],
            subject="Weekly Project Summary",
            message=email_body,
            now=True,
        )

    frappe.db.commit()


def _build_weekly_summary_html(manager_name, project_summaries):
    """Build the weekly summary email HTML inline (no separate template file)."""
    rows = ""
    for ps in project_summaries:
        overdue_badge = ""
        if ps["overdue_tasks"] > 0:
            overdue_badge = (
                f' <span style="color:#EF4444; font-weight:600;">'
                f'({ps["overdue_tasks"]} overdue)</span>'
            )

        rows += f"""
        <tr>
            <td style="padding:10px; border:1px solid #e5e7eb;">
                <a href="{ps['project_url']}" style="color:#5B4CF5; font-weight:600; text-decoration:none;">
                    {ps['project_name']}
                </a>
            </td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">
                {ps['completed_tasks']} / {ps['total_tasks']}{overdue_badge}
            </td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">
                {ps['hours_this_week']}h
            </td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">
                {ps['budget_utilization']}%
            </td>
        </tr>
        """

    return f"""
    <h3>Weekly Project Summary</h3>
    <p>Hi {manager_name},</p>
    <p>Here is your weekly summary for the past 7 days:</p>
    <table style="border-collapse:collapse; width:100%; max-width:700px;">
        <thead>
            <tr style="background:#f3f4f6;">
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:left;">Project</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Tasks (Done / Total)</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Hours This Week</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Budget Used</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    <p style="margin-top:16px; color:#6b7280; font-size:13px;">
        This is an automated weekly summary from Next PMS.
    </p>
    """
