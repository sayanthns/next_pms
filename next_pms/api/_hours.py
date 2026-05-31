# apps/next_pms/next_pms/api/_hours.py
"""Shared working-hours + target-hours helpers — single source of truth.

All reports (Employee Productivity, AI daily, weekly summary) derive
"how many hours should this user have worked" from here, so numbers stay
consistent. Target = effective working days x configurable hours/day
(default 8). The timer (PMS Time Log.duration_hours) is the only "actual
hours" source; PMS Checkin in/out is NOT used as a baseline.
"""

from datetime import timedelta

import frappe
from frappe.utils import flt, getdate

DEFAULT_WORKING_HOURS_PER_DAY = 8.0


def get_working_hours_per_day():
    """Configured fixed working hours per day. Defaults to 8 when unset/zero."""
    value = frappe.db.get_single_value("PMS AI Settings", "working_hours_per_day")
    hours = flt(value)
    return hours if hours > 0 else DEFAULT_WORKING_HOURS_PER_DAY


def working_days_in_range(from_date, to_date):
    """All non-Sunday dates in [from_date, to_date] (inclusive) as date objects."""
    days = []
    d = getdate(from_date)
    end = getdate(to_date)
    while d <= end:
        if d.weekday() != 6:  # 6 = Sunday
            days.append(d)
        d += timedelta(days=1)
    return days


def get_employee_for_user(user):
    """Active Employee for a user (falls back to any Employee, else None)."""
    employees = frappe.get_all(
        "Employee",
        filters={"user_id": user, "status": "Active"},
        fields=["name", "holiday_list"],
        limit=1,
        ignore_permissions=True,
    )
    if not employees:
        employees = frappe.get_all(
            "Employee",
            filters={"user_id": user},
            fields=["name", "holiday_list"],
            limit=1,
            ignore_permissions=True,
        )
    return employees[0] if employees else None


def get_holiday_dates(holiday_list_name, from_date, to_date):
    """Non-weekly-off holiday dates (str) in range for a holiday list."""
    if not holiday_list_name:
        return set()
    holidays = frappe.get_all(
        "Holiday",
        filters={
            "parent": holiday_list_name,
            "holiday_date": ["between", [str(getdate(from_date)), str(getdate(to_date))]],
            "weekly_off": 0,
        },
        fields=["holiday_date"],
        ignore_permissions=True,
    )
    return {str(h.holiday_date) for h in holidays}


def _get_leave_day_sets(employee_name, from_date, to_date):
    """Return (full_day_dates, half_day_dates) of APPROVED, non-cancelled leave in range.

    Frappe quirk: on cancel, Leave Application keeps status='Approved' but
    docstatus=2 — so we must exclude docstatus 2 explicitly. Half-day leaves
    (`half_day=1`, `half_day_date`) deduct only 0.5 of a working day, so they
    are tracked separately from full-day leave.
    """
    if not employee_name:
        return set(), set()
    leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee_name,
            "status": "Approved",
            "docstatus": ["!=", 2],
            "from_date": ["<=", str(getdate(to_date))],
            "to_date": [">=", str(getdate(from_date))],
        },
        fields=["from_date", "to_date", "half_day", "half_day_date"],
        ignore_permissions=True,
    )
    fd = getdate(from_date)
    td = getdate(to_date)
    full_dates = set()
    half_dates = set()
    for leave in leaves:
        half_str = None
        if leave.half_day and leave.half_day_date:
            hd = getdate(leave.half_day_date)
            if fd <= hd <= td:
                half_str = str(hd)
                half_dates.add(half_str)
        ld = getdate(leave.from_date)
        lt = getdate(leave.to_date)
        while ld <= lt:
            ds = str(ld)
            if fd <= ld <= td and ds != half_str:
                full_dates.add(ds)
            ld += timedelta(days=1)
    # A date marked half-day on any leave never counts as a full leave day.
    full_dates -= half_dates
    return full_dates, half_dates


def get_leave_dates(employee_name, from_date, to_date):
    """Full-day approved-leave dates (str) within range (excludes cancelled + half-days)."""
    full_dates, _half = _get_leave_day_sets(employee_name, from_date, to_date)
    return full_dates


def get_half_leave_dates(employee_name, from_date, to_date):
    """Half-day approved-leave dates (str) within range (excludes cancelled)."""
    _full, half_dates = _get_leave_day_sets(employee_name, from_date, to_date)
    return half_dates


def effective_working_days(user, from_date, to_date):
    """Non-Sunday days minus holidays minus full-day approved leave, as sorted str list.

    Half-day leaves remain in the list (the person is still partly available);
    their 0.5-day deduction is applied in compute_target_hours.
    """
    all_days = {str(d) for d in working_days_in_range(from_date, to_date)}
    employee = get_employee_for_user(user)
    employee_name = employee.name if employee else None
    holiday_list = employee.holiday_list if employee else None
    excused = get_holiday_dates(holiday_list, from_date, to_date) | get_leave_dates(
        employee_name, from_date, to_date
    )
    return sorted(all_days - excused)


def compute_target_hours(user, from_date, to_date):
    """Target hours over a range = effective working days x configured hours/day,
    minus 0.5 day per half-day leave that still falls on a working day."""
    working = set(effective_working_days(user, from_date, to_date))
    employee = get_employee_for_user(user)
    employee_name = employee.name if employee else None
    half_dates = get_half_leave_dates(employee_name, from_date, to_date)
    half_count = len(half_dates & working)
    effective_days = len(working) - 0.5 * half_count
    if effective_days < 0:
        effective_days = 0
    return round(effective_days * get_working_hours_per_day(), 2)


def compute_utilization(logged_hours, target_hours):
    """Utilization % = logged / target * 100. Returns 0.0 when target <= 0."""
    target = flt(target_hours)
    if target <= 0:
        return 0.0
    return round(flt(logged_hours) / target * 100, 1)
