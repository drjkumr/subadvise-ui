<script setup>
import { ref, watch } from 'vue'
import { useSubscriptionStore } from '@/stores/subscriptions'
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

const emit = defineEmits(['close'])
const subscriptionStore = useSubscriptionStore()
const currency = ref('EUR')
const isSaving = ref(false)
const errorMessage = ref('')
const conversionResult = ref(null)

watch(
  () => [props.isOpen, props.subscription],
  ([isOpen, subscription]) => {
    if (!isOpen) return
    const currentCurrency = subscription?.currency || 'USD'
    currency.value = COMMON_CURRENCIES.find((item) => item !== currentCurrency)
      || SUPPORTED_CURRENCIES.find((item) => item !== currentCurrency)
      || currentCurrency
    errorMessage.value = ''
    conversionResult.value = null
  },
  { immediate: true }
)

async function convertSubscription() {
  if (!props.subscription?.subscriptionId) {
    errorMessage.value = 'Select a saved subscription to convert.'
    return
  }
  if (currency.value === props.subscription.currency) {
    errorMessage.value = 'Choose a different currency from the current subscription currency.'
    return
  }

  isSaving.value = true
  errorMessage.value = ''
  conversionResult.value = null
  try {
    conversionResult.value = await subscriptionStore.convertSubscriptionCurrency(
      props.subscription.subscriptionId,
      currency.value
    )
  } catch (error) {
    errorMessage.value = error.message || 'Could not convert this subscription.'
  } finally {
    isSaving.value = false
  }
}

function formatCurrency(amount, currencyCode) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currencyCode,
      maximumFractionDigits: 2
    }).format(Number(amount))
  } catch {
    return `${Number(amount).toFixed(2)} ${currencyCode || ''}`
  }
}
</script>

<template>
  <div
    v-if="isOpen"
    class="modal-overlay"
    @click.self="emit('close')"
    role="dialog"
    aria-modal="true"
    aria-labelledby="convert-subscription-title"
  >
    <div class="modal-dialog">
      <header class="modal-header">
        <div>
          <p class="eyebrow" style="margin-bottom: 0.2rem;">CURRENCY CONVERSION</p>
          <h3 id="convert-subscription-title" class="modal-title">Convert {{ subscription?.subscriptionName }}</h3>
        </div>
        <button type="button" class="modal-close-btn" @click="emit('close')" aria-label="Close modal">
          &times;
        </button>
      </header>

      <form @submit.prevent="convertSubscription">
        <div class="modal-body">
          <p class="tool-muted-message">
            Convert the saved price from {{ subscription?.currency || 'USD' }} to another currency using current API rates.
            The saved subscription price and currency will be updated.
          </p>

          <div class="form-group">
            <label class="form-label" for="subscription-conversion-currency">Convert to</label>
            <select id="subscription-conversion-currency" v-model="currency" class="form-select">
              <option v-for="item in SUPPORTED_CURRENCIES" :key="item" :value="item" :disabled="item === subscription?.currency">
                {{ item }}{{ item === subscription?.currency ? ' (current)' : '' }}
              </option>
            </select>
          </div>

          <div v-if="errorMessage" class="alert-banner alert-danger" role="alert">
            <span aria-hidden="true">⚠</span><span>{{ errorMessage }}</span>
          </div>

          <div v-if="conversionResult?.conversion" class="conversion-result" role="status" aria-live="polite">
            <p class="eyebrow">SUBSCRIPTION UPDATED</p>
            <strong>{{ formatCurrency(conversionResult.conversion.convertedAmount, conversionResult.conversion.to) }}</strong>
            <span>
              {{ formatCurrency(conversionResult.conversion.amount, conversionResult.conversion.from) }}
              → {{ conversionResult.conversion.to }}
            </span>
            <small v-if="conversionResult.conversion.rateProvider">{{ conversionResult.conversion.rateProvider }}</small>
            <a
              v-if="conversionResult.conversion.attributionUrl"
              :href="conversionResult.conversion.attributionUrl"
              target="_blank"
              rel="noopener noreferrer"
            >
              ExchangeRate-API attribution
            </a>
          </div>
        </div>

        <footer class="modal-footer">
          <button type="button" class="btn-modal-cancel" @click="emit('close')">
            {{ conversionResult ? 'Done' : 'Cancel' }}
          </button>
          <button v-if="!conversionResult" type="submit" class="btn-primary-app" :disabled="isSaving">
            {{ isSaving ? 'Converting…' : 'Convert & Save' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>
