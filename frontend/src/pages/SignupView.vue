<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">PowerSymphony</h1>
      <p class="auth-subtitle">Create your account</p>

      <form @submit.prevent="handleSignup" class="auth-form">
        <div class="form-group">
          <label for="displayName">Display Name (optional)</label>
          <input
            id="displayName"
            v-model="displayName"
            type="text"
            placeholder="Your name"
            autocomplete="name"
          />
        </div>

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
            placeholder="At least 6 characters"
            required
            minlength="6"
            autocomplete="new-password"
          />
        </div>

        <p v-if="error" class="auth-error">{{ error }}</p>

        <button type="submit" class="auth-btn" :disabled="loading">
          {{ loading ? 'Creating account...' : 'Create Account' }}
        </button>
      </form>

      <p class="auth-switch">
        Already have an account?
        <router-link to="/login">Sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { signupUser } from '../utils/auth'

const router = useRouter()
const displayName = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSignup() {
  error.value = ''
  loading.value = true
  try {
    await signupUser(email.value, password.value, displayName.value)
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
  background: #0a0e17;
}

.auth-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 20px;
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 8px 48px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
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
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
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
