# apps/next_pms/next_pms/api/test_weekly_attendance.py
from frappe.tests.utils import FrappeTestCase

from next_pms.tasks import (
    _attendance_counts,
    _build_member_weekly_html,
    _checkin_reminder_reason,
    _performance_message,
)


class TestWeeklyAttendance(FrappeTestCase):
    """Pure attendance tallies for the weekly summary (no DB)."""

    WEEK = ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]  # Mon-Fri

    def test_partial_attendance_and_missed_checkout(self):
        checkins = [
            {"date": "2026-06-01", "checkout_time": "2026-06-01 18:00:00"},
            {"date": "2026-06-02", "checkout_time": "2026-06-02 17:30:00"},
            {"date": "2026-06-03", "checkout_time": None},  # missed checkout
        ]
        r = _attendance_counts(self.WEEK, checkins)
        self.assertEqual(r["working_days"], 5)
        self.assertEqual(r["days_checked_in"], 3)
        self.assertEqual(r["missed_checkin_days"], 2)  # 04, 05 no checkin
        self.assertEqual(r["missed_checkouts"], 1)

    def test_checkin_on_nonworking_day_not_counted(self):
        # Sunday checkin (not in working set) must not inflate days_checked_in
        checkins = [
            {"date": "2026-06-01", "checkout_time": "x"},
            {"date": "2026-05-31", "checkout_time": "x"},  # Sunday, outside working set
        ]
        r = _attendance_counts(self.WEEK, checkins)
        self.assertEqual(r["days_checked_in"], 1)
        self.assertEqual(r["missed_checkin_days"], 4)

    def test_no_checkins(self):
        r = _attendance_counts(self.WEEK, [])
        self.assertEqual(r["days_checked_in"], 0)
        self.assertEqual(r["missed_checkin_days"], 5)
        self.assertEqual(r["missed_checkouts"], 0)

    def test_full_attendance(self):
        checkins = [{"date": d, "checkout_time": "x"} for d in self.WEEK]
        r = _attendance_counts(self.WEEK, checkins)
        self.assertEqual(r["days_checked_in"], 5)
        self.assertEqual(r["missed_checkin_days"], 0)
        self.assertEqual(r["missed_checkouts"], 0)

    def test_member_email_renders_attendance(self):
        stats = {
            "full_name": "Test User", "logged_hours": 32.5, "target_hours": 40.0,
            "utilization": 81, "tasks_completed": 4, "tasks_in_progress": 2,
            "project_count": 3, "working_days": 5, "days_checked_in": 4,
            "missed_checkin_days": 1, "missed_checkouts": 2,
        }
        html = _build_member_weekly_html(stats, "2026-06-01", "2026-06-05")
        self.assertIn("Attendance", html)
        self.assertIn("Days Checked In", html)
        self.assertIn("4 / 5", html)
        self.assertIn("Missed Checkouts", html)
        self.assertIn("Weekly Summary", html)
        # util 81 -> encourage band; missed flags -> reminder note
        self.assertIn("keep it up", html.lower())
        self.assertIn("Reminder:", html)

    def test_performance_message_bands(self):
        hi, c, _ = _performance_message(95)
        self.assertIn("Congratulations", hi)
        self.assertEqual(c, "#10B981")
        mid, _, _ = _performance_message(70)
        self.assertIn("Solid week", mid)
        lo, c2, _ = _performance_message(30)
        self.assertEqual(c2, "#EF4444")
        # no flags -> empty note
        _, _, note = _performance_message(95, 0, 0)
        self.assertEqual(note, "")
        # flags -> reminder note
        _, _, note2 = _performance_message(95, 2, 1)
        self.assertIn("missed check-in", note2)
        self.assertIn("missed checkout", note2)

    def test_checkin_reminder_reason(self):
        # no check-in at all -> remind to check in
        self.assertEqual(_checkin_reminder_reason(None, None), "check-in")
        self.assertEqual(_checkin_reminder_reason("", None), "check-in")
        # checked in, no checkout -> remind to check out
        self.assertEqual(
            _checkin_reminder_reason("2026-06-01 09:00:00", None), "check-out"
        )
        # both present -> no reminder
        self.assertIsNone(
            _checkin_reminder_reason("2026-06-01 09:00:00", "2026-06-01 18:00:00")
        )
