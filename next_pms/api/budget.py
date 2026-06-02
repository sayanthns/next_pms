import random

import frappe
from frappe import _
from frappe.utils import flt
from next_pms.api.permissions import check_project_access

# Default approvers who may raise a project budget without OTP, and who receive the
# OTP when a non-approver requests an increase. Overridable in PMS AI Settings
# (field: budget_approver_emails).
DEFAULT_BUDGET_APPROVERS = ["sayanth@enfono.in", "muhsin@enfono.in"]
# Marker prefix on the thrown error so the frontend can detect "needs OTP" reliably.
BUDGET_OTP_REQUIRED = "BUDGET_OTP_REQUIRED"


def get_budget_approvers():
    """Return the list of approver emails (PMS AI Settings → fallback to defaults)."""
    raw = frappe.db.get_single_value("PMS AI Settings", "budget_approver_emails") or ""
    emails = []
    for part in raw.replace(";", ",").replace("\n", ",").split(","):
        e = part.strip()
        if e and e not in emails:
            emails.append(e)
    return emails or list(DEFAULT_BUDGET_APPROVERS)


def is_budget_approver(user=None):
    user = user or frappe.session.user
    return user in get_budget_approvers()


def _budget_otp_key(project, user):
    return f"pms_budget_otp:{project}:{user}"


@frappe.whitelist()
def request_budget_increase_otp(project, new_budget):
    """Generate a 6-digit OTP and email it to the budget approvers so a non-approver
    can confirm raising this project's Total Budget."""
    check_project_access(project)
    p = frappe.db.get_value(
        "PMS Project", project, ["project_name", "total_budget"], as_dict=True
    )
    if not p:
        frappe.throw(_("Project not found"))

    requester = frappe.session.user
    requester_name = frappe.db.get_value("User", requester, "full_name") or requester
    otp = str(random.randint(100000, 999999))
    # 30-min window: approver email delivery can lag a few minutes, so a 5-min OTP
    # could expire before it even arrives. Wider window keeps it usable.
    frappe.cache.set_value(_budget_otp_key(project, requester), otp, expires_in_sec=1800)

    approvers = get_budget_approvers()
    msg = f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif; max-width:520px;">
      <h3 style="margin:0 0 12px;">Budget Increase Approval</h3>
      <p style="margin:0 0 12px;"><b>{requester_name}</b> ({requester}) wants to raise the
      Total Budget of <b>{p.project_name}</b>.</p>
      <table style="border-collapse:collapse; margin-bottom:16px;">
        <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Current Budget</td>
            <td style="padding:6px 12px; border:1px solid #e5e7eb;">{flt(p.total_budget):,.2f}</td></tr>
        <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Requested Budget</td>
            <td style="padding:6px 12px; border:1px solid #e5e7eb; font-weight:700;">{flt(new_budget):,.2f}</td></tr>
      </table>
      <div style="background:#fef2f2; border-radius:10px; padding:18px; text-align:center;">
        <p style="color:#991b1b; font-size:13px; margin:0 0 8px;">Approval OTP</p>
        <p style="font-size:34px; font-weight:800; letter-spacing:8px; color:#dc2626; margin:0;">{otp}</p>
      </div>
      <p style="color:#6b7280; font-size:12px; margin-top:12px;">Share this code with {requester_name}
      only if you approve the increase. It expires in <b>30 minutes</b>. If you did not expect this, ignore it.</p>
    </div>
    """
    frappe.sendmail(
        recipients=approvers,
        subject=_("Budget increase OTP: {0}").format(p.project_name),
        message=msg, now=True,
    )
    return {"success": True, "message": _("OTP sent to the budget approver(s).")}


def verify_budget_otp(project, otp):
    """Validate the OTP a non-approver supplies to raise a project's budget.
    Raises on missing/expired/invalid; clears the OTP on success."""
    if not otp:
        frappe.throw(_("{0}: Budget increase needs an approver OTP.").format(BUDGET_OTP_REQUIRED))
    key = _budget_otp_key(project, frappe.session.user)
    stored = frappe.cache.get_value(key)
    if not stored:
        frappe.throw(_("{0}: OTP expired — request a new one.").format(BUDGET_OTP_REQUIRED))
    if str(otp).strip() != str(stored).strip():
        frappe.throw(_("{0}: Invalid OTP. Please try again.").format(BUDGET_OTP_REQUIRED))
    frappe.cache.delete_value(key)


# ── Status-change (reopen) OTP — reuses the same approver list ──────────────
STATUS_OTP_REQUIRED = "STATUS_OTP_REQUIRED"


def _status_otp_key(project, user):
    return f"pms_status_otp:{project}:{user}"


@frappe.whitelist()
def request_status_change_otp(project, new_status):
    """Email a 6-digit OTP to the approvers so a non-approver can reopen (move out of
    Completed) a project."""
    check_project_access(project)
    p = frappe.db.get_value(
        "PMS Project", project, ["project_name", "status"], as_dict=True
    )
    if not p:
        frappe.throw(_("Project not found"))

    requester = frappe.session.user
    requester_name = frappe.db.get_value("User", requester, "full_name") or requester
    otp = str(random.randint(100000, 999999))
    frappe.cache.set_value(_status_otp_key(project, requester), otp, expires_in_sec=1800)

    approvers = get_budget_approvers()
    msg = f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif; max-width:520px;">
      <h3 style="margin:0 0 12px;">Reopen Project Approval</h3>
      <p style="margin:0 0 12px;"><b>{requester_name}</b> ({requester}) wants to move
      <b>{p.project_name}</b> from <b>Completed</b> to <b>{frappe.utils.escape_html(str(new_status))}</b>.</p>
      <div style="background:#fef2f2; border-radius:10px; padding:18px; text-align:center;">
        <p style="color:#991b1b; font-size:13px; margin:0 0 8px;">Approval OTP</p>
        <p style="font-size:34px; font-weight:800; letter-spacing:8px; color:#dc2626; margin:0;">{otp}</p>
      </div>
      <p style="color:#6b7280; font-size:12px; margin-top:12px;">Share this code with {requester_name}
      only if you approve reopening this project. It expires in <b>30 minutes</b>.</p>
    </div>
    """
    frappe.sendmail(
        recipients=approvers,
        subject=_("Reopen project OTP: {0}").format(p.project_name),
        message=msg, now=True,
    )
    return {"success": True, "message": _("OTP sent to the approver(s).")}


def verify_status_change_otp(project, otp):
    """Validate the OTP a non-approver supplies to reopen a Completed project."""
    if not otp:
        frappe.throw(_("{0}: Reopening a completed project needs an approver OTP.").format(STATUS_OTP_REQUIRED))
    key = _status_otp_key(project, frappe.session.user)
    stored = frappe.cache.get_value(key)
    if not stored:
        frappe.throw(_("{0}: OTP expired — request a new one.").format(STATUS_OTP_REQUIRED))
    if str(otp).strip() != str(stored).strip():
        frappe.throw(_("{0}: Invalid OTP. Please try again.").format(STATUS_OTP_REQUIRED))
    frappe.cache.delete_value(key)


@frappe.whitelist()
def request_budget_increase(project):
    """Email a budget-increase request to the approver (sayanth@enfono.in)."""
    check_project_access(project)
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
