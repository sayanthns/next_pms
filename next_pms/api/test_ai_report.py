# next_pms/api/test_ai_report.py
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase
from next_pms.api import ai_report as R


class TestDailyReportSkip(FrappeTestCase):
    def test_sunday_returns_reason(self):
        # 2026-06-14 is a Sunday
        reason = R._should_skip_report_for("2026-06-14")
        self.assertTrue(reason)
        self.assertIn("Sunday", reason)

    def test_weekday_returns_none(self):
        # 2026-06-16 is a Tuesday; assumes no Holiday row for that date in dev DB
        self.assertIsNone(R._should_skip_report_for("2026-06-16"))


class TestBuildReport(FrappeTestCase):
    def _settings(self):
        return {"ai_provider": "Claude", "ai_api_key": "x",
                "ai_model": "m", "report_detail_level": "Detailed",
                "fallback_provider": "", "fallback_api_key": None, "fallback_model": "deepseek-chat"}

    def test_ai_failure_returns_metrics_and_error(self):
        with patch.object(R, "_call_llm", side_effect=Exception("boom")):
            out = R._build_report("2026-06-16", self._settings())
        self.assertIsNone(out["ai_parsed"])
        self.assertEqual(out["ai_error"], "boom")
        for k in ("full_data", "user_metrics", "process_mining", "time_patterns", "project_summary"):
            self.assertIn(k, out)

    def test_ai_success_parses(self):
        fake = '{"executive_summary":"ok","recommendations":[]}'
        with patch.object(R, "_call_llm", return_value=fake):
            out = R._build_report("2026-06-16", self._settings())
        self.assertIsNone(out["ai_error"])
        self.assertEqual(out["ai_parsed"]["executive_summary"], "ok")


class TestGetDailyReportData(FrappeTestCase):
    def test_denies_non_finance(self):
        with patch.object(frappe, "get_roles", return_value=["PMS Developer"]):
            with self.assertRaises(frappe.PermissionError):
                R.get_daily_report_data("2026-06-16")

    def test_future_date_throws(self):
        # run-tests session is Administrator -> permission passes
        from frappe.utils import add_days, today
        future = add_days(today(), 1)
        with self.assertRaises(frappe.exceptions.ValidationError):
            R.get_daily_report_data(future)

    def test_returns_shape(self):
        fake = '{"executive_summary":"ok","recommendations":[]}'
        with patch.object(R, "_call_llm", return_value=fake):
            out = R.get_daily_report_data("2026-06-16")
        for k in ("report_date", "skipped_reason", "overall", "ai", "ai_raw",
                  "ai_error", "user_metrics", "process_mining", "time_patterns", "project_summary"):
            self.assertIn(k, out)
        self.assertEqual(out["report_date"], "2026-06-16")

    def test_sunday_still_returns_data_with_notice(self):
        fake = '{"executive_summary":"ok","recommendations":[]}'
        with patch.object(R, "_call_llm", return_value=fake):
            out = R.get_daily_report_data("2026-06-14")  # Sunday
        self.assertTrue(out["skipped_reason"])
        self.assertIn("user_metrics", out)
