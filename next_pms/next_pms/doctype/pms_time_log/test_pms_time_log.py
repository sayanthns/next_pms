# Copyright (c) 2024, Next PMS and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime


class TestPMSTimeLog(FrappeTestCase):
    pass


class TestBudgetGuard(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def _task_on_project_at(self, util):
        # PMS Task.after_insert calls project.save() which re-validates links,
        # so the project's reqd links must point at real records.
        customer = frappe.get_all("Customer", limit=1, pluck="name")[0]
        sales_order = frappe.get_all("Sales Order", limit=1, pluck="name")[0]
        proj = frappe.get_doc({
            "doctype": "PMS Project", "project_name": f"ZZ Guard {util}",
            "status": "Active", "total_budget": 1000, "sales_order": sales_order,
            "client": customer, "project_manager": "Administrator",
        })
        proj.insert(ignore_permissions=True, ignore_links=True)
        task = frappe.get_doc({
            "doctype": "PMS Task", "task_title": "ZZ Guard Task",
            "project": proj.name, "status": "Backlog",
        })
        task.insert(ignore_permissions=True, ignore_links=True)
        # Set util AFTER task insert: PMS Task.after_insert calls project.save()
        # which recomputes budget_utilization, so it must be pinned last.
        frappe.db.set_value("PMS Project", proj.name, "budget_utilization", util)
        return task.name

    def test_blocks_new_log_at_96(self):
        task = self._task_on_project_at(96)
        log = frappe.get_doc({"doctype": "PMS Time Log", "task": task,
                              "user": "Administrator", "is_running": 1,
                              "start_time": now_datetime()})
        with self.assertRaises(frappe.ValidationError):
            log.insert(ignore_permissions=True)

    def test_allows_new_log_at_94(self):
        task = self._task_on_project_at(94)
        log = frappe.get_doc({"doctype": "PMS Time Log", "task": task,
                              "user": "Administrator", "is_running": 1,
                              "start_time": now_datetime()})
        log.insert(ignore_permissions=True)
        self.assertTrue(log.name)
