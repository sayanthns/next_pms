frappe.pages["pms-dashboard"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Next PMS",
		single_column: true,
	});

	page.main.html(`
		<div class="pms-app" id="pms-app">
			<div class="pms-layout">
				<nav class="pms-sidebar">
					<div class="pms-sidebar-logo">Next PMS</div>
					<ul class="pms-sidebar-nav">
						<li><a href="#" class="pms-nav-link active" data-view="projects">Projects</a></li>
						<li><a href="#" class="pms-nav-link" data-view="board">Board</a></li>
						<li><a href="#" class="pms-nav-link" data-view="gantt">Gantt</a></li>
						<li><a href="#" class="pms-nav-link" data-view="backlog">Backlog</a></li>
						<li><a href="#" class="pms-nav-link" data-view="team">Team</a></li>
						<li><a href="#" class="pms-nav-link" data-view="reports">Reports</a></li>
					</ul>
				</nav>
				<main class="pms-main">
					<div id="pms-view-container"></div>
				</main>
			</div>
		</div>
	`);

	// Navigation handling
	$(wrapper).on("click", ".pms-nav-link", function (e) {
		e.preventDefault();
		$(".pms-nav-link").removeClass("active");
		$(this).addClass("active");
		var view = $(this).data("view");
		load_view(page, view);
	});

	// Load default view
	load_view(page, "projects");

	// Subscribe to real-time updates
	frappe.realtime.on("task_updated", function (data) {
		// Refresh current view
		var active_view = $(".pms-nav-link.active").data("view");
		load_view(page, active_view);
	});
};

function load_view(page, view) {
	var container = $("#pms-view-container");

	switch (view) {
		case "projects":
			load_projects_view(container);
			break;
		case "board":
			load_board_view(container);
			break;
		case "gantt":
			load_gantt_view(container);
			break;
		case "backlog":
			load_backlog_view(container);
			break;
		case "team":
			load_team_view(container);
			break;
		case "reports":
			load_reports_view(container);
			break;
	}
}

function load_projects_view(container) {
	container.html('<div class="pms-loading">Loading projects...</div>');

	frappe.call({
		method: "next_pms.api.dashboard.get_all_projects_summary",
		callback(r) {
			if (r.message && r.message.length) {
				var html = '<div class="pms-project-grid">';
				r.message.forEach(function (project) {
					var budget_class = "safe";
					if (project.budget_utilization > 80) budget_class = "danger";
					else if (project.budget_utilization > 60) budget_class = "warning";

					var status_class = project.status.toLowerCase().replace(" ", "-");

					html += `
						<div class="pms-card" data-project="${project.name}">
							<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
								<span class="pms-card-title">${project.project_name}</span>
								<span class="pms-badge pms-badge-${status_class}">${project.status}</span>
							</div>
							<div style="font-size:12px; color:var(--pms-text-muted); margin-bottom:8px;">
								${project.client || ""} &middot; PM: ${project.project_manager || ""}
							</div>
							<div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px;">
								<span>Tasks: ${project.done_tasks}/${project.total_tasks}</span>
								<span>${project.progress}%</span>
							</div>
							<div class="pms-budget-bar">
								<div class="pms-budget-bar-fill ${budget_class}" style="width:${Math.min(project.progress, 100)}%"></div>
							</div>
							${
								project.total_budget
									? `
								<div style="display:flex; justify-content:space-between; font-size:11px; color:var(--pms-text-muted); margin-top:6px;">
									<span>Budget: ${format_currency(project.total_budget)}</span>
									<span>Used: ${(project.budget_utilization || 0).toFixed(0)}%</span>
								</div>
							`
									: ""
							}
						</div>
					`;
				});
				html += "</div>";
				container.html(html);

				// Click to open project
				container.find(".pms-card").on("click", function () {
					var project = $(this).data("project");
					frappe.set_route("Form", "PMS Project", project);
				});
			} else {
				container.html(`
					<div class="pms-empty-state">
						<div class="pms-empty-state-icon">&#128203;</div>
						<div class="pms-empty-state-title">No projects yet</div>
						<div class="pms-empty-state-desc">Create your first project to get started</div>
						<button class="btn btn-primary btn-sm" onclick="frappe.new_doc('PMS Project')">
							+ New Project
						</button>
					</div>
				`);
			}
		},
	});
}

function load_board_view(container) {
	// First, let user select a project
	var project = frappe.route_options && frappe.route_options.project;

	if (!project) {
		container.html(`
			<div style="margin-bottom:16px;">
				<label style="font-weight:600; margin-bottom:8px; display:block;">Select Project for Kanban Board</label>
				<div id="pms-project-selector"></div>
			</div>
			<div id="pms-kanban-container"></div>
		`);

		var field = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				fieldname: "project",
				options: "PMS Project",
				label: "Project",
				change: function () {
					var val = field.get_value();
					if (val) render_kanban(container.find("#pms-kanban-container"), val);
				},
			},
			parent: container.find("#pms-project-selector"),
			render_input: true,
		});
	} else {
		render_kanban(container, project);
	}
}

function render_kanban(container, project) {
	container.html('<div class="pms-loading">Loading board...</div>');

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "PMS Task",
			filters: { project: project },
			fields: [
				"name",
				"task_title",
				"status",
				"priority",
				"assigned_to",
				"due_date",
				"sprint",
			],
			limit_page_length: 0,
			order_by: "priority desc",
		},
		callback(r) {
			var tasks = r.message || [];
			var statuses = [
				"Backlog",
				"To Do",
				"In Progress",
				"In Review",
				"Done",
			];

			var html = '<div class="pms-kanban">';
			statuses.forEach(function (status) {
				var status_tasks = tasks.filter((t) => t.status === status);
				html += `
					<div class="pms-kanban-column" data-status="${status}">
						<div class="pms-kanban-column-header">
							<span>${status}</span>
							<span class="pms-kanban-column-count">${status_tasks.length}</span>
						</div>
						<div class="pms-kanban-cards" data-status="${status}">
				`;

				status_tasks.forEach(function (task) {
					var priority_class = task.priority
						? task.priority.toLowerCase()
						: "medium";
					var initials = (task.assigned_to || "?")
						.charAt(0)
						.toUpperCase();

					html += `
						<div class="pms-kanban-card" draggable="true" data-task="${task.name}">
							<div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
								<span class="pms-priority-dot pms-priority-${priority_class}"></span>
								<span style="font-size:11px; color:var(--pms-text-muted);">${task.name}</span>
							</div>
							<div class="pms-kanban-card-title">${task.task_title}</div>
							<div class="pms-kanban-card-meta">
								<span class="pms-avatar">${initials}</span>
								${task.due_date ? `<span class="pms-due-date upcoming">${task.due_date}</span>` : ""}
							</div>
						</div>
					`;
				});

				html += "</div></div>";
			});
			html += "</div>";
			container.html(html);

			// Drag and drop
			setup_kanban_dnd(container, project);
		},
	});
}

function setup_kanban_dnd(container, project) {
	var cards = container.find(".pms-kanban-card");
	var columns = container.find(".pms-kanban-cards");

	cards.on("dragstart", function (e) {
		$(this).addClass("dragging");
		e.originalEvent.dataTransfer.setData(
			"text/plain",
			$(this).data("task")
		);
	});

	cards.on("dragend", function () {
		$(this).removeClass("dragging");
	});

	columns.on("dragover", function (e) {
		e.preventDefault();
		$(this).css("background", "rgba(91, 76, 245, 0.05)");
	});

	columns.on("dragleave", function () {
		$(this).css("background", "");
	});

	columns.on("drop", function (e) {
		e.preventDefault();
		$(this).css("background", "");
		var task_name = e.originalEvent.dataTransfer.getData("text/plain");
		var new_status = $(this).data("status");

		frappe.call({
			method: "frappe.client.set_value",
			args: {
				doctype: "PMS Task",
				name: task_name,
				fieldname: "status",
				value: new_status,
			},
			callback() {
				render_kanban(container, project);
				frappe.show_alert({
					message: __("Task moved to {0}", [new_status]),
					indicator: "green",
				});
			},
		});
	});

	// Click card to open task
	cards.on("click", function (e) {
		if (!$(this).hasClass("dragging")) {
			frappe.set_route("Form", "PMS Task", $(this).data("task"));
		}
	});
}

function load_gantt_view(container) {
	container.html(`
		<div style="margin-bottom:16px;">
			<label style="font-weight:600; margin-bottom:8px; display:block;">Select Project for Gantt Chart</label>
			<div id="pms-gantt-project-selector"></div>
		</div>
		<div id="pms-gantt-container" style="overflow-x:auto;"></div>
	`);

	var field = frappe.ui.form.make_control({
		df: {
			fieldtype: "Link",
			fieldname: "project",
			options: "PMS Project",
			label: "Project",
			change: function () {
				var val = field.get_value();
				if (val) render_gantt(container.find("#pms-gantt-container"), val);
			},
		},
		parent: container.find("#pms-gantt-project-selector"),
		render_input: true,
	});
}

function render_gantt(container, project) {
	container.html('<div class="pms-loading">Loading Gantt chart...</div>');

	frappe.call({
		method: "next_pms.api.gantt.get_gantt_data",
		args: { project: project },
		callback(r) {
			var tasks = r.message || [];
			if (!tasks.length) {
				container.html(
					'<div class="pms-empty-state"><div class="pms-empty-state-title">No tasks with dates</div><div class="pms-empty-state-desc">Add start and due dates to tasks to see them on the Gantt chart</div></div>'
				);
				return;
			}

			// Use Frappe's built-in Gantt if available
			if (window.Gantt) {
				container.html(
					'<svg id="pms-gantt-svg" style="width:100%;"></svg>'
				);
				new Gantt("#pms-gantt-svg", tasks, {
					view_mode: "Week",
					on_click: function (task) {
						frappe.set_route("Form", "PMS Task", task.id);
					},
					on_date_change: function (task, start, end) {
						frappe.call({
							method: "next_pms.api.gantt.update_task_dates",
							args: {
								task: task.id,
								start_date: start,
								end_date: end,
							},
						});
					},
				});
			} else {
				// Fallback: simple table view
				var html =
					'<table class="table table-bordered"><thead><tr><th>Task</th><th>Start</th><th>End</th><th>Status</th><th>Progress</th></tr></thead><tbody>';
				tasks.forEach(function (t) {
					html += `<tr>
						<td><a href="/app/pms-task/${t.id}">${t.name}</a></td>
						<td>${t.start}</td>
						<td>${t.end}</td>
						<td>${t.status}</td>
						<td>${t.progress}%</td>
					</tr>`;
				});
				html += "</tbody></table>";
				container.html(html);
			}
		},
	});
}

function load_backlog_view(container) {
	container.html(`
		<div style="margin-bottom:16px;">
			<label style="font-weight:600;">Sprint Backlog</label>
			<div id="pms-backlog-project-selector" style="margin-top:8px;"></div>
		</div>
		<div id="pms-backlog-container"></div>
	`);

	var field = frappe.ui.form.make_control({
		df: {
			fieldtype: "Link",
			fieldname: "project",
			options: "PMS Project",
			label: "Project",
			change: function () {
				var val = field.get_value();
				if (val) render_backlog(container.find("#pms-backlog-container"), val);
			},
		},
		parent: container.find("#pms-backlog-project-selector"),
		render_input: true,
	});
}

function render_backlog(container, project) {
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "PMS Sprint",
			filters: { project: project },
			fields: ["name", "sprint_name", "status", "start_date", "end_date"],
			order_by: "start_date asc",
		},
		callback(r) {
			var sprints = r.message || [];
			var html = "";

			// Unassigned tasks (no sprint)
			html += `<div class="pms-card" style="margin-bottom:20px;">
				<div class="pms-card-title">Backlog (No Sprint)</div>
				<div id="pms-backlog-unassigned"></div>
			</div>`;

			sprints.forEach(function (sprint) {
				html += `
					<div class="pms-card" style="margin-bottom:20px;">
						<div style="display:flex; justify-content:space-between; align-items:center;">
							<div class="pms-card-title">${sprint.sprint_name}</div>
							<span class="pms-badge pms-badge-${sprint.status.toLowerCase()}">${sprint.status}</span>
						</div>
						<div style="font-size:12px; color:var(--pms-text-muted); margin-bottom:8px;">
							${sprint.start_date || ""} - ${sprint.end_date || ""}
						</div>
						<div id="pms-sprint-tasks-${sprint.name}"></div>
					</div>
				`;
			});

			container.html(html);

			// Load unassigned tasks
			load_sprint_tasks(
				container.find("#pms-backlog-unassigned"),
				project,
				null
			);

			// Load tasks for each sprint
			sprints.forEach(function (sprint) {
				load_sprint_tasks(
					container.find(`#pms-sprint-tasks-${sprint.name}`),
					project,
					sprint.name
				);
			});
		},
	});
}

function load_sprint_tasks(el, project, sprint) {
	var filters = { project: project };
	if (sprint) {
		filters.sprint = sprint;
	} else {
		filters.sprint = ["is", "not set"];
	}

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "PMS Task",
			filters: filters,
			fields: [
				"name",
				"task_title",
				"status",
				"priority",
				"assigned_to",
				"estimated_hours",
			],
			order_by: "priority desc",
			limit_page_length: 0,
		},
		callback(r) {
			var tasks = r.message || [];
			if (!tasks.length) {
				el.html(
					'<div style="color:var(--pms-text-muted); font-size:12px; padding:8px;">No tasks</div>'
				);
				return;
			}

			var html =
				'<table class="table table-sm" style="font-size:12px;"><tbody>';
			tasks.forEach(function (t) {
				html += `<tr>
					<td><span class="pms-priority-dot pms-priority-${(t.priority || "medium").toLowerCase()}"></span></td>
					<td><a href="/app/pms-task/${t.name}">${t.task_title}</a></td>
					<td>${t.status}</td>
					<td>${t.assigned_to || "-"}</td>
					<td>${t.estimated_hours || "-"}h</td>
				</tr>`;
			});
			html += "</tbody></table>";
			el.html(html);
		},
	});
}

function load_team_view(container) {
	container.html('<div class="pms-loading">Loading team view...</div>');

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "PMS Task",
			filters: {
				status: ["in", ["To Do", "In Progress", "In Review"]],
				assigned_to: ["is", "set"],
			},
			fields: [
				"name",
				"task_title",
				"status",
				"project",
				"assigned_to",
				"priority",
			],
			limit_page_length: 0,
			order_by: "assigned_to asc",
		},
		callback(r) {
			var tasks = r.message || [];
			var by_user = {};

			tasks.forEach(function (t) {
				if (!by_user[t.assigned_to]) by_user[t.assigned_to] = [];
				by_user[t.assigned_to].push(t);
			});

			var html = '<div style="display:grid; gap:16px;">';
			Object.keys(by_user).forEach(function (user) {
				var user_tasks = by_user[user];
				var initials = user.charAt(0).toUpperCase();

				html += `
					<div class="pms-card">
						<div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
							<span class="pms-avatar" style="width:32px;height:32px;font-size:14px;">${initials}</span>
							<div>
								<div style="font-weight:600;">${user}</div>
								<div style="font-size:11px; color:var(--pms-text-muted);">${user_tasks.length} active tasks</div>
							</div>
						</div>
				`;

				user_tasks.forEach(function (t) {
					html += `
						<div style="display:flex; align-items:center; gap:8px; padding:6px 0; border-top:1px solid var(--pms-border);">
							<span class="pms-priority-dot pms-priority-${(t.priority || "medium").toLowerCase()}"></span>
							<a href="/app/pms-task/${t.name}" style="font-size:13px;">${t.task_title}</a>
							<span class="pms-badge pms-badge-active" style="margin-left:auto;">${t.status}</span>
						</div>
					`;
				});

				html += "</div>";
			});
			html += "</div>";

			if (!tasks.length) {
				html = `
					<div class="pms-empty-state">
						<div class="pms-empty-state-title">No active tasks assigned</div>
						<div class="pms-empty-state-desc">Assign tasks to team members to see them here</div>
					</div>
				`;
			}

			container.html(html);
		},
	});
}

function load_reports_view(container) {
	container.html(`
		<div style="margin-bottom:16px;">
			<label style="font-weight:600;">Project Reports</label>
			<div id="pms-reports-project-selector" style="margin-top:8px;"></div>
		</div>
		<div id="pms-reports-container"></div>
	`);

	var field = frappe.ui.form.make_control({
		df: {
			fieldtype: "Link",
			fieldname: "project",
			options: "PMS Project",
			label: "Project",
			change: function () {
				var val = field.get_value();
				if (val)
					render_reports(
						container.find("#pms-reports-container"),
						val
					);
			},
		},
		parent: container.find("#pms-reports-project-selector"),
		render_input: true,
	});
}

function render_reports(container, project) {
	container.html('<div class="pms-loading">Loading reports...</div>');

	frappe.call({
		method: "next_pms.api.dashboard.get_project_dashboard",
		args: { project: project },
		callback(r) {
			var data = r.message;
			if (!data) return;

			var budget_class = "safe";
			if (data.budget_utilization > 80) budget_class = "danger";
			else if (data.budget_utilization > 60) budget_class = "warning";

			var html = `
				<div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:16px; margin-bottom:24px;">
					<div class="pms-card" style="text-align:center;">
						<div style="font-size:24px; font-weight:700; color:var(--pms-primary);">${data.total_tasks}</div>
						<div style="font-size:12px; color:var(--pms-text-muted);">Total Tasks</div>
					</div>
					<div class="pms-card" style="text-align:center;">
						<div style="font-size:24px; font-weight:700; color:var(--pms-success);">${data.total_actual_hours.toFixed(1)}h</div>
						<div style="font-size:12px; color:var(--pms-text-muted);">Total Hours Logged</div>
					</div>
					<div class="pms-card" style="text-align:center;">
						<div style="font-size:24px; font-weight:700; color:var(--pms-warning);">${format_currency(data.total_cost)}</div>
						<div style="font-size:12px; color:var(--pms-text-muted);">Total Cost</div>
					</div>
					<div class="pms-card" style="text-align:center;">
						<div style="font-size:24px; font-weight:700; color:${budget_class === "danger" ? "var(--pms-danger)" : "var(--pms-text)"};">${data.budget_utilization.toFixed(0)}%</div>
						<div style="font-size:12px; color:var(--pms-text-muted);">Budget Used</div>
					</div>
				</div>

				<div class="pms-card">
					<div class="pms-card-title">Budget Overview</div>
					<div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:8px;">
						<span>Total Budget: ${format_currency(data.total_budget)}</span>
						<span>Remaining: ${format_currency(data.budget_remaining)}</span>
					</div>
					<div class="pms-budget-bar" style="height:12px;">
						<div class="pms-budget-bar-fill ${budget_class}" style="width:${Math.min(data.budget_utilization, 100)}%"></div>
					</div>
				</div>

				<div class="pms-card" style="margin-top:16px;">
					<div class="pms-card-title">Task Status Breakdown</div>
					<table class="table" style="font-size:13px;">
						<tbody>
			`;

			Object.keys(data.task_counts).forEach(function (status) {
				var pct =
					data.total_tasks > 0
						? ((data.task_counts[status] / data.total_tasks) * 100).toFixed(0)
						: 0;
				html += `<tr><td>${status}</td><td>${data.task_counts[status]}</td><td>${pct}%</td></tr>`;
			});

			html += `</tbody></table></div>`;

			// Team breakdown
			if (data.team_members && data.team_members.length) {
				html += `
					<div class="pms-card" style="margin-top:16px;">
						<div class="pms-card-title">Team Cost Breakdown</div>
						<table class="table" style="font-size:13px;">
							<thead><tr><th>Member</th><th>Role</th><th>Rate</th><th>Hours</th><th>Cost</th></tr></thead>
							<tbody>
				`;
				data.team_members.forEach(function (m) {
					html += `<tr>
						<td>${m.user}</td>
						<td>${m.role || "-"}</td>
						<td>${format_currency(m.hourly_rate)}/h</td>
						<td>${m.total_hours}h</td>
						<td>${format_currency(m.total_cost)}</td>
					</tr>`;
				});
				html += "</tbody></table></div>";
			}

			container.html(html);
		},
	});
}

function format_currency(value) {
	if (!value) return "₹0";
	return "₹" + parseFloat(value).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}
