import re
import frappe
from frappe.utils import getdate, today
from datetime import timedelta

from next_pms.api.permissions import is_admin_user, is_manager_user
from next_pms.api._hours import (
    working_days_in_range as _working_days_in_range,
    get_employee_for_user as _get_employee_for_user,
    get_holiday_dates as _get_holiday_dates,
    get_leave_dates as _get_leave_dates,
    compute_target_hours,
    compute_utilization,
    get_working_hours_per_day,
)


def _strip_html(text):
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _get_date_range(period_days):
    to_date = getdate(today())
    if period_days == 0:
        from_date = getdate("2020-01-01")
    else:
        from_date = to_date - timedelta(days=int(period_days) - 1)
    return from_date, to_date


@frappe.whitelist()
def get_employee_productivity(user, period_days=30):
    period_days = int(period_days)
    current_user = frappe.session.user

    is_admin = is_admin_user()
    is_pm = is_manager_user()
    if not (is_admin or is_pm) and user != current_user:
        frappe.throw("Not permitted to view another user's productivity.")

    from_date, to_date = _get_date_range(period_days)
    from_str = str(from_date)
    to_str = str(to_date)

    # ── 1. Attendance ─────────────────────────────────────────────────
    all_non_sunday_days = _working_days_in_range(from_date, to_date)
    all_non_sunday_strs = {str(d) for d in all_non_sunday_days}

    employee = _get_employee_for_user(user)
    employee_name = employee.name if employee else None
    holiday_list_name = employee.holiday_list if employee else None

    holiday_dates = _get_holiday_dates(holiday_list_name, from_date, to_date)
    leave_dates = _get_leave_dates(employee_name, from_date, to_date)

    excused_dates = holiday_dates | leave_dates
    working_day_strs = all_non_sunday_strs - excused_dates
    working_days = sorted(working_day_strs)

    checkins = frappe.get_all(
        "PMS Checkin",
        filters={"user": user, "date": ["between", [from_str, to_str]]},
        fields=["date", "checkin_time", "checkout_time", "total_hours"],
        order_by="date asc",
    )
    checkin_map = {str(c.date): c for c in checkins}
    checked_in_days = set(checkin_map.keys())
    missing_days = sorted(working_day_strs - checked_in_days)

    total_office_hours = round(sum(c.total_hours or 0 for c in checkins), 2)
    avg_hours_per_day = (
        round(total_office_hours / len(checked_in_days), 2) if checked_in_days else 0
    )

    # ── 2. Time logs (timer) per day ──────────────────────────────────
    time_logs = frappe.get_all(
        "PMS Time Log",
        filters={
            "user": user,
            "start_time": ["between", [from_str + " 00:00:00", to_str + " 23:59:59"]],
            "is_running": 0,
        },
        fields=["start_time", "duration_hours", "task"],
    )
    # Group logged hours by date
    logged_by_day = {}
    for tl in time_logs:
        d = str(getdate(tl.start_time))
        logged_by_day[d] = round(logged_by_day.get(d, 0) + (tl.duration_hours or 0), 2)

    total_logged_hours = round(sum(logged_by_day.values()), 2)

    # Fixed-baseline target (configurable 8h x effective working days) — replaces checkin in/out as the baseline
    target_hours = compute_target_hours(user, from_date, to_date)
    utilization_pct = compute_utilization(total_logged_hours, target_hours)

    # ── 3. Day-wise hours summary — baseline is the FIXED daily target (8h),
    #       NOT checkin in/out. Compares timer-logged hours vs target.
    whpd = get_working_hours_per_day()
    # Show every working day plus any day that has logged time (e.g. Sunday work).
    relevant_days = sorted(working_day_strs | set(logged_by_day.keys()))
    day_summary = []
    for d in relevant_days:
        is_working = d in working_day_strs
        target_h = whpd if is_working else 0
        cin = checkin_map.get(d)
        office_h = round(cin.total_hours or 0, 2) if cin else 0
        logged_h = round(logged_by_day.get(d, 0), 2)
        gap_h = round(logged_h - target_h, 2)  # negative = under target
        timer_missing = target_h > 0 and logged_h == 0
        if not is_working:
            status = "off"            # non-working day (Sun/holiday/leave)
        elif logged_h == 0:
            status = "no_timer"
        elif logged_h >= target_h * 0.8:
            status = "good"
        else:
            status = "partial"
        day_summary.append({
            "date": d,
            "target_hours": target_h,
            "office_hours": office_h,   # actual checkin — informational only
            "logged_hours": logged_h,
            "gap_hours": gap_h,
            "timer_missing": timer_missing,
            "status": status,
        })

    timer_missing_days = [d for d in day_summary if d["timer_missing"]]

    # ── 4. Leave & holiday display ────────────────────────────────────
    leaves_in_period = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee_name,
            "status": "Approved",
            "from_date": ["<=", to_str],
            "to_date": [">=", from_str],
        },
        fields=["from_date", "to_date", "leave_type", "total_leave_days"],
    ) if employee_name else []
    leaves_display = [
        {
            "from_date": str(l.from_date),
            "to_date": str(l.to_date),
            "leave_type": l.leave_type,
            "days": l.total_leave_days,
        }
        for l in leaves_in_period
    ]

    holidays_display = []
    if holiday_list_name:
        hols = frappe.get_all(
            "Holiday",
            filters={
                "parent": holiday_list_name,
                "holiday_date": ["between", [from_str, to_str]],
                "weekly_off": 0,
            },
            fields=["holiday_date", "description"],
            order_by="holiday_date asc",
        )
        holidays_display = [
            {"date": str(h.holiday_date), "description": _strip_html(h.description)}
            for h in hols
        ]

    # ── 5. Tasks ──────────────────────────────────────────────────────
    task_fields = [
        "name", "task_title", "project", "status", "priority",
        "estimated_hours", "actual_hours", "due_date", "modified",
        "creation", "assigned_to",
    ]
    meta = frappe.get_meta("PMS Task")
    existing = {f.fieldname for f in meta.fields}
    safe_fields = [f for f in task_fields if f in existing or f in ("name", "creation", "modified")]

    all_tasks = frappe.get_all(
        "PMS Task",
        filters={"assigned_to": user},
        fields=safe_fields,
        limit=0,
    )

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

    # ── 6. Per-project breakdown ──────────────────────────────────────
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

    proj_ids = [p for p in project_map if p != "__no_project__"]
    project_names_map = {}
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
        # efficiency = est/actual (>100% = faster than estimated, <100% = slower)
        pm["efficiency_pct"] = (
            round((pm["estimated_hours"] / pm["actual_hours"]) * 100, 1)
            if pm["actual_hours"] > 0 and pm["estimated_hours"] > 0
            else None
        )
        # completion rate
        pm["completion_pct"] = (
            round(pm["done"] / pm["total"] * 100, 1) if pm["total"] > 0 else 0
        )
        projects_data.append(pm)
    projects_data.sort(key=lambda x: -x["total"])

    # Overall across all projects
    total_estimated = round(sum(t.estimated_hours or 0 for t in all_tasks), 2)
    total_actual = round(sum(t.actual_hours or 0 for t in all_tasks), 2)
    total_tasks = len(all_tasks)
    done_count = sum(1 for t in all_tasks if t.status == "Done")
    in_progress_count = sum(1 for t in all_tasks if t.status in ("In Progress", "In Review"))
    backlog_count = sum(1 for t in all_tasks if t.status in ("Backlog", "To Do"))
    overdue_count = sum(
        1 for t in all_tasks
        if t.due_date and getdate(t.due_date) < to_date and t.status != "Done"
    )

    overall_efficiency_pct = (
        round((total_estimated / total_actual) * 100, 1)
        if total_actual > 0 and total_estimated > 0 else None
    )
    overall_completion_pct = (
        round(done_count / total_tasks * 100, 1) if total_tasks > 0 else 0
    )

    # ── 7. On-time completion ─────────────────────────────────────────
    done_tasks_all = [t for t in all_tasks if t.status == "Done"]
    tasks_with_due = [t for t in done_tasks_all if t.due_date]
    on_time = [t for t in tasks_with_due if getdate(t.modified) <= getdate(t.due_date)]
    on_time_pct = (
        round(len(on_time) / len(tasks_with_due) * 100, 1)
        if tasks_with_due else None
    )

    # ── 8. Recommendations ────────────────────────────────────────────
    recommendations = []
    attendance_pct = (
        round(len(checked_in_days) / len(working_days) * 100, 1)
        if working_days else 100
    )
    if attendance_pct < 70:
        recommendations.append("Low attendance ({:.0f}%). Verify leave records or check-in issues.".format(attendance_pct))
    if len(timer_missing_days) > 2:
        recommendations.append("{} day(s) checked in but no task timer logged. Encourage daily time tracking.".format(len(timer_missing_days)))
    if overdue_count > 0:
        recommendations.append("{} overdue task(s). Review workload and due date accuracy.".format(overdue_count))
    if total_estimated > 0 and total_actual > total_estimated * 1.3:
        recommendations.append("Actual hours exceed estimates by >30%. Improve task time estimation.")
    elif total_estimated > 0 and total_actual < total_estimated * 0.5:
        recommendations.append("Actual hours well under estimates. Tasks may be under-logged or over-estimated.")
    if on_time_pct is not None and on_time_pct < 60:
        recommendations.append("On-time completion rate is low ({:.0f}%). Focus on deadline adherence.".format(on_time_pct))
    if not recommendations:
        recommendations.append("Performance looks good. Attendance, delivery, and time tracking are consistent.")

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
        "total_office_hours": total_office_hours,
        "total_logged_hours": total_logged_hours,
        "avg_hours_per_day": avg_hours_per_day,
        "target_hours": target_hours,
        "utilization_pct": utilization_pct,
        # leave & holidays
        "leaves": leaves_display,
        "holidays": holidays_display,
        "holiday_list": holiday_list_name or "",
        "leave_days_count": len(leave_dates & all_non_sunday_strs),
        "holiday_days_count": len(holiday_dates & all_non_sunday_strs),
        # day-wise hours summary
        "day_summary": day_summary,
        "timer_missing_days": timer_missing_days,
        # task summary
        "total_tasks": total_tasks,
        "done_count": done_count,
        "in_progress_count": in_progress_count,
        "backlog_count": backlog_count,
        "overdue_count": overdue_count,
        "active_in_period": len(period_task_names),
        "total_estimated_hours": total_estimated,
        "total_actual_hours": total_actual,
        "on_time_pct": on_time_pct,
        "overall_efficiency_pct": overall_efficiency_pct,
        "overall_completion_pct": overall_completion_pct,
        # per-project
        "projects": projects_data,
        # recommendations
        "recommendations": recommendations,
    }


@frappe.whitelist()
def get_productivity_users():
    is_admin = is_admin_user()
    is_pm = is_manager_user()

    if is_admin or is_pm:
        # Only internal PMS users — exclude portal customers (PMS Customer) and
        # System Users with no PMS role at all.
        pms_roles = ["Next PMS", "PMS Manager", "PMS Developer", "PMS Viewer"]
        role_rows = frappe.get_all(
            "Has Role",
            filters={"role": ["in", pms_roles], "parenttype": "User"},
            fields=["parent"],
            distinct=True,
        )
        pms_users = {r.parent for r in role_rows}
        cust_rows = frappe.get_all(
            "Has Role",
            filters={"role": "PMS Customer", "parenttype": "User"},
            fields=["parent"],
        )
        customers = {r.parent for r in cust_rows}
        candidates = list(pms_users - customers)
        users = frappe.get_all(
            "User",
            filters={
                "name": ["in", candidates],
                "enabled": 1,
                "user_type": "System User",
            },
            fields=["name", "full_name", "user_image"],
            order_by="full_name asc",
        ) if candidates else []
    else:
        u = frappe.session.user
        info = frappe.get_cached_value("User", u, ["full_name", "user_image"], as_dict=True) or {}
        users = [{"name": u, "full_name": info.get("full_name") or u, "user_image": info.get("user_image")}]

    return users
