<template>
  <div class="portal-reports">
    <div class="reports-header">
      <h1>Project Reports</h1>
      <div class="report-filters">
        <select v-model="selectedProject" class="filter-select">
          <option value="">All Projects</option>
          <option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name }}</option>
        </select>
        <select v-model="period" class="filter-select">
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading-state"><div class="spinner"></div></div>

    <template v-else>
      <!-- Overall Progress -->
      <div class="report-section">
        <h2 class="section-title">Overall Progress</h2>
        <div class="progress-cards">
          <div v-for="p in reportData" :key="p.project" class="progress-card">
            <div class="progress-card-header">
              <h3>{{ p.project_name }}</h3>
              <span class="progress-pct">{{ p.progress }}%</span>
            </div>
            <div class="progress-bar-wrap">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: p.progress + '%' }"></div>
              </div>
            </div>
            <div class="progress-stats">
              <div class="ps-item">
                <span class="ps-value">{{ p.total_tasks }}</span>
                <span class="ps-label">Total</span>
              </div>
              <div class="ps-item ps-done">
                <span class="ps-value">{{ p.completed_tasks }}</span>
                <span class="ps-label">Done</span>
              </div>
              <div class="ps-item ps-active">
                <span class="ps-value">{{ p.in_progress }}</span>
                <span class="ps-label">In Progress</span>
              </div>
              <div class="ps-item ps-open">
                <span class="ps-value">{{ p.open_tasks }}</span>
                <span class="ps-label">Open</span>
              </div>
            </div>

            <!-- Period activity -->
            <div class="period-activity">
              <h4>{{ period === 'weekly' ? 'This Week' : 'This Month' }}</h4>
              <div class="activity-stats">
                <span class="activity-item">
                  <span class="activity-count done">{{ p.period_completed }}</span> completed
                </span>
                <span class="activity-item">
                  <span class="activity-count new">{{ p.period_created }}</span> created
                </span>
              </div>
            </div>

            <!-- Milestones summary -->
            <div v-if="p.milestones?.length" class="milestones-summary">
              <h4>Milestones</h4>
              <div v-for="m in p.milestones" :key="m.name" class="milestone-row">
                <span class="milestone-name">{{ m.sprint_name }}</span>
                <div class="milestone-bar">
                  <div class="milestone-fill" :style="{ width: m.progress + '%' }"></div>
                </div>
                <span class="milestone-pct">{{ m.progress }}%</span>
                <span v-if="m.approval_status && m.approval_status !== 'Pending'" class="milestone-badge" :class="'mb-' + m.approval_status.toLowerCase().replace(/\s+/g, '-')">
                  {{ m.approval_status }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { call } from '@/utils/frappe'

const loading = ref(true)
const projects = ref([])
const allReportData = ref([])
const selectedProject = ref('')
const period = ref('weekly')

const reportData = computed(() => {
  if (!selectedProject.value) return allReportData.value
  return allReportData.value.filter(r => r.project === selectedProject.value)
})

onMounted(() => loadReport())
watch(period, () => loadReport())

async function loadReport() {
  loading.value = true
  try {
    const res = await call('next_pms.api.portal.get_portal_project_report', { period: period.value })
    if (res) {
      allReportData.value = res.projects || []
      projects.value = (res.projects || []).map(p => ({ name: p.project, project_name: p.project_name }))
    }
  } catch (e) {
    console.error('Failed to load report:', e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.portal-reports { max-width: 100%; }

.reports-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 12px; }
.reports-header h1 { font-size: 20px; font-weight: 700; color: #1e293b; margin: 0; }
.report-filters { display: flex; gap: 8px; }
.filter-select { padding: 6px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; background: #fff; }

.section-title { font-size: 16px; font-weight: 600; color: #334155; margin: 0 0 16px; }

.progress-cards { display: flex; flex-direction: column; gap: 16px; }
.progress-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px;
}
.progress-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.progress-card-header h3 { font-size: 16px; font-weight: 600; color: #1e293b; margin: 0; }
.progress-pct { font-size: 20px; font-weight: 700; color: #2563eb; }

.progress-bar-wrap { margin-bottom: 16px; }
.progress-bar { height: 8px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #2563eb, #3b82f6); border-radius: 4px; transition: width 0.5s; }

.progress-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.ps-item { text-align: center; padding: 10px; background: #f8fafc; border-radius: 8px; }
.ps-value { display: block; font-size: 20px; font-weight: 700; color: #1e293b; }
.ps-label { font-size: 11px; color: #94a3b8; }
.ps-done { background: #f0fdf4; }
.ps-done .ps-value { color: #16a34a; }
.ps-active { background: #eff6ff; }
.ps-active .ps-value { color: #2563eb; }
.ps-open { background: #fffbeb; }
.ps-open .ps-value { color: #d97706; }

.period-activity { margin-bottom: 16px; padding: 12px; background: #f8fafc; border-radius: 8px; }
.period-activity h4 { font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 8px; }
.activity-stats { display: flex; gap: 16px; }
.activity-item { font-size: 13px; color: #64748b; }
.activity-count { font-weight: 700; font-size: 15px; margin-right: 4px; }
.activity-count.done { color: #16a34a; }
.activity-count.new { color: #2563eb; }

.milestones-summary { padding-top: 12px; border-top: 1px solid #f1f5f9; }
.milestones-summary h4 { font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 10px; }
.milestone-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.milestone-name { font-size: 13px; font-weight: 500; color: #334155; min-width: 120px; }
.milestone-bar { flex: 1; height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden; }
.milestone-fill { height: 100%; background: #2563eb; border-radius: 3px; }
.milestone-pct { font-size: 12px; font-weight: 600; color: #64748b; min-width: 35px; text-align: right; }
.milestone-badge { font-size: 10px; font-weight: 500; padding: 1px 6px; border-radius: 4px; }
.mb-approved { background: #dcfce7; color: #16a34a; }
.mb-ready-for-review { background: #fffbeb; color: #d97706; }
.mb-changes-requested { background: #fef2f2; color: #dc2626; }

.loading-state { display: flex; flex-direction: column; align-items: center; padding: 60px; color: #94a3b8; gap: 12px; }
.spinner { width: 28px; height: 28px; border: 3px solid #e5e7eb; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .progress-stats { grid-template-columns: repeat(2, 1fr); }
  .milestone-name { min-width: 80px; }
}
</style>
