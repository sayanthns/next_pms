import { defineStore } from "pinia";
import { ref } from "vue";
import { call, getList, getDoc, setValue } from "@/utils/frappe";
import { eventBus, EVENTS } from "@/utils/eventBus";

export const useTaskStore = defineStore("tasks", () => {
  const tasks = ref([]);
  const currentTask = ref(null);
  const loading = ref(false);

  async function fetchTasks(projectName, filters = {}) {
    loading.value = true;
    try {
      const allFilters = { project: projectName, ...filters };
      const rawTasks = await getList("PMS Task", {
        fields: [
          "name",
          "task_title",
          "status",
          "priority",
          "assigned_to",
          "due_date",
          "start_date",
          "sprint",
          "estimated_hours",
          "actual_hours",
          "calculated_cost",
          "task_type",
          "is_billable",
          "parent_task",
        ],
        filters: allFilters,
        orderBy: "priority desc, modified desc",
        limit: 0,
      });

      // Fetch assignees for all tasks in bulk via dedicated API
      const taskNames = rawTasks.map((t) => t.name);
      let assigneesMap = {};
      if (taskNames.length) {
        try {
          assigneesMap = await call("next_pms.api.crud.get_bulk_task_assignees", {
            task_names: JSON.stringify(taskNames),
          });
        } catch (e) {
          console.warn("Could not fetch assignees:", e);
        }
      }

      // Merge assignees into tasks
      tasks.value = rawTasks.map((t) => ({
        ...t,
        assignees: assigneesMap[t.name] || [],
      }));
    } catch (error) {
      console.error("Failed to fetch tasks:", error);
      tasks.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function fetchTask(taskName) {
    loading.value = true;
    try {
      const doc = await getDoc("PMS Task", taskName);
      currentTask.value = doc;
    } catch (error) {
      console.error("Failed to fetch task:", error);
      currentTask.value = null;
    } finally {
      loading.value = false;
    }
  }

  async function updateTaskStatus(taskName, newStatus) {
    try {
      await call("next_pms.api.crud.update_task_status", {
        task: taskName,
        status: newStatus,
      });
      const task = tasks.value.find((t) => t.name === taskName);
      if (task) task.status = newStatus;
      if (currentTask.value && currentTask.value.name === taskName) {
        currentTask.value.status = newStatus;
      }
      eventBus.emit(EVENTS.TASK_STATUS_CHANGED, { task: taskName, status: newStatus });
      return true;
    } catch (error) {
      console.error("Failed to update task status:", error);
      return false;
    }
  }

  async function updateTaskAssignees(taskName, assignees) {
    try {
      const result = await call("next_pms.api.crud.update_task_assignees", {
        task: taskName,
        assignees: JSON.stringify(assignees),
      });
      const task = tasks.value.find((t) => t.name === taskName);
      if (task) task.assignees = result.assignees;
      if (currentTask.value && currentTask.value.name === taskName) {
        currentTask.value.assignees = result.assignees;
      }
      return result;
    } catch (error) {
      console.error("Failed to update assignees:", error);
      return null;
    }
  }

  async function fetchTaskTimeLogs(taskName) {
    try {
      return await getList("PMS Time Log", {
        fields: [
          "name",
          "user",
          "start_time",
          "end_time",
          "duration_hours",
          "duration_minutes",
          "notes",
          "is_running",
        ],
        filters: { task: taskName },
        orderBy: "start_time desc",
        limit: 50,
      });
    } catch (error) {
      console.error("Failed to fetch time logs:", error);
      return [];
    }
  }

  async function fetchTaskComments(taskName) {
    try {
      return await getList("PMS Comment", {
        fields: ["name", "user", "comment", "timestamp", "mentions"],
        filters: { task: taskName },
        orderBy: "timestamp desc",
        limit: 50,
      });
    } catch (error) {
      console.error("Failed to fetch comments:", error);
      return [];
    }
  }

  return {
    tasks,
    currentTask,
    loading,
    fetchTasks,
    fetchTask,
    updateTaskStatus,
    updateTaskAssignees,
    fetchTaskTimeLogs,
    fetchTaskComments,
  };
});
