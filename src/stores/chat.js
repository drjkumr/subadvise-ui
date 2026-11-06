import { defineStore } from 'pinia'
import subadviseAiApi from '@/api/subadviseAiApi'

const STORAGE_KEY_SESSIONS = 'subadvise.chatSessions'
const STORAGE_KEY_INTRO_SEEN = 'subadvise.chatIntroSeen'
const SESSION_KEY_OPEN = 'subadvise.chatOpen'

function loadSavedSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_SESSIONS)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.map((s) => ({
      sessionId: s.sessionId || s.session_id,
      name: (s.name && s.name.trim()) ? s.name.trim() : 'Untitled chat',
      createdAt: s.createdAt || s.created_at || new Date().toISOString()
    }))
  } catch {
    return []
  }
}

function saveSessions(sessions) {
  try {
    localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(sessions))
  } catch (err) {
    console.warn('Failed to save chat sessions to localStorage:', err)
  }
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    isOpen: sessionStorage.getItem(SESSION_KEY_OPEN) === 'true',
    introSeen: localStorage.getItem(STORAGE_KEY_INTRO_SEEN) === 'true',
    sessions: loadSavedSessions(),
    activeSessionId: null,
    activeSessionName: '',
    messages: [], // Array of { message_id, role, content, timestamp, error?: boolean }
    isSending: false,
    isLoadingSession: false,
    isDeletingSession: false,
    isClearingHistory: false,
    errorMessage: null,
    // Active confirm/deny prompt targeting the last AI message
    activeConfirmPrompt: null // { messageId: string }
  }),

  getters: {
    activeSession: (state) => {
      if (!state.activeSessionId) return null
      return state.sessions.find((s) => s.sessionId === state.activeSessionId) || null
    },

    displaySessionName: (state) => {
      if (!state.activeSessionName || !state.activeSessionName.trim()) {
        return 'Untitled chat'
      }
      return state.activeSessionName.trim()
    }
  },

  actions: {
    toggleOpen() {
      this.isOpen = !this.isOpen
      sessionStorage.setItem(SESSION_KEY_OPEN, String(this.isOpen))
    },

    setOpen(open) {
      this.isOpen = Boolean(open)
      sessionStorage.setItem(SESSION_KEY_OPEN, String(this.isOpen))
    },

    dismissIntroNotice() {
      this.introSeen = true
      localStorage.setItem(STORAGE_KEY_INTRO_SEEN, 'true')
    },

    startNewChat() {
      this.activeSessionId = null
      this.activeSessionName = ''
      this.messages = []
      this.errorMessage = null
      this.activeConfirmPrompt = null
    },

    async selectSession(sessionId) {
      if (this.activeSessionId === sessionId && this.messages.length > 0) return

      this.activeSessionId = sessionId
      this.activeConfirmPrompt = null
      this.errorMessage = null
      this.isLoadingSession = true

      const sessionMeta = this.sessions.find((s) => s.sessionId === sessionId)
      this.activeSessionName = sessionMeta ? sessionMeta.name : 'Untitled chat'

      try {
        const sessionData = await subadviseAiApi.getSession(sessionId)
        if (sessionData && Array.isArray(sessionData.messages)) {
          this.messages = sessionData.messages.map((m) => ({
            message_id: m.message_id || String(Date.now() + Math.random()),
            role: m.role,
            content: m.content,
            timestamp: m.timestamp || new Date().toISOString()
          }))
        } else {
          this.messages = []
        }

        // Check if metadata has a name and update if needed
        if (sessionData?.metadata?.name && (!sessionMeta || sessionMeta.name === 'Untitled chat')) {
          this.activeSessionName = sessionData.metadata.name
          if (sessionMeta) {
            sessionMeta.name = sessionData.metadata.name
            saveSessions(this.sessions)
          }
        }
      } catch (err) {
        this.errorMessage = `Could not load chat history: ${err.message}`
      } finally {
        this.isLoadingSession = false
      }
    },

    async createSession(sessionName) {
      const cleanName = (sessionName && sessionName.trim()) ? sessionName.trim() : 'Untitled chat'
      try {
        const response = await subadviseAiApi.createSession({ name: cleanName, client: 'web' })
        const sessionId = response.session_id
        const createdAt = response.created_at || new Date().toISOString()

        const newSessionRecord = {
          sessionId,
          name: cleanName,
          createdAt
        }

        this.sessions.unshift(newSessionRecord)
        saveSessions(this.sessions)

        this.activeSessionId = sessionId
        this.activeSessionName = cleanName
        this.messages = []
        this.activeConfirmPrompt = null
        this.errorMessage = null
        return newSessionRecord
      } catch (err) {
        this.errorMessage = `Failed to create chat session: ${err.message}`
        throw err
      }
    },

    async clearSessionHistory(sessionId = this.activeSessionId) {
      if (!sessionId) return false

      this.errorMessage = null
      this.isClearingHistory = true
      try {
        await subadviseAiApi.clearSessionHistory(sessionId)
        if (this.activeSessionId === sessionId) {
          this.messages = []
          this.activeConfirmPrompt = null
        }
        return true
      } catch (err) {
        this.errorMessage = `Failed to clear chat history: ${err.message}`
        return false
      } finally {
        this.isClearingHistory = false
      }
    },

    async deleteSession(sessionId) {
      if (!sessionId) return false

      this.errorMessage = null
      this.isDeletingSession = true
      try {
        await subadviseAiApi.deleteSession(sessionId)
        this.sessions = this.sessions.filter((session) => session.sessionId !== sessionId)
        saveSessions(this.sessions)

        if (this.activeSessionId === sessionId) {
          this.startNewChat()
        }
        return true
      } catch (err) {
        this.errorMessage = `Failed to delete chat session: ${err.message}`
        return false
      } finally {
        this.isDeletingSession = false
      }
    },

    async sendMessage(text, { addUserMessage = true } = {}) {
      if (!text || !text.trim()) return

      const userText = text.trim()
      this.errorMessage = null

      // If user sends any message, clear the previous confirm prompt
      this.activeConfirmPrompt = null

      // Ensure we have an active session
      if (!this.activeSessionId) {
        throw new Error('A chat session must be created before sending messages.')
      }

      if (addUserMessage) {
        this.messages.push({
          message_id: `user-${Date.now()}`,
          role: 'user',
          content: userText,
          timestamp: new Date().toISOString()
        })
      }

      this.isSending = true

      try {
        const response = await subadviseAiApi.sendMessage(this.activeSessionId, userText)
        const aiContent = response.response || ''
        const aiMessageId = `ai-${Date.now()}`

        this.messages.push({
          message_id: aiMessageId,
          role: 'assistant',
          content: aiContent,
          timestamp: new Date().toISOString()
        })

        // Check whether the response text contains the word 'confirm' (case-insensitive, whole word)
        const hasConfirmWord = /\bconfirm\b/i.test(aiContent)
        if (hasConfirmWord) {
          this.activeConfirmPrompt = {
            messageId: aiMessageId
          }
        }
      } catch (err) {
        // Show error inline in chat without losing conversation
        this.messages.push({
          message_id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Unable to get AI response: ${err.message}`,
          timestamp: new Date().toISOString(),
          error: true,
          retryPrompt: err.status === 504 || /timed out/i.test(err.message) ? userText : null
        })
      } finally {
        this.isSending = false
      }
    },

    async retryTimedOutMessage(messageId) {
      if (this.isSending) return

      const failedMessage = this.messages.find((message) => message.message_id === messageId)
      if (!failedMessage?.retryPrompt) return

      const prompt = failedMessage.retryPrompt
      this.messages = this.messages.filter((message) => message.message_id !== messageId)
      await this.sendMessage(prompt, { addUserMessage: false })
    },

    handleConfirmAction() {
      this.activeConfirmPrompt = null
      return this.sendMessage('confirm update')
    },

    handleDenyAction() {
      this.activeConfirmPrompt = null
      return this.sendMessage('cancel update')
    }
  }
})
