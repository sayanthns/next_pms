// Copyright (c) 2024, Next PMS and contributors
// For license information, please see license.txt

frappe.ui.form.on("PMS Sprint", {
	refresh(frm) {
		if (!frm.is_new()) {
			// --- View Tasks ---
			frm.add_custom_button(__("View Tasks"), function () {
				frappe.set_route("List", "PMS Task", {
					project: frm.doc.project,
					sprint: frm.doc.name,
				});
			});

			// --- Show task count and completion percentage ---
			render_sprint_stats(frm);

			// --- Open Backlog button (links to Vue SPA) ---
			if (frm.doc.project) {
				frm.add_custom_button(
					__("Open Backlog"),
					function () {
						window.open(
							"/next-pms/project/" +
								frm.doc.project +
								"/backlog",
							"_blank"
						);
					},
					__("Views")
				);
			}

			// --- Quick Activate / Complete Sprint buttons ---
			if (
				frm.doc.status === "Planning" ||
				frm.doc.status === "Draft"
			) {
				frm.add_custom_button(
					__("Activate Sprint"),
					function () {
						frappe.confirm(
							__(
								"Are you sure you want to activate this sprint?"
							),
							function () {
								frm.set_value("status", "Active");
								frm.save().then(function () {
									frappe.show_alert({
										message: __("Sprint activated"),
										indicator: "green",
									});
								});
							}
						);
					},
					__("Actions")
				);

				// Style as primary
				frm.custom_buttons[__("Activate Sprint")] &&
					frm.custom_buttons[__("Activate Sprint")].addClass(
						"btn-primary"
					);
			}

			if (frm.doc.status === "Active" || frm.doc.status === "In Progress") {
				frm.add_custom_button(
					__("Complete Sprint"),
					function () {
						frappe.confirm(
							__(
								"Are you sure you want to complete this sprint? Incomplete tasks will remain in the backlog."
							),
							function () {
								frm.set_value("status", "Completed");
								frm.save().then(function () {
									frappe.show_alert({
										message: __("Sprint completed"),
										indicator: "blue",
									});
								});
							}
						);
					},
					__("Actions")
				);
			}
		}

		// --- Filter project (exclude cancelled) ---
		frm.set_query("project", function () {
			return {
				filters: { status: ["not in", ["Cancelled"]] },
			};
		});
	},
});

function render_sprint_stats(frm) {
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "PMS Task",
			filters: {
				project: frm.doc.project,
				sprint: frm.doc.name,
			},
			fields: ["status", "count(name) as count"],
			group_by: "status",
			limit_page_length: 0,
		},
		callback: function (r) {
			if (!r.message) return;

			var status_data = r.message;
			var total = 0;
			var done = 0;

			status_data.forEach(function (row) {
				total += row.count || 0;
				if (row.status === "Done") {
					done += row.count || 0;
				}
			});

			if (!total) return;

			var pct = Math.round((done / total) * 100);

			var status_colors = {
				Backlog: "#9CA3AF",
				"To Do": "#3B82F6",
				"In Progress": "#F59E0B",
				"In Review": "#8B5CF6",
				Done: "#22C55E",
				Cancelled: "#EF4444",
			};

			var legend_html = "";
			status_data.forEach(function (row) {
				var color = status_colors[row.status] || "#6B7280";
				legend_html +=
					'<span style="display: inline-flex; align-items: center; gap: 4px; margin-right: 10px; font-size: 12px; color: #6b7280;">' +
					'<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ' +
					color +
					';"></span>' +
					row.status +
					": " +
					row.count +
					"</span>";
			});

			var stats_html =
				'<div class="pms-sprint-stats" style="' +
				"padding: 14px 16px; margin-bottom: 12px;" +
				"background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px;" +
				'">' +
				'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">' +
				'<span style="font-size: 13px; font-weight: 600; color: #166534;">Sprint Progress</span>' +
				'<span style="font-size: 14px; font-weight: 700; color: #166534;">' +
				pct +
				"% (" +
				done +
				"/" +
				total +
				" tasks)</span>" +
				"</div>" +
				'<div style="height: 8px; background: #dcfce7; border-radius: 4px; overflow: hidden; margin-bottom: 8px;">' +
				'<div style="height: 100%; width: ' +
				pct +
				"%; background: linear-gradient(90deg, #22c55e, #16a34a); border-radius: 4px; transition: width 0.4s ease;\"></div>" +
				"</div>" +
				'<div style="display: flex; flex-wrap: wrap;">' +
				legend_html +
				"</div>" +
				"</div>";

			$(frm.body).find(".pms-sprint-stats").remove();
			$(frm.body).find(".form-layout").prepend(stats_html);
		},
	});
}
