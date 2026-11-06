import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'
import ExpenseToolsView from '@/views/ExpenseToolsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/expense-tools',
      name: 'expense-tools',
      component: ExpenseToolsView
    },
    {
      // Fallback redirect to main page
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

export default router
