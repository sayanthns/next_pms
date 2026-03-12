// Copyright (c) 2024, Next PMS and contributors
// For license information, please see license.txt

frappe.ui.form.on("PMS Project", {
	refresh(frm) {
		if (!frm.is_new()) {
			// --- Dashboard: Task Count by Status ---
			render_task_status_dashboard(frm);

			// --- Recalculate Costs ---
			frm.add_custom_button(__("Recalculate Costs"), function () {
				frm.call("calculate_project_cost").then(() => {
					frm.reload_doc();
				});
			});

			// --- Navigation buttons ---
			frm.add_custom_button(__("View Tasks"), function () {
				frappe.set_route("List", "PMS Task", { project: frm.doc.name });
			});

			frm.add_custom_button(__("View Sprints"), function () {
				frappe.set_route("List", "PMS Sprint", { project: frm.doc.name });
			});

			// --- SPA Links ---
			frm.add_custom_button(
				__("Open Board"),
				function () {
					window.open(`/next-pms/project/${frm.doc.name}/board`, "_blank");
				},
				__("Views")
			);

			frm.add_custom_button(
				__("Open Gantt"),
				function () {
					window.open(`/next-pms/project/${frm.doc.name}/gantt`, "_blank");
				},
				__("Views")
			);

			frm.add_custom_button(
				__("View Reports"),
				function () {
					window.open(`/next-pms/reports/${frm.doc.name}`, "_blank");
				},
				__("Views")
			);

			// --- Generate Client Portal Access ---
			frm.add_custom_button(
				__("Generate Client Portal Access"),
				function () {
					frappe.prompt(
						[
							{
								fieldname: "client_user",
								fieldtype: "Link",
								options: "User",
								label: __("Client User"),
								reqd: 1,
							},
							{
								fieldname: "expires_on",
								fieldtype: "Date",
								label: __("Expires On"),
							},
						],
						function (values) {
							frappe.call({
								method: "frappe.client.insert",
								args: {
									doc: {
										doctype: "PMS Client Portal Access",
										project: frm.doc.name,
										user: values.client_user,
										expires_on: values.expires_on || "",
										enabled: 1,
									},
								},
								callback: function (r) {
									if (r.message) {
										frappe.show_alert({
											message: __(
												"Client Portal Access created for {0}",
												[values.client_user]
											),
											indicator: "green",
										});
									}
								},
							});
						},
						__("Generate Client Portal Access"),
						__("Create")
					);
				},
				__("Actions")
			);

			// --- Refresh calculated fields ---
			refresh_calculated_fields(frm);
		}
	},
});

function render_task_status_dashboard(frm) {
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "PMS Task",
			filters: { project: frm.doc.name },
			fields: ["status", "count(name) as count"],
			group_by: "status",
			limit_page_length: 0,
		},
		callback: function (r) {
			if (!r.message) return;

			const status_data = r.message;
			const total = status_data.reduce(
				(sum, row) => sum + (row.count || 0),
				0
			);

			if (!total) return;

			const status_colors = {
				Backlog: "#9CA3AF",
				"To Do": "#3B82F6",
				"In Progress": "#F59E0B",
				"In Review": "#8B5CF6",
				Done: "#22C55E",
				Cancelled: "#EF4444",
			};

			// Build dashboard HTML
			let bars_html = "";
			let legend_html = "";

			status_data.forEach(function (row) {
				const pct = ((row.count / total) * 100).toFixed(1);
				const color = status_colors[row.status] || "#6B7280";

				bars_html +=
					'<div style="width: ' +
					pct +
					"%; background: " +
					color +
					'; height: 8px; transition: width 0.3s ease;" title="' +
					row.status +
					": " +
					row.count +
					'"></div>';

				legend_html +=
					'<span style="display: inline-flex; align-items: center; gap: 4px; margin-right: 12px; font-size: 12px; color: #6b7280;">' +
					'<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ' +
					color +
					';"></span>' +
					row.status +
					" (" +
					row.count +
					")" +
					"</span>";
			});

			const dashboard_html =
				'<div class="pms-task-dashboard" style="margin-bottom: 16px;">' +
				'<div style="font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 8px;">Task Status (' +
				total +
				" total)</div>" +
				'<div style="display: flex; border-radius: 4px; overflow: hidden; background: #f3f4f6; margin-bottom: 8px;">' +
				bars_html +
				"</div>" +
				'<div style="display: flex; flex-wrap: wrap;">' +
				legend_html +
				"</div>" +
				"</div>";

			// Insert into form
			if (frm.fields_dict.project_name) {
				const $wrapper = $(frm.fields_dict.project_name.wrapper);
				$wrapper.find(".pms-task-dashboard").remove();
				$wrapper.before(dashboard_html);
			} else {
				$(frm.body).find(".pms-task-dashboard").remove();
				$(frm.body).find(".form-layout").prepend(dashboard_html);
			}
		},
	});
}

function refresh_calculated_fields(frm) {
	// Auto-refresh total cost, budget utilization etc. if they exist
	if (frm.doc.total_estimated_cost !== undefined) {
		frm.refresh_field("total_estimated_cost");
	}
	if (frm.doc.total_actual_cost !== undefined) {
		frm.refresh_field("total_actual_cost");
	}
	if (frm.doc.total_estimated_hours !== undefined) {
		frm.refresh_field("total_estimated_hours");
	}
	if (frm.doc.total_actual_hours !== undefined) {
		frm.refresh_field("total_actual_hours");
	}
	if (frm.doc.budget_utilization !== undefined) {
		frm.refresh_field("budget_utilization");
	}
}
