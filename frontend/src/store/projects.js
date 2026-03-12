import { defineStore } from "pinia";
import { ref } from "vue";
import { call, getList, getDoc } from "@/utils/frappe";

export const useProjectStore = defineStore("projects", () => {
  const projects = ref([]);
  const currentProject = ref(null);
  const loading = ref(false);

  async function fetchProjects() {
    loading.value = true;
    try {
      projects.value = await call(
        "next_pms.api.dashboard.get_all_projects_summary"
      );
    } catch (error) {
      console.error("Failed to fetch projects:", error);
      projects.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function fetchProject(projectName) {
    loading.value = true;
    try {
      currentProject.value = await getDoc("PMS Project", projectName);
      return currentProject.value;
    } catch (error) {
      console.error("Failed to fetch project:", error);
      currentProject.value = null;
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function fetchDashboard(projectName) {
    try {
      return await call("next_pms.api.dashboard.get_project_dashboard", {
        project: projectName,
      });
    } catch (error) {
      console.error("Failed to fetch dashboard:", error);
      return null;
    }
  }

  return {
    projects,
    currentProject,
    loading,
    fetchProjects,
    fetchProject,
    fetchDashboard,
  };
});
