import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import errorTracker from './services/errorTracker'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

// Initialize error tracking
errorTracker.init(app)

// Use Pinia for state management
app.use(pinia)

// Initialize auth store and check if user is already logged in
const authStore = useAuthStore()
authStore.initialize().then(() => {
  // Track route changes for error context
  router.afterEach((to) => {
    errorTracker.setRoute(to)
  })

  app.use(router)
  app.mount('#app')
})
