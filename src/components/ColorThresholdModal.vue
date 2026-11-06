<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { useSubscriptionStore } from '@/stores/subscriptions'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  subscription: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'saved'])

const subscriptionStore = useSubscriptionStore()

const isSaving = ref(false)
const errorMessage = ref(null)

const levels = reactive({
  red: 50,
  orange: 30,
  yellow: 15,
  lime: 5,
  green: 0
})

const levelMeta = [
  {
    key: 'red',
    label: 'RED',
    meaning: 'Most expensive (Top share of portfolio)',
    colorClass: 'badge-color-red',
    dotBg: '#e11d48'
  },
  {
    key: 'orange',
    label: 'ORANGE',
    meaning: 'Expensive (High cost tier)',
    colorClass: 'badge-color-orange',
    dotBg: '#ea580c'
  },
  {
    key: 'yellow',
    label: 'YELLOW',
    meaning: 'Medium (Average cost tier)',
    colorClass: 'badge-color-yellow',
    dotBg: '#ca8a04'
  },
  {
    key: 'lime',
    label: 'LIME',
    meaning: 'Low (Moderate budget tier)',
    colorClass: 'badge-color-lime',
    dotBg: '#65a30d'
  },
  {
    key: 'green',
    label: 'GREEN',
    meaning: 'Lowest cost, one of the lowest as a part of the whole',
    colorClass: 'badge-color-green',
    dotBg: '#16a34a'
  }
]

watch(
  () => props.isOpen,
  async (open) => {
    if (open) {
      errorMessage.value = null
      await subscriptionStore.fetchThresholds()
      levels.red = subscriptionStore.thresholds.red ?? 50
      levels.orange = subscriptionStore.thresholds.orange ?? 30
      levels.yellow = subscriptionStore.thresholds.yellow ?? 15
      levels.lime = subscriptionStore.thresholds.lime ?? 5
      levels.green = subscriptionStore.thresholds.green ?? 0
    }
  },
  { immediate: true }
)

function resetToDefaults() {
  levels.red = 50
  levels.orange = 30
  levels.yellow = 15
  levels.lime = 5
  levels.green = 0
  errorMessage.value = null
}

function validate() {
  errorMessage.value = null

  const keys = ['red', 'orange', 'yellow', 'lime', 'green']
  const nums = {}

  for (const k of keys) {
    const val = Number(levels[k])
    if (levels[k] === '' || isNaN(val)) {
      errorMessage.value = `All thresholds must be valid numbers (${k.toUpperCase()} is invalid).`
      return false
    }
    if (val < 0 || val > 100) {
      errorMessage.value = `Threshold values must be between 0 and 100 (${k.toUpperCase()} is ${val}).`
      return false
    }
    nums[k] = val
  }

  // Strictly descend: red > orange > yellow > lime > green
  if (nums.red <= nums.orange) {
    errorMessage.value = 'RED threshold must be strictly greater than ORANGE threshold.'
    return false
  }
  if (nums.orange <= nums.yellow) {
    errorMessage.value = 'ORANGE threshold must be strictly greater than YELLOW threshold.'
    return false
  }
  if (nums.yellow <= nums.lime) {
    errorMessage.value = 'YELLOW threshold must be strictly greater than LIME threshold.'
    return false
  }
  if (nums.lime <= nums.green) {
    errorMessage.value = 'LIME threshold must be strictly greater than GREEN threshold.'
    return false
  }

  return true
}

async function handleSave() {
  if (!validate()) return

  isSaving.value = true
  errorMessage.value = null

  try {
    const payload = {
      red: Number(levels.red),
      orange: Number(levels.orange),
      yellow: Number(levels.yellow),
      lime: Number(levels.lime),
      green: Number(levels.green)
    }

    await subscriptionStore.updateThresholds(payload)
    emit('saved')
    emit('close')
  } catch (err) {
    errorMessage.value = err.message || 'Failed to update color thresholds.'
  } finally {
    isSaving.value = false
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape') {
    emit('close')
  }
}
</script>

<template>
  <div
    v-if="isOpen"
    class="modal-overlay"
    @click.self="emit('close')"
    @keydown="handleKeydown"
    role="dialog"
    aria-modal="true"
    aria-labelledby="threshold-dialog-title"
  >
    <div class="modal-dialog" style="max-width: 600px;">
      <header class="modal-header">
        <div>
          <p class="eyebrow" style="margin-bottom: 0.2rem;">CLASSIFICATION SYSTEM</p>
          <h3 id="threshold-dialog-title" class="modal-title">
            Expense Color Thresholds
          </h3>
        </div>
        <button
          type="button"
          class="modal-close-btn"
          @click="emit('close')"
          aria-label="Close modal"
        >
          &times;
        </button>
      </header>

      <form @submit.prevent="handleSave">
        <div class="modal-body">
          <p style="margin: 0 0 0.85rem; font-size: 0.82rem; color: var(--muted); line-height: 1.55;">
            Configure the minimum percentage of total subscription cost required for each tier.
            Subscriptions are compared to the converted total and assigned the first color whose threshold is met in descending order.
          </p>

          <!-- Interactive Threshold Spectrum Visualizer -->
          <div style="position: relative; margin: 1.5rem 0.5rem 1rem;">
            <div class="threshold-visualizer">
              <!-- Visual markers for thresholds -->
              <div
                v-if="!isNaN(levels.red)"
                class="threshold-marker"
                :style="{ left: `${Math.min(100, Math.max(0, levels.red))}%` }"
              >
                <span class="threshold-marker-tag">RED {{ levels.red }}%</span>
              </div>
              <div
                v-if="!isNaN(levels.orange)"
                class="threshold-marker"
                :style="{ left: `${Math.min(100, Math.max(0, levels.orange))}%` }"
              >
                <span class="threshold-marker-tag">ORG {{ levels.orange }}%</span>
              </div>
              <div
                v-if="!isNaN(levels.yellow)"
                class="threshold-marker"
                :style="{ left: `${Math.min(100, Math.max(0, levels.yellow))}%` }"
              >
                <span class="threshold-marker-tag">YEL {{ levels.yellow }}%</span>
              </div>
              <div
                v-if="!isNaN(levels.lime)"
                class="threshold-marker"
                :style="{ left: `${Math.min(100, Math.max(0, levels.lime))}%` }"
              >
                <span class="threshold-marker-tag">LIME {{ levels.lime }}%</span>
              </div>
              <div
                v-if="!isNaN(levels.green)"
                class="threshold-marker"
                :style="{ left: `${Math.min(100, Math.max(0, levels.green))}%` }"
              >
                <span class="threshold-marker-tag">GRN {{ levels.green }}%</span>
              </div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.65rem; color: var(--muted); font-weight: 700; margin-top: 0.25rem;">
              <span>0% (Lowest Cost)</span>
              <span>100% (Highest Cost)</span>
            </div>
          </div>

          <!-- Error Alert Banner -->
          <div v-if="errorMessage" class="alert-banner alert-danger" role="alert">
            <span aria-hidden="true">⚠</span>
            <span>{{ errorMessage }}</span>
          </div>

          <!-- Loading State -->
          <div v-if="subscriptionStore.isThresholdsLoading" class="state-box" style="padding: 1.5rem 0;">
            <div class="spinner"></div>
            <p class="state-text">Loading current thresholds from server...</p>
          </div>

          <!-- Threshold Level Inputs -->
          <div v-else style="display: flex; flex-direction: column; gap: 0.75rem; margin-top: 1rem;">
            <div
              v-for="item in levelMeta"
              :key="item.key"
              style="display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.75rem 1rem; background: #faf8fd; border: 1px solid var(--line); border-radius: 0.85rem;"
            >
              <div style="display: flex; align-items: center; gap: 0.75rem; flex: 1;">
                <span
                  class="status-badge"
                  :class="item.colorClass"
                  style="font-weight: 800; min-width: 82px; justify-content: center;"
                >
                  {{ item.label }}
                </span>
                <span style="font-size: 0.76rem; color: var(--ink);">
                  {{ item.meaning }}
                </span>
              </div>

              <div style="display: flex; align-items: center; gap: 0.4rem;">
                <label :for="`threshold-${item.key}`" class="sr-only">
                  {{ item.label }} threshold percentage
                </label>
                <input
                  :id="`threshold-${item.key}`"
                  v-model="levels[item.key]"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  class="form-input"
                  style="width: 80px; text-align: right; padding: 0.45rem 0.6rem; font-weight: 700;"
                  required
                />
                <span style="font-size: 0.8rem; font-weight: 700; color: var(--muted);">%</span>
              </div>
            </div>
          </div>
        </div>

        <footer class="modal-footer" style="justify-content: space-between;">
          <button
            type="button"
            class="text-link"
            style="cursor: pointer; border: 0; background: transparent;"
            @click="resetToDefaults"
          >
            Reset Defaults (50, 30, 15, 5, 0)
          </button>

          <div style="display: flex; align-items: center; gap: 0.65rem;">
            <button
              type="button"
              class="btn-modal-cancel"
              @click="emit('close')"
              :disabled="isSaving"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn-primary-app"
              :disabled="isSaving || subscriptionStore.isThresholdsLoading"
            >
              <span v-if="isSaving">Saving...</span>
              <span v-else>Save Thresholds</span>
            </button>
          </div>
        </footer>
      </form>
    </div>
  </div>
</template>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
