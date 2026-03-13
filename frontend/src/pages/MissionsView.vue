<template>
  <div class="missions-page">
    <div v-if="!showCreate" class="missions-container">
      <div class="missions-header">
        <div>
          <h1 class="page-title">Mission Control</h1>
          <p class="page-subtitle">Give your AI team a goal. They'll plan it, build it, and launch it.</p>
        </div>
        <button class="new-mission-btn" @click="showCreate = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Mission
        </button>
      </div>

      <div v-if="missions.length === 0 && !loading" class="empty-state">
        <div class="empty-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
        </div>
        <h2>No Missions Yet</h2>
        <p>Start your first mission — tell your AI team what to build, and they'll make it happen.</p>
        <button class="create-first-btn" @click="showCreate = true">Create Your First Mission</button>
      </div>

      <div v-else-if="missions.length > 0" class="missions-list">
        <div
          v-for="m in missions"
          :key="m.id"
          class="mission-card"
          @click="$router.push(`/missions/${m.id}`)"
        >
          <div class="mission-card-status" :class="m.status">
            <span class="status-dot"></span>
            {{ statusLabel(m.status) }}
          </div>
          <h3 class="mission-card-goal">{{ m.goal }}</h3>
          <div class="mission-card-meta">
            <span>{{ timeAgo(m.updated_at || m.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="create-container">
      <button class="back-btn" @click="showCreate = false">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        Back
      </button>
      <div class="create-form">
        <h1 class="create-title">What's the mission?</h1>
        <p class="create-subtitle">Describe what you want your AI team to accomplish. Be as ambitious as you want.</p>
        <div class="goal-input-wrapper">
          <textarea
            v-model="newGoal"
            class="goal-input"
            placeholder="e.g., Build a cryptocurrency as popular as Bitcoin&#10;e.g., Create a social media platform and get 1M followers&#10;e.g., Launch a SaaS product that generates $10k/month"
            rows="5"
            @keydown.ctrl.enter="createMission"
            @keydown.meta.enter="createMission"
            ref="goalInput"
          ></textarea>
          <div class="goal-hint">Ctrl+Enter to submit</div>
        </div>
        <div class="example-goals">
          <span class="examples-label">Try:</span>
          <button v-for="ex in examples" :key="ex" class="example-chip" @click="newGoal = ex">{{ ex }}</button>
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button class="submit-btn" :disabled="!newGoal.trim() || creating" @click="createMission">
          <template v-if="creating">
            <span class="spinner"></span> Briefing the team...
          </template>
          <template v-else>Launch Mission</template>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const missions = ref([])
const loading = ref(true)
const showCreate = ref(false)
const newGoal = ref('')
const creating = ref(false)
const goalInput = ref(null)

const examples = [
  'Build a mobile app that helps people learn languages',
  'Create an AI-powered e-commerce store',
  'Launch a newsletter with 100k subscribers',
  'Build a SaaS tool for project management'
]

onMounted(async () => {
  await loadMissions()
})

async function loadMissions() {
  loading.value = true
  try {
    const res = await fetch('/api/missions')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    missions.value = data.missions || []
  } catch (e) {
    console.error('Failed to load missions:', e)
  } finally {
    loading.value = false
  }
}

const error = ref('')

async function createMission() {
  if (!newGoal.value.trim() || creating.value) return
  creating.value = true
  error.value = ''
  try {
    const res = await fetch('/api/missions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal: newGoal.value.trim() })
    })
    if (!res.ok) throw new Error(`Failed to create mission (${res.status})`)
    const data = await res.json()
    if (data.id) {
      router.push(`/missions/${data.id}`)
    }
  } catch (e) {
    console.error('Failed to create mission:', e)
    error.value = 'Failed to create mission. Please try again.'
  } finally {
    creating.value = false
  }
}

function statusLabel(s) {
  const labels = {
    gathering_info: 'Gathering Info',
    planning: 'Planning',
    awaiting_approval: 'Awaiting Approval',
    executing: 'Executing',
    completed: 'Completed'
  }
  return labels[s] || s
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
</script>

<style scoped>
.missions-page {
  min-height: calc(100vh - 55px);
  background: #0d1117;
  color: #c9d1d9;
  padding: 40px 24px;
}

.missions-container, .create-container {
  max-width: 900px;
  margin: 0 auto;
}

.missions-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #aaffcd, #99eaf9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 6px 0;
}

.page-subtitle {
  color: #8b949e;
  font-size: 15px;
  margin: 0;
}

.new-mission-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.new-mission-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  color: #30363d;
  margin-bottom: 20px;
}

.empty-state h2 {
  font-size: 22px;
  color: #e6edf3;
  margin: 0 0 8px 0;
}

.empty-state p {
  color: #8b949e;
  font-size: 15px;
  margin: 0 0 24px 0;
}

.create-first-btn {
  padding: 12px 28px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.create-first-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
}

.missions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mission-card {
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 12px;
  padding: 20px 24px;
  cursor: pointer;
  transition: all 0.2s;
}

.mission-card:hover {
  border-color: #388bfd44;
  background: #1c2333;
  transform: translateY(-1px);
}

.mission-card-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  padding: 3px 10px;
  border-radius: 12px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}

.mission-card-status.gathering_info { color: #58a6ff; background: rgba(88,166,255,0.1); }
.mission-card-status.gathering_info .status-dot { background: #58a6ff; }
.mission-card-status.planning { color: #a371f7; background: rgba(163,113,247,0.1); }
.mission-card-status.planning .status-dot { background: #a371f7; }
.mission-card-status.awaiting_approval { color: #f0883e; background: rgba(240,136,62,0.1); }
.mission-card-status.awaiting_approval .status-dot { background: #f0883e; }
.mission-card-status.executing { color: #3fb950; background: rgba(63,185,80,0.1); }
.mission-card-status.executing .status-dot { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.mission-card-status.completed { color: #8b949e; background: rgba(139,148,158,0.1); }
.mission-card-status.completed .status-dot { background: #8b949e; }

.mission-card-goal {
  font-size: 17px;
  font-weight: 600;
  color: #e6edf3;
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.mission-card-meta {
  color: #8b949e;
  font-size: 13px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: #8b949e;
  cursor: pointer;
  font-size: 14px;
  padding: 8px 0;
  margin-bottom: 20px;
  transition: color 0.2s;
}

.back-btn:hover { color: #e6edf3; }

.create-form {
  text-align: center;
  padding: 40px 0;
}

.create-title {
  font-size: 36px;
  font-weight: 700;
  background: linear-gradient(135deg, #aaffcd, #99eaf9, #a0c4ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 10px 0;
}

.create-subtitle {
  color: #8b949e;
  font-size: 16px;
  margin: 0 0 32px 0;
}

.goal-input-wrapper {
  position: relative;
  margin-bottom: 16px;
}

.goal-input {
  width: 100%;
  padding: 20px;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  color: #e6edf3;
  font-size: 16px;
  font-family: 'Inter', sans-serif;
  resize: vertical;
  min-height: 120px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.goal-input:focus {
  outline: none;
  border-color: #58a6ff;
  box-shadow: 0 0 0 3px rgba(88,166,255,0.15);
}

.goal-input::placeholder { color: #484f58; }

.goal-hint {
  position: absolute;
  bottom: 10px;
  right: 14px;
  color: #484f58;
  font-size: 12px;
}

.example-goals {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  align-items: center;
  margin-bottom: 28px;
}

.examples-label {
  color: #8b949e;
  font-size: 13px;
}

.example-chip {
  background: #21262d;
  border: 1px solid #30363d;
  color: #8b949e;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.example-chip:hover {
  background: #30363d;
  color: #c9d1d9;
  border-color: #484f58;
}

.submit-btn {
  padding: 14px 40px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 200px;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(46, 160, 67, 0.3);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  vertical-align: middle;
  margin-right: 6px;
}

.error-msg {
  color: #f85149;
  font-size: 14px;
  margin-bottom: 12px;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
