# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from next_pms.utils import get_pms_url
from next_pms.next_pms.doctype.pms_time_log.pms_time_log import SUPPORT_TASK_TYPES


class PMSTask(Document):
    def before_save(self):
        self.calculate_actual_hours()
        self.fetch_hourly_rate()
        self.calculate_task_cost()
        self._previous_assigned_to = (
            frappe.db.get_value("PMS Task", self.name, "assigned_to")
            if not self.is_new()
            else None
        )
        self._previous_status = (
            frappe.db.get_value("PMS Task", self.name, "status")
            if not self.is_new()
            else None
        )

    def validate(self):
        self.validate_dates()
        self.validate_project_stage()

    def validate_project_stage(self):
        # In a Completed project, only Support tasks may be CREATED. Existing tasks
        # stay editable. (Planning projects allow task creation but block time logging.)
        if not self.is_new() or not self.project:
            return
        status = frappe.db.get_value("PMS Project", self.project, "status")
        if status == "Completed" and (self.task_type or "") not in SUPPORT_TASK_TYPES:
            frappe.throw(
                _("This project is Completed — only Support tasks can be created here."),
                title=_("Task Creation Blocked"),
            )

    def validate_dates(self):
        if self.start_date and self.due_date:
            if getdate(self.due_date) < getdate(self.start_date):
                frappe.throw("Due Date cannot be before Start Date")

    def calculate_actual_hours(self):
        logs = frappe.get_all(
            "PMS Time Log",
            filters={"task": self.name, "is_running": 0},
            fields=["duration_hours"],
        )
        self.actual_hours = sum(l.duration_hours or 0 for l in logs)

    def fetch_hourly_rate(self):
        if self.assigned_to and self.project:
            project = frappe.get_doc("PMS Project", self.project)
            rate = project.get_team_member_rate(self.assigned_to)
            if rate:
                self.hourly_rate = rate

    def calculate_task_cost(self):
        self.calculated_cost = (self.actual_hours or 0) * (self.hourly_rate or 0)

    def after_insert(self):
        self.update_project_cost()

    def on_update(self):
        self.update_project_cost()

    def update_project_cost(self):
        if self.project:
            project = frappe.get_doc("PMS Project", self.project)
            project.calculate_project_cost()
            project.save(ignore_permissions=True)


def on_task_update(doc, method):
    """Called via hooks doc_events. Publishes real-time events and sends
    email notifications when tasks are updated or assigned."""
    event_data = {
        "task": doc.name,
        "task_title": doc.task_title,
        "status": doc.status,
        "project": doc.project,
        "assigned_to": doc.assigned_to,
        "priority": doc.priority,
        "modified_by": frappe.session.user,
    }

    # Publish to the project room (for project detail / board views)
    frappe.publish_realtime(
        "task_updated", event_data, room=f"project_{doc.project}",
    )

    # Also publish to all assignees (for dashboard / my-tasks views)
    notified_users = set()
    for assignee in doc.get("assignees", []):
        if assignee.user and assignee.user != frappe.session.user:
            notified_users.add(assignee.user)
    if doc.assigned_to and doc.assigned_to != frappe.session.user:
        notified_users.add(doc.assigned_to)
    reviewer = getattr(doc, "reviewer", None)
    if reviewer and reviewer != frappe.session.user:
        notified_users.add(reviewer)
    for user in notified_users:
        frappe.publish_realtime("task_updated", event_data, user=user)

    # Detect status change
    previous_status = getattr(doc, "_previous_status", None)
    if previous_status and doc.status != previous_status:
        _send_task_status_change_notifications(doc, previous_status)

    # Detect assignment change
    previous_assigned_to = getattr(doc, "_previous_assigned_to", None)

    if doc.assigned_to and doc.assigned_to != previous_assigned_to:
        # Publish task_assigned real-time event
        frappe.publish_realtime(
            "task_assigned",
            {
                "task": doc.name,
                "task_title": doc.task_title,
                "project": doc.project,
                "assigned_to": doc.assigned_to,
                "assigned_by": frappe.session.user,
                "priority": doc.priority,
            },
            room=f"project_{doc.project}",
        )

        # Also publish directly to the assigned user so they get notified
        # even if they are not in the project room yet
        frappe.publish_realtime(
            "task_assigned",
            {
                "task": doc.name,
                "task_title": doc.task_title,
                "project": doc.project,
                "assigned_to": doc.assigned_to,
                "assigned_by": frappe.session.user,
                "priority": doc.priority,
            },
            user=doc.assigned_to,
        )

        # Send email notification to the newly assigned user
        _send_task_assigned_email(doc)

        # Create Notification Log entry
        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "for_user": doc.assigned_to,
                "type": "Assignment",
                "document_type": "PMS Task",
                "document_name": doc.name,
                "subject": f"Task Assigned: {doc.task_title}",
                "from_user": frappe.session.user,
            }
        ).insert(ignore_permissions=True)

        # Push pms_notification so the notification badge updates instantly
        assigned_by_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
        frappe.publish_realtime(
            "pms_notification",
            {
                "type": "task_assigned",
                "task": doc.name,
                "task_title": doc.task_title,
                "project": doc.project,
                "assigned_to": doc.assigned_to,
                "changed_by": assigned_by_name,
            },
            user=doc.assigned_to,
        )

        # Web Push notification for task assignment
        from next_pms.api.push import send_push_to_users
        task_url = f"/next-pms/task/{doc.name}"
        send_push_to_users(
            [doc.assigned_to],
            title=f"Task Assigned: {doc.task_title}",
            body=f"{assigned_by_name} assigned you a task",
            url=task_url,
            ignore_user=frappe.session.user,
        )


def _send_task_assigned_email(doc):
    """Send an email notification to the assigned user using the HTML template."""
    try:
        project_name = frappe.db.get_value("PMS Project", doc.project, "project_name") or doc.project
        assigned_to_name = frappe.db.get_value("User", doc.assigned_to, "full_name") or doc.assigned_to
        task_url = get_pms_url("PMS Task", doc.name)

        message = frappe.render_template(
            "next_pms/templates/emails/task_assigned.html",
            {
                "task_title": doc.task_title,
                "assigned_to_name": assigned_to_name,
                "project_name": project_name,
                "priority": doc.priority or "Medium",
                "due_date": doc.due_date,
                "task_type": doc.task_type or "Task",
                "task_url": task_url,
            },
        )

        frappe.sendmail(
            recipients=[doc.assigned_to],
            subject=f"Task Assigned: {doc.task_title}",
            message=message,
            now=False,
        )
    except Exception:
        # Don't block task creation/update if email fails
        frappe.log_error("PMS: Failed to send task assigned email")


def _send_task_status_change_notifications(doc, old_status):
    """Send email notification to all task assignees when task status changes.
    Also notifies the notify_user and project manager when status is In Review or Done."""
    try:
        changed_by = frappe.session.user
        changed_by_name = frappe.db.get_value("User", changed_by, "full_name") or changed_by
        project_name = frappe.db.get_value("PMS Project", doc.project, "project_name") or doc.project
        task_url = get_pms_url("PMS Task", doc.name)

        # Get all assignees from child table
        recipients = []
        for assignee in doc.get("assignees", []):
            if assignee.user and assignee.user != changed_by:
                recipients.append(assignee.user)

        # Also include legacy assigned_to
        if doc.assigned_to and doc.assigned_to != changed_by and doc.assigned_to not in recipients:
            recipients.append(doc.assigned_to)

        # Notify the reviewer and project manager when In Review or Done
        if doc.status in ("In Review", "Done"):
            reviewer = getattr(doc, "reviewer", None)
            if reviewer and reviewer not in recipients:
                recipients.append(reviewer)
            if doc.project:
                pm = frappe.db.get_value("PMS Project", doc.project, "project_manager")
                if pm and pm != changed_by and pm not in recipients:
                    recipients.append(pm)

        if not recipients:
            return

        message = frappe.render_template(
            "next_pms/templates/emails/task_status_changed.html",
            {
                "task_title": doc.task_title,
                "project_name": project_name,
                "old_status": old_status,
                "new_status": doc.status,
                "changed_by": changed_by_name,
                "task_url": task_url,
            },
        )

        frappe.sendmail(
            recipients=recipients,
            subject=f"Task Status Changed: {doc.task_title} → {doc.status}",
            message=message,
            now=False,
        )

        # Create Notification Log and push realtime for each recipient
        for user in recipients:
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "PMS Task",
                    "document_name": doc.name,
                    "subject": f"Task Status Changed: {doc.task_title} → {doc.status}",
                    "from_user": changed_by,
                }
            ).insert(ignore_permissions=True)

            # Push realtime notification
            frappe.publish_realtime(
                "pms_notification",
                {
                    "type": "task_status_changed",
                    "task": doc.name,
                    "task_title": doc.task_title,
                    "project": doc.project,
                    "old_status": old_status,
                    "new_status": doc.status,
                    "changed_by": changed_by_name,
                },
                user=user,
            )

        # Web Push notifications for status change
        from next_pms.api.push import send_push_to_users
        push_url = f"/next-pms/task/{doc.name}"
        send_push_to_users(
            recipients,
            title=f"Task {doc.status}: {doc.task_title}",
            body=f"{changed_by_name} changed status to {doc.status}",
            url=push_url,
            ignore_user=changed_by,
        )

    except Exception:
        frappe.log_error("PMS: Failed to send task status change notification")
