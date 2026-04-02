import frappe
from frappe.utils import today, getdate, format_date, add_days
from next_pms.api.permissions import is_admin_user


@frappe.whitelist()
def get_project_report_data(project, date=None):
    """Collect project status data for a given date. Returns dict for template rendering."""
    if not date:
        date = today()

    report_date = str(getdate(date))

    # Project info
    proj = frappe.get_doc("PMS Project", project)

    # Tasks completed on this date (status = Done, modified on report_date)
    tasks_done = frappe.get_all(
        "PMS Task",
        filters={
            "project": project,
            "status": "Done",
            "modified": ["between", [f"{report_date} 00:00:00", f"{report_date} 23:59:59"]],
        },
        fields=["name", "task_title", "assigned_to", "priority"],
        order_by="modified desc",
    )

    # Enrich with assignee names
    for t in tasks_done:
        if t.assigned_to:
            t["assignee_name"] = frappe.db.get_value("User", t.assigned_to, "full_name") or t.assigned_to

    # Tasks currently in progress
    tasks_in_progress = frappe.get_all(
        "PMS Task",
        filters={
            "project": project,
            "status": ["in", ["In Progress", "In Review"]],
        },
        fields=["name", "task_title", "assigned_to", "status", "priority"],
        order_by="modified desc",
    )

    for t in tasks_in_progress:
        if t.assigned_to:
            t["assignee_name"] = frappe.db.get_value("User", t.assigned_to, "full_name") or t.assigned_to

    # New tasks created on this date
    tasks_new = frappe.get_all(
        "PMS Task",
        filters={
            "project": project,
            "creation": ["between", [f"{report_date} 00:00:00", f"{report_date} 23:59:59"]],
        },
        fields=["name", "task_title", "priority", "status"],
        order_by="creation desc",
    )

    # Overall progress
    total_tasks = frappe.db.count("PMS Task", {"project": project})
    done_tasks = frappe.db.count("PMS Task", {"project": project, "status": "Done"})
    progress_pct = round((done_tasks / total_tasks * 100) if total_tasks else 0)

    return {
        "project_name": proj.project_name,
        "project_status": proj.status,
        "client": proj.client,
        "report_date": report_date,
        "formatted_date": format_date(report_date, "EEEE, d MMMM yyyy"),
        "tasks_done": tasks_done,
        "tasks_done_count": len(tasks_done),
        "tasks_in_progress": tasks_in_progress,
        "tasks_in_progress_count": len(tasks_in_progress),
        "tasks_new": tasks_new,
        "tasks_new_count": len(tasks_new),
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "progress_pct": progress_pct,
    }


@frappe.whitelist()
def send_project_report(project, recipients, date=None):
    """Generate and email the project status report to specified recipients."""
    if isinstance(recipients, str):
        # Could be comma-separated or JSON
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]

    if not recipients:
        frappe.throw("Please provide at least one recipient email.")

    data = get_project_report_data(project, date)

    message = frappe.render_template(
        "next_pms/templates/emails/project_status_report.html",
        data,
    )

    subject = f"{data['project_name']} — Status Update ({data['formatted_date']})"

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        now=True,
    )

    return {
        "success": True,
        "message": f"Report sent to {len(recipients)} recipient(s).",
    }


@frappe.whitelist()
def get_project_report_recipients(project):
    """Return suggested recipients for the project report."""
    proj = frappe.get_doc("PMS Project", project)
    suggestions = []

    # Project's saved report recipients
    if proj.get("report_recipients"):
        for r in proj.report_recipients.split(","):
            r = r.strip()
            if r:
                suggestions.append(r)

    # Client contacts (primary email from Customer)
    if proj.client:
        # Get linked contacts with email
        contacts = frappe.get_all(
            "Dynamic Link",
            filters={
                "link_doctype": "Customer",
                "link_name": proj.client,
                "parenttype": "Contact",
            },
            fields=["parent"],
        )
        for c in contacts:
            email = frappe.db.get_value("Contact", c.parent, "email_id")
            if email and email not in suggestions:
                suggestions.append(email)

    # Portal access users
    portal_users = frappe.get_all(
        "PMS Client Portal Access",
        filters={"project": project},
        pluck="client_email",
    )
    for email in portal_users:
        if email and email not in suggestions:
            suggestions.append(email)

    return suggestions


def send_scheduled_project_reports():
    """Cron job: send daily reports for all active projects with auto_send_report enabled."""
    projects = frappe.get_all(
        "PMS Project",
        filters={
            "status": "Active",
            "auto_send_report": 1,
            "report_recipients": ["is", "set"],
        },
        fields=["name", "project_name", "report_recipients"],
    )

    report_date = str(add_days(today(), -1))  # Yesterday's report

    for proj in projects:
        recipients = [r.strip() for r in (proj.report_recipients or "").split(",") if r.strip()]
        if not recipients:
            continue

        try:
            send_project_report(proj.name, recipients, date=report_date)
        except Exception:
            frappe.log_error(
                f"Failed to send scheduled report for {proj.project_name}",
                "Project Report Scheduler",
            )
