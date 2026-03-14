import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { call } from "@/utils/frappe";

export const useSettingsStore = defineStore("settings", () => {
  const currency = ref("INR");
  const roles = ref([]);
  const isAdmin = ref(false);
  const isManager = ref(false);
  const isDeveloper = ref(false);
  const isCustomer = ref(false);
  const canViewFinance = ref(false);
  const canViewAnalytics = ref(false);
  const canCreateProject = ref(false);
  const canManageTeam = ref(false);
  const canManageUsers = ref(false);
  const sidebarPermissions = ref({});
  const projectTabPermissions = ref({});
  const featurePermissions = ref({});
  const loaded = ref(false);

  async function fetchSettings(force = false) {
    // Skip if already loaded and not forced — avoids redundant API calls on every route change
    if (loaded.value && !force) return;
    try {
      const result = await call("next_pms.api.settings.get_pms_settings", {}, { cache: 30000 });
      if (result) {
        currency.value = result.currency || "INR";
        roles.value = result.roles || [];
        isAdmin.value = !!result.is_admin;
        isManager.value = !!result.is_manager;
        isDeveloper.value = !!result.is_developer;
        isCustomer.value = !!result.is_customer;
        canViewFinance.value = !!result.can_view_finance;
        canViewAnalytics.value = !!result.can_view_analytics;
        canCreateProject.value = !!result.can_create_project;
        canManageTeam.value = !!result.can_manage_team;
        canManageUsers.value = !!result.can_manage_users;
        sidebarPermissions.value = result.sidebar_permissions || {};
        projectTabPermissions.value = result.project_tab_permissions || {};
        featurePermissions.value = result.feature_permissions || {};
      }
    } catch (e) {
      console.error("Failed to fetch PMS settings:", e);
    } finally {
      loaded.value = true;
    }
  }

  function formatCurrency(value) {
    const num = Number(value) || 0;
    const locale = currency.value === "INR" ? "en-IN" : "en-US";
    try {
      return new Intl.NumberFormat(locale, {
        style: "currency",
        currency: currency.value,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(num);
    } catch {
      return `${currency.value} ${num.toLocaleString()}`;
    }
  }

  return {
    currency,
    roles,
    isAdmin,
    isManager,
    isDeveloper,
    isCustomer,
    canViewFinance,
    canViewAnalytics,
    canCreateProject,
    canManageTeam,
    canManageUsers,
    sidebarPermissions,
    projectTabPermissions,
    featurePermissions,
    loaded,
    fetchSettings,
    formatCurrency,
  };
});
