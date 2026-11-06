<script setup>
import { ref, computed } from 'vue'
import { useSubscriptionStore } from '@/stores/subscriptions'
import { useChatStore } from '@/stores/chat'
import { useThemeStore } from '@/stores/theme'
import SubscriptionTable from '@/components/SubscriptionTable.vue'
import AiChatSidebar from '@/components/AiChatSidebar.vue'

const subscriptionStore = useSubscriptionStore()
const chatStore = useChatStore()
const themeStore = useThemeStore()
const tableRef = ref(null)

const totalCount = computed(() => subscriptionStore.rawTotalCount)
const upcomingCount = computed(() => subscriptionStore.upcomingRenewals.length)
const monthlySubscriptionTotals = computed(() =>
  Object.entries(subscriptionStore.monthlySubscriptionTotals?.totalsByCurrency || {})
)
const monthlyTotalsMonthLabel = computed(() => {
  const { year, month } = subscriptionStore.monthlySubscriptionTotals || {}
  const date = year && month ? new Date(year, month - 1, 1) : new Date()
  return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
})

const highCostCount = computed(() => {
  const dist = subscriptionStore.colorDistribution
  return (dist.red || 0) + (dist.orange || 0)
})

const barSegments = computed(() => {
  const total = totalCount.value
  if (total === 0) return []

  const dist = subscriptionStore.colorDistribution
  const colors = [
    { key: 'red', label: 'RED', class: 'seg-red', count: dist.red || 0, dotBg: '#e11d48' },
    { key: 'orange', label: 'ORANGE', class: 'seg-orange', count: dist.orange || 0, dotBg: '#ea580c' },
    { key: 'yellow', label: 'YELLOW', class: 'seg-yellow', count: dist.yellow || 0, dotBg: '#ca8a04' },
    { key: 'lime', label: 'LIME', class: 'seg-lime', count: dist.lime || 0, dotBg: '#65a30d' },
    { key: 'green', label: 'GREEN', class: 'seg-green', count: dist.green || 0, dotBg: '#16a34a' }
  ]

  return colors.map((c) => ({
    ...c,
    percentage: Math.round((c.count / total) * 100)
  }))
})

function handleAddSubscriptionClick() {
  if (tableRef.value) {
    tableRef.value.openAddModal()
  }
}

function handleThresholdsClick() {
  if (tableRef.value) {
    tableRef.value.openThresholdModal(null)
  }
}

function handleClearLocalStorage() {
  const confirmed = window.confirm(
    'Clear SubAdvise data saved in this browser? This removes saved chat metadata, expense targets, and theme preference. Subscription records on the server are not affected.'
  )
  if (!confirmed) return

  try {
    const appStorageKeys = Object.keys(window.localStorage)
      .filter((key) => key.startsWith('subadvise.'))
    appStorageKeys.forEach((key) => window.localStorage.removeItem(key))
    window.location.reload()
  } catch (error) {
    console.error('Failed to clear SubAdvise local storage:', error)
    window.alert(`Could not clear local storage: ${error.message}`)
  }
}

function formatTime(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
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
</script>

<template>
  <div class="app-container">
    <!-- Top App Bar -->
    <header class="app-topbar" role="banner">
      <div class="topbar-left">
        <a class="topbar-brand" href="/" aria-label="SubAdvise home">
          <img
            src="/subadvise-logo.png"
            alt="SubAdvise to Copilot logo"
            class="brand-icon-img"
          />
          <span class="brand-title">SubAdvise</span>
        </a>
      </div>

      <div class="topbar-right">
        <!-- Dark Mode Toggle Button -->
        <button
          type="button"
          class="btn-topbar-action"
          @click="themeStore.toggleTheme"
          :title="themeStore.theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
          :aria-label="themeStore.theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
        >
          <span aria-hidden="true">{{ themeStore.theme === 'dark' ? '☀️' : '🌙' }}</span>
          <span>{{ themeStore.theme === 'dark' ? 'Light' : 'Dark' }}</span>
        </button>

        <!-- Classification Thresholds in top navbar -->
        <button
          type="button"
          class="btn-topbar-action"
          @click="handleThresholdsClick"
          title="Configure expense classification color thresholds"
        >
          <span aria-hidden="true">🎨</span>
          <span>Classification Thresholds</span>
        </button>

        <!-- Add Subscription primary action -->
        <button
          type="button"
          class="btn-topbar-action btn-topbar-primary"
          @click="handleAddSubscriptionClick"
          title="Create a new subscription"
        >
          <span aria-hidden="true">+</span>
          <span>Add Subscription</span>
        </button>

        <button
          type="button"
          class="btn-topbar-action"
          @click="handleClearLocalStorage"
          title="Clear SubAdvise data saved in this browser"
        >
          <span aria-hidden="true">⌫</span>
          <span>Clear Local Storage</span>
        </button>

        <!-- Toggle Copilot Panel -->
        <button
          type="button"
          class="btn-topbar-action btn-topbar-copilot"
          :class="{ 'is-active': chatStore.isOpen }"
          @click="chatStore.toggleOpen()"
          aria-label="Toggle Copilot panel"
        >
          <span aria-hidden="true">✦</span>
          <span>{{ chatStore.isOpen ? 'Copilot Open' : 'AI Copilot' }}</span>
        </button>
      </div>
    </header>

    <!-- App Body: Left Navigation + Main Canvas + Right Copilot Dock -->
    <div class="app-body">
      <!-- Left Navigation Rail -->
      <nav class="app-sidebar" aria-label="Application Navigation">
        <div>
          <div class="sidebar-heading">Navigation</div>
          <div class="sidebar-nav-list">
            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === 'ALL' }"
              @click="subscriptionStore.setColorFilter('ALL')"
            >
              <div class="nav-item-left">
                <span class="nav-icon" aria-hidden="true">⌂</span>
                <span>Subscriptions</span>
              </div>
              <span class="nav-badge">{{ totalCount }}</span>
            </button>

            <button
              type="button"
              class="sidebar-nav-item"
              @click="handleThresholdsClick"
            >
              <div class="nav-item-left">
                <span class="nav-icon" aria-hidden="true">🎨</span>
                <span>Color Thresholds</span>
              </div>
            </button>

            <router-link class="sidebar-nav-item" to="/expense-tools">
              <div class="nav-item-left">
                <span class="nav-icon" aria-hidden="true">⇄</span>
                <span>Targets & Currency</span>
              </div>
            </router-link>

            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': chatStore.isOpen }"
              @click="chatStore.setOpen(!chatStore.isOpen)"
            >
              <div class="nav-item-left">
                <span class="nav-icon" aria-hidden="true">✦</span>
                <span>AI Copilot</span>
              </div>
              <span class="nav-badge" style="background: #ead9ff; color: var(--purple-dark);">AI</span>
            </button>
          </div>

          <!-- Color Classification Filters -->
          <div class="sidebar-heading" style="margin-top: 1.25rem;">Cost Classification</div>
          <div class="sidebar-nav-list">
            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === 'ALL' }"
              @click="subscriptionStore.setColorFilter('ALL')"
            >
              <div class="nav-item-left">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: #6b5e7d;"></span>
                <span>All Tiers</span>
              </div>
              <span class="nav-badge">{{ totalCount }}</span>
            </button>

            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === 'red' }"
              @click="subscriptionStore.setColorFilter('red')"
            >
              <div class="nav-item-left">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-red);"></span>
                <span>Red (Highest)</span>
              </div>
              <span class="nav-badge">{{ subscriptionStore.colorDistribution.red || 0 }}</span>
            </button>

            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === 'orange' }"
              @click="subscriptionStore.setColorFilter('orange')"
            >
              <div class="nav-item-left">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-orange);"></span>
                <span>Orange (High)</span>
              </div>
              <span class="nav-badge">{{ subscriptionStore.colorDistribution.orange || 0 }}</span>
            </button>

            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === 'yellow' }"
              @click="subscriptionStore.setColorFilter('yellow')"
            >
              <div class="nav-item-left">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-yellow);"></span>
                <span>Yellow (Medium)</span>
              </div>
              <span class="nav-badge">{{ subscriptionStore.colorDistribution.yellow || 0 }}</span>
            </button>

            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === 'lime' }"
              @click="subscriptionStore.setColorFilter('lime')"
            >
              <div class="nav-item-left">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-lime);"></span>
                <span>Lime (Low)</span>
              </div>
              <span class="nav-badge">{{ subscriptionStore.colorDistribution.lime || 0 }}</span>
            </button>

            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === 'green' }"
              @click="subscriptionStore.setColorFilter('green')"
            >
              <div class="nav-item-left">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-green);"></span>
                <span>Green (Lowest)</span>
              </div>
              <span class="nav-badge">{{ subscriptionStore.colorDistribution.green || 0 }}</span>
            </button>
          </div>
        </div>

        <!-- Sidebar Footer Status: Actual Live Status -->
        <div class="sidebar-footer">
          <div class="workspace-status-card">
            <span
              class="status-dot"
              :class="{
                'status-dot-active': subscriptionStore.apiStatus === 'connected',
                'status-dot-syncing': subscriptionStore.apiStatus === 'syncing',
                'status-dot-error': subscriptionStore.apiStatus === 'error',
                'status-dot-idle': subscriptionStore.apiStatus === 'idle'
              }"
              aria-hidden="true"
            ></span>
            <div style="flex: 1; overflow: hidden;">
              <div style="font-size: 0.72rem; font-weight: 700; color: var(--ink-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {{
                  subscriptionStore.apiStatus === 'connected'
                    ? 'Backend Connected'
                    : subscriptionStore.apiStatus === 'syncing'
                    ? 'Syncing with API...'
                    : subscriptionStore.apiStatus === 'error'
                    ? 'API Disconnected'
                    : 'API Ready'
                }}
              </div>
              <div style="font-size: 0.65rem; color: var(--ink-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {{
                  subscriptionStore.apiStatus === 'connected' && subscriptionStore.lastSyncedAt
                    ? `Synced ${formatTime(subscriptionStore.lastSyncedAt)}`
                    : subscriptionStore.apiStatus === 'error'
                    ? 'Backend service offline'
                    : 'Port 7071 / 7072'
                }}
              </div>
            </div>
            <button
              v-if="subscriptionStore.apiStatus === 'error'"
              type="button"
              style="border: 0; background: transparent; color: var(--purple-primary); font-size: 0.85rem; cursor: pointer; padding: 0.1rem;"
              title="Retry connection"
              @click="subscriptionStore.fetchSubscriptions"
            >
              ↻
            </button>
          </div>
        </div>
      </nav>

      <!-- Main Workspace Canvas -->
      <main class="app-main-canvas" role="main">
        <!-- Canvas Header -->
        <div class="canvas-header">
          <div class="canvas-title-group">
            <h1>Subscriptions Dashboard</h1>
            <p>Manage your recurring plans, cost classifications, and renewal schedules.</p>
          </div>
        </div>

        <!-- Compact KPI Summary Strip -->
        <section class="kpi-strip" aria-label="Overview KPI Metrics">
          <div class="kpi-card">
            <div class="kpi-card-left">
              <h4>Total Active Plans</h4>
              <div class="kpi-val">{{ totalCount }}</div>
            </div>
            <span
              class="kpi-pill"
              :style="{
                background: subscriptionStore.apiStatus === 'connected' ? '#dcfce7' : '#fee2e2',
                color: subscriptionStore.apiStatus === 'connected' ? '#15803d' : '#991b1b'
              }"
            >
              {{ subscriptionStore.apiStatus === 'connected' ? '● Connected' : '● Offline' }}
            </span>
          </div>

          <div class="kpi-card">
            <div class="kpi-card-left">
              <h4>Top Expense Tiers</h4>
              <div class="kpi-val" style="color: #be123c;">{{ highCostCount }}</div>
            </div>
            <span class="kpi-pill" style="background: #ffe4e6; color: #be123c;">Red & Orange</span>
          </div>

          <div class="kpi-card">
            <div class="kpi-card-left">
              <h4>Renewing in 30 Days</h4>
              <div class="kpi-val" style="color: #a16207;">{{ upcomingCount }}</div>
            </div>
            <span class="kpi-pill" style="background: #fef9c3; color: #854d0e;">Action Needed</span>
          </div>

          <div class="kpi-card kpi-card-monthly" aria-label="Monthly subscription renewal totals">
            <div class="kpi-card-left monthly-subscription-kpi-content">
              <h4>Monthly Expense · {{ monthlyTotalsMonthLabel }}</h4>
              <p v-if="subscriptionStore.isMonthlySubscriptionTotalsLoading" class="monthly-subscription-message" role="status">
                Loading totals…
              </p>
              <p v-else-if="subscriptionStore.monthlySubscriptionTotalsError" class="monthly-subscription-message is-error" role="alert">
                {{ subscriptionStore.monthlySubscriptionTotalsError }}
              </p>
              <p v-else-if="monthlySubscriptionTotals.length === 0" class="monthly-subscription-message">
                No subscriptions renewing this month
              </p>
              <div v-else class="monthly-subscription-totals">
                <div
                  v-for="[currency, amount] in monthlySubscriptionTotals"
                  :key="currency"
                  class="monthly-subscription-total"
                >
                  <span>{{ currency }}</span>
                  <strong>{{ formatCurrency(amount, currency) }}</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Cost Classification Spectrum Bar -->
        <section v-if="totalCount > 0" class="spectrum-card-app" aria-label="Cost Classification Spectrum">
          <div class="spectrum-header-row">
            <h4>Cost Classification Distribution</h4>
            <button
              type="button"
              style="background: transparent; border: 0; color: var(--purple-primary); font-size: 0.72rem; font-weight: 700; cursor: pointer;"
              @click="subscriptionStore.setColorFilter('ALL')"
            >
              Reset Filter
            </button>
          </div>

          <div class="spectrum-bar-wrap">
            <div
              v-for="seg in barSegments"
              :key="seg.key"
              class="spectrum-segment"
              :class="seg.class"
              :style="{ width: `${seg.percentage}%` }"
              :title="`${seg.label}: ${seg.count} plans (${seg.percentage}%)`"
            ></div>
          </div>

          <div class="spectrum-chips">
            <button
              type="button"
              class="spectrum-chip-btn"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === 'ALL' }"
              @click="subscriptionStore.setColorFilter('ALL')"
            >
              All ({{ totalCount }})
            </button>

            <button
              v-for="seg in barSegments"
              :key="seg.key"
              type="button"
              class="spectrum-chip-btn"
              :class="{ 'is-active': subscriptionStore.selectedColorFilter === seg.key }"
              @click="subscriptionStore.setColorFilter(seg.key)"
            >
              <span class="chip-color-dot" :style="{ background: seg.dotBg }"></span>
              <span>{{ seg.label }} ({{ seg.count }})</span>
            </button>
          </div>
        </section>

        <!-- Subscriptions Table Grid -->
        <SubscriptionTable ref="tableRef" />
      </main>

      <!-- Right Copilot Dock Panel (Toggled via header/sidebar) -->
      <AiChatSidebar />
    </div>
  </div>
</template>
