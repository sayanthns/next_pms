"""Calendar / scheduled-meetings API for the Next PMS SPA.

Meetings are stored in the PMS Meeting DocType (participants in the
PMS Meeting Attendee child table). Managers/admins see and edit everything;
any non-customer user can view the team calendar and their own schedule and
schedule meetings they coordinate. Minutes of Meeting are mandatory before a
meeting can be marked Held (enforced in the PMS Meeting controller).
"""

import json

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, nowdate, add_days, cint

from next_pms.api.weekly_plan import _user_context

LIST_FIELDS = ["name", "subject", "project", "start_time", "meeting_date", "day_of_week",
               "meeting_type", "coordinator", "status", "duration_mins", "mom_pdf", "next_actions"]


def _guard_view():
    ctx = _user_context()
    if ctx["is_customer"] or frappe.session.user == "Guest":
        frappe.throw(_("You are not permitted to view the calendar."), frappe.PermissionError)
    return ctx


def _can_edit(ctx, coordinator=None):
    return bool(ctx["is_admin"] or ctx["is_manager"] or (coordinator and coordinator == ctx["user"]))


def _participants_of(names):
    out = {}
    if not names:
        return out
    for p in frappe.get_all("PMS Meeting Attendee",
                            filters={"parent": ["in", names], "parenttype": "PMS Meeting"},
                            fields=["parent", "user", "full_name", "response"],
                            ignore_permissions=True):
        out.setdefault(p.parent, []).append(
            {"user": p.user, "full_name": p.full_name or p.user, "response": p.response})
    return out


def _project_names(pids):
    pids = [p for p in pids if p]
    if not pids:
        return {}
    return dict(frappe.get_all("PMS Project", filters={"name": ["in", pids]},
                               fields=["name", "project_name"], as_list=True, ignore_permissions=True))


@frappe.whitelist()
def list_meetings(start=None, end=None, scope="mine"):
    """Meetings between `start` and `end` (inclusive). scope='mine' → only meetings
    where the caller is coordinator or a participant; scope='all' → the whole team
    calendar. Defaults to a 4-week window from today when no dates are given."""
    ctx = _guard_view()
    s = getdate(start) if start else getdate(nowdate())
    e = getdate(end) if end else add_days(s, 27)

    meetings = frappe.get_all("PMS Meeting",
                              filters={"meeting_date": ["between", [str(s), str(e)]]},
                              fields=LIST_FIELDS,
                              order_by="meeting_date asc, start_time asc",
                              ignore_permissions=True)
    names = [m.name for m in meetings]
    parts = _participants_of(names)
    pnames = _project_names({m.project for m in meetings})

    out = []
    for m in meetings:
        ps = parts.get(m.name, [])
        mine = (m.coordinator == ctx["user"]) or any(p["user"] == ctx["user"] for p in ps)
        if scope == "mine" and not mine:
            continue
        m["project_name"] = pnames.get(m.project) or m.project
        m["participants"] = ps
        m["has_mom"] = bool(m.get("mom_pdf"))
        m["can_edit"] = _can_edit(ctx, m.coordinator)
        m["is_mine"] = mine
        out.append(m)
    return out


@frappe.whitelist()
def get_meeting(name):
    ctx = _guard_view()
    doc = frappe.get_doc("PMS Meeting", name)
    d = doc.as_dict()
    d["project_name"] = _project_names({doc.project}).get(doc.project) or doc.project
    d["participants"] = [{"user": p.user, "full_name": p.full_name or p.user, "response": p.response}
                         for p in (doc.participants or [])]
    d["has_mom"] = bool(doc.mom_pdf)
    d["can_edit"] = _can_edit(ctx, doc.coordinator)
    return d


@frappe.whitelist()
def save_meeting(payload):
    """Create or update a meeting. New meetings: any non-customer user (defaults the
    coordinator to the caller). Existing: managers/admins or the coordinator. Minutes
    are enforced by the controller when status=Held."""
    ctx = _guard_view()
    if isinstance(payload, str):
        payload = json.loads(payload)

    name = payload.get("name")
    if name:
        existing_coord = frappe.db.get_value("PMS Meeting", name, "coordinator")
        if not _can_edit(ctx, existing_coord):
            frappe.throw(_("You can only edit meetings you coordinate."), frappe.PermissionError)
        doc = frappe.get_doc("PMS Meeting", name)
    else:
        doc = frappe.new_doc("PMS Meeting")
        doc.coordinator = payload.get("coordinator") or ctx["user"]

    if not name and payload.get("coordinator"):
        doc.coordinator = payload.get("coordinator")
    elif name:
        doc.coordinator = payload.get("coordinator") or doc.coordinator

    doc.subject = payload.get("subject")
    doc.project = payload.get("project") or None
    doc.start_time = payload.get("start_time") or None
    doc.meeting_type = payload.get("meeting_type") or "Client Weekly"
    doc.status = payload.get("status") or "Planned"
    doc.duration_mins = cint(payload.get("duration_mins")) or 30
    doc.mom_pdf = payload.get("mom_pdf") or None
    doc.minutes = payload.get("minutes")
    doc.next_actions = payload.get("next_actions")

    doc.set("participants", [])
    seen = set()
    for row in (payload.get("participants") or []):
        u = row.get("user") if isinstance(row, dict) else row
        if not u or u in seen:
            continue
        seen.add(u)
        doc.append("participants", {"user": u, "response": (row.get("response") if isinstance(row, dict) else None) or "Invited"})

    doc.save(ignore_permissions=True)
    return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def delete_meeting(name):
    ctx = _guard_view()
    coord = frappe.db.get_value("PMS Meeting", name, "coordinator")
    if not _can_edit(ctx, coord):
        frappe.throw(_("You can only delete meetings you coordinate."), frappe.PermissionError)
    frappe.delete_doc("PMS Meeting", name, ignore_permissions=True)
    return {"ok": True}


@frappe.whitelist()
def calendar_options():
    """Users (for the attendee/coordinator pickers) and active projects (for the
    project picker). Users = internal PMS staff only (the 'Next PMS' role), which
    excludes portal customers and System Users with no PMS access — same list the
    Task Report and task modal use."""
    _guard_view()
    from next_pms.api.crud import get_all_users
    users = get_all_users()
    projects = frappe.get_all("PMS Project",
                              filters={"status": ["in", ("Planning", "Active", "On Hold")]},
                              fields=["name", "project_name"], order_by="project_name asc",
                              ignore_permissions=True)
    return {"users": users, "projects": projects}
