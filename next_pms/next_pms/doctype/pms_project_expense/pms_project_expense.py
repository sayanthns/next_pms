# Copyright (c) 2026, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PMSProjectExpense(Document):
    def validate(self):
        if flt(self.amount) <= 0:
            frappe.throw(_("Expense amount must be greater than zero."))

    def on_update(self):
        self._sync_project()

    def after_insert(self):
        self._sync_project()

    def on_trash(self):
        self._sync_project()

    def _sync_project(self):
        # Recompute the project's spend (labour + expenses) and utilization.
        if self.project:
            from next_pms.next_pms.doctype.pms_project.pms_project import (
                update_project_financials,
            )

            update_project_financials(self.project)
