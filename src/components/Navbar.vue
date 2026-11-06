<script setup>
import { useChatStore } from '@/stores/chat'
import { useThemeStore } from '@/stores/theme'

const chatStore = useChatStore()
const themeStore = useThemeStore()

const emit = defineEmits(['add-subscription', 'open-thresholds'])
</script>

<template>
  <header class="app-topbar" role="banner">
    <div class="topbar-left">
      <a class="topbar-brand" href="/" aria-label="SubAdvise home">
        <img
          src="/subadvise-logo.png"
          alt="SubAdvise to Copilot logo"
          class="brand-icon-img"
        />
        <span class="brand-title">SubAdvise</span>
      </a>
    </div>

    <div class="topbar-right">
      <!-- Dark Mode Toggle Button -->
      <button
        type="button"
        class="btn-topbar-action"
        @click="themeStore.toggleTheme"
        :title="themeStore.theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
        :aria-label="themeStore.theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
      >
        <span aria-hidden="true">{{ themeStore.theme === 'dark' ? '☀️' : '🌙' }}</span>
        <span>{{ themeStore.theme === 'dark' ? 'Light' : 'Dark' }}</span>
      </button>

      <button
        type="button"
        class="btn-topbar-action"
        @click="emit('open-thresholds')"
        title="Configure expense classification color thresholds"
      >
        <span aria-hidden="true">🎨</span>
        <span>Classification Thresholds</span>
      </button>

      <button
        type="button"
        class="btn-topbar-action btn-topbar-primary"
        @click="emit('add-subscription')"
        title="Create a new subscription"
      >
        <span aria-hidden="true">+</span>
        <span>Add Subscription</span>
      </button>

      <button
        type="button"
        class="btn-topbar-action btn-topbar-copilot"
        :class="{ 'is-active': chatStore.isOpen }"
        @click="chatStore.toggleOpen()"
        aria-label="Toggle Copilot panel"
      >
        <span aria-hidden="true">✦</span>
        <span>{{ chatStore.isOpen ? 'Copilot Open' : 'AI Copilot' }}</span>
      </button>
    </div>
  </header>
</template>
