import frappe
import json
import requests
from frappe.utils import today, now_datetime, get_url_to_form


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

    if not settings.get("daily_report_recipient"):
        return {"success": False, "message": "No recipient email set."}

    # Gather work data
    work_data = get_daily_work_summary()

    if not work_data.get("time_logs") and not work_data.get("status_changes"):
        return {"success": False, "message": "No work data found for today."}

    # Call LLM
    try:
        ai_analysis = _call_llm(settings, work_data)
    except Exception as e:
        frappe.log_error(f"PMS AI Report: LLM call failed - {str(e)}")
        ai_analysis = f"AI analysis unavailable: {str(e)}"

    # Send email
    _send_report_email(settings, work_data, ai_analysis)

    return {"success": True, "message": "Daily AI report sent."}


def _get_ai_settings():
    """Read AI settings from the Single DocType."""
    try:
        doc = frappe.get_single("PMS AI Settings")
        return {
            "ai_provider": doc.ai_provider or "OpenAI",
            "ai_api_key": doc.get_password("ai_api_key") if doc.ai_api_key else None,
            "ai_model": doc.ai_model or "gpt-4o",
            "daily_report_enabled": bool(doc.daily_report_enabled),
            "daily_report_recipient": doc.daily_report_recipient or "",
        }
    except Exception:
        return None


def get_daily_work_summary():
    """Gather all work data for today."""
    report_date = today()

    # 1. Time logs from today
    time_logs = frappe.db.sql("""
        SELECT
            tl.name, tl.user, tl.task, tl.start_time, tl.end_time,
            tl.duration_hours, tl.duration_minutes, tl.is_running, tl.notes,
            t.task_title, t.project, t.estimated_hours, t.actual_hours,
            t.status as task_status, t.priority,
            p.project_name
        FROM `tabPMS Time Log` tl
        LEFT JOIN `tabPMS Task` t ON t.name = tl.task
        LEFT JOIN `tabPMS Project` p ON p.name = t.project
        WHERE DATE(tl.start_time) = %s
        ORDER BY tl.user, tl.start_time
    """, (report_date,), as_dict=True)

    # 2. Tasks that changed status today
    status_changes = frappe.db.sql("""
        SELECT
            t.name, t.task_title, t.status, t.project,
            t.assigned_to, t.estimated_hours, t.actual_hours,
            p.project_name,
            t.modified_by
        FROM `tabPMS Task` t
        LEFT JOIN `tabPMS Project` p ON p.name = t.project
        WHERE DATE(t.modified) = %s
        ORDER BY t.modified DESC
    """, (report_date,), as_dict=True)

    # 3. Per-user aggregation
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

    # Convert sets to lists for JSON serialization
    for u in user_stats.values():
        u["tasks_worked"] = list(u["tasks_worked"])
        u["total_hours"] = round(u["total_hours"], 2)

    # 4. Overall stats
    active_projects = frappe.db.count("PMS Project", {"status": "Active"})
    tasks_completed_today = frappe.db.count(
        "PMS Task",
        {"status": "Done", "modified": [">=", f"{report_date} 00:00:00"], "modified": ["<=", f"{report_date} 23:59:59"]},
    )

    return {
        "date": report_date,
        "time_logs": [
            {
                "user": log.user,
                "task": log.task_title or log.task,
                "project": log.project_name or log.project,
                "hours": round((log.duration_hours or 0), 2),
                "estimated_hours": log.estimated_hours,
                "actual_hours": log.actual_hours,
                "is_running": log.is_running,
                "notes": log.notes,
                "priority": log.priority,
            }
            for log in time_logs
        ],
        "status_changes": [
            {
                "task": sc.task_title,
                "project": sc.project_name or sc.project,
                "status": sc.status,
                "assigned_to": sc.assigned_to,
                "estimated_hours": sc.estimated_hours,
                "actual_hours": sc.actual_hours,
            }
            for sc in status_changes[:50]  # Limit to 50
        ],
        "user_activity": list(user_stats.values()),
        "overall": {
            "active_projects": active_projects,
            "tasks_completed_today": tasks_completed_today,
            "total_time_logged": round(sum(u["total_hours"] for u in user_stats.values()), 2),
            "active_users": len(user_stats),
        },
    }


def _call_llm(settings, work_data):
    """Call the configured LLM provider with the work data for analysis."""
    prompt = _build_analysis_prompt(work_data)
    provider = settings.get("ai_provider", "OpenAI")
    api_key = settings.get("ai_api_key")
    model = settings.get("ai_model", "gpt-4o")

    if provider == "OpenAI":
        return _call_openai(api_key, model, prompt)
    elif provider == "Claude":
        return _call_claude(api_key, model, prompt)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")


def _build_analysis_prompt(work_data):
    """Build the analysis prompt with structured work data."""
    data_json = json.dumps(work_data, indent=2, default=str)

    return f"""You are an AI project management analyst. Analyze the following daily work summary data and provide a concise, actionable report.

## Work Data for {work_data['date']}
{data_json}

## Please provide:
1. **Team Performance Summary** (2-3 sentences): Overall team productivity assessment
2. **Individual Performance** (brief per-user summary): Hours logged, tasks worked on, efficiency
3. **Tasks Exceeding Estimates**: Flag any tasks where actual hours significantly exceed estimated hours
4. **Potential Bottlenecks**: Identify any concerning patterns (e.g., tasks stuck too long, uneven workload)
5. **Recommendations**: 2-3 actionable suggestions for improvement

Keep the analysis concise but insightful. Use bullet points where helpful. Focus on actionable insights rather than just restating the data."""


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
                {"role": "system", "content": "You are a helpful project management analyst."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2000,
            "temperature": 0.7,
        },
        timeout=60,
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
            "max_tokens": 2000,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["content"][0]["text"]


def _send_report_email(settings, work_data, ai_analysis):
    """Render and send the daily AI report email."""
    recipient = settings.get("daily_report_recipient")
    report_date = work_data.get("date", today())

    # Build user activity table data
    user_activity = work_data.get("user_activity", [])

    message = frappe.render_template(
        "next_pms/templates/emails/daily_ai_report.html",
        {
            "report_date": report_date,
            "overall": work_data.get("overall", {}),
            "ai_analysis": ai_analysis,
            "user_activity": user_activity,
        },
    )

    frappe.sendmail(
        recipients=[recipient],
        subject=f"PMS Daily AI Report - {report_date}",
        message=message,
        now=True,
    )
