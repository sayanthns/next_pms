// Copyright (c) 2024, Next PMS and contributors
// For license information, please see license.txt

frappe.ui.form.on("PMS Task", {
	refresh(frm) {
		// --- Filter sprint by project ---
		frm.set_query("sprint", function () {
			return {
				filters: { project: frm.doc.project },
			};
		});

		// --- Filter parent_task by project (exclude self) ---
		frm.set_query("parent_task", function () {
			return {
				filters: {
					project: frm.doc.project,
					name: ["!=", frm.doc.name],
				},
			};
		});

		if (!frm.is_new()) {
			// --- Timer start/stop buttons ---
			setup_timer_buttons(frm);

			// --- Quick status change buttons ---
			setup_status_buttons(frm);

			// --- Show task cost in a highlighted section ---
			render_task_cost_section(frm);

			// --- "Open in Board" button ---
			if (frm.doc.project) {
				frm.add_custom_button(
					__("Open in Board"),
					function () {
						window.open(
							"/next-pms/project/" +
								frm.doc.project +
								"/board",
							"_blank"
						);
					},
					__("Views")
				);
			}
		}
	},

	project(frm) {
		// Clear sprint when project changes
		frm.set_value("sprint", "");
	},

	assigned_to(frm) {
		// Auto-fetch hourly_rate from project member when assigned_to changes
		if (frm.doc.assigned_to && frm.doc.project) {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "PMS Project Member",
					filters: {
						parent: frm.doc.project,
						user: frm.doc.assigned_to,
					},
					fields: ["hourly_rate"],
					limit_page_length: 1,
				},
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						var rate = r.message[0].hourly_rate;
						if (rate) {
							frm.set_value("hourly_rate", rate);
							frappe.show_alert({
								message: __(
									"Hourly rate set to {0} from project member settings",
									[rate]
								),
								indicator: "blue",
							});
						}
					}
				},
			});
		}
	},
});

function setup_timer_buttons(frm) {
	// Check if there is a running timer for this task
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "PMS Time Log",
			filters: {
				task: frm.doc.name,
				is_running: 1,
			},
			fields: ["name", "start_time"],
			limit_page_length: 1,
		},
		callback: function (r) {
			if (r.message && r.message.length > 0) {
				// Timer is running - show elapsed time and stop button
				var time_log = r.message[0];
				show_running_timer(frm, time_log);

				frm.add_custom_button(
					__("Stop Timer"),
					function () {
						frappe.call({
							method: "next_pms.api.timer.stop_timer",
							args: { log_name: time_log.name },
							callback: function (res) {
								if (res.message) {
									frappe.show_alert({
										message: __("Timer stopped"),
										indicator: "orange",
									});
									frm.reload_doc();
								}
							},
						});
					},
					__("Timer")
				);

				// Style the stop button red
				frm.custom_buttons[__("Stop Timer")] &&
					frm.custom_buttons[__("Stop Timer")].addClass(
						"btn-danger"
					);
			} else {
				// No timer running - show start button
				frm.add_custom_button(
					__("Start Timer"),
					function () {
						frappe.call({
							method: "next_pms.api.timer.start_timer",
							args: { task: frm.doc.name },
							callback: function (res) {
								if (res.message) {
									frappe.show_alert({
										message: __("Timer started"),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					},
					__("Timer")
				);

				// Style the start button green
				frm.custom_buttons[__("Start Timer")] &&
					frm.custom_buttons[__("Start Timer")].addClass(
						"btn-success"
					);
			}
		},
	});
}

function show_running_timer(frm, time_log) {
	if (!time_log || !time_log.start_time) return;

	var start = frappe.datetime.str_to_obj(time_log.start_time);
	var $timer_display = $(
		'<div class="pms-running-timer" style="' +
			"padding: 10px 15px; margin-bottom: 12px;" +
			"background: linear-gradient(135deg, #fef3c7, #fde68a);" +
			"border: 1px solid #f59e0b; border-radius: 8px;" +
			"display: flex; align-items: center; gap: 10px;" +
			"font-size: 14px; color: #92400e;" +
			'">' +
			'<span style="width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; animation: pulse-dot 2s infinite;"></span>' +
			'<span>Timer running:</span> <strong class="timer-elapsed" style="font-family: monospace; font-size: 16px;">00:00:00</strong>' +
			"</div>"
	);

	// Add pulse animation
	if (!$("style#pms-timer-pulse").length) {
		$("head").append(
			'<style id="pms-timer-pulse">' +
				"@keyframes pulse-dot { 0% { box-shadow: 0 0 0 0 rgba(245,158,11,0.4); } 70% { box-shadow: 0 0 0 8px rgba(245,158,11,0); } 100% { box-shadow: 0 0 0 0 rgba(245,158,11,0); } }" +
				"</style>"
		);
	}

	// Remove any existing timer display
	$(frm.body).find(".pms-running-timer").remove();
	$(frm.body).find(".form-layout").prepend($timer_display);

	// Update elapsed time every second
	function update_elapsed() {
		var now = new Date();
		var diff = Math.floor((now - start) / 1000);
		var hrs = Math.floor(diff / 3600);
		var mins = Math.floor((diff % 3600) / 60);
		var secs = diff % 60;
		var formatted =
			String(hrs).padStart(2, "0") +
			":" +
			String(mins).padStart(2, "0") +
			":" +
			String(secs).padStart(2, "0");
		$timer_display.find(".timer-elapsed").text(formatted);
	}

	update_elapsed();
	frm._timer_interval = setInterval(update_elapsed, 1000);

	// Clear interval on form close
	frm.on_remove = function () {
		if (frm._timer_interval) {
			clearInterval(frm._timer_interval);
		}
	};
}

function setup_status_buttons(frm) {
	var statuses = ["Backlog", "To Do", "In Progress", "In Review", "Done"];

	statuses.forEach(function (status) {
		if (frm.doc.status !== status) {
			frm.add_custom_button(
				__(status),
				function () {
					frm.set_value("status", status);
					frm.save();
				},
				__("Set Status")
			);
		}
	});
}

function render_task_cost_section(frm) {
	var estimated_hours = frm.doc.estimated_hours || 0;
	var actual_hours = frm.doc.actual_hours || 0;
	var hourly_rate = frm.doc.hourly_rate || 0;
	var estimated_cost = estimated_hours * hourly_rate;
	var actual_cost = actual_hours * hourly_rate;

	if (!hourly_rate && !estimated_hours && !actual_hours) return;

	var cost_html =
		'<div class="pms-cost-section" style="' +
		"padding: 12px 16px; margin-bottom: 12px;" +
		"background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px;" +
		'">' +
		'<div style="font-size: 12px; font-weight: 600; color: #0369a1; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Task Cost Summary</div>' +
		'<div style="display: flex; gap: 24px; flex-wrap: wrap;">' +
		'<div style="font-size: 12px; color: #6b7280;">' +
		"Hourly Rate: <strong>" +
		frappe.format(hourly_rate, { fieldtype: "Currency" }) +
		"</strong></div>" +
		'<div style="font-size: 12px; color: #6b7280;">' +
		"Est. Cost: <strong>" +
		frappe.format(estimated_cost, { fieldtype: "Currency" }) +
		"</strong></div>" +
		'<div style="font-size: 12px; color: #6b7280;">' +
		"Actual Cost: <strong>" +
		frappe.format(actual_cost, { fieldtype: "Currency" }) +
		"</strong></div>" +
		"</div>" +
		"</div>";

	$(frm.body).find(".pms-cost-section").remove();
	$(frm.body).find(".pms-running-timer").length
		? $(frm.body).find(".pms-running-timer").after(cost_html)
		: $(frm.body).find(".form-layout").prepend(cost_html);
}
