# Copyright (c) 2026, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, nowdate

ACTIVE = ("Planning", "Active", "On Hold")


def execute(filters=None):
    filters = filters or {}
    to_date = getdate(filters.get("to_date") or nowdate())
    from_date = getdate(filters.get("from_date") or add_days(to_date, -to_date.weekday()))

    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "PMS Project", "width": 180},
        {"label": _("Coordinator"), "fieldname": "coordinator", "fieldtype": "Data", "width": 150},
        {"label": _("Cadence"), "fieldname": "cadence", "fieldtype": "Data", "width": 140},
        {"label": _("Planned"), "fieldname": "planned", "fieldtype": "Int", "width": 80},
        {"label": _("Held"), "fieldname": "held", "fieldtype": "Int", "width": 70},
        {"label": _("Missed"), "fieldname": "missed", "fieldtype": "Int", "width": 80},
        {"label": _("Rescheduled"), "fieldname": "rescheduled", "fieldtype": "Int", "width": 100},
        {"label": _("Compliance"), "fieldname": "compliance", "fieldtype": "Data", "width": 110},
    ]

    projects = frappe.get_all("PMS Project", filters={"status": ["in", ACTIVE]},
                              fields=["name", "project_name", "meeting_coordinator"],
                              ignore_permissions=True)

    data = []
    for p in projects:
        days = frappe.get_all("PMS Project Meeting Day",
                              filters={"parent": p["name"], "parenttype": "PMS Project"},
                              pluck="weekday", ignore_permissions=True)
        if not days:
            continue  # only projects with a planned cadence
        meetings = frappe.get_all("PMS Meeting",
                                  filters={"project": p["name"],
                                           "meeting_date": ["between", [str(from_date), str(to_date)]]},
                                  fields=["status"], ignore_permissions=True)
        cnt = {"planned": 0, "held": 0, "missed": 0, "rescheduled": 0}
        for m in meetings:
            k = (m.status or "").lower()
            if k in cnt:
                cnt[k] += 1
        data.append({
            "project": p.get("project_name") or p["name"],
            "coordinator": p.get("meeting_coordinator"),
            "cadence": ", ".join(days),
            "planned": cnt["planned"],
            "held": cnt["held"],
            "missed": cnt["missed"],
            "rescheduled": cnt["rescheduled"],
            "compliance": "OK" if cnt["held"] else "MISSED",
        })

    return columns, data
