<script setup>
import { useChatStore } from '@/stores/chat'
import { useThemeStore } from '@/stores/theme'
import AiChatSidebar from '@/components/AiChatSidebar.vue'
import ExpenseTargetsPanel from '@/components/ExpenseTargetsPanel.vue'
import CurrencyConversionPanel from '@/components/CurrencyConversionPanel.vue'

const chatStore = useChatStore()
const themeStore = useThemeStore()
</script>

<template>
  <div class="app-container">
    <header class="app-topbar" role="banner">
      <div class="topbar-left">
        <router-link class="topbar-brand" to="/" aria-label="SubAdvise dashboard">
          <img
            src="/subadvise-logo.png"
            alt="SubAdvise to Copilot logo"
            class="brand-icon-img"
          />
          <span class="brand-title">SubAdvise</span>
        </router-link>
      </div>

      <div class="topbar-right">
        <router-link class="btn-topbar-action" to="/">
          <span aria-hidden="true">⌂</span>
          <span>Subscriptions</span>
        </router-link>
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

    <div class="app-body">
      <nav class="app-sidebar" aria-label="Application Navigation">
        <div>
          <div class="sidebar-heading">Navigation</div>
          <div class="sidebar-nav-list">
            <router-link class="sidebar-nav-item" to="/">
              <div class="nav-item-left">
                <span class="nav-icon" aria-hidden="true">⌂</span>
                <span>Subscriptions</span>
              </div>
            </router-link>
            <router-link class="sidebar-nav-item is-active" to="/expense-tools" aria-current="page">
              <div class="nav-item-left">
                <span class="nav-icon" aria-hidden="true">⇄</span>
                <span>Targets & Currency</span>
              </div>
            </router-link>
            <button
              type="button"
              class="sidebar-nav-item"
              :class="{ 'is-active': chatStore.isOpen }"
              @click="chatStore.setOpen(!chatStore.isOpen)"
            >
              <div class="nav-item-left">
                <span class="nav-icon" aria-hidden="true">✦</span>
                <span>AI Copilot</span>
              </div>
            </button>
          </div>
        </div>
      </nav>

      <main class="app-main-canvas" role="main">
        <div class="canvas-header">
          <div class="canvas-title-group">
            <h1>Targets & Currency</h1>
            <p>Set expense budgets, track spending, and convert currencies.</p>
          </div>
        </div>

        <div class="dashboard-tools-grid">
          <ExpenseTargetsPanel />
          <CurrencyConversionPanel />
        </div>
      </main>

      <AiChatSidebar />
    </div>
  </div>
</template>
