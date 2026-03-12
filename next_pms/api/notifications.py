import frappe


@frappe.whitelist()
def get_notifications():
    """Get unread notifications for current user."""
    user = frappe.session.user
    notifications = frappe.get_all(
        "Notification Log",
        filters={"for_user": user, "read": 0, "document_type": ["in", ["PMS Task", "PMS Project", "PMS Comment"]]},
        fields=["name", "subject", "document_type", "document_name", "creation"],
        order_by="creation desc",
        limit=20,
    )
    return notifications


@frappe.whitelist()
def mark_notification_read(notification):
    """Mark a notification as read."""
    frappe.db.set_value("Notification Log", notification, "read", 1)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def mark_all_read():
    """Mark all PMS notifications as read for current user."""
    frappe.db.sql("""
        UPDATE `tabNotification Log`
        SET `read` = 1
        WHERE `for_user` = %s AND `read` = 0
        AND `document_type` IN ('PMS Task', 'PMS Project', 'PMS Comment')
    """, frappe.session.user)
    frappe.db.commit()
    return {"success": True}
