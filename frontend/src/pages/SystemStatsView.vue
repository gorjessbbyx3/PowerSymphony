<template>
  <div class="system-stats-view">
    <div class="header">
      <h1>System Status</h1>
      <div class="header-actions">
        <button class="btn btn-ghost" :class="{ spinning: loading }" @click="loadStats">
          <span class="icon">↻</span> Refresh
        </button>
        <button class="btn btn-warning" @click="clearCache" :disabled="clearing">
          {{ clearing ? 'Clearing…' : 'Clear LLM Cache' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div class="stats-grid" v-if="stats">
      <!-- Health checks -->
      <section class="card">
        <h2>Health Checks</h2>
        <div v-if="health" class="check-list">
          <div
            v-for="(val, key) in health.checks"
            :key="key"
            class="check-row"
            :class="checkStatus(val)"
          >
            <span class="check-key">{{ key }}</span>
            <span class="check-val">{{ formatCheck(val) }}</span>
          </div>
        </div>
        <div v-else class="placeholder">Loading…</div>
      </section>

      <!-- LLM Cache -->
      <section class="card">
        <h2>LLM Response Cache</h2>
        <div v-if="stats.llm_cache" class="metric-list">
          <div class="metric" v-for="(val, key) in stats.llm_cache" :key="key">
            <span class="metric-key">{{ formatKey(key) }}</span>
            <span class="metric-val">{{ val }}</span>
          </div>
        </div>
      </section>

      <!-- Sessions -->
      <section class="card">
        <h2>Sessions</h2>
        <div v-if="stats.sessions" class="metric-list">
          <div class="metric">
            <span class="metric-key">Active</span>
            <span class="metric-val">{{ stats.sessions.active }}</span>
          </div>
          <div class="metric">
            <span class="metric-key">Historical (disk)</span>
            <span class="metric-val">{{ stats.sessions.historical }}</span>
          </div>
          <template v-if="stats.sessions.by_status">
            <div
              class="metric"
              v-for="(count, status) in stats.sessions.by_status"
              :key="status"
            >
              <span class="metric-key status-badge" :class="status">{{ status }}</span>
              <span class="metric-val">{{ count }}</span>
            </div>
          </template>
        </div>
      </section>

      <!-- Config -->
      <section class="card">
        <h2>Configuration</h2>
        <div v-if="stats.config" class="metric-list">
          <div class="metric" v-for="(val, key) in stats.config" :key="key">
            <span class="metric-key">{{ formatKey(key) }}</span>
            <span class="metric-val">{{ val }}</span>
          </div>
        </div>
      </section>

      <!-- Providers -->
      <section class="card">
        <h2>AI Providers</h2>
        <div v-if="stats.providers && stats.providers.length" class="provider-list">
          <span class="provider-tag" v-for="p in stats.providers" :key="p">{{ p }}</span>
        </div>
        <div v-else class="placeholder">None registered</div>
      </section>

      <!-- Browser Extension -->
      <section class="card">
        <h2>Browser Extension</h2>
        <div class="metric-list">
          <div class="metric">
            <span class="metric-key">Connected sessions</span>
            <span class="metric-val">{{ stats.browser_sessions ?? 0 }}</span>
          </div>
        </div>
        <p class="hint">Load the extension from <code>browser-extension/</code> in Chrome dev mode.</p>
      </section>
    </div>

    <!-- Session history -->
    <section class="card history-card" v-if="history && Object.keys(history).length">
      <h2>Past Sessions (disk)</h2>
      <table class="history-table">
        <thead>
          <tr>
            <th>Session ID</th>
            <th>Workflow</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, id) in history" :key="id">
            <td class="session-id">{{ id.slice(0, 12) }}…</td>
            <td>{{ s.yaml_file }}</td>
            <td>
              <span class="status-badge" :class="s.status">{{ s.status }}</span>
            </td>
            <td>{{ formatDate(s.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const stats = ref(null)
const health = ref(null)
const history = ref(null)
const loading = ref(false)
const clearing = ref(false)
const error = ref(null)

async function loadStats() {
  loading.value = true
  error.value = null
  try {
    const [statsRes, healthRes] = await Promise.all([
      fetch('/api/system/stats'),
      fetch('/api/system/health/detailed'),
    ])
    stats.value = await statsRes.json()
    health.value = await healthRes.json()
    const sessRes = await fetch('/api/sessions')
    if (sessRes.ok) {
      const sessData = await sessRes.json()
      history.value = sessData.historical || null
    }
  } catch (err) {
    error.value = `Failed to load stats: ${err.message}`
  } finally {
    loading.value = false
  }
}

async function clearCache() {
  clearing.value = true
  try {
    const res = await fetch('/api/system/cache/clear', { method: 'POST' })
    const data = await res.json()
    if (data.ok) {
      await loadStats()
    } else {
      error.value = `Cache clear failed: ${data.error}`
    }
  } catch (err) {
    error.value = `Cache clear error: ${err.message}`
  } finally {
    clearing.value = false
  }
}

function formatKey(key) {
  return key.replace(/_/g, ' ')
}

function formatCheck(val) {
  if (typeof val === 'string') return val
  if (val?.status) return val.status + (val.available ? ` (${val.available.join(', ')})` : '') + (val.count != null ? ` — ${val.count} files` : '')
  return JSON.stringify(val)
}

function checkStatus(val) {
  const s = typeof val === 'string' ? val : val?.status
  if (s === 'ok') return 'ok'
  if (s?.startsWith('error')) return 'error'
  return ''
}

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString()
}

onMounted(loadStats)
</script>

<style scoped>
.system-stats-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-ghost {
  background: transparent;
  border-color: var(--border-color, #ddd);
}

.btn-warning {
  background: #f59e0b;
  color: white;
  border-color: #d97706;
}

.btn-warning:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinning .icon {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-banner {
  background: #fee2e2;
  color: #b91c1c;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.card {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
  padding: 20px;
}

.card h2 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 14px;
  color: var(--text-secondary, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.75rem;
}

.metric-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
}

.metric-key {
  color: var(--text-secondary, #6b7280);
  text-transform: capitalize;
}

.metric-val {
  font-weight: 500;
  font-family: monospace;
}

.check-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.check-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.875rem;
}

.check-row.ok {
  background: #d1fae5;
  color: #065f46;
}

.check-row.error {
  background: #fee2e2;
  color: #991b1b;
}

.check-key {
  font-weight: 500;
  text-transform: capitalize;
}

.provider-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.provider-tag {
  background: var(--accent-bg, #eff6ff);
  color: var(--accent, #2563eb);
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
}

.hint {
  margin-top: 10px;
  font-size: 0.8rem;
  color: var(--text-secondary, #9ca3af);
}

code {
  background: var(--code-bg, #f3f4f6);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.8rem;
}

.history-card {
  overflow-x: auto;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.history-table th {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 2px solid var(--border-color, #e5e7eb);
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: 0.05em;
}

.history-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color, #f3f4f6);
}

.session-id {
  font-family: monospace;
  font-size: 0.8rem;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-badge.completed { background: #d1fae5; color: #065f46; }
.status-badge.running { background: #dbeafe; color: #1d4ed8; }
.status-badge.error { background: #fee2e2; color: #991b1b; }
.status-badge.cancelled { background: #f3f4f6; color: #6b7280; }
.status-badge.waiting_for_input { background: #fef3c7; color: #92400e; }

.placeholder {
  color: var(--text-secondary, #9ca3af);
  font-size: 0.875rem;
}
</style>
