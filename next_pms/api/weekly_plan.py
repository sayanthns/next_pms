import json

import frappe
from frappe import _
from frappe.utils import flt, cint

ACTIVE_PROJECT_STATUS = ("Planning", "Active", "On Hold")
CLOSED_PROJECT_STATUS = ("Completed", "Cancelled")
STATUS_COLOR = {"Planning": "blue", "Active": "green", "On Hold": "orange",
                "Completed": "grey", "Cancelled": "grey"}
_CHILD_META = {"name", "parent", "parentfield", "parenttype", "idx", "creation",
               "modified", "modified_by", "owner", "docstatus", "doctype",
               "__islocal", "__unsaved"}


def _h(hours):
    h = flt(hours)
    if not h:
        return ""
    return (str(int(h)) if h == int(h) else str(round(h, 1))) + "h"


def _strip(rows):
    return [{k: v for k, v in r.items() if k not in _CHILD_META} for r in (rows or [])]


def _user_context():
    roles = set(frappe.get_roles(frappe.session.user))
    is_admin = bool({"System Manager", "Administrator"} & roles)
    is_manager = "PMS Manager" in roles
    is_developer = "PMS Developer" in roles
    is_customer = "PMS Customer" in roles and not (is_admin or is_manager or is_developer)
    return {"is_admin": is_admin, "is_manager": is_manager,
            "is_developer": is_developer, "is_customer": is_customer,
            "user": frappe.session.user}


def _resolve_name(week_start=None):
    if week_start:
        return frappe.db.get_value("Weekly Plan", {"week_start": week_start}, "name")
    return frappe.db.get_value("Weekly Plan", {"published": 1}, "name",
                               order_by="week_start desc")


def _load_week_dict(name):
    return frappe.get_doc("Weekly Plan", name).as_dict()


def _attach_team_names(plan):
    """Resolve each project's comma-separated team emails to display names so the UI
    can show real initials/hover, not a single ambiguous letter."""
    emails = set()
    for p in plan.get("projects", []):
        for e in (p.get("team") or "").split(","):
            e = e.strip()
            if e:
                emails.add(e)
    names = {}
    if emails:
        for u in frappe.get_all("User", filters={"name": ["in", list(emails)]},
                                fields=["name", "full_name"], ignore_permissions=True):
            names[u.name] = u.full_name or u.name
    for p in plan.get("projects", []):
        p["team_list"] = [{"user": e.strip(), "name": names.get(e.strip(), e.strip())}
                          for e in (p.get("team") or "").split(",") if e.strip()]


def _user_project_names(user):
    """Projects the user is on, derived from assigned PMS Tasks (perms bypassed —
    the weekly plan is internal and the caller is already an authenticated dev)."""
    names = frappe.get_all("PMS Task", filters={"assigned_to": user},
                           pluck="project", ignore_permissions=True)
    return {n for n in names if n}


@frappe.whitelist()
def list_weeks():
    ctx = _user_context()
    if ctx["is_customer"] or frappe.session.user == "Guest":
        frappe.throw(_("You are not permitted to view the weekly plan."), frappe.PermissionError)
    filters = {} if (ctx["is_admin"] or ctx["is_manager"]) else {"published": 1}
    return frappe.get_all("Weekly Plan", filters=filters,
                          fields=["name", "week_start", "title"],
                          order_by="week_start desc", ignore_permissions=True)


@frappe.whitelist()
def get_week(week_start=None):
    ctx = _user_context()
    if ctx["is_customer"] or frappe.session.user == "Guest":
        frappe.throw(_("You are not permitted to view the weekly plan."), frappe.PermissionError)

    name = _resolve_name(week_start)
    if not name:
        return None
    plan = _load_week_dict(name)
    _attach_team_names(plan)

    if ctx["is_admin"] or ctx["is_manager"]:
        return plan

    # developer: scope to self
    user = ctx["user"]
    my_projects = _user_project_names(user)
    team_keyed = {p.get("project") for p in plan.get("projects", [])
                  if user in [e.strip() for e in (p.get("team") or "").split(",")]}
    keep = my_projects | team_keyed
    plan["allocations"] = [a for a in plan.get("allocations", []) if a.get("member") == user]
    plan["projects"] = [p for p in plan.get("projects", []) if p.get("project") in keep]
    plan["watch_list"] = [w for w in plan.get("watch_list", []) if w.get("owner") == user]
    # priorities, checklist, closures, narrative remain global
    return plan


def _require_manager():
    ctx = _user_context()
    if not (ctx["is_admin"] or ctx["is_manager"]):
        frappe.throw(_("Only managers can prefill or edit the weekly plan."), frappe.PermissionError)
    return ctx


@frappe.whitelist()
def prefill_week(week_start=None):
    """Manager-only. Build a DRAFT (not saved) from live PMS data:
    projects = active PMS Projects + members + open-task effort;
    allocations = open tasks grouped by assignee. Manager curates judgment bits."""
    _require_manager()

    projects = []
    for p in frappe.get_all("PMS Project", filters={"status": ["in", ACTIVE_PROJECT_STATUS]},
                            fields=["name", "status"], ignore_permissions=True):
        members = frappe.get_all("PMS Project Member",
                                 filters={"parent": p["name"], "parenttype": "PMS Project"},
                                 pluck="user", ignore_permissions=True)
        effort = frappe.db.sql(
            "select coalesce(sum(estimated_hours), 0) from `tabPMS Task` "
            "where project = %s and status != 'Done'", (p["name"],))[0][0]
        projects.append({
            "project": p["name"], "status_label": p["status"],
            "status_color": STATUS_COLOR.get(p["status"], "grey"),
            "effort": _h(effort),
            "team": ",".join([u for u in members if u]),
        })

    tasks = frappe.get_all("PMS Task", filters={"status": ["!=", "Done"], "assigned_to": ["is", "set"]},
                           fields=["assigned_to", "task_title", "estimated_hours"],
                           ignore_permissions=True)
    by_user = {}
    for t in tasks:
        u = t["assigned_to"]
        d = by_user.setdefault(u, {"member": u, "planned_hours": 0.0, "lines": []})
        d["planned_hours"] += flt(t["estimated_hours"])
        if len(d["lines"]) < 12:
            hr = _h(t["estimated_hours"])
            d["lines"].append((t["task_title"] or "Task") + (" " + hr if hr else ""))
    allocations = [{"member": d["member"], "planned_hours": round(d["planned_hours"], 2),
                    "capacity_hours": 40, "tasks": "\n".join(d["lines"])}
                   for d in by_user.values()]

    return {"week_start": week_start, "allocations": allocations, "projects": projects}


@frappe.whitelist()
def roll_forward(from_week, to_week):
    """Manager-only. Clone a prior week into a draft for `to_week`, dropping projects
    whose PMS Project is now Completed/Cancelled. Not saved — manager reviews + saves."""
    _require_manager()
    name = _resolve_name(from_week)
    if not name:
        frappe.throw(_("No weekly plan found for that week."))
    src = _load_week_dict(name)

    closed = set()
    for p in src.get("projects", []):
        st = frappe.db.get_value("PMS Project", p.get("project"), "status")
        if st in CLOSED_PROJECT_STATUS:
            closed.add(p.get("project"))

    return {
        "week_start": to_week, "published": 0,
        "intro": src.get("intro"), "headline_note": src.get("headline_note"),
        "allocations": _strip(src.get("allocations")),
        "projects": _strip([p for p in src.get("projects", []) if p.get("project") not in closed]),
        "closures": _strip(src.get("closures")),
        "priorities": _strip(src.get("priorities")),
        "watch_list": _strip(src.get("watch_list")),
        "checklist": _strip(src.get("checklist")),
        "working_notes": src.get("working_notes"),
        "week_shape": src.get("week_shape"),
        "meetings_note": src.get("meetings_note"),
    }


_SIMPLE_TABLES = ("allocations", "projects", "closures", "priorities", "watch_list", "checklist")


@frappe.whitelist()
def save_week(payload):
    """Manager-only upsert of a Weekly Plan from the in-app editor. Replaces child
    tables wholesale; controller recomputes week_end/title/WSJF on save."""
    _require_manager()
    if isinstance(payload, str):
        payload = json.loads(payload)

    week_start = payload.get("week_start")
    if not week_start:
        frappe.throw(_("Week start is required."))

    name = frappe.db.get_value("Weekly Plan", {"week_start": week_start}, "name")
    doc = frappe.get_doc("Weekly Plan", name) if name else frappe.new_doc("Weekly Plan")
    doc.week_start = week_start
    for f in ("intro", "headline_note", "working_notes", "week_shape", "meetings_note"):
        doc.set(f, payload.get(f))
    doc.published = cint(payload.get("published"))

    for table in _SIMPLE_TABLES:
        doc.set(table, [])
        for row in (payload.get(table) or []):
            doc.append(table, _strip([row])[0])

    doc.save()
    return {"name": doc.name, "week_start": str(doc.week_start), "title": doc.title}


@frappe.whitelist()
def log_client_error(message=None, url=None):
    """Capture a frontend JS error server-side (Error Log) so blank-screen crashes are
    diagnosable without the browser console. Logged-in users only."""
    frappe.log_error(message=(str(message) or "")[:5000],
                     title="PMS Client Error " + (str(url or "")[:80]))
    return {"ok": True}


@frappe.whitelist()
def get_form_options():
    """Manager-only. Dropdown options for the editor: PMS users + active projects."""
    _require_manager()
    users = frappe.db.sql(
        "select distinct u.name, u.full_name from `tabUser` u "
        "join `tabHas Role` r on r.parent = u.name "
        "where u.enabled = 1 and r.role in %s order by u.full_name",
        (("PMS Developer", "PMS Manager"),), as_dict=True)
    projects = frappe.get_all("PMS Project", filters={"status": ["in", ACTIVE_PROJECT_STATUS]},
                              fields=["name", "project_name"], order_by="project_name",
                              ignore_permissions=True)
    return {
        "users": [{"value": u.name, "label": u.full_name or u.name} for u in users],
        "projects": [{"value": p.name, "label": p.project_name or p.name} for p in projects],
    }
