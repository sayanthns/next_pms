# apps/next_pms/next_pms/api/test_settings.py
import frappe
from frappe.tests.utils import FrappeTestCase

from next_pms.api import settings


class TestSettings(FrappeTestCase):
    def test_ai_settings_roundtrip_hours(self):
        frappe.set_user("Administrator")
        settings.save_ai_settings(working_hours_per_day=7, weekly_summary_recipient="x@example.com")
        data = settings.get_ai_settings()
        self.assertEqual(data["working_hours_per_day"], 7.0)
        self.assertEqual(data["weekly_summary_recipient"], "x@example.com")
        settings.save_ai_settings(working_hours_per_day=8, weekly_summary_recipient="sayanth@enfono.in")
