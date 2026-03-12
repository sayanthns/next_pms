// Copyright (c) 2024, Next PMS and contributors
// For license information, please see license.txt

frappe.ui.form.on("PMS Time Log", {
	refresh(frm) {
		// --- Filter task to non-completed tasks ---
		frm.set_query("task", function () {
			return {
				filters: { status: ["not in", ["Done", "Cancelled"]] },
			};
		});

		// --- Auto-set user to current user on new ---
		if (frm.is_new()) {
			if (!frm.doc.user) {
				frm.set_value("user", frappe.session.user);
			}
		}

		if (!frm.is_new()) {
			// --- Timer start/stop on the form ---
			setup_time_log_timer(frm);

			// --- Show calculated duration live while timer is running ---
			if (frm.doc.is_running && frm.doc.start_time) {
				show_live_duration(frm);
			}
		}
	},

	onload(frm) {
		// Auto-set user on new form load
		if (frm.is_new() && !frm.doc.user) {
			frm.set_value("user", frappe.session.user);
		}
	},
});

function setup_time_log_timer(frm) {
	if (frm.doc.is_running) {
		// Timer is running - show stop button
		frm.add_custom_button(
			__("Stop Timer"),
			function () {
				var now = frappe.datetime.now_datetime();
				frm.set_value("end_time", now);
				frm.set_value("is_running", 0);

				// Calculate duration
				if (frm.doc.start_time) {
					var start = frappe.datetime.str_to_obj(frm.doc.start_time);
					var end = new Date();
					var diff_hours = (end - start) / (1000 * 60 * 60);
					frm.set_value("duration_hours", Math.round(diff_hours * 100) / 100);
				}

				frm.save().then(function () {
					frappe.show_alert({
						message: __("Timer stopped"),
						indicator: "orange",
					});
					// Clear the live timer interval
					if (frm._duration_interval) {
						clearInterval(frm._duration_interval);
					}
				});
			},
			__("Timer")
		);

		// Style stop button
		frm.custom_buttons[__("Stop Timer")] &&
			frm.custom_buttons[__("Stop Timer")].addClass("btn-danger");
	} else if (!frm.doc.end_time) {
		// Timer not started yet - show start button
		frm.add_custom_button(
			__("Start Timer"),
			function () {
				var now = frappe.datetime.now_datetime();
				frm.set_value("start_time", now);
				frm.set_value("is_running", 1);
				frm.save().then(function () {
					frappe.show_alert({
						message: __("Timer started"),
						indicator: "green",
					});
					frm.reload_doc();
				});
			},
			__("Timer")
		);

		// Style start button
		frm.custom_buttons[__("Start Timer")] &&
			frm.custom_buttons[__("Start Timer")].addClass("btn-success");
	}
}

function show_live_duration(frm) {
	var start = frappe.datetime.str_to_obj(frm.doc.start_time);

	var $duration_display = $(
		'<div class="pms-live-duration" style="' +
			"padding: 10px 15px; margin-bottom: 12px;" +
			"background: linear-gradient(135deg, #fef3c7, #fde68a);" +
			"border: 1px solid #f59e0b; border-radius: 8px;" +
			"display: flex; align-items: center; gap: 10px;" +
			"font-size: 14px; color: #92400e;" +
			'">' +
			'<span style="width: 8px; height: 8px; border-radius: 50%; background: #ef4444; animation: pms-pulse 2s infinite;"></span>' +
			"<span>Duration:</span> " +
			'<strong class="duration-value" style="font-family: monospace; font-size: 18px;">00:00:00</strong>' +
			"</div>"
	);

	// Add pulse animation if not already present
	if (!$("style#pms-duration-pulse").length) {
		$("head").append(
			'<style id="pms-duration-pulse">' +
				"@keyframes pms-pulse { 0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); } 70% { box-shadow: 0 0 0 8px rgba(239,68,68,0); } 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); } }" +
				"</style>"
		);
	}

	$(frm.body).find(".pms-live-duration").remove();
	$(frm.body).find(".form-layout").prepend($duration_display);

	function update_duration() {
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
		$duration_display.find(".duration-value").text(formatted);
	}

	update_duration();
	frm._duration_interval = setInterval(update_duration, 1000);

	// Clear interval on form close
	frm.on_remove = function () {
		if (frm._duration_interval) {
			clearInterval(frm._duration_interval);
		}
	};
}
