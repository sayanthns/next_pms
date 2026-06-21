import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase
from next_pms.api import weekly_plan as W


def _ctx(is_admin=False, is_manager=False, is_developer=False, is_customer=False, user="dev@x.com"):
    return {"is_admin": is_admin, "is_manager": is_manager,
            "is_developer": is_developer, "is_customer": is_customer, "user": user}


def _plan():
    return {
        "allocations": [{"member": "dev@x.com"}, {"member": "other@x.com"}],
        "projects": [
            {"project": "Alpha", "team_members": [{"user": "dev@x.com"}]},
            {"project": "Beta", "team_members": [{"user": "other@x.com"}]},
        ],
        "priorities": [{"project": "Alpha"}],
        "checklist": [{"item": "ship"}],
        "watch_list": [{"item": "risk1", "owner": "dev@x.com"},
                       {"item": "risk2", "owner": "other@x.com"}],
        "closures": [{"project": "Gamma"}],
        "working_notes": "<p>notes</p>",
    }


class TestWeeklyPlanScope(FrappeTestCase):
    def test_customer_denied(self):
        with patch.object(W, "_user_context", return_value=_ctx(is_customer=True)):
            with self.assertRaises(frappe.PermissionError):
                W.get_week()

    def test_manager_sees_all(self):
        with patch.object(W, "_user_context", return_value=_ctx(is_manager=True)), \
             patch.object(W, "_resolve_name", return_value="WP-1"), \
             patch.object(W, "_load_week_dict", return_value=_plan()):
            out = W.get_week()
        self.assertEqual(len(out["allocations"]), 2)
        self.assertEqual(len(out["projects"]), 2)
        self.assertEqual(len(out["watch_list"]), 2)

    def test_developer_scoped(self):
        with patch.object(W, "_user_context", return_value=_ctx(is_developer=True, user="dev@x.com")), \
             patch.object(W, "_resolve_name", return_value="WP-1"), \
             patch.object(W, "_load_week_dict", return_value=_plan()), \
             patch.object(W, "_user_project_names", return_value=set()):
            out = W.get_week()
        # own allocation only
        self.assertEqual([a["member"] for a in out["allocations"]], ["dev@x.com"])
        # projects where dev is on the team (Alpha) only
        self.assertEqual([p["project"] for p in out["projects"]], ["Alpha"])
        # own watch items only
        self.assertEqual([w["item"] for w in out["watch_list"]], ["risk1"])
        # global sections untouched
        self.assertEqual(len(out["priorities"]), 1)
        self.assertEqual(len(out["checklist"]), 1)
        self.assertEqual(out["working_notes"], "<p>notes</p>")

    def test_developer_project_via_assigned_task(self):
        # dev not in any team_members, but assigned a PMS Task on Beta -> Beta included
        with patch.object(W, "_user_context", return_value=_ctx(is_developer=True, user="dev@x.com")), \
             patch.object(W, "_resolve_name", return_value="WP-1"), \
             patch.object(W, "_load_week_dict", return_value=_plan()), \
             patch.object(W, "_user_project_names", return_value={"Beta"}):
            out = W.get_week()
        self.assertEqual(sorted(p["project"] for p in out["projects"]), ["Alpha", "Beta"])

    def test_no_plan_returns_none(self):
        with patch.object(W, "_user_context", return_value=_ctx(is_manager=True)), \
             patch.object(W, "_resolve_name", return_value=None):
            self.assertIsNone(W.get_week())


class TestPrefillRollForward(FrappeTestCase):
    def test_prefill_requires_manager(self):
        with patch.object(W, "_user_context", return_value=_ctx(is_developer=True)):
            with self.assertRaises(frappe.PermissionError):
                W.prefill_week("2026-06-22")

    def test_prefill_maps_projects_and_allocations(self):
        def ga(doctype, **kw):
            if doctype == "PMS Project":
                return [{"name": "Alpha", "status": "Active"}]
            if doctype == "PMS Project Member":
                return ["dev@x.com"]            # pluck=user
            if doctype == "PMS Task":
                return [{"assigned_to": "dev@x.com", "task_title": "T1", "estimated_hours": 8}]
            return []
        with patch.object(W, "_user_context", return_value=_ctx(is_manager=True)), \
             patch.object(frappe, "get_all", side_effect=ga), \
             patch.object(frappe.db, "sql", return_value=[[8.0]]):
            out = W.prefill_week("2026-06-22")
        self.assertEqual(out["projects"][0]["project"], "Alpha")
        self.assertEqual(out["projects"][0]["status_color"], "green")
        self.assertEqual(out["projects"][0]["effort"], "8h")
        self.assertEqual(out["projects"][0]["team_members"], [{"user": "dev@x.com"}])
        self.assertEqual(out["allocations"][0]["member"], "dev@x.com")
        self.assertEqual(out["allocations"][0]["planned_hours"], 8.0)
        self.assertEqual(out["allocations"][0]["capacity_hours"], 40)
        self.assertIn("T1 8h", out["allocations"][0]["tasks"])

    def test_roll_forward_drops_closed_and_strips_ids(self):
        src = {
            "intro": "x", "headline_note": None,
            "allocations": [{"name": "row1", "member": "a@x.com", "planned_hours": 5}],
            "projects": [{"project": "Alpha"}, {"project": "Gamma"}],
            "closures": [], "priorities": [], "watch_list": [], "checklist": [],
            "working_notes": "<p>n</p>", "week_shape": "", "meetings_note": "",
        }
        statuses = {"Alpha": "Active", "Gamma": "Completed"}
        with patch.object(W, "_user_context", return_value=_ctx(is_manager=True)), \
             patch.object(W, "_resolve_name", return_value="WP-prev"), \
             patch.object(W, "_load_week_dict", return_value=src), \
             patch.object(frappe.db, "get_value", side_effect=lambda dt, n, f: statuses.get(n)):
            out = W.roll_forward("2026-06-15", "2026-06-22")
        self.assertEqual(out["week_start"], "2026-06-22")
        self.assertEqual(out["published"], 0)
        self.assertEqual([p["project"] for p in out["projects"]], ["Alpha"])  # Gamma dropped
        self.assertNotIn("name", out["allocations"][0])  # child ids stripped


class TestSaveWeek(FrappeTestCase):
    def test_save_requires_manager(self):
        with patch.object(W, "_user_context", return_value=_ctx(is_developer=True)):
            with self.assertRaises(frappe.PermissionError):
                W.save_week('{"week_start": "2026-07-13"}')

    def test_save_roundtrip_and_wsjf(self):
        # run-tests session = Administrator -> manager gate passes
        import json as _json
        payload = {
            "week_start": "2026-07-13", "published": 1, "intro": "round-trip",
            "allocations": [{"member": "Administrator", "planned_hours": 10, "capacity_hours": 40}],
            "priorities": [{"project": "P1", "user_value": 8, "time_criticality": 4,
                            "risk_reduction": 2, "job_size": 2}],
        }
        res = W.save_week(_json.dumps(payload))
        self.assertEqual(res["week_start"], "2026-07-13")
        out = W.get_week("2026-07-13")
        self.assertEqual(out["intro"], "round-trip")
        self.assertEqual(out["allocations"][0]["member"], "Administrator")
        self.assertEqual(out["priorities"][0]["wsjf_score"], 7.0)  # (8+4+2)/2 recomputed on save
