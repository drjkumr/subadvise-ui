/**
 * API client module for SubAdvise AI API (FastAPI service).
 * Handles assistant chat, session management, and message history.
 */

const DEFAULT_BASE_URL = 'http://localhost:7072'
const BASE_URL = (import.meta.env.VITE_SUBADVISE_AI_API_URL || DEFAULT_BASE_URL).replace(/\/+$/, '')

// AI responses can take time, especially during initialization.
const AI_TIMEOUT_MS = 600000
const STANDARD_TIMEOUT_MS = 15000

/**
 * Standard fetch wrapper with custom timeout and uniform error formatting.
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const timeoutMs = options.timeoutMs || STANDARD_TIMEOUT_MS

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
      let errorMessage = `AI request failed with status ${response.status} (${response.statusText})`
      try {
        const errorData = await response.json()
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
          } else {
            errorMessage = errorData.detail
          }
        } else if (errorData.message) {
          errorMessage = errorData.message
        }
      } catch {
        // Non-JSON response
      }
      const error = new Error(errorMessage)
      error.status = response.status
      throw error
    }

    if (response.status === 204) {
      return null
    }

    return await response.json()
  } catch (err) {
    if (err.name === 'AbortError') {
      const timeoutError = new Error(
        `AI response timed out after ${timeoutMs / 1000} seconds. The backend may still be initializing local models.`
      )
      timeoutError.status = 504
      throw timeoutError
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export const subadviseAiApi = {
  baseUrl: BASE_URL,

  /**
   * Create an assistant chat session.
   * POST /api/assistant/sessions
   */
  async createSession(metadata = {}) {
    return await request('/api/assistant/sessions', {
      method: 'POST',
      body: JSON.stringify({ metadata })
    })
  },

  /**
   * Get a chat session and its full message history.
   * GET /api/assistant/sessions/{sessionId}
   */
  async getSession(sessionId) {
    return await request(`/api/assistant/sessions/${sessionId}`)
  },

  /**
   * Delete a chat session and its associated history and semantic context.
   * DELETE /api/assistant/sessions/{sessionId}
   */
  async deleteSession(sessionId) {
    return await request(`/api/assistant/sessions/${sessionId}`, {
      method: 'DELETE'
    })
  },

  /**
   * Send a message to the assistant for an active session.
   * POST /api/assistant/chat
   * Uses a 600-second timeout for slow model responses.
   */
  async sendMessage(sessionId, message) {
    return await request('/api/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        message: message
      }),
      timeoutMs: AI_TIMEOUT_MS
    })
  },

  /**
   * Clear session history if needed.
   * DELETE /api/assistant/sessions/{sessionId}/history
   */
  async clearSessionHistory(sessionId) {
    return await request(`/api/assistant/sessions/${sessionId}/history`, {
      method: 'DELETE'
    })
  }
}

export default subadviseAiApi
