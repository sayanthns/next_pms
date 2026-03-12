import frappe
from next_pms.api.permissions import get_user_projects, check_project_access, get_current_user_feature_permissions


@frappe.whitelist()
def get_project_dashboard(project):
    """Return aggregated stats for a project: task counts by status,
    total hours, cost breakdown, sprint progress.
    """
    check_project_access(project)

    # Task counts by status
    task_counts = {}
    statuses = ["Backlog", "To Do", "In Progress", "In Review", "Done"]
    for status in statuses:
        count = frappe.db.count("PMS Task", {"project": project, "status": status})
        task_counts[status] = count

    total_tasks = sum(task_counts.values())

    # Hours and cost
    tasks = frappe.get_all(
        "PMS Task",
        filters={"project": project},
        fields=[
            "sum(estimated_hours) as total_estimated",
            "sum(actual_hours) as total_actual",
            "sum(calculated_cost) as total_cost",
        ],
    )

    hours_data = tasks[0] if tasks else {}

    # Project budget info
    project_doc = frappe.get_doc("PMS Project", project)

    # Sprint progress
    sprints = frappe.get_all(
        "PMS Sprint",
        filters={"project": project},
        fields=["name", "sprint_name", "status", "start_date", "end_date"],
        order_by="start_date asc",
    )

    sprint_data = []
    for sprint in sprints:
        sprint_tasks = frappe.db.count("PMS Task", {"sprint": sprint.name})
        sprint_done = frappe.db.count(
            "PMS Task", {"sprint": sprint.name, "status": "Done"}
        )
        sprint_data.append(
            {
                "name": sprint.name,
                "sprint_name": sprint.sprint_name,
                "status": sprint.status,
                "start_date": str(sprint.start_date) if sprint.start_date else None,
                "end_date": str(sprint.end_date) if sprint.end_date else None,
                "total_tasks": sprint_tasks,
                "done_tasks": sprint_done,
                "progress": round((sprint_done / sprint_tasks * 100), 1) if sprint_tasks else 0,
            }
        )

    # Team utilization
    team_members = []
    for member in project_doc.team_members:
        member_hours = frappe.get_all(
            "PMS Time Log",
            filters={
                "user": member.user,
                "task": ["in", frappe.get_all("PMS Task", filters={"project": project}, pluck="name") or [""]],
                "is_running": 0,
            },
            fields=["sum(duration_hours) as total_hours"],
        )
        total_hours = (member_hours[0].total_hours or 0) if member_hours else 0
        member_cost = total_hours * (member.hourly_rate or 0)
        team_members.append(
            {
                "user": member.user,
                "role": member.role,
                "hourly_rate": member.hourly_rate,
                "total_hours": round(total_hours, 2),
                "total_cost": round(member_cost, 2),
            }
        )

    # Budget info
    budget_remaining = (project_doc.total_budget or 0) - (project_doc.calculated_cost or 0)

    return {
        "project": project,
        "project_name": project_doc.project_name,
        "status": project_doc.status,
        "task_counts": task_counts,
        "total_tasks": total_tasks,
        "total_estimated_hours": hours_data.get("total_estimated") or 0,
        "total_actual_hours": hours_data.get("total_actual") or 0,
        "total_cost": hours_data.get("total_cost") or 0,
        "total_budget": project_doc.total_budget or 0,
        "calculated_cost": project_doc.calculated_cost or 0,
        "budget_utilization": project_doc.budget_utilization or 0,
        "budget_remaining": round(budget_remaining, 2),
        "sprints": sprint_data,
        "team_members": team_members,
    }


@frappe.whitelist()
def get_all_projects_summary():
    """Return summary of all projects for the dashboard overview."""
    allowed_projects = get_user_projects()
    feature_perms = get_current_user_feature_permissions()

    # If view_all_projects is disabled, force team-member filtering even for admins
    if not feature_perms.get("view_all_projects", True) and allowed_projects is None:
        # Admin user but feature permission says no — filter to own projects
        user = frappe.session.user
        manager_projects = frappe.get_all(
            "PMS Project", filters={"project_manager": user}, pluck="name"
        )
        member_projects = frappe.db.get_all(
            "PMS Project Member", filters={"user": user}, pluck="parent"
        )
        allowed_projects = list(set(manager_projects + member_projects)) or ["__none__"]

    filters = {"status": ["not in", ["Cancelled"]]}
    if allowed_projects is not None:
        filters["name"] = ["in", allowed_projects]

    projects = frappe.get_all(
        "PMS Project",
        filters=filters,
        fields=[
            "name",
            "project_name",
            "client",
            "project_manager",
            "status",
            "start_date",
            "end_date",
            "total_budget",
            "calculated_cost",
            "budget_utilization",
        ],
        order_by="modified desc",
    )

    for project in projects:
        # Add task count
        project["total_tasks"] = frappe.db.count("PMS Task", {"project": project.name})
        project["done_tasks"] = frappe.db.count(
            "PMS Task", {"project": project.name, "status": "Done"}
        )
        project["progress"] = (
            round((project["done_tasks"] / project["total_tasks"] * 100), 1)
            if project["total_tasks"]
            else 0
        )

    return projects
