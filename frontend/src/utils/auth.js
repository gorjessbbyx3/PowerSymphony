import { reactive } from 'vue'

const TOKEN_KEY = 'ps_auth_token'
const USER_KEY = 'ps_auth_user'

export const authState = reactive({
  user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
  token: localStorage.getItem(TOKEN_KEY) || null,
  get isAuthenticated() {
    return !!this.token
  }
})

export function setAuth(user, token) {
  authState.user = user
  authState.token = token
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  authState.user = null
  authState.token = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export async function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) }

  if (authState.token) {
    headers['Authorization'] = `Bearer ${authState.token}`
  }

  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(url, { ...options, headers })

  if (res.status === 401) {
    clearAuth()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  return res
}

export async function loginUser(email, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Login failed')
  setAuth(data.user, data.token)
  return data
}

export async function signupUser(email, password, displayName) {
  const res = await fetch('/api/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName || null })
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Signup failed')
  setAuth(data.user, data.token)
  return data
}

export async function logoutUser() {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' })
  } catch (e) {
    // ignore
  }
  clearAuth()
}
