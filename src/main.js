import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Import Template Design System styles first, then app enhancements
import './assets/template.css'
import './assets/app.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')

