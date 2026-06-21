import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate


class TestWeeklyPlan(FrappeTestCase):
    def _new(self):
        d = frappe.new_doc("Weekly Plan")
        d.week_start = "2026-06-22"  # Monday
        return d

    def test_validate_sets_week_end_and_title(self):
        d = self._new()
        d.validate()
        self.assertEqual(str(getdate(d.week_end)), "2026-06-27")  # +5 = Saturday
        self.assertIn("22 Jun", d.title)
        self.assertIn("27 Jun", d.title)

    def test_wsjf_computed_per_priority(self):
        d = self._new()
        d.append("priorities", {"project": "A", "user_value": 8,
                                "time_criticality": 5, "risk_reduction": 3, "job_size": 2})
        d.append("priorities", {"project": "B", "user_value": 9,
                                "time_criticality": 9, "risk_reduction": 0, "job_size": 0})  # js 0 -> 1
        d.validate()
        self.assertEqual(d.priorities[0].wsjf_score, 8.0)    # (8+5+3)/2
        self.assertEqual(d.priorities[1].wsjf_score, 18.0)   # (9+9+0)/1
