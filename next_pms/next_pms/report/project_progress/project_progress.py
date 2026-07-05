# Copyright (c) 2026, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, flt, date_diff
from next_pms.api.weekly_plan import get_plan_for_date

ACTIVE = ("Planning", "Active", "On Hold")


def execute(filters=None):
    filters = filters or {}
    today = getdate(nowdate())
    plan_name = get_plan_for_date(today)
    target = {}
    ws = str(today)
    if plan_name:
        wp = frappe.get_doc("Weekly Plan", plan_name)
        ws = str(wp.week_start)
        for p in wp.projects:
            if p.get("project"):
                target[p.project] = flt(p.get("target_hours"))

    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "PMS Project", "width": 190},
        {"label": _("Target h"), "fieldname": "target", "fieldtype": "Float", "width": 80},
        {"label": _("Actual h"), "fieldname": "actual", "fieldtype": "Float", "width": 80},
        {"label": _("Done"), "fieldname": "done", "fieldtype": "Int", "width": 70},
        {"label": _("Open"), "fieldname": "open", "fieldtype": "Int", "width": 70},
        {"label": _("% Complete"), "fieldname": "pct", "fieldtype": "Percent", "width": 100},
        {"label": _("Close Date"), "fieldname": "close_date", "fieldtype": "Date", "width": 100},
        {"label": _("Delivery"), "fieldname": "delivery", "fieldtype": "Data", "width": 130},
    ]

    projects = frappe.get_all("PMS Project", filters={"status": ["in", ACTIVE]},
                              fields=["name", "project_name", "target_close_date"], ignore_permissions=True)
    data = []
    for p in projects:
        actual = flt(frappe.db.sql("""
            select round(sum(tl.duration_hours), 2) from `tabPMS Time Log` tl
            join `tabPMS Task` t on t.name = tl.task
            where tl.is_running = 0 and t.project = %s and DATE(tl.start_time) between %s and %s""",
            (p.name, ws, str(today)))[0][0] or 0)
        done = frappe.db.count("PMS Task", {"project": p.name, "status": "Done"})
        openc = frappe.db.count("PMS Task", {"project": p.name, "status": ["not in", ["Done"]]})
        total = done + openc
        pct = (done / total * 100) if total else 0
        delivery = "—"
        if p.get("target_close_date"):
            dd = date_diff(p.target_close_date, today)
            if dd < 0:
                delivery = "Overdue %sd" % (-dd)
            elif dd <= 3 and pct < 80:
                delivery = "At risk (%sd)" % dd
            else:
                delivery = "On track (%sd)" % dd
        data.append({
            "project": p.name, "target": target.get(p.name, 0), "actual": actual,
            "done": done, "open": openc, "pct": pct,
            "close_date": p.get("target_close_date"), "delivery": delivery,
        })
    return columns, data
