# Copyright (c) 2026, Next PMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class PMSProjectPayment(Document):
    def validate(self):
        if flt(self.amount) <= 0:
            frappe.throw(_("Payment amount must be greater than zero."))

        # A payment can only be marked Received when a Payment Entry proves it.
        if self.status == "Received" and not self.payment_entry:
            frappe.throw(
                _("Link a Payment Entry before marking this payment as Received."),
                title=_("Payment Entry Required"),
            )

        # Stamp / clear the received date with the status.
        if self.status == "Received" and not self.received_on:
            self.received_on = today()
        elif self.status != "Received":
            self.received_on = None
