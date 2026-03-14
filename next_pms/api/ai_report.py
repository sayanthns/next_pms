import frappe
import json
import requests
from frappe.utils import today, now_datetime, getdate, format_date
from next_pms.utils import get_pms_url
from collections import defaultdict


@frappe.whitelist()
def generate_daily_report():
    """Generate and send the AI daily work summary email.
    Called by scheduler daily or manually via the settings UI.
    """
    settings = _get_ai_settings()
    if not settings:
        return {"success": False, "message": "AI settings not configured."}

    if not settings.get("daily_report_enabled") and not frappe.flags.force_ai_report:
        return {"success": False, "message": "Daily report is disabled."}

    if not settings.get("ai_api_key"):
        return {"success": False, "message": "API key not set."}

    recipients = _get_recipients(settings)
    if not recipients:
        return {"success": False, "message": "No recipient email set."}

    # Gather comprehensive work data
    report_date = today()
    work_data = get_daily_work_summary(report_date)
    user_metrics = _build_user_metrics(report_date)
    process_mining = _get_process_mining_data(report_date)
    time_patterns = _get_time_patterns(report_date)
    project_summary = _get_project_summary(report_date)

    # Build full data context for AI
    full_data = {
        "date": report_date,
        "overall": work_data.get("overall", {}),
        "user_metrics": user_metrics,
        "process_mining": process_mining,
        "time_patterns": time_patterns,
        "project_summary": project_summary,
    }

    # Call LLM for intelligent analysis
    detail_level = settings.get("report_detail_level", "Detailed")
    ai_parsed = None
    ai_raw = ""
    try:
        ai_raw = _call_llm(settings, full_data, detail_level)
        ai_parsed = _parse_ai_response(ai_raw)
    except Exception as e:
        frappe.log_error(f"PMS AI Report: LLM call failed - {str(e)}")
        ai_parsed = None
        ai_raw = f"AI analysis unavailable: {str(e)}"

    # Send email to all recipients
    _send_report_email(recipients, full_data, ai_parsed, ai_raw, user_metrics,
                       process_mining, time_patterns, project_summary)

    return {"success": True, "message": f"Daily AI report sent to {len(recipients)} recipient(s)."}


def _get_ai_settings():
    """Read AI settings from the Single DocType."""
    try:
        doc = frappe.get_single("PMS AI Settings")
        return {
            "ai_provider": doc.ai_provider or "Claude",
            "ai_api_key": doc.get_password("ai_api_key") if doc.ai_api_key else None,
            "ai_model": doc.ai_model or "claude-sonnet-4-20250514",
            "daily_report_enabled": bool(doc.daily_report_enabled),
            "daily_report_recipient": doc.daily_report_recipient or "",
            "daily_report_recipients": doc.daily_report_recipients or "",
            "report_detail_level": doc.report_detail_level or "Detailed",
        }
    except Exception:
        return None


def _get_recipients(settings):
    """Build list of unique email recipients."""
    recipients = []
    primary = (settings.get("daily_report_recipient") or "").strip()
    if primary:
        recipients.append(primary)
    additional = settings.get("daily_report_recipients") or ""
    for email in additional.split(","):
        email = email.strip()
        if email and email not in recipients:
            recipients.append(email)
    return recipients


def get_daily_work_summary(report_date=None):
    """Gather overall work data for today."""
    if not report_date:
        report_date = today()

    # Time logs from today
    time_logs = frappe.db.sql("""
        SELECT
            tl.user, tl.task, tl.duration_hours, tl.is_running,
            t.task_title, t.project, t.estimated_hours, t.actual_hours,
            t.status as task_status, t.priority,
            p.project_name
        FROM `tabPMS Time Log` tl
        LEFT JOIN `tabPMS Task` t ON t.name = tl.task
        LEFT JOIN `tabPMS Project` p ON p.name = t.project
        WHERE DATE(tl.start_time) = %s
        ORDER BY tl.user, tl.start_time
    """, (report_date,), as_dict=True)

    # Per-user aggregation
    user_stats = {}
    for log in time_logs:
        user = log.user
        if user not in user_stats:
            user_stats[user] = {
                "user": user,
                "full_name": frappe.db.get_value("User", user, "full_name") or user,
                "total_hours": 0,
                "tasks_worked": set(),
            }
        user_stats[user]["total_hours"] += (log.duration_hours or 0)
        if log.task:
            user_stats[user]["tasks_worked"].add(log.task_title or log.task)

    for u in user_stats.values():
        u["tasks_worked"] = list(u["tasks_worked"])
        u["total_hours"] = round(u["total_hours"], 2)

    # Overall stats
    active_projects = frappe.db.count("PMS Project", {"status": "Active"})
    tasks_completed_today = frappe.db.sql("""
        SELECT COUNT(*) as cnt FROM `tabPMS Task`
        WHERE status = 'Done'
        AND DATE(modified) = %s
    """, (report_date,))[0][0] or 0

    total_tasks_modified = frappe.db.sql("""
        SELECT COUNT(*) as cnt FROM `tabPMS Task`
        WHERE DATE(modified) = %s
    """, (report_date,))[0][0] or 0

    return {
        "date": report_date,
        "user_activity": list(user_stats.values()),
        "overall": {
            "active_projects": active_projects,
            "tasks_completed_today": tasks_completed_today,
            "total_tasks_modified": total_tasks_modified,
            "total_time_logged": round(sum(u["total_hours"] for u in user_stats.values()), 2),
            "active_users": len(user_stats),
        },
    }


def _build_user_metrics(report_date):
    """Build comprehensive per-user productivity metrics."""
    users = frappe.db.sql("""
        SELECT DISTINCT user FROM (
            SELECT user FROM `tabPMS Time Log` WHERE DATE(start_time) = %s
            UNION
            SELECT assigned_to as user FROM `tabPMS Task`
            WHERE DATE(modified) = %s AND assigned_to IS NOT NULL AND assigned_to != ''
        ) combined
    """, (report_date, report_date), as_dict=True)

    user_list = [u.user for u in users]
    if not user_list:
        return []

    # Batch load user names
    user_names = {}
    for u in frappe.db.sql(
        "SELECT name, full_name FROM `tabUser` WHERE name IN %s", [user_list], as_dict=True
    ):
        user_names[u.name] = u.full_name or u.name

    metrics = []
    for user in user_list:
        full_name = user_names.get(user, user)

        # Tasks allocated (assigned to this user, modified today or currently active)
        tasks_allocated = frappe.db.count("PMS Task", {
            "assigned_to": user,
            "status": ["not in", ["Done", "Cancelled"]],
        })

        # Tasks completed today
        tasks_completed = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabPMS Task`
            WHERE assigned_to = %s AND status = 'Done' AND DATE(modified) = %s
        """, (user, report_date))[0][0] or 0

        # Tasks in progress
        tasks_in_progress = frappe.db.count("PMS Task", {
            "assigned_to": user,
            "status": ["in", ["In Progress", "In Review"]],
        })

        # Hours: estimated vs actual for tasks assigned to user
        hours_data = frappe.db.sql("""
            SELECT
                COALESCE(SUM(estimated_hours), 0) as est,
                COALESCE(SUM(actual_hours), 0) as actual
            FROM `tabPMS Task`
            WHERE assigned_to = %s AND status != 'Cancelled'
        """, (user,), as_dict=True)[0]

        # Time logged today
        time_today = frappe.db.sql("""
            SELECT COALESCE(SUM(duration_hours), 0) as hours
            FROM `tabPMS Time Log`
            WHERE user = %s AND DATE(start_time) = %s AND is_running = 0
        """, (user, report_date))[0][0] or 0

        # Check-in/out from PMS Checkin
        checkin_data = frappe.db.sql("""
            SELECT checkin_time, checkout_time, total_hours
            FROM `tabPMS Checkin`
            WHERE user = %s AND date = %s
            LIMIT 1
        """, (user, report_date), as_dict=True)

        checkin_info = checkin_data[0] if checkin_data else {}

        # Productivity score
        est_hours = float(hours_data.est or 0)
        actual_hours = float(hours_data.actual or 0)
        productivity = round((actual_hours / est_hours * 100), 1) if est_hours > 0 else 0

        metrics.append({
            "user": user,
            "full_name": full_name,
            "tasks_allocated": tasks_allocated,
            "tasks_completed": tasks_completed,
            "tasks_in_progress": tasks_in_progress,
            "estimated_hours": round(est_hours, 2),
            "actual_hours": round(actual_hours, 2),
            "hours_logged_today": round(float(time_today), 2),
            "productivity_pct": productivity,
            "checkin_time": str(checkin_info.get("checkin_time", "")) if checkin_info.get("checkin_time") else "-",
            "checkout_time": str(checkin_info.get("checkout_time", "")) if checkin_info.get("checkout_time") else "-",
            "office_hours": round(float(checkin_info.get("total_hours", 0)), 2) if checkin_info.get("total_hours") else 0,
        })

    return metrics


def _get_process_mining_data(report_date):
    """Extract process mining insights from Version audit trail.
    Analyzes task status transitions for workflow discovery and anomaly detection.
    """
    # Get all version logs for PMS Task modified today
    versions = frappe.db.sql("""
        SELECT v.data, v.creation, v.owner, v.docname
        FROM `tabVersion` v
        WHERE v.ref_doctype = 'PMS Task'
        AND DATE(v.creation) = %s
        ORDER BY v.creation
    """, (report_date,), as_dict=True)

    # Expected workflow order
    expected_flow = ["Backlog", "To Do", "In Progress", "In Review", "Done"]
    expected_indices = {s: i for i, s in enumerate(expected_flow)}

    transitions = defaultdict(int)
    skipped_stages = []
    rework_loops = []
    stage_durations = defaultdict(list)

    for ver in versions:
        try:
            data = json.loads(ver.data)
        except (json.JSONDecodeError, TypeError):
            continue

        for change in data.get("changed", []):
            if len(change) >= 3 and change[0] == "status":
                old_status = change[1]
                new_status = change[2]
                task_name = ver.docname

                # Count transition
                transition_key = f"{old_status} -> {new_status}"
                transitions[transition_key] += 1

                # Detect skipped stages
                old_idx = expected_indices.get(old_status, -1)
                new_idx = expected_indices.get(new_status, -1)
                if old_idx >= 0 and new_idx >= 0 and (new_idx - old_idx) > 1:
                    task_title = frappe.db.get_value("PMS Task", task_name, "task_title") or task_name
                    skipped_stages.append({
                        "task": task_title,
                        "from": old_status,
                        "to": new_status,
                        "skipped": [expected_flow[i] for i in range(old_idx + 1, new_idx)],
                    })

                # Detect rework (going backwards)
                if old_idx >= 0 and new_idx >= 0 and new_idx < old_idx:
                    task_title = frappe.db.get_value("PMS Task", task_name, "task_title") or task_name
                    rework_loops.append({
                        "task": task_title,
                        "from": old_status,
                        "to": new_status,
                    })

    # Stale tasks — tasks in progress with no activity for 3+ days
    stale_tasks = frappe.db.sql("""
        SELECT t.name, t.task_title, t.status, t.assigned_to, t.modified,
               DATEDIFF(%s, t.modified) as days_stale,
               p.project_name
        FROM `tabPMS Task` t
        LEFT JOIN `tabPMS Project` p ON p.name = t.project
        WHERE t.status IN ('In Progress', 'In Review')
        AND DATEDIFF(%s, t.modified) >= 3
        ORDER BY days_stale DESC
        LIMIT 20
    """, (report_date, report_date), as_dict=True)

    return {
        "transitions": dict(transitions),
        "total_transitions": sum(transitions.values()),
        "skipped_stages": skipped_stages[:10],
        "rework_loops": rework_loops[:10],
        "stale_tasks": [
            {
                "task": s.task_title or s.name,
                "status": s.status,
                "assigned_to": s.assigned_to,
                "days_stale": s.days_stale,
                "project": s.project_name or "",
            }
            for s in stale_tasks
        ],
    }


def _get_time_patterns(report_date):
    """Analyze time logging patterns for productivity insights."""
    # Hourly distribution of time log starts
    hourly = frappe.db.sql("""
        SELECT HOUR(start_time) as hr, COUNT(*) as cnt
        FROM `tabPMS Time Log`
        WHERE DATE(start_time) = %s
        GROUP BY HOUR(start_time)
        ORDER BY hr
    """, (report_date,), as_dict=True)

    hourly_dist = {str(h.hr): h.cnt for h in hourly}

    # Find peak hours
    peak_hour = max(hourly_dist, key=hourly_dist.get) if hourly_dist else None
    peak_label = f"{int(peak_hour)}:00 - {int(peak_hour)+1}:00" if peak_hour else "N/A"

    # Overtime: time logs after 6 PM
    overtime_users = frappe.db.sql("""
        SELECT DISTINCT user FROM `tabPMS Time Log`
        WHERE DATE(start_time) = %s AND HOUR(start_time) >= 18
    """, (report_date,), as_dict=True)

    overtime_names = []
    for u in overtime_users:
        name = frappe.db.get_value("User", u.user, "full_name") or u.user
        overtime_names.append(name)

    # Average task completion time vs estimate (for tasks completed today)
    completion_data = frappe.db.sql("""
        SELECT
            AVG(CASE WHEN estimated_hours > 0 THEN actual_hours / estimated_hours ELSE NULL END) as avg_ratio,
            COUNT(*) as completed_count
        FROM `tabPMS Task`
        WHERE status = 'Done' AND DATE(modified) = %s AND estimated_hours > 0
    """, (report_date,), as_dict=True)[0]

    avg_ratio = round(float(completion_data.avg_ratio or 0) * 100, 1)

    # Total unique tasks worked on today
    tasks_worked = frappe.db.sql("""
        SELECT COUNT(DISTINCT task) as cnt FROM `tabPMS Time Log`
        WHERE DATE(start_time) = %s AND task IS NOT NULL
    """, (report_date,))[0][0] or 0

    return {
        "hourly_distribution": hourly_dist,
        "peak_hour": peak_label,
        "overtime_users": overtime_names,
        "overtime_count": len(overtime_names),
        "avg_completion_ratio_pct": avg_ratio,
        "tasks_worked_on": tasks_worked,
    }


def _get_project_summary(report_date):
    """Per-project summary: tasks done, hours logged, budget utilization."""
    projects = frappe.db.sql("""
        SELECT
            p.name, p.project_name, p.status, p.total_budget,
            (SELECT COUNT(*) FROM `tabPMS Task` t
             WHERE t.project = p.name AND t.status = 'Done' AND DATE(t.modified) = %s) as tasks_done_today,
            (SELECT COALESCE(SUM(tl.duration_hours), 0) FROM `tabPMS Time Log` tl
             JOIN `tabPMS Task` t2 ON t2.name = tl.task
             WHERE t2.project = p.name AND DATE(tl.start_time) = %s) as hours_today,
            (SELECT COUNT(*) FROM `tabPMS Task` t3
             WHERE t3.project = p.name AND t3.status NOT IN ('Done', 'Cancelled')) as open_tasks,
            p.calculated_cost
        FROM `tabPMS Project` p
        WHERE p.status = 'Active'
        ORDER BY p.project_name
    """, (report_date, report_date), as_dict=True)

    result = []
    for proj in projects:
        budget = float(proj.total_budget or 0)
        cost = float(proj.calculated_cost or 0)
        budget_pct = round((cost / budget * 100), 1) if budget > 0 else 0

        # Only include projects with activity today or open tasks
        if proj.tasks_done_today or proj.hours_today or proj.open_tasks:
            result.append({
                "project": proj.project_name or proj.name,
                "tasks_done_today": proj.tasks_done_today or 0,
                "hours_today": round(float(proj.hours_today or 0), 2),
                "open_tasks": proj.open_tasks or 0,
                "budget_pct": budget_pct,
            })

    return result


# ── LLM Integration ─────────────────────────────────────────────


def _call_llm(settings, full_data, detail_level="Detailed"):
    """Call the configured LLM provider with comprehensive data."""
    prompt = _build_analysis_prompt(full_data, detail_level)
    provider = settings.get("ai_provider", "Claude")
    api_key = settings.get("ai_api_key")
    model = settings.get("ai_model", "claude-sonnet-4-20250514")

    if provider == "OpenAI":
        return _call_openai(api_key, model, prompt)
    elif provider == "Claude":
        return _call_claude(api_key, model, prompt)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")


def _build_analysis_prompt(full_data, detail_level="Detailed"):
    """Build a structured prompt that returns JSON for clean email rendering."""
    data_json = json.dumps(full_data, indent=2, default=str)

    detail_instructions = {
        "Summary": "Keep each section brief (2-3 sentences). Skip minor details.",
        "Detailed": "Provide moderate detail with key metrics and specific task/user names.",
        "Full": "Provide thorough analysis with all data points and detailed reasoning.",
    }

    return f"""You are an expert IT project management analyst. Analyze this daily work data and return a structured JSON response.

## Work Data for {full_data['date']}
{data_json}

## Detail Level: {detail_level}
{detail_instructions.get(detail_level, detail_instructions["Detailed"])}

## IMPORTANT: Return ONLY valid JSON (no markdown, no code fences). Use this exact structure:

{{
  "executive_summary": "3-4 sentences about the day's overall productivity and critical flags.",
  "user_assessments": [
    {{
      "name": "User Full Name",
      "rating": "Good|Average|Needs Attention|Critical",
      "summary": "Brief assessment of their day's work, tasks, hours, attendance."
    }}
  ],
  "process_insights": [
    "Insight about workflow transitions, skipped stages, rework loops, or stale tasks."
  ],
  "time_analysis": [
    "Insight about peak hours, overtime, completion speed, idle patterns."
  ],
  "bottlenecks": [
    {{
      "severity": "High|Medium|Low",
      "issue": "Description of the bottleneck or risk."
    }}
  ],
  "recommendations": [
    {{
      "priority": 1,
      "action": "Specific, concrete recommendation for tomorrow."
    }}
  ]
}}

Rules:
- user_assessments: one entry per active user found in the data. Rating must be exactly one of: Good, Average, Needs Attention, Critical.
- process_insights: 2-5 bullet points about workflow health.
- time_analysis: 2-4 bullet points about time patterns.
- bottlenecks: top 3 risks, sorted by severity.
- recommendations: 3-5 prioritized actions, numbered starting at 1.
- Return ONLY the JSON object. No explanation, no markdown fences."""


def _call_openai(api_key, model, prompt):
    """Call OpenAI API."""
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert project management analyst with process mining expertise."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 3000,
            "temperature": 0.7,
        },
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _call_claude(api_key, model, prompt):
    """Call Anthropic Claude API."""
    if not model or model == "gpt-4o":
        model = "claude-sonnet-4-20250514"

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 3000,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        },
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    return data["content"][0]["text"]


# ── Response Parsing ─────────────────────────────────────────────

import re


def _parse_ai_response(raw_text):
    """Parse the AI JSON response. Handles markdown code fences gracefully."""
    text = raw_text.strip()
    # Strip markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            parsed = json.loads(match.group())
        else:
            return None

    # Validate expected keys exist
    expected_keys = ["executive_summary", "recommendations"]
    if not any(k in parsed for k in expected_keys):
        return None

    return parsed


# ── Email Delivery ───────────────────────────────────────────────


def _send_report_email(recipients, full_data, ai_parsed, ai_raw, user_metrics,
                       process_mining, time_patterns, project_summary):
    """Render and send the comprehensive daily AI report email."""
    report_date = full_data.get("date", today())

    message = frappe.render_template(
        "next_pms/templates/emails/daily_ai_report.html",
        {
            "report_date": report_date,
            "overall": full_data.get("overall", {}),
            "ai": ai_parsed,
            "ai_raw": ai_raw,
            "user_metrics": user_metrics,
            "process_mining": process_mining,
            "time_patterns": time_patterns,
            "project_summary": project_summary,
        },
    )

    frappe.sendmail(
        recipients=recipients,
        subject=f"NextPMS Daily Productivity Report - {report_date}",
        message=message,
        now=True,
    )
