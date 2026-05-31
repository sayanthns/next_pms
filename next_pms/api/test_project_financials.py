# apps/next_pms/next_pms/api/test_project_financials.py
import frappe
from frappe.tests.utils import FrappeTestCase

from next_pms.api.project_report import get_project_financials, _financials_dict


class TestProjectFinancials(FrappeTestCase):
    def test_so_util_zero_safe(self):
        f = _financials_dict(so_value=0, budget=0, actual=10)
        self.assertEqual(f["so_util"], 0)
        self.assertEqual(f["budget_util"], 0)

    def test_financials_math(self):
        f = _financials_dict(so_value=200, budget=100, actual=50)
        self.assertEqual(f["so_value"], 200)
        self.assertEqual(f["budget"], 100)
        self.assertEqual(f["actual"], 50)
        self.assertEqual(f["budget_util"], 50.0)
        self.assertEqual(f["so_util"], 25.0)

    def test_get_project_financials_shape(self):
        proj = frappe.db.get_value("PMS Project", {}, "name")
        if not proj:
            self.skipTest("no PMS Project in test db")
        f = get_project_financials(proj)
        for k in ("so_value", "budget", "actual", "budget_util", "so_util"):
            self.assertIn(k, f)
