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
  // Offset between server clock and client clock (serverTime - clientTime) in ms
  let serverClockOffset = 0;
  let intervalId = null;

  const elapsedFormatted = computed(() => {
    const total = Math.max(0, elapsedSeconds.value);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  });

  function parseServerDatetime(dtStr) {
    // Parse a datetime string from Frappe as a local Date object
    // Frappe returns datetimes in the server's timezone without offset info
    // We treat them as-is and use serverClockOffset to reconcile with client time
    if (!dtStr) return 0;
    return new Date(dtStr.replace(" ", "T")).getTime();
  }

  function calibrateServerOffset(serverTimeStr) {
    // Calculate offset: how far ahead/behind the server clock is vs client clock
    // Both parsed as "local" (no Z suffix) — the difference gives the timezone gap
    if (serverTimeStr) {
      const serverMs = new Date(serverTimeStr.replace(" ", "T")).getTime();
      serverClockOffset = serverMs - Date.now();
    }
  }

  function startElapsedCounter() {
    stopElapsedCounter();
    intervalId = setInterval(() => {
      if (startTime.value) {
        // "Server now" = client Date.now() + offset to match server clock
        const serverNowMs = Date.now() + serverClockOffset;
        const startMs = parseServerDatetime(startTime.value);
        elapsedSeconds.value = Math.max(0, Math.floor((serverNowMs - startMs) / 1000));
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
          serverClockOffset: serverClockOffset,
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
          // Restore saved offset if available, then fetch fresh from server
          if (data.serverClockOffset != null) {
            serverClockOffset = data.serverClockOffset;
          }
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
        calibrateServerOffset(result.server_time);
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
      calibrateServerOffset(result.server_time);
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

  function resetTimerState() {
    isRunning.value = false;
    stopElapsedCounter();
    currentLog.value = null;
    currentTask.value = null;
    currentTaskTitle.value = "";
    startTime.value = null;
    elapsedSeconds.value = 0;
    saveToLocalStorage();
  }

  async function stopTimer() {
    if (!currentLog.value) {
      // No log reference — try fetching from server to find any running timer
      try {
        const running = await call("next_pms.api.timer.get_running_timer");
        if (running && running.log_name) {
          currentLog.value = running.log_name;
        } else {
          // No running timer on server either — just reset UI
          resetTimerState();
          return;
        }
      } catch {
        resetTimerState();
        return;
      }
    }

    try {
      const result = await call("next_pms.api.timer.stop_timer", {
        log_name: currentLog.value,
      });
      const stoppedData = {
        logName: currentLog.value,
        task: currentTask.value,
        taskTitle: currentTaskTitle.value,
        durationMinutes: result.duration_minutes,
        durationHours: result.duration_hours,
      };
      resetTimerState();
      eventBus.emit(EVENTS.TIMER_STOPPED, stoppedData);
      return stoppedData;
    } catch (error) {
      // If stop failed (log not found, already stopped, etc.), reset UI anyway
      console.error("Stop timer error:", error);
      resetTimerState();
      // Re-check if there's actually a running timer on server
      fetchRunningTimer();
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
