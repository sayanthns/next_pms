import json

import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

from next_pms.api import calendar as C


def _ctx(is_admin=False, is_manager=False, is_developer=False, is_customer=False, user="dev@x.com"):
    return {"is_admin": is_admin, "is_manager": is_manager,
            "is_developer": is_developer, "is_customer": is_customer, "user": user}


class TestMeetingController(FrappeTestCase):
    def _new(self, **kw):
        doc = frappe.new_doc("PMS Meeting")
        doc.update({"subject": "Test sync", "meeting_type": "Internal", "status": "Planned"})
        doc.update(kw)
        return doc

    def test_start_time_sets_date_and_day(self):
        doc = self._new(start_time="2026-07-08 10:30:00")
        doc.insert(ignore_permissions=True)
        self.assertEqual(str(doc.meeting_date), "2026-07-08")
        self.assertEqual(doc.day_of_week, "Wednesday")

    def test_held_requires_minutes(self):
        doc = self._new(start_time="2026-07-08 10:30:00", status="Held")
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_held_with_minutes_saves(self):
        doc = self._new(start_time="2026-07-08 10:30:00", status="Held",
                        minutes="<p>Discussed rollout.</p>")
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.status, "Held")

    def test_planned_needs_no_minutes(self):
        doc = self._new(start_time="2026-07-08 10:30:00", status="Planned")
        doc.insert(ignore_permissions=True)  # must not raise
        self.assertTrue(doc.name)

    def test_subject_fallback(self):
        doc = frappe.new_doc("PMS Meeting")
        doc.update({"meeting_type": "Ad-hoc", "status": "Planned", "start_time": "2026-07-09 09:00:00"})
        doc.insert(ignore_permissions=True)
        self.assertTrue(doc.subject)


class TestCalendarApi(FrappeTestCase):
    def test_customer_denied_view(self):
        with patch.object(C, "_user_context", return_value=_ctx(is_customer=True)):
            with self.assertRaises(frappe.PermissionError):
                C.list_meetings()

    def test_save_and_list_roundtrip(self):
        # run-tests session = Administrator -> is_admin true
        payload = {
            "subject": "Weekly sync", "meeting_type": "Internal",
            "start_time": "2026-07-08 11:00:00", "duration_mins": 30, "status": "Planned",
            "participants": [{"user": "Administrator"}],
        }
        res = C.save_meeting(json.dumps(payload))
        self.assertTrue(res["name"])
        got = C.get_meeting(res["name"])
        self.assertEqual(got["subject"], "Weekly sync")
        self.assertEqual([p["user"] for p in got["participants"]], ["Administrator"])
        self.assertFalse(got["has_mom"])

    def test_save_held_without_minutes_blocked(self):
        payload = {"subject": "Retro", "meeting_type": "Internal",
                   "start_time": "2026-07-08 15:00:00", "status": "Held", "participants": []}
        with self.assertRaises(frappe.ValidationError):
            C.save_meeting(json.dumps(payload))

    def test_mine_scope_excludes_others(self):
        # a meeting coordinated by someone else with no matching participant is hidden in 'mine'
        payload = {"subject": "Other team", "meeting_type": "Internal",
                   "start_time": "2026-07-08 16:00:00", "status": "Planned",
                   "coordinator": "Administrator", "participants": []}
        res = C.save_meeting(json.dumps(payload))
        with patch.object(C, "_user_context", return_value=_ctx(is_developer=True, user="nobody@x.com")):
            mine = C.list_meetings(start="2026-07-06", end="2026-07-12", scope="mine")
            names = [m["name"] for m in mine]
            self.assertNotIn(res["name"], names)
            all_m = C.list_meetings(start="2026-07-06", end="2026-07-12", scope="all")
            self.assertIn(res["name"], [m["name"] for m in all_m])
