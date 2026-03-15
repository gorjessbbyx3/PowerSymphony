<template>
  <div class="office3d-page">
    <div class="office3d-header">
      <div class="header-left">
        <button class="back-link" @click="$router.push(missionId ? `/missions/${missionId}/office` : '/team')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          {{ missionId ? 'HQ Feed' : 'Team' }}
        </button>
        <h2 class="page-title">AI Team Office</h2>
        <div class="mission-badge" v-if="mission">
          <span class="status-dot" :class="mission.status"></span>
          {{ mission.goal?.substring(0, 50) }}{{ mission.goal?.length > 50 ? '...' : '' }}
        </div>
      </div>
      <div class="header-right">
        <div class="zoom-controls">
          <button @click="zoomIn" class="zoom-btn">+</button>
          <button @click="zoomOut" class="zoom-btn">-</button>
        </div>
      </div>
    </div>

    <div class="office3d-viewport" ref="viewport" @wheel.prevent="onWheel">
      <div class="office3d-scene" :style="sceneStyle">
        <!-- Floor grid -->
        <div class="floor-grid">
          <div v-for="i in 120" :key="'g'+i" class="grid-cell"></div>
        </div>

        <!-- Meeting Room (center) -->
        <div class="room meeting-room" :class="{ active: meetingActive }">
          <div class="room-floor"></div>
          <div class="room-wall-back"></div>
          <div class="room-wall-left"></div>
          <div class="room-label">Meeting Room</div>
          <div class="meeting-table"></div>
          <!-- Agents in meeting -->
          <div v-for="(agent, i) in meetingAgents" :key="'m'+agent.id"
            class="agent-figure meeting-agent"
            :style="meetingAgentPos(i)"
            :class="{ speaking: isSpeaking(agent.id) }"
          >
            <div class="agent-body" :style="{ '--agent-color': agent.color }">
              <div class="agent-head">{{ agent.avatar }}</div>
              <div class="agent-torso"></div>
            </div>
            <div class="agent-nameplate">{{ agent.name.split('—')[0].trim() }}</div>
            <div class="speech-indicator" v-if="isSpeaking(agent.id)">
              <span></span><span></span><span></span>
            </div>
          </div>
          <div class="meeting-status" v-if="meetingActive">
            <div class="meeting-pulse"></div>
            Meeting in progress
          </div>
        </div>

        <!-- Individual offices -->
        <div v-for="(agent, idx) in agents" :key="agent.id"
          class="room agent-office"
          :class="{ active: isAgentActive(agent.id), focused: focusedAgent === agent.id }"
          :style="officePosition(idx)"
          @click="focusAgent(agent.id)"
        >
          <div class="room-floor" :style="{ background: agent.color + '08' }"></div>
          <div class="room-wall-back" :style="{ borderColor: agent.color + '30' }"></div>
          <div class="room-wall-left" :style="{ borderColor: agent.color + '20' }"></div>
          <div class="room-label" :style="{ color: agent.color }">{{ agent.name.split('—')[0].trim() }}</div>
          <div class="office-role">{{ agent.role.split('&')[0].trim() }}</div>

          <!-- Desk -->
          <div class="desk">
            <div class="desk-surface"></div>
            <div class="monitor">
              <div class="monitor-screen" :class="agentWorkStatus(agent.id)">
                <div class="screen-lines" v-if="isAgentActive(agent.id)">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Agent avatar in office -->
          <div class="agent-figure in-office" :class="{ working: isAgentActive(agent.id), idle: !isAgentActive(agent.id) }">
            <div class="agent-body" :style="{ '--agent-color': agent.color }">
              <div class="agent-head">{{ agent.avatar }}</div>
              <div class="agent-torso"></div>
              <div class="agent-arms" v-if="isAgentActive(agent.id)"></div>
            </div>
            <div class="agent-status-bubble" v-if="lastMessage(agent.id)" :class="lastMessageType(agent.id)">
              {{ lastMessage(agent.id)?.substring(0, 45) }}{{ (lastMessage(agent.id)?.length || 0) > 45 ? '...' : '' }}
            </div>
            <div class="thinking-dots" v-if="isThinking(agent.id)">
              <span></span><span></span><span></span>
            </div>
          </div>

          <!-- Leader crown -->
          <div class="office-crown" v-if="agent.id === electedLeaderId">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="#ffd700" stroke="#ffd700" stroke-width="1"><path d="M2 4l3 12h14l3-12-6 7-4-9-4 9-6-7z"/><rect x="5" y="18" width="14" height="3" rx="1"/></svg>
          </div>

          <!-- Progress indicator -->
          <div class="office-progress" v-if="agentProgress(agent.id) != null">
            <div class="office-progress-fill" :style="{ width: agentProgress(agent.id) + '%', background: agent.color }"></div>
          </div>
        </div>

        <!-- Walking agents (between offices) -->
        <div v-for="walker in walkingAgents" :key="'w'+walker.id"
          class="agent-figure walking"
          :style="walker.style"
        >
          <div class="agent-body" :style="{ '--agent-color': walker.color }">
            <div class="agent-head">{{ walker.avatar }}</div>
            <div class="agent-torso"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Info panel when agent is focused -->
    <div class="agent-info-panel" v-if="focusedAgent && focusedAgentData" @click.self="focusedAgent = null">
      <div class="info-card">
        <button class="info-close" @click="focusedAgent = null">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
        <div class="info-header">
          <div class="info-avatar" :style="{ background: focusedAgentData.color }">{{ focusedAgentData.avatar }}</div>
          <div>
            <h3 :style="{ color: focusedAgentData.color }">{{ focusedAgentData.name.split('—')[0].trim() }}</h3>
            <div class="info-role">{{ focusedAgentData.role }}</div>
            <div class="info-leader" v-if="focusedAgent === electedLeaderId">Project Lead</div>
          </div>
        </div>
        <div class="info-status">
          <span class="info-status-dot" :class="isAgentActive(focusedAgent) ? 'active' : 'idle'"></span>
          {{ isAgentActive(focusedAgent) ? 'Working' : 'Idle' }}
          <span v-if="agentProgress(focusedAgent) != null" class="info-progress">{{ agentProgress(focusedAgent) }}%</span>
        </div>
        <div class="info-message" v-if="lastMessage(focusedAgent)">
          <div class="info-msg-label">Latest</div>
          <p>{{ lastMessage(focusedAgent) }}</p>
        </div>
        <div class="info-thinking" v-if="lastThinking(focusedAgent)">
          <div class="info-msg-label">Thinking</div>
          <p>{{ lastThinking(focusedAgent) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const missionId = computed(() => route.params.id)

const mission = ref(null)
const messages = ref([])
const teamAgents = ref([])
const zoom = ref(1)
const focusedAgent = ref(null)
let pollInterval = null

const agents = computed(() => teamAgents.value.filter(a => a.id !== 'team_leader'))
const leaderAgent = computed(() => teamAgents.value.find(a => a.id === 'team_leader'))

const electedLeaderId = computed(() => {
  const ctx = mission.value?.context
  if (!ctx) return 'team_leader'
  const context = typeof ctx === 'string' ? JSON.parse(ctx) : ctx
  return context?.elected_leader || 'team_leader'
})

const focusedAgentData = computed(() => {
  if (!focusedAgent.value) return null
  return teamAgents.value.find(a => a.id === focusedAgent.value)
})

const meetingActive = computed(() => {
  if (!mission.value) return false
  return mission.value.status === 'planning' || mission.value.status === 'gathering_info'
})

const meetingAgents = computed(() => {
  if (!meetingActive.value) return []
  return teamAgents.value.slice(0, 5)
})

// Simulate agents walking between offices
const walkingAgents = computed(() => {
  if (!mission.value || mission.value.status !== 'executing') return []
  const walkers = []
  const convos = messages.value.filter(m => m.metadata?.type === 'conversation' || m.metadata?.type === 'handoff')
  const recent = convos.slice(-2)
  recent.forEach((m, i) => {
    const agent = teamAgents.value.find(a => a.id === m.agent_name)
    if (agent && m.metadata?.to_agent) {
      const fromIdx = agents.value.findIndex(a => a.id === m.agent_name)
      const toIdx = agents.value.findIndex(a => a.id === m.metadata.to_agent)
      if (fromIdx >= 0 && toIdx >= 0) {
        const fromPos = officePositionXY(fromIdx)
        const toPos = officePositionXY(toIdx)
        const midX = (fromPos.x + toPos.x) / 2
        const midY = (fromPos.y + toPos.y) / 2
        walkers.push({
          id: agent.id + i,
          avatar: agent.avatar,
          color: agent.color,
          style: { left: midX + 'px', top: midY + 'px' }
        })
      }
    }
  })
  return walkers
})

const sceneStyle = computed(() => ({
  transform: `scale(${zoom.value})`,
  transformOrigin: 'center center'
}))

function officePosition(idx) {
  const positions = [
    { left: '40px', top: '30px' },    // top-left
    { left: '290px', top: '30px' },   // top-center
    { left: '540px', top: '30px' },   // top-right
    { left: '40px', top: '290px' },   // bottom-left
    { left: '540px', top: '290px' },  // bottom-right
    { left: '40px', top: '550px' },   // far-bottom-left
    { left: '540px', top: '550px' },  // far-bottom-right
  ]
  return positions[idx] || positions[0]
}

function officePositionXY(idx) {
  const style = officePosition(idx)
  return {
    x: parseInt(style.left) + 100,
    y: parseInt(style.top) + 100
  }
}

function meetingAgentPos(i) {
  const positions = [
    { left: '30px', top: '60px' },
    { left: '110px', top: '40px' },
    { left: '170px', top: '70px' },
    { left: '70px', top: '100px' },
    { left: '150px', top: '110px' },
  ]
  return positions[i] || positions[0]
}

function isAgentActive(agentId) {
  if (!mission.value) return false
  if (mission.value.status === 'executing') return agentHasSpoken(agentId)
  if (mission.value.status === 'planning') return true
  return agentHasSpoken(agentId)
}

function isThinking(agentId) {
  if (!mission.value) return false
  return mission.value.status === 'planning'
}

function isSpeaking(agentId) {
  const recent = messages.value.slice(-5)
  return recent.some(m => m.agent_name === agentId)
}

function agentHasSpoken(agentId) {
  return messages.value.some(m => m.agent_name === agentId)
}

function agentWorkStatus(agentId) {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (m.agent_name === agentId && m.metadata?.status) return m.metadata.status
  }
  return 'idle'
}

function agentProgress(agentId) {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (m.agent_name === agentId && m.metadata?.progress != null) return m.metadata.progress
  }
  return null
}

function lastMessage(agentId) {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].agent_name === agentId) return messages.value[i].content
  }
  return null
}

function lastThinking(agentId) {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (m.agent_name === agentId && m.metadata?.thinking) return m.metadata.thinking
  }
  return null
}

function lastMessageType(agentId) {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (m.agent_name === agentId && m.metadata?.type) return m.metadata.type
  }
  return ''
}

function focusAgent(id) {
  focusedAgent.value = focusedAgent.value === id ? null : id
}

function zoomIn() { zoom.value = Math.min(zoom.value + 0.15, 2) }
function zoomOut() { zoom.value = Math.max(zoom.value - 0.15, 0.4) }
function onWheel(e) {
  if (e.deltaY < 0) zoomIn()
  else zoomOut()
}

onMounted(async () => {
  await loadTeam()
  if (missionId.value) {
    await loadMission()
    pollInterval = setInterval(pollForUpdates, 5000)
  }
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

async function loadTeam() {
  try {
    const res = await fetch('/api/missions/team/agents')
    if (res.ok) {
      const data = await res.json()
      teamAgents.value = data.agents || []
    }
  } catch (e) { console.error(e) }
}

async function loadMission() {
  try {
    const id = missionId.value
    const [mRes, msgRes] = await Promise.all([
      fetch(`/api/missions/${id}`),
      fetch(`/api/missions/${id}/messages`)
    ])
    if (mRes.ok) mission.value = await mRes.json()
    if (msgRes.ok) {
      const data = await msgRes.json()
      messages.value = data.messages || []
    }
  } catch (e) { /* silent */ }
}

async function pollForUpdates() {
  await loadMission()
}
</script>

<style scoped>
.office3d-page { height: calc(100vh - var(--topbar-h, 56px)); background: #080c14; overflow: hidden; font-family: 'Inter', sans-serif; display: flex; flex-direction: column; position: relative; }

.office3d-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; border-bottom: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); flex-shrink: 0; }
.header-left { display: flex; align-items: center; gap: 14px; }
.back-link { display: flex; align-items: center; gap: 4px; background: none; border: none; color: #8b949e; cursor: pointer; font-size: 13px; padding: 6px 10px; border-radius: 8px; transition: all 0.2s; }
.back-link:hover { color: #e6edf3; background: rgba(255,255,255,0.05); }
.page-title { font-size: 16px; font-weight: 700; color: #e6edf3; margin: 0; }
.mission-badge { font-size: 11px; color: #8b949e; display: flex; align-items: center; gap: 6px; padding: 4px 10px; background: rgba(255,255,255,0.03); border-radius: 8px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #30363d; }
.status-dot.executing { background: #3fb950; animation: pulse 1.5s infinite; }
.status-dot.planning { background: #a371f7; animation: pulse 1.5s infinite; }
.header-right { display: flex; gap: 6px; }
.zoom-controls { display: flex; gap: 4px; }
.zoom-btn { width: 28px; height: 28px; border-radius: 8px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); color: #c9d1d9; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; }
.zoom-btn:hover { background: rgba(255,255,255,0.08); }

/* Viewport */
.office3d-viewport { flex: 1; overflow: hidden; display: flex; align-items: center; justify-content: center; perspective: 1200px; }
.office3d-scene { width: 780px; height: 800px; position: relative; transform-style: preserve-3d; transition: transform 0.3s ease; }

/* Floor grid */
.floor-grid { position: absolute; inset: 0; display: grid; grid-template-columns: repeat(12, 1fr); grid-template-rows: repeat(10, 1fr); opacity: 0.15; pointer-events: none; }
.grid-cell { border: 1px solid rgba(88,166,255,0.15); }

/* Room base styles */
.room { position: absolute; border-radius: 12px; transition: all 0.3s; cursor: pointer; }
.room:hover { transform: translateY(-2px); }
.room-floor { position: absolute; inset: 0; border-radius: 12px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); }
.room.active .room-floor { border-color: rgba(255,255,255,0.12); background: rgba(255,255,255,0.03); }
.room-wall-back { position: absolute; top: 0; left: 0; right: 0; height: 8px; background: rgba(255,255,255,0.04); border-radius: 12px 12px 0 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
.room-wall-left { position: absolute; top: 0; left: 0; bottom: 0; width: 8px; background: rgba(255,255,255,0.03); border-radius: 12px 0 0 12px; border-right: 1px solid rgba(255,255,255,0.04); }
.room-label { position: absolute; top: 14px; left: 16px; font-size: 11px; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }

/* Meeting room */
.meeting-room { left: 230px; top: 250px; width: 250px; height: 170px; z-index: 5; }
.meeting-room.active { box-shadow: 0 0 40px rgba(163,113,247,0.1); }
.meeting-room.active .room-floor { border-color: rgba(163,113,247,0.2); background: rgba(163,113,247,0.03); }
.meeting-table { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 100px; height: 50px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 25px; }
.meeting-status { position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%); font-size: 9px; color: #a371f7; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.meeting-pulse { width: 6px; height: 6px; border-radius: 50%; background: #a371f7; animation: pulse 1.5s infinite; }

/* Agent office */
.agent-office { width: 200px; height: 210px; }
.agent-office.focused { z-index: 10; box-shadow: 0 0 30px rgba(88,166,255,0.15); }
.office-role { position: absolute; top: 28px; left: 16px; font-size: 9px; color: #484f58; }
.office-crown { position: absolute; top: 10px; right: 12px; }

/* Desk */
.desk { position: absolute; bottom: 55px; left: 50%; transform: translateX(-50%); width: 90px; height: 35px; }
.desk-surface { position: absolute; bottom: 0; width: 100%; height: 8px; background: rgba(139,148,158,0.12); border-radius: 4px; border: 1px solid rgba(255,255,255,0.05); }
.monitor { position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); width: 50px; height: 30px; }
.monitor-screen { width: 100%; height: 100%; background: rgba(10,14,23,0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; position: relative; }
.monitor-screen.working { border-color: rgba(63,185,80,0.3); }
.monitor-screen.collaborating { border-color: rgba(88,166,255,0.3); }
.monitor-screen.blocked { border-color: rgba(248,81,73,0.3); }
.screen-lines { display: flex; flex-direction: column; gap: 3px; padding: 4px; }
.screen-lines span { height: 2px; background: rgba(63,185,80,0.4); border-radius: 1px; animation: screenFlicker 2s infinite; }
.screen-lines span:nth-child(2) { width: 70%; animation-delay: 0.3s; }
.screen-lines span:nth-child(3) { width: 40%; animation-delay: 0.6s; }
@keyframes screenFlicker { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }

/* Agent figures */
.agent-figure { position: absolute; z-index: 3; }
.agent-body { display: flex; flex-direction: column; align-items: center; }
.agent-head { width: 28px; height: 28px; border-radius: 50%; background: var(--agent-color); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 11px; color: #fff; border: 2px solid rgba(255,255,255,0.15); z-index: 1; position: relative; }
.agent-torso { width: 22px; height: 18px; background: var(--agent-color); opacity: 0.6; border-radius: 0 0 8px 8px; margin-top: -4px; }
.agent-arms { position: absolute; top: 30px; width: 34px; height: 4px; background: var(--agent-color); opacity: 0.4; border-radius: 2px; animation: typing 0.5s infinite alternate; }
@keyframes typing { from { transform: scaleX(0.9); } to { transform: scaleX(1.1); } }

/* In-office agent */
.in-office { bottom: 95px; left: 50%; transform: translateX(-50%); }
.in-office.working .agent-head { box-shadow: 0 0 12px var(--agent-color); }
.in-office.idle { opacity: 0.5; }

/* Agent name & status */
.agent-nameplate { font-size: 8px; color: #8b949e; text-align: center; margin-top: 2px; white-space: nowrap; }
.agent-status-bubble { position: absolute; bottom: 55px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 4px 8px; font-size: 8px; color: #c9d1d9; white-space: nowrap; max-width: 180px; overflow: hidden; text-overflow: ellipsis; backdrop-filter: blur(4px); }
.agent-status-bubble.blocker { border-color: rgba(248,81,73,0.3); color: #f85149; }
.agent-status-bubble.breakthrough { border-color: rgba(255,215,0,0.3); color: #ffd700; }
.agent-status-bubble.debate { border-color: rgba(240,136,62,0.3); color: #f0883e; }

/* Thinking animation */
.thinking-dots, .speech-indicator { display: flex; gap: 3px; justify-content: center; margin-top: 4px; }
.thinking-dots span, .speech-indicator span { width: 4px; height: 4px; border-radius: 50%; background: #a371f7; animation: dotBounce 1.4s ease-in-out infinite; }
.speech-indicator span { background: #3fb950; }
.thinking-dots span:nth-child(2), .speech-indicator span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3), .speech-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotBounce { 0%, 80%, 100% { transform: scale(0.6); } 40% { transform: scale(1.2); } }

/* Meeting agents */
.meeting-agent { z-index: 6; }
.meeting-agent.speaking .agent-head { box-shadow: 0 0 12px var(--agent-color); animation: speakPulse 1.5s infinite; }
@keyframes speakPulse { 0%, 100% { box-shadow: 0 0 8px var(--agent-color); } 50% { box-shadow: 0 0 20px var(--agent-color); } }

/* Walking agents */
.walking { z-index: 8; animation: walkBob 0.6s infinite alternate; }
@keyframes walkBob { from { transform: translateY(0); } to { transform: translateY(-4px); } }

/* Progress bar in office */
.office-progress { position: absolute; bottom: 8px; left: 16px; right: 16px; height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.office-progress-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }

/* Info panel overlay */
.agent-info-panel { position: absolute; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
.info-card { background: #0d1117; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 24px; width: 380px; max-height: 80vh; overflow-y: auto; position: relative; }
.info-close { position: absolute; top: 16px; right: 16px; background: none; border: none; color: #484f58; cursor: pointer; }
.info-close:hover { color: #e6edf3; }
.info-header { display: flex; gap: 14px; align-items: center; margin-bottom: 16px; }
.info-avatar { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 18px; color: #fff; }
.info-header h3 { margin: 0; font-size: 18px; }
.info-role { font-size: 12px; color: #8b949e; }
.info-leader { font-size: 10px; color: #ffd700; font-weight: 700; text-transform: uppercase; margin-top: 2px; }
.info-status { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #8b949e; padding: 8px 12px; background: rgba(255,255,255,0.03); border-radius: 10px; margin-bottom: 14px; }
.info-status-dot { width: 8px; height: 8px; border-radius: 50%; background: #30363d; }
.info-status-dot.active { background: #3fb950; animation: pulse 1.5s infinite; }
.info-progress { margin-left: auto; font-weight: 700; color: #58a6ff; }
.info-msg-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #484f58; margin-bottom: 4px; }
.info-message { margin-bottom: 12px; }
.info-message p { font-size: 13px; color: #c9d1d9; line-height: 1.5; margin: 0; }
.info-thinking { padding: 10px 12px; background: rgba(163,113,247,0.04); border: 1px solid rgba(163,113,247,0.1); border-radius: 10px; border-left: 3px solid rgba(163,113,247,0.25); }
.info-thinking p { font-size: 12px; color: #8b949e; line-height: 1.5; margin: 0; font-style: italic; }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

@media (max-width: 900px) {
  .office3d-scene { transform-origin: top left; }
  .info-card { width: 90%; }
}
</style>
