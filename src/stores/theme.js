import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'subadvise.theme'

export const useThemeStore = defineStore('theme', () => {
  // Check localStorage or system preference
  const saved = localStorage.getItem(STORAGE_KEY)
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
  const initialTheme = saved || (prefersDark ? 'dark' : 'light')

  const theme = ref(initialTheme)

  function applyTheme(newTheme) {
    theme.value = newTheme
    localStorage.setItem(STORAGE_KEY, newTheme)
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
      document.documentElement.setAttribute('data-theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      document.documentElement.setAttribute('data-theme', 'light')
    }
  }

  function toggleTheme() {
    applyTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  // Initialize immediately
  applyTheme(theme.value)

  return {
    theme,
    toggleTheme,
    applyTheme
  }
})

