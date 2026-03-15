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
            <button class="view-toggle-btn" @click="$router.push(`/missions/${route.params.id}/office`)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
              Headquarters
            </button>
            <button
              v-if="mission.status === 'awaiting_approval'"
              class="approve-btn"
              @click="approvePlan"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              Approve Plan
            </button>
          </div>
        </div>

        <div class="messages-container" ref="messagesContainer">
          <div v-if="loading" class="loading-state">
            <div class="loading-dots">
              <span></span><span></span><span></span>
            </div>
            <p>Loading mission...</p>
          </div>

          <div v-if="loadError" class="error-banner">{{ loadError }}</div>

          <template v-if="!loading && !loadError">
            <div
              v-for="(msg, idx) in messages"
              :key="msg.id"
              class="message"
              :class="[msg.role, { 'animate-in': idx >= animateFromIndex }]"
              :style="{ animationDelay: idx >= animateFromIndex ? `${(idx - animateFromIndex) * 0.08}s` : '0s' }"
            >
              <div v-if="msg.role === 'user'" class="msg-row user-row">
                <div class="msg-bubble user-bubble">
                  <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
                </div>
                <div class="msg-avatar user-avatar">You</div>
              </div>

              <div v-else-if="msg.role === 'agent'" class="msg-row agent-row">
                <div class="msg-avatar agent-avatar" :style="{ background: msg.agent?.color || '#58a6ff' }">
                  {{ msg.agent?.avatar || 'A' }}
                </div>
                <div class="msg-bubble agent-bubble" :style="{ borderColor: (msg.agent?.color || '#58a6ff') + '20' }">
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

            <div v-if="sending" class="message agent animate-in">
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
          <div class="input-wrapper" :class="{ focused: inputFocused }">
            <textarea
              v-model="userInput"
              class="chat-input"
              :placeholder="inputPlaceholder"
              rows="1"
              @keydown.enter.exact.prevent="sendMessage"
              @input="autoResize"
              @focus="inputFocused = true"
              @blur="inputFocused = false"
              ref="chatInput"
              :disabled="sending"
            ></textarea>
            <button class="send-btn" @click="sendMessage" :disabled="!userInput.trim() || sending">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
          <div v-if="sendError" class="error-banner small">{{ sendError }}</div>
          <div class="input-hints">
            <span v-if="mission?.status === 'gathering_info'">Answer the team's questions, or say <strong>"Go ahead"</strong> to start planning</span>
            <span v-else-if="mission?.status === 'awaiting_approval'">Review the plan above, then say <strong>"Approve"</strong> or request changes</span>
            <span v-else-if="mission?.status === 'executing'">
              Your team is running autonomously.
              <a class="hq-link" @click.prevent="$router.push(`/missions/${route.params.id}/office`)">Watch them in HQ</a>
              or ask for updates here.
            </span>
          </div>
        </div>
      </div>

      <div class="team-panel" :class="{ collapsed: teamPanelCollapsed }">
        <button class="panel-toggle" @click="teamPanelCollapsed = !teamPanelCollapsed" :title="teamPanelCollapsed ? 'Show team' : 'Hide team'">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline :points="teamPanelCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"/>
          </svg>
        </button>
        <div class="panel-content" v-if="!teamPanelCollapsed">
          <h3 class="panel-title">Your AI Team</h3>
          <div class="team-list">
            <div v-for="agent in teamAgents" :key="agent.id" class="team-member" :class="{ active: agentHasSpoken(agent.id) }">
              <div class="member-avatar" :style="{ background: agent.color }">{{ agent.avatar }}</div>
              <div class="member-info">
                <div class="member-name">{{ agent.name.split('—')[0].trim() }}</div>
                <div class="member-role">{{ agent.role }}</div>
              </div>
              <div class="member-status-dot" :class="agentStatus(agent.id)"></div>
            </div>
          </div>

          <div v-if="mission?.plan" class="plan-summary">
            <h3 class="panel-title">Mission Plan</h3>
            <div class="plan-meta-row">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <span>{{ mission.plan.timeline }}</span>
            </div>
            <div class="plan-phases">
              <div v-for="(phase, i) in mission.plan.phases || []" :key="i" class="phase-item">
                <div class="phase-marker-wrap">
                  <div class="phase-dot" :class="{ active: mission.status === 'executing' && i === 0 }"></div>
                  <div v-if="i < (mission.plan.phases || []).length - 1" class="phase-line"></div>
                </div>
                <div class="phase-detail">
                  <div class="phase-name">{{ phase.name }}</div>
                  <div class="phase-duration">{{ phase.duration }}</div>
                  <div class="phase-assignees">
                    <div v-for="aId in (phase.assigned_to || []).slice(0, 3)" :key="aId" class="phase-avatar" :style="{ background: getAgentColor(aId) }">
                      {{ getAgentAvatar(aId) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="mission?.plan?.risks" class="risks-section">
            <h3 class="panel-title">Risks</h3>
            <div v-for="(risk, i) in mission.plan.risks.slice(0, 3)" :key="i" class="risk-item">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f0883e" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              <span>{{ risk }}</span>
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
const inputFocused = ref(false)
const teamAgents = ref([])
const animateFromIndex = ref(0)
const loadError = ref('')
const sendError = ref('')

const agentMap = computed(() => {
  const map = {}
  teamAgents.value.forEach(a => { map[a.id] = a })
  return map
})

const inputPlaceholder = computed(() => {
  if (!mission.value) return 'Type a message...'
  const s = mission.value.status
  if (s === 'gathering_info') return 'Answer the questions or say "Go ahead"...'
  if (s === 'awaiting_approval') return 'Say "Approve" or suggest changes...'
  if (s === 'executing') return 'Ask for a progress update...'
  return 'Type a message...'
})

onMounted(async () => {
  await Promise.all([loadMission(), loadTeam()])
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
    animateFromIndex.value = messages.value.length
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
    if (res.ok) {
      const data = await res.json()
      teamAgents.value = data.agents || []
    }
  } catch (e) {
    console.error('Failed to load team:', e)
  }
}

async function sendMessage() {
  if (!userInput.value.trim() || sending.value) return
  const content = userInput.value.trim()
  userInput.value = ''
  sendError.value = ''

  const prevLen = messages.value.length
  const optimisticMsg = {
    id: Date.now(),
    role: 'user',
    content,
    created_at: new Date().toISOString()
  }
  animateFromIndex.value = prevLen
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
    animateFromIndex.value = prevLen + 1
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
    animateFromIndex.value = messages.value.length
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

function agentHasSpoken(agentId) {
  return messages.value.some(m => m.agent_name === agentId)
}

function agentStatus(agentId) {
  if (!mission.value) return 'idle'
  if (mission.value.status === 'executing') return agentHasSpoken(agentId) ? 'active' : 'idle'
  if (mission.value.status === 'planning') return 'thinking'
  return agentHasSpoken(agentId) ? 'spoke' : 'idle'
}

function getAgentColor(id) { return agentMap.value[id]?.color || '#58a6ff' }
function getAgentAvatar(id) { return agentMap.value[id]?.avatar || '?' }

function statusLabel(s) {
  return { gathering_info: 'Gathering Info', planning: 'Planning', awaiting_approval: 'Awaiting Approval', executing: 'Executing', completed: 'Completed' }[s] || s
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
.mission-chat-page {
  height: calc(100vh - var(--topbar-h, 56px));
  background: #0a0e17;
  overflow: hidden;
  font-family: 'Inter', sans-serif;
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
  border-bottom: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  gap: 16px;
  flex-shrink: 0;
  backdrop-filter: blur(10px);
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

.header-center { flex: 1; min-width: 0; }

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

.header-actions { flex-shrink: 0; display: flex; gap: 8px; align-items: center; }

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

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-behavior: smooth;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #8b949e;
  padding: 60px;
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

.message.animate-in {
  animation: slideIn 0.4s ease-out both;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-row {
  display: flex;
  gap: 10px;
  max-width: 82%;
}

.user-row { margin-left: auto; }
.agent-row { margin-right: auto; }
.system-row { margin: 4px auto; max-width: 100%; }

.msg-avatar {
  width: 34px;
  height: 34px;
  border-radius: 12px;
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
  border-radius: 12px;
}

.agent-avatar { color: #fff; border-radius: 12px; }

.msg-bubble {
  padding: 14px 18px;
  border-radius: 18px;
  line-height: 1.55;
  font-size: 14px;
}

.user-bubble {
  background: linear-gradient(135deg, #1f6feb, #388bfd);
  color: #fff;
  border-bottom-right-radius: 6px;
  box-shadow: 0 2px 12px rgba(31,111,235,0.2);
}

.agent-bubble {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  color: #c9d1d9;
  border-bottom-left-radius: 6px;
}

.msg-agent-name {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 6px;
}

.agent-role {
  font-weight: 400;
  font-size: 11px;
  opacity: 0.5;
  margin-left: 6px;
}

.msg-content :deep(.md-h2) { font-size: 16px; color: #e6edf3; margin: 12px 0 6px; font-weight: 700; }
.msg-content :deep(.md-h3) { font-size: 14px; color: #e6edf3; margin: 10px 0 4px; font-weight: 600; }
.msg-content :deep(.md-li) { padding-left: 16px; position: relative; margin: 4px 0; }
.msg-content :deep(.md-li::before) { content: ''; position: absolute; left: 4px; top: 9px; width: 4px; height: 4px; border-radius: 50%; background: #484f58; }
.msg-content :deep(.md-hr) { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 14px 0; }

.system-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #8b949e;
  font-size: 13px;
  background: rgba(255,255,255,0.02);
  padding: 8px 16px;
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.04);
}

.typing-indicator { display: flex; gap: 4px; padding: 4px 0; }
.typing-indicator span {
  width: 7px; height: 7px; border-radius: 50%; background: #484f58;
  animation: typing 1.2s ease-in-out infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
  30% { transform: translateY(-5px); opacity: 1; }
}

.input-area {
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  flex-shrink: 0;
  backdrop-filter: blur(10px);
}

.input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 10px 14px;
  transition: all 0.3s;
}

.input-wrapper.focused {
  border-color: rgba(88,166,255,0.4);
  box-shadow: 0 0 0 3px rgba(88,166,255,0.08);
  background: rgba(255,255,255,0.04);
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
  padding: 2px 0;
}

.chat-input::placeholder { color: #484f58; }

.send-btn {
  background: linear-gradient(135deg, #238636, #2ea043);
  border: none;
  color: #fff;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(46,160,67,0.2);
}

.send-btn:hover:not(:disabled) { transform: scale(1.05); box-shadow: 0 4px 12px rgba(46,160,67,0.3); }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; box-shadow: none; }

.input-hints {
  text-align: center;
  color: #484f58;
  font-size: 12px;
  margin-top: 8px;
}

.input-hints strong { color: #8b949e; }
.hq-link { color: #58a6ff; cursor: pointer; text-decoration: none; font-weight: 500; }
.hq-link:hover { color: #79c0ff; text-decoration: underline; }

.error-banner {
  color: #f85149;
  background: rgba(248,81,73,0.08);
  border: 1px solid rgba(248,81,73,0.2);
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  text-align: center;
}

.error-banner.small { padding: 6px 12px; margin-top: 6px; font-size: 12px; }

.team-panel {
  width: 300px;
  border-left: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  flex-shrink: 0;
  position: relative;
  transition: width 0.3s;
  overflow-y: auto;
}

.team-panel.collapsed { width: 40px; }

.panel-toggle {
  position: absolute;
  top: 14px;
  left: 10px;
  background: none;
  border: none;
  color: #8b949e;
  cursor: pointer;
  padding: 4px;
  z-index: 1;
  transition: color 0.2s;
}

.panel-toggle:hover { color: #e6edf3; }

.panel-content { padding: 16px; padding-top: 44px; }

.panel-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #484f58;
  margin: 0 0 14px;
  font-weight: 700;
}

.team-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 28px;
}

.team-member {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  transition: all 0.2s;
}

.team-member:hover { background: rgba(255,255,255,0.04); }
.team-member.active { background: rgba(255,255,255,0.03); }

.member-avatar {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
  color: #fff;
  flex-shrink: 0;
}

.member-info { flex: 1; min-width: 0; }
.member-name { font-size: 13px; font-weight: 600; color: #e6edf3; }
.member-role { font-size: 11px; color: #484f58; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.member-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.member-status-dot.idle { background: #21262d; }
.member-status-dot.spoke { background: #30363d; }
.member-status-dot.thinking { background: #f0883e; animation: pulse 1.5s ease-in-out infinite; }
.member-status-dot.active { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }

.plan-summary { margin-bottom: 24px; }

.plan-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #8b949e;
  font-size: 13px;
  margin-bottom: 14px;
}

.plan-phases { display: flex; flex-direction: column; }

.phase-item { display: flex; gap: 10px; }

.phase-marker-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 14px;
  flex-shrink: 0;
}

.phase-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #21262d;
  background: transparent;
  flex-shrink: 0;
}

.phase-dot.active { border-color: #3fb950; background: #3fb950; box-shadow: 0 0 8px rgba(63,185,80,0.4); }

.phase-line { width: 2px; flex: 1; background: #21262d; min-height: 20px; }

.phase-detail { padding-bottom: 16px; }
.phase-name { font-size: 13px; font-weight: 600; color: #c9d1d9; line-height: 1.3; }
.phase-duration { font-size: 11px; color: #484f58; margin-top: 2px; }

.phase-assignees {
  display: flex;
  margin-top: 6px;
}

.phase-avatar {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 9px;
  color: #fff;
  border: 2px solid #0a0e17;
  margin-right: -4px;
}

.risks-section { margin-bottom: 20px; }

.risk-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 8px;
  line-height: 1.4;
}

.risk-item svg { flex-shrink: 0; margin-top: 1px; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@media (max-width: 768px) {
  .team-panel { display: none; }
  .msg-row { max-width: 95%; }
}
</style>
