import frappe
from frappe import _
from frappe.utils import flt
from next_pms.api.permissions import check_project_access


@frappe.whitelist()
def request_budget_increase(project):
    """Email a budget-increase request to the approver (sayanth@enfono.in)."""
    APPROVER = "sayanth@enfono.in"
    p = frappe.db.get_value(
        "PMS Project", project,
        ["project_name", "total_budget", "calculated_cost", "budget_utilization"],
        as_dict=True,
    )
    if not p:
        frappe.throw(_("Project not found"))
    requester = frappe.session.user
    requester_name = frappe.db.get_value("User", requester, "full_name") or requester
    msg = (
        "<h3>Budget Increase Request</h3>"
        f"<p><b>{requester_name}</b> ({requester}) requests a budget increase.</p>"
        "<table style='border-collapse:collapse;'>"
        f"<tr><td style='padding:6px 12px; border:1px solid #e5e7eb;'>Project</td><td style='padding:6px 12px; border:1px solid #e5e7eb;'>{p.project_name}</td></tr>"
        f"<tr><td style='padding:6px 12px; border:1px solid #e5e7eb;'>Current Budget</td><td style='padding:6px 12px; border:1px solid #e5e7eb;'>{flt(p.total_budget):,.2f}</td></tr>"
        f"<tr><td style='padding:6px 12px; border:1px solid #e5e7eb;'>Actual Cost</td><td style='padding:6px 12px; border:1px solid #e5e7eb;'>{flt(p.calculated_cost):,.2f}</td></tr>"
        f"<tr><td style='padding:6px 12px; border:1px solid #e5e7eb;'>Utilisation</td><td style='padding:6px 12px; border:1px solid #e5e7eb;'>{flt(p.budget_utilization):.0f}%</td></tr>"
        "</table>"
        "<p>Raise the Total Budget on the project to unblock time logging.</p>"
    )
    frappe.sendmail(
        recipients=[APPROVER],
        subject=_("Budget increase request: {0}").format(p.project_name),
        message=msg, now=True,
    )
    return {"success": True, "message": _("Request sent to {0}").format(APPROVER)}


@frappe.whitelist()
def recalculate_project_budget(project):
    """Force recalculation of all budget figures for a project."""
    check_project_access(project)
    project_doc = frappe.get_doc("PMS Project", project)

    # Recalculate all task costs
    tasks = frappe.get_all(
        "PMS Task",
        filters={"project": project},
        fields=["name"],
    )

    for task_data in tasks:
        task = frappe.get_doc("PMS Task", task_data.name)
        task.calculate_actual_hours()
        task.calculate_task_cost()
        task.db_update()

    # Recalculate project cost
    project_doc.calculate_project_cost()
    project_doc.db_update()
    frappe.db.commit()

    return {
        "calculated_cost": project_doc.calculated_cost,
        "budget_utilization": project_doc.budget_utilization,
        "total_budget": project_doc.total_budget,
        "remaining": flt(project_doc.total_budget) - flt(project_doc.calculated_cost),
    }


@frappe.whitelist()
def get_budget_forecast(project):
    """Forecast project budget based on current burn rate."""
    check_project_access(project)
    project_doc = frappe.get_doc("PMS Project", project)

    # Calculate daily burn rate
    from frappe.utils import getdate, date_diff, today

    if not project_doc.start_date:
        return {"error": "Project has no start date"}

    days_elapsed = date_diff(today(), project_doc.start_date)
    if days_elapsed <= 0:
        days_elapsed = 1

    daily_burn_rate = flt(project_doc.calculated_cost) / days_elapsed

    # Calculate projected total cost
    total_days = (
        date_diff(project_doc.end_date, project_doc.start_date)
        if project_doc.end_date
        else days_elapsed * 2
    )
    projected_cost = daily_burn_rate * total_days

    # Calculate days until budget exhausted
    remaining_budget = flt(project_doc.total_budget) - flt(project_doc.calculated_cost)
    days_until_exhausted = (
        int(remaining_budget / daily_burn_rate) if daily_burn_rate > 0 else None
    )

    return {
        "daily_burn_rate": round(daily_burn_rate, 2),
        "projected_total_cost": round(projected_cost, 2),
        "days_until_budget_exhausted": days_until_exhausted,
        "remaining_budget": round(remaining_budget, 2),
        "on_track": (
            projected_cost <= flt(project_doc.total_budget)
            if project_doc.total_budget
            else True
        ),
    }


@frappe.whitelist()
def get_cost_breakdown(project):
    """Get detailed cost breakdown by team member and task type."""
    check_project_access(project)
    # By team member
    member_costs = frappe.db.sql(
        """
        SELECT
            t.assigned_to as member,
            COUNT(t.name) as task_count,
            SUM(t.actual_hours) as total_hours,
            SUM(t.calculated_cost) as total_cost
        FROM `tabPMS Task` t
        WHERE t.project = %s AND t.assigned_to IS NOT NULL AND t.assigned_to != ''
        GROUP BY t.assigned_to
        ORDER BY total_cost DESC
    """,
        project,
        as_dict=True,
    )

    # By task type
    type_costs = frappe.db.sql(
        """
        SELECT
            t.task_type as type,
            COUNT(t.name) as task_count,
            SUM(t.actual_hours) as total_hours,
            SUM(t.calculated_cost) as total_cost
        FROM `tabPMS Task` t
        WHERE t.project = %s AND t.task_type IS NOT NULL AND t.task_type != ''
        GROUP BY t.task_type
        ORDER BY total_cost DESC
    """,
        project,
        as_dict=True,
    )

    # By sprint
    sprint_costs = frappe.db.sql(
        """
        SELECT
            COALESCE(s.sprint_name, 'No Sprint') as sprint_name,
            COUNT(t.name) as task_count,
            SUM(t.actual_hours) as total_hours,
            SUM(t.calculated_cost) as total_cost
        FROM `tabPMS Task` t
        LEFT JOIN `tabPMS Sprint` s ON t.sprint = s.name
        WHERE t.project = %s
        GROUP BY t.sprint
        ORDER BY total_cost DESC
    """,
        project,
        as_dict=True,
    )

    return {
        "by_member": member_costs,
        "by_type": type_costs,
        "by_sprint": sprint_costs,
    }
