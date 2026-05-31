# apps/next_pms/next_pms/next_pms/doctype/pms_project/test_pms_project.py
# Copyright (c) 2024, Next PMS and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPMSProject(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def _ensure_customer(self):
        # `client` (Link -> Customer) is reqd on PMS Project; ensure a test Customer exists
        name = "ZZ Test Customer"
        if not frappe.db.exists("Customer", name):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": name,
            }).insert(ignore_permissions=True)
        return name

    def _new_project(self, **kwargs):
        doc = frappe.get_doc({
            "doctype": "PMS Project",
            "project_name": kwargs.get("project_name", "ZZ Test Project"),
            # client and project_manager are reqd:1 on PMS Project — set them so the
            # ONLY thing that can fail insert is the total_budget rule under test.
            "client": self._ensure_customer(),
            "project_manager": "Administrator",
            "status": "Active",
            "total_budget": kwargs.get("total_budget", 1000),
            # sales_order is reqd:1 + mandatory-on-new; use a fake link so inserts pass
            # with ignore_links=True (no real Sales Order needed for these tests).
            "sales_order": kwargs.get("sales_order", "TEST-SO-LINK"),
        })
        return doc

    def test_new_project_requires_positive_budget(self):
        doc = self._new_project(total_budget=0)
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True, ignore_links=True)

    def test_new_project_with_budget_passes(self):
        doc = self._new_project(total_budget=5000)
        doc.insert(ignore_permissions=True, ignore_links=True)
        self.assertEqual(doc.total_budget, 5000)

    def test_new_project_requires_sales_order(self):
        doc = self._new_project()
        doc.sales_order = None
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True, ignore_links=True)

    def test_existing_project_without_budget_can_save(self):
        # Legacy project: insert with budget, then zero it in DB and ensure save still works
        doc = self._new_project(total_budget=5000)
        doc.insert(ignore_permissions=True, ignore_links=True)
        frappe.db.set_value("PMS Project", doc.name, "total_budget", 0)
        reloaded = frappe.get_doc("PMS Project", doc.name)
        reloaded.description = "edited"
        reloaded.save(ignore_permissions=True, ignore_links=True)  # must NOT throw (grandfathered)
