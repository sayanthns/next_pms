import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class PMSMeeting(Document):
    def validate(self):
        if self.meeting_date:
            self.day_of_week = getdate(self.meeting_date).strftime('%A')
        if not self.coordinator and self.project:
            self.coordinator = frappe.db.get_value('PMS Project', self.project, 'meeting_coordinator')
