# Copyright (c) 2024, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PMSProject(Document):
	def validate(self):
		self.calculate_project_cost()
		self.validate_dates()

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
		if self.total_budget:
			self.budget_utilization = (self.calculated_cost / self.total_budget) * 100
		else:
			self.budget_utilization = 0

	def get_team_member_rate(self, user):
		for member in self.team_members:
			if member.user == user:
				return member.hourly_rate or 0
		return 0
