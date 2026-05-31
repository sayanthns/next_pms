# apps/next_pms/next_pms/api/test_budget_request.py
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

from next_pms.api import budget


class TestBudgetRequest(FrappeTestCase):
    def test_request_emails_sayanth(self):
        proj = frappe.db.get_value("PMS Project", {}, "name")
        if not proj:
            self.skipTest("no project")
        with patch("frappe.sendmail") as m:
            res = budget.request_budget_increase(proj)
        self.assertTrue(res.get("success"))
        self.assertIn("sayanth@enfono.in", m.call_args.kwargs.get("recipients", []))
