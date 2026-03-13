<template>
  <div class="missions-page">
    <div class="particles-bg">
      <div class="glow glow-1"></div>
      <div class="glow glow-2"></div>
    </div>

    <div v-if="!showCreate" class="missions-container">
      <div class="missions-header">
        <div>
          <h1 class="page-title">Mission Control</h1>
          <p class="page-subtitle">Give your AI team a goal. They'll plan it, build it, and launch it.</p>
        </div>
        <button class="new-mission-btn" @click="showCreate = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          New Mission
        </button>
      </div>

      <div v-if="missions.length === 0 && !loading" class="empty-state">
        <div class="empty-visual">
          <div class="empty-orbit">
            <div v-for="(a, i) in miniAvatars" :key="i" class="orbit-avatar" :style="{ background: a.color, animationDelay: `${i * -0.5}s` }">{{ a.letter }}</div>
          </div>
        </div>
        <h2>Your AI Team is Ready</h2>
        <p>8 specialized agents are standing by. Give them a mission and watch them work.</p>
        <button class="create-first-btn" @click="showCreate = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          Launch Your First Mission
        </button>
      </div>

      <div v-if="missions.length > 0" class="missions-grid">
        <div
          v-for="m in missions"
          :key="m.id"
          class="mission-card glass-card"
          @click="$router.push(`/missions/${m.id}`)"
        >
          <div class="card-top">
            <div class="card-status" :class="m.status">
              <span class="status-dot"></span>
              {{ statusLabel(m.status) }}
            </div>
            <span class="card-time">{{ timeAgo(m.updated_at || m.created_at) }}</span>
          </div>
          <h3 class="card-goal">{{ m.goal }}</h3>
          <div class="card-progress" v-if="m.status === 'executing'">
            <div class="progress-bar">
              <div class="progress-fill" style="width: 35%"></div>
            </div>
            <span class="progress-label">In progress</span>
          </div>
          <div class="card-agents">
            <div v-for="(a, i) in cardAvatars" :key="i" class="mini-avatar" :style="{ background: a.color, zIndex: 8-i }">{{ a.letter }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="create-container">
      <button class="back-btn" @click="showCreate = false">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        Back to Missions
      </button>

      <div class="create-hero">
        <h1 class="create-title">What's the mission?</h1>
        <p class="create-subtitle">Describe your goal. Your AI team of 8 specialists will take it from there.</p>
      </div>

      <div class="goal-input-wrapper">
        <textarea
          v-model="newGoal"
          class="goal-input"
          placeholder="Describe your mission in detail..."
          rows="4"
          @keydown.ctrl.enter="createMission"
          @keydown.meta.enter="createMission"
          ref="goalInput"
        ></textarea>
        <div class="input-footer">
          <span class="char-count" :class="{ warn: newGoal.length > 500 }">{{ newGoal.length }}/500</span>
          <span class="key-hint">Ctrl+Enter to submit</span>
        </div>
      </div>

      <div class="templates-section">
        <h3 class="templates-title">Or start from a template</h3>
        <div class="template-categories">
          <button v-for="cat in categories" :key="cat.id" class="cat-btn" :class="{ active: activeCategory === cat.id }" @click="activeCategory = cat.id">
            <span class="cat-icon" v-html="cat.icon"></span>
            {{ cat.label }}
          </button>
        </div>
        <div class="templates-grid">
          <div v-for="tpl in filteredTemplates" :key="tpl.goal" class="template-card glass-card" @click="newGoal = tpl.goal">
            <div class="tpl-emoji">{{ tpl.emoji }}</div>
            <h4 class="tpl-title">{{ tpl.title }}</h4>
            <p class="tpl-desc">{{ tpl.desc }}</p>
          </div>
        </div>
      </div>

      <div class="submit-area">
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button class="submit-btn" :disabled="!newGoal.trim() || creating" @click="createMission">
          <template v-if="creating">
            <span class="spinner"></span> Briefing the team...
          </template>
          <template v-else>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            Launch Mission
          </template>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const missions = ref([])
const loading = ref(true)
const showCreate = ref(false)
const newGoal = ref('')
const creating = ref(false)
const error = ref('')
const activeCategory = ref('all')

const miniAvatars = [
  { letter: 'A', color: '#58a6ff' }, { letter: 'M', color: '#f0883e' },
  { letter: 'J', color: '#a371f7' }, { letter: 'S', color: '#3fb950' },
  { letter: 'R', color: '#79c0ff' }, { letter: 'C', color: '#d2a8ff' },
  { letter: 'T', color: '#f778ba' }, { letter: 'O', color: '#ffa657' }
]

const cardAvatars = miniAvatars.slice(0, 5)

const categories = [
  { id: 'all', label: 'All', icon: '&#9733;' },
  { id: 'product', label: 'Product', icon: '&#128640;' },
  { id: 'marketing', label: 'Marketing', icon: '&#128227;' },
  { id: 'engineering', label: 'Engineering', icon: '&#9881;' },
  { id: 'business', label: 'Business', icon: '&#128188;' },
]

const templates = [
  { category: 'product', emoji: '📱', title: 'Mobile App', goal: 'Build a mobile app that helps people track their daily habits and improve their productivity with AI-powered recommendations', desc: 'Full mobile app with AI coaching' },
  { category: 'product', emoji: '🛒', title: 'E-Commerce Platform', goal: 'Create an AI-powered e-commerce store that personalizes product recommendations and automates inventory management', desc: 'Smart online store with AI' },
  { category: 'product', emoji: '💬', title: 'SaaS Platform', goal: 'Build a SaaS platform for team collaboration with real-time chat, project management, and AI-assisted task prioritization', desc: 'Team collaboration SaaS tool' },
  { category: 'marketing', emoji: '📰', title: 'Newsletter Empire', goal: 'Launch a niche newsletter and grow it to 100,000 subscribers with automated content curation and personalized delivery', desc: 'Grow a massive newsletter' },
  { category: 'marketing', emoji: '📲', title: 'Social Media Growth', goal: 'Create a social media presence across all major platforms and grow to 1 million followers with AI-generated content strategy', desc: 'Build a social media following' },
  { category: 'marketing', emoji: '🎯', title: 'Lead Generation Engine', goal: 'Build an automated B2B lead generation system with AI outreach, CRM integration, and conversion tracking', desc: 'Automated B2B lead gen' },
  { category: 'engineering', emoji: '⛓️', title: 'Blockchain Project', goal: 'Build a cryptocurrency or blockchain-based platform with smart contracts, a token economy, and a community-driven governance model', desc: 'Crypto & blockchain platform' },
  { category: 'engineering', emoji: '🤖', title: 'AI Assistant', goal: 'Create a domain-specific AI assistant that can answer questions, automate tasks, and learn from user interactions over time', desc: 'Custom AI assistant' },
  { category: 'engineering', emoji: '🔌', title: 'API Marketplace', goal: 'Build a marketplace where developers can discover, test, and subscribe to APIs with automated documentation and billing', desc: 'Developer API marketplace' },
  { category: 'business', emoji: '💰', title: 'Revenue Machine', goal: 'Create a digital product or service that generates $10,000/month in recurring revenue within 6 months', desc: 'Build a revenue stream' },
  { category: 'business', emoji: '📊', title: 'Data Analytics Tool', goal: 'Build a business intelligence dashboard that aggregates data from multiple sources and provides AI-powered insights and predictions', desc: 'BI tool with AI insights' },
  { category: 'business', emoji: '🏢', title: 'Marketplace Platform', goal: 'Create a two-sided marketplace connecting service providers with customers, with automated matching, payments, and reviews', desc: 'Two-sided marketplace' },
]

const filteredTemplates = computed(() => {
  if (activeCategory.value === 'all') return templates
  return templates.filter(t => t.category === activeCategory.value)
})

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
    if (data.id) router.push(`/missions/${data.id}`)
  } catch (e) {
    error.value = 'Failed to create mission. Please try again.'
  } finally {
    creating.value = false
  }
}

function statusLabel(s) {
  return { gathering_info: 'Gathering Info', planning: 'Planning', awaiting_approval: 'Awaiting Approval', executing: 'Executing', completed: 'Completed' }[s] || s
}

function timeAgo(d) {
  if (!d) return ''
  const diff = Math.floor((Date.now() - new Date(d)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
</script>

<style scoped>
.missions-page {
  min-height: calc(100vh - var(--topbar-h, 56px));
  background: #0a0e17;
  color: #c9d1d9;
  padding: 40px 24px;
  position: relative;
  font-family: 'Inter', sans-serif;
}

.particles-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
}

.glow-1 {
  width: 500px;
  height: 500px;
  background: rgba(88,166,255,0.06);
  top: -100px;
  left: -100px;
  animation: glowDrift 15s ease-in-out infinite;
}

.glow-2 {
  width: 400px;
  height: 400px;
  background: rgba(163,113,247,0.05);
  bottom: -100px;
  right: -100px;
  animation: glowDrift 18s ease-in-out infinite reverse;
}

@keyframes glowDrift {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, 20px); }
}

.missions-container, .create-container {
  max-width: 960px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.missions-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 36px;
}

.page-title {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, #aaffcd, #99eaf9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 6px;
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
  padding: 12px 24px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 16px rgba(46,160,67,0.25);
}

.new-mission-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(46,160,67,0.35);
}

.empty-state { text-align: center; padding: 60px 20px; }

.empty-visual {
  width: 120px;
  height: 120px;
  margin: 0 auto 24px;
  position: relative;
}

.empty-orbit {
  width: 100%;
  height: 100%;
  position: relative;
  animation: slowSpin 20s linear infinite;
}

.orbit-avatar {
  position: absolute;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 11px;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.orbit-avatar:nth-child(1) { top: 0; left: 50%; transform: translateX(-50%); }
.orbit-avatar:nth-child(2) { top: 15%; right: 5%; }
.orbit-avatar:nth-child(3) { top: 50%; right: 0; transform: translateY(-50%); }
.orbit-avatar:nth-child(4) { bottom: 15%; right: 5%; }
.orbit-avatar:nth-child(5) { bottom: 0; left: 50%; transform: translateX(-50%); }
.orbit-avatar:nth-child(6) { bottom: 15%; left: 5%; }
.orbit-avatar:nth-child(7) { top: 50%; left: 0; transform: translateY(-50%); }
.orbit-avatar:nth-child(8) { top: 15%; left: 5%; }

@keyframes slowSpin { to { transform: rotate(360deg); } }

.empty-state h2 { font-size: 24px; color: #e6edf3; margin: 0 0 8px; }
.empty-state p { color: #8b949e; font-size: 15px; margin: 0 0 28px; max-width: 400px; display: inline-block; }

.create-first-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 32px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(46,160,67,0.25);
}

.create-first-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(46,160,67,0.35);
}

.missions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}

.glass-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  transition: all 0.3s;
}

.glass-card:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.12);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

.mission-card { padding: 22px 24px; cursor: pointer; }

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 3px 10px;
  border-radius: 10px;
}

.status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.card-status.gathering_info { color: #58a6ff; background: rgba(88,166,255,0.1); }
.card-status.gathering_info .status-dot { background: #58a6ff; }
.card-status.planning { color: #a371f7; background: rgba(163,113,247,0.1); }
.card-status.planning .status-dot { background: #a371f7; }
.card-status.awaiting_approval { color: #f0883e; background: rgba(240,136,62,0.1); }
.card-status.awaiting_approval .status-dot { background: #f0883e; }
.card-status.executing { color: #3fb950; background: rgba(63,185,80,0.1); }
.card-status.executing .status-dot { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.card-status.completed { color: #8b949e; background: rgba(139,148,158,0.1); }
.card-status.completed .status-dot { background: #8b949e; }

.card-time { font-size: 12px; color: #484f58; }

.card-goal {
  font-size: 17px;
  font-weight: 600;
  color: #e6edf3;
  margin: 0 0 14px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-progress { margin-bottom: 12px; }

.progress-bar {
  width: 100%;
  height: 4px;
  background: rgba(255,255,255,0.06);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3fb950, #58a6ff);
  border-radius: 2px;
  transition: width 0.5s ease;
}

.progress-label { font-size: 11px; color: #8b949e; }

.card-agents {
  display: flex;
}

.mini-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 10px;
  color: #fff;
  border: 2px solid #0a0e17;
  margin-right: -6px;
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
  margin-bottom: 16px;
  transition: color 0.2s;
}

.back-btn:hover { color: #e6edf3; }

.create-hero { text-align: center; padding: 20px 0 32px; }

.create-title {
  font-size: 40px;
  font-weight: 800;
  background: linear-gradient(135deg, #aaffcd, #99eaf9, #a0c4ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 10px;
}

.create-subtitle {
  color: #8b949e;
  font-size: 16px;
  margin: 0;
}

.goal-input-wrapper {
  margin-bottom: 8px;
}

.goal-input {
  width: 100%;
  padding: 20px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  color: #e6edf3;
  font-size: 16px;
  font-family: 'Inter', sans-serif;
  resize: vertical;
  min-height: 100px;
  transition: all 0.3s;
  box-sizing: border-box;
}

.goal-input:focus {
  outline: none;
  border-color: #58a6ff;
  box-shadow: 0 0 0 3px rgba(88,166,255,0.15), 0 4px 20px rgba(88,166,255,0.1);
}

.goal-input::placeholder { color: #484f58; }

.input-footer {
  display: flex;
  justify-content: space-between;
  padding: 6px 4px;
  font-size: 12px;
  color: #484f58;
}

.char-count.warn { color: #f0883e; }
.key-hint { color: #30363d; }

.templates-section { margin: 32px 0; }

.templates-title {
  font-size: 15px;
  font-weight: 600;
  color: #8b949e;
  margin: 0 0 16px;
  text-align: center;
}

.template-categories {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.cat-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  color: #8b949e;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.cat-btn:hover { background: rgba(255,255,255,0.06); color: #c9d1d9; }

.cat-btn.active {
  background: rgba(88,166,255,0.1);
  border-color: rgba(88,166,255,0.3);
  color: #58a6ff;
}

.cat-icon { font-size: 14px; }

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.template-card {
  padding: 18px 20px;
  cursor: pointer;
}

.template-card:hover { border-color: rgba(88,166,255,0.3); }

.tpl-emoji { font-size: 24px; margin-bottom: 8px; }

.tpl-title {
  font-size: 15px;
  font-weight: 600;
  color: #e6edf3;
  margin: 0 0 4px;
}

.tpl-desc {
  font-size: 13px;
  color: #8b949e;
  margin: 0;
}

.submit-area { text-align: center; padding: 24px 0 40px; }

.error-msg {
  color: #f85149;
  font-size: 14px;
  margin-bottom: 12px;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 16px 40px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 14px;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(46,160,67,0.25);
  min-width: 220px;
  justify-content: center;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(46,160,67,0.35);
}

.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

@media (max-width: 768px) {
  .missions-header { flex-direction: column; gap: 16px; }
  .missions-grid { grid-template-columns: 1fr; }
  .templates-grid { grid-template-columns: 1fr; }
  .create-title { font-size: 28px; }
}
</style>
