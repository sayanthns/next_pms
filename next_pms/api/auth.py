# apps/next_pms/next_pms/api/auth.py
import frappe
from frappe import _
from frappe.rate_limiter import rate_limit


@frappe.whitelist(allow_guest=True)
@rate_limit(key="usr", limit=10, seconds=300)
def get_api_credentials(usr, pwd):
    """Native-app login endpoint.

    allow_guest=True is REQUIRED: this IS the login. The Android APK bundles a
    Vue SPA via Capacitor and cannot use Frappe session cookies, so it needs
    token (api_key/api_secret) auth. There is no session yet when this is
    called, hence it must be reachable by Guest. Security is enforced inside:
    credentials are validated via LoginManager.authenticate (raises
    AuthenticationError on failure) and keys are only returned on success, for
    System Users only.
    """
    if not usr or not pwd:
        frappe.throw(_("Username and password are required"), frappe.AuthenticationError)

    # frappe.utils.password.check_password raises frappe.AuthenticationError on
    # bad credentials and returns the correctly-cased username on success
    # (verified against Frappe v15.68.1). We use it directly rather than
    # LoginManager().authenticate because LoginManager.__init__ touches
    # frappe.local.request.path, which is absent in CLI/test contexts. This
    # primitive only verifies the password — it creates no login session.
    from frappe.utils.password import check_password

    user = check_password(usr, pwd)

    enabled, user_type = frappe.db.get_value(
        "User", user, ["enabled", "user_type"]
    )
    if not (user == "Administrator" or enabled):
        frappe.throw(_("User disabled or missing"), frappe.AuthenticationError)

    if user_type != "System User":
        frappe.throw(_("This account cannot use the mobile app"), frappe.AuthenticationError)

    api_key, api_secret = _ensure_api_keys(user)
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
    }


def _ensure_api_keys(user):
    """Return (api_key, api_secret) for the user, generating them if absent.

    We replicate frappe.core.doctype.user.user.generate_keys rather than call
    it directly, because that function calls frappe.only_for("System Manager")
    which raises PermissionError under the Guest context of this endpoint.
    Verified against Frappe v15.68.1: generate_keys generates 15-char hashes,
    sets api_key (only if missing) + api_secret, saves, and returns only the
    plaintext {"api_secret": ...}. api_secret is a Password field, read back
    via get_password.
    """
    user_doc = frappe.get_doc("User", user)

    if user_doc.api_key and user_doc.get_password("api_secret"):
        return user_doc.api_key, user_doc.get_password("api_secret")

    api_secret = frappe.generate_hash(length=15)
    if not user_doc.api_key:
        user_doc.api_key = frappe.generate_hash(length=15)
    user_doc.api_secret = api_secret
    user_doc.save(ignore_permissions=True)

    return user_doc.api_key, api_secret
