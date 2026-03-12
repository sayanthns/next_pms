# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PMSActivityRate(Document):
    def validate(self):
        self.validate_unique_rate()

    def validate_unique_rate(self):
        existing = frappe.get_all(
            "PMS Activity Rate",
            filters={
                "activity_name": self.activity_name,
                "project": self.project or "",
                "name": ["!=", self.name],
            },
            limit=1,
        )
        if existing:
            scope = f"project {self.project}" if self.project else "global scope"
            frappe.throw(f"Activity rate for '{self.activity_name}' already exists at {scope}")
