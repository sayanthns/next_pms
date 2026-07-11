# apps/next_pms/next_pms/api/test_performance_snapshots.py
"""TDD suite for Monthly Frozen Performance Score Snapshots + PM Override.

Written BEFORE implementation (per .pipeline/spec.md). Every test here is
expected to FAIL until:
  - DocTypes `PMS Performance Score` (submittable) and
    `PMS Performance Dimension` (child) exist,
  - `next_pms.tasks._upsert_month_snapshots` exists and
    `send_monthly_performance_report` is snapshot-first,
  - `next_pms.api.performance.get_score_history` / `apply_adjustment`
    endpoints exist,
  - `compute_team_performance` rows carry `dimension_rows`.

Style follows next_pms/api/test_hours.py / test_weekly_plan.py: plain
FrappeTestCase, deterministic synthetic month (2026-06), no network.
Run: bench --site mysite.local run-tests --app next_pms \
       --module next_pms.api.test_performance_snapshots
"""

from contextlib import ExitStack
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate

MONTH_KEY = "2026-06"
MONTH_LABEL = "June 2026"
MONTH_START = getdate("2026-06-01")
MONTH_END = getdate("2026-06-30")

USER_A = "perf-snap-a@example.com"
USER_B = "perf-snap-b@example.com"
MANAGER = "perf-snap-mgr@example.com"
NON_MANAGER = "perf-snap-dev@example.com"

ALL_TEST_USERS = [USER_A, USER_B, MANAGER, NON_MANAGER]

DIM_SPEC = [
    ("delivery", 25),
    ("timeliness", 15),
    ("utilization", 15),
    ("plan_adherence", 15),
    ("efficiency", 10),
    ("quality", 10),
    ("consistency", 5),
    ("attendance", 5),
]


# ─────────────────────────── helpers ───────────────────────────


def _ensure_role(role):
    if not frappe.db.exists("Role", role):
        frappe.get_doc({"doctype": "Role", "role_name": role}).insert(
            ignore_permissions=True
        )


def _ensure_user(email, roles):
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0,
                "enabled": 1,
                "user_type": "System User",
            }
        ).insert(ignore_permissions=True)
    user = frappe.get_doc("User", email)
    existing = {r.role for r in user.roles}
    changed = False
    for role in roles:
        _ensure_role(role)
        if role not in existing:
            user.append("roles", {"role": role})
            changed = True
    if changed:
        user.save(ignore_permissions=True)


def _purge_snapshots(users=None):
    """Hard-delete snapshot rows (perms give nobody delete — go via db)."""
    if not frappe.db.table_exists("PMS Performance Score"):
        return
    filters = {"user": ["in", users]} if users else {}
    names = frappe.get_all(
        "PMS Performance Score", filters=filters, pluck="name", ignore_permissions=True
    )
    if names:
        frappe.db.delete("PMS Performance Dimension", {"parent": ["in", names]})
        frappe.db.delete("PMS Performance Score", {"name": ["in", names]})
    frappe.db.commit()


def _dimension_rows(score=80.0):
    """Engine-shaped detail rows: quality excluded to exercise the
    included/None-score path."""
    rows = []
    for key, weight in DIM_SPEC:
        included = key != "quality"
        rows.append(
            {
                "key": key,
                "weight": weight,
                "included": included,
                "score": score if included else None,
                "raw": f"synthetic basis for {key}"
                if included
                else "No data in period — excluded",
                "weighted": round(weight * score / 90, 1) if included else None,
            }
        )
    return rows


def _ranked_row(user, rank, composite=72.4, band="B", dim_score=80.0):
    """Shape of one compute_team_performance ranked row (+ dimension_rows)."""
    dims = _dimension_rows(dim_score)
    return {
        "user": user,
        "full_name": user,
        "user_image": None,
        "composite_score": composite,
        "band": band,
        "included_weight": 90,
        "target_hours": 160.0,
        "total_logged_hours": 141.5,
        "completed_count": 12,
        "dimensions": {r["key"]: r["score"] for r in dims if r["included"]},
        "dimension_rows": dims,
        "rank": rank,
    }


def _upsert(rows, month_start=MONTH_START, month_end=MONTH_END, label=MONTH_LABEL):
    from next_pms.tasks import _upsert_month_snapshots

    return _upsert_month_snapshots(rows, month_start, month_end, label)


def _make_snapshot(
    user,
    month_key=MONTH_KEY,
    month_label=MONTH_LABEL,
    composite=72.4,
    band="B",
    submit=True,
    **overrides,
):
    """Insert a synthetic snapshot doc directly (as Administrator)."""
    from_date = getdate(f"{month_key}-01")
    doc_dict = {
        "doctype": "PMS Performance Score",
        "user": user,
        "month_key": month_key,
        "month_label": month_label,
        "from_date": from_date,
        "to_date": get_last_day(from_date),
        "composite_score": composite,
        "band": band,
        "included_weight": 90,
        "rank": 1,
        "total_ranked": 2,
        "target_hours": 160.0,
        "logged_hours": 141.5,
        "completed_count": 12,
        "dimensions": [
            {
                "dim_key": "delivery",
                "weight": 25,
                "included": 1,
                "score": 81.0,
                "raw_basis": "12h est. delivered / 160h target",
            },
            {
                "dim_key": "quality",
                "weight": 10,
                "included": 0,
                "raw_basis": "No data in period — excluded",
            },
        ],
    }
    doc_dict.update(overrides)
    doc = frappe.get_doc(doc_dict)
    doc.insert(ignore_permissions=True)
    if submit:
        doc.submit()
    return doc


class SnapshotTestCase(FrappeTestCase):
    """Shared setup: test users + clean snapshot slate, Administrator session."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        _ensure_user(USER_A, ["PMS Developer"])
        _ensure_user(USER_B, ["PMS Developer"])
        _ensure_user(MANAGER, ["PMS Manager"])
        _ensure_user(NON_MANAGER, ["PMS Developer"])

    def setUp(self):
        frappe.set_user("Administrator")
        _purge_snapshots(ALL_TEST_USERS)
        self.addCleanup(frappe.set_user, "Administrator")
        self.addCleanup(_purge_snapshots, ALL_TEST_USERS)


# ─────────────────── 1-3. _upsert_month_snapshots ───────────────────


class TestUpsertMonthSnapshots(SnapshotTestCase):
    def test_creates_named_submitted_snapshots_with_children(self):
        rows = [_ranked_row(USER_A, 1), _ranked_row(USER_B, 2, composite=68.0, band="C")]
        created, skipped = _upsert(rows)

        name_a = f"PERF-{MONTH_KEY}-{USER_A}"
        name_b = f"PERF-{MONTH_KEY}-{USER_B}"
        self.assertEqual(sorted(created), sorted([name_a, name_b]))
        self.assertEqual(skipped, [])

        doc = frappe.get_doc("PMS Performance Score", name_a)
        self.assertEqual(doc.docstatus, 1)
        self.assertEqual(doc.user, USER_A)
        self.assertEqual(doc.month_key, MONTH_KEY)
        self.assertEqual(doc.month_label, MONTH_LABEL)
        self.assertEqual(str(doc.from_date), str(MONTH_START))
        self.assertEqual(str(doc.to_date), str(MONTH_END))
        self.assertEqual(flt(doc.composite_score), 72.4)
        self.assertEqual(doc.band, "B")
        self.assertEqual(doc.included_weight, 90)
        self.assertEqual(doc.rank, 1)
        self.assertEqual(doc.total_ranked, 2)
        self.assertEqual(flt(doc.target_hours), 160.0)
        self.assertEqual(flt(doc.logged_hours), 141.5)
        self.assertEqual(doc.completed_count, 12)

        # before_submit seeds final_* from frozen values (adjustment 0)
        self.assertEqual(flt(doc.final_score), 72.4)
        self.assertEqual(doc.final_band, "B")
        self.assertEqual(flt(doc.adjustment), 0.0)

        # child rows: full 8-dimension detail incl. raw_basis
        self.assertEqual(len(doc.dimensions), 8)
        by_key = {d.dim_key: d for d in doc.dimensions}
        self.assertEqual(set(by_key), {k for k, _ in DIM_SPEC})
        delivery = by_key["delivery"]
        self.assertEqual(delivery.weight, 25)
        self.assertTrue(delivery.included)
        self.assertEqual(flt(delivery.score), 80.0)
        self.assertEqual(delivery.raw_basis, "synthetic basis for delivery")
        quality = by_key["quality"]
        self.assertFalse(quality.included)
        self.assertEqual(quality.raw_basis, "No data in period — excluded")

        self.assertEqual(
            frappe.get_all(
                "PMS Performance Score", {"user": USER_B, "docstatus": 1}, pluck="name"
            ),
            [name_b],
        )

    def test_second_call_skips_and_frozen_values_win(self):
        _upsert([_ranked_row(USER_A, 1), _ranked_row(USER_B, 2)])
        count_before = len(
            frappe.get_all("PMS Performance Score", {"user": ["in", [USER_A, USER_B]]})
        )

        # re-run with DIFFERENT scores — frozen snapshot must win
        created, skipped = _upsert(
            [_ranked_row(USER_A, 1, composite=90.0, band="A"),
             _ranked_row(USER_B, 2, composite=10.0, band="D")]
        )
        self.assertEqual(created, [])
        self.assertEqual(
            sorted(skipped),
            sorted([f"PERF-{MONTH_KEY}-{USER_A}", f"PERF-{MONTH_KEY}-{USER_B}"]),
        )
        count_after = len(
            frappe.get_all("PMS Performance Score", {"user": ["in", [USER_A, USER_B]]})
        )
        self.assertEqual(count_before, count_after)
        self.assertEqual(
            flt(
                frappe.db.get_value(
                    "PMS Performance Score", f"PERF-{MONTH_KEY}-{USER_A}", "composite_score"
                )
            ),
            72.4,
        )

    def test_draft_leftover_replaced_and_submitted(self):
        # crash leftover: draft with stale score
        _make_snapshot(USER_A, composite=10.0, band="D", submit=False)
        name_a = f"PERF-{MONTH_KEY}-{USER_A}"
        self.assertEqual(
            frappe.db.get_value("PMS Performance Score", name_a, "docstatus"), 0
        )

        created, _skipped = _upsert([_ranked_row(USER_A, 1)])
        self.assertIn(name_a, created)

        docs = frappe.get_all(
            "PMS Performance Score",
            filters={"user": USER_A},
            fields=["name", "docstatus", "composite_score"],
        )
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].docstatus, 1)
        self.assertEqual(flt(docs[0].composite_score), 72.4)  # current rows, not stale


# ─────────────────── 4. cron: snapshot-first, email idempotency ───────────────────


class TestMonthlyCronEmailIdempotency(SnapshotTestCase):
    def _run_cron(self, rows, mail_mock):
        """Run send_monthly_performance_report with the scoring engine and
        sendmail patched. Patches both possible binding sites of
        compute_team_performance (function-local or module-level import)."""
        import next_pms.tasks as tasks_mod

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "next_pms.api.performance.compute_team_performance",
                    return_value=rows,
                )
            )
            if hasattr(tasks_mod, "compute_team_performance"):
                stack.enter_context(
                    patch.object(
                        tasks_mod, "compute_team_performance", return_value=rows
                    )
                )
            stack.enter_context(patch("frappe.sendmail", mail_mock))
            tasks_mod.send_monthly_performance_report()

    def test_first_run_snapshots_then_mails_rerun_sends_nothing(self):
        # cron windows on the previous calendar month, derived from today
        prev_start = get_first_day(add_months(getdate(), -1))
        run_month_key = prev_start.strftime("%Y-%m")
        rows = [_ranked_row(USER_A, 1), _ranked_row(USER_B, 2, composite=68.0, band="C")]

        from unittest.mock import MagicMock

        mail1 = MagicMock()
        self._run_cron(rows, mail1)

        # snapshots created and submitted for the cron's month
        for user in (USER_A, USER_B):
            name = f"PERF-{run_month_key}-{user}"
            self.assertEqual(
                frappe.db.get_value("PMS Performance Score", name, "docstatus"),
                1,
                f"expected submitted snapshot {name}",
            )
        # 2 member mails + 1 leaderboard mail
        self.assertEqual(mail1.call_count, 3)
        recipients = [c.kwargs.get("recipients") for c in mail1.call_args_list]
        self.assertIn([USER_A], recipients)
        self.assertIn([USER_B], recipients)

        # immediate re-run: nothing new created → ZERO emails
        count_before = len(
            frappe.get_all("PMS Performance Score", {"user": ["in", [USER_A, USER_B]]})
        )
        mail2 = MagicMock()
        self._run_cron(rows, mail2)
        count_after = len(
            frappe.get_all("PMS Performance Score", {"user": ["in", [USER_A, USER_B]]})
        )
        self.assertEqual(count_before, count_after)
        self.assertEqual(mail2.call_count, 0)


# ─────────────────── 5. freeze semantics + doctype structure ───────────────────


class TestFreeze(SnapshotTestCase):
    def test_frozen_parent_field_rejected_post_submit(self):
        doc = _make_snapshot(USER_A)
        doc.composite_score = 50.0
        self.assertRaises(frappe.UpdateAfterSubmitError, doc.save)

    def test_frozen_child_score_rejected_post_submit(self):
        doc = _make_snapshot(USER_A)
        doc.dimensions[0].score = 1.0
        self.assertRaises(frappe.UpdateAfterSubmitError, doc.save)

    def test_no_role_can_delete_cancel_or_amend(self):
        meta = frappe.get_meta("PMS Performance Score")
        self.assertTrue(meta.is_submittable)
        self.assertTrue(meta.track_changes)
        roles = {p.role for p in meta.permissions}
        self.assertIn("System Manager", roles)
        self.assertIn("PMS Manager", roles)
        # management-only: no read for other PMS roles
        self.assertNotIn("PMS Developer", roles)
        self.assertNotIn("PMS Viewer", roles)
        self.assertNotIn("PMS Customer", roles)
        for perm in meta.permissions:
            self.assertFalse(perm.get("delete"), f"{perm.role} must not delete")
            self.assertFalse(perm.get("cancel"), f"{perm.role} must not cancel")
            self.assertFalse(perm.get("amend"), f"{perm.role} must not amend")

    def test_field_level_allow_on_submit_matrix(self):
        meta = frappe.get_meta("PMS Performance Score")
        frozen = [
            "user", "month_key", "month_label", "from_date", "to_date",
            "composite_score", "band", "included_weight", "rank",
            "total_ranked", "target_hours", "logged_hours",
            "completed_count", "dimensions",
        ]
        override = [
            "adjustment", "adjustment_reason", "adjusted_by",
            "adjusted_on", "final_score", "final_band",
        ]
        for f in frozen:
            df = meta.get_field(f)
            self.assertIsNotNone(df, f"missing field {f}")
            self.assertFalse(df.allow_on_submit, f"{f} must NOT allow_on_submit")
        for f in override:
            df = meta.get_field(f)
            self.assertIsNotNone(df, f"missing field {f}")
            self.assertTrue(df.allow_on_submit, f"{f} MUST allow_on_submit")

    def test_dimension_child_doctype_shape(self):
        meta = frappe.get_meta("PMS Performance Dimension")
        self.assertTrue(meta.istable)
        for f in ("dim_key", "weight", "included", "score", "raw_basis"):
            self.assertIsNotNone(meta.get_field(f), f"missing child field {f}")


# ─────────────────── 6-9. apply_adjustment ───────────────────


class TestApplyAdjustment(SnapshotTestCase):
    def _adjust(self, name, adjustment, reason=None):
        from next_pms.api.performance import apply_adjustment

        return apply_adjustment(name, adjustment, reason)

    def test_happy_path_as_manager_with_audit_trail(self):
        doc = _make_snapshot(USER_A, composite=82.0, band="B")
        frappe.set_user(MANAGER)
        out = self._adjust(doc.name, 5, "Carried critical release solo")

        fresh = frappe.get_doc("PMS Performance Score", doc.name)
        self.assertEqual(flt(fresh.adjustment), 5.0)
        self.assertEqual(fresh.adjustment_reason, "Carried critical release solo")
        self.assertEqual(flt(fresh.final_score), 87.0)
        self.assertEqual(fresh.final_band, "A")  # recomputed: 87 >= 85 → A
        self.assertEqual(fresh.adjusted_by, MANAGER)
        self.assertTrue(fresh.adjusted_on)
        # frozen values untouched
        self.assertEqual(flt(fresh.composite_score), 82.0)
        self.assertEqual(fresh.band, "B")

        # endpoint returns the refreshed row for the UI
        self.assertEqual(flt(out.get("final_score")), 87.0)
        self.assertEqual(out.get("final_band"), "A")

        # Version audit trail names the changed field
        frappe.set_user("Administrator")
        versions = frappe.get_all(
            "Version",
            filters={"ref_doctype": "PMS Performance Score", "docname": doc.name},
            fields=["data"],
            ignore_permissions=True,
        )
        self.assertTrue(
            any('"adjustment"' in (v.data or "") for v in versions),
            "expected a Version row recording the adjustment change",
        )

    def test_clamp_high(self):
        doc = _make_snapshot(USER_A, composite=96.0, band="A")
        self._adjust(doc.name, 10, "exceptional month")
        fresh = frappe.db.get_value(
            "PMS Performance Score", doc.name, ["final_score", "final_band"], as_dict=True
        )
        self.assertEqual(flt(fresh.final_score), 100.0)
        self.assertEqual(fresh.final_band, "A")

    def test_clamp_low(self):
        doc = _make_snapshot(USER_A, composite=4.0, band="D")
        self._adjust(doc.name, -10, "serious escalation")
        fresh = frappe.db.get_value(
            "PMS Performance Score", doc.name, ["final_score", "final_band"], as_dict=True
        )
        self.assertEqual(flt(fresh.final_score), 0.0)
        self.assertEqual(fresh.final_band, "D")

    def test_out_of_range_throws(self):
        doc = _make_snapshot(USER_A)
        with self.assertRaises(frappe.ValidationError):
            self._adjust(doc.name, 10.5, "too much")
        with self.assertRaises(frappe.ValidationError):
            self._adjust(doc.name, -11, "too little")
        # doc untouched
        self.assertEqual(
            flt(frappe.db.get_value("PMS Performance Score", doc.name, "adjustment")),
            0.0,
        )

    def test_nonzero_adjustment_requires_reason(self):
        doc = _make_snapshot(USER_A)
        with self.assertRaises(frappe.ValidationError):
            self._adjust(doc.name, 3)  # no reason
        with self.assertRaises(frappe.ValidationError):
            self._adjust(doc.name, 3, "")  # empty reason

    def test_zero_adjustment_needs_no_reason(self):
        doc = _make_snapshot(USER_A)
        self._adjust(doc.name, 3, "initial bump")
        # clearing back to 0 without a reason is allowed
        self._adjust(doc.name, 0)
        fresh = frappe.get_doc("PMS Performance Score", doc.name)
        self.assertEqual(flt(fresh.adjustment), 0.0)
        self.assertEqual(flt(fresh.final_score), flt(fresh.composite_score))
        self.assertEqual(fresh.final_band, fresh.band)

    def test_draft_rejected(self):
        doc = _make_snapshot(USER_A, submit=False)
        with self.assertRaises(frappe.ValidationError):
            self._adjust(doc.name, 5, "should not apply to drafts")

    def test_desk_save_path_hits_same_rules(self):
        """Controller enforces the bound even without the endpoint —
        a manager editing via desk form must hit the same validation."""
        doc = _make_snapshot(USER_A)
        fresh = frappe.get_doc("PMS Performance Score", doc.name)
        fresh.adjustment = 25  # out of range
        fresh.adjustment_reason = "desk tamper"
        self.assertRaises(frappe.ValidationError, fresh.save)

    def test_non_numeric_adjustment_coerces_to_zero(self):
        # documented edge: flt('abc') → 0.0 → reason-optional path, no crash
        doc = _make_snapshot(USER_A)
        self._adjust(doc.name, "abc")
        self.assertEqual(
            flt(frappe.db.get_value("PMS Performance Score", doc.name, "adjustment")),
            0.0,
        )


# ─────────────────── 10. permission gates ───────────────────


class TestPermissionGates(SnapshotTestCase):
    def test_non_manager_blocked_on_both_endpoints(self):
        doc = _make_snapshot(USER_A)
        from next_pms.api import performance

        frappe.set_user(NON_MANAGER)
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            performance.get_score_history(USER_A)
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            performance.apply_adjustment(doc.name, 5, "not allowed")

        # gate runs BEFORE doc access: blocked even for a bogus name
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            performance.apply_adjustment("PERF-0000-00-nobody", 5, "x")

        frappe.set_user("Administrator")
        self.assertEqual(
            flt(frappe.db.get_value("PMS Performance Score", doc.name, "adjustment")),
            0.0,
        )

    def test_manager_allowed_on_both_endpoints(self):
        doc = _make_snapshot(USER_A)
        from next_pms.api import performance

        frappe.set_user(MANAGER)
        history = performance.get_score_history(USER_A)
        self.assertEqual(len(history), 1)
        out = performance.apply_adjustment(doc.name, 2, "manager access check")
        self.assertEqual(flt(out.get("adjustment")), 2.0)


# ─────────────────── 11. get_score_history shape & order ───────────────────


class TestScoreHistory(SnapshotTestCase):
    def test_only_submitted_newest_first_with_adjustment_fields(self):
        from next_pms.api.performance import apply_adjustment, get_score_history

        _make_snapshot(USER_A, month_key="2026-05", month_label="May 2026",
                       composite=61.0, band="C")
        june = _make_snapshot(USER_A, month_key="2026-06", month_label="June 2026",
                              composite=82.0, band="B")
        # a draft must never appear in history
        _make_snapshot(USER_A, month_key="2026-04", month_label="April 2026",
                       submit=False)
        # someone else's snapshot must not leak in
        _make_snapshot(USER_B, month_key="2026-06", composite=50.0, band="C")

        apply_adjustment(june.name, 5, "strong delivery")

        history = get_score_history(USER_A)
        self.assertEqual(len(history), 2)  # drafts + other users excluded
        self.assertEqual([r["month_key"] for r in history], ["2026-06", "2026-05"])

        newest = history[0]
        for field in (
            "name", "month_key", "month_label", "from_date", "to_date",
            "composite_score", "band", "adjustment", "adjustment_reason",
            "adjusted_by", "adjusted_on", "final_score", "final_band",
            "rank", "total_ranked",
        ):
            self.assertIn(field, newest, f"history row missing {field}")
        self.assertEqual(flt(newest["adjustment"]), 5.0)
        self.assertEqual(newest["adjustment_reason"], "strong delivery")
        self.assertEqual(flt(newest["final_score"]), 87.0)
        self.assertEqual(newest["final_band"], "A")

        older = history[1]
        self.assertEqual(flt(older["adjustment"]), 0.0)
        self.assertEqual(flt(older["final_score"]), 61.0)


# ─────────────────── 12. engine back-compat regression ───────────────────


class TestEngineRegression(SnapshotTestCase):
    def test_rows_keep_dimensions_dict_and_gain_dimension_rows(self):
        from next_pms.api.performance import WEIGHTS, compute_team_performance

        rows = compute_team_performance(MONTH_START, MONTH_END)
        self.assertTrue(rows, "expected at least the test PMS users to be scored")
        for r in rows:
            # legacy score-dict kept (leaderboard UI / emails)
            self.assertIn("dimensions", r)
            self.assertIsInstance(r["dimensions"], dict)
            # new full detail list
            self.assertIn("dimension_rows", r)
            self.assertIsInstance(r["dimension_rows"], list)
            self.assertEqual(len(r["dimension_rows"]), len(WEIGHTS))
            for d in r["dimension_rows"]:
                for key in ("key", "weight", "included", "score", "raw", "weighted"):
                    self.assertIn(key, d)
            # dict is exactly the included subset of the detail rows
            self.assertEqual(
                r["dimensions"],
                {d["key"]: d["score"] for d in r["dimension_rows"] if d["included"]},
            )
