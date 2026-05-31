import frappe
from frappe.utils import today, getdate, format_date, add_days, flt
from next_pms.api.permissions import is_admin_user


def _financials_dict(so_value, budget, actual):
    so_value = flt(so_value); budget = flt(budget); actual = flt(actual)
    return {
        "so_value": round(so_value, 2),
        "budget": round(budget, 2),
        "actual": round(actual, 2),
        "budget_util": round(actual / budget * 100, 1) if budget > 0 else 0,
        "so_util": round(actual / so_value * 100, 1) if so_value > 0 else 0,
    }


@frappe.whitelist()
def get_project_financials(project):
    """SO value vs budget vs actual cost for a project."""
    proj = frappe.db.get_value(
        "PMS Project", project,
        ["sales_order", "total_budget", "calculated_cost"], as_dict=True,
    ) or {}
    so_value = 0
    if proj.get("sales_order"):
        so_value = frappe.db.get_value("Sales Order", proj["sales_order"], "grand_total") or 0
    return _financials_dict(so_value, proj.get("total_budget"), proj.get("calculated_cost"))


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

    financials = get_project_financials(project)

    return {
        "financials": financials,
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


### --- Multi-project combined report APIs --- ###


@frappe.whitelist()
def get_multi_project_report_data(projects, date=None):
    """Collect status data for multiple projects. Returns list of per-project data."""
    import json as _json
    if isinstance(projects, str):
        projects = _json.loads(projects)

    if not date:
        date = str(add_days(today(), -1))

    results = []
    totals = {"tasks_done_count": 0, "tasks_in_progress_count": 0, "tasks_new_count": 0,
              "total_tasks": 0, "done_tasks": 0}

    for project_name in projects:
        data = get_project_report_data(project_name, date)
        results.append(data)
        totals["tasks_done_count"] += data["tasks_done_count"]
        totals["tasks_in_progress_count"] += data["tasks_in_progress_count"]
        totals["tasks_new_count"] += data["tasks_new_count"]
        totals["total_tasks"] += data["total_tasks"]
        totals["done_tasks"] += data["done_tasks"]

    totals["progress_pct"] = round((totals["done_tasks"] / totals["total_tasks"] * 100)
                                    if totals["total_tasks"] else 0)

    formatted_date = format_date(str(getdate(date)), "EEEE, d MMMM yyyy")
    return {"projects": results, "totals": totals, "formatted_date": formatted_date,
            "report_date": str(getdate(date))}


@frappe.whitelist()
def send_multi_project_report(projects, recipients, report_name=None, date=None):
    """Generate and email a combined report for multiple projects."""
    import json as _json
    if isinstance(projects, str):
        projects = _json.loads(projects)
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]

    if not recipients:
        frappe.throw("Please provide at least one recipient email.")
    if not projects:
        frappe.throw("Please select at least one project.")

    data = get_multi_project_report_data(projects, date)
    data["report_name"] = report_name or "Project Status Update"

    message = frappe.render_template(
        "next_pms/templates/emails/project_multi_status_report.html",
        data,
    )

    subject = f"{data['report_name']} — {data['formatted_date']}"

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        now=True,
    )

    return {"success": True, "message": f"Combined report sent to {len(recipients)} recipient(s)."}


@frappe.whitelist()
def get_report_configs():
    """Return all saved report configs."""
    configs = frappe.get_all(
        "PMS Report Config",
        fields=["name", "report_name", "recipients", "auto_send", "owner", "modified"],
        order_by="modified desc",
        ignore_permissions=True,
    )

    for c in configs:
        c["projects"] = frappe.get_all(
            "PMS Report Config Project",
            filters={"parent": c["name"]},
            fields=["project"],
            order_by="idx asc",
        )
        # Enrich with project names
        for p in c["projects"]:
            p["project_name"] = frappe.db.get_value("PMS Project", p["project"], "project_name") or p["project"]

    return configs


@frappe.whitelist()
def save_report_config(report_name, projects, recipients, auto_send=False, config_name=None):
    """Create or update a report config."""
    import json as _json
    if isinstance(projects, str):
        projects = _json.loads(projects)
    auto_send = str(auto_send).lower() in ("true", "1", "yes")

    if config_name:
        doc = frappe.get_doc("PMS Report Config", config_name)
        doc.report_name = report_name
        doc.recipients = recipients
        doc.auto_send = 1 if auto_send else 0
        doc.set("projects", [])
        for p in projects:
            doc.append("projects", {"project": p})
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "PMS Report Config",
            "report_name": report_name,
            "recipients": recipients,
            "auto_send": 1 if auto_send else 0,
            "projects": [{"project": p} for p in projects],
        })
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True, "name": doc.name, "report_name": doc.report_name}


@frappe.whitelist()
def delete_report_config(config_name):
    """Delete a saved report config."""
    frappe.delete_doc("PMS Report Config", config_name, ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


def send_scheduled_multi_project_reports():
    """Cron: send combined reports for all configs with auto_send enabled."""
    configs = frappe.get_all(
        "PMS Report Config",
        filters={"auto_send": 1, "recipients": ["is", "set"]},
        fields=["name", "report_name", "recipients"],
    )

    report_date = str(add_days(today(), -1))

    for config in configs:
        projects = frappe.get_all(
            "PMS Report Config Project",
            filters={"parent": config.name},
            pluck="project",
            order_by="idx asc",
        )
        if not projects:
            continue

        recipients = [r.strip() for r in (config.recipients or "").split(",") if r.strip()]
        if not recipients:
            continue

        try:
            send_multi_project_report(projects, recipients, report_name=config.report_name, date=report_date)
        except Exception:
            frappe.log_error(
                f"Failed to send scheduled multi-project report: {config.report_name}",
                "Multi-Project Report Scheduler",
            )


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
