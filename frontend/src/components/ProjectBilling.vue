<template>
  <div class="billing">
    <div v-if="errorMsg" class="billing-error">{{ errorMsg }}</div>

    <!-- Summary -->
    <div class="billing-cards">
      <div class="bcard"><span class="bval">{{ fmt(summary.total_budget) }}</span><span class="blbl">Budget</span></div>
      <div class="bcard"><span class="bval">{{ fmt(summary.labour_cost) }}</span><span class="blbl">Labour</span></div>
      <div class="bcard"><span class="bval">{{ fmt(summary.expenses) }}</span><span class="blbl">Expenses</span></div>
      <div class="bcard"><span class="bval">{{ fmt(summary.spent) }}</span><span class="blbl">Spent</span></div>
      <div class="bcard"><span class="bval" :class="{ over: summary.remaining < 0 }">{{ fmt(summary.remaining) }}</span><span class="blbl">Remaining</span></div>
    </div>
    <div class="billing-cards">
      <div class="bcard ok"><span class="bval">{{ fmt(summary.payments_received) }}</span><span class="blbl">Payments Received</span></div>
      <div class="bcard warn"><span class="bval" :class="{ over: summary.outstanding > 0 }">{{ fmt(summary.outstanding) }}</span><span class="blbl">Outstanding (Budget − Received)</span></div>
    </div>

    <!-- Expenses -->
    <div class="billing-section">
      <div class="bs-head">
        <h3>Expenses</h3>
        <span class="bs-sub">Reduce remaining budget. No accounting entry.</span>
      </div>
      <form v-if="canManage" class="brow" @submit.prevent="addExpense">
        <input v-model.number="exp.amount" type="number" min="0" step="0.01" placeholder="Amount" class="bin" />
        <input v-model="exp.expense_date" type="date" class="bin" />
        <select v-model="exp.category" class="bin">
          <option>Subcontract</option><option>Software</option><option>Travel</option><option>Onsite Charges</option><option>Server</option><option>Additional Works</option><option>AMC</option><option>Other</option>
        </select>
        <input v-model="exp.description" type="text" placeholder="Description" class="bin bin-grow" />
        <button class="bbtn" :disabled="busy">Add</button>
      </form>
      <table class="btable" v-if="expenses.length">
        <thead><tr><th>Date</th><th>Category</th><th>Description</th><th class="r">Amount</th><th v-if="canManage"></th></tr></thead>
        <tbody>
          <tr v-for="e in expenses" :key="e.name">
            <td>{{ fmtDate(e.expense_date) }}</td>
            <td>{{ e.category }}</td>
            <td>{{ e.description || '—' }}</td>
            <td class="r">{{ fmt(e.amount) }}</td>
            <td v-if="canManage" class="r"><button class="blink-del" @click="delExpense(e.name)">Delete</button></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="bempty">No expenses logged.</p>
    </div>

    <!-- Client Payments -->
    <div class="billing-section">
      <div class="bs-head">
        <h3>Client Payments</h3>
        <span class="bs-sub">Money received. A linked ERPNext Payment Entry is required.</span>
      </div>
      <form v-if="canManage" class="brow" @submit.prevent="addPayment">
        <input v-model.number="pay.amount" type="number" min="0" step="0.01" placeholder="Amount" class="bin" />
        <input v-model="pay.payment_date" type="date" class="bin" />
        <input v-model="pay.description" type="text" placeholder="Milestone / note" class="bin bin-grow" />
        <select v-model="pay.payment_entry" class="bin bin-select" required>
          <option value="" disabled>Select Payment Entry (required)</option>
          <option v-for="pe in paymentEntries" :key="pe.name" :value="pe.name">
            {{ pe.name }} — {{ fmt(pe.paid_amount) }}{{ pe.posting_date ? ' · ' + fmtDate(pe.posting_date) : '' }}
          </option>
        </select>
        <button class="bbtn" :disabled="busy || !pay.amount || !pay.payment_entry">Add</button>
      </form>
      <p v-if="canManage && !paymentEntries.length" class="bhint">No unlinked Payment Entries found for this client. Create a Receive-type Payment Entry for this customer in ERPNext Accounts first.</p>
      <table class="btable" v-if="payments.length">
        <thead><tr><th>Date</th><th>Description</th><th class="r">Amount</th><th>Status</th><th>Payment Entry</th><th v-if="canManage"></th></tr></thead>
        <tbody>
          <tr v-for="p in payments" :key="p.name">
            <td>{{ fmtDate(p.payment_date) }}</td>
            <td>{{ p.description || '—' }}</td>
            <td class="r">{{ fmt(p.amount) }}</td>
            <td><span class="pill" :class="p.status === 'Received' ? 'pill-ok' : 'pill-warn'">{{ p.status }}</span></td>
            <td>{{ p.payment_entry || '—' }}</td>
            <td v-if="canManage" class="r">
              <button class="blink-del" @click="delPayment(p.name)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="bempty">No payments recorded.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { call } from '@/utils/frappe'
import { useSettingsStore } from '@/store/settings'

const props = defineProps({
  projectId: { type: String, required: true },
  canManage: { type: Boolean, default: false },
})

const settingsStore = useSettingsStore()
const summary = ref({})
const expenses = ref([])
const payments = ref([])
const paymentEntries = ref([])
const errorMsg = ref('')
const busy = ref(false)
const today = new Date().toISOString().slice(0, 10)
const exp = reactive({ amount: null, expense_date: today, category: 'Other', description: '' })
const pay = reactive({ amount: null, payment_date: today, description: '', payment_entry: '' })

function fmt(v) { return settingsStore.formatCurrency(v || 0) }
function fmtDate(d) { return d ? new Date(d).toLocaleDateString() : '—' }

async function loadAll() {
  try {
    const [s, e, p, pe] = await Promise.all([
      call('next_pms.api.billing.get_project_billing_summary', { project: props.projectId }),
      call('next_pms.api.billing.list_project_expenses', { project: props.projectId }),
      call('next_pms.api.billing.list_project_payments', { project: props.projectId }),
      props.canManage ? call('next_pms.api.billing.list_payment_entries', { project: props.projectId }) : Promise.resolve([]),
    ])
    summary.value = s || {}
    expenses.value = e || []
    payments.value = p || []
    paymentEntries.value = pe || []
  } catch (err) {
    errorMsg.value = (err && err.message) || 'Failed to load billing.'
  }
}

async function addExpense() {
  if (!exp.amount || exp.amount <= 0) { errorMsg.value = 'Enter a valid expense amount.'; return }
  busy.value = true; errorMsg.value = ''
  try {
    await call('next_pms.api.billing.add_project_expense', {
      project: props.projectId, amount: exp.amount, expense_date: exp.expense_date,
      category: exp.category, description: exp.description,
    })
    exp.amount = null; exp.description = ''
    await loadAll()
  } catch (err) { errorMsg.value = (err && err.message) || 'Failed to add expense.' }
  finally { busy.value = false }
}

async function delExpense(name) {
  busy.value = true
  try { await call('next_pms.api.billing.delete_project_expense', { name }); await loadAll() }
  catch (err) { errorMsg.value = (err && err.message) || 'Failed to delete.' }
  finally { busy.value = false }
}

async function addPayment() {
  if (!pay.amount || pay.amount <= 0) { errorMsg.value = 'Enter a valid payment amount.'; return }
  if (!pay.payment_entry) { errorMsg.value = 'A Payment Entry is required to record a client payment.'; return }
  busy.value = true; errorMsg.value = ''
  try {
    await call('next_pms.api.billing.add_project_payment', {
      project: props.projectId, amount: pay.amount, payment_date: pay.payment_date,
      description: pay.description, payment_entry: pay.payment_entry || null,
    })
    pay.amount = null; pay.description = ''; pay.payment_entry = ''
    await loadAll()
  } catch (err) { errorMsg.value = (err && err.message) || 'Failed to add payment.' }
  finally { busy.value = false }
}

async function delPayment(name) {
  busy.value = true
  try { await call('next_pms.api.billing.delete_project_payment', { name }); await loadAll() }
  catch (err) { errorMsg.value = (err && err.message) || 'Failed to delete.' }
  finally { busy.value = false }
}

onMounted(loadAll)
</script>

<style scoped>
.billing { display: flex; flex-direction: column; gap: 20px; }
.billing-error { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 12px; font-size: 13px; }
.billing-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
.bcard { background: var(--bg-surface, #fff); border: 1px solid var(--border-default, #e5e7eb); border-radius: 10px; padding: 14px; text-align: center; }
.bcard.ok { background: #f0fdf4; } .bcard.warn { background: #fffbeb; }
.bval { display: block; font-size: 18px; font-weight: 800; color: var(--text-primary, #111827); }
.bval.over { color: #dc2626; }
.blbl { display: block; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af; margin-top: 4px; }
.billing-section { border: 1px solid var(--border-default, #e5e7eb); border-radius: 10px; padding: 16px; }
.bs-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; }
.bs-head h3 { margin: 0; font-size: 15px; font-weight: 700; }
.bs-sub { font-size: 11px; color: #9ca3af; }
.brow { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; align-items: stretch; }
.bin { box-sizing: border-box; height: 38px; padding: 8px 10px; border: 1px solid var(--border-default, #e5e7eb); border-radius: 8px; font-size: 13px; background: #fff; color: var(--text-primary, #111827); }
.bin-grow { flex: 1; min-width: 140px; }
select.bin { cursor: pointer; max-width: 100%; }
.bin-select { flex: 1 1 240px; min-width: 200px; }
.brow .bbtn { height: 38px; }
.bbtn { background: #2563eb; color: #fff; border: none; border-radius: 8px; padding: 8px 16px; font-weight: 600; font-size: 13px; cursor: pointer; }
.bbtn:disabled { opacity: 0.6; cursor: not-allowed; }
.bbtn-ghost { background: #f3f4f6; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; }
.btable { width: 100%; border-collapse: collapse; font-size: 13px; }
.btable th, .btable td { padding: 8px 10px; border-bottom: 1px solid #f3f4f6; text-align: left; }
.btable th.r, .btable td.r { text-align: right; }
.bempty { color: #9ca3af; font-size: 13px; margin: 4px 0 0; }
.bhint { color: #b45309; font-size: 12px; margin: 6px 0 0; }
.pill { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; }
.pill-ok { background: #d1fae5; color: #065f46; } .pill-warn { background: #fef3c7; color: #92400e; }
.blink { background: none; border: none; color: #2563eb; font-size: 12px; cursor: pointer; margin-right: 8px; }
.blink-del { background: none; border: none; color: #dc2626; font-size: 12px; cursor: pointer; }
.bmodal { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.bmodal-card { background: #fff; border-radius: 12px; padding: 22px; width: 420px; max-width: 92vw; display: flex; flex-direction: column; gap: 10px; }
.bmodal-card h4 { margin: 0; font-size: 16px; }
.bmodal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px; }
</style>
