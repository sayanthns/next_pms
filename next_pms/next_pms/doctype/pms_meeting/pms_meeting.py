import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime


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

        # Client Weekly meetings must be tied to a project (blocks scheduling, not just Held)
        if self.meeting_type == "Client Weekly" and not self.project:
            frappe.throw(_("A Client Weekly meeting must have a Project."))

        # The MoM PDF is mandatory to mark a meeting Held (scheduling as Planned needs nothing)
        if self.status == "Held":
            if not self.mom_pdf:
                frappe.throw(_("Attach the MoM (PDF) before marking a meeting as Held."))
            if not str(self.mom_pdf).lower().endswith(".pdf"):
                frappe.throw(_("The MoM attachment must be a PDF file."))

    def after_insert(self):
        """Seed one follow-up Task per participant on the meeting's project. Runs once
        (on creation) so editing the meeting never adds or removes tasks. Meetings with
        no project (Internal/Ad-hoc) create nothing — PMS Task requires a project."""
        if not self.project or not self.participants:
            return
        on_date = (" on %s" % self.meeting_date) if self.meeting_date else ""
        note = _("Auto-created from meeting %s%s.") % (self.name, on_date)
        seen = set()
        for row in self.participants:
            if not row.user or row.user in seen:
                continue
            seen.add(row.user)
            task = frappe.new_doc("PMS Task")
            task.task_title = "Follow-up: %s" % self.subject
            task.project = self.project
            task.assigned_to = row.user
            task.task_type = "Meeting"
            task.status = "To Do"
            task.source_meeting = self.name
            if self.meeting_date:
                task.due_date = self.meeting_date
            task.description = note
            task.insert(ignore_permissions=True)
