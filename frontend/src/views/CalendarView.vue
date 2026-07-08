<template>
  <div class="cal">
    <header class="cal-head">
      <div>
        <h1 class="cal-title">Calendar</h1>
        <p class="cal-sub">Scheduled meetings &amp; your team's schedule</p>
      </div>
      <div class="cal-controls">
        <div class="cal-scope" role="tablist" aria-label="Scope">
          <button role="tab" :aria-selected="scope === 'mine'" :class="{ on: scope === 'mine' }" @click="setScope('mine')">My schedule</button>
          <button role="tab" :aria-selected="scope === 'all'" :class="{ on: scope === 'all' }" @click="setScope('all')">All meetings</button>
        </div>
        <button class="cal-btn primary" @click="openCreate" title="Schedule a meeting">+ New meeting</button>
      </div>
    </header>

    <div class="cal-nav">
      <button class="cal-navbtn" @click="shift(-28)" aria-label="Earlier">‹ Earlier</button>
      <button class="cal-navbtn" @click="goToday">Today</button>
      <button class="cal-navbtn" @click="shift(28)" aria-label="Later">Later ›</button>
      <span class="cal-range">{{ rangeLabel }}</span>
    </div>

    <div v-if="errorMsg" class="cal-error" role="alert">{{ errorMsg }} <button class="cal-link" @click="load">Retry</button></div>
    <div v-if="loading" class="cal-loading"><span class="cal-spin" aria-hidden="true"></span> Loading…</div>
    <div v-else-if="!groups.length" class="cal-empty">
      No meetings in this window.
      <button class="cal-link" @click="openCreate">Schedule one →</button>
    </div>

    <section v-for="g in groups" :key="g.date" class="cal-day">
      <div class="cal-dayhead">
        <span class="cal-dow">{{ g.dow }}</span>
        <span class="cal-date" :class="{ today: g.isToday }">{{ g.label }}</span>
      </div>
      <article v-for="m in g.items" :key="m.name" class="cal-card" :class="{ held: m.status === 'Held', cancelled: m.status === 'Cancelled' }">
        <div class="cal-time">
          <template v-if="m.start_time"><b>{{ zoneTimes(m.start_time).ist }}</b><span class="cal-tz">IST</span><span v-if="m.duration_mins">{{ m.duration_mins }}m</span></template>
          <template v-else><b>—</b></template>
        </div>
        <div class="cal-body">
          <div class="cal-crow">
            <h3 class="cal-subj">{{ m.subject }}</h3>
            <span class="cal-badge" :class="'st-' + (m.status || 'Planned').toLowerCase()">{{ m.status }}</span>
          </div>
          <div class="cal-zones" v-if="m.start_time">
            <span>KSA {{ zoneTimes(m.start_time).ksa }}</span>
            <span>UAE {{ zoneTimes(m.start_time).uae }}</span>
            <span>IST {{ zoneTimes(m.start_time).ist }}</span>
          </div>
          <div class="cal-meta">
            <span v-if="m.project_name" class="cal-chip proj">{{ m.project_name }}</span>
            <span class="cal-chip type">{{ m.meeting_type }}</span>
            <a v-if="m.mom_pdf" :href="m.mom_pdf" target="_blank" rel="noopener" class="cal-mom ok link" title="Open the MoM PDF">MoM ↗</a>
            <span v-else-if="m.status === 'Held'" class="cal-mom ok" title="Marked held">Held</span>
            <span v-else-if="isPast(m) && m.status === 'Planned'" class="cal-mom due" title="This meeting is past and not marked Held">Needs update</span>
          </div>
          <div class="cal-people" v-if="m.participants && m.participants.length">
            <span v-for="p in m.participants" :key="p.user" class="cal-av" :style="{ background: avatarColor(p.full_name) }" :title="p.full_name + (p.response && p.response !== 'Invited' ? ' · ' + p.response : '')">{{ initials(p.full_name) }}</span>
            <span v-if="m.coordinator" class="cal-coord" title="Coordinator">·  {{ coordName(m) }}</span>
          </div>
        </div>
        <div class="cal-actions" v-if="m.can_edit">
          <button class="cal-mini" @click="openEdit(m)">Edit</button>
          <button v-if="m.status !== 'Held' && m.status !== 'Cancelled'" class="cal-mini go" @click="openComplete(m)">Mark held</button>
        </div>
      </article>
    </section>

    <!-- Meeting modal -->
    <div v-if="modal.open" class="cal-modal-backdrop" @click.self="closeModal">
      <div class="cal-modal" role="dialog" aria-modal="true">
        <div class="cal-modal-head">
          <h2>{{ modal.name ? (modal.markHeld ? 'Mark meeting held' : 'Edit meeting') : 'New meeting' }}</h2>
          <button class="cal-x" @click="closeModal" aria-label="Close">✕</button>
        </div>
        <div class="cal-modal-body">
          <!-- Mark-held mode: skip the scheduling fields, just capture the MoM -->
          <div v-if="modal.markHeld" class="cal-heldctx">
            <div class="cal-heldsubj">{{ form.subject }}</div>
            <div class="cal-heldmeta">Attach the minutes (PDF) to mark this meeting as held.</div>
          </div>

          <template v-if="!modal.markHeld">
          <div class="cal-f">
            <label>Subject *</label>
            <input v-model="form.subject" type="text" placeholder="e.g. Weekly sync — Steel Force" />
          </div>
          <div class="cal-frow">
            <div class="cal-f">
              <label>Project <span v-if="projectRequired" class="cal-req">*</span></label>
              <select v-model="form.project">
                <option value="">— none —</option>
                <option v-for="p in options.projects" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option>
              </select>
            </div>
            <div class="cal-f">
              <label>Type</label>
              <select v-model="form.meeting_type">
                <option>Client Weekly</option><option>Internal</option><option>Ad-hoc</option>
              </select>
            </div>
          </div>
          <div class="cal-frow">
            <div class="cal-f">
              <label>Start <span class="cal-optional">(IST)</span></label>
              <input v-model="form.start_local" type="datetime-local" />
              <div class="cal-zonehint" v-if="startZones">KSA {{ startZones.ksa }} · UAE {{ startZones.uae }}</div>
            </div>
            <div class="cal-f">
              <label>Duration (mins)</label>
              <input v-model.number="form.duration_mins" type="number" min="0" step="15" />
            </div>
          </div>
          <div class="cal-frow">
            <div class="cal-f">
              <label>Coordinator</label>
              <select v-model="form.coordinator">
                <option value="">— none —</option>
                <option v-for="u in options.users" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
              </select>
            </div>
            <div class="cal-f">
              <label>Status</label>
              <select v-model="form.status">
                <option>Planned</option><option>Held</option><option>Missed</option><option>Rescheduled</option><option>Cancelled</option>
              </select>
            </div>
          </div>
          <div class="cal-f">
            <label>Participants</label>
            <input v-model="userFilter" type="text" class="cal-search" placeholder="Filter people…" />
            <div class="cal-picker">
              <label v-for="u in filteredUsers" :key="u.name" class="cal-pick">
                <input type="checkbox" :value="u.name" v-model="form.participants" />
                <span>{{ u.full_name || u.name }}</span>
              </label>
            </div>
            <div class="cal-selcount" v-if="form.participants.length">{{ form.participants.length }} selected</div>
          </div>
          </template>

          <div class="cal-f">
            <label>MoM (PDF) <span v-if="momRequired" class="cal-req">— required to mark Held</span></label>
            <div v-if="form.mom_pdf" class="cal-file">
              <a :href="form.mom_pdf" target="_blank" rel="noopener">{{ momFileName }}</a>
              <button type="button" class="cal-filex" @click="form.mom_pdf = ''" aria-label="Remove">✕</button>
            </div>
            <div v-else>
              <input ref="pdfInput" type="file" accept="application/pdf,.pdf" @change="onPdfPick" :disabled="uploading" />
              <span v-if="uploading" class="cal-uploading">Uploading…</span>
            </div>
          </div>
          <div class="cal-f" v-if="!modal.markHeld">
            <label>Notes <span class="cal-optional">(optional)</span></label>
            <RichTextEditor v-model="form.minutes" />
          </div>
          <div class="cal-f" v-if="!modal.markHeld">
            <label>Next actions</label>
            <textarea v-model="form.next_actions" rows="2" placeholder="One per line"></textarea>
          </div>
          <div v-if="modalError" class="cal-error sm">{{ modalError }}</div>
        </div>
        <div class="cal-modal-foot">
          <button v-if="modal.name && form.can_delete" class="cal-btn danger" @click="removeMeeting" :disabled="saving">Delete</button>
          <span class="cal-spacer"></span>
          <button class="cal-btn" @click="closeModal" :disabled="saving">Cancel</button>
          <button class="cal-btn primary" @click="save" :disabled="saving">{{ saving ? 'Saving…' : (modal.markHeld ? 'Save & mark Held' : 'Save') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { call } from '@/utils/frappe'
import RichTextEditor from '@/components/RichTextEditor.vue'

const scope = ref('mine')
const meetings = ref([])
const loading = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const modalError = ref('')
const options = reactive({ users: [], projects: [] })
const userFilter = ref('')
const windowStart = ref(mondayOf(new Date()))
const uploading = ref(false)
const pdfInput = ref(null)

const modal = reactive({ open: false, name: null, markHeld: false })
const form = reactive(blankForm())

function blankForm() {
  return {
    subject: '', project: '', meeting_type: 'Client Weekly', start_local: '',
    duration_mins: 30, coordinator: '', status: 'Planned',
    participants: [], mom_pdf: '', minutes: '', next_actions: '', can_delete: false,
  }
}

// ── date helpers ──
function mondayOf(d) { const x = new Date(d); const wd = (x.getDay() + 6) % 7; x.setDate(x.getDate() - wd); x.setHours(0, 0, 0, 0); return x }
function ymd(d) { const x = new Date(d); return x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0') + '-' + String(x.getDate()).padStart(2, '0') }
function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x }
const windowEnd = computed(() => addDays(windowStart.value, 27))
const rangeLabel = computed(() => fmt(windowStart.value) + ' – ' + fmt(windowEnd.value))
function fmt(d) { return new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) }
function isPast(m) { if (!m.start_time && !m.meeting_date) return false; const d = new Date(String(m.start_time || m.meeting_date).replace(' ', 'T')); return d < new Date() }

// Stored start_time is the IST wall-clock (system tz = Asia/Kolkata). KSA = IST-2:30,
// UAE = IST-1:30 (all three observe no DST, so fixed offsets are exact). Math is done in
// UTC to stay independent of the viewer's browser timezone.
function zoneTimes(dt) {
  if (!dt) return { ist: '', ksa: '', uae: '' }
  const s = String(dt).replace('T', ' ')
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})[ ]+(\d{2}):(\d{2})/)
  if (!m) return { ist: '', ksa: '', uae: '' }
  const base = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5])
  const hhmm = (ms) => { const x = new Date(ms); return String(x.getUTCHours()).padStart(2, '0') + ':' + String(x.getUTCMinutes()).padStart(2, '0') }
  return { ist: hhmm(base), ksa: hhmm(base - 150 * 60000), uae: hhmm(base - 90 * 60000) }
}
const startZones = computed(() => form.start_local ? zoneTimes(form.start_local) : null)

function initials(name) {
  if (!name) return '?'
  const base = String(name).replace(/@.*/, '')
  const parts = base.split(/[\s._]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return base.slice(0, 2).toUpperCase()
}
function avatarColor(name) {
  const colors = ['#1A2E3A', '#2c7d63', '#3A9E7E', '#0891b2', '#E8631A', '#7c3aed', '#1d4ed8', '#16a34a', '#9a3412']
  let h = 0
  for (const c of String(name || '?')) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return colors[h % colors.length]
}
function coordName(m) {
  const u = options.users.find(x => x.name === m.coordinator)
  return u ? (u.full_name || u.name) : m.coordinator
}

const filteredUsers = computed(() => {
  const q = userFilter.value.trim().toLowerCase()
  if (!q) return options.users
  return options.users.filter(u => (u.full_name || u.name).toLowerCase().includes(q))
})
const momRequired = computed(() => form.status === 'Held')
const projectRequired = computed(() => form.meeting_type === 'Client Weekly')
const momFileName = computed(() => (form.mom_pdf || '').split('/').pop() || 'MoM.pdf')

function csrfToken() {
  return document.cookie.split('; ').find(c => c.startsWith('csrf_token='))?.split('=')[1]
    || (window.frappe && window.frappe.csrf_token) || ''
}
async function onPdfPick(e) {
  const file = e.target.files && e.target.files[0]
  if (!file) return
  if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
    modalError.value = 'The MoM must be a PDF file.'
    if (pdfInput.value) pdfInput.value.value = ''
    return
  }
  uploading.value = true; modalError.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('is_private', '1')
    fd.append('folder', 'Home/Attachments')
    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: csrfToken() ? { 'X-Frappe-CSRF-Token': csrfToken() } : {},
      credentials: 'include',
      body: fd,
    })
    const data = await res.json()
    const url = data && data.message && data.message.file_url
    if (!url) throw new Error('Upload failed')
    form.mom_pdf = url
  } catch (err) {
    modalError.value = 'Failed to upload the PDF. Try again.'
  } finally {
    uploading.value = false
    if (pdfInput.value) pdfInput.value.value = ''
  }
}

// ── grouping ──
const groups = computed(() => {
  const by = {}
  for (const m of meetings.value) {
    const key = m.meeting_date || (m.start_time ? m.start_time.slice(0, 10) : 'undated')
    ;(by[key] = by[key] || []).push(m)
  }
  const todayY = ymd(new Date())
  return Object.keys(by).sort().map(k => {
    const d = new Date(k + 'T00:00:00')
    return {
      date: k,
      dow: isNaN(d) ? '' : d.toLocaleDateString(undefined, { weekday: 'short' }),
      label: isNaN(d) ? k : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }),
      isToday: k === todayY,
      items: by[k].sort((a, b) => String(a.start_time || '').localeCompare(String(b.start_time || ''))),
    }
  })
})

// ── data ──
async function load() {
  loading.value = true; errorMsg.value = ''
  try {
    meetings.value = await call('next_pms.api.calendar.list_meetings',
      { start: ymd(windowStart.value), end: ymd(windowEnd.value), scope: scope.value }) || []
  } catch (e) {
    meetings.value = []
    errorMsg.value = (e && e.message) || 'Failed to load meetings.'
  } finally { loading.value = false }
}
async function loadOptions() {
  try {
    const o = await call('next_pms.api.calendar.calendar_options')
    options.users = o.users || []; options.projects = o.projects || []
  } catch (e) { /* non-fatal */ }
}
function setScope(s) { if (scope.value !== s) { scope.value = s; load() } }
function shift(days) { windowStart.value = addDays(windowStart.value, days); load() }
function goToday() { windowStart.value = mondayOf(new Date()); load() }

// ── modal ──
function openCreate() {
  Object.assign(form, blankForm())
  // coordinator left blank → backend defaults it to the current user on create
  modal.name = null; modal.markHeld = false; modalError.value = ''; userFilter.value = ''
  modal.open = true
}
async function openEdit(m, markHeld = false) {
  modalError.value = ''; userFilter.value = ''; saving.value = true
  try {
    const d = await call('next_pms.api.calendar.get_meeting', { name: m.name })
    Object.assign(form, blankForm(), {
      subject: d.subject || '', project: d.project || '', meeting_type: d.meeting_type || 'Client Weekly',
      start_local: d.start_time ? String(d.start_time).replace(' ', 'T').slice(0, 16) : '',
      duration_mins: d.duration_mins || 30, coordinator: d.coordinator || '',
      status: markHeld ? 'Held' : (d.status || 'Planned'),
      participants: (d.participants || []).map(p => p.user),
      mom_pdf: d.mom_pdf || '', minutes: d.minutes || '', next_actions: d.next_actions || '',
      can_delete: !!d.can_edit,
    })
    modal.name = m.name; modal.markHeld = markHeld; modal.open = true
  } catch (e) {
    errorMsg.value = (e && e.message) || 'Failed to open meeting.'
  } finally { saving.value = false }
}
function openComplete(m) { openEdit(m, true) }
function closeModal() { modal.open = false }

function toServerDt(local) { return local ? local.replace('T', ' ') + ':00' : null }

async function save() {
  modalError.value = ''
  if (!form.subject.trim()) { modalError.value = 'Subject is required.'; return }
  if (form.meeting_type === 'Client Weekly' && !form.project) {
    modalError.value = 'A Client Weekly meeting must have a Project.'; return
  }
  if (form.status === 'Held' && !form.mom_pdf) {
    modalError.value = 'Attach the MoM (PDF) before marking a meeting as Held.'; return
  }
  saving.value = true
  try {
    const payload = {
      name: modal.name || undefined,
      subject: form.subject.trim(), project: form.project || null,
      start_time: toServerDt(form.start_local), meeting_type: form.meeting_type,
      duration_mins: form.duration_mins, coordinator: form.coordinator || null,
      status: form.status, mom_pdf: form.mom_pdf || null,
      minutes: form.minutes, next_actions: form.next_actions,
      participants: form.participants.map(u => ({ user: u })),
    }
    await call('next_pms.api.calendar.save_meeting', { payload: JSON.stringify(payload) })
    modal.open = false
    await load()
  } catch (e) {
    modalError.value = (e && e.message) || 'Failed to save.'
  } finally { saving.value = false }
}
async function removeMeeting() {
  if (!modal.name) return
  if (!window.confirm('Delete this meeting?')) return
  saving.value = true
  try {
    await call('next_pms.api.calendar.delete_meeting', { name: modal.name })
    modal.open = false
    await load()
  } catch (e) {
    modalError.value = (e && e.message) || 'Failed to delete.'
  } finally { saving.value = false }
}

onMounted(async () => { await Promise.all([loadOptions(), load()]) })
</script>

<style scoped>
.cal { padding: 4px 0 60px; color: #1a2330; }
.cal-head { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 14px; margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px solid #e3e9e6; }
.cal-title { font-size: 22px; font-weight: 800; margin: 0; letter-spacing: -0.3px; color: #1A2E3A; }
.cal-sub { margin: 4px 0 0; font-size: 13.5px; color: #64748b; }
.cal-controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.cal-scope { display: inline-flex; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 9px; padding: 2px; }
.cal-scope button { border: none; background: none; padding: 6px 12px; font-size: 13px; font-weight: 600; color: #64748b; border-radius: 7px; cursor: pointer; }
.cal-scope button.on { background: #fff; color: #1A2E3A; box-shadow: 0 1px 2px rgba(0,0,0,.06); }
.cal-btn { padding: 8px 13px; border: 1px solid #d0d5dd; border-radius: 8px; background: #fff; cursor: pointer; font-size: 13px; font-weight: 600; color: #1A2E3A; }
.cal-btn:hover { background: #f5f7fa; }
.cal-btn.primary { background: #3A9E7E; color: #fff; border-color: #2c7d63; }
.cal-btn.danger { background: #fff; color: #b42318; border-color: #fda29b; }
.cal-btn:disabled { opacity: .6; cursor: default; }

.cal-nav { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; }
.cal-navbtn { padding: 6px 12px; border: 1px solid #d0d5dd; border-radius: 8px; background: #fff; cursor: pointer; font-size: 13px; font-weight: 600; color: #41514c; }
.cal-navbtn:hover { background: #f5f7fa; }
.cal-range { margin-left: auto; font-size: 13px; color: #64748b; font-weight: 600; }

.cal-error { background: #fef2f2; border: 1px solid #fda29b; color: #912018; padding: 10px 14px; border-radius: 10px; margin-bottom: 14px; }
.cal-error.sm { padding: 8px 12px; font-size: 13px; margin: 4px 0 0; }
.cal-link { background: none; border: none; color: #2c7d63; font-weight: 700; cursor: pointer; text-decoration: underline; }
.cal-loading, .cal-empty { padding: 48px 0; text-align: center; color: #64748b; }
.cal-spin { display: inline-block; width: 14px; height: 14px; border: 2px solid #cbd5d0; border-top-color: #3A9E7E; border-radius: 50%; animation: calspin .7s linear infinite; vertical-align: middle; }
@keyframes calspin { to { transform: rotate(360deg); } }

.cal-day { margin-bottom: 22px; }
.cal-dayhead { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; }
.cal-dow { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .5px; color: #94a3b8; }
.cal-date { font-size: 14px; font-weight: 800; color: #1A2E3A; }
.cal-date.today { color: #2c7d63; }

.cal-card { display: flex; gap: 14px; background: #fff; border: 1px solid #e3e9e6; border-radius: 12px; padding: 12px 14px; margin-bottom: 8px; align-items: flex-start; }
.cal-card.held { border-left: 3px solid #3A9E7E; }
.cal-card.cancelled { opacity: .6; }
.cal-time { min-width: 58px; text-align: center; padding-top: 2px; }
.cal-time b { display: block; font-size: 14px; color: #1A2E3A; font-weight: 800; }
.cal-time span { font-size: 11px; color: #94a3b8; display: block; }
.cal-time .cal-tz { font-size: 9px; font-weight: 700; letter-spacing: .5px; color: #b8c0cc; }
.cal-zones { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 5px; font-size: 11.5px; color: #64748b; font-weight: 600; }
.cal-zones span:first-child { color: #2c7d63; }
.cal-zonehint { font-size: 11.5px; color: #2c7d63; font-weight: 600; margin-top: 4px; }
.cal-body { flex: 1; min-width: 0; }
.cal-crow { display: flex; align-items: center; gap: 10px; }
.cal-subj { font-size: 15px; font-weight: 700; color: #1A2E3A; margin: 0; }
.cal-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; align-items: center; }
.cal-chip { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 7px; }
.cal-chip.proj { background: #eef6f3; color: #2c7d63; border: 1px solid #cfe7dd; }
.cal-chip.type { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
.cal-mom { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 7px; }
.cal-mom.ok { background: #f0fdf4; color: #15803d; }
.cal-mom.link { text-decoration: none; cursor: pointer; }
.cal-mom.link:hover { background: #dcfce7; text-decoration: underline; }
.cal-mom.due { background: #fff7ed; color: #9a3412; }
.cal-people { display: flex; align-items: center; gap: 4px; margin-top: 9px; flex-wrap: wrap; }
.cal-av { width: 24px; height: 24px; border-radius: 7px; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 800; color: #fff; }
.cal-coord { font-size: 11.5px; color: #94a3b8; margin-left: 4px; }
.cal-badge { font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 20px; margin-left: auto; white-space: nowrap; }
.st-planned { background: #eff6ff; color: #1d4ed8; } .st-held { background: #f0fdf4; color: #15803d; }
.st-missed { background: #fef2f2; color: #b91c1c; } .st-rescheduled { background: #fff7ed; color: #9a3412; }
.st-cancelled { background: #f1f5f9; color: #64748b; }
.cal-actions { display: flex; flex-direction: column; gap: 6px; }
.cal-mini { padding: 4px 10px; font-size: 12px; font-weight: 600; border: 1px solid #d0d5dd; border-radius: 7px; background: #fff; cursor: pointer; color: #41514c; white-space: nowrap; }
.cal-mini:hover { background: #f5f7fa; }
.cal-mini.go { border-color: #2c7d63; color: #2c7d63; }

.cal-modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,.45); display: flex; align-items: flex-start; justify-content: center; padding: 40px 16px; z-index: 1000; overflow-y: auto; }
.cal-modal { background: #fff; border-radius: 14px; width: 100%; max-width: 560px; box-shadow: 0 20px 50px rgba(0,0,0,.25); }
.cal-modal-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e3e9e6; }
.cal-modal-head h2 { font-size: 17px; font-weight: 800; color: #1A2E3A; margin: 0; }
.cal-x { border: none; background: none; font-size: 18px; color: #94a3b8; cursor: pointer; }
.cal-modal-body { padding: 16px 20px; max-height: 62vh; overflow-y: auto; }
.cal-f { margin-bottom: 13px; }
.cal-f > label { display: block; font-size: 12px; font-weight: 700; color: #41514c; margin-bottom: 5px; }
.cal-req { color: #9a3412; font-weight: 600; }
.cal-optional { color: #94a3b8; font-weight: 500; }
.cal-heldctx { background: #f4f8f6; border: 1px solid #cfe7dd; border-radius: 10px; padding: 12px 14px; margin-bottom: 16px; }
.cal-heldsubj { font-size: 15px; font-weight: 700; color: #1A2E3A; }
.cal-heldmeta { font-size: 12.5px; color: #64748b; margin-top: 3px; }
.cal-file { display: flex; align-items: center; gap: 8px; background: #f4f8f6; border: 1px solid #cfe7dd; border-radius: 8px; padding: 8px 11px; font-size: 13px; }
.cal-file a { color: #2c7d63; font-weight: 600; text-decoration: none; word-break: break-all; }
.cal-file a:hover { text-decoration: underline; }
.cal-filex { margin-left: auto; border: none; background: none; color: #94a3b8; cursor: pointer; font-size: 14px; flex-shrink: 0; }
.cal-uploading { font-size: 12px; color: #64748b; margin-left: 8px; }
.cal-f input[type=text], .cal-f input[type=number], .cal-f input[type=datetime-local], .cal-f select, .cal-f textarea { width: 100%; padding: 8px 11px; border: 1px solid #d0d5dd; border-radius: 8px; font-size: 13.5px; color: inherit; background: #fff; box-sizing: border-box; }
.cal-frow { display: flex; gap: 12px; } .cal-frow .cal-f { flex: 1; }
.cal-search { margin-bottom: 6px; }
.cal-picker { max-height: 140px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 8px; }
.cal-pick { display: flex; align-items: center; gap: 8px; padding: 4px 2px; font-size: 13px; color: #374151; cursor: pointer; }
.cal-pick input { width: auto; }
.cal-selcount { font-size: 11.5px; color: #64748b; margin-top: 4px; }
.cal-modal-foot { display: flex; align-items: center; gap: 8px; padding: 14px 20px; border-top: 1px solid #e3e9e6; }
.cal-spacer { flex: 1; }
@media (max-width: 620px) { .cal-frow { flex-direction: column; gap: 0; } }
</style>
