<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const missions = ref([])
const stats = ref({ total: 0, executing: 0, completed: 0, planning: 0 })
const loading = ref(true)

const recentMissions = computed(() => missions.value.slice(0, 4))

const cubeColors = ['#aaffcd', '#99eaf9', '#a0c4ff', '#d2a8ff', '#f0883e']
const particles = Array.from({ length: 50 }, (_, i) => ({
  id: i,
  left: `${Math.random() * 100}%`,
  top: `${Math.random() * 100}%`,
  size: `${Math.random() * 4 + 2}px`,
  color: cubeColors[Math.floor(Math.random() * cubeColors.length)],
  duration: `${Math.random() * 30 + 40}s`,
  delay: `-${Math.random() * 60}s`,
  opacity: Math.random() * 0.3 + 0.1
}))

onMounted(async () => {
  try {
    const res = await fetch('/api/missions')
    if (res.ok) {
      const data = await res.json()
      missions.value = data.missions || []
      stats.value.total = missions.value.length
      stats.value.executing = missions.value.filter(m => m.status === 'executing').length
      stats.value.completed = missions.value.filter(m => m.status === 'completed').length
      stats.value.planning = missions.value.filter(m => ['gathering_info', 'planning', 'awaiting_approval'].includes(m.status)).length
    }
  } catch (e) { /* ignore */ }
  loading.value = false
})

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

const teamMembers = [
  { avatar: 'A', name: 'Alex', role: 'Team Leader', color: '#58a6ff' },
  { avatar: 'M', name: 'Maya', role: 'Market Research', color: '#f0883e' },
  { avatar: 'J', name: 'Jordan', role: 'Product Strategy', color: '#a371f7' },
  { avatar: 'S', name: 'Sam', role: 'Lead Engineer', color: '#3fb950' },
  { avatar: 'R', name: 'Riley', role: 'DevOps', color: '#79c0ff' },
  { avatar: 'C', name: 'Casey', role: 'QA & Compliance', color: '#d2a8ff' },
  { avatar: 'T', name: 'Taylor', role: 'Growth', color: '#f778ba' },
  { avatar: 'O', name: 'Morgan', role: 'Operations', color: '#ffa657' }
]
</script>

<template>
  <div class="home-view">
    <div class="particles-bg">
      <div v-for="p in particles" :key="p.id" class="particle"
        :style="{ left: p.left, top: p.top, width: p.size, height: p.size, backgroundColor: p.color, animationDuration: p.duration, animationDelay: p.delay, opacity: p.opacity }">
      </div>
    </div>

    <div class="home-content">
      <section class="hero-section">
        <div class="hero-badge">AI-Powered Team Orchestration</div>
        <h1 class="hero-title">
          <span class="gradient-text">PowerSymphony</span>
        </h1>
        <p class="hero-subtitle">Give your AI team a mission. They'll research, plan, build, and launch it — autonomously.</p>
        <div class="hero-actions">
          <button class="btn-primary" @click="router.push('/missions')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            Start a Mission
          </button>
          <button class="btn-secondary" @click="router.push('/tutorial')">How It Works</button>
        </div>
      </section>

      <section class="stats-row" v-if="stats.total > 0">
        <div class="stat-card">
          <div class="stat-number">{{ stats.total }}</div>
          <div class="stat-label">Total Missions</div>
        </div>
        <div class="stat-card executing">
          <div class="stat-number">{{ stats.executing }}</div>
          <div class="stat-label">In Progress</div>
          <div class="stat-pulse" v-if="stats.executing > 0"></div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ stats.planning }}</div>
          <div class="stat-label">Planning</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ stats.completed }}</div>
          <div class="stat-label">Completed</div>
        </div>
      </section>

      <section class="recent-section" v-if="recentMissions.length > 0">
        <div class="section-header">
          <h2 class="section-title">Recent Missions</h2>
          <button class="see-all-btn" @click="router.push('/missions')">See all</button>
        </div>
        <div class="missions-grid">
          <div v-for="m in recentMissions" :key="m.id" class="mission-card glass-card" @click="router.push(`/missions/${m.id}`)">
            <div class="card-status" :class="m.status">
              <span class="dot"></span>{{ statusLabel(m.status) }}
            </div>
            <h3 class="card-goal">{{ m.goal }}</h3>
            <div class="card-footer">
              <span class="card-time">{{ timeAgo(m.updated_at || m.created_at) }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="team-section">
        <div class="section-header">
          <h2 class="section-title">Your AI Team</h2>
        </div>
        <div class="team-grid">
          <div v-for="t in teamMembers" :key="t.avatar" class="team-card glass-card">
            <div class="team-avatar" :style="{ background: t.color }">{{ t.avatar }}</div>
            <div class="team-name">{{ t.name }}</div>
            <div class="team-role">{{ t.role }}</div>
          </div>
        </div>
      </section>

      <section class="capabilities-section">
        <div class="section-header">
          <h2 class="section-title">What Your Team Can Do</h2>
        </div>
        <div class="capabilities-grid">
          <div class="capability glass-card">
            <div class="cap-icon" style="background: rgba(63,185,80,0.15); color: #3fb950;">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            </div>
            <h3>Build Software</h3>
            <p>Full-stack apps, APIs, mobile apps — your engineering team handles it all.</p>
          </div>
          <div class="capability glass-card">
            <div class="cap-icon" style="background: rgba(240,136,62,0.15); color: #f0883e;">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>
            </div>
            <h3>Market & Grow</h3>
            <p>SEO, social media, content marketing, and user acquisition at scale.</p>
          </div>
          <div class="capability glass-card">
            <div class="cap-icon" style="background: rgba(163,113,247,0.15); color: #a371f7;">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
            </div>
            <h3>Research & Plan</h3>
            <p>Market research, competitive analysis, product roadmaps, and strategy.</p>
          </div>
          <div class="capability glass-card">
            <div class="cap-icon" style="background: rgba(247,120,186,0.15); color: #f778ba;">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
            </div>
            <h3>Launch & Scale</h3>
            <p>Deployment, infrastructure, monitoring, and scaling to millions.</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  width: 100%;
  min-height: calc(100vh - var(--topbar-h, 56px));
  background: #0a0e17;
  position: relative;
  overflow-x: hidden;
  overflow-y: auto;
  font-family: 'Inter', sans-serif;
}

.particles-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.particles-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(800px 400px at 20% 20%, rgba(170,255,205,0.06), transparent),
    radial-gradient(600px 400px at 80% 60%, rgba(160,196,255,0.06), transparent);
  animation: bgDrift 20s ease-in-out infinite;
}

@keyframes bgDrift {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.02); }
}

.particle {
  position: absolute;
  border-radius: 50%;
  animation: float 30s linear infinite;
}

@keyframes float {
  0% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(10px, -20px) scale(1.2); }
  50% { transform: translate(-15px, 10px) scale(0.8); }
  75% { transform: translate(20px, 15px) scale(1.1); }
  100% { transform: translate(0, 0) scale(1); }
}

.home-content {
  position: relative;
  z-index: 1;
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px 60px;
}

.hero-section {
  text-align: center;
  padding: 80px 0 50px;
}

.hero-badge {
  display: inline-block;
  padding: 6px 16px;
  background: rgba(88,166,255,0.1);
  border: 1px solid rgba(88,166,255,0.2);
  border-radius: 20px;
  color: #58a6ff;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 20px;
  letter-spacing: 0.3px;
}

.hero-title {
  font-size: 64px;
  font-weight: 800;
  margin: 0 0 16px;
  letter-spacing: -2px;
  line-height: 1.1;
}

.gradient-text {
  background: linear-gradient(135deg, #aaffcd, #99eaf9, #a0c4ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 20px;
  color: #8b949e;
  max-width: 600px;
  margin: 0 auto 32px;
  line-height: 1.5;
}

.hero-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  background: linear-gradient(135deg, #238636 0%, #2ea043 50%, #3fb950 100%);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(46,160,67,0.25);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(46,160,67,0.35);
}

.btn-secondary {
  padding: 14px 28px;
  background: rgba(255,255,255,0.05);
  border: 1px solid #30363d;
  color: #c9d1d9;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: rgba(255,255,255,0.1);
  border-color: #484f58;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 48px;
}

.stat-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
}

.stat-card:hover {
  border-color: rgba(255,255,255,0.12);
  transform: translateY(-2px);
}

.stat-card.executing {
  border-color: rgba(63,185,80,0.3);
}

.stat-pulse {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3fb950;
  animation: pulse 2s ease-in-out infinite;
}

.stat-number {
  font-size: 36px;
  font-weight: 700;
  color: #e6edf3;
  line-height: 1;
  margin-bottom: 6px;
}

.stat-label {
  font-size: 13px;
  color: #8b949e;
  font-weight: 500;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0;
}

.see-all-btn {
  background: none;
  border: none;
  color: #58a6ff;
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  transition: color 0.2s;
}

.see-all-btn:hover { color: #79c0ff; }

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

.missions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 48px;
}

.mission-card {
  padding: 20px 24px;
  cursor: pointer;
}

.card-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
  padding: 3px 10px;
  border-radius: 10px;
}

.dot { width: 6px; height: 6px; border-radius: 50%; }
.card-status.gathering_info { color: #58a6ff; background: rgba(88,166,255,0.1); }
.card-status.gathering_info .dot { background: #58a6ff; }
.card-status.planning { color: #a371f7; background: rgba(163,113,247,0.1); }
.card-status.planning .dot { background: #a371f7; }
.card-status.awaiting_approval { color: #f0883e; background: rgba(240,136,62,0.1); }
.card-status.awaiting_approval .dot { background: #f0883e; }
.card-status.executing { color: #3fb950; background: rgba(63,185,80,0.1); }
.card-status.executing .dot { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.card-status.completed { color: #8b949e; background: rgba(139,148,158,0.1); }
.card-status.completed .dot { background: #8b949e; }

.card-goal {
  font-size: 16px;
  font-weight: 600;
  color: #e6edf3;
  margin: 0 0 12px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  font-size: 12px;
  color: #484f58;
}

.team-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 48px;
}

.team-card {
  padding: 20px;
  text-align: center;
}

.team-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  color: #fff;
  margin: 0 auto 10px;
}

.team-name {
  font-size: 14px;
  font-weight: 600;
  color: #e6edf3;
}

.team-role {
  font-size: 12px;
  color: #8b949e;
  margin-top: 2px;
}

.capabilities-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.capability {
  padding: 24px;
}

.cap-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.capability h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e6edf3;
  margin: 0 0 6px;
}

.capability p {
  font-size: 14px;
  color: #8b949e;
  margin: 0;
  line-height: 1.5;
}

.recent-section, .team-section, .capabilities-section {
  margin-bottom: 48px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@media (max-width: 768px) {
  .hero-title { font-size: 40px; }
  .hero-subtitle { font-size: 16px; }
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .missions-grid { grid-template-columns: 1fr; }
  .team-grid { grid-template-columns: repeat(2, 1fr); }
  .capabilities-grid { grid-template-columns: 1fr; }
  .hero-actions { flex-direction: column; align-items: center; }
}
</style>
