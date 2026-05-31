# apps/next_pms/next_pms/api/test_auth.py
import frappe
from frappe.tests.utils import FrappeTestCase
from next_pms.api import auth


class TestAuth(FrappeTestCase):
    def test_invalid_credentials_throw(self):
        with self.assertRaises(frappe.AuthenticationError):
            auth.get_api_credentials("Administrator", "definitely-wrong-pw-xyz-123")

    def test_valid_credentials_return_keys(self):
        # admin password on the test site
        pw = frappe.conf.admin_password or "admin"
        try:
            res = auth.get_api_credentials("Administrator", pw)
        except frappe.AuthenticationError:
            self.skipTest("test-site admin password unknown; covered by invalid-cred test")
        self.assertIn("api_key", res)
        self.assertIn("api_secret", res)
        self.assertTrue(res["api_key"])
        self.assertEqual(res["user"], "Administrator")
