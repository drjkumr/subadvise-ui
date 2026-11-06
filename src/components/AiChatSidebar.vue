<script setup>
import { ref, watch, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const markdown = new MarkdownIt({
  breaks: true,
  html: false,
  linkify: true
})

const messageInput = ref('')
const newSessionNameInput = ref('')
const showSessionsDrawer = ref(false)
const chatMessagesContainer = ref(null)
const isCreatingSession = ref(false)
const sessionCreationError = ref(null)

const starterPrompts = [
  'Which subscriptions renew in the next 30 days?',
  'Which subscriptions are classified in the Red tier?',
  'Summarize my total monthly subscription spending',
  'Convert my Netflix subscription to EUR'
]

// Auto-scroll chat to bottom when messages change
watch(
  () => chatStore.messages.length,
  () => {
    scrollToBottom()
  }
)

watch(
  () => chatStore.isSending,
  () => {
    scrollToBottom()
  }
)

function scrollToBottom() {
  nextTick(() => {
    if (chatMessagesContainer.value) {
      chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight
    }
  })
}

async function handleStartSession() {
  const name = newSessionNameInput.value.trim() || 'Untitled chat'
  isCreatingSession.value = true
  sessionCreationError.value = null

  try {
    await chatStore.createSession(name)
    newSessionNameInput.value = ''
    showSessionsDrawer.value = false
    scrollToBottom()
  } catch (err) {
    sessionCreationError.value = err.message || 'Failed to initialize chat session'
  } finally {
    isCreatingSession.value = false
  }
}

async function handleSendMessage(overrideText = null) {
  const text = (overrideText || messageInput.value).trim()
  if (!text || chatStore.isSending) return

  // If there's no session yet, auto-create one first
  if (!chatStore.activeSessionId) {
    const sessionName = newSessionNameInput.value.trim() || text.slice(0, 30) || 'Untitled chat'
    try {
      await chatStore.createSession(sessionName)
    } catch {
      return
    }
  }

  if (!overrideText) {
    messageInput.value = ''
  }
  await chatStore.sendMessage(text)
  scrollToBottom()
}

function handleConfirm() {
  chatStore.handleConfirmAction()
  scrollToBottom()
}

function handleDeny() {
  chatStore.handleDenyAction()
  scrollToBottom()
}

function selectPastSession(sessionId) {
  chatStore.selectSession(sessionId)
  showSessionsDrawer.value = false
  scrollToBottom()
}

async function handleClearHistory() {
  if (!window.confirm('Clear the messages in this chat? This cannot be undone.')) return
  await chatStore.clearSessionHistory()
}

async function handleDeleteSession(sessionId, sessionName) {
  if (chatStore.isSending) return
  if (!window.confirm(`Delete "${sessionName}" and all of its history? This cannot be undone.`)) return
  await chatStore.deleteSession(sessionId)
}

function handleNewChat() {
  chatStore.startNewChat()
  showSessionsDrawer.value = false
}

function formatMessageTime(isoString) {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function renderMarkdown(content) {
  return markdown.render(content || '')
}
</script>

<template>
  <aside
    v-if="chatStore.isOpen"
    id="ai-copilot-dock"
    class="app-copilot-dock"
    role="complementary"
    aria-label="SubAdvise AI Copilot Dock"
  >
    <!-- Dock Header -->
    <header class="copilot-dock-header">
      <div class="copilot-dock-title">
        <span class="copilot-badge-icon" aria-hidden="true">✦</span>
        <span>AI Copilot</span>
        <span class="copilot-tag-pill" style="font-size: 0.6rem;">
          Groq
        </span>
      </div>

      <div style="display: flex; align-items: center; gap: 0.4rem;">
        <button
          type="button"
          class="btn-row-action"
          style="padding: 0.25rem 0.55rem; font-size: 0.7rem;"
          @click="showSessionsDrawer = !showSessionsDrawer"
          :title="showSessionsDrawer ? 'Hide sessions' : 'View past sessions'"
          aria-label="Toggle sessions menu"
        >
          <span>Sessions ({{ chatStore.sessions.length }})</span>
        </button>

        <button
          type="button"
          class="modal-close-btn"
          style="width: 28px; height: 28px; display: grid; place-items: center;"
          @click="chatStore.setOpen(false)"
          aria-label="Close Copilot dock"
        >
          &times;
        </button>
      </div>
    </header>

    <!-- Sessions Drawer (List of past chat sessions) -->
    <div v-if="showSessionsDrawer" class="copilot-sessions-panel">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
        <span style="font-size: 0.7rem; font-weight: 800; color: var(--ink-muted); text-transform: uppercase;">
          Saved Conversations
        </span>
        <button
          type="button"
          class="btn-primary-app"
          style="padding: 0.2rem 0.55rem; font-size: 0.68rem;"
          @click="handleNewChat"
        >
          + New Chat
        </button>
      </div>

      <div v-if="chatStore.sessions.length === 0" style="padding: 0.5rem; text-align: center; font-size: 0.74rem; color: var(--ink-muted);">
        No saved sessions yet.
      </div>

      <div v-else class="copilot-session-list">
        <div
          v-for="s in chatStore.sessions"
          :key="s.sessionId"
          class="copilot-session-row"
        >
          <button
            type="button"
            class="copilot-session-select sidebar-nav-item"
            :class="{ 'is-active': s.sessionId === chatStore.activeSessionId }"
            :disabled="chatStore.isDeletingSession || chatStore.isSending"
            @click="selectPastSession(s.sessionId)"
          >
            <span class="copilot-session-name">{{ s.name || 'Untitled chat' }}</span>
            <span class="copilot-session-created">{{ formatMessageTime(s.createdAt) }}</span>
          </button>
          <button
            type="button"
            class="copilot-session-delete"
            :disabled="chatStore.isDeletingSession || chatStore.isSending"
            :aria-label="`Delete ${s.name || 'Untitled chat'}`"
            title="Delete session"
            @click="handleDeleteSession(s.sessionId, s.name || 'Untitled chat')"
          >
            &times;
          </button>
        </div>
      </div>
    </div>

    <div v-if="chatStore.errorMessage" class="copilot-action-error" role="alert">
      {{ chatStore.errorMessage }}
    </div>

    <!-- Active Session Bar -->
    <div class="copilot-session-bar">
      <div style="display: flex; align-items: center; gap: 0.4rem; overflow: hidden;">
        <span aria-hidden="true" style="color: var(--purple-primary);">💬</span>
        <span style="font-weight: 700; color: var(--ink-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="chatStore.displaySessionName">
          {{ chatStore.activeSessionId ? chatStore.displaySessionName : 'No active session' }}
        </span>
      </div>

      <div v-if="chatStore.activeSessionId" class="copilot-session-actions">
        <button
          type="button"
          class="copilot-session-action"
          :disabled="chatStore.isClearingHistory || chatStore.isSending"
          @click="handleClearHistory"
        >
          {{ chatStore.isClearingHistory ? 'Clearing...' : 'Clear history' }}
        </button>
        <button
          type="button"
          class="copilot-session-action"
          @click="handleNewChat"
        >
          + New
        </button>
      </div>
    </div>

    <!-- First-Use Expectation Notice (Shown once per browser before chat) -->
    <div v-if="!chatStore.introSeen" class="copilot-messages-area" style="justify-content: center;">
      <div class="copilot-panel-box">
        <span class="copilot-tag-pill">
          FIRST-TIME NOTICE
        </span>
        <h4 class="copilot-panel-title">
          Initializing Local AI Models
        </h4>
        <p class="copilot-panel-text" style="color: var(--ink-secondary);">
          AI responses can take a little time, especially on first use, because the backend is initializing the local AI chat and session storage.
        </p>
        <p class="copilot-panel-text" style="margin-bottom: 1rem;">
          Please be patient and avoid resending messages while waiting.
        </p>
        <button
          type="button"
          class="btn-primary-app"
          style="width: 100%; justify-content: center; padding: 0.5rem;"
          @click="chatStore.dismissIntroNotice"
        >
          Got it
        </button>
      </div>
    </div>

    <!-- Session Creation Step (Before first message is sent in a new chat) -->
    <div
      v-else-if="!chatStore.activeSessionId"
      class="copilot-messages-area"
      style="justify-content: center;"
    >
      <div class="copilot-panel-box">
        <span class="copilot-tag-pill">
          NEW CONVERSATION
        </span>
        <h4 class="copilot-panel-title">
          Name this conversation
        </h4>
        <p class="copilot-panel-text">
          Enter a session name before sending your first message.
        </p>

        <form @submit.prevent="handleStartSession" style="display: flex; flex-direction: column; gap: 0.65rem;">
          <input
            v-model="newSessionNameInput"
            type="text"
            class="form-input"
            placeholder="e.g. Q1 Subscription Audit"
            aria-label="Chat session name"
            required
            :disabled="isCreatingSession"
          />

          <div v-if="sessionCreationError" class="alert-banner alert-danger" style="margin-bottom: 0;">
            <span>{{ sessionCreationError }}</span>
          </div>

          <button
            type="submit"
            class="btn-primary-app"
            style="width: 100%; justify-content: center; padding: 0.55rem;"
            :disabled="isCreatingSession"
          >
            <span v-if="isCreatingSession">Initializing session...</span>
            <span v-else>Start Chat ✦</span>
          </button>
        </form>
      </div>
    </div>

    <!-- Active Chat Messages Flow -->
    <div
      v-else
      ref="chatMessagesContainer"
      class="copilot-messages-area"
      role="log"
      aria-live="polite"
    >
      <!-- Session Loading Spinner -->
      <div v-if="chatStore.isLoadingSession" class="state-box" style="padding: 1.5rem 0;">
        <div class="spinner"></div>
        <p style="font-size: 0.75rem; color: var(--ink-muted); margin-top: 0.5rem;">Loading chat history...</p>
      </div>

      <!-- Empty Messages State with Starter Prompts -->
      <div
        v-else-if="chatStore.messages.length === 0"
        style="margin: auto 0; padding: 0.5rem 0;"
      >
        <div style="text-align: center; margin-bottom: 1rem;">
          <span style="font-size: 1.8rem;" aria-hidden="true">🤖</span>
          <h4 style="margin: 0.25rem 0 0.15rem; font-size: 0.95rem; color: var(--ink-primary); font-weight: 800;">
            SubAdvise Copilot Ready
          </h4>
          <p style="margin: 0; font-size: 0.75rem; color: var(--ink-muted);">
            Ask questions about renewal schedules, expenses, or currency conversions.
          </p>
        </div>

        <div style="display: flex; flex-direction: column; gap: 0.4rem;">
          <span style="font-size: 0.65rem; font-weight: 800; color: var(--ink-muted); text-transform: uppercase;">
            Suggested prompts:
          </span>
          <button
            v-for="prompt in starterPrompts"
            :key="prompt"
            type="button"
            class="copilot-prompt-pill"
            @click="handleSendMessage(prompt)"
          >
            <span>{{ prompt }}</span>
            <span style="color: var(--purple-primary); font-weight: 700;">→</span>
          </button>
        </div>
      </div>

      <!-- Messages Stream -->
      <template v-else>
        <div
          v-for="msg in chatStore.messages"
          :key="msg.message_id"
          class="msg-bubble-app"
          :class="{
            'msg-user-app': msg.role === 'user',
            'msg-ai-app': msg.role !== 'user',
            'is-error': msg.error
          }"
        >
          <div
            v-if="msg.role === 'user'"
            class="msg-content"
            style="white-space: pre-wrap;"
          >{{ msg.content }}</div>
          <div
            v-else
            class="msg-content msg-markdown"
            v-html="renderMarkdown(msg.content)"
          ></div>
          <div class="msg-time-app">
            {{ formatMessageTime(msg.timestamp) }}
          </div>
          <button
            v-if="msg.retryPrompt"
            type="button"
            class="msg-retry-app"
            :disabled="chatStore.isSending"
            @click="chatStore.retryTimedOutMessage(msg.message_id)"
          >
            Try again
          </button>

          <!-- Confirm and Deny Buttons (Triggered when AI response contains whole word 'confirm') -->
          <div
            v-if="chatStore.activeConfirmPrompt?.messageId === msg.message_id && !chatStore.isSending"
            class="confirm-deny-app-row"
          >
            <button
              type="button"
              class="btn-confirm-app"
              @click="handleConfirm"
              aria-label="Confirm proposal"
            >
              ✓ Confirm
            </button>
            <button
              type="button"
              class="btn-deny-app"
              @click="handleDeny"
              aria-label="Deny proposal"
            >
              ✕ Deny
            </button>
          </div>
        </div>

        <!-- Waiting / Typing indicator -->
        <div v-if="chatStore.isSending" class="copilot-typing-box">
          <div style="display: flex; gap: 0.3rem; align-items: center; margin-bottom: 0.25rem;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--purple-primary);"></span>
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--purple-primary);"></span>
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--purple-primary);"></span>
          </div>
          <p style="margin: 0; font-size: 0.7rem; color: var(--ink-muted); font-style: italic;">
            AI is thinking... responses may take up to 10 minutes on first run.
          </p>
        </div>
      </template>
    </div>

    <!-- Input Footer Bar -->
    <footer
      v-if="chatStore.introSeen && chatStore.activeSessionId"
      class="copilot-input-bar"
    >
      <form
        style="width: 100%; display: flex; gap: 0.5rem;"
        @submit.prevent="handleSendMessage()"
      >
        <input
          v-model="messageInput"
          type="text"
          class="copilot-text-input"
          placeholder="Ask a question or command..."
          aria-label="Type message to SubAdvise Copilot"
          :disabled="chatStore.isSending"
        />
        <button
          type="submit"
          class="copilot-send-btn"
          :disabled="!messageInput.trim() || chatStore.isSending"
          title="Send message"
          aria-label="Send message"
        >
          ➤
        </button>
      </form>
    </footer>
  </aside>
</template>
