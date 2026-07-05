import frappe
from frappe.tests.utils import FrappeTestCase
from next_pms.api import weekly_plan as W


class TestPlanForDate(FrappeTestCase):
    def test_returns_none_when_no_plan(self):
        self.assertIsNone(W.get_plan_for_date("1999-01-04"))


class TestPlanVsActualReport(FrappeTestCase):
    def test_executes(self):
        from next_pms.next_pms.report.plan_vs_actual_hours import plan_vs_actual_hours as R
        cols, data = R.execute({})
        self.assertTrue(any(c["fieldname"] == "deviation" for c in cols))
        self.assertIsInstance(data, list)


class TestProjectProgressReport(FrappeTestCase):
    def test_executes(self):
        from next_pms.next_pms.report.project_progress import project_progress as R
        cols, data = R.execute({})
        self.assertTrue(any(c["fieldname"] == "delivery" for c in cols))
        self.assertIsInstance(data, list)


class TestPlanVsActualSummary(FrappeTestCase):
    def test_shape(self):
        from next_pms.api import ai_report as R
        out = R._get_plan_vs_actual("2026-06-24")
        for k in ("deviations", "at_risk"):
            self.assertIn(k, out)
        self.assertIsInstance(out["deviations"], list)
