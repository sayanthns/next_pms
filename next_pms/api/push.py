import frappe
import json
from py_vapid import Vapid


@frappe.whitelist(allow_guest=False)
def get_vapid_public_key():
    """Return the VAPID public key for push subscription."""
    public_key = frappe.conf.get("push_vapid_public_key")
    if not public_key:
        frappe.throw("Push notifications not configured. Run: bench execute next_pms.api.push.generate_vapid_keys")
    return public_key


@frappe.whitelist(allow_guest=False)
def save_push_subscription(subscription):
    """Save a push subscription for the current user."""
    if isinstance(subscription, str):
        subscription = json.loads(subscription)

    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys", {})
    p256dh = keys.get("p256dh", "")
    auth = keys.get("auth", "")

    if not endpoint:
        frappe.throw("Invalid subscription: missing endpoint")

    user = frappe.session.user

    # Check if this subscription already exists
    existing = frappe.db.exists("PMS Push Subscription", {"endpoint": endpoint})
    if existing:
        # Update the user (in case it changed)
        frappe.db.set_value("PMS Push Subscription", existing, {
            "user": user,
            "p256dh": p256dh,
            "auth": auth,
        })
    else:
        doc = frappe.get_doc({
            "doctype": "PMS Push Subscription",
            "user": user,
            "endpoint": endpoint,
            "p256dh": p256dh,
            "auth": auth,
        })
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist(allow_guest=False)
def remove_push_subscription(endpoint):
    """Remove a push subscription."""
    name = frappe.db.get_value("PMS Push Subscription", {"endpoint": endpoint})
    if name:
        frappe.delete_doc("PMS Push Subscription", name, ignore_permissions=True)
        frappe.db.commit()
    return {"status": "ok"}


def send_push_to_user(user, title, body, url=None, ignore_user=None):
    """Send a web push notification to all devices of a user.
    Called from task hooks. Runs in background via enqueue."""
    if user == ignore_user:
        return

    private_key = frappe.conf.get("push_vapid_private_key")
    public_key = frappe.conf.get("push_vapid_public_key")
    if not private_key or not public_key:
        return  # Push not configured, silently skip

    subscriptions = frappe.get_all(
        "PMS Push Subscription",
        filters={"user": user},
        fields=["endpoint", "p256dh", "auth"],
    )

    if not subscriptions:
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url or "/next-pms/",
        "icon": "/assets/next_pms/icons/icon-192x192.png",
    })

    vapid_claims = {"sub": f"mailto:{frappe.conf.get('push_vapid_email', 'admin@example.com')}"}

    for sub in subscriptions:
        try:
            from pywebpush import webpush
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=vapid_claims,
            )
        except Exception as e:
            error_str = str(e)
            # Remove expired/invalid subscriptions (410 Gone or 404)
            if "410" in error_str or "404" in error_str:
                try:
                    name = frappe.db.get_value("PMS Push Subscription", {"endpoint": sub.endpoint})
                    if name:
                        frappe.delete_doc("PMS Push Subscription", name, ignore_permissions=True)
                except Exception:
                    pass
            else:
                frappe.log_error(f"Push notification failed for {user}: {error_str}", "PMS Push Error")


def send_push_to_users(users, title, body, url=None, ignore_user=None):
    """Send push to multiple users. Enqueues each as a background job."""
    for user in users:
        if user and user != ignore_user:
            frappe.enqueue(
                "next_pms.api.push.send_push_to_user",
                user=user,
                title=title,
                body=body,
                url=url,
                ignore_user=ignore_user,
                queue="short",
                now=frappe.flags.in_test,
            )


def generate_vapid_keys():
    """Generate VAPID keys and store in site config.
    Run: bench execute next_pms.api.push.generate_vapid_keys
    """
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    import base64

    # Generate key pair
    private_key = ec.generate_private_key(ec.SECP256R1())

    # Export private key as base64 URL-safe
    private_numbers = private_key.private_numbers()
    private_bytes = private_numbers.private_value.to_bytes(32, byteorder="big")
    private_b64 = base64.urlsafe_b64encode(private_bytes).rstrip(b"=").decode()

    # Export public key as uncompressed point (65 bytes: 0x04 + x + y)
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()
    x_bytes = public_numbers.x.to_bytes(32, byteorder="big")
    y_bytes = public_numbers.y.to_bytes(32, byteorder="big")
    public_bytes = b"\x04" + x_bytes + y_bytes
    public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode()

    # Save to site config
    frappe.conf.push_vapid_private_key = private_b64
    frappe.conf.push_vapid_public_key = public_b64

    site_config_path = frappe.get_site_path("site_config.json")
    with open(site_config_path, "r") as f:
        config = json.load(f)

    config["push_vapid_private_key"] = private_b64
    config["push_vapid_public_key"] = public_b64

    with open(site_config_path, "w") as f:
        json.dump(config, f, indent=1, sort_keys=True)

    print(f"VAPID keys generated successfully!")
    print(f"Public key: {public_b64}")
    print(f"Private key: {private_b64}")
    print(f"Keys saved to site_config.json")
    print(f"\nIMPORTANT: Also set push_vapid_email in site_config.json:")
    print(f'  "push_vapid_email": "your-email@example.com"')
