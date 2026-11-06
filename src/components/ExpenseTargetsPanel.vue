<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import subadviseApi from '@/api/subadviseApi'
import { COMMON_CURRENCIES, SUPPORTED_CURRENCIES } from '@/utils/currencies'

const STORAGE_KEY = 'subadvise.expenseTargets'

function formatLocalDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getCurrentMonth() {
  const date = new Date()
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function getMonthEnd(dateString) {
  const [year, month] = dateString.split('-').map(Number)
  return formatLocalDate(new Date(year, month, 0))
}

function addLocalDays(dateString, days) {
  const [year, month, day] = dateString.split('-').map(Number)
  return formatLocalDate(new Date(year, month - 1, day + days))
}

function loadSavedTargets() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return { targets: [], error: null }
    const targets = JSON.parse(saved)
    if (!Array.isArray(targets)) {
      throw new Error('Saved target data is not a list.')
    }
    if (targets.some((target) => !target.targetId || !target.currency || !target.endDate)) {
      throw new Error('One or more saved targets are missing required details.')
    }
    return { targets, error: null }
  } catch (error) {
    return { targets: [], error: `Could not load browser-saved targets: ${error.message}` }
  }
}

const savedState = loadSavedTargets()
const targets = ref(savedState.targets)
const storageError = ref(savedState.error)
const isCreatingTarget = ref(false)
const isRecordingExpense = ref(false)
const isReportLoading = ref(false)
const targetError = ref('')
const expenseError = ref('')
const reportError = ref('')
const report = ref(null)
const targetCreatedMessage = ref('')
const isRenewalDraft = ref(false)
const targetFormElement = ref(null)
const targetEndDateInput = ref(null)
const expenseCreatedMessage = ref('')
const reportMonth = ref(getCurrentMonth())
const selectedTargetId = ref(targets.value[0]?.targetId || '')
let reportRequestId = 0

const targetForm = reactive({
  name: '',
  targetExpense: '',
  currency: 'USD',
  startDate: formatLocalDate(new Date()),
  endDate: getMonthEnd(getCurrentMonth() + '-01')
})

const expenseForm = reactive({
  actualExpense: ''
})

const selectedTarget = computed(() =>
  targets.value.find((target) => target.targetId === selectedTargetId.value) || null
)
const expenseCurrency = computed(() => selectedTarget.value?.currency || '')
const targetsForMonth = computed(() =>
  targets.value.filter((target) => target.endDate?.slice(0, 7) === reportMonth.value)
)
const reportTotals = computed(() => Object.entries(report.value?.totalsByCurrency || {}))

function targetSpend(targetId) {
  return (report.value?.expenses || [])
    .filter((expense) => expense.targetId === targetId)
    .reduce((total, expense) => total + Number(expense.actualExpense || 0), 0)
}

function formatCurrency(amount, currency) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 2
    }).format(Number(amount))
  } catch {
    return `${Number(amount).toFixed(2)} ${currency || ''}`
  }
}

function formatDate(value) {
  if (!value) return '—'
  const [year, month, day] = value.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC'
  })
}

function persistTargets() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(targets.value))
    storageError.value = ''
  } catch (error) {
    storageError.value = `Target is saved by the API but could not be remembered in this browser: ${error.message}`
  }
}

function prepareTargetRenewal(target) {
  targetError.value = ''
  targetCreatedMessage.value = ''
  isRenewalDraft.value = true
  targetForm.name = target.name || ''
  targetForm.targetExpense = String(target.targetExpense)
  targetForm.currency = target.currency
  targetForm.startDate = addLocalDays(target.endDate, 1)
  targetForm.endDate = ''

  nextTick(() => {
    targetFormElement.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    targetEndDateInput.value?.focus({ preventScroll: true })
  })
}

async function loadMonthlyReport() {
  const [year, month] = reportMonth.value.split('-').map(Number)
  if (!year || month < 1 || month > 12) {
    reportError.value = 'Choose a valid month to load the expense report.'
    return
  }
  const requestId = ++reportRequestId
  isReportLoading.value = true
  reportError.value = ''
  try {
    const result = await subadviseApi.getMonthlyExpenses(year, month)
    if (requestId === reportRequestId) {
      report.value = result
    }
  } catch (error) {
    if (requestId === reportRequestId) {
      reportError.value = error.message || 'Could not load the monthly expense report.'
    }
  } finally {
    if (requestId === reportRequestId) {
      isReportLoading.value = false
    }
  }
}

watch(reportMonth, loadMonthlyReport)

async function createTarget() {
  targetError.value = ''
  targetCreatedMessage.value = ''
  const amount = Number(targetForm.targetExpense)
  if (!targetForm.name.trim()) {
    targetError.value = 'Enter a name for this target.'
    return
  }
  if (targetForm.targetExpense === '' || !Number.isFinite(amount) || amount < 0) {
    targetError.value = 'Target amount must be a valid number equal to or greater than zero.'
    return
  }
  if (!targetForm.endDate) {
    targetError.value = 'An end date is required.'
    return
  }
  if (targetForm.startDate && targetForm.startDate > targetForm.endDate) {
    targetError.value = 'Start date must not be after the end date.'
    return
  }

  isCreatingTarget.value = true
  const isRenewal = isRenewalDraft.value
  try {
    const created = await subadviseApi.createExpenseTarget(targetForm)
    if (!created?.targetId) {
      throw new Error('The API response did not include a target ID.')
    }
    const savedTarget = { ...created, name: targetForm.name.trim() }
    targets.value = [savedTarget, ...targets.value]
    persistTargets()
    selectedTargetId.value = savedTarget.targetId
    expenseForm.actualExpense = ''
    targetCreatedMessage.value = isRenewal ? 'Target renewed.' : 'Target saved.'
    isRenewalDraft.value = false
    targetForm.name = ''
    targetForm.targetExpense = ''
  } catch (error) {
    targetError.value = error.message || 'Could not save this target.'
  } finally {
    isCreatingTarget.value = false
  }
}

async function recordExpense() {
  expenseError.value = ''
  expenseCreatedMessage.value = ''
  const amount = Number(expenseForm.actualExpense)
  if (!selectedTarget.value) {
    expenseError.value = 'Create or select a target before recording an expense.'
    return
  }
  if (expenseForm.actualExpense === '' || !Number.isFinite(amount) || amount < 0) {
    expenseError.value = 'Actual expense must be a valid number equal to or greater than zero.'
    return
  }

  isRecordingExpense.value = true
  try {
    const result = await subadviseApi.createExpense({
      actualExpense: amount,
      currency: selectedTarget.value.currency,
      targetId: selectedTarget.value.targetId
    })
    expenseCreatedMessage.value = `Expense recorded. Difference from target: ${formatCurrency(result.difference, result.currency)}.`
    expenseForm.actualExpense = ''
    const targetMonth = selectedTarget.value.endDate.slice(0, 7)
    if (reportMonth.value === targetMonth) {
      await loadMonthlyReport()
    } else {
      reportMonth.value = targetMonth
    }
  } catch (error) {
    expenseError.value = error.message || 'Could not record this expense.'
  } finally {
    isRecordingExpense.value = false
  }
}

onMounted(loadMonthlyReport)
</script>

<template>
  <section class="dashboard-tool-card" aria-labelledby="expense-targets-title">
    <header class="dashboard-tool-header">
      <div>
        <p class="eyebrow">BUDGET TRACKING</p>
        <h2 id="expense-targets-title" class="dashboard-tool-title">Expense Targets</h2>
      </div>
      <span class="dashboard-tool-icon" aria-hidden="true">◎</span>
    </header>

    <p class="dashboard-tool-description">
      Set a spending limit for a date range and record actual expenses against it.
    </p>

    <div v-if="storageError" class="alert-banner alert-danger" role="alert">
      <span aria-hidden="true">⚠</span><span>{{ storageError }}</span>
    </div>

    <form ref="targetFormElement" class="dashboard-tool-form" @submit.prevent="createTarget">
      <div class="form-grid">
        <div class="form-group form-full">
          <label class="form-label" for="target-name">Target name</label>
          <input id="target-name" v-model="targetForm.name" class="form-input" maxlength="80" placeholder="e.g. Dining out" />
        </div>
        <div class="form-group">
          <label class="form-label" for="target-amount">Budget amount</label>
          <input id="target-amount" v-model="targetForm.targetExpense" class="form-input" type="number" min="0" step="0.01" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="target-currency">Currency</label>
          <select id="target-currency" v-model="targetForm.currency" class="form-select">
            <option v-for="currency in COMMON_CURRENCIES" :key="currency" :value="currency">{{ currency }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="target-start-date">Start date</label>
          <input id="target-start-date" v-model="targetForm.startDate" class="form-input" type="date" />
        </div>
        <div class="form-group">
          <label class="form-label" for="target-end-date">End date</label>
          <input id="target-end-date" ref="targetEndDateInput" v-model="targetForm.endDate" class="form-input" type="date" required />
        </div>
      </div>
      <p v-if="isRenewalDraft" class="tool-muted-message">
        Renewal starts the day after the previous target ends. Choose an end date for this period.
      </p>
      <div v-if="targetError" class="alert-banner alert-danger" role="alert">{{ targetError }}</div>
      <p v-if="targetCreatedMessage" class="tool-success-message" role="status">{{ targetCreatedMessage }}</p>
      <button class="btn-primary-app" type="submit" :disabled="isCreatingTarget">
        {{ isCreatingTarget ? 'Saving…' : isRenewalDraft ? 'Renew Target' : 'Set Target' }}
      </button>
    </form>

    <div class="tool-divider"></div>

    <form class="dashboard-tool-form" @submit.prevent="recordExpense">
      <h3 class="dashboard-tool-subtitle">Record an expense</h3>
      <div class="form-grid">
        <div class="form-group form-full">
          <label class="form-label" for="expense-target">Target</label>
          <select id="expense-target" v-model="selectedTargetId" class="form-select" :disabled="targets.length === 0">
            <option value="" disabled>Select a target</option>
            <option v-for="target in targets" :key="target.targetId" :value="target.targetId">
              {{ target.name || 'Expense target' }} · {{ formatCurrency(target.targetExpense, target.currency) }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="actual-expense">Actual amount</label>
          <input id="actual-expense" v-model="expenseForm.actualExpense" class="form-input" type="number" min="0" step="0.01" required :disabled="!selectedTarget" />
        </div>
        <div class="form-group">
          <label class="form-label" for="actual-currency">Currency</label>
          <input id="actual-currency" class="form-input" :value="expenseCurrency || 'Select a target'" readonly />
        </div>
      </div>
      <div v-if="expenseError" class="alert-banner alert-danger" role="alert">{{ expenseError }}</div>
      <p v-if="expenseCreatedMessage" class="tool-success-message" role="status">{{ expenseCreatedMessage }}</p>
      <button class="btn-secondary" type="submit" :disabled="isRecordingExpense || !selectedTarget">
        {{ isRecordingExpense ? 'Recording…' : 'Record Expense' }}
      </button>
    </form>

    <div class="tool-divider"></div>

    <div class="monthly-report-header">
      <h3 class="dashboard-tool-subtitle">Monthly activity</h3>
      <label class="form-label" for="report-month">Month</label>
      <input id="report-month" v-model="reportMonth" class="form-input report-month-input" type="month" />
    </div>
    <div v-if="reportError" class="alert-banner alert-danger" role="alert">{{ reportError }}</div>
    <p v-if="isReportLoading" class="tool-muted-message" role="status">Loading monthly report…</p>
    <template v-else-if="report">
      <div v-if="reportTotals.length" class="monthly-total-list">
        <div v-for="[currency, amount] in reportTotals" :key="currency" class="monthly-total">
          <span>{{ currency }} total</span>
          <strong>{{ formatCurrency(amount, currency) }}</strong>
        </div>
      </div>
      <p v-else class="tool-muted-message">No expenses recorded for this month.</p>

      <div v-if="targetsForMonth.length" class="target-progress-list">
        <div v-for="target in targetsForMonth" :key="target.targetId" class="target-progress-row">
          <div class="target-progress-heading">
            <strong>{{ target.name || 'Expense target' }}</strong>
            <span>{{ formatDate(target.endDate) }}</span>
          </div>
          <div class="target-progress-heading">
            <span>Budget {{ formatCurrency(target.targetExpense, target.currency) }}</span>
            <button type="button" class="btn-row-action" @click="prepareTargetRenewal(target)">
              Renew target
            </button>
          </div>
          <div class="target-progress-heading">
            <span>{{ formatCurrency(targetSpend(target.targetId), target.currency) }} spent</span>
            <span>of {{ formatCurrency(target.targetExpense, target.currency) }}</span>
          </div>
          <div class="target-progress-track">
            <div
              class="target-progress-fill"
              :class="{ 'is-over-target': targetSpend(target.targetId) > Number(target.targetExpense) }"
              :style="{ width: `${Math.min(100, Number(target.targetExpense) > 0 ? targetSpend(target.targetId) / Number(target.targetExpense) * 100 : targetSpend(target.targetId) > 0 ? 100 : 0)}%` }"
            ></div>
          </div>
        </div>
      </div>
      <p v-if="report.expenses?.length" class="tool-muted-message">
        {{ report.expenses.length }} expense{{ report.expenses.length === 1 ? '' : 's' }} recorded this month.
      </p>
    </template>

    <p class="tool-note">
      Target IDs are saved in this browser because the API does not provide a target-list endpoint.
    </p>
  </section>
</template>
