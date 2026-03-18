import { createRouter, createWebHistory } from "vue-router";

// Lazy-load all views for faster initial page load
const DashboardView = () => import("@/views/DashboardView.vue");
const ProjectList = () => import("@/views/ProjectList.vue");
const ProjectDetailView = () => import("@/views/ProjectDetailView.vue");
const TaskDetailView = () => import("@/views/TaskDetailView.vue");
const TeamView = () => import("@/views/TeamView.vue");
const UserDetailView = () => import("@/views/UserDetailView.vue");
const ReportsView = () => import("@/views/ReportsView.vue");

const routes = [
  {
    path: "/",
    redirect: "/dashboard",
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: DashboardView,
  },
  {
    path: "/projects",
    name: "ProjectList",
    component: ProjectList,
  },
  {
    path: "/my-tasks",
    name: "MyTasks",
    component: () => import("@/views/MyTasksView.vue"),
  },
  // Unified project detail page with tabs
  {
    path: "/project/:id",
    name: "ProjectDetail",
    component: ProjectDetailView,
    props: true,
  },
  // Legacy route redirects (preserve bookmarks)
  {
    path: "/project/:id/overview",
    redirect: (to) => `/project/${to.params.id}?tab=overview`,
  },
  {
    path: "/project/:id/board",
    redirect: (to) => `/project/${to.params.id}?tab=tasks&view=board`,
  },
  {
    path: "/project/:id/tasks",
    redirect: (to) => `/project/${to.params.id}?tab=tasks&view=list`,
  },
  {
    path: "/project/:id/gantt",
    redirect: (to) => `/project/${to.params.id}?tab=tasks&view=gantt`,
  },
  {
    path: "/project/:id/backlog",
    redirect: (to) => `/project/${to.params.id}?tab=backlog`,
  },
  {
    path: "/task/:id",
    name: "TaskDetail",
    component: TaskDetailView,
    props: true,
  },
  {
    path: "/team",
    name: "TeamView",
    component: TeamView,
    meta: { requiresSettings: true },
  },
  {
    path: "/user/:id",
    name: "UserDetail",
    component: UserDetailView,
    props: true,
  },
  {
    path: "/timelogs",
    name: "Timelogs",
    component: () => import("@/views/TimelogsView.vue"),
  },
  {
    path: "/reports",
    name: "ReportsView",
    component: ReportsView,
    meta: { requiresAnalytics: true },
  },
  {
    path: "/reports/:projectId",
    name: "ProjectReports",
    component: ReportsView,
    props: true,
    meta: { requiresAnalytics: true },
  },
  {
    path: "/task-report",
    name: "TaskReport",
    component: () => import("@/views/TaskReportView.vue"),
  },
  {
    path: "/support-tickets",
    name: "SupportTickets",
    component: () => import("@/views/SupportTicketsView.vue"),
    meta: { requiresSettings: true },
  },
  {
    path: "/portal-analytics",
    name: "PortalAnalytics",
    component: () => import("@/views/PortalAnalyticsView.vue"),
    meta: { requiresSettings: true },
  },
  {
    path: "/user-management",
    redirect: "/team?tab=users",
  },
  // ─── Client Portal Routes ───
  {
    path: "/portal",
    component: () => import("@/views/portal/PortalLayout.vue"),
    meta: { isPortal: true },
    children: [
      {
        path: "",
        name: "PortalDashboard",
        component: () => import("@/views/portal/PortalDashboard.vue"),
      },
      {
        path: "project/:id",
        name: "PortalProject",
        component: () => import("@/views/portal/PortalProject.vue"),
        props: true,
      },
      {
        path: "tickets",
        name: "PortalTickets",
        component: () => import("@/views/portal/PortalTickets.vue"),
      },
      {
        path: "reports",
        name: "PortalReports",
        component: () => import("@/views/portal/PortalReports.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory("/next-pms/"),
  routes,
});

// Route guards for role-based access and portal token auth
router.beforeEach(async (to, from, next) => {
  // Portal token login: if ?token= is present, log in via API first
  if (to.meta.isPortal && to.query.token) {
    try {
      const { call } = await import("@/utils/frappe");
      await call("next_pms.api.portal.portal_token_login", { token: to.query.token });
      // Remove token from URL after login (clean URL)
      const { token, ...otherQuery } = to.query;
      return next({ path: to.path, query: otherQuery, replace: true });
    } catch (e) {
      console.error("Portal token login failed:", e);
      // Redirect to a simple error or login page
      return next("/portal");
    }
  }

  // Redirect PMS Customer users to portal (block access to admin routes)
  if (!to.meta.isPortal && to.path !== '/portal' && !to.path.startsWith('/portal')) {
    const { useSettingsStore } = await import("@/store/settings");
    const settingsStore = useSettingsStore();
    if (!settingsStore.loaded) {
      await settingsStore.fetchSettings();
    }
    if (settingsStore.isCustomer) {
      return next("/portal");
    }
  }

  if (to.meta.requiresAnalytics || to.meta.requiresAdmin || to.meta.requiresSettings) {
    // Dynamically import to avoid circular deps
    const { useSettingsStore } = await import("@/store/settings");
    const settingsStore = useSettingsStore();
    if (!settingsStore.loaded) {
      await settingsStore.fetchSettings();
    }

    if (to.meta.requiresAnalytics && !settingsStore.canViewAnalytics) {
      return next("/dashboard");
    }
    if (to.meta.requiresAdmin && !settingsStore.isAdmin) {
      return next("/dashboard");
    }
    if (to.meta.requiresSettings && settingsStore.sidebarPermissions.settings === false) {
      return next("/dashboard");
    }
  }
  next();
});

export default router;
