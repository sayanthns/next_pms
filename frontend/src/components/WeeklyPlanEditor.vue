<template>
  <div class="wpe">
    <div class="wpe-bar">
      <div class="wpe-meta">
        <label class="wpe-f"><span>Week start (Mon)</span><input type="date" v-model="form.week_start" /></label>
        <label class="wpe-f"><span>Headline note</span><input type="text" v-model="form.headline_note" placeholder="e.g. Jun 25 · Aqrar deadline" /></label>
        <label class="wpe-chk"><input type="checkbox" v-model="form.published" /> Published</label>
      </div>
      <div class="wpe-actions">
        <button class="wpe-btn" :disabled="busy" @click="prefill" title="Fill people + projects from live PMS data">Prefill from PMS</button>
        <select v-model="rollFrom" class="wpe-sel" :disabled="busy">
          <option :value="null">Roll forward from…</option>
          <option v-for="w in weeks" :key="w.name" :value="w.week_start">{{ w.title || w.week_start }}</option>
        </select>
        <button class="wpe-btn" :disabled="busy || !rollFrom" @click="rollForward">Roll forward</button>
        <span class="wpe-spacer"></span>
        <button class="wpe-btn ghost" :disabled="busy" @click="$emit('cancel')">Cancel</button>
        <button class="wpe-btn primary" :disabled="busy" @click="save">{{ busy ? 'Saving…' : 'Save' }}</button>
      </div>
    </div>
    <div v-if="msg" class="wpe-msg" :class="msgType">{{ msg }}</div>

    <label class="wpe-f wide"><span>Intro</span><textarea v-model="form.intro" rows="2"></textarea></label>

    <!-- Allocations -->
    <fieldset class="wpe-set"><legend>People (capacity → utilisation)</legend>
      <div class="wpe-rows">
        <div class="wpe-row a" v-for="(r, i) in form.allocations" :key="'a' + i">
          <select v-model="r.member" class="grow"><option value="">— person —</option><option v-for="u in users" :key="u.value" :value="u.value">{{ u.label }}</option></select>
          <input v-model="r.role" placeholder="role" />
          <input v-model.number="r.planned_hours" type="number" step="0.5" placeholder="planned" title="planned hours" />
          <input v-model.number="r.capacity_hours" type="number" step="1" placeholder="cap" title="capacity hours" />
          <input v-model="r.tasks" class="grow" placeholder="tasks — one per line" />
          <button class="wpe-x" @click="form.allocations.splice(i, 1)" aria-label="remove">✕</button>
        </div>
      </div>
      <button class="wpe-add" @click="form.allocations.push({ member: '', role: '', planned_hours: 0, capacity_hours: 40, tasks: '' })">+ person</button>
    </fieldset>

    <!-- Projects -->
    <fieldset class="wpe-set"><legend>Projects (RAG health)</legend>
      <div class="wpe-prows">
        <div class="wpe-prow" v-for="(r, i) in form.projects" :key="'p' + i">
          <div class="wpe-row">
            <select v-model="r.project" class="grow"><option value="">— project —</option><option v-for="p in projects" :key="p.value" :value="p.value">{{ p.label }}</option></select>
            <input v-model="r.focus" class="grow" placeholder="this week's focus" />
            <input v-model="r.effort" placeholder="effort ~8h" />
            <input v-model="r.status_label" placeholder="status" />
            <select v-model="r.status_color"><option v-for="c in COLORS" :key="c" :value="c">{{ c }}</option></select>
            <select v-model="r.health"><option value="">health</option><option>Green</option><option>Amber</option><option>Red</option></select>
            <button class="wpe-x" @click="form.projects.splice(i, 1)" aria-label="remove">✕</button>
          </div>
          <div class="wpe-team">
            <span class="wpe-teamlbl">Team:</span>
            <span v-for="(m, j) in r.team" :key="j" class="wpe-teamsel">
              <select v-model="r.team[j]"><option value="">—</option><option v-for="u in users" :key="u.value" :value="u.value">{{ u.label }}</option></select>
              <button class="wpe-xs" @click="r.team.splice(j, 1)" aria-label="remove member">✕</button>
            </span>
            <button class="wpe-add sm" @click="r.team.push('')">+ member</button>
          </div>
        </div>
      </div>
      <button class="wpe-add" @click="form.projects.push({ project: '', focus: '', team: [], effort: '', status_label: '', status_color: 'green', health: '' })">+ project</button>
    </fieldset>

    <!-- Priorities -->
    <fieldset class="wpe-set"><legend>Priorities (WSJF — value/time/risk ÷ size)</legend>
      <div class="wpe-rows">
        <div class="wpe-row pr" v-for="(r, i) in form.priorities" :key="'pr' + i">
          <input v-model="r.project" class="grow" placeholder="project / theme" />
          <input v-model="r.note" class="grow" placeholder="note" />
          <input v-model.number="r.user_value" type="number" placeholder="val" title="user/biz value" />
          <input v-model.number="r.time_criticality" type="number" placeholder="time" title="time criticality" />
          <input v-model.number="r.risk_reduction" type="number" placeholder="risk" title="risk reduction" />
          <input v-model.number="r.job_size" type="number" placeholder="size" title="job size" />
          <span class="wpe-wsjf" title="WSJF preview">{{ wsjf(r) }}</span>
          <label class="wpe-chk sm"><input type="checkbox" v-model="r.hot" /> hot</label>
          <button class="wpe-x" @click="form.priorities.splice(i, 1)" aria-label="remove">✕</button>
        </div>
      </div>
      <button class="wpe-add" @click="form.priorities.push({ project: '', note: '', user_value: 5, time_criticality: 5, risk_reduction: 3, job_size: 1, badge_label: '', badge_color: 'green', hot: 0 })">+ priority</button>
    </fieldset>

    <!-- Watch (RAID) -->
    <fieldset class="wpe-set"><legend>Watch list (RAID)</legend>
      <div class="wpe-rows">
        <div class="wpe-row w" v-for="(r, i) in form.watch_list" :key="'w' + i">
          <input v-model="r.item" class="grow" placeholder="watch item" />
          <select v-model="r.raid_type"><option>Risk</option><option>Assumption</option><option>Issue</option><option>Dependency</option></select>
          <select v-model="r.level"><option>High</option><option>Med</option><option>Low</option></select>
          <input v-model="r.mitigation" class="grow" placeholder="how we handle it" />
          <select v-model="r.owner"><option value="">— owner —</option><option v-for="u in users" :key="u.value" :value="u.value">{{ u.label }}</option></select>
          <button class="wpe-x" @click="form.watch_list.splice(i, 1)" aria-label="remove">✕</button>
        </div>
      </div>
      <button class="wpe-add" @click="form.watch_list.push({ item: '', raid_type: 'Risk', level: 'Med', mitigation: '', owner: '' })">+ watch</button>
    </fieldset>

    <!-- Checklist -->
    <fieldset class="wpe-set"><legend>Checklist</legend>
      <div class="wpe-rows">
        <div class="wpe-row c" v-for="(r, i) in form.checklist" :key="'c' + i">
          <input v-model="r.who" placeholder="who/when" />
          <input v-model="r.item" class="grow" placeholder="checklist item" />
          <button class="wpe-x" @click="form.checklist.splice(i, 1)" aria-label="remove">✕</button>
        </div>
      </div>
      <button class="wpe-add" @click="form.checklist.push({ who: '', item: '' })">+ item</button>
    </fieldset>

    <!-- Closures -->
    <fieldset class="wpe-set"><legend>Closures</legend>
      <div class="wpe-rows">
        <div class="wpe-row cl" v-for="(r, i) in form.closures" :key="'cl' + i">
          <input v-model="r.project" class="grow" placeholder="project" />
          <input v-model="r.work" class="grow" placeholder="this week" />
          <select v-model="r.owner"><option value="">— owner —</option><option v-for="u in users" :key="u.value" :value="u.value">{{ u.label }}</option></select>
          <button class="wpe-x" @click="form.closures.splice(i, 1)" aria-label="remove">✕</button>
        </div>
      </div>
      <button class="wpe-add" @click="form.closures.push({ project: '', work: 'Final sign-off + handover', owner: '', status_label: 'Closure' })">+ closure</button>
    </fieldset>

    <!-- Narrative -->
    <fieldset class="wpe-set"><legend>Narrative (HTML allowed)</legend>
      <label class="wpe-f wide"><span>How we're working</span><textarea v-model="form.working_notes" rows="3"></textarea></label>
      <label class="wpe-f wide"><span>Meetings &amp; closures</span><textarea v-model="form.meetings_note" rows="3"></textarea></label>
      <label class="wpe-f wide"><span>Week shape</span><textarea v-model="form.week_shape" rows="3"></textarea></label>
    </fieldset>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from '@/utils/frappe'

const props = defineProps({ initial: { type: Object, default: null }, weeks: { type: Array, default: () => [] } })
const emit = defineEmits(['saved', 'cancel'])

const COLORS = ['red', 'orange', 'green', 'blue', 'grey']
const busy = ref(false)
const msg = ref('')
const msgType = ref('')
const rollFrom = ref(null)
const users = ref([])
const projects = ref([])

function blank() {
  return {
    week_start: '', published: 1, intro: '', headline_note: '',
    allocations: [], projects: [], priorities: [], watch_list: [], checklist: [], closures: [],
    working_notes: '', week_shape: '', meetings_note: '',
  }
}
function hydrate(src) {
  const f = Object.assign(blank(), JSON.parse(JSON.stringify(src || {})))
  f.published = src && src.published != null ? !!src.published : true
  for (const t of ['allocations', 'projects', 'priorities', 'watch_list', 'checklist', 'closures']) {
    if (!Array.isArray(f[t])) f[t] = []
  }
  f.projects = f.projects.map(p => ({ ...p, team: (p.team_members || []).map(m => m.user).filter(Boolean) }))
  return f
}
const form = ref(hydrate(props.initial))

function wsjf(r) {
  const js = Number(r.job_size) || 1
  return Math.round((((+r.user_value || 0) + (+r.time_criticality || 0) + (+r.risk_reduction || 0)) / js) * 100) / 100
}

function buildPayload() {
  const f = JSON.parse(JSON.stringify(form.value))
  f.published = f.published ? 1 : 0
  f.projects = (f.projects || []).map(p => {
    const team_members = (p.team || []).filter(Boolean).map(u => ({ user: u }))
    const { team, ...rest } = p
    return { ...rest, team_members }
  })
  return f
}

async function save() {
  if (!form.value.week_start) { flash('Week start is required.', 'err'); return }
  busy.value = true; msg.value = ''
  try {
    await call('next_pms.api.weekly_plan.save_week', { payload: JSON.stringify(buildPayload()) })
    flash('Saved.', 'ok')
    emit('saved', form.value.week_start)
  } catch (e) { flash((e && e.message) || 'Save failed.', 'err') }
  finally { busy.value = false }
}

async function prefill() {
  if (!form.value.week_start) { flash('Set the week start first.', 'err'); return }
  busy.value = true; msg.value = ''
  try {
    const d = await call('next_pms.api.weekly_plan.prefill_week', { week_start: form.value.week_start })
    form.value.allocations = d.allocations || []
    form.value.projects = (d.projects || []).map(p => ({ ...p, team: (p.team_members || []).map(m => m.user) }))
    flash('Prefilled people + projects from PMS — edit the judgment bits.', 'ok')
  } catch (e) { flash((e && e.message) || 'Prefill failed.', 'err') }
  finally { busy.value = false }
}

async function rollForward() {
  if (!rollFrom.value || !form.value.week_start) { flash('Pick a source week and set the new week start.', 'err'); return }
  busy.value = true; msg.value = ''
  try {
    const d = await call('next_pms.api.weekly_plan.roll_forward', { from_week: rollFrom.value, to_week: form.value.week_start })
    form.value = hydrate(d)
    flash('Rolled forward — closed projects dropped. Review + save.', 'ok')
  } catch (e) { flash((e && e.message) || 'Roll-forward failed.', 'err') }
  finally { busy.value = false }
}

function flash(t, type) { msg.value = t; msgType.value = type }

onMounted(async () => {
  try {
    const o = await call('next_pms.api.weekly_plan.get_form_options')
    users.value = o.users || []
    projects.value = o.projects || []
  } catch (e) { /* options optional; fields still usable */ }
})
</script>

<style scoped>
.wpe { background: #fff; border: 1px solid #e3e9e6; border-radius: 12px; padding: 16px; margin-bottom: 18px; }
.wpe-bar { display: flex; justify-content: space-between; gap: 14px; flex-wrap: wrap; align-items: flex-end; }
.wpe-meta { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
.wpe-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.wpe-spacer { width: 8px; }
.wpe-f { display: flex; flex-direction: column; gap: 3px; font-size: 12px; color: #64748b; }
.wpe-f.wide { margin-top: 12px; }
.wpe-f input, .wpe-f textarea, .wpe-sel, .wpe-row input, .wpe-row select { border: 1px solid #d0d5dd; border-radius: 7px; padding: 6px 9px; font-size: 13px; color: #1a2330; background: #fff; }
.wpe-f input:focus-visible, .wpe-row input:focus-visible, .wpe-row select:focus-visible, .wpe-sel:focus-visible { outline: 2px solid #3A9E7E; outline-offset: 1px; }
.wpe-chk { font-size: 13px; display: flex; align-items: center; gap: 6px; color: #41514c; }
.wpe-chk.sm { font-size: 11px; }
.wpe-btn { padding: 7px 13px; border: 1px solid #d0d5dd; border-radius: 8px; background: #fff; cursor: pointer; font-size: 13px; font-weight: 600; }
.wpe-btn:hover:not(:disabled) { background: #f5f7fa; }
.wpe-btn:disabled { opacity: .5; cursor: default; }
.wpe-btn.primary { background: #3A9E7E; color: #fff; border-color: #2c7d63; }
.wpe-btn.ghost { color: #64748b; }
.wpe-msg { margin-top: 10px; padding: 8px 12px; border-radius: 8px; font-size: 13px; }
.wpe-msg.ok { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.wpe-msg.err { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.wpe-set { border: 1px solid #eef2f0; border-radius: 10px; padding: 12px 14px; margin-top: 14px; }
.wpe-set legend { font-size: 12px; font-weight: 800; color: #1A2E3A; padding: 0 6px; text-transform: uppercase; letter-spacing: .4px; }
.wpe-rows, .wpe-prows { display: flex; flex-direction: column; gap: 6px; }
.wpe-prow { border: 1px solid #f0f3f1; border-radius: 8px; padding: 8px; background: #fbfdfc; }
.wpe-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.wpe-row input, .wpe-row select { flex: 0 0 auto; min-width: 70px; }
.wpe-row .grow { flex: 1; min-width: 120px; }
.wpe-row.a input:nth-of-type(2), .wpe-row.a input:nth-of-type(3), .wpe-row.pr input[type=number] { flex: 0 0 64px; min-width: 52px; }
.wpe-team { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 6px; padding-left: 2px; }
.wpe-teamlbl { font-size: 11px; color: #94a3b8; font-weight: 600; }
.wpe-teamsel { display: inline-flex; align-items: center; gap: 2px; }
.wpe-teamsel select { border: 1px solid #d0d5dd; border-radius: 6px; padding: 4px 7px; font-size: 12px; }
.wpe-wsjf { font-size: 11px; font-weight: 800; color: #2c7d63; background: #eef6f3; border: 1px solid #cfe7dd; padding: 4px 8px; border-radius: 6px; white-space: nowrap; }
.wpe-x { flex: 0 0 auto; width: 26px; height: 26px; border: 1px solid #fbc4c4; background: #fef2f2; color: #b91c1c; border-radius: 6px; cursor: pointer; font-size: 12px; }
.wpe-xs { width: 18px; height: 18px; border: none; background: none; color: #b91c1c; cursor: pointer; font-size: 11px; }
.wpe-add { margin-top: 8px; padding: 5px 11px; border: 1px dashed #cfe7dd; background: #f5faf8; color: #2c7d63; border-radius: 7px; cursor: pointer; font-size: 12px; font-weight: 600; }
.wpe-add.sm { margin-top: 0; padding: 3px 8px; }
</style>
