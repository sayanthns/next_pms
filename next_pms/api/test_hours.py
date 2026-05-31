# apps/next_pms/next_pms/api/test_hours.py
import frappe
from frappe.tests.utils import FrappeTestCase

from next_pms.api import _hours


class TestHours(FrappeTestCase):
    def test_working_days_excludes_sunday(self):
        # 2026-06-01 (Mon) .. 2026-06-07 (Sun) inclusive -> 6 non-Sunday days
        days = _hours.working_days_in_range("2026-06-01", "2026-06-07")
        self.assertEqual(len(days), 6)
        self.assertTrue(all(d.weekday() != 6 for d in days))

    def test_compute_utilization_zero_target(self):
        self.assertEqual(_hours.compute_utilization(10, 0), 0.0)

    def test_compute_utilization_basic(self):
        self.assertEqual(_hours.compute_utilization(20, 40), 50.0)

    def test_working_hours_per_day_default(self):
        # A 0/blank stored value falls back to the 8h default
        frappe.db.set_single_value("PMS AI Settings", "working_hours_per_day", 0)
        self.assertEqual(_hours.get_working_hours_per_day(), 8.0)

    def test_working_hours_per_day_configured(self):
        frappe.db.set_single_value("PMS AI Settings", "working_hours_per_day", 7.5)
        self.assertEqual(_hours.get_working_hours_per_day(), 7.5)
        frappe.db.set_single_value("PMS AI Settings", "working_hours_per_day", 8)

    def test_target_hours_no_employee(self):
        # Mon 2026-06-01 .. Fri 2026-06-05 = 5 non-Sunday days; unknown user => no holiday/leave deduction
        frappe.db.set_single_value("PMS AI Settings", "working_hours_per_day", 8)
        t = _hours.compute_target_hours("nonexistent-user@example.com", "2026-06-01", "2026-06-05")
        self.assertEqual(t, 40.0)

    def test_target_hours_single_sunday_is_zero(self):
        # 2026-06-07 is a Sunday => no working days => target 0
        t = _hours.compute_target_hours("nonexistent-user@example.com", "2026-06-07", "2026-06-07")
        self.assertEqual(t, 0.0)

    def test_working_days_reverse_range_empty(self):
        self.assertEqual(_hours.working_days_in_range("2026-06-10", "2026-06-01"), [])
