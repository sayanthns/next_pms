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
