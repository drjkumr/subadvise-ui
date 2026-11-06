import { defineStore } from 'pinia'
import subadviseApi from '@/api/subadviseApi'

export const useSubscriptionStore = defineStore('subscriptions', {
  state: () => ({
    subscriptions: [],
    isLoading: false,
    error: null,
    monthlySubscriptionTotals: null,
    isMonthlySubscriptionTotalsLoading: false,
    monthlySubscriptionTotalsError: null,
    apiStatus: 'idle', // 'idle' | 'syncing' | 'connected' | 'error'
    lastSyncedAt: null,
    searchQuery: '',
    selectedColorFilter: 'ALL',
    sortBy: 'renewal-asc',
    currentPage: 1,
    pageSize: 50,
    thresholds: {
      red: 50,
      orange: 30,
      yellow: 15,
      lime: 5,
      green: 0
    },
    isThresholdsLoading: false,
    thresholdsError: null
  }),

  getters: {
    colorDistribution: (state) => {
      const counts = { red: 0, orange: 0, yellow: 0, lime: 0, green: 0, other: 0 }
      for (const s of state.subscriptions) {
        const c = (s.color || '').toLowerCase()
        if (counts[c] !== undefined) {
          counts[c]++
        } else {
          counts.other++
        }
      }
      return counts
    },

    upcomingRenewals: (state) => {
      const now = new Date()
      const in30Days = new Date()
      in30Days.setDate(in30Days.getDate() + 30)

      return state.subscriptions.filter((s) => {
        if (!s.renewalDate) return false
        const d = new Date(s.renewalDate)
        return d >= now && d <= in30Days
      })
    },

    filteredSubscriptions: (state) => {
      let result = [...state.subscriptions]

      // Filter by color level if selected
      if (state.selectedColorFilter && state.selectedColorFilter !== 'ALL') {
        const filterColor = state.selectedColorFilter.toLowerCase()
        result = result.filter((s) => (s.color || '').toLowerCase() === filterColor)
      }

      // Sort
      result.sort((a, b) => {
        if (state.sortBy === 'name-asc') {
          return (a.subscriptionName || '').localeCompare(b.subscriptionName || '')
        }
        if (state.sortBy === 'name-desc') {
          return (b.subscriptionName || '').localeCompare(a.subscriptionName || '')
        }
        if (state.sortBy === 'price-desc') {
          return (Number(b.subscriptionPrice) || 0) - (Number(a.subscriptionPrice) || 0)
        }
        if (state.sortBy === 'price-asc') {
          return (Number(a.subscriptionPrice) || 0) - (Number(b.subscriptionPrice) || 0)
        }
        if (state.sortBy === 'renewal-asc') {
          return new Date(a.renewalDate || 0) - new Date(b.renewalDate || 0)
        }
        if (state.sortBy === 'renewal-desc') {
          return new Date(b.renewalDate || 0) - new Date(a.renewalDate || 0)
        }
        return 0
      })

      return result
    },

    totalCount: (state) => state.filteredSubscriptions.length,
    rawTotalCount: (state) => state.subscriptions.length,

    totalPages(state) {
      const total = this.totalCount
      return Math.max(1, Math.ceil(total / state.pageSize))
    },

    paginatedSubscriptions(state) {
      const start = (state.currentPage - 1) * state.pageSize
      const end = start + state.pageSize
      return this.filteredSubscriptions.slice(start, end)
    },

    rangeText(state) {
      const total = this.totalCount
      if (total === 0) return '0 of 0'
      const start = (state.currentPage - 1) * state.pageSize + 1
      const end = Math.min(start + state.pageSize - 1, total)
      return `${start}–${end} of ${total}`
    }
  },

  actions: {
    async fetchSubscriptions() {
      this.isLoading = true
      this.apiStatus = 'syncing'
      this.error = null
      try {
        let data
        if (this.searchQuery && this.searchQuery.trim()) {
          data = await subadviseApi.searchSubscriptions(this.searchQuery.trim())
        } else {
          data = await subadviseApi.getAllSubscriptions()
        }
        this.subscriptions = Array.isArray(data) ? data : []
        this.apiStatus = 'connected'
        this.lastSyncedAt = new Date()
        if (this.currentPage > this.totalPages) {
          this.currentPage = this.totalPages
        }
        void this.fetchMonthlySubscriptionTotals()
      } catch (err) {
        this.error = err.message || 'Failed to load subscriptions'
        this.apiStatus = 'error'
        this.subscriptions = []
      } finally {
        this.isLoading = false
      }
    },

    async fetchMonthlySubscriptionTotals() {
      const now = new Date()
      this.isMonthlySubscriptionTotalsLoading = true
      this.monthlySubscriptionTotalsError = null
      try {
        this.monthlySubscriptionTotals = await subadviseApi.getMonthlySubscriptionTotals(
          now.getFullYear(),
          now.getMonth() + 1
        )
      } catch (err) {
        this.monthlySubscriptionTotals = null
        this.monthlySubscriptionTotalsError = err.message || "Failed to load this month's subscription total."
      } finally {
        this.isMonthlySubscriptionTotalsLoading = false
      }
    },

    setSearchQuery(query) {
      this.searchQuery = query
      this.currentPage = 1
      return this.fetchSubscriptions()
    },

    setColorFilter(color) {
      this.selectedColorFilter = color
      this.currentPage = 1
    },

    setSortBy(sort) {
      this.sortBy = sort
      this.currentPage = 1
    },

    setPage(page) {
      if (page >= 1 && page <= this.totalPages) {
        this.currentPage = page
      }
    },

    nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++
      }
    },

    prevPage() {
      if (this.currentPage > 1) {
        this.currentPage--
      }
    },

    async createSubscription(formData) {
      this.isLoading = true
      this.error = null
      try {
        const created = await subadviseApi.createSubscription(formData)
        await this.fetchSubscriptions()
        return created
      } catch (err) {
        this.error = err.message || 'Failed to create subscription'
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async updateSubscription(id, formData) {
      this.isLoading = true
      this.error = null
      try {
        const updated = await subadviseApi.updateSubscription(id, formData)
        await this.fetchSubscriptions()
        return updated
      } catch (err) {
        this.error = err.message || 'Failed to update subscription'
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async deleteSubscription(id) {
      this.isLoading = true
      this.error = null
      try {
        await subadviseApi.deleteSubscription(id)
        const remainingTotal = this.subscriptions.length - 1
        const maxPage = Math.max(1, Math.ceil(remainingTotal / this.pageSize))
        if (this.currentPage > maxPage) {
          this.currentPage = maxPage
        }
        await this.fetchSubscriptions()
      } catch (err) {
        this.error = err.message || 'Failed to delete subscription'
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async convertSubscriptionCurrency(id, currency) {
      this.isLoading = true
      this.error = null
      try {
        const conversion = await subadviseApi.convertSubscriptionCurrency(id, currency)
        await this.fetchSubscriptions()
        return conversion
      } catch (err) {
        this.error = err.message || 'Failed to convert subscription currency'
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async fetchThresholds() {
      this.isThresholdsLoading = true
      this.thresholdsError = null
      try {
        const data = await subadviseApi.getColorThresholds()
        if (data && typeof data === 'object') {
          this.thresholds = {
            red: data.red ?? 50,
            orange: data.orange ?? 30,
            yellow: data.yellow ?? 15,
            lime: data.lime ?? 5,
            green: data.green ?? 0
          }
        }
      } catch (err) {
        this.thresholdsError = err.message || 'Could not load thresholds from server; using defaults.'
      } finally {
        this.isThresholdsLoading = false
      }
    },

    async updateThresholds(newThresholds) {
      this.isThresholdsLoading = true
      this.thresholdsError = null
      try {
        const updated = await subadviseApi.updateColorThresholds(newThresholds)
        this.thresholds = updated || newThresholds
        await this.fetchSubscriptions()
        return this.thresholds
      } catch (err) {
        this.thresholdsError = err.message || 'Failed to save color thresholds'
        throw err
      } finally {
        this.isThresholdsLoading = false
      }
    }
  }
})
