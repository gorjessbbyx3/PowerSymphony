<template>
  <div class="mission-chat-page">
    <div class="chat-layout">
      <div class="chat-main">
        <div class="chat-header">
          <button class="back-link" @click="$router.push('/missions')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
            Missions
          </button>
          <div class="header-center" v-if="mission">
            <h2 class="mission-goal-title">{{ mission.goal }}</h2>
            <div class="mission-status-badge" :class="mission.status">
              <span class="status-dot"></span>
              {{ statusLabel(mission.status) }}
            </div>
          </div>
          <div class="header-actions" v-if="mission">
            <button
              v-if="mission.status === 'awaiting_approval'"
              class="approve-btn"
              @click="approvePlan"
            >Approve Plan</button>
          </div>
        </div>

        <div class="messages-container" ref="messagesContainer">
          <div v-if="loading" class="loading-state">
            <span class="spinner"></span> Loading mission...
          </div>

          <div v-if="loadError" class="error-banner">{{ loadError }}</div>

          <template v-else>
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="message"
              :class="[msg.role, msg.agent_name]"
            >
              <div v-if="msg.role === 'user'" class="msg-row user-row">
                <div class="msg-bubble user-bubble">
                  <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
                </div>
                <div class="msg-avatar user-avatar">You</div>
              </div>

              <div v-else-if="msg.role === 'agent'" class="msg-row agent-row">
                <div
                  class="msg-avatar agent-avatar"
                  :style="{ background: msg.agent?.color || '#58a6ff' }"
                >{{ msg.agent?.avatar || 'A' }}</div>
                <div class="msg-bubble agent-bubble">
                  <div class="msg-agent-name" :style="{ color: msg.agent?.color || '#58a6ff' }">
                    {{ msg.agent?.name || msg.agent_name }}
                    <span class="agent-role">{{ msg.agent?.role }}</span>
                  </div>
                  <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
                </div>
              </div>

              <div v-else-if="msg.role === 'system'" class="msg-row system-row">
                <div class="system-msg">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                  {{ msg.content }}
                </div>
              </div>
            </div>

            <div v-if="sending" class="message agent">
              <div class="msg-row agent-row">
                <div class="msg-avatar agent-avatar" style="background: #58a6ff">A</div>
                <div class="msg-bubble agent-bubble">
                  <div class="typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <div class="input-area">
          <div class="input-wrapper">
            <textarea
              v-model="userInput"
              class="chat-input"
              :placeholder="inputPlaceholder"
              rows="1"
              @keydown.enter.exact.prevent="sendMessage"
              @input="autoResize"
              ref="chatInput"
              :disabled="sending"
            ></textarea>
            <button class="send-btn" @click="sendMessage" :disabled="!userInput.trim() || sending">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
          <div v-if="sendError" class="error-banner small">{{ sendError }}</div>
          <div class="input-hints">
            <span v-if="mission?.status === 'gathering_info'">Answer the team leader's questions, or say "Go ahead" to start planning</span>
            <span v-else-if="mission?.status === 'awaiting_approval'">Review the plan and say "Approve" or ask for changes</span>
            <span v-else-if="mission?.status === 'executing'">Your team is working. Ask for updates anytime.</span>
          </div>
        </div>
      </div>

      <div class="team-panel" :class="{ collapsed: teamPanelCollapsed }">
        <button class="panel-toggle" @click="teamPanelCollapsed = !teamPanelCollapsed">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline :points="teamPanelCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"/>
          </svg>
        </button>
        <div class="panel-content" v-if="!teamPanelCollapsed">
          <h3 class="panel-title">Your AI Team</h3>
          <div class="team-list">
            <div v-for="agent in teamAgents" :key="agent.id" class="team-member">
              <div class="member-avatar" :style="{ background: agent.color }">{{ agent.avatar }}</div>
              <div class="member-info">
                <div class="member-name">{{ agent.name }}</div>
                <div class="member-role">{{ agent.role }}</div>
              </div>
              <div class="member-status-dot" :class="agentStatus(agent.id)"></div>
            </div>
          </div>

          <div v-if="mission?.plan" class="plan-summary">
            <h3 class="panel-title">Mission Plan</h3>
            <div class="plan-timeline">
              <div class="plan-meta">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                {{ mission.plan.timeline }}
              </div>
              <div
                v-for="(phase, i) in mission.plan.phases || []"
                :key="i"
                class="plan-phase"
              >
                <div class="phase-marker">
                  <div class="phase-dot" :class="{ active: mission.status === 'executing' && i === 0, done: false }"></div>
                  <div v-if="i < (mission.plan.phases || []).length - 1" class="phase-line"></div>
                </div>
                <div class="phase-content">
                  <div class="phase-name">{{ phase.name }}</div>
                  <div class="phase-duration">{{ phase.duration }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const mission = ref(null)
const messages = ref([])
const loading = ref(true)
const sending = ref(false)
const userInput = ref('')
const teamPanelCollapsed = ref(false)
const messagesContainer = ref(null)
const chatInput = ref(null)

const teamAgents = ref([])

const inputPlaceholder = computed(() => {
  if (!mission.value) return 'Type a message...'
  const s = mission.value.status
  if (s === 'gathering_info') return 'Answer the questions or say "Go ahead" to start planning...'
  if (s === 'awaiting_approval') return 'Say "Approve" to start, or suggest changes...'
  if (s === 'executing') return 'Ask for a progress update...'
  return 'Type a message...'
})

onMounted(async () => {
  await Promise.all([loadMission(), loadTeam()])
})

const loadError = ref('')

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
    await nextTick()
    scrollToBottom()
  } catch (e) {
    console.error('Failed to load mission:', e)
    loadError.value = e.message || 'Failed to load mission'
  } finally {
    loading.value = false
  }
}

async function loadTeam() {
  try {
    const res = await fetch('/api/missions/team/agents')
    const data = await res.json()
    teamAgents.value = data.agents || []
  } catch (e) {
    console.error('Failed to load team:', e)
  }
}

const sendError = ref('')

async function sendMessage() {
  if (!userInput.value.trim() || sending.value) return
  const content = userInput.value.trim()
  userInput.value = ''
  sendError.value = ''

  const optimisticMsg = {
    id: Date.now(),
    role: 'user',
    content,
    created_at: new Date().toISOString()
  }
  messages.value.push(optimisticMsg)
  await nextTick()
  scrollToBottom()

  sending.value = true
  try {
    const res = await fetch(`/api/missions/${route.params.id}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    })
    if (!res.ok) {
      messages.value = messages.value.filter(m => m.id !== optimisticMsg.id)
      throw new Error(`Failed to send (${res.status})`)
    }
    await loadMission()
  } catch (e) {
    console.error('Failed to send message:', e)
    sendError.value = 'Failed to send message. Please try again.'
  } finally {
    sending.value = false
    await nextTick()
    scrollToBottom()
  }
}

async function approvePlan() {
  try {
    const res = await fetch(`/api/missions/${route.params.id}/approve`, { method: 'POST' })
    if (!res.ok) throw new Error(`Failed to approve (${res.status})`)
    await loadMission()
  } catch (e) {
    console.error('Failed to approve plan:', e)
    sendError.value = 'Failed to approve plan. Please try again.'
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function agentStatus(agentId) {
  if (!mission.value) return 'idle'
  if (mission.value.status === 'executing') return 'active'
  if (mission.value.status === 'planning') return 'thinking'
  return 'idle'
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

function renderMarkdown(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

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
.mission-chat-page {
  height: calc(100vh - 55px);
  background: #0d1117;
  overflow: hidden;
}

.chat-layout {
  display: flex;
  height: 100%;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #21262d;
  background: #161b22;
  gap: 16px;
  flex-shrink: 0;
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
  border-radius: 6px;
  transition: all 0.2s;
  white-space: nowrap;
}

.back-link:hover { color: #e6edf3; background: #21262d; }

.header-center {
  flex: 1;
  min-width: 0;
}

.mission-goal-title {
  font-size: 15px;
  font-weight: 600;
  color: #e6edf3;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.header-actions { flex-shrink: 0; }

.approve-btn {
  padding: 8px 20px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.approve-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #8b949e;
  padding: 40px;
}

.msg-row {
  display: flex;
  gap: 10px;
  max-width: 85%;
}

.user-row {
  margin-left: auto;
  flex-direction: row;
}

.agent-row {
  margin-right: auto;
}

.system-row {
  margin: 0 auto;
  max-width: 100%;
}

.msg-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
  flex-shrink: 0;
}

.user-avatar {
  background: linear-gradient(135deg, #aaffcd, #99eaf9);
  color: #0d1117;
}

.agent-avatar {
  color: #fff;
}

.msg-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  line-height: 1.5;
  font-size: 14px;
}

.user-bubble {
  background: #1f6feb;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.agent-bubble {
  background: #161b22;
  border: 1px solid #21262d;
  color: #c9d1d9;
  border-bottom-left-radius: 4px;
}

.msg-agent-name {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 4px;
}

.agent-role {
  font-weight: 400;
  font-size: 11px;
  opacity: 0.6;
  margin-left: 6px;
}

.msg-content :deep(.md-h2) {
  font-size: 16px;
  color: #e6edf3;
  margin: 10px 0 6px;
}

.msg-content :deep(.md-h3) {
  font-size: 14px;
  color: #e6edf3;
  margin: 8px 0 4px;
}

.msg-content :deep(.md-li) {
  padding-left: 16px;
  position: relative;
  margin: 3px 0;
}

.msg-content :deep(.md-li::before) {
  content: '•';
  position: absolute;
  left: 4px;
  color: #484f58;
}

.msg-content :deep(.md-hr) {
  border: none;
  border-top: 1px solid #30363d;
  margin: 12px 0;
}

.system-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #8b949e;
  font-size: 13px;
  background: #161b2266;
  padding: 8px 16px;
  border-radius: 20px;
  border: 1px solid #21262d;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-indicator span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #484f58;
  animation: typing 1.2s ease-in-out infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-5px); opacity: 1; }
}

.input-area {
  padding: 16px 20px;
  border-top: 1px solid #21262d;
  background: #161b22;
  flex-shrink: 0;
}

.input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 12px;
  padding: 8px 12px;
  transition: border-color 0.2s;
}

.input-wrapper:focus-within {
  border-color: #58a6ff;
  box-shadow: 0 0 0 3px rgba(88,166,255,0.1);
}

.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #e6edf3;
  font-size: 14px;
  font-family: 'Inter', sans-serif;
  resize: none;
  min-height: 24px;
  max-height: 120px;
  outline: none;
  padding: 4px 0;
}

.chat-input::placeholder { color: #484f58; }

.send-btn {
  background: linear-gradient(135deg, #238636, #2ea043);
  border: none;
  color: #fff;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) { transform: scale(1.05); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.input-hints {
  text-align: center;
  color: #484f58;
  font-size: 12px;
  margin-top: 6px;
}

.team-panel {
  width: 280px;
  border-left: 1px solid #21262d;
  background: #161b22;
  flex-shrink: 0;
  position: relative;
  transition: width 0.2s;
  overflow-y: auto;
}

.team-panel.collapsed { width: 36px; }

.panel-toggle {
  position: absolute;
  top: 12px;
  left: 8px;
  background: none;
  border: none;
  color: #8b949e;
  cursor: pointer;
  padding: 4px;
  z-index: 1;
}

.panel-toggle:hover { color: #e6edf3; }

.panel-content {
  padding: 16px;
  padding-top: 40px;
}

.panel-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #8b949e;
  margin: 0 0 12px 0;
  font-weight: 600;
}

.team-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 24px;
}

.team-member {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.team-member:hover { background: #21262d; }

.member-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
  color: #fff;
  flex-shrink: 0;
}

.member-info { flex: 1; min-width: 0; }

.member-name {
  font-size: 13px;
  font-weight: 600;
  color: #e6edf3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.member-role {
  font-size: 11px;
  color: #8b949e;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.member-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.member-status-dot.idle { background: #30363d; }
.member-status-dot.thinking { background: #f0883e; animation: pulse 1.5s ease-in-out infinite; }
.member-status-dot.active { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }

.plan-summary { margin-top: 8px; }

.plan-timeline { display: flex; flex-direction: column; gap: 0; }

.plan-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #8b949e;
  font-size: 13px;
  margin-bottom: 12px;
}

.plan-phase {
  display: flex;
  gap: 10px;
}

.phase-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 12px;
  flex-shrink: 0;
}

.phase-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #30363d;
  background: transparent;
  flex-shrink: 0;
}

.phase-dot.active { border-color: #3fb950; background: #3fb950; }
.phase-dot.done { border-color: #8b949e; background: #8b949e; }

.phase-line {
  width: 2px;
  flex: 1;
  background: #21262d;
  min-height: 20px;
}

.phase-content {
  padding-bottom: 16px;
}

.phase-name {
  font-size: 13px;
  font-weight: 600;
  color: #c9d1d9;
  line-height: 1.3;
}

.phase-duration {
  font-size: 11px;
  color: #8b949e;
  margin-top: 2px;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.2);
  border-top-color: #58a6ff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.error-banner {
  color: #f85149;
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid rgba(248, 81, 73, 0.3);
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  text-align: center;
}

.error-banner.small {
  padding: 6px 12px;
  margin-top: 6px;
  font-size: 12px;
}

@media (max-width: 768px) {
  .team-panel { display: none; }
  .msg-row { max-width: 95%; }
}
</style>
