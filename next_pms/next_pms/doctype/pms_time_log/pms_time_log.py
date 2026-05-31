# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, time_diff_in_seconds, get_datetime, flt


class PMSTimeLog(Document):
    def before_insert(self):
        self.validate_budget_available()

    def validate_budget_available(self):
        # Block NEW time entries (timer start or manual) when the project budget is exhausted.
        # Stopping/updating an existing log is an UPDATE, not insert -> not blocked.
        if not self.task:
            return
        project = frappe.db.get_value("PMS Task", self.task, "project")
        if not project:
            return
        util = flt(frappe.db.get_value("PMS Project", project, "budget_utilization"))
        if util >= 95:
            frappe.throw(
                _("Project budget at {0}% (>= 95%). New time entries are blocked until the budget is increased. Use 'Request budget increase'.").format(round(util)),
                title=_("Budget Exhausted"),
            )

    def validate(self):
        self.validate_running_timer()
        self.calculate_duration()

    def validate_running_timer(self):
        if self.is_running:
            existing = frappe.get_all(
                "PMS Time Log",
                filters={
                    "user": self.user,
                    "is_running": 1,
                    "name": ["!=", self.name],
                },
                limit=1,
            )
            if existing:
                frappe.throw(
                    f"User {self.user} already has a running timer: {existing[0].name}. "
                    "Please stop it before starting a new one."
                )

    def calculate_duration(self):
        if self.start_time and self.end_time and not self.is_running:
            start = get_datetime(self.start_time)
            end = get_datetime(self.end_time)
            if end < start:
                frappe.throw("End Time cannot be before Start Time")
            diff_seconds = time_diff_in_seconds(end, start)
            self.duration_minutes = int(diff_seconds / 60)
            self.duration_hours = round(diff_seconds / 3600, 2)
        elif self.is_running:
            self.duration_minutes = 0
            self.duration_hours = 0


def on_time_log_change(doc, method):
    """Called via hooks doc_events. Updates parent task hours and cost."""
    if doc.task:
        task = frappe.get_doc("PMS Task", doc.task)
        task.calculate_actual_hours()
        task.calculate_task_cost()
        task.db_update()

        # Check if task exceeds estimated hours
        if task.estimated_hours and task.actual_hours > task.estimated_hours:
            project_manager = frappe.db.get_value("PMS Project", task.project, "project_manager")
            if project_manager:
                frappe.publish_realtime(
                    "task_hours_exceeded",
                    {
                        "task": task.name,
                        "task_title": task.task_title,
                        "estimated": task.estimated_hours,
                        "actual": task.actual_hours,
                    },
                    user=project_manager,
                )

        # Update project cost
        if task.project:
            project = frappe.get_doc("PMS Project", task.project)
            project.calculate_project_cost()
            project.db_update()
