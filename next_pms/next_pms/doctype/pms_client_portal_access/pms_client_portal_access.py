# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
import secrets


class PMSClientPortalAccess(Document):
    def before_insert(self):
        if not self.access_token:
            self.access_token = secrets.token_urlsafe(32)

    def validate(self):
        self.validate_project_portal()

    def validate_project_portal(self):
        if self.project:
            enabled = frappe.db.get_value("PMS Project", self.project, "client_portal_enabled")
            if not enabled:
                frappe.throw(
                    f"Client portal is not enabled for project {self.project}. "
                    "Enable it first in the project settings."
                )

    def regenerate_token(self):
        self.access_token = secrets.token_urlsafe(32)
        self.save(ignore_permissions=True)
        return self.access_token
