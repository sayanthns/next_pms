import frappe
from frappe import _
from frappe.utils import now_datetime, add_days, getdate, get_datetime
from next_pms.utils import get_pms_url


def send_deadline_reminders():
    """Send notifications for tasks with deadlines approaching within 1 day."""
    tomorrow = add_days(getdate(), 1)
    tasks = frappe.get_all(
        "PMS Task",
        filters={
            "due_date": tomorrow,
            "status": ["not in", ["Done", "Cancelled"]],
            "assigned_to": ["is", "set"],
        },
        fields=["name", "task_title", "assigned_to", "project", "due_date", "status"],
    )

    for task in tasks:
        assigned_to_name = frappe.db.get_value("User", task.assigned_to, "full_name") or task.assigned_to
        project_name = frappe.db.get_value("PMS Project", task.project, "project_name") or task.project
        task_url = get_pms_url("PMS Task", task.name)

        message = frappe.render_template(
            "next_pms/templates/emails/deadline_reminder.html",
            {
                "task_title": task.task_title,
                "assigned_to_name": assigned_to_name,
                "project_name": project_name,
                "due_date": task.due_date,
                "status": task.status,
                "task_url": task_url,
            },
        )

        frappe.sendmail(
            recipients=[task.assigned_to],
            subject=f"Task Due Tomorrow: {task.task_title}",
            message=message,
            now=True,
        )

        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "for_user": task.assigned_to,
                "type": "Alert",
                "document_type": "PMS Task",
                "document_name": task.name,
                "subject": f"Task Due Tomorrow: {task.task_title}",
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()


def check_long_running_timers():
    """Alert users with timers running for more than 4 hours."""
    four_hours_ago = frappe.utils.add_to_date(now_datetime(), hours=-4)

    running_logs = frappe.get_all(
        "PMS Time Log",
        filters={
            "is_running": 1,
            "start_time": ["<", four_hours_ago],
        },
        fields=["name", "user", "task", "start_time"],
    )

    for log in running_logs:
        task_title = frappe.db.get_value("PMS Task", log.task, "task_title")
        hours_running = (now_datetime() - get_datetime(log.start_time)).total_seconds() / 3600
        user_name = frappe.db.get_value("User", log.user, "full_name") or log.user
        task_url = get_pms_url("PMS Task", log.task)

        message = frappe.render_template(
            "next_pms/templates/emails/timer_reminder.html",
            {
                "user_name": user_name,
                "task_title": task_title,
                "hours_running": f"{hours_running:.1f}",
                "task_url": task_url,
            },
        )

        frappe.sendmail(
            recipients=[log.user],
            subject=f"Timer Running: {task_title} ({hours_running:.1f}h)",
            message=message,
            now=True,
        )

        # Create Notification Log entry
        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "for_user": log.user,
                "type": "Alert",
                "document_type": "PMS Time Log",
                "document_name": log.name,
                "subject": f"Timer Running: {task_title} ({hours_running:.1f}h)",
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()


def check_budget_alerts():
    """Check projects exceeding 80% budget utilization."""
    projects = frappe.get_all(
        "PMS Project",
        filters={
            "status": "Active",
            "total_budget": [">", 0],
        },
        fields=[
            "name", "project_name", "project_manager",
            "budget_utilization", "total_budget", "calculated_cost",
        ],
    )

    for project in projects:
        if project.budget_utilization and project.budget_utilization >= 80:
            manager_name = (
                frappe.db.get_value("User", project.project_manager, "full_name")
                or project.project_manager
            )
            used_budget = project.calculated_cost or 0
            remaining = (project.total_budget or 0) - used_budget
            project_url = get_pms_url("PMS Project", project.name)

            message = frappe.render_template(
                "next_pms/templates/emails/budget_alert.html",
                {
                    "project_name": project.project_name,
                    "manager_name": manager_name,
                    "utilization": f"{project.budget_utilization:.0f}",
                    "total_budget": f"{project.total_budget:,.2f}",
                    "used_budget": f"{used_budget:,.2f}",
                    "remaining": f"{remaining:,.2f}",
                    "project_url": project_url,
                },
            )

            frappe.sendmail(
                recipients=[project.project_manager],
                subject=f"Budget Alert: {project.project_name} at {project.budget_utilization:.0f}%",
                message=message,
                now=True,
            )

            # Create Notification Log entry
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": project.project_manager,
                    "type": "Alert",
                    "document_type": "PMS Project",
                    "document_name": project.name,
                    "subject": f"Budget Alert: {project.project_name} at {project.budget_utilization:.0f}%",
                }
            ).insert(ignore_permissions=True)

    frappe.db.commit()


def get_week_start(d):
    """Monday of the week containing date d."""
    d = getdate(d)
    return add_days(d, -d.weekday())  # weekday(): Monday=0


def _get_active_members(from_dt, to_dt):
    """Enabled users who logged time this week OR are members of an Active project."""
    logged = frappe.get_all(
        "PMS Time Log",
        filters={"start_time": ["between", [from_dt, to_dt]], "is_running": 0},
        fields=["user"],
        group_by="user",
    )
    members = {l.user for l in logged if l.user}

    active_projects = frappe.get_all("PMS Project", filters={"status": "Active"}, fields=["name"])
    active_proj_names = [p.name for p in active_projects]
    if active_proj_names:
        project_members = frappe.get_all(
            "PMS Project Member",
            filters={"parenttype": "PMS Project", "parent": ["in", active_proj_names]},
            fields=["user"],
        )
        members |= {m.user for m in project_members if m.user}

    if not members:
        return []
    enabled = frappe.get_all(
        "User",
        # System User only: portal/customer (Website User) accounts that happen to be
        # project members must not receive internal weekly stats emails.
        filters={"name": ["in", list(members)], "enabled": 1, "user_type": "System User"},
        fields=["name"],
    )
    return [u.name for u in enabled]


def _member_week_stats(user, week_start, week_end, from_dt, to_dt):
    """Per-member weekly stats dict (no email). Uses shared 8h-baseline target."""
    from next_pms.api._hours import compute_target_hours, compute_utilization

    full_name = frappe.db.get_value("User", user, "full_name") or user

    logs = frappe.get_all(
        "PMS Time Log",
        filters={"user": user, "start_time": ["between", [from_dt, to_dt]], "is_running": 0},
        fields=["duration_hours", "task"],
    )
    logged_hours = round(sum(l.duration_hours or 0 for l in logs), 2)
    target_hours = compute_target_hours(user, week_start, week_end)
    utilization = compute_utilization(logged_hours, target_hours)

    # Approximation: PMS Task has no completion_date, so we proxy "completed this week"
    # as status=Done AND last-modified within the window. A Done task edited later in the
    # week can be over-counted. Acceptable for a summary; a dedicated completion_date field
    # is the proper fix (tracked as a follow-up).
    tasks_completed = frappe.db.sql(
        """
        SELECT COUNT(*) FROM `tabPMS Task`
        WHERE assigned_to = %s AND status = 'Done'
          AND DATE(modified) BETWEEN %s AND %s
        """,
        (user, str(week_start), str(week_end)),
    )[0][0] or 0
    tasks_in_progress = frappe.db.count(
        "PMS Task", {"assigned_to": user, "status": ["in", ["In Progress", "In Review"]]}
    )

    task_names = list({l.task for l in logs if l.task})
    projects_touched = set()
    if task_names:
        for row in frappe.get_all(
            "PMS Task", filters={"name": ["in", task_names]}, fields=["project"]
        ):
            if row.project:
                projects_touched.add(row.project)

    # Attendance over the week. Denominator = effective working days (excludes
    # Sundays, holidays, full-day approved leave) — same basis as the 8h target.
    from next_pms.api._hours import effective_working_days

    working_day_strs = set(effective_working_days(user, week_start, week_end))
    checkins = frappe.get_all(
        "PMS Checkin",
        filters={"user": user, "date": ["between", [str(week_start), str(week_end)]]},
        fields=["date", "checkout_time"],
    )

    return {
        "user": user,
        "full_name": full_name,
        "logged_hours": logged_hours,
        "target_hours": target_hours,
        "utilization": utilization,
        "tasks_completed": tasks_completed,
        "tasks_in_progress": tasks_in_progress,
        "project_count": len(projects_touched),
        **_attendance_counts(working_day_strs, checkins),
    }


def _attendance_counts(working_day_strs, checkins):
    """Attendance tallies for a week. Pure — no DB.
    working_day_strs: iterable of 'YYYY-MM-DD' effective working days.
    checkins: list of dicts/objects with .date and .checkout_time.
    """
    working = set(str(d) for d in working_day_strs)
    checked = {str(c["date"]) for c in checkins if c.get("date")}
    return {
        "working_days": len(working),
        "days_checked_in": len(checked & working),
        "missed_checkin_days": len(working - checked),
        "missed_checkouts": sum(1 for c in checkins if not c.get("checkout_time")),
    }


def send_weekly_summary():
    """Saturday 07:00 cron - per active member: own weekly stats email.
    Configured recipient (default sayanth@enfono.in): all-members table.

    Window = the just-completed work week, Monday 00:00 .. Friday 23:59. The job
    fires Saturday morning, so Saturday is intentionally NOT counted as a target
    day (no one has worked it yet) - counting it would deflate utilization.
    """
    today = getdate()
    week_end = add_days(today, -1)  # Friday (job runs Saturday morning)
    week_start = get_week_start(week_end)  # Monday of that week
    from_dt = str(week_start) + " 00:00:00"
    to_dt = str(week_end) + " 23:59:59"

    members = _get_active_members(from_dt, to_dt)
    team_rows = []

    for user in members:
        stats = _member_week_stats(user, week_start, week_end, from_dt, to_dt)
        team_rows.append(stats)
        try:
            frappe.sendmail(
                recipients=[user],
                subject=_("Your Weekly Work Summary"),
                message=_build_member_weekly_html(stats, str(week_start), str(week_end)),
                now=True,
            )
        except Exception:
            frappe.log_error(
                title=f"Weekly summary email failed for {user}",
                message=frappe.get_traceback(),
            )

    recipient = (
        frappe.db.get_single_value("PMS AI Settings", "weekly_summary_recipient")
        or "sayanth@enfono.in"
    )
    if team_rows:
        try:
            frappe.sendmail(
                recipients=[recipient],
                subject=_("Team Weekly Work Summary"),
                message=_build_team_weekly_html(team_rows, str(week_start), str(week_end)),
                now=True,
            )
        except Exception:
            frappe.log_error(
                title=f"Team weekly summary email failed for {recipient}",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()


def _util_color(util):
    if util >= 90:
        return "#10B981"
    if util >= 60:
        return "#F59E0B"
    return "#EF4444"


def _performance_message(utilization, missed_checkin_days=0, missed_checkouts=0):
    """Return (headline, color, note) encouragement banner based on utilization.
    >=90 congratulate, 60-89 encourage, <60 nudge. Pure — no DB."""
    u = utilization or 0
    if u >= 90:
        headline = "Outstanding week — excellent utilization. Congratulations! \U0001F389"
        color = "#10B981"
    elif u >= 60:
        headline = "Solid week — keep it up, almost at target. \U0001F4AA"
        color = "#F59E0B"
    else:
        headline = "Below target this week — let's pick it up next week. \U0001F4C8"
        color = "#EF4444"
    flags = []
    if missed_checkin_days:
        flags.append(f"{missed_checkin_days} missed check-in(s)")
    if missed_checkouts:
        flags.append(f"{missed_checkouts} missed checkout(s)")
    note = ("Reminder: " + ", ".join(flags) + " — please remember to check in and out daily.") if flags else ""
    return headline, color, note


def _stat_card(label, value, value_color="#111827"):
    return f"""
        <td style="padding:14px 10px; border:1px solid #eef0f3; background:#ffffff; text-align:center; width:33%;">
            <div style="font-size:22px; font-weight:800; color:{value_color};">{value}</div>
            <div style="font-size:10px; letter-spacing:0.5px; text-transform:uppercase; color:#9ca3af; margin-top:4px;">{label}</div>
        </td>"""


def _build_member_weekly_html(stats, from_str, to_str):
    color = _util_color(stats["utilization"])
    miss_ci = stats.get("missed_checkin_days", 0)
    miss_co = stats.get("missed_checkouts", 0)
    ci_color = "#EF4444" if miss_ci else "#10B981"
    co_color = "#EF4444" if miss_co else "#10B981"
    headline, hcolor, note = _performance_message(stats["utilization"], miss_ci, miss_co)
    note_html = (
        f'<div style="margin-top:8px; font-size:12px; color:#b45309;">{note}</div>' if note else ""
    )
    return f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; max-width:560px; margin:0 auto; background:#f5f6f8; padding:24px;">
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;">
        <tr>
          <td bgcolor="#2563eb" style="background-color:#2563eb; background:linear-gradient(135deg,#4f46e5,#2563eb); padding:24px 28px; border-radius:12px 12px 0 0;">
            <div style="font-size:12px; letter-spacing:1px; text-transform:uppercase; color:#dbeafe;">Next PMS &middot; Weekly Summary</div>
            <div style="font-size:22px; font-weight:800; margin-top:6px; color:#ffffff;">Hi {stats['full_name']},</div>
            <div style="font-size:13px; color:#dbeafe; margin-top:4px;">{from_str} &nbsp;&rarr;&nbsp; {to_str}</div>
          </td>
        </tr>
      </table>

      <div style="background:#ffffff; padding:18px 28px; border-left:4px solid {hcolor};">
        <div style="font-size:15px; font-weight:700; color:{hcolor};">{headline}</div>
        {note_html}
      </div>

      <div style="background:#ffffff; padding:8px 20px 20px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate; border-spacing:8px;">
          <tr>
            {_stat_card("Hours Logged", f"{stats['logged_hours']:.1f}h", "#2563eb")}
            {_stat_card("Target", f"{stats['target_hours']:.1f}h")}
            {_stat_card("Utilization", f"{stats['utilization']:.0f}%", color)}
          </tr>
          <tr>
            {_stat_card("Tasks Done", stats['tasks_completed'], "#059669")}
            {_stat_card("In Progress", stats['tasks_in_progress'])}
            {_stat_card("Projects", stats['project_count'])}
          </tr>
        </table>

        <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; color:#6b7280; margin:14px 6px 6px;">Attendance</div>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; font-size:13px;">
          <tr>
            <td style="padding:10px 12px; border:1px solid #eef0f3;">Days Checked In</td>
            <td style="padding:10px 12px; border:1px solid #eef0f3; text-align:right; font-weight:700;">{stats.get('days_checked_in', 0)} / {stats.get('working_days', 0)}</td>
          </tr>
          <tr>
            <td style="padding:10px 12px; border:1px solid #eef0f3;">Missed Check-ins</td>
            <td style="padding:10px 12px; border:1px solid #eef0f3; text-align:right; font-weight:700; color:{ci_color};">{miss_ci}</td>
          </tr>
          <tr>
            <td style="padding:10px 12px; border:1px solid #eef0f3;">Missed Checkouts</td>
            <td style="padding:10px 12px; border:1px solid #eef0f3; text-align:right; font-weight:700; color:{co_color};">{miss_co}</td>
          </tr>
        </table>
      </div>

      <div style="background:#ffffff; border-radius:0 0 12px 12px; padding:16px 28px; border-top:1px solid #eef0f3; color:#9ca3af; font-size:11px; line-height:1.6;">
        Target = 8h &times; working days (excludes Sundays, holidays, approved leave).
        Utilization = Hours Logged &divide; Target. Days Checked In counts working days with a check-in;
        Missed Checkouts = check-ins with no checkout recorded.
        <br>Automated weekly summary from Next PMS.
      </div>
    </div>
    """


def _build_team_weekly_html(team_rows, from_str, to_str):
    rows = ""
    for s in sorted(team_rows, key=lambda x: x["utilization"], reverse=True):
        color = _util_color(s["utilization"])
        rows += f"""
        <tr>
            <td style="padding:10px; border:1px solid #e5e7eb;">{s['full_name']}</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['logged_hours']:.1f}h</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['target_hours']:.1f}h</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center; color:{color}; font-weight:600;">{s['utilization']:.0f}%</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['tasks_completed']}</td>
        </tr>
        """
    return f"""
    <h3>Team Weekly Work Summary</h3>
    <p>Week <strong>{from_str}</strong> to <strong>{to_str}</strong> - {len(team_rows)} active member(s):</p>
    <table style="border-collapse:collapse; width:100%; max-width:760px;">
        <thead>
            <tr style="background:#f3f4f6;">
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:left;">Member</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Logged</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Target</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Utilization</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Tasks Done</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:16px; color:#6b7280; font-size:13px;">
        Target = 8h x working days (excludes Sundays, holidays, approved leave).
        Automated weekly summary from Next PMS.
    </p>
    """


def _checkin_reminder_reason(checkin_time, checkout_time):
    """Return the missing-attendance reason for a day, or None if complete. Pure.
    No check-in at all -> 'check-in'. Checked in but never out -> 'check-out'."""
    if not checkin_time:
        return "check-in"
    if not checkout_time:
        return "check-out"
    return None


def send_checkin_reminders():
    """Daily (working days): email each staff member who missed their check-in or
    check-out on the previous day. Only fires on the person's effective working days
    (excludes Sundays, holidays, full-day approved leave)."""
    from next_pms.api._hours import effective_working_days

    rd = add_days(getdate(), -1)
    rd_str = str(rd)
    from_dt = rd_str + " 00:00:00"
    to_dt = rd_str + " 23:59:59"

    members = _get_active_members(from_dt, to_dt)
    sent = 0
    for user in members:
        if rd_str not in set(effective_working_days(user, rd, rd)):
            continue  # not a working day for this user
        ci = (
            frappe.db.get_value(
                "PMS Checkin",
                {"user": user, "date": rd_str},
                ["checkin_time", "checkout_time"],
                as_dict=True,
            )
            or {}
        )
        reason = _checkin_reminder_reason(ci.get("checkin_time"), ci.get("checkout_time"))
        if not reason:
            continue
        full_name = frappe.db.get_value("User", user, "full_name") or user
        try:
            frappe.sendmail(
                recipients=[user],
                subject=_("Reminder: missing {0} on {1}").format(reason, rd_str),
                message=_build_checkin_reminder_html(full_name, reason, rd_str),
                now=True,
            )
            sent += 1
        except Exception:
            frappe.log_error(
                title=f"Check-in reminder email failed for {user}",
                message=frappe.get_traceback(),
            )
    frappe.db.commit()
    return {"sent": sent, "date": rd_str}


def _build_checkin_reminder_html(full_name, reason, date_str):
    label = "check-in and check-out" if reason == "check-in" else "check-out"
    return f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; max-width:520px; margin:0 auto; background:#f5f6f8; padding:24px;">
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;">
        <tr>
          <td bgcolor="#dc2626" style="background-color:#dc2626; padding:20px 28px; border-radius:12px 12px 0 0;">
            <div style="font-size:12px; letter-spacing:1px; text-transform:uppercase; color:#fee2e2;">Next PMS &middot; Attendance Reminder</div>
            <div style="font-size:20px; font-weight:800; margin-top:6px; color:#ffffff;">Hi {full_name},</div>
          </td>
        </tr>
      </table>
      <div style="background:#ffffff; border-radius:0 0 12px 12px; padding:22px 28px; color:#374151; font-size:14px; line-height:1.6;">
        <p style="margin:0 0 12px;">Our records show no <strong>{label}</strong> for you on <strong>{date_str}</strong>.</p>
        <p style="margin:0 0 12px;">Please remember to check in when you start and check out when you finish &mdash; it keeps your work hours and weekly summary accurate.</p>
        <p style="margin:16px 0 0; color:#9ca3af; font-size:12px;">Automated attendance reminder from Next PMS. If you were on leave or this is a mistake, please update your check-in record.</p>
      </div>
    </div>
    """
