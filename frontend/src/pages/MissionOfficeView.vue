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
          Chat
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
      <!-- Leader & Team Status Bar -->
      <div class="hq-status-bar">
        <div class="leader-badge" v-if="electedLeader">
          <div class="leader-avatar" :style="{ background: electedLeader.color }">{{ electedLeader.avatar }}</div>
          <div class="leader-info">
            <div class="leader-label">Project Lead</div>
            <div class="leader-name">{{ electedLeader.name.split('—')[0].trim() }}</div>
          </div>
          <div class="leader-crown">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="#ffd700" stroke="#ffd700" stroke-width="1"><path d="M2 4l3 12h14l3-12-6 7-4-9-4 9-6-7z"/><rect x="5" y="18" width="14" height="3" rx="1"/></svg>
          </div>
        </div>
        <div class="team-status-pills">
          <div
            v-for="agent in teamAgents"
            :key="agent.id"
            class="agent-pill"
            :class="{ active: agentStatus(agent.id) === 'active', thinking: agentStatus(agent.id) === 'thinking', leader: agent.id === electedLeaderId }"
            @click="selectAgent(agent)"
          >
            <div class="pill-dot" :style="{ background: agent.color }">{{ agent.avatar }}</div>
            <span class="pill-status-dot" :class="agentStatus(agent.id)"></span>
          </div>
        </div>
        <div class="hq-stats">
          <span class="hq-stat"><strong>{{ agentMessages.length }}</strong> messages</span>
          <span class="hq-stat"><strong>{{ votes.length }}</strong> votes</span>
        </div>
      </div>

      <div class="hq-layout">
        <!-- Main feed — the heart of headquarters -->
        <div class="hq-feed">
          <div class="feed-header">
            <h3 class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
              Headquarters
            </h3>
            <div class="feed-filters">
              <button v-for="f in feedFilters" :key="f.id" class="filter-chip" :class="{ active: activeFeedFilter === f.id }" @click="activeFeedFilter = f.id">{{ f.label }}</button>
            </div>
          </div>

          <div class="feed-list" ref="feedContainer">
            <div v-if="filteredMessages.length === 0" class="empty-feed">
              <p>Waiting for agents to start collaborating...</p>
            </div>

            <template v-for="(msg, idx) in filteredMessages" :key="msg.id">
              <!-- System messages -->
              <div v-if="msg.role === 'system'" class="feed-system-msg">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                {{ msg.content }}
              </div>

              <!-- Vote messages -->
              <div v-else-if="msg.metadata?.type === 'vote' && msg.metadata?.phase === 'proposed'" class="feed-vote-card">
                <div class="vote-header">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a371f7" stroke-width="2"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>
                  <span class="vote-badge">Team Vote</span>
                </div>
                <div class="vote-topic">{{ extractVoteTopic(msg.content) }}</div>
                <div class="vote-result-section" v-if="getVoteResult(msg.metadata?.vote_id)">
                  <div class="vote-bar-group">
                    <div v-for="(count, option) in getVoteResult(msg.metadata.vote_id).tally" :key="option" class="vote-bar-row">
                      <span class="vote-option-label">{{ option }}</span>
                      <div class="vote-bar-track">
                        <div class="vote-bar-fill" :style="{ width: (count / 8 * 100) + '%' }" :class="{ winner: option === getVoteResult(msg.metadata.vote_id).winner }"></div>
                      </div>
                      <span class="vote-count">{{ count }}</span>
                    </div>
                  </div>
                  <div class="vote-winner-tag">
                    Decided: <strong>{{ getVoteResult(msg.metadata.vote_id).winner }}</strong>
                  </div>
                </div>
              </div>

              <!-- Election messages -->
              <div v-else-if="msg.metadata?.type === 'election'" class="feed-election-msg">
                <div class="election-badge" v-if="msg.metadata.phase === 'nomination'">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="#ffd700" stroke="#ffd700" stroke-width="1"><path d="M2 4l3 12h14l3-12-6 7-4-9-4 9-6-7z"/><rect x="5" y="18" width="14" height="3" rx="1"/></svg>
                  Leader Election
                </div>
                <div class="feed-msg-row">
                  <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">{{ getAgent(msg.agent_name)?.avatar || '?' }}</div>
                  <div class="feed-msg-body">
                    <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                    <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                  </div>
                </div>
              </div>

              <!-- Vote cast messages (compact) -->
              <div v-else-if="msg.metadata?.type === 'vote' && msg.metadata?.phase === 'cast'" class="feed-vote-cast">
                <div class="feed-msg-dot small" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">{{ getAgent(msg.agent_name)?.avatar || '?' }}</div>
                <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                <span class="cast-text">voted for <strong>{{ msg.metadata.choice }}</strong></span>
              </div>

              <!-- Vote result (compact) -->
              <div v-else-if="msg.metadata?.type === 'vote' && msg.metadata?.phase === 'result'" class="feed-vote-result-msg">
                <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">{{ getAgent(msg.agent_name)?.avatar || '?' }}</div>
                <div class="feed-msg-body">
                  <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                  <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                </div>
              </div>

              <!-- Regular agent messages -->
              <div v-else-if="msg.role === 'agent'" class="feed-agent-msg" :class="{ 'is-leader': msg.agent_name === electedLeaderId }">
                <div class="feed-msg-row">
                  <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">
                    {{ getAgent(msg.agent_name)?.avatar || '?' }}
                    <span v-if="msg.agent_name === electedLeaderId" class="mini-crown">
                      <svg width="8" height="8" viewBox="0 0 24 24" fill="#ffd700" stroke="none"><path d="M2 4l3 12h14l3-12-6 7-4-9-4 9-6-7z"/></svg>
                    </span>
                  </div>
                  <div class="feed-msg-body">
                    <div class="feed-msg-header">
                      <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                      <span class="feed-role">{{ getAgent(msg.agent_name)?.role }}</span>
                      <span class="feed-time">{{ formatTime(msg.created_at) }}</span>
                    </div>
                    <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                    <div class="feed-reasoning" v-if="msg.metadata?.reasoning">
                      <button class="reasoning-toggle" @click="toggleReasoning(msg.id)">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/></svg>
                        {{ expandedReasoning.has(msg.id) ? 'Hide' : 'Show' }} thinking
                      </button>
                      <div v-if="expandedReasoning.has(msg.id)" class="reasoning-text">{{ msg.metadata.reasoning }}</div>
                    </div>
                    <div v-if="msg.metadata?.current_task" class="feed-task-tag">{{ msg.metadata.current_task }}</div>
                  </div>
                </div>
              </div>

              <!-- User messages (minimal) -->
              <div v-else-if="msg.role === 'user'" class="feed-user-msg">
                <div class="user-bubble">{{ msg.content }}</div>
              </div>
            </template>
          </div>
        </div>

        <!-- Side panel — agent detail or plan -->
        <div class="hq-sidebar">
          <div v-if="selectedAgent" class="agent-detail-card">
            <button class="detail-close" @click="selectedAgent = null">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
            <div class="detail-top">
              <AgentAvatar :agentId="selectedAgent.id" :color="selectedAgent.color" :icon="selectedAgent.icon" :letter="selectedAgent.avatar" :size="48"/>
              <div>
                <h3 class="detail-name" :style="{ color: selectedAgent.color }">{{ selectedAgent.name.split('—')[0].trim() }}</h3>
                <div class="detail-role">{{ selectedAgent.role }}</div>
                <div class="detail-leader-tag" v-if="selectedAgent.id === electedLeaderId">Project Lead</div>
              </div>
            </div>
            <p class="detail-desc">{{ selectedAgent.description }}</p>
            <div class="detail-kpis" v-if="selectedAgent.kpis?.length">
              <div class="detail-label">KPIs</div>
              <div v-for="(kpi, i) in selectedAgent.kpis.slice(0, 3)" :key="i" class="kpi-row">{{ kpi }}</div>
            </div>
          </div>

          <div v-else class="plan-card" v-if="mission?.plan">
            <div class="detail-label">Mission Plan</div>
            <div class="plan-title">{{ mission.plan.title }}</div>
            <div class="plan-timeline">{{ mission.plan.timeline }}</div>
            <div class="plan-phases-list">
              <div v-for="(phase, i) in mission.plan.phases || []" :key="i" class="plan-phase-row">
                <div class="phase-num" :class="{ active: mission.status === 'executing' && i === 0 }">{{ i + 1 }}</div>
                <div class="phase-info">
                  <div class="phase-name">{{ phase.name }}</div>
                  <div class="phase-dur">{{ phase.duration }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="votes-card" v-if="votes.length > 0">
            <div class="detail-label">Decisions Made</div>
            <div v-for="v in votes" :key="v.id" class="vote-summary-row">
              <div class="vote-summary-topic">{{ v.topic }}</div>
              <div class="vote-summary-result" v-if="v.result">{{ v.result.winner }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-dots"><span></span><span></span><span></span></div>
      <p>Entering headquarters...</p>
    </div>
    <div v-if="loadError" class="error-banner">{{ loadError }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import AgentAvatar from '../components/AgentAvatar.vue'

const route = useRoute()

const mission = ref(null)
const messages = ref([])
const teamAgents = ref([])
const votes = ref([])
const selectedAgent = ref(null)
const loading = ref(true)
const loadError = ref('')
const animateFrom = ref(0)
const expandedReasoning = ref(new Set())
const feedContainer = ref(null)
const activeFeedFilter = ref('all')
let pollInterval = null

const feedFilters = [
  { id: 'all', label: 'All' },
  { id: 'decisions', label: 'Decisions' },
  { id: 'agents', label: 'Agents Only' },
]

const agentMap = computed(() => {
  const map = {}
  teamAgents.value.forEach(a => { map[a.id] = a })
  return map
})

const electedLeaderId = computed(() => {
  const ctx = mission.value?.context
  if (!ctx) return 'team_leader'
  const context = typeof ctx === 'string' ? JSON.parse(ctx) : ctx
  return context?.elected_leader || 'team_leader'
})

const electedLeader = computed(() => agentMap.value[electedLeaderId.value] || null)

const agentMessages = computed(() => messages.value.filter(m => m.role === 'agent'))

const filteredMessages = computed(() => {
  if (activeFeedFilter.value === 'all') return messages.value.filter(m => m.role !== 'user' || m.content)
  if (activeFeedFilter.value === 'decisions') {
    return messages.value.filter(m =>
      m.metadata?.type === 'vote' ||
      m.metadata?.type === 'election' ||
      (m.role === 'system')
    )
  }
  if (activeFeedFilter.value === 'agents') {
    return messages.value.filter(m => m.role === 'agent')
  }
  return messages.value
})

onMounted(async () => {
  await Promise.all([loadMission(), loadTeam()])
  await loadVotes()
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
  } catch (e) { console.error(e) }
}

async function loadVotes() {
  try {
    const res = await fetch(`/api/missions/${route.params.id}/votes`)
    if (res.ok) {
      const data = await res.json()
      votes.value = data.votes || []
    }
  } catch (e) { /* ignore */ }
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
    await loadVotes()
  } catch (e) { /* silent */ }
}

async function approvePlan() {
  try {
    const res = await fetch(`/api/missions/${route.params.id}/approve`, { method: 'POST' })
    if (!res.ok) throw new Error('Failed to approve')
    animateFrom.value = messages.value.length
    await loadMission()
  } catch (e) { console.error(e) }
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

function agentHasSpoken(agentId) {
  return messages.value.some(m => m.agent_name === agentId)
}

function getAgent(id) { return agentMap.value[id] || null }
function getAgentShortName(id) { return agentMap.value[id]?.name?.split('—')[0]?.trim() || id }

function getVoteResult(voteId) {
  if (!voteId) return null
  const v = votes.value.find(vote => vote.id === voteId)
  return v?.result || null
}

function extractVoteTopic(content) {
  const match = content.match(/\*\*Team Vote:\*\*\s*(.+?)(?:\n|$)/)
  return match ? match[1] : content.substring(0, 80)
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
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
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
.office-page { height: calc(100vh - var(--topbar-h, 56px)); background: #0a0e17; overflow: hidden; font-family: 'Inter', sans-serif; display: flex; flex-direction: column; }

.office-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; border-bottom: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); backdrop-filter: blur(10px); flex-shrink: 0; gap: 16px; }
.header-left { display: flex; align-items: center; gap: 16px; min-width: 0; flex: 1; }
.back-link { display: flex; align-items: center; gap: 4px; background: none; border: none; color: #8b949e; cursor: pointer; font-size: 13px; padding: 6px 10px; border-radius: 8px; transition: all 0.2s; white-space: nowrap; }
.back-link:hover { color: #e6edf3; background: rgba(255,255,255,0.05); }
.header-info { min-width: 0; }
.mission-title { font-size: 14px; font-weight: 600; color: #e6edf3; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 400px; }
.mission-status-badge { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.mission-status-badge.gathering_info { color: #58a6ff; } .mission-status-badge.gathering_info .status-dot { background: #58a6ff; }
.mission-status-badge.planning { color: #a371f7; } .mission-status-badge.planning .status-dot { background: #a371f7; }
.mission-status-badge.awaiting_approval { color: #f0883e; } .mission-status-badge.awaiting_approval .status-dot { background: #f0883e; }
.mission-status-badge.executing { color: #3fb950; } .mission-status-badge.executing .status-dot { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.header-right { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.view-toggle-btn { display: flex; align-items: center; gap: 6px; padding: 7px 14px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); color: #c9d1d9; border-radius: 10px; font-size: 13px; cursor: pointer; transition: all 0.2s; }
.view-toggle-btn:hover { background: rgba(255,255,255,0.08); color: #e6edf3; }
.approve-btn { display: flex; align-items: center; gap: 6px; padding: 7px 18px; background: linear-gradient(135deg, #238636, #2ea043); color: #fff; border: none; border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 10px rgba(46,160,67,0.25); }
.approve-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(46,160,67,0.35); }

/* HQ Status Bar */
.hq-status-bar { display: flex; align-items: center; gap: 16px; padding: 12px 20px; border-bottom: 1px solid rgba(255,255,255,0.04); background: rgba(255,255,255,0.015); flex-shrink: 0; }
.leader-badge { display: flex; align-items: center; gap: 10px; padding: 6px 14px 6px 6px; background: rgba(255,215,0,0.06); border: 1px solid rgba(255,215,0,0.15); border-radius: 12px; }
.leader-avatar { width: 32px; height: 32px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; color: #fff; }
.leader-info { }
.leader-label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.8px; color: #ffd700; font-weight: 700; }
.leader-name { font-size: 13px; font-weight: 600; color: #e6edf3; }
.leader-crown { flex-shrink: 0; }
.team-status-pills { display: flex; gap: 4px; flex: 1; }
.agent-pill { position: relative; cursor: pointer; transition: all 0.2s; border-radius: 10px; padding: 2px; }
.agent-pill:hover { background: rgba(255,255,255,0.06); }
.agent-pill.leader .pill-dot { box-shadow: 0 0 0 2px rgba(255,215,0,0.3); }
.pill-dot { width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 10px; color: #fff; }
.pill-status-dot { position: absolute; bottom: 0; right: 0; width: 8px; height: 8px; border-radius: 50%; border: 2px solid #0a0e17; background: #30363d; }
.pill-status-dot.active { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.pill-status-dot.thinking { background: #a371f7; animation: pulse 1.5s ease-in-out infinite; }
.hq-stats { display: flex; gap: 14px; font-size: 12px; color: #484f58; flex-shrink: 0; }
.hq-stat strong { color: #8b949e; }

/* HQ Layout */
.office-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.hq-layout { flex: 1; display: flex; overflow: hidden; }
.hq-feed { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.feed-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px 8px; flex-shrink: 0; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: #e6edf3; margin: 0; }
.feed-filters { display: flex; gap: 4px; }
.filter-chip { padding: 4px 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; color: #8b949e; font-size: 11px; cursor: pointer; transition: all 0.2s; }
.filter-chip:hover { background: rgba(255,255,255,0.06); }
.filter-chip.active { background: rgba(88,166,255,0.1); border-color: rgba(88,166,255,0.25); color: #58a6ff; }

.feed-list { flex: 1; overflow-y: auto; padding: 8px 20px 20px; display: flex; flex-direction: column; gap: 6px; }
.empty-feed { text-align: center; padding: 40px; color: #484f58; font-size: 13px; }

/* Feed message types */
.feed-system-msg { display: flex; align-items: center; gap: 6px; color: #8b949e; font-size: 12px; padding: 6px 12px; background: rgba(255,255,255,0.02); border-radius: 16px; border: 1px solid rgba(255,255,255,0.03); margin: 4px 0; }

.feed-agent-msg { padding: 10px 14px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 14px; transition: all 0.2s; }
.feed-agent-msg:hover { background: rgba(255,255,255,0.035); border-color: rgba(255,255,255,0.07); }
.feed-agent-msg.is-leader { border-left: 3px solid rgba(255,215,0,0.3); }

.feed-msg-row { display: flex; gap: 10px; }
.feed-msg-dot { width: 28px; height: 28px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 10px; color: #fff; flex-shrink: 0; position: relative; }
.feed-msg-dot.small { width: 20px; height: 20px; border-radius: 6px; font-size: 8px; }
.mini-crown { position: absolute; top: -4px; right: -4px; }
.feed-msg-body { flex: 1; min-width: 0; }
.feed-msg-header { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; flex-wrap: wrap; }
.feed-name { font-size: 13px; font-weight: 700; }
.feed-role { font-size: 10px; color: #484f58; }
.feed-time { font-size: 10px; color: #30363d; margin-left: auto; }
.feed-text { font-size: 13px; color: #c9d1d9; line-height: 1.55; }
.feed-text :deep(.md-h2) { font-size: 14px; color: #e6edf3; margin: 8px 0 4px; font-weight: 700; }
.feed-text :deep(.md-h3) { font-size: 13px; color: #e6edf3; margin: 6px 0 3px; font-weight: 600; }
.feed-text :deep(.md-li) { padding-left: 14px; position: relative; margin: 3px 0; }
.feed-text :deep(.md-li::before) { content: ''; position: absolute; left: 3px; top: 8px; width: 3px; height: 3px; border-radius: 50%; background: #484f58; }
.feed-text :deep(.md-hr) { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 10px 0; }

.feed-reasoning { margin-top: 6px; }
.reasoning-toggle { display: flex; align-items: center; gap: 4px; background: none; border: none; color: #484f58; font-size: 11px; cursor: pointer; padding: 2px 0; }
.reasoning-toggle:hover { color: #8b949e; }
.reasoning-text { font-size: 11px; color: #484f58; line-height: 1.5; font-style: italic; margin-top: 4px; padding: 6px 10px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 2px solid rgba(255,255,255,0.06); }
.feed-task-tag { display: inline-block; margin-top: 6px; font-size: 10px; background: rgba(255,255,255,0.04); color: #8b949e; padding: 2px 8px; border-radius: 6px; }

/* Election messages */
.feed-election-msg { padding: 10px 14px; background: rgba(255,215,0,0.03); border: 1px solid rgba(255,215,0,0.1); border-radius: 14px; }
.election-badge { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: #ffd700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }

/* Vote messages */
.feed-vote-card { padding: 14px 16px; background: rgba(163,113,247,0.04); border: 1px solid rgba(163,113,247,0.15); border-radius: 14px; }
.vote-header { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.vote-badge { font-size: 11px; font-weight: 700; color: #a371f7; text-transform: uppercase; letter-spacing: 0.5px; }
.vote-topic { font-size: 14px; font-weight: 600; color: #e6edf3; margin-bottom: 12px; }
.vote-result-section { margin-top: 8px; }
.vote-bar-group { display: flex; flex-direction: column; gap: 6px; }
.vote-bar-row { display: flex; align-items: center; gap: 10px; }
.vote-option-label { font-size: 11px; color: #c9d1d9; width: 200px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vote-bar-track { flex: 1; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
.vote-bar-fill { height: 100%; background: #484f58; border-radius: 3px; transition: width 0.5s ease; }
.vote-bar-fill.winner { background: linear-gradient(90deg, #a371f7, #58a6ff); }
.vote-count { font-size: 11px; color: #8b949e; width: 16px; text-align: right; }
.vote-winner-tag { margin-top: 10px; font-size: 12px; color: #a371f7; padding: 4px 10px; background: rgba(163,113,247,0.08); border-radius: 8px; display: inline-block; }

.feed-vote-cast { display: flex; align-items: center; gap: 8px; padding: 4px 12px; font-size: 12px; color: #8b949e; }
.cast-text strong { color: #c9d1d9; }
.feed-vote-result-msg { padding: 10px 14px; background: rgba(163,113,247,0.03); border: 1px solid rgba(163,113,247,0.1); border-radius: 14px; }

.feed-user-msg { display: flex; justify-content: flex-end; }
.user-bubble { padding: 8px 14px; background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.2); border-radius: 14px; color: #79c0ff; font-size: 13px; max-width: 60%; }

/* Sidebar */
.hq-sidebar { width: 320px; border-left: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.015); overflow-y: auto; padding: 16px; flex-shrink: 0; display: flex; flex-direction: column; gap: 14px; }

.agent-detail-card, .plan-card, .votes-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 16px; position: relative; }
.detail-close { position: absolute; top: 12px; right: 12px; background: none; border: none; color: #484f58; cursor: pointer; padding: 4px; border-radius: 6px; }
.detail-close:hover { color: #e6edf3; background: rgba(255,255,255,0.05); }
.detail-top { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.detail-name { font-size: 15px; font-weight: 700; margin: 0; }
.detail-role { font-size: 11px; color: #8b949e; }
.detail-leader-tag { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #ffd700; margin-top: 2px; }
.detail-desc { font-size: 12px; color: #8b949e; line-height: 1.5; margin: 0 0 12px; }
.detail-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #484f58; margin-bottom: 8px; }
.detail-kpis { }
.kpi-row { font-size: 11px; color: #8b949e; padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.03); line-height: 1.4; }

.plan-title { font-size: 14px; font-weight: 600; color: #e6edf3; margin-bottom: 4px; }
.plan-timeline { font-size: 12px; color: #8b949e; margin-bottom: 12px; }
.plan-phases-list { display: flex; flex-direction: column; gap: 6px; }
.plan-phase-row { display: flex; align-items: center; gap: 10px; }
.phase-num { width: 22px; height: 22px; border-radius: 50%; border: 2px solid #21262d; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #484f58; flex-shrink: 0; }
.phase-num.active { border-color: #3fb950; color: #3fb950; background: rgba(63,185,80,0.1); }
.phase-info { min-width: 0; }
.phase-name { font-size: 12px; font-weight: 600; color: #c9d1d9; }
.phase-dur { font-size: 10px; color: #484f58; }

.vote-summary-row { padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.vote-summary-topic { font-size: 12px; color: #c9d1d9; margin-bottom: 2px; }
.vote-summary-result { font-size: 11px; color: #a371f7; font-weight: 600; }

.loading-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: #8b949e; padding: 60px; flex: 1; }
.loading-dots { display: flex; gap: 6px; }
.loading-dots span { width: 10px; height: 10px; border-radius: 50%; background: #30363d; animation: loadBounce 1.4s ease-in-out infinite; }
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes loadBounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
.error-banner { color: #f85149; background: rgba(248,81,73,0.08); border: 1px solid rgba(248,81,73,0.2); padding: 10px 16px; border-radius: 10px; font-size: 13px; text-align: center; margin: 20px; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

@media (max-width: 900px) {
  .hq-sidebar { display: none; }
  .hq-status-bar { flex-wrap: wrap; }
  .vote-option-label { width: 120px; }
  .mission-title { max-width: 200px; }
}
</style>
