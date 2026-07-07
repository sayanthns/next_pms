// Copyright (c) 2026, Next PMS and contributors
// For license information, please see license.txt

frappe.query_reports["Plan vs Actual Hours"] = {
	filters: [
		{
			fieldname: "weekly_plan",
			label: __("Weekly Plan"),
			fieldtype: "Link",
			options: "Weekly Plan",
		},
		{
			fieldname: "as_on",
			label: __("As On Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			description: __("Used to pick the week when no Weekly Plan is selected"),
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			description: __("Restrict to one department's projects. Blank = all. Defaults to the Plan Evaluation Department in PMS AI Settings."),
		},
	],
	onload(report) {
		frappe.db.get_single_value("PMS AI Settings", "plan_department").then((dept) => {
			if (dept && !frappe.query_report.get_filter_value("department")) {
				frappe.query_report.set_filter_value("department", dept);
			}
		});
	},
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (column.fieldname === "status") {
			const color =
				data.status === "Unplanned" ? "red" : data.status === "Not Started" ? "orange" : "green";
			return `<span class="indicator-pill ${color}">${__(data.status)}</span>`;
		}
		if (column.fieldname === "unplanned" && data.unplanned) {
			return `<span style="color:var(--red-600);font-weight:600">${value}</span>`;
		}
		if (column.fieldname === "deviation" && data.deviation < 0) {
			return `<span style="color:var(--orange-600)">${value}</span>`;
		}
		return value;
	},
};
