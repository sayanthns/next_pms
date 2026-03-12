import frappe
from frappe.utils import now_datetime, today, get_datetime, time_diff_in_seconds

from next_pms.api.permissions import is_admin_user, is_manager_user


@frappe.whitelist()
def checkin():
    """Check in the current user. Creates a PMS Checkin with is_active=1.
    Prevents duplicate active check-ins for the same day.
    """
    user = frappe.session.user

    # Check for existing active check-in today
    existing = frappe.get_all(
        "PMS Checkin",
        filters={"user": user, "date": today(), "is_active": 1},
        limit=1,
    )
    if existing:
        frappe.throw("You are already checked in today.")

    doc = frappe.new_doc("PMS Checkin")
    doc.user = user
    doc.date = today()
    doc.checkin_time = now_datetime()
    doc.is_active = 1
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "checkin_time": str(doc.checkin_time),
        "is_active": True,
    }


@frappe.whitelist()
def checkout():
    """Check out the current user. Sets checkout_time, calculates total_hours, clears is_active."""
    user = frappe.session.user

    # Find active check-in for today
    active = frappe.get_all(
        "PMS Checkin",
        filters={"user": user, "date": today(), "is_active": 1},
        fields=["name"],
        limit=1,
    )
    if not active:
        frappe.throw("No active check-in found for today.")

    doc = frappe.get_doc("PMS Checkin", active[0].name)
    doc.checkout_time = now_datetime()
    doc.is_active = 0

    # Calculate total hours
    start = get_datetime(doc.checkin_time)
    end = get_datetime(doc.checkout_time)
    diff_seconds = time_diff_in_seconds(end, start)
    doc.total_hours = round(diff_seconds / 3600, 2)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "checkin_time": str(doc.checkin_time),
        "checkout_time": str(doc.checkout_time),
        "total_hours": doc.total_hours,
        "is_active": False,
    }


@frappe.whitelist()
def get_today_checkin():
    """Return the current user's check-in status for today."""
    user = frappe.session.user

    checkins = frappe.get_all(
        "PMS Checkin",
        filters={"user": user, "date": today()},
        fields=["name", "checkin_time", "checkout_time", "is_active", "total_hours"],
        order_by="checkin_time desc",
        limit=1,
    )

    if checkins:
        c = checkins[0]
        return {
            "name": c.name,
            "checkin_time": str(c.checkin_time) if c.checkin_time else None,
            "checkout_time": str(c.checkout_time) if c.checkout_time else None,
            "is_active": bool(c.is_active),
            "total_hours": c.total_hours,
        }

    return None


@frappe.whitelist()
def get_checkin_history(user_filter=None, from_date=None, to_date=None, limit=50):
    """Get check-in history. Admin/PM see all users, Developer sees only their own."""
    user = frappe.session.user
    is_admin = is_admin_user()
    is_pm = is_manager_user()

    filters = {}

    # Role-based access
    if is_admin or is_pm:
        if user_filter:
            filters["user"] = user_filter
    else:
        filters["user"] = user

    if from_date:
        filters["date"] = [">=", from_date]
    if to_date:
        if "date" in filters:
            filters["date"] = ["between", [from_date or "2020-01-01", to_date]]
        else:
            filters["date"] = ["<=", to_date]

    records = frappe.get_all(
        "PMS Checkin",
        filters=filters,
        fields=["name", "user", "date", "checkin_time", "checkout_time", "is_active", "total_hours"],
        order_by="date desc, checkin_time desc",
        limit_page_length=int(limit),
    )

    # Enrich with user full name
    for r in records:
        r["user_full_name"] = (
            frappe.get_cached_value("User", r["user"], "full_name") or r["user"]
        )
        r["checkin_time"] = str(r["checkin_time"]) if r["checkin_time"] else None
        r["checkout_time"] = str(r["checkout_time"]) if r["checkout_time"] else None

    return records
