# Copyright (c) 2026, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, flt
from next_pms.api.weekly_plan import get_plan_for_date

STATUS_ON_PLAN = "On Plan"
STATUS_UNPLANNED = "Unplanned"
STATUS_NOT_STARTED = "Not Started"


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 180},
        {"label": _("Person"), "fieldname": "person", "fieldtype": "Data", "width": 150},
        {"label": _("Est. Hrs"), "fieldname": "estimated", "fieldtype": "Float", "width": 90},
        {"label": _("Planned"), "fieldname": "planned", "fieldtype": "Float", "width": 90},
        {"label": _("Actual"), "fieldname": "actual", "fieldtype": "Float", "width": 90},
        {"label": _("On-Plan Hrs"), "fieldname": "on_plan", "fieldtype": "Float", "width": 100},
        {"label": _("Unplanned Hrs"), "fieldname": "unplanned", "fieldtype": "Float", "width": 110},
        {"label": _("Deviation"), "fieldname": "deviation", "fieldtype": "Float", "width": 95},
        {"label": _("% Consumed"), "fieldname": "pct", "fieldtype": "Percent", "width": 100},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
    ]

    plan_name = filters.get("weekly_plan") or get_plan_for_date(filters.get("as_on") or nowdate())
    if not plan_name:
        return columns, []

    # Restrict to a department's projects (default from PMS AI Settings). Blank = all.
    dept = filters.get("department")
    if dept is None:
        dept = frappe.db.get_single_value("PMS AI Settings", "plan_department")
    allowed = None
    if dept:
        allowed = set(frappe.get_all("PMS Project", filters={"department": dept},
                                     pluck="name", ignore_permissions=True))

    wp = frappe.get_doc("Weekly Plan", plan_name)
    ws = str(wp.week_start)
    we = str(getdate(nowdate()))
    if getdate(we) > getdate(wp.week_end):
        we = str(wp.week_end)

    planned = {}
    for a in wp.allocations:
        if not a.get("project") or not flt(a.planned_hours):
            continue
        if allowed is not None and a.project not in allowed:
            continue
        k = (a.project, a.member)
        planned[k] = planned.get(k, 0) + flt(a.planned_hours)

    # actual per (project, person); project-less time logs land in "No Project"
    rows = frappe.db.sql("""
        select coalesce(t.project, '') as project, tl.user as person,
               round(sum(tl.duration_hours), 2) h
        from `tabPMS Time Log` tl left join `tabPMS Task` t on t.name = tl.task
        where tl.is_running = 0 and DATE(tl.start_time) between %s and %s
        group by coalesce(t.project, ''), tl.user""", (ws, we), as_dict=True)
    actual = {(r.project, r.person): flt(r.h) for r in rows
              if flt(r.h) and (allowed is None or r.project in allowed)}

    # estimated: total task estimate per (project, assignee) — scope context, not time-windowed
    est_rows = frappe.db.sql("""
        select project, assigned_to as person, round(sum(estimated_hours), 2) h
        from `tabPMS Task`
        where assigned_to is not null and project is not null
        group by project, assigned_to""", as_dict=True)
    estimated = {(r.project, r.person): flt(r.h) for r in est_rows
                 if flt(r.h) and (allowed is None or r.project in allowed)}

    keys = set(planned) | set(actual)
    pids = {k[0] for k in keys if k[0]}
    uids = {k[1] for k in keys if k[1]}
    names = {}
    if pids:
        names.update(dict(frappe.get_all(
            "PMS Project", filters={"name": ["in", list(pids)]},
            fields=["name", "project_name"], as_list=True, ignore_permissions=True)))
    if uids:
        names.update(dict(frappe.get_all(
            "User", filters={"name": ["in", list(uids)]},
            fields=["name", "full_name"], as_list=True, ignore_permissions=True)))
    names[""] = _("No Project")

    data = []
    for (pid, uid) in sorted(keys, key=lambda k: (names.get(k[0]) or k[0], names.get(k[1]) or k[1])):
        p = planned.get((pid, uid), 0)
        a = actual.get((pid, uid), 0)
        if p and a:
            status = STATUS_ON_PLAN
        elif p:
            status = STATUS_NOT_STARTED
        else:
            status = STATUS_UNPLANNED
        data.append({
            "project": names.get(pid) or pid, "person": names.get(uid) or uid,
            "estimated": estimated.get((pid, uid), 0),
            "planned": p, "actual": a,
            "on_plan": a if p else 0,
            "unplanned": a if not p else 0,
            "deviation": round(a - p, 2),
            "pct": (a / p * 100) if p else 0,
            "status": status,
        })

    total_estimated = sum(r["estimated"] for r in data)
    total_planned = sum(r["planned"] for r in data)
    total_actual = sum(r["actual"] for r in data)
    total_unplanned = sum(r["unplanned"] for r in data)
    unplanned_pct = (total_unplanned / total_actual * 100) if total_actual else 0

    report_summary = [
        {"label": _("Estimated"), "value": round(total_estimated, 2), "datatype": "Float"},
        {"label": _("Planned"), "value": round(total_planned, 2), "datatype": "Float"},
        {"label": _("Actual"), "value": round(total_actual, 2), "datatype": "Float"},
        {"label": _("On-Plan"), "value": round(total_actual - total_unplanned, 2),
         "datatype": "Float", "indicator": "Green"},
        {"label": _("Unplanned"), "value": round(total_unplanned, 2), "datatype": "Float",
         "indicator": "Red" if total_unplanned else "Green"},
        {"label": _("Unplanned %"), "value": round(unplanned_pct, 1), "datatype": "Percent",
         "indicator": "Red" if unplanned_pct > 20 else ("Orange" if unplanned_pct else "Green")},
    ]

    # per-person grouped chart: planned vs on-plan vs unplanned
    per_person = {}
    for r in data:
        d = per_person.setdefault(r["person"], {"planned": 0, "on_plan": 0, "unplanned": 0})
        d["planned"] += r["planned"]
        d["on_plan"] += r["on_plan"]
        d["unplanned"] += r["unplanned"]
    people = sorted(per_person)
    chart = {
        "data": {
            "labels": people,
            "datasets": [
                {"name": _("Planned"), "values": [round(per_person[p]["planned"], 2) for p in people]},
                {"name": _("On-Plan Actual"), "values": [round(per_person[p]["on_plan"], 2) for p in people]},
                {"name": _("Unplanned Actual"), "values": [round(per_person[p]["unplanned"], 2) for p in people]},
            ],
        },
        "type": "bar",
        "colors": ["#7cd6fd", "#28a745", "#dc3545"],
        "barOptions": {"spaceRatio": 0.5},
    }

    message = _("Est. Hrs = total estimated hours of tasks assigned to that person on the project (full scope, not time-windowed). Unplanned = time logged with no planned hours for that project+person in the weekly plan.")
    return columns, data, message, chart, report_summary
