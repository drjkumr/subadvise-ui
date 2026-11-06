<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useSubscriptionStore } from '@/stores/subscriptions'
import SubscriptionModal from './SubscriptionModal.vue'
import DeleteConfirmModal from './DeleteConfirmModal.vue'
import ColorThresholdModal from './ColorThresholdModal.vue'
import ConvertSubscriptionModal from './ConvertSubscriptionModal.vue'

const subscriptionStore = useSubscriptionStore()

// Local search query for debouncing
const searchInput = ref('')
let debounceTimer = null

// Modals state
const isModalOpen = ref(false)
const selectedSubscription = ref(null)

const isDeleteModalOpen = ref(false)
const subscriptionToDelete = ref(null)

const isThresholdModalOpen = ref(false)
const subscriptionForThreshold = ref(null)

const isConvertModalOpen = ref(false)
const subscriptionForConversion = ref(null)

onMounted(() => {
  subscriptionStore.fetchSubscriptions()
})

// Debounce search input by ~300ms
watch(searchInput, (newVal) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    subscriptionStore.setSearchQuery(newVal)
  }, 300)
})

function clearSearch() {
  searchInput.value = ''
  subscriptionStore.setSearchQuery('')
}

function openAddModal() {
  selectedSubscription.value = null
  isModalOpen.value = true
}

function openEditModal(sub) {
  selectedSubscription.value = { ...sub }
  isModalOpen.value = true
}

function openDeleteModal(sub) {
  subscriptionToDelete.value = sub
  isDeleteModalOpen.value = true
}

function openThresholdModal(sub) {
  subscriptionForThreshold.value = sub
  isThresholdModalOpen.value = true
}

function openConvertModal(sub) {
  subscriptionForConversion.value = sub
  isConvertModalOpen.value = true
}

async function handleSaveSubscription(formData) {
  try {
    if (selectedSubscription.value?.subscriptionId) {
      await subscriptionStore.updateSubscription(selectedSubscription.value.subscriptionId, formData)
    } else {
      await subscriptionStore.createSubscription(formData)
    }
    isModalOpen.value = false
  } catch (err) {
    // Handled in modal
  }
}

async function handleDeleteSubscription(id) {
  try {
    await subscriptionStore.deleteSubscription(id)
    isDeleteModalOpen.value = false
  } catch (err) {
    // Error state in store
  }
}

// Generate brand avatar gradient based on string hash
function getAvatarGradient(name) {
  const str = name || 'Sub'
  const gradients = [
    'linear-gradient(135deg, #e11d48, #be123c)', // Netflix red
    'linear-gradient(135deg, #10b981, #047857)', // Spotify green
    'linear-gradient(135deg, #6366f1, #4338ca)', // Discord / Tech indigo
    'linear-gradient(135deg, #ec4899, #be185d)', // Figma / Design pink
    'linear-gradient(135deg, #f59e0b, #b45309)', // AWS amber
    'linear-gradient(135deg, #0ea5e9, #0369a1)', // Google blue
    'linear-gradient(135deg, #8b5cf6, #6d28d9)'  // GitHub purple
  ]
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % gradients.length
  return gradients[index]
}

function getColorBadgeClass(color) {
  const c = (color || '').toLowerCase()
  switch (c) {
    case 'red':
      return 'badge-color-red'
    case 'orange':
      return 'badge-color-orange'
    case 'yellow':
      return 'badge-color-yellow'
    case 'lime':
      return 'badge-color-lime'
    case 'green':
      return 'badge-color-green'
    default:
      return 'badge-color-neutral'
  }
}

function formatCurrency(amount, currency) {
  if (amount === null || amount === undefined || isNaN(amount)) return '—'
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currency || 'USD',
      maximumFractionDigits: 2
    }).format(amount)
  } catch {
    return `${Number(amount).toFixed(2)} ${currency || ''}`
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  try {
    const [year, month, day] = dateStr.split('-')
    if (!year || !month || !day) return dateStr
    const d = new Date(Date.UTC(year, month - 1, day))
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: 'UTC'
    })
  } catch {
    return dateStr
  }
}

// Calculate days until renewal
function getRenewalBadge(renewalDateStr) {
  if (!renewalDateStr) return null
  const now = new Date()
  const todayUtc = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())
  const [year, month, day] = renewalDateStr.split('-')
  if (!year || !month || !day) return null
  const renewalUtc = Date.UTC(Number(year), Number(month) - 1, Number(day))

  const diffDays = Math.ceil((renewalUtc - todayUtc) / (1000 * 60 * 60 * 24))

  if (diffDays < 0) {
    return { text: 'Past due', isUrgent: true }
  }
  if (diffDays === 0) {
    return { text: 'Due today', isUrgent: true }
  }
  if (diffDays <= 30) {
    return { text: `In ${diffDays}d`, isUrgent: true }
  }
  return { text: `In ${diffDays}d`, isUrgent: false }
}

// Generate page numbers for pagination
const displayedPageNumbers = computed(() => {
  const total = subscriptionStore.totalPages
  const current = subscriptionStore.currentPage
  const delta = 2
  const pages = []

  for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
    pages.push(i)
  }
  return pages
})

defineExpose({
  openAddModal,
  openThresholdModal
})
</script>

<template>
  <div class="table-container-app">
    <!-- Toolbar: Search, Filters & Sorting -->
    <div class="table-toolbar-app">
      <!-- Search Input -->
      <div class="search-box-app">
        <span class="search-icon-app" aria-hidden="true">🔍</span>
        <input
          v-model="searchInput"
          type="search"
          class="search-input-app"
          placeholder="Search subscriptions..."
          aria-label="Search subscriptions by name"
        />
        <button
          v-if="searchInput"
          type="button"
          class="search-clear-app"
          @click="clearSearch"
          aria-label="Clear search query"
        >
          &times;
        </button>
      </div>

      <!-- Right Controls: Sort & Refresh -->
      <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
        <div style="display: flex; align-items: center; gap: 0.35rem;">
          <label for="table-sort" style="font-size: 0.72rem; font-weight: 700; color: var(--ink-muted);">
            SORT:
          </label>
          <select
            id="table-sort"
            :value="subscriptionStore.sortBy"
            @change="subscriptionStore.setSortBy($event.target.value)"
            class="sort-select-app"
            aria-label="Sort subscriptions"
          >
            <option value="renewal-asc">Renewal (Soonest)</option>
            <option value="renewal-desc">Renewal (Furthest)</option>
            <option value="price-desc">Price (High to Low)</option>
            <option value="price-asc">Price (Low to High)</option>
            <option value="name-asc">Name (A–Z)</option>
            <option value="name-desc">Name (Z–A)</option>
          </select>
        </div>

        <button
          type="button"
          class="btn-row-action"
          @click="subscriptionStore.fetchSubscriptions"
          :disabled="subscriptionStore.isLoading"
          title="Refresh subscriptions"
          aria-label="Refresh subscriptions list"
        >
          <span aria-hidden="true" :style="{ display: 'inline-block', transform: subscriptionStore.isLoading ? 'rotate(180deg)' : 'none', transition: 'transform 0.4s ease' }">↻</span>
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Error Banner -->
    <div v-if="subscriptionStore.error" class="alert-banner alert-danger" style="margin: 0.75rem;" role="alert">
      <span aria-hidden="true">⚠</span>
      <div style="flex: 1;">
        <strong>Error connecting to SubAdvise API:</strong>
        <p style="margin: 0.15rem 0 0;">{{ subscriptionStore.error }}</p>
      </div>
      <button
        type="button"
        class="btn-row-action"
        @click="subscriptionStore.fetchSubscriptions"
      >
        Retry
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="subscriptionStore.isLoading && subscriptionStore.subscriptions.length === 0" class="state-box">
      <div class="spinner"></div>
      <h3 style="margin: 0.5rem 0 0.2rem; font-size: 0.95rem; color: var(--ink-primary);">Loading subscriptions</h3>
      <p style="margin: 0; font-size: 0.75rem; color: var(--ink-muted);">Fetching recurring plans and classifying costs...</p>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!subscriptionStore.isLoading && subscriptionStore.subscriptions.length === 0"
      class="state-box"
    >
      <div style="font-size: 2rem;" aria-hidden="true">📁</div>
      <h3 style="margin: 0.5rem 0 0.2rem; font-size: 0.95rem; color: var(--ink-primary);">
        {{ subscriptionStore.searchQuery ? 'No matching subscriptions' : 'No subscriptions yet' }}
      </h3>
      <p style="margin: 0 0 0.85rem; font-size: 0.78rem; color: var(--ink-muted);">
        {{
          subscriptionStore.searchQuery
            ? `No subscriptions found matching "${subscriptionStore.searchQuery}". Try a different name or clear the search.`
            : 'Get started by creating your first subscription to track renewal schedules and classify expenses.'
        }}
      </p>
      <button
        v-if="subscriptionStore.searchQuery"
        type="button"
        class="btn-row-action"
        @click="clearSearch"
      >
        Clear Search
      </button>
    </div>

    <!-- Empty Filtered Results State -->
    <div
      v-else-if="subscriptionStore.filteredSubscriptions.length === 0"
      class="state-box"
    >
      <div style="font-size: 2rem;" aria-hidden="true">🎯</div>
      <h3 style="margin: 0.5rem 0 0.2rem; font-size: 0.95rem; color: var(--ink-primary);">
        No subscriptions in this tier
      </h3>
      <p style="margin: 0 0 0.85rem; font-size: 0.78rem; color: var(--ink-muted);">
        No subscriptions currently classified under the "{{ subscriptionStore.selectedColorFilter.toUpperCase() }}" threshold.
      </p>
      <button
        type="button"
        class="btn-row-action"
        @click="subscriptionStore.setColorFilter('ALL')"
      >
        Show All Subscriptions
      </button>
    </div>

    <!-- Subscriptions Table -->
    <div v-else class="table-scroll-app">
      <table class="data-table-app" aria-label="Subscriptions Table">
        <thead>
          <tr>
            <th scope="col">Subscription Plan</th>
            <th scope="col">Start Date</th>
            <th scope="col">Renewal Date</th>
            <th scope="col">Price & Currency</th>
            <th scope="col">Cost Level</th>
            <th scope="col" style="text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="sub in subscriptionStore.paginatedSubscriptions"
            :key="sub.subscriptionId"
          >
            <!-- Subscription Name & Avatar -->
            <td>
              <div class="service-cell-app">
                <div
                  class="service-avatar-app"
                  :style="{ background: getAvatarGradient(sub.subscriptionName) }"
                  aria-hidden="true"
                >
                  {{ (sub.subscriptionName || 'S').slice(0, 2).toUpperCase() }}
                </div>
                <div class="service-title-app">
                  <strong>{{ sub.subscriptionName }}</strong>
                  <small>{{ sub.currency || 'USD' }} · Recurring</small>
                </div>
              </div>
            </td>

            <!-- Start Date -->
            <td>{{ formatDate(sub.subscriptionDate) }}</td>

            <!-- Renewal Date & Countdown Pill -->
            <td>
              <div style="display: flex; align-items: center; gap: 0.45rem;">
                <span style="font-weight: 700; color: var(--ink-primary);">{{ formatDate(sub.renewalDate) }}</span>
                <span
                  v-if="getRenewalBadge(sub.renewalDate)"
                  class="renewal-badge-app"
                  :class="getRenewalBadge(sub.renewalDate).isUrgent ? 'renewal-badge-urgent' : 'renewal-badge-normal'"
                >
                  {{ getRenewalBadge(sub.renewalDate).text }}
                </span>
              </div>
            </td>

            <!-- Price & Currency -->
            <td>
              <strong style="color: var(--ink-primary); font-size: 0.85rem;">
                {{ formatCurrency(sub.subscriptionPrice, sub.currency) }}
              </strong>
            </td>

            <!-- Color Level Badge with Animated Dot -->
            <td>
              <span
                class="status-badge"
                :class="getColorBadgeClass(sub.color)"
                :title="`Relative cost: ${sub.color || 'unclassified'}`"
              >
                {{ (sub.color || 'Standard').toUpperCase() }}
              </span>
            </td>

            <!-- Row Actions -->
            <td style="text-align: right;">
              <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.35rem;">
                <button
                  type="button"
                  class="btn-row-action"
                  @click="openConvertModal(sub)"
                  title="Convert and save subscription currency"
                  :aria-label="`Convert ${sub.subscriptionName} currency`"
                >
                  <span aria-hidden="true">⇄</span>
                  <span>Convert</span>
                </button>

                <!-- Edit button -->
                <button
                  type="button"
                  class="btn-row-action"
                  @click="openEditModal(sub)"
                  title="Edit subscription"
                  :aria-label="`Edit ${sub.subscriptionName}`"
                >
                  <span aria-hidden="true">✎</span>
                  <span>Edit</span>
                </button>

                <!-- Color Threshold button -->
                <button
                  type="button"
                  class="btn-row-action"
                  @click="openThresholdModal(sub)"
                  title="Adjust thresholds"
                  :aria-label="`Color thresholds for ${sub.subscriptionName}`"
                >
                  <span aria-hidden="true">🎨</span>
                  <span>Threshold</span>
                </button>

                <!-- Delete button -->
                <button
                  type="button"
                  class="btn-row-action btn-row-danger"
                  @click="openDeleteModal(sub)"
                  title="Delete subscription"
                  :aria-label="`Delete ${sub.subscriptionName}`"
                >
                  <span aria-hidden="true">🗑</span>
                  <span>Delete</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination Controls (At most 50 items per page) -->
    <div
      v-if="subscriptionStore.filteredSubscriptions.length > 0"
      class="pagination-bar-app"
    >
      <div class="pagination-range-text">
        Showing <strong>{{ subscriptionStore.rangeText }}</strong>
        <span v-if="subscriptionStore.selectedColorFilter !== 'ALL'">
          (filtered by {{ subscriptionStore.selectedColorFilter.toUpperCase() }})
        </span>
      </div>

      <nav
        class="pagination-pages-group"
        aria-label="Pagination Navigation"
        v-if="subscriptionStore.totalPages > 1"
      >
        <button
          type="button"
          class="page-btn-app"
          @click="subscriptionStore.prevPage"
          :disabled="subscriptionStore.currentPage <= 1"
          aria-label="Previous page"
        >
          ‹
        </button>

        <button
          v-for="pageNum in displayedPageNumbers"
          :key="pageNum"
          type="button"
          class="page-btn-app"
          :class="{ 'is-active': pageNum === subscriptionStore.currentPage }"
          @click="subscriptionStore.setPage(pageNum)"
          :aria-label="`Page ${pageNum}`"
          :aria-current="pageNum === subscriptionStore.currentPage ? 'page' : null"
        >
          {{ pageNum }}
        </button>

        <button
          type="button"
          class="page-btn-app"
          @click="subscriptionStore.nextPage"
          :disabled="subscriptionStore.currentPage >= subscriptionStore.totalPages"
          aria-label="Next page"
        >
          ›
        </button>
      </nav>
    </div>
  </div>

  <!-- Add/Edit Subscription Modal -->
  <SubscriptionModal
    :is-open="isModalOpen"
    :subscription="selectedSubscription"
    @close="isModalOpen = false"
    @save="handleSaveSubscription"
  />

  <!-- Delete Confirmation Modal -->
  <DeleteConfirmModal
    :is-open="isDeleteModalOpen"
    :subscription="subscriptionToDelete"
    @close="isDeleteModalOpen = false"
    @confirm="handleDeleteSubscription"
  />

  <!-- Color Threshold Editor Modal -->
  <ColorThresholdModal
    :is-open="isThresholdModalOpen"
    :subscription="subscriptionForThreshold"
    @close="isThresholdModalOpen = false"
  />

  <ConvertSubscriptionModal
    :is-open="isConvertModalOpen"
    :subscription="subscriptionForConversion"
    @close="isConvertModalOpen = false"
  />
</template>
