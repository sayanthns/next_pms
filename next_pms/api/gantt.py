import frappe
from frappe.utils import getdate
from next_pms.api.permissions import check_project_access


@frappe.whitelist()
def get_gantt_data(project):
    """Return tasks formatted for frappe-gantt chart rendering.
    Each task includes id, name, start, end, progress, dependencies, and metadata.
    """
    check_project_access(project)

    tasks = frappe.get_all(
        "PMS Task",
        filters={"project": project},
        fields=[
            "name",
            "task_title",
            "start_date",
            "due_date",
            "status",
            "assigned_to",
            "priority",
            "parent_task",
            "estimated_hours",
            "actual_hours",
            "sprint",
        ],
        order_by="start_date asc, priority desc",
    )

    gantt_tasks = []
    for task in tasks:
        # Calculate progress based on status
        progress = _calculate_progress(task)

        # Build dependencies string
        dependencies = task.parent_task or ""

        gantt_tasks.append(
            {
                "id": task.name,
                "name": task.task_title,
                "start": str(task.start_date) if task.start_date else str(getdate()),
                "end": str(task.due_date) if task.due_date else str(task.start_date or getdate()),
                "progress": progress,
                "dependencies": dependencies,
                "assignee": task.assigned_to or "",
                "priority": task.priority,
                "status": task.status,
                "sprint": task.sprint or "",
                "custom_class": _get_priority_class(task.priority),
            }
        )

    return gantt_tasks


@frappe.whitelist()
def update_task_dates(task, start_date, end_date):
    """Update task dates from Gantt drag-to-reschedule."""
    task_doc = frappe.get_doc("PMS Task", task)
    task_doc.start_date = start_date
    task_doc.due_date = end_date
    task_doc.save()
    frappe.db.commit()

    return {"task": task, "start_date": start_date, "end_date": end_date}


def _calculate_progress(task):
    """Calculate task progress percentage based on status and hours."""
    status_progress = {
        "Backlog": 0,
        "To Do": 0,
        "In Progress": 50,
        "In Review": 80,
        "Done": 100,
    }

    if task.status == "In Progress" and task.estimated_hours and task.actual_hours:
        # More granular progress based on hours
        hours_progress = min((task.actual_hours / task.estimated_hours) * 100, 95)
        return round(hours_progress)

    return status_progress.get(task.status, 0)


def _get_priority_class(priority):
    """Return CSS class based on priority for Gantt bar coloring."""
    classes = {
        "Critical": "bar-critical",
        "High": "bar-high",
        "Medium": "bar-medium",
        "Low": "bar-low",
    }
    return classes.get(priority, "bar-medium")
