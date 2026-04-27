import frappe
from frappe.utils import getdate, add_days, today, date_diff
from datetime import date, timedelta

from next_pms.api.permissions import is_admin_user, is_manager_user


def _get_date_range(period_days):
    """Return (from_date, to_date). period_days=0 means all-time."""
    to_date = getdate(today())
    if period_days == 0:
        from_date = getdate("2020-01-01")
    else:
        from_date = to_date - timedelta(days=int(period_days) - 1)
    return from_date, to_date


def _working_days_in_range(from_date, to_date):
    """List of dates in range that are NOT Sunday (weekday != 6)."""
    days = []
    d = from_date
    while d <= to_date:
        if d.weekday() != 6:  # 6 = Sunday
            days.append(d)
        d += timedelta(days=1)
    return days


@frappe.whitelist()
def get_employee_productivity(user, period_days=30):
    """
    Return comprehensive productivity data for a given user over a period.
    period_days: 5 | 10 | 30 | 45 | 60 | 90 | 0 (all-time)
    """
    period_days = int(period_days)
    current_user = frappe.session.user

    # Access control: developer can only view their own
    is_admin = is_admin_user()
    is_pm = is_manager_user()
    if not (is_admin or is_pm) and user != current_user:
        frappe.throw("Not permitted to view another user's productivity.")

    from_date, to_date = _get_date_range(period_days)
    from_str = str(from_date)
    to_str = str(to_date)

    # ── 1. Attendance ────────────────────────────────────────────────
    working_days = _working_days_in_range(from_date, to_date)
    working_day_strs = {str(d) for d in working_days}

    checkins = frappe.get_all(
        "PMS Checkin",
        filters={"user": user, "date": ["between", [from_str, to_str]]},
        fields=["date", "checkin_time", "checkout_time", "total_hours"],
    )
    checked_in_days = {str(c.date) for c in checkins}
    missing_days = sorted(working_day_strs - checked_in_days)

    total_hours_logged = round(sum(c.total_hours or 0 for c in checkins), 2)
    avg_hours_per_day = (
        round(total_hours_logged / len(checked_in_days), 2) if checked_in_days else 0
    )

    # ── 2. Tasks ─────────────────────────────────────────────────────
    # Tasks where this user is assigned_to and modified/created in range
    task_fields = [
        "name", "task_title", "project", "status", "priority",
        "estimated_hours", "actual_hours", "due_date", "modified",
        "creation", "assigned_to",
    ]
    meta = frappe.get_meta("PMS Task")
    existing = {f.fieldname for f in meta.fields}
    safe_fields = [f for f in task_fields if f in existing or f in ("name", "creation", "modified")]

    # All active tasks assigned to user (no date filter — ongoing)
    all_tasks = frappe.get_all(
        "PMS Task",
        filters={"assigned_to": user},
        fields=safe_fields,
        limit=0,
    )

    # Tasks modified within period (gives activity picture)
    period_tasks = frappe.get_all(
        "PMS Task",
        filters={
            "assigned_to": user,
            "modified": ["between", [from_str + " 00:00:00", to_str + " 23:59:59"]],
        },
        fields=safe_fields,
        limit=0,
    )
    period_task_names = {t.name for t in period_tasks}

    # ── 3. Per-project breakdown ──────────────────────────────────────
    project_map = {}
    for t in all_tasks:
        proj = t.project or "__no_project__"
        if proj not in project_map:
            project_map[proj] = {
                "project": proj,
                "project_name": proj,
                "total": 0, "done": 0, "in_progress": 0, "overdue": 0,
                "estimated_hours": 0.0, "actual_hours": 0.0,
            }
        pm = project_map[proj]
        pm["total"] += 1
        pm["estimated_hours"] += t.estimated_hours or 0
        pm["actual_hours"] += t.actual_hours or 0
        if t.status == "Done":
            pm["done"] += 1
        elif t.status in ("In Progress", "In Review"):
            pm["in_progress"] += 1
        if t.due_date and getdate(t.due_date) < to_date and t.status != "Done":
            pm["overdue"] += 1

    # Enrich project names
    project_names_map = {}
    proj_ids = [p for p in project_map if p != "__no_project__"]
    if proj_ids:
        projs = frappe.get_all(
            "PMS Project",
            filters={"name": ["in", proj_ids]},
            fields=["name", "project_name"],
        )
        project_names_map = {p.name: p.project_name for p in projs}

    projects_data = []
    for proj, pm in project_map.items():
        if proj != "__no_project__":
            pm["project_name"] = project_names_map.get(proj, proj)
        pm["estimated_hours"] = round(pm["estimated_hours"], 2)
        pm["actual_hours"] = round(pm["actual_hours"], 2)
        pm["efficiency_pct"] = (
            round((pm["estimated_hours"] / pm["actual_hours"]) * 100, 1)
            if pm["actual_hours"] > 0
            else None
        )
        projects_data.append(pm)
    projects_data.sort(key=lambda x: -x["total"])

    # ── 4. On-time completion ─────────────────────────────────────────
    done_tasks_all = [t for t in all_tasks if t.status == "Done"]
    tasks_with_due = [t for t in done_tasks_all if t.due_date]
    on_time = [t for t in tasks_with_due if getdate(t.modified) <= getdate(t.due_date)]
    on_time_pct = (
        round(len(on_time) / len(tasks_with_due) * 100, 1)
        if tasks_with_due else None
    )

    # ── 5. Overall task summary ───────────────────────────────────────
    total_tasks = len(all_tasks)
    done_count = sum(1 for t in all_tasks if t.status == "Done")
    in_progress_count = sum(1 for t in all_tasks if t.status in ("In Progress", "In Review"))
    backlog_count = sum(1 for t in all_tasks if t.status in ("Backlog", "To Do"))
    overdue_count = sum(
        1 for t in all_tasks
        if t.due_date and getdate(t.due_date) < to_date and t.status != "Done"
    )
    total_estimated = round(sum(t.estimated_hours or 0 for t in all_tasks), 2)
    total_actual = round(sum(t.actual_hours or 0 for t in all_tasks), 2)
    active_in_period = len(period_task_names)

    # ── 6. Recommendation ────────────────────────────────────────────
    recommendations = []
    attendance_pct = (
        round(len(checked_in_days) / len(working_days) * 100, 1)
        if working_days else 100
    )
    if attendance_pct < 70:
        recommendations.append("Low attendance ({:.0f}%). Verify leave records or check-in issues.".format(attendance_pct))
    if overdue_count > 0:
        recommendations.append("{} overdue task(s). Review workload and due date accuracy.".format(overdue_count))
    if total_estimated > 0 and total_actual > total_estimated * 1.3:
        recommendations.append("Actual hours exceed estimates by >30%. Improve task time estimation.")
    elif total_estimated > 0 and total_actual < total_estimated * 0.5:
        recommendations.append("Actual hours are well under estimates. Tasks may be under-logged or over-estimated.")
    if on_time_pct is not None and on_time_pct < 60:
        recommendations.append("On-time completion rate is low ({:.0f}%). Focus on deadline adherence.".format(on_time_pct))
    if not recommendations:
        if on_time_pct is not None and on_time_pct >= 80 and attendance_pct >= 80:
            recommendations.append("Good performance. High attendance and on-time delivery.")
        else:
            recommendations.append("Productivity looks acceptable. Continue consistent check-ins and task updates.")

    user_info = frappe.get_cached_value("User", user, ["full_name", "user_image"], as_dict=True) or {}

    return {
        "user": user,
        "user_full_name": user_info.get("full_name") or user,
        "user_image": user_info.get("user_image"),
        "period_days": period_days,
        "from_date": from_str,
        "to_date": to_str,
        # attendance
        "working_days_count": len(working_days),
        "checked_in_days_count": len(checked_in_days),
        "missing_days": missing_days,
        "attendance_pct": attendance_pct,
        "total_hours_logged": total_hours_logged,
        "avg_hours_per_day": avg_hours_per_day,
        # task summary
        "total_tasks": total_tasks,
        "done_count": done_count,
        "in_progress_count": in_progress_count,
        "backlog_count": backlog_count,
        "overdue_count": overdue_count,
        "active_in_period": active_in_period,
        "total_estimated_hours": total_estimated,
        "total_actual_hours": total_actual,
        "on_time_pct": on_time_pct,
        # per-project
        "projects": projects_data,
        # recommendations
        "recommendations": recommendations,
    }


@frappe.whitelist()
def get_productivity_users():
    """Return list of users the current user is allowed to see productivity for."""
    is_admin = is_admin_user()
    is_pm = is_manager_user()

    if is_admin or is_pm:
        users = frappe.get_all(
            "User",
            filters={"enabled": 1, "user_type": "System User"},
            fields=["name", "full_name", "user_image"],
            order_by="full_name asc",
        )
    else:
        u = frappe.session.user
        info = frappe.get_cached_value("User", u, ["full_name", "user_image"], as_dict=True) or {}
        users = [{"name": u, "full_name": info.get("full_name") or u, "user_image": info.get("user_image")}]

    return users
