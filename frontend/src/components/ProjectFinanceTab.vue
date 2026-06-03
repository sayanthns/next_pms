<template>
  <div class="pf">
    <div class="pf-head">
      <h2 class="pf-title">Project Finance</h2>
      <p class="pf-sub">Budget, spend and collections across all active projects. Amounts in {{ currencyLabel }}.</p>
    </div>

    <div v-if="errorMsg" class="pf-error">{{ errorMsg }}</div>
    <div v-if="loading" class="pf-loading">Loading…</div>

    <template v-else>
      <!-- Totals strip -->
      <div class="pf-cards">
        <div class="pf-card"><span class="v">{{ fmt(totals.budget) }}</span><span class="l">Total Budget</span></div>
        <div class="pf-card"><span class="v">{{ fmt(totals.spent) }}</span><span class="l">Spent (Labour+Exp)</span></div>
        <div class="pf-card"><span class="v" :class="{ over: totals.remaining < 0 }">{{ fmt(totals.remaining) }}</span><span class="l">Remaining</span></div>
        <div class="pf-card ok"><span class="v">{{ fmt(totals.received) }}</span><span class="l">Received</span></div>
        <div class="pf-card warn"><span class="v" :class="{ over: totals.outstanding > 0 }">{{ fmt(totals.outstanding) }}</span><span class="l">Outstanding</span></div>
      </div>

      <input v-model="q" type="text" placeholder="Filter by project or client…" class="pf-filter" />

      <div class="pf-table-wrap">
        <table class="pf-table">
          <thead>
            <tr>
              <th>Project</th><th>Status</th>
              <th class="r">Budget</th><th class="r">Labour</th><th class="r">Expenses</th>
              <th class="r">Spent</th><th class="r">Remaining</th><th class="r">Received</th><th class="r">Outstanding</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filtered" :key="r.project" @click="goProject(r.project)" class="pf-row">
              <td class="pf-name">{{ r.project_name }}</td>
              <td><span class="pf-status" :class="'st-' + r.status.toLowerCase().replace(' ','-')">{{ r.status }}</span></td>
              <td class="r">{{ fmt(r.budget) }}</td>
              <td class="r">{{ fmt(r.labour) }}</td>
              <td class="r">{{ fmt(r.expenses) }}</td>
              <td class="r">{{ fmt(r.spent) }}</td>
              <td class="r" :class="{ over: r.remaining < 0 }">{{ fmt(r.remaining) }}</td>
              <td class="r">{{ fmt(r.received) }}</td>
              <td class="r" :class="{ over: r.outstanding > 0 }">{{ fmt(r.outstanding) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="pf-total">
              <td colspan="2"><strong>Total ({{ filtered.length }})</strong></td>
              <td class="r"><strong>{{ fmt(sum('budget')) }}</strong></td>
              <td class="r"><strong>{{ fmt(sum('labour')) }}</strong></td>
              <td class="r"><strong>{{ fmt(sum('expenses')) }}</strong></td>
              <td class="r"><strong>{{ fmt(sum('spent')) }}</strong></td>
              <td class="r"><strong>{{ fmt(sum('remaining')) }}</strong></td>
              <td class="r"><strong>{{ fmt(sum('received')) }}</strong></td>
              <td class="r"><strong>{{ fmt(sum('outstanding')) }}</strong></td>
            </tr>
          </tfoot>
        </table>
        <p v-if="!rows.length" class="pf-empty">No projects found.</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '@/utils/frappe'
import { useSettingsStore } from '@/store/settings'

const router = useRouter()
const settingsStore = useSettingsStore()
const rows = ref([])
const totals = ref({})
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')

const currencyLabel = computed(() => settingsStore.currency || 'INR')
function fmt(v) { return settingsStore.formatCurrency(v || 0) }

const filtered = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return rows.value
  return rows.value.filter(r =>
    (r.project_name || '').toLowerCase().includes(s) || (r.client || '').toLowerCase().includes(s)
  )
})
function sum(k) { return filtered.value.reduce((a, r) => a + (r[k] || 0), 0) }
function goProject(name) { router.push(`/project/${name}?tab=billing`) }

async function load() {
  loading.value = true; errorMsg.value = ''
  try {
    const res = await call('next_pms.api.billing.get_projects_finance_summary')
    rows.value = res.rows || []
    totals.value = res.totals || {}
  } catch (e) {
    errorMsg.value = (e && e.message) || 'Failed to load finance report.'
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.pf { padding: 4px 0; }
.pf-head { margin-bottom: 16px; }
.pf-title { font-size: 20px; font-weight: 800; margin: 0; }
.pf-sub { font-size: 13px; color: #6b7280; margin: 4px 0 0; }
.pf-error { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 12px; font-size: 13px; margin-bottom: 12px; }
.pf-loading { color: #9ca3af; padding: 20px 0; }
.pf-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
.pf-card { background: var(--bg-surface,#fff); border: 1px solid var(--border-default,#e5e7eb); border-radius: 10px; padding: 14px; text-align: center; }
.pf-card.ok { background: #f0fdf4; } .pf-card.warn { background: #fffbeb; }
.pf-card .v { display: block; font-size: 18px; font-weight: 800; }
.pf-card .v.over { color: #dc2626; }
.pf-card .l { display: block; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af; margin-top: 4px; }
.pf-filter { width: 100%; max-width: 320px; padding: 8px 12px; border: 1px solid var(--border-default,#e5e7eb); border-radius: 8px; font-size: 13px; margin-bottom: 12px; }
.pf-table-wrap { overflow-x: auto; border: 1px solid var(--border-default,#e5e7eb); border-radius: 10px; }
.pf-table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.pf-table th, .pf-table td { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; text-align: left; }
.pf-table th.r, .pf-table td.r { text-align: right; }
.pf-table thead th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; color: #6b7280; background: #f9fafb; }
.pf-row { cursor: pointer; }
.pf-row:hover { background: #f8fafc; }
.pf-name { font-weight: 600; }
.pf-table td.over { color: #dc2626; font-weight: 600; }
.pf-total td { border-top: 2px solid #e5e7eb; background: #fafafa; }
.pf-status { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px; background: #eef2ff; color: #3730a3; }
.st-active { background: #d1fae5; color: #065f46; }
.st-completed { background: #e0e7ff; color: #3730a3; }
.st-on-hold { background: #fef3c7; color: #92400e; }
.st-planning { background: #f3f4f6; color: #6b7280; }
.pf-empty { padding: 20px; color: #9ca3af; text-align: center; }
</style>
