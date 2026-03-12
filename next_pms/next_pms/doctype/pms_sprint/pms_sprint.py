# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class PMSSprint(Document):
    def before_save(self):
        self._previous_status = (
            frappe.db.get_value("PMS Sprint", self.name, "status")
            if not self.is_new()
            else None
        )

    def validate(self):
        self.validate_dates()
        self.validate_project_dates()

    def on_update(self):
        self._publish_sprint_status_change()

    def validate_dates(self):
        if self.start_date and self.end_date:
            if getdate(self.end_date) < getdate(self.start_date):
                frappe.throw("Sprint End Date cannot be before Start Date")

    def validate_project_dates(self):
        if self.project and self.start_date:
            project = frappe.get_doc("PMS Project", self.project)
            sprint_start = getdate(self.start_date)
            sprint_end = getdate(self.end_date) if self.end_date else None
            if project.start_date and sprint_start < getdate(project.start_date):
                frappe.throw(
                    f"Sprint Start Date cannot be before Project Start Date ({project.start_date})"
                )
            if project.end_date and sprint_end and sprint_end > getdate(project.end_date):
                frappe.throw(
                    f"Sprint End Date cannot be after Project End Date ({project.end_date})"
                )

    def _publish_sprint_status_change(self):
        """Publish sprint_updated event when the sprint status changes."""
        previous_status = getattr(self, "_previous_status", None)

        if previous_status and self.status != previous_status:
            frappe.publish_realtime(
                "sprint_updated",
                {
                    "sprint": self.name,
                    "sprint_name": self.sprint_name if hasattr(self, "sprint_name") else self.name,
                    "project": self.project,
                    "status": self.status,
                    "previous_status": previous_status,
                    "modified_by": frappe.session.user,
                },
                room=f"project_{self.project}",
            )
