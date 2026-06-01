# apps/next_pms/next_pms/api/test_task_report.py
from frappe.tests.utils import FrappeTestCase

from next_pms.api.crud import _aggregate_window_hours, _apply_window_to_tasks


class TestTaskReportWindow(FrappeTestCase):
    """Effort-window behaviour: the report counts only the hours LOGGED in the
    window and includes only tasks with logs in range. Estimated hours stay
    lifetime per task. These exercise the pure helpers (no DB)."""

    def test_aggregate_sums_per_task(self):
        logs = [
            {"task": "TASK-A", "duration_hours": 5},
            {"task": "TASK-A", "duration_hours": 3.5},
            {"task": "TASK-B", "duration_hours": 2},
        ]
        self.assertEqual(
            _aggregate_window_hours(logs), {"TASK-A": 8.5, "TASK-B": 2}
        )

    def test_aggregate_ignores_blank_task_and_none_hours(self):
        logs = [
            {"task": None, "duration_hours": 9},
            {"task": "TASK-A", "duration_hours": None},
            {"task": "TASK-A", "duration_hours": 4},
        ]
        self.assertEqual(_aggregate_window_hours(logs), {"TASK-A": 4})

    def test_apply_window_excludes_tasks_without_logs(self):
        tasks = [
            {"name": "TASK-A", "actual_hours": 100, "estimated_hours": 50},
            {"name": "TASK-B", "actual_hours": 30, "estimated_hours": 20},
        ]
        # Only TASK-A logged time in the window
        out = _apply_window_to_tasks(tasks, {"TASK-A": 5.0})
        names = {t["name"] for t in out}
        self.assertEqual(names, {"TASK-A"})
        # actual overridden to in-window hours; estimate untouched (lifetime)
        self.assertEqual(out[0]["actual_hours"], 5.0)
        self.assertEqual(out[0]["estimated_hours"], 50)

    def test_apply_window_recomputes_cost_from_window_hours(self):
        tasks = [{"name": "TASK-A", "actual_hours": 100, "hourly_rate": 350,
                  "calculated_cost": 35000}]
        out = _apply_window_to_tasks(tasks, {"TASK-A": 4.0})
        self.assertEqual(out[0]["actual_hours"], 4.0)
        self.assertEqual(out[0]["calculated_cost"], 1400.0)

    def test_apply_window_skips_cost_when_rate_stripped(self):
        # Non-finance users have hourly_rate removed before this runs
        tasks = [{"name": "TASK-A", "actual_hours": 100}]
        out = _apply_window_to_tasks(tasks, {"TASK-A": 6.0})
        self.assertEqual(out[0]["actual_hours"], 6.0)
        self.assertNotIn("calculated_cost", out[0])
