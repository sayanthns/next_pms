# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from next_pms.utils import get_pms_url


class PMSComment(Document):
    def after_insert(self):
        self.notify_mentions()
        self.notify_task_owner()
        self.send_comment_email()
        self.send_push_notifications()
        self.notify_portal_client()

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
            task_url = get_pms_url("PMS Task", self.task)

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

    def send_push_notifications(self):
        """Send push notifications for comments and mentions."""
        try:
            from next_pms.api.push import send_push_to_user

            task = frappe.get_doc("PMS Task", self.task)
            commenter_name = frappe.db.get_value("User", self.user, "full_name") or self.user
            task_url = f"/next-pms/task/{self.task}"

            # Push to mentioned users
            if self.mentions:
                mentioned_users = [u.strip() for u in self.mentions.split(",") if u.strip()]
                for user in mentioned_users:
                    if user != self.user and frappe.db.exists("User", user):
                        frappe.enqueue(
                            "next_pms.api.push.send_push_to_user",
                            user=user,
                            title=f"Mentioned in: {task.task_title}",
                            body=f"{commenter_name} mentioned you in a comment",
                            url=task_url,
                            ignore_user=self.user,
                            queue="short",
                            now=frappe.flags.in_test,
                        )

                        # Send email to mentioned user
                        try:
                            project_name = frappe.db.get_value(
                                "PMS Project", task.project, "project_name"
                            ) or task.project
                            full_task_url = get_pms_url("PMS Task", self.task)
                            message = frappe.render_template(
                                "next_pms/templates/emails/task_comment.html",
                                {
                                    "task_title": task.task_title,
                                    "project_name": project_name,
                                    "commenter": commenter_name,
                                    "comment_text": self.comment or "",
                                    "task_url": full_task_url,
                                },
                            )
                            frappe.sendmail(
                                recipients=[user],
                                subject=f"You were mentioned in: {task.task_title}",
                                message=message,
                                now=False,
                            )
                        except Exception:
                            frappe.log_error("PMS: Failed to send mention email")

            # Push to all task assignees (except commenter and already-mentioned users)
            mentioned = set()
            if self.mentions:
                mentioned = {u.strip() for u in self.mentions.split(",") if u.strip()}

            push_recipients = set()
            for assignee in task.get("assignees", []):
                if assignee.user and assignee.user != self.user and assignee.user not in mentioned:
                    push_recipients.add(assignee.user)

            if task.assigned_to and task.assigned_to != self.user and task.assigned_to not in mentioned:
                push_recipients.add(task.assigned_to)

            for user in push_recipients:
                frappe.enqueue(
                    "next_pms.api.push.send_push_to_user",
                    user=user,
                    title=f"New Comment: {task.task_title}",
                    body=f"{commenter_name} commented on a task",
                    url=task_url,
                    ignore_user=self.user,
                    queue="short",
                    now=frappe.flags.in_test,
                )

        except Exception:
            frappe.log_error("PMS: Failed to send comment push notifications")

    def notify_portal_client(self):
        """Notify portal clients when their support ticket gets a response."""
        try:
            from next_pms.api.portal import notify_client_on_ticket_response
            comment_text = self.comment or getattr(self, 'content', '') or ''
            commenter = self.user or getattr(self, 'author', '') or ''
            frappe.enqueue(
                "next_pms.api.portal.notify_client_on_ticket_response",
                task_name=self.task,
                comment_content=comment_text,
                commenter=commenter,
                queue="short",
                now=frappe.flags.in_test,
            )
        except Exception:
            frappe.log_error("PMS: Failed to enqueue portal client notification")
