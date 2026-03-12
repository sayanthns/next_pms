import { defineStore } from "pinia";
import { ref } from "vue";
import { call } from "@/utils/frappe";

export const useCheckinStore = defineStore("checkin", () => {
  const isCheckedIn = ref(false);
  const checkinData = ref(null);
  const loading = ref(false);

  async function fetchTodayCheckin() {
    try {
      const result = await call("next_pms.api.checkin.get_today_checkin");
      if (result && result.is_active) {
        isCheckedIn.value = true;
        checkinData.value = result;
      } else {
        isCheckedIn.value = false;
        checkinData.value = result || null;
      }
    } catch (e) {
      console.error("Failed to fetch check-in status:", e);
    }
  }

  async function doCheckin() {
    loading.value = true;
    try {
      const result = await call("next_pms.api.checkin.checkin");
      isCheckedIn.value = true;
      checkinData.value = result;
      return result;
    } catch (error) {
      throw error;
    } finally {
      loading.value = false;
    }
  }

  async function doCheckout() {
    loading.value = true;
    try {
      const result = await call("next_pms.api.checkin.checkout");
      isCheckedIn.value = false;
      checkinData.value = result;
      return result;
    } catch (error) {
      throw error;
    } finally {
      loading.value = false;
    }
  }

  return {
    isCheckedIn,
    checkinData,
    loading,
    fetchTodayCheckin,
    doCheckin,
    doCheckout,
  };
});
