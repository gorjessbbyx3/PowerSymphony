<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">PowerSymphony</h1>
      <p class="auth-subtitle">Sign in to your account</p>

      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="you@example.com"
            required
            autocomplete="email"
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Your password"
            required
            autocomplete="current-password"
          />
        </div>

        <p v-if="error" class="auth-error">{{ error }}</p>

        <button type="submit" class="auth-btn" :disabled="loading">
          {{ loading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>

      <p class="auth-switch">
        Don't have an account?
        <router-link to="/signup">Create one</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser } from '../utils/auth'

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await loginUser(email.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
}

.auth-card {
  background: #1c2333;
  border: 1px solid #2d3748;
  border-radius: 16px;
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.auth-title {
  font-size: 28px;
  font-weight: 700;
  text-align: center;
  margin: 0 0 8px;
  background: linear-gradient(90deg, #aaffcd, #99eaf9, #a0c4ff);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-family: 'Inter', sans-serif;
}

.auth-subtitle {
  text-align: center;
  color: #8b949e;
  margin: 0 0 32px;
  font-size: 15px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  color: #c9d1d9;
  font-size: 14px;
  font-weight: 500;
}

.form-group input {
  padding: 12px 14px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  color: #e6edf3;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input:focus {
  border-color: #58a6ff;
}

.form-group input::placeholder {
  color: #484f58;
}

.auth-error {
  color: #f85149;
  font-size: 14px;
  margin: 0;
  padding: 8px 12px;
  background: rgba(248, 81, 73, 0.1);
  border-radius: 6px;
}

.auth-btn {
  padding: 12px;
  background: linear-gradient(135deg, #aaffcd, #99eaf9);
  color: #0d1117;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.auth-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.auth-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-switch {
  text-align: center;
  color: #8b949e;
  font-size: 14px;
  margin-top: 24px;
}

.auth-switch a {
  color: #58a6ff;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
