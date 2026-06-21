import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, formatdate, flt, cint


class WeeklyPlan(Document):
    def validate(self):
        self.week_end = add_days(getdate(self.week_start), 5)
        start = formatdate(self.week_start, "d MMM")
        end = formatdate(self.week_end, "d MMM yyyy")
        self.title = "Weekly Plan \u00b7 " + str(start) + " \u2013 " + str(end)
        for row in (self.priorities or []):
            js = cint(row.job_size) or 1
            row.wsjf_score = round(
                (flt(row.user_value) + flt(row.time_criticality) + flt(row.risk_reduction)) / js, 2
            )
