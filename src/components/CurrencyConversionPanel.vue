<script setup>
import { reactive, ref, watch } from 'vue'
import subadviseApi from '@/api/subadviseApi'
import { SUPPORTED_CURRENCIES } from '@/utils/currencies'

const form = reactive({
  amount: '',
  from: 'USD',
  to: 'EUR'
})

const result = ref(null)
const errorMessage = ref('')
const isConverting = ref(false)

watch(
  [() => form.amount, () => form.from, () => form.to],
  () => {
    result.value = null
    errorMessage.value = ''
  }
)

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

function formatRateDate(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function swapCurrencies() {
  const currentFrom = form.from
  form.from = form.to
  form.to = currentFrom
}

async function convert() {
  errorMessage.value = ''
  result.value = null
  const amount = Number(form.amount)
  if (form.amount === '' || !Number.isFinite(amount) || amount < 0) {
    errorMessage.value = 'Enter a valid amount equal to or greater than zero.'
    return
  }
  if (!form.from || !form.to) {
    errorMessage.value = 'Choose both source and target currencies.'
    return
  }

  isConverting.value = true
  try {
    result.value = await subadviseApi.convertCurrency({
      amount,
      from: form.from,
      to: form.to
    })
  } catch (error) {
    errorMessage.value = error.message || 'Currency conversion failed.'
  } finally {
    isConverting.value = false
  }
}
</script>

<template>
  <section class="dashboard-tool-card" aria-labelledby="currency-conversion-title">
    <header class="dashboard-tool-header">
      <div>
        <p class="eyebrow">EXCHANGE RATES</p>
        <h2 id="currency-conversion-title" class="dashboard-tool-title">Currency Converter</h2>
      </div>
      <span class="dashboard-tool-icon" aria-hidden="true">⇄</span>
    </header>

    <p class="dashboard-tool-description">
      Convert an amount using the API’s latest available exchange-rate snapshot.
    </p>

    <form class="dashboard-tool-form" @submit.prevent="convert">
      <div class="form-group">
        <label class="form-label" for="conversion-amount">Amount</label>
        <input
          id="conversion-amount"
          v-model="form.amount"
          class="form-input"
          type="number"
          min="0"
          step="any"
          placeholder="100"
          required
        />
      </div>

      <div class="conversion-currency-row">
        <div class="form-group">
          <label class="form-label" for="conversion-from">From</label>
          <select id="conversion-from" v-model="form.from" class="form-select">
            <option v-for="currency in SUPPORTED_CURRENCIES" :key="currency" :value="currency">{{ currency }}</option>
          </select>
        </div>
        <button
          class="currency-swap-button"
          type="button"
          @click="swapCurrencies"
          aria-label="Swap source and target currencies"
          title="Swap currencies"
        >
          ⇄
        </button>
        <div class="form-group">
          <label class="form-label" for="conversion-to">To</label>
          <select id="conversion-to" v-model="form.to" class="form-select">
            <option v-for="currency in SUPPORTED_CURRENCIES" :key="currency" :value="currency">{{ currency }}</option>
          </select>
        </div>
      </div>

      <div v-if="errorMessage" class="alert-banner alert-danger" role="alert">
        <span aria-hidden="true">⚠</span><span>{{ errorMessage }}</span>
      </div>

      <button class="btn-primary-app" type="submit" :disabled="isConverting">
        {{ isConverting ? 'Converting…' : 'Convert Amount' }}
      </button>
    </form>

    <div v-if="result" class="conversion-result" role="status" aria-live="polite">
      <p class="eyebrow">CONVERTED AMOUNT</p>
      <strong>{{ formatCurrency(result.convertedAmount, result.to) }}</strong>
      <span>{{ formatCurrency(result.amount, result.from) }} → {{ result.to }}</span>
      <small v-if="result.rateLastUpdated">Rates updated {{ formatRateDate(result.rateLastUpdated) }}</small>
      <small v-if="result.rateProvider">{{ result.rateProvider }}</small>
      <a
        v-if="result.attributionUrl"
        :href="result.attributionUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        ExchangeRate-API attribution
      </a>
    </div>

    <p class="tool-note">
      Exchange rates are cached and may update once per day. Some supported ISO currencies may not have a provider rate.
    </p>
  </section>
</template>
