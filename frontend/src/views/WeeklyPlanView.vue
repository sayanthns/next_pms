<template>
  <div class="wp">
    <!-- Header -->
    <header class="wp-head">
      <div>
        <h1 class="wp-title">Weekly Plan</h1>
        <p class="wp-sub" v-if="plan">{{ plan.title }}</p>
        <p class="wp-sub" v-else>Team plan for the week</p>
      </div>
      <div class="wp-controls">
        <template v-if="weeks.length">
          <label for="wp-week" class="wp-sr">Week</label>
          <select id="wp-week" v-model="selectedWeek" class="wp-select">
            <option v-for="w in weeks" :key="w.name" :value="w.week_start">{{ w.title || w.week_start }}</option>
          </select>
        </template>
        <template v-if="canEdit && !editing">
          <button class="wp-editbtn" v-if="plan" @click="startEdit">Edit</button>
          <button class="wp-editbtn primary" @click="startNew">New week</button>
        </template>
      </div>
    </header>

    <WeeklyPlanEditor v-if="editing" :initial="editInitial" :weeks="weeks"
                      @saved="onSaved" @cancel="editing = false" />

    <template v-if="!editing">
    <div v-if="errorMsg" class="wp-error" role="alert">{{ errorMsg }} <button class="wp-link" @click="loadWeek(true)">Retry</button></div>
    <div v-if="loading" class="wp-loading"><span class="wp-spin" aria-hidden="true"></span> Loading plan…</div>
    <div v-else-if="!plan" class="wp-empty">No weekly plan published yet.</div>

    <template v-else>
      <!-- Hero stats -->
      <div class="wp-stats">
        <div class="wp-stat"><b>{{ (plan.projects || []).length }}</b><span>Active projects</span></div>
        <div class="wp-stat"><b>{{ (plan.closures || []).length }}</b><span>Closures</span></div>
        <div class="wp-stat"><b>{{ (plan.priorities || []).length }}</b><span>Priorities</span></div>
        <div class="wp-stat" v-if="plan.headline_note"><b>!</b><span>{{ plan.headline_note }}</span></div>
      </div>
      <p v-if="plan.intro" class="wp-intro">{{ plan.intro }}</p>

      <!-- People -->
      <section class="wp-sec" v-if="(plan.allocations || []).length" aria-labelledby="wp-people">
        <h2 id="wp-people" class="wp-h">Who's on what</h2>
        <p class="wp-secsub">Planned hours vs capacity. Utilisation flags overload — not a scorecard.</p>
        <div class="wp-people">
          <article class="wp-pcard" v-for="a in plan.allocations" :key="a.name || a.member">
            <div class="wp-phead">
              <span class="wp-av" :style="{ background: avatarColor(a.display_name || a.member) }">{{ initials(a.display_name || a.member) }}</span>
              <div class="wp-pwho">
                <div class="wp-pname">{{ a.display_name || a.member }}</div>
                <div class="wp-prole">{{ a.role }}</div>
              </div>
              <span class="wp-util" :class="utilClass(a)" :title="utilTitle(a)">
                {{ num(a.planned_hours) }}h<span class="wp-utilpct" v-if="cap(a)"> · {{ utilPct(a) }}%</span>
              </span>
            </div>
            <div class="wp-tasks" v-if="taskList(a).length">
              <span v-for="(t, i) in taskList(a)" :key="i" class="wp-t" :class="t.cls">{{ t.text }}</span>
            </div>
          </article>
        </div>
      </section>

      <!-- Projects -->
      <section class="wp-sec" v-if="(plan.projects || []).length" aria-labelledby="wp-proj">
        <h2 id="wp-proj" class="wp-h">Project-wise plan</h2>
        <div class="wp-tablewrap">
          <table class="wp-table">
            <thead><tr><th>Project</th><th>Focus</th><th>Team</th><th class="r">Effort</th><th>Status</th><th>Health</th></tr></thead>
            <tbody>
              <tr v-for="p in plan.projects" :key="p.name || p.project">
                <td class="wp-strong">{{ p.project_name || p.project }}</td>
                <td>{{ p.focus }}</td>
                <td><span v-for="(m, i) in (p.team_members || [])" :key="i" class="wp-chip">{{ initials(m.full_name || m.user) }}</span></td>
                <td class="r">{{ p.effort }}</td>
                <td><span class="wp-badge" :class="'bc-' + (p.status_color || 'grey')">{{ p.status_label || '—' }}</span></td>
                <td><span v-if="p.health" class="wp-badge" :class="'rag-' + p.health.toLowerCase()" :title="p.health_reason">{{ p.health }}</span><span v-else class="wp-muted">—</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Closures -->
      <section class="wp-sec" v-if="(plan.closures || []).length" aria-labelledby="wp-clo">
        <h2 id="wp-clo" class="wp-h">Project closures</h2>
        <div class="wp-tablewrap">
          <table class="wp-table">
            <thead><tr><th>Project</th><th>This week</th><th>Owner</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="c in plan.closures" :key="c.name || c.project">
                <td class="wp-strong">{{ c.project }}</td><td>{{ c.work }}</td><td>{{ c.owner }}</td>
                <td><span class="wp-badge bc-grey">{{ c.status_label || 'Closure' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Priorities (WSJF-ranked) -->
      <section class="wp-sec" v-if="rankedPriorities.length" aria-labelledby="wp-prio">
        <h2 id="wp-prio" class="wp-h">Priority stack</h2>
        <p class="wp-secsub">Ranked by WSJF — (value + time-criticality + risk-reduction) ÷ job-size. Protect top-down.</p>
        <div class="wp-prio">
          <article class="wp-pc" :class="{ hot: pr.hot }" v-for="(pr, i) in rankedPriorities" :key="pr.name || i">
            <span class="wp-rank">{{ i + 1 }}</span>
            <h3 class="wp-pch">{{ pr.project }}</h3>
            <p class="wp-pcp" v-if="pr.note">{{ pr.note }}</p>
            <div class="wp-pcmeta">
              <span class="wp-badge" :class="'bc-' + (pr.badge_color || 'green')" v-if="pr.badge_label">{{ pr.badge_label }}</span>
              <span class="wp-wsjf" :title="'WSJF score'">WSJF {{ num(pr.wsjf_score) }}</span>
            </div>
          </article>
        </div>
      </section>

      <!-- Watch list (RAID) -->
      <section class="wp-sec" v-if="(plan.watch_list || []).length" aria-labelledby="wp-watch">
        <h2 id="wp-watch" class="wp-h">Watch list</h2>
        <div class="wp-tablewrap">
          <table class="wp-table">
            <thead><tr><th>Watch</th><th>RAID</th><th>Level</th><th>How we handle it</th><th>Owner</th></tr></thead>
            <tbody>
              <tr v-for="(w, i) in plan.watch_list" :key="w.name || i">
                <td>{{ w.item }}</td>
                <td><span class="wp-badge raid" :class="'raid-' + (w.raid_type || 'Risk').toLowerCase()">{{ w.raid_type || 'Risk' }}</span></td>
                <td><span class="wp-badge" :class="lvlClass(w.level)">{{ w.level || 'Med' }}</span></td>
                <td>{{ w.mitigation }}</td>
                <td>{{ w.owner }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Checklist -->
      <section class="wp-sec" v-if="(plan.checklist || []).length" aria-labelledby="wp-chk">
        <h2 id="wp-chk" class="wp-h">This week's checklist</h2>
        <p class="wp-secsub">Tick as you go (saved in your browser).</p>
        <ul class="wp-cklist">
          <li v-for="(item, i) in plan.checklist" :key="i">
            <label class="wp-ck" :class="{ done: checks[ckKey(i)] }">
              <input type="checkbox" v-model="checks[ckKey(i)]" @change="saveChecks" />
              <span class="wp-ckbox" aria-hidden="true">✓</span>
              <span class="wp-cklbl"><span class="wp-ckwho" v-if="item.who">{{ item.who }}</span>{{ item.item }}</span>
            </label>
          </li>
        </ul>
      </section>

      <!-- Narrative -->
      <section class="wp-sec" v-if="plan.working_notes || plan.week_shape || plan.meetings_note">
        <div class="wp-narr" v-if="plan.working_notes"><h2 class="wp-h">How we're working</h2><div class="wp-rt" v-html="plan.working_notes"></div></div>
        <div class="wp-narr" v-if="plan.meetings_note"><h2 class="wp-h">Meetings &amp; closures</h2><div class="wp-rt" v-html="plan.meetings_note"></div></div>
        <div class="wp-narr" v-if="plan.week_shape"><h2 class="wp-h">Week shape</h2><div class="wp-rt" v-html="plan.week_shape"></div></div>
      </section>
    </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { call } from '@/utils/frappe'
import { useSettingsStore } from '@/store/settings'
import WeeklyPlanEditor from '@/components/WeeklyPlanEditor.vue'

const settingsStore = useSettingsStore()
const weeks = ref([])
const selectedWeek = ref(null)
const plan = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const checks = ref({})
const editing = ref(false)
const editInitial = ref(null)
const canEdit = computed(() => settingsStore.isManager || settingsStore.isAdmin)

function startEdit() { editInitial.value = plan.value; editing.value = true }
function startNew() { editInitial.value = null; editing.value = true }
async function onSaved(weekStart) {
  editing.value = false
  await loadWeeks()
  if (weekStart) selectedWeek.value = weekStart
  await loadWeek(true)
}

function num(v) { const n = Number(v); return Number.isFinite(n) ? Math.round(n * 100) / 100 : 0 }
function cap(a) { return Number(a.capacity_hours) > 0 }
function utilPct(a) { return cap(a) ? Math.round(num(a.planned_hours) / num(a.capacity_hours) * 100) : 0 }
function utilClass(a) {
  if (!cap(a)) return ''
  const p = utilPct(a)
  if (p > 100) return 'u-over'
  if (p > 85) return 'u-hot'
  if (p < 60) return 'u-low'
  return 'u-ok'
}
function utilTitle(a) {
  if (!cap(a)) return ''
  const p = utilPct(a)
  const tag = p > 100 ? 'over-allocated' : p > 85 ? 'near capacity' : p < 60 ? 'under-utilised' : 'healthy (70–85% target)'
  return num(a.planned_hours) + 'h of ' + num(a.capacity_hours) + 'h capacity — ' + tag
}
function taskList(a) {
  const raw = (a.tasks || '').split('\n').map(s => s.trim()).filter(Boolean)
  return raw.map(line => {
    let cls = '', text = line
    if (line.startsWith('**')) { cls = 'key'; text = line.slice(2).trim() }
    else if (line.startsWith('!')) { cls = 'lock'; text = line.slice(1).trim() }
    else if (line.startsWith('~')) { cls = 'prov'; text = line.slice(1).trim() }
    return { cls, text }
  })
}
function initials(name) {
  if (!name) return '?'
  const parts = String(name).replace(/@.*/, '').split(/[\s._]+/).filter(Boolean)
  return ((parts[0] || '')[0] || '' + (parts[1] || '')[0] || '').toUpperCase().slice(0, 2)
    || String(name)[0].toUpperCase()
}
function avatarColor(name) {
  const colors = ['#1A2E3A', '#2c7d63', '#3A9E7E', '#0891b2', '#E8631A', '#7c3aed', '#1d4ed8', '#16a34a', '#9a3412']
  let h = 0
  for (const c of String(name)) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return colors[h % colors.length]
}
function lvlClass(l) { return l === 'High' ? 'bc-red' : l === 'Low' ? 'bc-grey' : 'bc-orange' }

const rankedPriorities = computed(() =>
  [...(plan.value?.priorities || [])].sort((a, b) => num(b.wsjf_score) - num(a.wsjf_score)))

function ckKey(i) { return (selectedWeek.value || 'wk') + ':' + i }
function saveChecks() { try { localStorage.setItem('wp-checks', JSON.stringify(checks.value)) } catch (e) {} }
function loadChecks() { try { checks.value = JSON.parse(localStorage.getItem('wp-checks') || '{}') } catch (e) { checks.value = {} } }

async function loadWeeks() {
  try { weeks.value = await call('next_pms.api.weekly_plan.list_weeks') || [] }
  catch (e) { weeks.value = [] }
  if (weeks.value.length && !selectedWeek.value) selectedWeek.value = weeks.value[0].week_start
}
async function loadWeek(force = false) {
  loading.value = true; errorMsg.value = ''
  try {
    plan.value = await call('next_pms.api.weekly_plan.get_week',
      selectedWeek.value ? { week_start: selectedWeek.value } : {})
  } catch (e) {
    plan.value = null
    errorMsg.value = (e && e.message) || 'Failed to load the weekly plan.'
  } finally { loading.value = false }
}

watch(selectedWeek, () => loadWeek())
onMounted(async () => { loadChecks(); await loadWeeks(); await loadWeek() })
</script>

<style scoped>
.wp { padding: 4px 0 40px; color: #1a2330; }
.wp-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.wp-head { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 14px; margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid #e3e9e6; }
.wp-title { font-size: 22px; font-weight: 800; margin: 0; letter-spacing: -0.3px; color: #1A2E3A; }
.wp-sub { margin: 4px 0 0; font-size: 13.5px; color: #64748b; }
.wp-select { padding: 8px 12px; border: 1px solid #d0d5dd; border-radius: 8px; font-size: 13.5px; background: #fff; color: inherit; }
.wp-select:focus-visible { outline: 2px solid #3A9E7E; outline-offset: 1px; }
.wp-editbtn { padding: 8px 13px; border: 1px solid #d0d5dd; border-radius: 8px; background: #fff; cursor: pointer; font-size: 13px; font-weight: 600; color: #1A2E3A; }
.wp-editbtn:hover { background: #f5f7fa; }
.wp-editbtn.primary { background: #3A9E7E; color: #fff; border-color: #2c7d63; }
.wp-editbtn:focus-visible { outline: 2px solid #3A9E7E; outline-offset: 1px; }

.wp-error { background: #fef2f2; border: 1px solid #fda29b; color: #912018; padding: 10px 14px; border-radius: 10px; margin-bottom: 14px; }
.wp-link { background: none; border: none; color: #b42318; font-weight: 700; cursor: pointer; text-decoration: underline; }
.wp-loading, .wp-empty { padding: 48px 0; text-align: center; color: #64748b; }
.wp-spin { display: inline-block; width: 14px; height: 14px; border: 2px solid #cbd5d0; border-top-color: #3A9E7E; border-radius: 50%; animation: wpspin .7s linear infinite; vertical-align: middle; }
@keyframes wpspin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .wp-spin { animation-duration: 1.4s; } }

.wp-stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.wp-stat { background: #fff; border: 1px solid #e3e9e6; border-radius: 12px; padding: 12px 16px; min-width: 110px; }
.wp-stat b { display: block; font-size: 22px; font-weight: 800; color: #1A2E3A; }
.wp-stat span { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .4px; }
.wp-intro { font-size: 14px; color: #475569; margin-bottom: 20px; max-width: 760px; }

.wp-sec { margin-bottom: 32px; }
.wp-h { font-size: 17px; font-weight: 800; color: #1A2E3A; margin: 0 0 4px; letter-spacing: -0.2px; }
.wp-secsub { color: #64748b; font-size: 13px; margin: 0 0 14px; }

.wp-people { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.wp-pcard { background: #fff; border: 1px solid #e3e9e6; border-radius: 13px; padding: 15px 16px; }
.wp-phead { display: flex; align-items: center; gap: 11px; margin-bottom: 11px; }
.wp-av { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 12px; color: #fff; flex-shrink: 0; }
.wp-pwho { min-width: 0; }
.wp-pname { font-weight: 800; color: #1A2E3A; font-size: 15px; }
.wp-prole { font-size: 11.5px; color: #94a3b8; }
.wp-util { margin-left: auto; font-size: 12px; font-weight: 800; padding: 3px 10px; border-radius: 8px; white-space: nowrap; border: 1px solid; }
.u-ok { color: #2c7d63; background: #eef6f3; border-color: #cfe7dd; }
.u-low { color: #475569; background: #f1f5f9; border-color: #e2e8f0; }
.u-hot { color: #9a3412; background: #fff7ed; border-color: #fcd9b6; }
.u-over { color: #b91c1c; background: #fef2f2; border-color: #fbc4c4; }
.wp-tasks { display: flex; flex-wrap: wrap; gap: 6px; }
.wp-t { font-size: 12px; background: #f4f8f6; color: #334155; border: 1px solid #e3e9e6; padding: 3px 10px; border-radius: 7px; }
.wp-t.key { background: #eef6f3; border-color: #cfe7dd; color: #2c7d63; font-weight: 600; }
.wp-t.lock { background: #fff7ed; border-color: #fcd9b6; color: #9a3412; font-weight: 600; }
.wp-t.prov { background: #f1f5f9; color: #64748b; border-color: #e2e8f0; }

.wp-tablewrap { overflow-x: auto; }
.wp-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13.5px; background: #fff; border: 1px solid #e3e9e6; border-radius: 12px; overflow: hidden; }
.wp-table thead th { background: #f4f8f6; color: #1A2E3A; text-align: left; padding: 10px 14px; font-size: 10.5px; text-transform: uppercase; letter-spacing: .5px; }
.wp-table th.r, .wp-table td.r { text-align: right; }
.wp-table td { padding: 10px 14px; border-top: 1px solid #eef2f0; vertical-align: top; color: #41514c; }
.wp-strong { font-weight: 700; color: #1A2E3A; }
.wp-muted { color: #94a3b8; }
.wp-chip { display: inline-block; font-size: 11px; font-weight: 700; background: #eef2f0; color: #41514c; border: 1px solid #dde5e1; padding: 1px 7px; border-radius: 6px; margin: 1px 3px 1px 0; }

.wp-badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 20px; white-space: nowrap; }
.bc-red { background: #fef2f2; color: #b91c1c; } .bc-orange { background: #fff7ed; color: #9a3412; }
.bc-green { background: #f0fdf4; color: #15803d; } .bc-blue { background: #eff6ff; color: #1d4ed8; } .bc-grey { background: #f1f5f9; color: #475569; }
.rag-green { background: #f0fdf4; color: #15803d; } .rag-amber { background: #fff7ed; color: #9a3412; } .rag-red { background: #fef2f2; color: #b91c1c; }
.raid-risk { background: #fef2f2; color: #b91c1c; } .raid-assumption { background: #eff6ff; color: #1d4ed8; }
.raid-issue { background: #fff7ed; color: #9a3412; } .raid-dependency { background: #f5f3ff; color: #6d28d9; }

.wp-prio { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.wp-pc { position: relative; background: #fff; border: 1px solid #e3e9e6; border-top: 3px solid #3A9E7E; border-radius: 12px; padding: 14px 16px; }
.wp-pc.hot { border-top-color: #E8631A; }
.wp-rank { position: absolute; top: -12px; right: 14px; width: 26px; height: 26px; border-radius: 50%; background: #1A2E3A; color: #fff; font-weight: 800; font-size: 13px; display: flex; align-items: center; justify-content: center; }
.wp-pch { font-size: 15px; color: #1A2E3A; font-weight: 800; margin: 0 0 3px; }
.wp-pcp { font-size: 12.5px; color: #64748b; margin: 0 0 8px; }
.wp-pcmeta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.wp-wsjf { font-size: 11px; font-weight: 800; color: #2c7d63; background: #eef6f3; border: 1px solid #cfe7dd; padding: 2px 8px; border-radius: 6px; }

.wp-cklist { list-style: none; margin: 0; padding: 0; }
.wp-ck { display: flex; gap: 12px; align-items: flex-start; background: #fff; border: 1px solid #e3e9e6; border-radius: 11px; padding: 12px 16px; margin-bottom: 8px; cursor: pointer; }
.wp-ck input { position: absolute; opacity: 0; width: 0; height: 0; }
.wp-ckbox { width: 20px; height: 20px; border: 2px solid #cbd5d0; border-radius: 6px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; background: #fff; color: transparent; font-size: 12px; font-weight: 900; }
.wp-ck input:focus-visible + .wp-ckbox { outline: 2px solid #3A9E7E; outline-offset: 2px; }
.wp-cklbl { font-size: 14px; color: #374151; }
.wp-ckwho { display: inline-block; font-size: 11px; font-weight: 700; color: #2c7d63; background: #e9f6f1; padding: 1px 8px; border-radius: 6px; margin-right: 8px; }
.wp-ck.done { background: #f5faf8; border-color: #cdeadf; }
.wp-ck.done .wp-ckbox { background: #3A9E7E; border-color: #3A9E7E; color: #fff; }
.wp-ck.done .wp-cklbl { color: #94a3b8; text-decoration: line-through; }

.wp-narr { margin-bottom: 18px; }
.wp-rt { font-size: 13.5px; color: #475569; line-height: 1.6; }
.wp-rt :deep(ul) { padding-left: 18px; }

@media (max-width: 820px) { .wp-stats { gap: 8px; } .wp-stat { min-width: 90px; } }
</style>
