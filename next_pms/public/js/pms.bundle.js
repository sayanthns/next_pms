// Next PMS - Main bundle entry point
// This file is loaded globally via hooks.py app_include_js

// Register real-time event handlers
frappe.realtime.on("task_updated", function (data) {
	if (cur_page && cur_page.page && cur_page.page.label === "PMS Dashboard") {
		// Refresh dashboard if on the PMS Dashboard page
		cur_page.page.wrapper.find(".pms-app").trigger("task-updated", data);
	}

	// Show notification
	frappe.show_alert({
		message: __("Task {0} updated to {1}", [data.task, data.status]),
		indicator: "blue",
	});
});

frappe.realtime.on("task_hours_exceeded", function (data) {
	frappe.show_alert({
		message: __(
			"Task {0} has exceeded estimated hours ({1}h actual vs {2}h estimated)",
			[data.task_title, data.actual, data.estimated]
		),
		indicator: "orange",
	});
});

frappe.realtime.on("pms_mention", function (data) {
	frappe.show_alert({
		message: __("{0} mentioned you in task {1}", [
			data.from_user,
			data.task_title,
		]),
		indicator: "blue",
	});
});

frappe.realtime.on("pms_new_comment", function (data) {
	frappe.show_alert({
		message: __("New comment on {0} by {1}", [
			data.task_title,
			data.from_user,
		]),
		indicator: "blue",
	});
});

frappe.realtime.on("client_comment", function (data) {
	frappe.show_alert({
		message: __("Client {0} commented on task {1}", [
			data.client_email,
			data.task_title,
		]),
		indicator: "green",
	});
});
