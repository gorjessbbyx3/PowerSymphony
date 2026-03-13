<template>
  <div class="office-page">
    <div class="office-header">
      <div class="header-left">
        <button class="back-link" @click="$router.push('/missions')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          Missions
        </button>
        <div class="header-info" v-if="mission">
          <h2 class="mission-title">{{ mission.goal }}</h2>
          <div class="mission-status-badge" :class="mission.status">
            <span class="status-dot"></span>
            {{ statusLabel(mission.status) }}
          </div>
        </div>
      </div>
      <div class="header-right">
        <button class="view-toggle-btn" @click="$router.push(`/missions/${route.params.id}`)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          Chat View
        </button>
        <button
          v-if="mission?.status === 'awaiting_approval'"
          class="approve-btn"
          @click="approvePlan"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          Approve Plan
        </button>
      </div>
    </div>

    <div class="office-body" v-if="!loading && !loadError">
      <div class="office-floor">
        <div class="floor-header">
          <h3 class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            Virtual Office
          </h3>
          <div class="floor-legend">
            <span class="legend-item"><span class="legend-dot idle"></span>Idle</span>
            <span class="legend-item"><span class="legend-dot thinking"></span>Thinking</span>
            <span class="legend-item"><span class="legend-dot active"></span>Working</span>
          </div>
        </div>

        <div class="workstations-grid">
          <div
            v-for="agent in teamAgents"
            :key="agent.id"
            class="workstation"
            :class="{ selected: selectedAgent?.id === agent.id, [agentStatus(agent.id)]: true }"
            @click="selectAgent(agent)"
          >
            <div class="ws-glow" :style="{ background: agent.color }"></div>
            <div class="ws-content">
              <AgentAvatar
                :agentId="agent.id"
                :color="agent.color"
                :icon="agent.icon"
                :letter="agent.avatar"
                :size="52"
              />
              <div class="ws-info">
                <div class="ws-name" :style="{ color: agent.color }">{{ agent.name.split('—')[0].trim() }}</div>
                <div class="ws-role">{{ agent.role }}</div>
              </div>
              <div class="ws-status-indicator" :class="agentStatus(agent.id)">
                <span class="ws-status-dot"></span>
                {{ agentStatusLabel(agent.id) }}
              </div>
              <div class="ws-current-task" v-if="getAgentCurrentTask(agent.id)">
                {{ getAgentCurrentTask(agent.id) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="office-panels">
        <div class="detail-panel" v-if="selectedAgent">
          <div class="detail-header">
            <AgentAvatar
              :agentId="selectedAgent.id"
              :color="selectedAgent.color"
              :icon="selectedAgent.icon"
              :letter="selectedAgent.avatar"
              :size="44"
            />
            <div>
              <h3 class="detail-name" :style="{ color: selectedAgent.color }">{{ selectedAgent.name }}</h3>
              <div class="detail-role">{{ selectedAgent.role }}</div>
            </div>
            <button class="detail-close" @click="selectedAgent = null">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="detail-section">
            <div class="detail-label">About</div>
            <p class="detail-description">{{ selectedAgent.description }}</p>
          </div>

          <div class="detail-section" v-if="selectedAgent.kpis?.length">
            <div class="detail-label">Key Performance Indicators</div>
            <div class="kpi-list">
              <div v-for="(kpi, i) in selectedAgent.kpis" :key="i" class="kpi-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" :stroke="selectedAgent.color" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                <span>{{ kpi }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="selectedAgent.dependencies?.length">
            <div class="detail-label">Dependencies</div>
            <div class="dep-list">
              <div v-for="(dep, i) in selectedAgent.dependencies" :key="i" class="dep-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                <span>{{ dep }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="getAgentMessages(selectedAgent.id).length">
            <div class="detail-label">Recent Activity</div>
            <div class="activity-list">
              <div v-for="msg in getAgentMessages(selectedAgent.id).slice(-3)" :key="msg.id" class="activity-item">
                <div class="activity-content" v-html="renderMarkdown(msg.content.substring(0, 200) + (msg.content.length > 200 ? '...' : ''))"></div>
                <div class="activity-reasoning" v-if="msg.metadata?.reasoning">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                  {{ msg.metadata.reasoning }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="discussion-feed">
          <h3 class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
            Team Discussion
            <span class="msg-count">{{ agentMessages.length }}</span>
          </h3>
          <div class="feed-list" ref="feedContainer">
            <div v-if="agentMessages.length === 0" class="empty-feed">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#30363d" stroke-width="1.5"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
              <p>No team discussions yet. Start the mission to see agents collaborate.</p>
            </div>
            <div
              v-for="(msg, idx) in agentMessages"
              :key="msg.id"
              class="feed-msg"
              :class="{ 'animate-in': idx >= animateFrom }"
              :style="{ animationDelay: idx >= animateFrom ? `${(idx - animateFrom) * 0.06}s` : '0s' }"
            >
              <div class="feed-msg-avatar">
                <AgentAvatar
                  :agentId="msg.agent_name"
                  :color="msg.agent?.color || '#58a6ff'"
                  :icon="msg.agent?.icon || ''"
                  :letter="msg.agent?.avatar || '?'"
                  :size="32"
                />
              </div>
              <div class="feed-msg-body">
                <div class="feed-msg-header">
                  <span class="feed-agent-name" :style="{ color: msg.agent?.color || '#58a6ff' }">
                    {{ msg.agent?.name?.split('—')[0]?.trim() || msg.agent_name }}
                  </span>
                  <span class="feed-msg-time">{{ formatTime(msg.created_at) }}</span>
                </div>
                <div class="feed-msg-content" v-html="renderMarkdown(msg.content)"></div>
                <div class="feed-msg-reasoning" v-if="msg.metadata?.reasoning">
                  <button class="reasoning-toggle" @click="toggleReasoning(msg.id)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    {{ expandedReasoning.has(msg.id) ? 'Hide' : 'Show' }} reasoning
                  </button>
                  <div v-if="expandedReasoning.has(msg.id)" class="reasoning-text">
                    {{ msg.metadata.reasoning }}
                  </div>
                </div>
                <div class="feed-msg-meta" v-if="msg.metadata?.current_task">
                  <span class="meta-tag">{{ msg.metadata.current_task }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-dots"><span></span><span></span><span></span></div>
      <p>Loading virtual office...</p>
    </div>
    <div v-if="loadError" class="error-banner">{{ loadError }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AgentAvatar from '../components/AgentAvatar.vue'

const route = useRoute()
const router = useRouter()

const mission = ref(null)
const messages = ref([])
const teamAgents = ref([])
const selectedAgent = ref(null)
const loading = ref(true)
const loadError = ref('')
const animateFrom = ref(0)
const expandedReasoning = ref(new Set())
const feedContainer = ref(null)
let pollInterval = null

const agentMessages = computed(() =>
  messages.value.filter(m => m.role === 'agent')
)

onMounted(async () => {
  await Promise.all([loadMission(), loadTeam()])
  pollInterval = setInterval(pollForUpdates, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

async function loadMission() {
  const id = route.params.id
  loading.value = true
  loadError.value = ''
  try {
    const [mRes, msgRes] = await Promise.all([
      fetch(`/api/missions/${id}`),
      fetch(`/api/missions/${id}/messages`)
    ])
    if (!mRes.ok) throw new Error(`Mission not found (${mRes.status})`)
    if (!msgRes.ok) throw new Error(`Failed to load messages (${msgRes.status})`)
    mission.value = await mRes.json()
    const msgData = await msgRes.json()
    messages.value = msgData.messages || []
    animateFrom.value = messages.value.length
  } catch (e) {
    loadError.value = e.message || 'Failed to load mission'
  } finally {
    loading.value = false
  }
}

async function loadTeam() {
  try {
    const res = await fetch('/api/missions/team/agents')
    if (res.ok) {
      const data = await res.json()
      teamAgents.value = data.agents || []
    }
  } catch (e) {
    console.error('Failed to load team:', e)
  }
}

async function pollForUpdates() {
  const id = route.params.id
  try {
    const [mRes, msgRes] = await Promise.all([
      fetch(`/api/missions/${id}`),
      fetch(`/api/missions/${id}/messages`)
    ])
    if (mRes.ok) mission.value = await mRes.json()
    if (msgRes.ok) {
      const msgData = await msgRes.json()
      const newMsgs = msgData.messages || []
      if (newMsgs.length > messages.value.length) {
        animateFrom.value = messages.value.length
        messages.value = newMsgs
        await nextTick()
        if (feedContainer.value) {
          feedContainer.value.scrollTop = feedContainer.value.scrollHeight
        }
      }
    }
  } catch (e) {
    // silent poll failure
  }
}

async function approvePlan() {
  try {
    const res = await fetch(`/api/missions/${route.params.id}/approve`, { method: 'POST' })
    if (!res.ok) throw new Error('Failed to approve')
    animateFrom.value = messages.value.length
    await loadMission()
  } catch (e) {
    console.error('Failed to approve plan:', e)
  }
}

function selectAgent(agent) {
  selectedAgent.value = selectedAgent.value?.id === agent.id ? null : agent
}

function agentStatus(agentId) {
  if (!mission.value) return 'idle'
  const s = mission.value.status
  if (s === 'executing') return agentHasSpoken(agentId) ? 'active' : 'idle'
  if (s === 'planning') return 'thinking'
  if (s === 'awaiting_approval') return agentHasSpoken(agentId) ? 'active' : 'idle'
  return agentHasSpoken(agentId) ? 'active' : 'idle'
}

function agentStatusLabel(agentId) {
  const s = agentStatus(agentId)
  return { active: 'Working', thinking: 'Thinking', idle: 'Standby' }[s] || 'Standby'
}

function agentHasSpoken(agentId) {
  return messages.value.some(m => m.agent_name === agentId)
}

function getAgentCurrentTask(agentId) {
  const msgs = messages.value.filter(m => m.agent_name === agentId)
  if (!msgs.length) return null
  const last = msgs[msgs.length - 1]
  return last.metadata?.current_task || null
}

function getAgentMessages(agentId) {
  return messages.value.filter(m => m.agent_name === agentId)
}

function toggleReasoning(msgId) {
  const s = new Set(expandedReasoning.value)
  if (s.has(msgId)) s.delete(msgId)
  else s.add(msgId)
  expandedReasoning.value = s
}

function statusLabel(s) {
  return { gathering_info: 'Gathering Info', planning: 'Planning', awaiting_approval: 'Awaiting Approval', executing: 'Executing', completed: 'Completed' }[s] || s
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function renderMarkdown(text) {
  if (!text) return ''
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h2">$1</h3>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h3">$1</h4>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/^  - (.+)$/gm, '<div class="md-li">$1</div>')
  html = html.replace(/^- (.+)$/gm, '<div class="md-li">$1</div>')
  html = html.replace(/^\d+\. (.+)$/gm, '<div class="md-li md-ol">$1</div>')
  html = html.replace(/^---$/gm, '<hr class="md-hr">')
  html = html.replace(/\n\n/g, '<br><br>')
  html = html.replace(/\n/g, '<br>')
  return html
}
</script>

<style scoped>
.office-page {
  height: calc(100vh - var(--topbar-h, 56px));
  background: #0a0e17;
  overflow: hidden;
  font-family: 'Inter', sans-serif;
  display: flex;
  flex-direction: column;
}

.office-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex: 1;
}

.back-link {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: #8b949e;
  cursor: pointer;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.2s;
  white-space: nowrap;
}

.back-link:hover { color: #e6edf3; background: rgba(255,255,255,0.05); }

.header-info { min-width: 0; }

.mission-title {
  font-size: 15px;
  font-weight: 600;
  color: #e6edf3;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 500px;
}

.mission-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}

.status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.mission-status-badge.gathering_info { color: #58a6ff; }
.mission-status-badge.gathering_info .status-dot { background: #58a6ff; }
.mission-status-badge.planning { color: #a371f7; }
.mission-status-badge.planning .status-dot { background: #a371f7; }
.mission-status-badge.awaiting_approval { color: #f0883e; }
.mission-status-badge.awaiting_approval .status-dot { background: #f0883e; }
.mission-status-badge.executing { color: #3fb950; }
.mission-status-badge.executing .status-dot { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.header-right {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  color: #c9d1d9;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.view-toggle-btn:hover {
  background: rgba(255,255,255,0.08);
  color: #e6edf3;
}

.approve-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 10px rgba(46,160,67,0.25);
}

.approve-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(46,160,67,0.35);
}

.office-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.office-floor {
  padding: 20px 24px 0;
  flex-shrink: 0;
}

.floor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #e6edf3;
  margin: 0;
}

.msg-count {
  background: rgba(255,255,255,0.06);
  color: #8b949e;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 10px;
  font-weight: 500;
}

.floor-legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #8b949e;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.idle { background: #30363d; }
.legend-dot.thinking { background: #a371f7; animation: pulse 1.5s ease-in-out infinite; }
.legend-dot.active { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }

.workstations-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.workstation {
  position: relative;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.workstation:hover {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.1);
  transform: translateY(-2px);
}

.workstation.selected {
  border-color: rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.05);
}

.ws-glow {
  position: absolute;
  top: -30px;
  right: -30px;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  opacity: 0.06;
  filter: blur(20px);
  pointer-events: none;
}

.workstation.active .ws-glow { opacity: 0.12; }
.workstation.thinking .ws-glow { opacity: 0.1; }

.ws-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
}

.ws-info { min-width: 0; width: 100%; }

.ws-name {
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ws-role {
  font-size: 10px;
  color: #8b949e;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ws-status-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #484f58;
}

.ws-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #30363d;
}

.ws-status-indicator.active { color: #3fb950; }
.ws-status-indicator.active .ws-status-dot { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.ws-status-indicator.thinking { color: #a371f7; }
.ws-status-indicator.thinking .ws-status-dot { background: #a371f7; animation: pulse 1.5s ease-in-out infinite; }

.ws-current-task {
  font-size: 10px;
  color: #8b949e;
  background: rgba(255,255,255,0.03);
  padding: 3px 8px;
  border-radius: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.office-panels {
  flex: 1;
  display: flex;
  gap: 0;
  overflow: hidden;
  border-top: 1px solid rgba(255,255,255,0.06);
  margin-top: 16px;
}

.detail-panel {
  width: 360px;
  border-right: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  overflow-y: auto;
  flex-shrink: 0;
  padding: 20px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.detail-name {
  font-size: 15px;
  font-weight: 700;
  margin: 0;
}

.detail-role {
  font-size: 12px;
  color: #8b949e;
  margin-top: 2px;
}

.detail-close {
  margin-left: auto;
  background: none;
  border: none;
  color: #484f58;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.2s;
}

.detail-close:hover { color: #e6edf3; background: rgba(255,255,255,0.05); }

.detail-section {
  margin-bottom: 20px;
}

.detail-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #8b949e;
  margin-bottom: 8px;
}

.detail-description {
  font-size: 13px;
  color: #c9d1d9;
  line-height: 1.6;
  margin: 0;
}

.kpi-list, .dep-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kpi-item, .dep-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: #c9d1d9;
  line-height: 1.5;
}

.kpi-item svg, .dep-item svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.activity-item {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  padding: 10px 12px;
}

.activity-content {
  font-size: 12px;
  color: #c9d1d9;
  line-height: 1.5;
}

.activity-reasoning {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
  color: #8b949e;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255,255,255,0.04);
  font-style: italic;
}

.activity-reasoning svg {
  flex-shrink: 0;
  margin-top: 1px;
}

.discussion-feed {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 20px 0;
  min-width: 0;
}

.discussion-feed .section-title {
  margin-bottom: 12px;
  flex-shrink: 0;
}

.feed-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 16px;
}

.empty-feed {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: #484f58;
  text-align: center;
  font-size: 13px;
}

.feed-msg {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 14px;
  transition: all 0.2s;
}

.feed-msg:hover {
  background: rgba(255,255,255,0.035);
  border-color: rgba(255,255,255,0.07);
}

.feed-msg.animate-in {
  animation: slideIn 0.4s ease-out both;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.feed-msg-avatar {
  flex-shrink: 0;
  margin-top: 2px;
}

.feed-msg-body {
  flex: 1;
  min-width: 0;
}

.feed-msg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.feed-agent-name {
  font-size: 13px;
  font-weight: 700;
}

.feed-msg-time {
  font-size: 11px;
  color: #484f58;
  flex-shrink: 0;
}

.feed-msg-content {
  font-size: 13px;
  color: #c9d1d9;
  line-height: 1.55;
}

.feed-msg-content :deep(.md-h2) { font-size: 14px; color: #e6edf3; margin: 8px 0 4px; font-weight: 700; }
.feed-msg-content :deep(.md-h3) { font-size: 13px; color: #e6edf3; margin: 6px 0 3px; font-weight: 600; }
.feed-msg-content :deep(.md-li) { padding-left: 14px; position: relative; margin: 3px 0; }
.feed-msg-content :deep(.md-li::before) { content: ''; position: absolute; left: 3px; top: 8px; width: 3px; height: 3px; border-radius: 50%; background: #484f58; }
.feed-msg-content :deep(.md-hr) { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 10px 0; }

.feed-msg-reasoning {
  margin-top: 8px;
}

.reasoning-toggle {
  display: flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  color: #8b949e;
  font-size: 11px;
  cursor: pointer;
  padding: 3px 0;
  transition: color 0.2s;
}

.reasoning-toggle:hover { color: #c9d1d9; }

.reasoning-text {
  font-size: 12px;
  color: #8b949e;
  line-height: 1.5;
  font-style: italic;
  margin-top: 6px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.02);
  border-radius: 8px;
  border-left: 2px solid rgba(255,255,255,0.08);
}

.feed-msg-meta {
  margin-top: 6px;
}

.meta-tag {
  font-size: 10px;
  background: rgba(255,255,255,0.04);
  color: #8b949e;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 500;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #8b949e;
  padding: 60px;
  flex: 1;
}

.loading-dots {
  display: flex;
  gap: 6px;
}

.loading-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #30363d;
  animation: loadBounce 1.4s ease-in-out infinite;
}

.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes loadBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.error-banner {
  color: #f85149;
  background: rgba(248,81,73,0.08);
  border: 1px solid rgba(248,81,73,0.2);
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  text-align: center;
  margin: 20px;
}

@media (max-width: 1200px) {
  .workstations-grid { grid-template-columns: repeat(4, 1fr); }
  .detail-panel { width: 300px; }
}

@media (max-width: 900px) {
  .workstations-grid { grid-template-columns: repeat(2, 1fr); }
  .office-panels { flex-direction: column; }
  .detail-panel { width: 100%; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.06); max-height: 250px; }
  .mission-title { max-width: 200px; }
}
</style>
