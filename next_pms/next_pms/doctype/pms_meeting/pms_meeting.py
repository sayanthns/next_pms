import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, strip_html_tags


class PMSMeeting(Document):
    def validate(self):
        # start_time is the source of truth for the calendar; keep meeting_date in sync
        if self.start_time:
            self.meeting_date = getdate(get_datetime(self.start_time))
        if self.meeting_date:
            self.day_of_week = getdate(self.meeting_date).strftime("%A")

        if not self.coordinator and self.project:
            self.coordinator = frappe.db.get_value("PMS Project", self.project, "meeting_coordinator")

        # fallback subject so legacy rows (created before the field existed) still save
        if not self.subject:
            base = self.project or _(self.meeting_type or "Meeting")
            self.subject = "%s%s" % (base, " - " + str(self.meeting_date) if self.meeting_date else "")

        # MoM is mandatory to mark a meeting Held (scheduling as Planned needs no minutes)
        if self.status == "Held" and not (strip_html_tags(self.minutes or "").strip()):
            frappe.throw(_("Minutes of Meeting are required before a meeting can be marked as Held."))
