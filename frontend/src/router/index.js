import { createRouter, createWebHistory } from "vue-router";

import DashboardView from "@/views/DashboardView.vue";
import ProjectList from "@/views/ProjectList.vue";
import ProjectDetailView from "@/views/ProjectDetailView.vue";
import TaskDetailView from "@/views/TaskDetailView.vue";
import TeamView from "@/views/TeamView.vue";
import UserDetailView from "@/views/UserDetailView.vue";
import ReportsView from "@/views/ReportsView.vue";

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
    path: "/user-management",
    redirect: "/team?tab=users",
  },
];

const router = createRouter({
  history: createWebHistory("/next-pms/"),
  routes,
});

// Route guards for role-based access
router.beforeEach(async (to, from, next) => {
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
