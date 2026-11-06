<script setup>
import { ref, reactive, watch, nextTick } from 'vue'
import { COMMON_CURRENCIES, SUPPORTED_CURRENCIES } from '@/utils/currencies'

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

const emit = defineEmits(['close', 'save'])

const isSubmitting = ref(false)
const serverError = ref(null)
const nameInputRef = ref(null)

const presets = [
  { name: 'Netflix', price: 15.99, currency: 'USD' },
  { name: 'Spotify', price: 11.99, currency: 'USD' },
  { name: 'GitHub Copilot', price: 10.00, currency: 'USD' },
  { name: 'ChatGPT Plus', price: 20.00, currency: 'USD' },
  { name: 'Google One', price: 2.99, currency: 'USD' },
  { name: 'AWS Cloud', price: 45.00, currency: 'USD' }
]

const form = reactive({
  subscriptionName: '',
  subscriptionDate: '',
  renewalDate: '',
  subscriptionPrice: '',
  currency: 'USD'
})

const errors = reactive({
  subscriptionName: '',
  subscriptionDate: '',
  renewalDate: '',
  subscriptionPrice: '',
  currency: ''
})

function resetErrors() {
  errors.subscriptionName = ''
  errors.subscriptionDate = ''
  errors.renewalDate = ''
  errors.subscriptionPrice = ''
  errors.currency = ''
  serverError.value = null
}

function todayIso() {
  return new Date().toISOString().split('T')[0]
}

function oneYearFromTodayIso() {
  const d = new Date()
  d.setFullYear(d.getFullYear() + 1)
  return d.toISOString().split('T')[0]
}

function applyPreset(preset) {
  form.subscriptionName = preset.name
  form.subscriptionPrice = preset.price
  form.currency = preset.currency
  if (!form.subscriptionDate) form.subscriptionDate = todayIso()
  if (!form.renewalDate) form.renewalDate = oneYearFromTodayIso()
}

watch(
  () => props.isOpen,
  (open) => {
    resetErrors()
    if (open) {
      if (props.subscription) {
        // Edit mode
        form.subscriptionName = props.subscription.subscriptionName || ''
        form.subscriptionDate = props.subscription.subscriptionDate || ''
        form.renewalDate = props.subscription.renewalDate || ''
        form.subscriptionPrice = props.subscription.subscriptionPrice ?? ''
        form.currency = props.subscription.currency || 'USD'
      } else {
        // Add mode: sensible defaults
        form.subscriptionName = ''
        form.subscriptionDate = todayIso()
        form.renewalDate = oneYearFromTodayIso()
        form.subscriptionPrice = ''
        form.currency = 'USD'
      }

      nextTick(() => {
        if (nameInputRef.value) {
          nameInputRef.value.focus()
        }
      })
    }
  },
  { immediate: true }
)

function validate() {
  resetErrors()
  let isValid = true

  if (!form.subscriptionName || !form.subscriptionName.trim()) {
    errors.subscriptionName = 'Subscription name is required.'
    isValid = false
  }

  if (!form.subscriptionDate) {
    errors.subscriptionDate = 'Subscription start date is required.'
    isValid = false
  }

  if (!form.renewalDate) {
    errors.renewalDate = 'Renewal date is required.'
    isValid = false
  }

  const priceNum = Number(form.subscriptionPrice)
  if (form.subscriptionPrice === '' || isNaN(priceNum) || priceNum < 0) {
    errors.subscriptionPrice = 'Price must be a valid number equal to or greater than 0.'
    isValid = false
  }

  if (!form.currency || !/^[A-Z]{3}$/.test(form.currency.toUpperCase())) {
    errors.currency = 'Currency must be a 3-letter ISO 4217 currency code.'
    isValid = false
  }

  return isValid
}

async function handleSubmit() {
  if (!validate()) return

  isSubmitting.value = true
  serverError.value = null

  try {
    const payload = {
      subscriptionName: form.subscriptionName.trim(),
      subscriptionDate: form.subscriptionDate,
      renewalDate: form.renewalDate,
      subscriptionPrice: Number(form.subscriptionPrice),
      currency: form.currency.trim().toUpperCase()
    }

    emit('save', payload)
  } catch (err) {
    serverError.value = err.message || 'An unexpected error occurred while saving.'
  } finally {
    isSubmitting.value = false
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
    :aria-labelledby="subscription ? 'edit-dialog-title' : 'add-dialog-title'"
  >
    <div class="modal-dialog">
      <header class="modal-header">
        <div>
          <p class="eyebrow" style="margin-bottom: 0.2rem;">SUBSCRIPTION RECORD</p>
          <h3 :id="subscription ? 'edit-dialog-title' : 'add-dialog-title'" class="modal-title">
            {{ subscription ? 'Edit Subscription' : 'Add New Subscription' }}
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

      <form @submit.prevent="handleSubmit">
        <div class="modal-body">
          <!-- Quick Presets when adding a new subscription -->
          <div v-if="!subscription" style="margin-bottom: 1.1rem;">
            <p style="margin: 0 0 0.4rem; font-size: 0.72rem; font-weight: 700; color: var(--muted); text-transform: uppercase;">
              Quick Presets:
            </p>
            <div class="preset-bar">
              <button
                v-for="p in presets"
                :key="p.name"
                type="button"
                class="preset-chip"
                @click="applyPreset(p)"
                :title="`Fill with ${p.name} ($${p.price})`"
              >
                + {{ p.name }}
              </button>
            </div>
          </div>

          <!-- Server Error Notice -->
          <div v-if="serverError" class="alert-banner alert-danger" role="alert">
            <span aria-hidden="true">⚠</span>
            <div>
              <strong>Error saving subscription:</strong>
              <p style="margin: 0.2rem 0 0;">{{ serverError }}</p>
            </div>
          </div>

          <div class="form-grid">
            <!-- Subscription Name -->
            <div class="form-group form-full">
              <label for="sub-name" class="form-label">
                Subscription Name <span class="required-star">*</span>
              </label>
              <input
                id="sub-name"
                ref="nameInputRef"
                v-model="form.subscriptionName"
                type="text"
                class="form-input"
                :class="{ 'has-error': errors.subscriptionName }"
                placeholder="e.g. Netflix, Spotify, GitHub Copilot"
                required
              />
              <span v-if="errors.subscriptionName" class="form-error">
                {{ errors.subscriptionName }}
              </span>
            </div>

            <!-- Price -->
            <div class="form-group">
              <label for="sub-price" class="form-label">
                Price <span class="required-star">*</span>
              </label>
              <input
                id="sub-price"
                v-model="form.subscriptionPrice"
                type="number"
                step="0.01"
                min="0"
                class="form-input"
                :class="{ 'has-error': errors.subscriptionPrice }"
                placeholder="0.00"
                required
              />
              <span v-if="errors.subscriptionPrice" class="form-error">
                {{ errors.subscriptionPrice }}
              </span>
            </div>

            <!-- Currency -->
            <div class="form-group">
              <label for="sub-currency" class="form-label">
                Currency <span class="required-star">*</span>
              </label>
              <select
                id="sub-currency"
                v-model="form.currency"
                class="form-select"
                :class="{ 'has-error': errors.currency }"
                required
              >
                <optgroup label="Common Currencies">
                  <option v-for="c in COMMON_CURRENCIES" :key="c" :value="c">
                    {{ c }}
                  </option>
                </optgroup>
                <optgroup label="All Supported Currencies">
                  <option v-for="c in SUPPORTED_CURRENCIES" :key="c" :value="c">
                    {{ c }}
                  </option>
                </optgroup>
              </select>
              <span v-if="errors.currency" class="form-error">
                {{ errors.currency }}
              </span>
            </div>

            <!-- Start Date -->
            <div class="form-group">
              <label for="sub-date" class="form-label">
                Subscription Date <span class="required-star">*</span>
              </label>
              <input
                id="sub-date"
                v-model="form.subscriptionDate"
                type="date"
                class="form-input"
                :class="{ 'has-error': errors.subscriptionDate }"
                required
              />
              <span v-if="errors.subscriptionDate" class="form-error">
                {{ errors.subscriptionDate }}
              </span>
            </div>

            <!-- Renewal Date -->
            <div class="form-group">
              <label for="sub-renewal" class="form-label">
                Renewal Date <span class="required-star">*</span>
              </label>
              <input
                id="sub-renewal"
                v-model="form.renewalDate"
                type="date"
                class="form-input"
                :class="{ 'has-error': errors.renewalDate }"
                required
              />
              <span v-if="errors.renewalDate" class="form-error">
                {{ errors.renewalDate }}
              </span>
            </div>
          </div>
        </div>

        <footer class="modal-footer">
          <button
            type="button"
            class="btn-modal-cancel"
            @click="emit('close')"
            :disabled="isSubmitting"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="btn-primary-app"
            :disabled="isSubmitting"
          >
            <span v-if="isSubmitting">Saving...</span>
            <span v-else>{{ subscription ? 'Update Subscription' : 'Create Subscription' }}</span>
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>
