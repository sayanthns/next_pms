# apps/next_pms/next_pms/next_pms/doctype/pms_performance_score/pms_performance_score.py
"""Frozen monthly Performance Score snapshot (submittable).

Created and submitted by the 1st-of-month cron (next_pms.tasks) before any
performance email goes out, so emails and history always match an immutable
record. The ONLY post-submit change allowed is a bounded (±10), reasoned
management adjustment — every other field lacks allow_on_submit and is
rejected by core validate_update_after_submit. track_changes gives a
Version audit trail of each adjustment for free.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from next_pms.api.performance import _band


class PMSPerformanceScore(Document):
    def validate(self):
        # Derive month fields from the window when unset (manual desk entry).
        if not self.month_key and self.from_date:
            self.month_key = getdate(self.from_date).strftime("%Y-%m")
        if not self.month_label and self.from_date:
            self.month_label = getdate(self.from_date).strftime("%B %Y")
        self._validate_adjustment()

    def before_submit(self):
        # Seed final_* from the frozen values when there is no adjustment.
        if not flt(self.adjustment):
            self.final_score = flt(self.composite_score)
            self.final_band = self.band

    def before_update_after_submit(self):
        # `validate` does NOT run on a submitted doc's save() — this hook
        # is the post-submit path, so the adjustment rules apply here too.
        self._validate_adjustment()

    def _validate_adjustment(self):
        """Bound + reason rules, then recompute final_score/final_band.
        Shared by validate (pre-submit) and before_update_after_submit."""
        adj = flt(self.adjustment)
        if not -10 <= adj <= 10:
            frappe.throw(_("Adjustment must be between -10 and +10."))
        if adj and not (self.adjustment_reason or "").strip():
            frappe.throw(_("A reason is required for a non-zero adjustment."))
        final = round(min(max(flt(self.composite_score) + adj, 0), 100), 1)
        self.final_score = final
        self.final_band = _band(final)
