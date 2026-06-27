# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PMSProject(Document):
	def validate(self):
		self.validate_client()
		self.validate_budget()
		self.validate_sales_order()
		self.calculate_project_cost()
		self.validate_dates()

	def validate_client(self):
		# Client is mandatory for client projects; internal projects have no client.
		if not self.is_internal and not self.client:
			frappe.throw(_("Client is required"))

	def validate_budget(self):
		# Mandatory only on new client projects; internal + existing projects grandfathered.
		if self.is_new() and not self.is_internal and flt(self.total_budget) <= 0:
			frappe.throw(_("Total Budget is required and must be greater than 0"))

	def validate_sales_order(self):
		# Mandatory only on new client projects; internal + existing projects grandfathered.
		if self.is_new() and not self.is_internal and not self.sales_order:
			frappe.throw(_("Sales Order is required"))

	def validate_dates(self):
		if self.start_date and self.end_date:
			if self.end_date < self.start_date:
				frappe.throw("End Date cannot be before Start Date")

	def after_insert(self):
		self._publish_project_event("project_created")

	def on_update(self):
		self._publish_project_event("project_updated")

	def _publish_project_event(self, event):
		"""Publish a real-time event for this project."""
		frappe.publish_realtime(
			event,
			{
				"project": self.name,
				"project_name": self.project_name,
				"status": self.status,
				"budget_utilization": self.budget_utilization,
				"modified_by": frappe.session.user,
			},
			room=self.get_project_room(),
		)

	def get_project_room(self):
		"""Return the room name used for real-time subscriptions for this project."""
		return f"project_{self.name}"

	def calculate_project_cost(self):
		tasks = frappe.get_all(
			"PMS Task",
			filters={"project": self.name},
			fields=["calculated_cost"],
		)
		self.calculated_cost = sum(t.calculated_cost or 0 for t in tasks)
		# Spend = labour cost (from time logs) + logged project expenses.
		self.total_expenses = flt(
			frappe.db.get_value(
				"PMS Project Expense", {"project": self.name}, "sum(amount)"
			)
		)
		spent = flt(self.calculated_cost) + flt(self.total_expenses)
		if self.total_budget:
			self.budget_utilization = (spent / self.total_budget) * 100
		else:
			self.budget_utilization = 0

	def get_team_member_rate(self, user):
		for member in self.team_members:
			if member.user == user:
				return member.hourly_rate or 0
		return 0


def update_project_financials(project):
	"""Recompute a project's labour cost, expenses and utilization WITHOUT a full
	save (avoids re-validation / timestamp churn). Called from expense changes and
	anywhere spend must be refreshed."""
	if not project or not frappe.db.exists("PMS Project", project):
		return
	labour = flt(
		frappe.db.get_value("PMS Task", {"project": project}, "sum(calculated_cost)")
	)
	expenses = flt(
		frappe.db.get_value("PMS Project Expense", {"project": project}, "sum(amount)")
	)
	total_budget = flt(frappe.db.get_value("PMS Project", project, "total_budget"))
	utilization = ((labour + expenses) / total_budget * 100) if total_budget else 0
	frappe.db.set_value(
		"PMS Project",
		project,
		{
			"calculated_cost": labour,
			"total_expenses": expenses,
			"budget_utilization": utilization,
		},
		update_modified=False,
	)
