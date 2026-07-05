# Copyright (c) 2026, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, flt
from next_pms.api.weekly_plan import get_plan_for_date


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 190},
        {"label": _("Person"), "fieldname": "person", "fieldtype": "Data", "width": 160},
        {"label": _("Planned"), "fieldname": "planned", "fieldtype": "Float", "width": 90},
        {"label": _("Actual"), "fieldname": "actual", "fieldtype": "Float", "width": 90},
        {"label": _("Deviation"), "fieldname": "deviation", "fieldtype": "Float", "width": 100},
        {"label": _("% Consumed"), "fieldname": "pct", "fieldtype": "Percent", "width": 100},
    ]
    plan_name = filters.get("weekly_plan") or get_plan_for_date(filters.get("as_on") or nowdate())
    if not plan_name:
        return columns, []

    wp = frappe.get_doc("Weekly Plan", plan_name)
    ws = str(wp.week_start)
    we = str(getdate(nowdate()))
    if getdate(we) > getdate(wp.week_end):
        we = str(wp.week_end)

    planned = {}
    for a in wp.allocations:
        if not a.get("project"):
            continue
        k = (a.project, a.member)
        planned[k] = planned.get(k, 0) + flt(a.planned_hours)

    rows = frappe.db.sql("""
        select t.project as project, tl.user as person, round(sum(tl.duration_hours), 2) h
        from `tabPMS Time Log` tl join `tabPMS Task` t on t.name = tl.task
        where tl.is_running = 0 and DATE(tl.start_time) between %s and %s and t.project is not null
        group by t.project, tl.user""", (ws, we), as_dict=True)
    actual = {(r.project, r.person): flt(r.h) for r in rows}

    keys = set(planned) | set(actual)
    names = {}
    for pid, uid in keys:
        if pid not in names:
            names[pid] = frappe.db.get_value("PMS Project", pid, "project_name") or pid
        if uid not in names:
            names[uid] = frappe.db.get_value("User", uid, "full_name") or uid

    data = []
    for (pid, uid) in sorted(keys, key=lambda k: (names.get(k[0], k[0]), names.get(k[1], k[1]))):
        p = planned.get((pid, uid), 0)
        a = actual.get((pid, uid), 0)
        data.append({
            "project": names.get(pid, pid), "person": names.get(uid, uid),
            "planned": p, "actual": a, "deviation": round(a - p, 2),
            "pct": (a / p * 100) if p else 0,
        })
    return columns, data
