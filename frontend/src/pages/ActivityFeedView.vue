<template>
  <div class="activity-page">
    <div class="particles-bg">
      <div class="glow glow-1"></div>
      <div class="glow glow-2"></div>
    </div>

    <div class="activity-container">
      <div class="activity-header">
        <div>
          <h1 class="page-title">Activity</h1>
          <p class="page-subtitle">Live updates from your AI agents across all missions</p>
        </div>
        <div class="header-controls">
          <button
            v-for="f in filters"
            :key="f.id"
            class="filter-btn"
            :class="{ active: activeFilter === f.id }"
            @click="activeFilter = f.id"
          >{{ f.label }}</button>
        </div>
      </div>

      <div class="feed-layout">
        <div class="feed-main">
          <div v-if="loading" class="loading-state">
            <div class="loading-dots"><span></span><span></span><span></span></div>
            <p>Loading activity...</p>
          </div>

          <div v-else-if="filteredEvents.length === 0" class="empty-feed">
            <p>No activity yet. Launch a mission to see your agents in action.</p>
          </div>

          <div v-else class="timeline">
            <div
              v-for="(event, idx) in filteredEvents"
              :key="event.id"
              class="timeline-item"
              :class="{ 'animate-in': true }"
              :style="{ animationDelay: `${idx * 0.05}s` }"
            >
              <div class="timeline-marker">
                <div class="marker-dot" :style="{ background: event.agent?.color || '#58a6ff' }"></div>
                <div v-if="idx < filteredEvents.length - 1" class="marker-line"></div>
              </div>
              <div class="timeline-content">
                <div class="event-header">
                  <div class="event-agent">
                    <div class="agent-dot" :style="{ background: event.agent?.color || '#58a6ff' }">
                      {{ event.agent?.avatar || 'A' }}
                    </div>
                    <span class="agent-name">{{ event.agent?.name || 'Agent' }}</span>
                    <span class="event-action">{{ event.action }}</span>
                  </div>
                  <span class="event-time">{{ timeAgo(event.timestamp) }}</span>
                </div>
                <div class="event-body" v-if="event.detail">
                  {{ event.detail }}
                </div>
                <div class="event-mission" v-if="event.mission" @click="$router.push(`/missions/${event.mission.id}`)">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                  {{ event.mission.goal }}
                </div>
                <div v-if="event.type === 'workflow_created'" class="event-workflow-tag">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                  Workflow auto-generated
                </div>
                <div v-if="event.type === 'collaboration'" class="event-collab-tag">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                  Shared with {{ event.shared_with }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="feed-sidebar">
          <div class="sidebar-card">
            <h3 class="sidebar-title">Active Now</h3>
            <div class="active-agents">
              <div v-for="a in activeAgents" :key="a.id" class="active-agent">
                <div class="active-dot" :style="{ background: a.color }">{{ a.avatar }}</div>
                <div class="active-info">
                  <div class="active-name">{{ a.name }}</div>
                  <div class="active-task">{{ a.currentTask }}</div>
                </div>
                <div class="pulse-dot"></div>
              </div>
              <div v-if="activeAgents.length === 0" class="no-active">
                All agents idle
              </div>
            </div>
          </div>

          <div class="sidebar-card">
            <h3 class="sidebar-title">Recent Missions</h3>
            <div class="sidebar-missions">
              <div
                v-for="m in recentMissions"
                :key="m.id"
                class="sidebar-mission"
                @click="$router.push(`/missions/${m.id}`)"
              >
                <div class="mission-status-pip" :class="m.status"></div>
                <div class="mission-label">{{ m.goal }}</div>
              </div>
              <div v-if="recentMissions.length === 0" class="no-missions">No missions yet</div>
            </div>
          </div>

          <div class="sidebar-card stats-card">
            <h3 class="sidebar-title">Today</h3>
            <div class="day-stats">
              <div class="day-stat">
                <span class="day-stat-num">{{ todayStats.tasks }}</span>
                <span class="day-stat-label">Tasks done</span>
              </div>
              <div class="day-stat">
                <span class="day-stat-num">{{ todayStats.messages }}</span>
                <span class="day-stat-label">Messages</span>
              </div>
              <div class="day-stat">
                <span class="day-stat-num">{{ todayStats.workflows }}</span>
                <span class="day-stat-label">Workflows</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'

const loading = ref(true)
const activeFilter = ref('all')
const events = ref([])
const missions = ref([])
let pollInterval = null

const filters = [
  { id: 'all', label: 'All' },
  { id: 'progress', label: 'Progress' },
  { id: 'decisions', label: 'Decisions' },
  { id: 'collaboration', label: 'Collaboration' },
]

const teamAgents = [
  { id: 'alex', avatar: 'A', name: 'Alex', role: 'Team Leader', color: '#58a6ff' },
  { id: 'maya', avatar: 'M', name: 'Maya', role: 'Market Research', color: '#f0883e' },
  { id: 'jordan', avatar: 'J', name: 'Jordan', role: 'Product Strategy', color: '#a371f7' },
  { id: 'sam', avatar: 'S', name: 'Sam', role: 'Lead Engineer', color: '#3fb950' },
  { id: 'riley', avatar: 'R', name: 'Riley', role: 'DevOps', color: '#79c0ff' },
  { id: 'casey', avatar: 'C', name: 'Casey', role: 'QA & Compliance', color: '#d2a8ff' },
  { id: 'taylor', avatar: 'T', name: 'Taylor', role: 'Growth', color: '#f778ba' },
  { id: 'morgan', avatar: 'O', name: 'Morgan', role: 'Operations', color: '#ffa657' },
]

const agentMap = Object.fromEntries(teamAgents.map(a => [a.id, a]))

const filteredEvents = computed(() => {
  if (activeFilter.value === 'all') return events.value
  return events.value.filter(e => e.category === activeFilter.value)
})

const activeAgents = computed(() => {
  const executing = missions.value.filter(m => m.status === 'executing')
  if (executing.length === 0) return []
  // Show agents that have recent activity
  const active = new Set()
  events.value.slice(0, 10).forEach(e => {
    if (e.agent?.id) active.add(e.agent.id)
  })
  return teamAgents
    .filter(a => active.has(a.id))
    .slice(0, 5)
    .map(a => ({
      ...a,
      currentTask: getAgentTask(a.id),
    }))
})

const recentMissions = computed(() => missions.value.slice(0, 5))

const todayStats = computed(() => {
  const today = new Date().toDateString()
  const todayEvents = events.value.filter(e => new Date(e.timestamp).toDateString() === today)
  return {
    tasks: todayEvents.filter(e => e.type === 'task_complete').length,
    messages: todayEvents.filter(e => e.type === 'message').length,
    workflows: todayEvents.filter(e => e.type === 'workflow_created').length,
  }
})

function getAgentTask(agentId) {
  const recent = events.value.find(e => e.agent?.id === agentId)
  return recent?.action || 'Working...'
}

onMounted(async () => {
  await Promise.all([loadActivity(), loadMissions()])
  // Poll for updates every 10 seconds
  pollInterval = setInterval(async () => {
    await Promise.all([loadActivity(), loadMissions()])
  }, 10000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

async function loadActivity() {
  try {
    const res = await fetch('/api/activity')
    if (res.ok) {
      const data = await res.json()
      events.value = (data.events || []).map(e => ({
        ...e,
        agent: e.agent_id ? agentMap[e.agent_id] || { avatar: '?', name: e.agent_name || 'Agent', color: '#58a6ff' } : e.agent,
      }))
    } else {
      // If endpoint doesn't exist yet, show sample data
      events.value = buildSampleEvents()
    }
  } catch {
    events.value = buildSampleEvents()
  } finally {
    loading.value = false
  }
}

async function loadMissions() {
  try {
    const res = await fetch('/api/missions')
    if (res.ok) {
      const data = await res.json()
      missions.value = data.missions || []
    }
  } catch { /* ignore */ }
}

function buildSampleEvents() {
  // Graceful fallback when the API isn't wired yet
  const now = Date.now()
  return [
    { id: 1, type: 'progress', category: 'progress', agent: teamAgents[0], action: 'coordinated task assignments', detail: 'Distributed research tasks across the team based on each agent\'s specialization.', timestamp: new Date(now - 60000).toISOString(), mission: missions.value[0] || null },
    { id: 2, type: 'workflow_created', category: 'progress', agent: teamAgents[3], action: 'created a new workflow', detail: 'Auto-generated a 6-node workflow for the backend API pipeline.', timestamp: new Date(now - 180000).toISOString(), mission: missions.value[0] || null },
    { id: 3, type: 'collaboration', category: 'collaboration', agent: teamAgents[1], action: 'shared research findings', detail: 'Compiled market analysis and shared with Jordan for product strategy review.', shared_with: 'Jordan', timestamp: new Date(now - 300000).toISOString(), mission: missions.value[0] || null },
    { id: 4, type: 'decision', category: 'decisions', agent: teamAgents[2], action: 'recommended tech stack', detail: 'Suggested React + FastAPI based on team capabilities and project requirements.', timestamp: new Date(now - 600000).toISOString(), mission: missions.value[0] || null },
    { id: 5, type: 'task_complete', category: 'progress', agent: teamAgents[4], action: 'set up CI/CD pipeline', detail: 'Configured automated testing and deployment workflow.', timestamp: new Date(now - 900000).toISOString(), mission: missions.value[0] || null },
    { id: 6, type: 'collaboration', category: 'collaboration', agent: teamAgents[5], action: 'reviewed code quality', detail: 'Ran compliance checks on the generated codebase. All checks passed.', shared_with: 'Sam', timestamp: new Date(now - 1200000).toISOString(), mission: missions.value[0] || null },
    { id: 7, type: 'progress', category: 'progress', agent: teamAgents[6], action: 'drafted launch plan', detail: 'Created growth strategy with target milestones for the first 90 days.', timestamp: new Date(now - 1800000).toISOString(), mission: missions.value[0] || null },
    { id: 8, type: 'message', category: 'progress', agent: teamAgents[7], action: 'updated resource allocation', detail: 'Optimized compute allocation across active workflows for faster execution.', timestamp: new Date(now - 2400000).toISOString(), mission: missions.value[0] || null },
  ]
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
.activity-page {
  min-height: calc(100vh - var(--topbar-h, 56px));
  background: #0a0e17;
  color: #c9d1d9;
  padding: 40px 24px;
  position: relative;
  font-family: 'Inter', sans-serif;
}

.particles-bg { position: fixed; inset: 0; pointer-events: none; z-index: 0; }
.glow { position: absolute; border-radius: 50%; filter: blur(100px); }
.glow-1 { width: 500px; height: 500px; background: rgba(88,166,255,0.06); top: -100px; left: -100px; animation: glowDrift 15s ease-in-out infinite; }
.glow-2 { width: 400px; height: 400px; background: rgba(163,113,247,0.05); bottom: -100px; right: -100px; animation: glowDrift 18s ease-in-out infinite reverse; }
@keyframes glowDrift { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(30px, 20px); } }

.activity-container { max-width: 1200px; margin: 0 auto; position: relative; z-index: 1; }

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, #aaffcd, #99eaf9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 6px;
}

.page-subtitle { color: #8b949e; font-size: 15px; margin: 0; }

.header-controls { display: flex; gap: 6px; align-items: center; }

.filter-btn {
  padding: 7px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  color: #8b949e;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover { background: rgba(255,255,255,0.06); color: #c9d1d9; }
.filter-btn.active { background: rgba(88,166,255,0.1); border-color: rgba(88,166,255,0.3); color: #58a6ff; }

.feed-layout { display: flex; gap: 24px; align-items: flex-start; }
.feed-main { flex: 1; min-width: 0; }
.feed-sidebar { width: 300px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px; position: sticky; top: 80px; }

.loading-state { display: flex; flex-direction: column; align-items: center; gap: 12px; color: #8b949e; padding: 60px; }
.loading-dots { display: flex; gap: 6px; }
.loading-dots span { width: 10px; height: 10px; border-radius: 50%; background: #30363d; animation: loadBounce 1.4s ease-in-out infinite; }
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes loadBounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }

.empty-feed { text-align: center; padding: 60px 20px; color: #8b949e; font-size: 15px; }

/* Timeline */
.timeline { display: flex; flex-direction: column; }

.timeline-item {
  display: flex;
  gap: 16px;
  animation: slideIn 0.4s ease-out both;
}

@keyframes slideIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

.timeline-marker { display: flex; flex-direction: column; align-items: center; width: 20px; flex-shrink: 0; padding-top: 4px; }
.marker-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; box-shadow: 0 0 8px rgba(88,166,255,0.3); }
.marker-line { width: 2px; flex: 1; background: rgba(255,255,255,0.06); min-height: 20px; }

.timeline-content {
  flex: 1;
  padding-bottom: 24px;
  min-width: 0;
}

.event-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }

.event-agent { display: flex; align-items: center; gap: 8px; }

.agent-dot {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 10px;
  color: #fff;
  flex-shrink: 0;
}

.agent-name { font-size: 14px; font-weight: 600; color: #e6edf3; }
.event-action { font-size: 14px; color: #8b949e; }
.event-time { font-size: 12px; color: #484f58; white-space: nowrap; }

.event-body {
  font-size: 14px;
  color: #8b949e;
  line-height: 1.5;
  margin-bottom: 8px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 12px;
}

.event-mission {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #58a6ff;
  cursor: pointer;
  padding: 4px 10px;
  background: rgba(88,166,255,0.08);
  border-radius: 8px;
  transition: all 0.2s;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-mission:hover { background: rgba(88,166,255,0.15); }

.event-workflow-tag, .event-collab-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 8px;
  margin-top: 6px;
}

.event-workflow-tag { color: #3fb950; background: rgba(63,185,80,0.1); }
.event-collab-tag { color: #a371f7; background: rgba(163,113,247,0.1); }

/* Sidebar cards */
.sidebar-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 20px;
  backdrop-filter: blur(10px);
}

.sidebar-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #484f58;
  margin: 0 0 14px;
  font-weight: 700;
}

.active-agents { display: flex; flex-direction: column; gap: 10px; }

.active-agent { display: flex; align-items: center; gap: 10px; }

.active-dot {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 11px;
  color: #fff;
  flex-shrink: 0;
}

.active-info { flex: 1; min-width: 0; }
.active-name { font-size: 13px; font-weight: 600; color: #e6edf3; }
.active-task { font-size: 11px; color: #8b949e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3fb950;
  animation: pulse 1.5s ease-in-out infinite;
  flex-shrink: 0;
}

.no-active, .no-missions { font-size: 13px; color: #484f58; }

.sidebar-missions { display: flex; flex-direction: column; gap: 8px; }

.sidebar-mission {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar-mission:hover { background: rgba(255,255,255,0.04); }

.mission-status-pip {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.mission-status-pip.gathering_info { background: #58a6ff; }
.mission-status-pip.planning { background: #a371f7; }
.mission-status-pip.awaiting_approval { background: #f0883e; }
.mission-status-pip.executing { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.mission-status-pip.completed { background: #8b949e; }

.mission-label {
  font-size: 13px;
  color: #c9d1d9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.day-stats { display: flex; gap: 12px; }
.day-stat { flex: 1; text-align: center; }
.day-stat-num { display: block; font-size: 22px; font-weight: 700; color: #e6edf3; }
.day-stat-label { font-size: 11px; color: #484f58; }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

@media (max-width: 900px) {
  .feed-layout { flex-direction: column; }
  .feed-sidebar { width: 100%; position: static; flex-direction: row; flex-wrap: wrap; }
  .sidebar-card { flex: 1; min-width: 250px; }
}

@media (max-width: 768px) {
  .activity-header { flex-direction: column; }
  .header-controls { flex-wrap: wrap; }
}
</style>
