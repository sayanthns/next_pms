import frappe
from frappe.utils import today, add_days, add_months, now_datetime
import random


def create_demo_data():
    """Create demo data for Next PMS testing."""
    if frappe.db.count("PMS Project") > 0:
        print("Demo data already exists. Skipping.")
        return

    print("Creating demo data...")

    # Ensure roles exist
    for role in ["PMS Manager", "PMS Developer", "PMS Viewer"]:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert()

    # Get existing users or use Administrator
    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        pluck="name",
        limit=5,
    )
    if not users:
        users = ["Administrator"]

    admin = users[0]
    developers = users[1:] if len(users) > 1 else [admin]

    # Create Activity Rates
    rates = [
        {"activity_name": "Development", "rate_per_hour": 150},
        {"activity_name": "Design", "rate_per_hour": 120},
        {"activity_name": "QA Testing", "rate_per_hour": 100},
        {"activity_name": "Project Management", "rate_per_hour": 175},
        {"activity_name": "Documentation", "rate_per_hour": 80},
    ]
    for rate_data in rates:
        rate = frappe.new_doc("PMS Activity Rate")
        rate.update(rate_data)
        rate.insert(ignore_permissions=True)

    # Create Projects
    projects_data = [
        {
            "project_name": "E-Commerce Platform Redesign",
            "status": "Active",
            "total_budget": 50000,
            "description": "<p>Complete redesign of the client's e-commerce platform including new UI, payment integration, and mobile responsiveness.</p>",
        },
        {
            "project_name": "Mobile Banking App",
            "status": "Active",
            "total_budget": 75000,
            "description": "<p>Native mobile banking application with biometric auth, transaction history, and fund transfers.</p>",
        },
        {
            "project_name": "CRM Integration Suite",
            "status": "Planning",
            "total_budget": 30000,
            "description": "<p>Integration of multiple CRM systems with custom API middleware and data sync.</p>",
        },
    ]

    for proj_data in projects_data:
        project = frappe.new_doc("PMS Project")
        project.project_name = proj_data["project_name"]
        project.client = (
            frappe.get_all("Customer", limit=1, pluck="name")[0]
            if frappe.get_all("Customer", limit=1)
            else None
        )
        project.project_manager = admin
        project.status = proj_data["status"]
        project.start_date = add_days(today(), -30)
        project.end_date = add_months(today(), 3)
        project.total_budget = proj_data["total_budget"]
        project.description = proj_data["description"]
        project.client_portal_enabled = 1

        # Add team members
        for dev in developers:
            project.append(
                "team_members",
                {
                    "user": dev,
                    "role": random.choice(["Developer", "Designer", "QA", "Lead"]),
                    "hourly_rate": random.choice([100, 120, 150, 175]),
                },
            )

        project.insert(ignore_permissions=True)

        # Create Sprints
        sprint_statuses = ["Completed", "Active", "Planned"]
        for i, sprint_status in enumerate(sprint_statuses):
            sprint = frappe.new_doc("PMS Sprint")
            sprint.sprint_name = f"Sprint {i + 1}"
            sprint.project = project.name
            sprint.start_date = add_days(today(), -30 + (i * 14))
            sprint.end_date = add_days(sprint.start_date, 13)
            sprint.status = sprint_status
            sprint.goal = f"Sprint {i + 1} goals for {project.project_name}"
            sprint.insert(ignore_permissions=True)

            # Create Tasks per sprint
            task_templates = [
                ("Setup project architecture", "Feature", "Done", "High"),
                ("Design database schema", "Feature", "Done", "High"),
                (
                    "Implement user authentication",
                    "Feature",
                    "In Progress",
                    "Critical",
                ),
                ("Create API endpoints", "Feature", "In Progress", "High"),
                ("Write unit tests", "Research", "To Do", "Medium"),
                ("UI component library", "Feature", "In Review", "Medium"),
                ("Performance optimization", "Improvement", "Backlog", "Low"),
                ("Bug: login redirect loop", "Bug", "In Progress", "Critical"),
                ("Documentation update", "Documentation", "To Do", "Low"),
                ("Code review fixes", "Improvement", "Done", "Medium"),
            ]

            for j, (title, task_type, status, priority) in enumerate(
                task_templates[: random.randint(3, 7)]
            ):
                task = frappe.new_doc("PMS Task")
                task.task_title = f"{title} - {project.project_name[:20]}"
                task.project = project.name
                task.sprint = sprint.name
                task.assigned_to = random.choice(developers)
                task.priority = priority
                task.status = status if sprint_status != "Planned" else "Backlog"
                task.task_type = task_type
                task.estimated_hours = random.choice([2, 4, 8, 16, 24])
                task.start_date = add_days(sprint.start_date, random.randint(0, 5))
                task.due_date = add_days(task.start_date, random.randint(2, 10))
                task.hourly_rate = random.choice([100, 120, 150])
                task.is_billable = 1
                task.description = (
                    f"<p>Task: {title}</p>"
                    f"<p>Part of {sprint.sprint_name} in {project.project_name}.</p>"
                )
                task.insert(ignore_permissions=True)

                # Create time logs for completed/in-progress tasks
                if status in ["Done", "In Progress", "In Review"]:
                    hours_logged = random.uniform(
                        1, float(task.estimated_hours or 8)
                    )
                    log = frappe.new_doc("PMS Time Log")
                    log.task = task.name
                    log.user = task.assigned_to
                    log.start_time = add_days(
                        now_datetime(), -random.randint(1, 20)
                    )
                    from frappe.utils import add_to_date

                    log.end_time = add_to_date(
                        log.start_time, hours=hours_logged
                    )
                    log.is_running = 0
                    log.duration_hours = round(hours_logged, 2)
                    log.duration_minutes = int(hours_logged * 60)
                    log.notes = f"Worked on {title}"
                    log.insert(ignore_permissions=True)

        # Create Client Portal Access
        portal = frappe.new_doc("PMS Client Portal Access")
        portal.project = project.name
        portal.client_email = "client@example.com"
        portal.is_active = 1
        portal.insert(ignore_permissions=True)
        print(
            f"  Portal token for {project.project_name}: {portal.access_token}"
        )

    frappe.db.commit()
    print(
        f"Demo data created: {len(projects_data)} projects with sprints, tasks, and time logs."
    )
