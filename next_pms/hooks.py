app_name = "next_pms"
app_title = "Next PMS"
app_publisher = "EFTPMS"
app_description = "IT Project Management System"
app_email = "info@eftpms.com"
app_license = "MIT"

required_apps = []

app_include_css = ["/assets/next_pms/css/pms.css"]
app_include_js = ["/assets/next_pms/js/pms.bundle.js"]

after_install = "next_pms.setup.install.after_install"

# Add Service-Worker-Allowed header for PWA
after_request = ["next_pms.utils.add_sw_headers"]

doc_events = {
    "PMS Time Log": {
        "after_insert": "next_pms.next_pms.doctype.pms_time_log.pms_time_log.on_time_log_change",
        "on_update": "next_pms.next_pms.doctype.pms_time_log.pms_time_log.on_time_log_change",
        "on_trash": "next_pms.next_pms.doctype.pms_time_log.pms_time_log.on_time_log_change",
    },
    "PMS Task": {
        "on_update": "next_pms.next_pms.doctype.pms_task.pms_task.on_task_update",
    },
}

permission_query_conditions = {
    "PMS Project": "next_pms.api.permissions.project_query_conditions",
    "PMS Task": "next_pms.api.permissions.task_query_conditions",
}

has_permission = {
    "PMS Project": "next_pms.api.permissions.has_project_permission",
    "PMS Task": "next_pms.api.permissions.has_task_permission",
}

scheduler_events = {
    "daily": [
        "next_pms.tasks.send_deadline_reminders",
        "next_pms.tasks.check_budget_alerts",
    ],
    "hourly": [
        "next_pms.tasks.check_long_running_timers",
    ],
    "cron": {
        "0 3 * * *": [
            "next_pms.api.ai_report.generate_daily_report",
        ],
        "0 8 * * 1-6": [
            "next_pms.api.project_report.send_scheduled_project_reports",
            "next_pms.api.project_report.send_scheduled_multi_project_reports",
        ],
        "0 7 * * 6": [
            "next_pms.tasks.send_weekly_summary",
        ],
    },
}

website_route_rules = [
    {"from_route": "/next-pms/<path:app_path>", "to_route": "next-pms"},
]

fixtures = [
    {
        "doctype": "Role",
        "filters": [["name", "in", ["Next PMS", "PMS Customer"]]],
    },
]
