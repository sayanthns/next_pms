import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, formatdate, flt, cint


class WeeklyPlan(Document):
    def validate(self):
        self.week_end = add_days(getdate(self.week_start), 5)
        start = formatdate(self.week_start, "d MMM")
        end = formatdate(self.week_end, "d MMM yyyy")
        self.title = "Weekly Plan \u00b7 " + str(start) + " \u2013 " + str(end)
        for row in (self.priorities or []):
            js = cint(row.job_size) or 1
            row.wsjf_score = round(
                (flt(row.user_value) + flt(row.time_criticality) + flt(row.risk_reduction)) / js, 2
            )
        self.sync_projects_from_allocations()

    def sync_projects_from_allocations(self):
        """Allocations are the source of truth for hours: for every project that has
        allocation rows, recompute the Projects row's target_hours (sum of planned_hours)
        and team (distinct members). Allocated projects missing from the Projects table
        get a row appended. Judgment fields (focus, status, health) stay manual."""
        sums, teams = {}, {}
        for a in (self.allocations or []):
            if not a.project:
                continue
            sums[a.project] = sums.get(a.project, 0.0) + flt(a.planned_hours)
            if a.member:
                teams.setdefault(a.project, set()).add(a.member)

        names = {}
        if sums:
            names = dict(frappe.get_all(
                "PMS Project", filters={"name": ["in", list(sums)]},
                fields=["name", "project_name"], as_list=True, ignore_permissions=True))
        for a in (self.allocations or []):
            if a.project:
                a.project_name = names.get(a.project) or a.project_name

        existing = set()
        for p in (self.projects or []):
            if not p.project:
                continue
            existing.add(p.project)
            if p.project in sums:
                p.target_hours = round(sums[p.project], 2)
                members = teams.get(p.project)
                if members:
                    p.team = ",".join(sorted(members))

        for project in sums:
            if project in existing:
                continue
            self.append("projects", {
                "project": project,
                "project_name": names.get(project),
                "target_hours": round(sums[project], 2),
                "team": ",".join(sorted(teams.get(project, set()))),
                "status_color": "grey",
            })
