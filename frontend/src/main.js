import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import './assets/styles/fonts.css'
import { authState, clearAuth } from './utils/auth'

const originalFetch = window.fetch
window.fetch = async function(url, options = {}) {
  const urlStr = typeof url === 'string' ? url : url?.url || ''
  if (urlStr.startsWith('/api/') && authState.token) {
    options = { ...options }
    options.headers = { ...(options.headers || {}) }
    if (!options.headers['Authorization']) {
      options.headers['Authorization'] = `Bearer ${authState.token}`
    }
  }
  const res = await originalFetch.call(this, url, options)
  if (res.status === 401 && urlStr.startsWith('/api/') && !urlStr.includes('/api/auth/')) {
    clearAuth()
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }
  return res
}

createApp(App).use(router).mount('#app')
