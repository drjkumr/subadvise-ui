/**
 * API client module for SubAdvise Backend API (Spring Boot service).
 * Handles all subscription and color threshold operations.
 */

const DEFAULT_BASE_URL = 'http://localhost:7071'
const BASE_URL = (import.meta.env.VITE_SUBADVISE_API_URL || DEFAULT_BASE_URL).replace(/\/+$/, '')

const DEFAULT_TIMEOUT_MS = 15000

/**
 * Standard fetch wrapper with timeout and uniform error formatting.
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const headers = {
      Accept: 'application/json',
      ...options.headers
    }

    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal
    })

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status} (${response.statusText})`
      try {
        const errorData = await response.json()
        if (errorData.message) {
          errorMessage = errorData.message
        } else if (errorData.detail) {
          errorMessage = errorData.detail
        } else if (typeof errorData === 'string') {
          errorMessage = errorData
        }
      } catch {
        // Response was not JSON
      }
      const error = new Error(errorMessage)
      error.status = response.status
      throw error
    }

    // 204 No Content
    if (response.status === 204) {
      return null
    }

    return await response.json()
  } catch (err) {
    if (err.name === 'AbortError') {
      const timeoutError = new Error(`Request timed out after ${timeoutMs / 1000} seconds`)
      timeoutError.status = 504
      throw timeoutError
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export const subadviseApi = {
  baseUrl: BASE_URL,

  /**
   * Retrieve all saved subscriptions.
   * GET /api/subscriptions
   */
  async getAllSubscriptions() {
    return await request('/api/subscriptions')
  },

  /**
   * Retrieve renewal totals by currency for a calendar month.
   * GET /api/subscriptions/monthly?year={year}&month={month}
   */
  async getMonthlySubscriptionTotals(year, month) {
    const query = new URLSearchParams({
      year: String(year),
      month: String(month)
    })
    return await request(`/api/subscriptions/monthly?${query}`)
  },

  /**
   * Search subscriptions by name fragment (case-insensitive).
   * GET /api/subscriptions/search?name={name}
   */
  async searchSubscriptions(name) {
    if (!name || !name.trim()) {
      return await this.getAllSubscriptions()
    }
    const query = encodeURIComponent(name.trim())
    return await request(`/api/subscriptions/search?name=${query}`)
  },

  /**
   * Get single subscription by UUID.
   * GET /api/subscriptions/{id}
   */
  async getSubscription(id) {
    return await request(`/api/subscriptions/${id}`)
  },

  /**
   * Create a new subscription record.
   * POST /api/subscriptions
   */
  async createSubscription(data) {
    return await request('/api/subscriptions', {
      method: 'POST',
      body: JSON.stringify({
        subscriptionName: data.subscriptionName,
        subscriptionDate: data.subscriptionDate,
        renewalDate: data.renewalDate,
        subscriptionPrice: Number(data.subscriptionPrice),
        currency: data.currency
      })
    })
  },

  /**
   * Partially update an existing subscription.
   * PATCH /api/subscriptions/{id}
   */
  async updateSubscription(id, data) {
    const payload = {}
    if (data.subscriptionName !== undefined) payload.subscriptionName = data.subscriptionName
    if (data.subscriptionDate !== undefined) payload.subscriptionDate = data.subscriptionDate
    if (data.renewalDate !== undefined) payload.renewalDate = data.renewalDate
    if (data.subscriptionPrice !== undefined) payload.subscriptionPrice = Number(data.subscriptionPrice)
    if (data.currency !== undefined) payload.currency = data.currency

    return await request(`/api/subscriptions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    })
  },

  /**
   * Delete a subscription by ID.
   * DELETE /api/subscriptions/{id}
   */
  async deleteSubscription(id) {
    return await request(`/api/subscriptions/${id}`, {
      method: 'DELETE'
    })
  },

  /**
   * Convert and save a subscription in another currency.
   * PATCH /api/subscriptions/{id}/convert?to={currency}
   */
  async convertSubscriptionCurrency(id, currency) {
    const query = encodeURIComponent(currency)
    return await request(`/api/subscriptions/${id}/convert?to=${query}`, {
      method: 'PATCH'
    })
  },

  /**
   * Convert an amount between currencies using the latest available rates.
   * GET /api/currency/convert?amount={amount}&from={currency}&to={currency}
   */
  async convertCurrency({ amount, from, to }) {
    const query = new URLSearchParams({
      amount: String(amount),
      from,
      to
    })
    return await request(`/api/currency/convert?${query}`)
  },

  /**
   * Create a target amount and date period.
   * POST /api/expenses/targets
   */
  async createExpenseTarget(data) {
    return await request('/api/expenses/targets', {
      method: 'POST',
      body: JSON.stringify({
        targetExpense: Number(data.targetExpense),
        currency: data.currency,
        ...(data.startDate ? { startDate: data.startDate } : {}),
        endDate: data.endDate
      })
    })
  },

  /**
   * Record an actual expense against an existing target.
   * POST /api/expenses
   */
  async createExpense(data) {
    return await request('/api/expenses', {
      method: 'POST',
      body: JSON.stringify({
        actualExpense: Number(data.actualExpense),
        currency: data.currency,
        targetId: data.targetId
      })
    })
  },

  /**
   * Retrieve the expense report for a calendar month.
   * GET /api/expenses/monthly?year={year}&month={month}
   */
  async getMonthlyExpenses(year, month) {
    const query = new URLSearchParams({
      year: String(year),
      month: String(month)
    })
    return await request(`/api/expenses/monthly?${query}`)
  },

  /**
   * Get configured application-wide color thresholds.
   * GET /api/expenses/color-thresholds
   */
  async getColorThresholds() {
    return await request('/api/expenses/color-thresholds')
  },

  /**
   * Update application-wide color thresholds.
   * PUT /api/expenses/color-thresholds
   */
  async updateColorThresholds(thresholds) {
    return await request('/api/expenses/color-thresholds', {
      method: 'PUT',
      body: JSON.stringify({
        red: Number(thresholds.red),
        orange: Number(thresholds.orange),
        yellow: Number(thresholds.yellow),
        lime: Number(thresholds.lime),
        green: Number(thresholds.green)
      })
    })
  }
}

export default subadviseApi
