# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url_to_form


class PMSComment(Document):
    def after_insert(self):
        self.notify_mentions()
        self.notify_task_owner()
        self.send_comment_email()

    def notify_mentions(self):
        if self.mentions:
            mentioned_users = [u.strip() for u in self.mentions.split(",") if u.strip()]
            task_title = frappe.db.get_value("PMS Task", self.task, "task_title")
            for user in mentioned_users:
                if frappe.db.exists("User", user):
                    frappe.publish_realtime(
                        "pms_mention",
                        {
                            "task": self.task,
                            "task_title": task_title,
                            "from_user": self.user,
                            "comment": self.name,
                        },
                        user=user,
                    )

                    # Create Notification Log for mention
                    frappe.get_doc(
                        {
                            "doctype": "Notification Log",
                            "for_user": user,
                            "type": "Mention",
                            "document_type": "PMS Task",
                            "document_name": self.task,
                            "subject": f"You were mentioned in task: {task_title}",
                            "from_user": self.user,
                        }
                    ).insert(ignore_permissions=True)

    def notify_task_owner(self):
        task = frappe.get_doc("PMS Task", self.task)
        if task.assigned_to and task.assigned_to != self.user:
            frappe.publish_realtime(
                "pms_new_comment",
                {
                    "task": self.task,
                    "task_title": task.task_title,
                    "from_user": self.user,
                    "comment": self.name,
                },
                user=task.assigned_to,
            )

    def send_comment_email(self):
        """Email all task assignees (except commenter) about the new comment."""
        try:
            task = frappe.get_doc("PMS Task", self.task)
            commenter_name = frappe.db.get_value("User", self.user, "full_name") or self.user
            project_name = frappe.db.get_value("PMS Project", task.project, "project_name") or task.project
            task_url = get_url_to_form("PMS Task", self.task)

            # Gather all assignees
            recipients = []
            for assignee in task.get("assignees", []):
                if assignee.user and assignee.user != self.user:
                    recipients.append(assignee.user)

            # Also include legacy assigned_to
            if task.assigned_to and task.assigned_to != self.user and task.assigned_to not in recipients:
                recipients.append(task.assigned_to)

            if not recipients:
                return

            message = frappe.render_template(
                "next_pms/templates/emails/task_comment.html",
                {
                    "task_title": task.task_title,
                    "project_name": project_name,
                    "commenter": commenter_name,
                    "comment_text": self.comment or "",
                    "task_url": task_url,
                },
            )

            frappe.sendmail(
                recipients=recipients,
                subject=f"New Comment on: {task.task_title}",
                message=message,
                now=False,
            )

            # Create Notification Log for each recipient
            for user in recipients:
                frappe.get_doc(
                    {
                        "doctype": "Notification Log",
                        "for_user": user,
                        "type": "Alert",
                        "document_type": "PMS Task",
                        "document_name": self.task,
                        "subject": f"New comment on: {task.task_title}",
                        "from_user": self.user,
                    }
                ).insert(ignore_permissions=True)

        except Exception:
            frappe.log_error("PMS: Failed to send comment email notification")
