import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { call } from "@/utils/frappe";
import { eventBus, EVENTS } from "@/utils/eventBus";

export const useTimerStore = defineStore("timer", () => {
  const isRunning = ref(false);
  const currentLog = ref(null);
  const currentTask = ref(null);
  const currentTaskTitle = ref("");
  const startTime = ref(null);
  const elapsedSeconds = ref(0);
  let intervalId = null;

  const elapsedFormatted = computed(() => {
    const h = Math.floor(elapsedSeconds.value / 3600);
    const m = Math.floor((elapsedSeconds.value % 3600) / 60);
    const s = elapsedSeconds.value % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  });

  function parseServerTime(dtStr) {
    // Frappe returns UTC datetimes without timezone suffix (e.g. "2026-03-12 15:30:45.123456")
    // Append 'Z' so JS Date parses it as UTC instead of local time
    if (dtStr && !dtStr.endsWith("Z") && !dtStr.includes("+")) {
      return new Date(dtStr.replace(" ", "T") + "Z").getTime();
    }
    return new Date(dtStr).getTime();
  }

  function startElapsedCounter() {
    stopElapsedCounter();
    intervalId = setInterval(() => {
      if (startTime.value) {
        elapsedSeconds.value = Math.floor(
          (Date.now() - parseServerTime(startTime.value)) / 1000
        );
      }
    }, 1000);
  }

  function stopElapsedCounter() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }

  function saveToLocalStorage() {
    if (isRunning.value) {
      localStorage.setItem(
        "pms_timer",
        JSON.stringify({
          isRunning: true,
          logName: currentLog.value,
          task: currentTask.value,
          taskTitle: currentTaskTitle.value,
          startTime: startTime.value,
        })
      );
    } else {
      localStorage.removeItem("pms_timer");
    }
  }

  function loadFromLocalStorage() {
    const saved = localStorage.getItem("pms_timer");
    if (saved) {
      try {
        const data = JSON.parse(saved);
        if (data.isRunning) {
          isRunning.value = true;
          currentLog.value = data.logName;
          currentTask.value = data.task;
          currentTaskTitle.value = data.taskTitle;
          startTime.value = data.startTime;
          startElapsedCounter();
        }
      } catch {
        localStorage.removeItem("pms_timer");
      }
    }
  }

  async function fetchRunningTimer() {
    try {
      const result = await call("next_pms.api.timer.get_running_timer");
      if (result) {
        isRunning.value = true;
        currentLog.value = result.log_name;
        currentTask.value = result.task;
        currentTaskTitle.value = result.task_title;
        startTime.value = result.start_time;
        startElapsedCounter();
        saveToLocalStorage();
      }
    } catch {
      // No running timer or error
    }
  }

  async function startTimer(taskName) {
    // Check if user is checked in (import dynamically to avoid circular deps)
    const { useCheckinStore } = await import("@/store/checkin");
    const checkinStore = useCheckinStore();
    if (!checkinStore.isCheckedIn) {
      throw new Error("You must check in before starting a timer. Please check in first.");
    }

    try {
      const result = await call("next_pms.api.timer.start_timer", {
        task: taskName,
      });
      isRunning.value = true;
      currentLog.value = result.log_name;
      currentTask.value = result.task;
      currentTaskTitle.value = result.task_title;
      startTime.value = result.start_time;
      elapsedSeconds.value = 0;
      startElapsedCounter();
      saveToLocalStorage();
      return result;
    } catch (error) {
      throw error;
    }
  }

  async function stopTimer() {
    if (!currentLog.value) return;
    try {
      const result = await call("next_pms.api.timer.stop_timer", {
        log_name: currentLog.value,
      });
      isRunning.value = false;
      stopElapsedCounter();
      const stoppedData = {
        logName: currentLog.value,
        task: currentTask.value,
        taskTitle: currentTaskTitle.value,
        durationMinutes: result.duration_minutes,
        durationHours: result.duration_hours,
      };
      currentLog.value = null;
      currentTask.value = null;
      currentTaskTitle.value = "";
      startTime.value = null;
      elapsedSeconds.value = 0;
      saveToLocalStorage();
      eventBus.emit(EVENTS.TIMER_STOPPED, stoppedData);
      return stoppedData;
    } catch (error) {
      throw error;
    }
  }

  // Initialize
  loadFromLocalStorage();

  return {
    isRunning,
    currentLog,
    currentTask,
    currentTaskTitle,
    startTime,
    elapsedSeconds,
    elapsedFormatted,
    startTimer,
    stopTimer,
    fetchRunningTimer,
    loadFromLocalStorage,
  };
});
