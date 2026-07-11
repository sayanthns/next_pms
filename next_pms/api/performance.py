# apps/next_pms/next_pms/api/performance.py
"""Composite Performance Score — management-only evaluation metric.

Combines 8 dimensions (delivery, timeliness, efficiency, utilization,
plan adherence, quality, consistency, attendance) into one weighted
0-100 score. Every dimension is leave/holiday adjusted via the shared
helpers in next_pms.api._hours so nobody is penalised for approved
absence. Dimensions with no underlying data in the window are EXCLUDED
and the remaining weights renormalised — a person with no completed
tasks is not scored 0 on timeliness, they are simply not scored on it.

Weights are fixed in code for v1 (single source of truth, auditable).
A PMS Performance Settings doctype can replace WEIGHTS later without
changing the formulas.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate

from next_pms.api._hours import (
    compute_target_hours,
    compute_utilization,
    effective_working_days,
    get_working_hours_per_day,
)
from next_pms.api.permissions import is_admin_user, is_manager_user
from next_pms.api.productivity import _get_date_range

# Dimension weights (must sum to 100). Rationale documented in the
# Performance tab's methodology section — keep both in sync.
WEIGHTS = {
    "delivery": 25,      # output volume, weighted by PM-approved estimates
    "timeliness": 15,    # on-time completion of due-dated tasks
    "utilization": 15,   # logged hours vs leave-adjusted target
    "plan_adherence": 15,  # hours on Weekly-Plan-committed projects vs planned
    "efficiency": 10,    # estimate accuracy (capped — no sandbagging reward)
    "quality": 10,       # 1 - reopen rate of completed tasks
    "consistency": 5,    # steady daily logging vs binge logging
    "attendance": 5,     # check-in presence on effective working days
}

EFFICIENCY_CAP = 120.0  # >120% est/actual scores as 120 (anti-sandbagging)

BANDS = [(85, "A"), (70, "B"), (50, "C"), (0, "D")]


def _band(score):
    for cutoff, letter in BANDS:
        if score >= cutoff:
            return letter
    return "D"


def _reopened_task_names(task_names):
    """Tasks whose status ever moved FROM 'Done' back to something else,
    detected via Frappe Version history. Rework signal for the quality
    dimension."""
    if not task_names:
        return set()
    versions = frappe.get_all(
        "Version",
        filters={
            "ref_doctype": "PMS Task",
            "docname": ["in", task_names],
            "data": ["like", '%"status"%'],
        },
        fields=["docname", "data"],
        limit=0,
        ignore_permissions=True,
    )
    reopened = set()
    for v in versions:
        if v.docname in reopened:
            continue
        try:
            changed = json.loads(v.data).get("changed") or []
        except Exception:
            continue
        for row in changed:
            # row = [fieldname, old_value, new_value]
            if len(row) >= 3 and row[0] == "status" and row[1] == "Done" and row[2] != "Done":
                reopened.add(v.docname)
                break
    return reopened


def _plan_adherence(user, from_date, to_date, logged_by_project):
    """Actual hours on Weekly-Plan-committed projects vs planned hours,
    across all published Weekly Plans overlapping the window. Returns
    (pct or None, planned_hours, actual_on_planned)."""
    plans = frappe.get_all(
        "Weekly Plan",
        filters={
            "published": 1,
            "week_start": ["<=", str(to_date)],
            "week_end": [">=", str(from_date)],
        },
        pluck="name",
        ignore_permissions=True,
    )
    if not plans:
        return None, 0.0, 0.0
    allocations = frappe.get_all(
        "Weekly Plan Allocation",
        filters={"parent": ["in", plans], "member": user},
        fields=["project", "planned_hours"],
        ignore_permissions=True,
    )
    planned = round(sum(flt(a.planned_hours) for a in allocations), 2)
    if planned <= 0:
        return None, 0.0, 0.0
    planned_projects = {a.project for a in allocations if a.project}
    actual = round(
        sum(h for p, h in logged_by_project.items() if p in planned_projects), 2
    )
    return round(min(actual / planned, 1.0) * 100, 1), planned, actual


def _resolve_window(period_days, from_date=None, to_date=None):
    """Explicit [from_date, to_date] wins over rolling period_days."""
    if from_date and to_date:
        fd, td = getdate(from_date), getdate(to_date)
        if fd > td:
            frappe.throw(_("From Date must be on or before To Date."))
        return fd, td
    return _get_date_range(int(period_days))


@frappe.whitelist()
def get_performance_score(user, period_days=30, from_date=None, to_date=None):
    """Composite performance score for one employee. Management-only.
    Window = explicit from_date/to_date if both given, else rolling
    period_days ending today."""
    if not (is_admin_user() or is_manager_user()):
        frappe.throw(_("Performance scores are visible to management only."))

    fd, td = _resolve_window(period_days, from_date, to_date)
    out = _compute_score(user, fd, td)
    out["period_days"] = int(period_days)
    return out


def _compute_score(user, from_date, to_date):
    """Scoring engine — no permission gate (callers gate). Also used by
    the leaderboard endpoint and the monthly performance email cron."""
    from_str, to_str = str(from_date), str(to_date)

    # ── Shared bases ──────────────────────────────────────────────────
    working_day_strs = set(effective_working_days(user, from_date, to_date))
    target_hours = compute_target_hours(user, from_date, to_date)
    whpd = get_working_hours_per_day()

    time_logs = frappe.get_all(
        "PMS Time Log",
        filters={
            "user": user,
            "start_time": ["between", [from_str + " 00:00:00", to_str + " 23:59:59"]],
            "is_running": 0,
        },
        fields=["start_time", "duration_hours", "task"],
        limit=0,
        ignore_permissions=True,
    )
    logged_by_day = {}
    hours_by_task = {}
    for tl in time_logs:
        d = str(getdate(tl.start_time))
        logged_by_day[d] = logged_by_day.get(d, 0) + flt(tl.duration_hours)
        if tl.task:
            hours_by_task[tl.task] = hours_by_task.get(tl.task, 0) + flt(tl.duration_hours)
    total_logged = round(sum(logged_by_day.values()), 2)

    worked_tasks = (
        frappe.get_all(
            "PMS Task",
            filters={"name": ["in", list(hours_by_task)]},
            fields=["name", "project", "status", "estimated_hours", "due_date", "modified"],
            limit=0,
            ignore_permissions=True,
        )
        if hours_by_task
        else []
    )
    logged_by_project = {}
    for t in worked_tasks:
        if t.project:
            logged_by_project[t.project] = round(
                logged_by_project.get(t.project, 0) + hours_by_task.get(t.name, 0), 2
            )

    # Tasks completed in the window (Done + last modified inside window —
    # same proxy the weekly email uses; PMS Task has no completion_date).
    completed = [
        t for t in worked_tasks
        if t.status == "Done" and from_date <= getdate(t.modified) <= to_date
    ]

    dimensions = {}

    # ── 1. Delivery: estimated hours of completed tasks vs target ─────
    if target_hours > 0:
        delivered_est = round(sum(flt(t.estimated_hours) for t in completed), 2)
        dimensions["delivery"] = {
            "score": round(min(delivered_est / target_hours, 1.0) * 100, 1),
            "raw": f"{delivered_est}h est. delivered / {target_hours}h target",
        }

    # ── 2. Timeliness: on-time completions ────────────────────────────
    with_due = [t for t in completed if t.due_date]
    if with_due:
        on_time = sum(1 for t in with_due if getdate(t.modified) <= getdate(t.due_date))
        dimensions["timeliness"] = {
            "score": round(on_time / len(with_due) * 100, 1),
            "raw": f"{on_time}/{len(with_due)} due-dated tasks on time",
        }

    # ── 3. Utilization: logged vs leave-adjusted target ───────────────
    if target_hours > 0:
        util = compute_utilization(total_logged, target_hours)
        dimensions["utilization"] = {
            "score": round(min(util, 100.0), 1),
            "raw": f"{total_logged}h logged / {target_hours}h target ({util}%)",
        }

    # ── 4. Plan adherence: hours on committed projects vs planned ─────
    plan_pct, planned_h, actual_on_planned = _plan_adherence(
        user, from_date, to_date, logged_by_project
    )
    if plan_pct is not None:
        dimensions["plan_adherence"] = {
            "score": plan_pct,
            "raw": f"{actual_on_planned}h on planned projects / {planned_h}h planned",
        }

    # ── 5. Efficiency: est/actual on worked tasks, capped ─────────────
    est_worked = round(sum(flt(t.estimated_hours) for t in worked_tasks), 2)
    if est_worked > 0 and total_logged > 0:
        eff = min(est_worked / total_logged * 100, EFFICIENCY_CAP)
        dimensions["efficiency"] = {
            "score": round(eff / EFFICIENCY_CAP * 100, 1),
            "raw": f"{est_worked}h est. / {total_logged}h actual "
                   f"({round(est_worked / total_logged * 100, 1)}%, capped {EFFICIENCY_CAP:.0f}%)",
        }

    # ── 6. Quality: 1 - reopen rate ────────────────────────────────────
    if completed:
        reopened = _reopened_task_names([t.name for t in completed])
        dimensions["quality"] = {
            "score": round((1 - len(reopened) / len(completed)) * 100, 1),
            "raw": f"{len(reopened)}/{len(completed)} completed tasks reopened",
        }

    # ── 7. Consistency: days with >=50% of daily target logged ────────
    if working_day_strs:
        threshold = whpd * 0.5
        steady = sum(
            1 for d in working_day_strs if flt(logged_by_day.get(d, 0)) >= threshold
        )
        dimensions["consistency"] = {
            "score": round(steady / len(working_day_strs) * 100, 1),
            "raw": f"{steady}/{len(working_day_strs)} working days with >={threshold:.0f}h logged",
        }

    # ── 8. Attendance: check-in presence ──────────────────────────────
    if working_day_strs:
        checkins = frappe.get_all(
            "PMS Checkin",
            filters={"user": user, "date": ["between", [from_str, to_str]]},
            fields=["date"],
            ignore_permissions=True,
        )
        checked = {str(c.date) for c in checkins} & working_day_strs
        dimensions["attendance"] = {
            "score": round(len(checked) / len(working_day_strs) * 100, 1),
            "raw": f"{len(checked)}/{len(working_day_strs)} working days checked in",
        }

    # ── Composite: renormalise over included dimensions ────────────────
    included_weight = sum(WEIGHTS[k] for k in dimensions)
    composite = (
        round(
            sum(WEIGHTS[k] * dimensions[k]["score"] for k in dimensions)
            / included_weight,
            1,
        )
        if included_weight
        else 0.0
    )

    rows = []
    for key in WEIGHTS:  # stable display order
        dim = dimensions.get(key)
        rows.append({
            "key": key,
            "weight": WEIGHTS[key],
            "included": dim is not None,
            "score": dim["score"] if dim else None,
            "raw": dim["raw"] if dim else "No data in period — excluded",
            "weighted": round(WEIGHTS[key] * dim["score"] / included_weight, 1)
            if dim and included_weight else None,
        })

    user_info = frappe.get_cached_value(
        "User", user, ["full_name", "user_image"], as_dict=True
    ) or {}

    return {
        "user": user,
        "user_full_name": user_info.get("full_name") or user,
        "user_image": user_info.get("user_image"),
        "from_date": from_str,
        "to_date": to_str,
        "composite_score": composite,
        "band": _band(composite),
        "included_weight": included_weight,
        "dimensions": rows,
        "target_hours": target_hours,
        "total_logged_hours": total_logged,
        "working_days_count": len(working_day_strs),
        "completed_count": len(completed),
        "worked_task_count": len(worked_tasks),
    }


def _pms_member_users():
    """Enabled internal PMS users (same population as the productivity
    user picker): has a PMS role, not a portal customer, System User."""
    pms_roles = ["Next PMS", "PMS Manager", "PMS Developer", "PMS Viewer"]
    role_rows = frappe.get_all(
        "Has Role",
        filters={"role": ["in", pms_roles], "parenttype": "User"},
        fields=["parent"],
        distinct=True,
        ignore_permissions=True,
    )
    pms_users = {r.parent for r in role_rows}
    cust_rows = frappe.get_all(
        "Has Role",
        filters={"role": "PMS Customer", "parenttype": "User"},
        fields=["parent"],
        ignore_permissions=True,
    )
    candidates = list(pms_users - {r.parent for r in cust_rows})
    if not candidates:
        return []
    return frappe.get_all(
        "User",
        filters={"name": ["in", candidates], "enabled": 1, "user_type": "System User"},
        pluck="name",
        ignore_permissions=True,
    )


def compute_team_performance(from_date, to_date):
    """Score every PMS member over [from_date, to_date], ranked by
    composite desc. Internal — no permission gate; callers gate.
    Members with zero scorable data (included_weight == 0) are listed
    unranked at the bottom rather than shown as rank-worthy zeros."""
    rows = []
    for user in _pms_member_users():
        try:
            s = _compute_score(user, getdate(from_date), getdate(to_date))
        except Exception:
            frappe.log_error(
                title=f"Team performance scoring failed for {user}",
                message=frappe.get_traceback(),
            )
            continue
        rows.append({
            "user": s["user"],
            "full_name": s["user_full_name"],
            "user_image": s["user_image"],
            "composite_score": s["composite_score"],
            "band": s["band"],
            "included_weight": s["included_weight"],
            "target_hours": s["target_hours"],
            "total_logged_hours": s["total_logged_hours"],
            "completed_count": s["completed_count"],
            "dimensions": {d["key"]: d["score"] for d in s["dimensions"] if d["included"]},
        })
    scored = sorted(
        (r for r in rows if r["included_weight"] > 0),
        key=lambda r: r["composite_score"],
        reverse=True,
    )
    unscored = [r for r in rows if r["included_weight"] == 0]
    for i, r in enumerate(scored, start=1):
        r["rank"] = i
    for r in unscored:
        r["rank"] = None
    return scored + unscored


@frappe.whitelist()
def get_team_performance(period_days=30, from_date=None, to_date=None):
    """Ranked leaderboard of all PMS members. Management-only."""
    if not (is_admin_user() or is_manager_user()):
        frappe.throw(_("Performance scores are visible to management only."))
    fd, td = _resolve_window(period_days, from_date, to_date)
    return {
        "from_date": str(fd),
        "to_date": str(td),
        "rows": compute_team_performance(fd, td),
    }
