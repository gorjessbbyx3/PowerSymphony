<template>
  <div class="orch-view">
    <div class="header">
      <div>
        <h1>Agent Orchestration</h1>
        <p class="subtitle">8 specialized AI agents collaborating with interdependent roles and clear KPIs</p>
      </div>
      <div class="header-stats">
        <div class="stat-pill" :class="{ good: summary.agents_healthy === summary.total_agents }">
          <span class="stat-value">{{ summary.agents_healthy }}/{{ summary.total_agents }}</span>
          <span class="stat-label">Healthy</span>
        </div>
        <div class="stat-pill">
          <span class="stat-value">{{ summary.agents_running }}</span>
          <span class="stat-label">Running</span>
        </div>
        <div class="stat-pill">
          <span class="stat-value">{{ summary.total_runs }}</span>
          <span class="stat-label">Total Runs</span>
        </div>
        <div class="stat-pill" :class="{ good: summary.kpis_met === summary.kpis_total }">
          <span class="stat-value">{{ summary.kpis_met }}/{{ summary.kpis_total }}</span>
          <span class="stat-label">KPIs Met</span>
        </div>
      </div>
    </div>

    <div class="tabs">
      <button :class="['tab', { active: tab === 'agents' }]" @click="tab = 'agents'">Agent Dashboard</button>
      <button :class="['tab', { active: tab === 'deps' }]" @click="tab = 'deps'">Dependency Graph</button>
      <button :class="['tab', { active: tab === 'kpis' }]" @click="tab = 'kpis'">KPI Tracker</button>
      <button :class="['tab', { active: tab === 'sync' }]" @click="tab = 'sync'">Sync Log</button>
    </div>

    <!-- Agent Dashboard -->
    <div v-if="tab === 'agents'" class="agents-grid">
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="agent-card"
        :class="{ selected: selectedAgent?.id === agent.id, running: agent.status === 'running' }"
        @click="selectAgent(agent)"
      >
        <div class="card-top">
          <div class="agent-icon" :style="{ background: agent.color + '22', color: agent.color }">
            <span>{{ ICONS[agent.icon] || '🤖' }}</span>
          </div>
          <div class="status-badge" :class="agent.status">{{ agent.status }}</div>
        </div>
        <h3 class="agent-name">{{ agent.name }}</h3>
        <p class="agent-desc">{{ agent.description }}</p>
        <div class="kpi-bar">
          <div class="kpi-label">
            <span>{{ agent.kpi }}</span>
            <span class="kpi-value">{{ agent.kpi_current }}{{ agent.kpi_unit }}</span>
          </div>
          <div class="progress-track">
            <div
              class="progress-fill"
              :style="{
                width: kpiProgress(agent) + '%',
                background: agent.color,
              }"
            ></div>
          </div>
        </div>
        <div class="sub-agents">
          <span v-for="s in agent.sub_agents" :key="s" class="sub-tag">{{ s }}</span>
        </div>
        <div class="card-footer">
          <span class="runs-count">{{ agent.runs_total }} runs</span>
          <span v-if="agent.last_run" class="last-run">{{ timeAgo(agent.last_run) }}</span>
        </div>
      </div>
    </div>

    <!-- Agent Detail Panel -->
    <div v-if="tab === 'agents' && selectedAgent" class="detail-panel">
      <div class="detail-header">
        <div>
          <h2 :style="{ color: selectedAgent.color }">{{ selectedAgent.name }}</h2>
          <p>{{ selectedAgent.description }}</p>
        </div>
        <div class="detail-actions">
          <button class="btn btn-primary" @click="triggerRun(selectedAgent.id)" :disabled="selectedAgent.status === 'running'">
            {{ selectedAgent.status === 'running' ? 'Running…' : 'Run Agent' }}
          </button>
          <button class="btn btn-ghost" @click="completeRun(selectedAgent.id)" v-if="selectedAgent.status === 'running'">
            Mark Complete
          </button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="detail-section">
          <h4>Dependencies (receives data from)</h4>
          <div v-if="selectedAgent.depends_on.length === 0" class="empty">No dependencies — entry point agent</div>
          <div v-else class="dep-list">
            <span
              v-for="d in selectedAgent.depends_on"
              :key="d"
              class="dep-chip"
              :style="{ borderColor: AGENT_MAP[d]?.color }"
              @click="selectAgent(AGENT_MAP[d])"
            >{{ AGENT_MAP[d]?.name || d }}</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>Feeds into (sends data to)</h4>
          <div v-if="selectedAgent.feeds_into.length === 0" class="empty">Terminal agent — no downstream</div>
          <div v-else class="dep-list">
            <span
              v-for="d in selectedAgent.feeds_into"
              :key="d"
              class="dep-chip"
              :style="{ borderColor: AGENT_MAP[d]?.color }"
              @click="selectAgent(AGENT_MAP[d])"
            >{{ AGENT_MAP[d]?.name || d }}</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>Sub-Agents</h4>
          <div class="sub-list">
            <div v-for="s in selectedAgent.sub_agents" :key="s" class="sub-item">
              <span class="sub-dot" :style="{ background: selectedAgent.color }"></span>
              {{ s }}
            </div>
          </div>
        </div>
        <div class="detail-section">
          <h4>KPI Status</h4>
          <div class="kpi-detail">
            <div class="kpi-big-number" :style="{ color: selectedAgent.color }">
              {{ selectedAgent.kpi_current }}<span class="kpi-unit">{{ selectedAgent.kpi_unit }}</span>
            </div>
            <div class="kpi-target">Target: {{ selectedAgent.kpi_target }}{{ selectedAgent.kpi_unit }}</div>
            <div class="progress-track lg">
              <div class="progress-fill" :style="{ width: kpiProgress(selectedAgent) + '%', background: selectedAgent.color }"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="detail-section full">
        <h4>Update KPI Value</h4>
        <div class="kpi-update-row">
          <input type="number" v-model.number="kpiInput" class="input sm" placeholder="New value" />
          <button class="btn btn-primary sm" @click="updateKPI(selectedAgent.id)">Update</button>
        </div>
      </div>
    </div>

    <!-- Dependency Graph -->
    <div v-if="tab === 'deps'" class="dep-graph-section">
      <div class="dep-graph">
        <svg :viewBox="`0 0 ${graphW} ${graphH}`" class="dep-svg">
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#555" />
            </marker>
          </defs>
          <line
            v-for="(e, i) in graphEdges"
            :key="'e'+i"
            :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
            stroke="#444" stroke-width="2" marker-end="url(#arrowhead)"
          />
          <g v-for="n in graphNodes" :key="n.id" @click="selectAgent(AGENT_MAP[n.id]); tab = 'agents'">
            <rect
              :x="n.x - 70" :y="n.y - 22" width="140" height="44" rx="8"
              :fill="n.color + '22'" :stroke="n.color" stroke-width="2"
              class="graph-node"
            />
            <text :x="n.x" :y="n.y + 5" text-anchor="middle" :fill="n.color" font-size="12" font-weight="600">
              {{ n.label }}
            </text>
          </g>
        </svg>
      </div>
      <div class="dep-legend">
        <p>Click any node to view agent details. Arrows show data flow direction.</p>
      </div>
    </div>

    <!-- KPI Tracker -->
    <div v-if="tab === 'kpis'" class="kpi-section">
      <div class="kpi-grid">
        <div v-for="k in kpis" :key="k.agent_id" class="kpi-card">
          <div class="kpi-card-header">
            <span class="kpi-agent-name" :style="{ color: k.color }">{{ k.agent_name }}</span>
            <span class="kpi-pct" :class="{ met: k.progress_pct >= 100 }">{{ k.progress_pct }}%</span>
          </div>
          <div class="kpi-card-metric">{{ k.kpi }}</div>
          <div class="kpi-card-numbers">
            <span>{{ k.current }}{{ k.unit }}</span>
            <span class="kpi-card-target">/ {{ k.target }}{{ k.unit }}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: Math.min(k.progress_pct, 100) + '%', background: k.color }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Sync Log -->
    <div v-if="tab === 'sync'" class="sync-section">
      <div class="sync-input-row">
        <select v-model="syncAgent" class="select">
          <option value="">Select agent…</option>
          <option v-for="a in agents" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <input v-model="syncMessage" class="input flex" placeholder="Sync message…" @keyup.enter="postSync" />
        <button class="btn btn-primary" @click="postSync" :disabled="!syncAgent || !syncMessage">Post</button>
      </div>
      <div class="sync-feed">
        <div v-if="syncLog.length === 0" class="empty">No sync entries yet. Agents will log activity here.</div>
        <div v-for="(entry, i) in syncLog" :key="i" class="sync-entry">
          <div class="sync-dot" :style="{ background: AGENT_MAP[entry.agent_id]?.color || '#555' }"></div>
          <div class="sync-content">
            <span class="sync-agent" :style="{ color: AGENT_MAP[entry.agent_id]?.color }">
              {{ AGENT_MAP[entry.agent_id]?.name || entry.agent_id }}
            </span>
            <span class="sync-type">{{ entry.type }}</span>
            <span v-if="entry.message" class="sync-msg">{{ entry.message }}</span>
          </div>
          <span class="sync-time">{{ timeAgo(entry.timestamp) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const ICONS = {
  search: '🔍', lightbulb: '💡', code: '⚙️', plug: '🔌',
  shield: '🛡️', megaphone: '📢', dollar: '💰', rocket: '🚀',
}

const tab = ref('agents')
const agents = ref([])
const kpis = ref([])
const syncLog = ref([])
const summary = ref({ total_agents: 8, agents_running: 0, agents_healthy: 8, total_runs: 0, kpis_met: 0, kpis_total: 8 })
const selectedAgent = ref(null)
const kpiInput = ref(0)
const syncAgent = ref('')
const syncMessage = ref('')

const AGENT_MAP = computed(() => {
  const m = {}
  agents.value.forEach(a => { m[a.id] = a })
  return m
})

const POSITIONS = {
  market_researcher: { x: 140, y: 50 },
  product_strategist: { x: 380, y: 50 },
  core_engineer: { x: 380, y: 160 },
  integration_engineer: { x: 620, y: 100 },
  tester_compliance: { x: 620, y: 220 },
  sales_marketing: { x: 140, y: 160 },
  fundraising_ops: { x: 140, y: 280 },
  scaler_innovator: { x: 620, y: 340 },
}

const graphW = 780
const graphH = 410

const graphNodes = computed(() =>
  agents.value.map(a => ({
    id: a.id,
    label: a.name,
    color: a.color,
    ...POSITIONS[a.id],
  }))
)

const graphEdges = computed(() => {
  const edges = []
  agents.value.forEach(a => {
    const from = POSITIONS[a.id]
    if (!from) return
    a.feeds_into.forEach(tid => {
      const to = POSITIONS[tid]
      if (!to) return
      const dx = to.x - from.x
      const dy = to.y - from.y
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      edges.push({
        x1: from.x + (dx / dist) * 72,
        y1: from.y + (dy / dist) * 24,
        x2: to.x - (dx / dist) * 72,
        y2: to.y - (dy / dist) * 24,
      })
    })
  })
  return edges
})

function kpiProgress(agent) {
  if (!agent.kpi_target) return agent.kpi_current === 0 ? 100 : 0
  return Math.min(100, (agent.kpi_current / agent.kpi_target) * 100)
}

function timeAgo(ts) {
  if (!ts) return ''
  const secs = Math.floor(Date.now() / 1000 - ts)
  if (secs < 60) return `${secs}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
  return `${Math.floor(secs / 86400)}d ago`
}

function selectAgent(agent) {
  if (!agent) return
  selectedAgent.value = agent
  kpiInput.value = agent.kpi_current || 0
}

async function loadData() {
  try {
    const [agentsRes, kpisRes, summaryRes, syncRes] = await Promise.all([
      fetch('/api/orchestration/agents').then(r => r.json()),
      fetch('/api/orchestration/kpis').then(r => r.json()),
      fetch('/api/orchestration/summary').then(r => r.json()),
      fetch('/api/orchestration/sync?limit=50').then(r => r.json()),
    ])
    agents.value = agentsRes.agents || []
    kpis.value = kpisRes.kpis || []
    Object.assign(summary.value, summaryRes)
    syncLog.value = syncRes.entries || []
    if (selectedAgent.value) {
      const updated = agents.value.find(a => a.id === selectedAgent.value.id)
      if (updated) selectedAgent.value = updated
    }
  } catch (e) {
    console.error('Failed to load orchestration data:', e)
  }
}

async function triggerRun(id) {
  await fetch(`/api/orchestration/agents/${id}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  await loadData()
}

async function completeRun(id) {
  await fetch(`/api/orchestration/agents/${id}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  await loadData()
}

async function updateKPI(id) {
  await fetch(`/api/orchestration/agents/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kpi_current: kpiInput.value }),
  })
  await loadData()
}

async function postSync() {
  if (!syncAgent.value || !syncMessage.value) return
  await fetch('/api/orchestration/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: syncAgent.value, message: syncMessage.value }),
  })
  syncMessage.value = ''
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
.orch-view { max-width: 1400px; margin: 0 auto; padding: 32px 24px; font-family: 'Inter', sans-serif; }
.header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; gap: 16px; }
.header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(90deg, #aaffcd, #99eaf9, #a0c4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 6px; }
.subtitle { color: #8e8e8e; margin: 0; font-size: 14px; }
.header-stats { display: flex; gap: 12px; }
.stat-pill { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 10px; padding: 10px 16px; text-align: center; min-width: 70px; }
.stat-pill.good { border-color: #34d399; }
.stat-value { display: block; font-size: 18px; font-weight: 700; color: #f0f0f0; }
.stat-label { font-size: 11px; color: #777; text-transform: uppercase; letter-spacing: 0.5px; }

.tabs { display: flex; gap: 4px; background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 10px; padding: 5px; margin-bottom: 20px; }
.tab { flex: 1; padding: 9px; border-radius: 7px; border: none; cursor: pointer; font-size: 13px; background: transparent; color: #8e8e8e; transition: all 0.2s; }
.tab.active { background: #2d2d2d; color: #f0f0f0; }

.agents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 16px; margin-bottom: 20px; }
.agent-card { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 18px; cursor: pointer; transition: all 0.2s; }
.agent-card:hover { border-color: #444; transform: translateY(-2px); }
.agent-card.selected { border-color: #aaffcd; box-shadow: 0 0 20px rgba(170, 255, 205, 0.08); }
.agent-card.running { border-color: #fbbf24; }
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.agent-icon { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.status-badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
.status-badge.idle { background: #2d2d2d; color: #8e8e8e; }
.status-badge.running { background: #fbbf2422; color: #fbbf24; }
.status-badge.error { background: #ef444422; color: #ef4444; }
.agent-name { font-size: 15px; font-weight: 600; color: #f0f0f0; margin: 0 0 6px; }
.agent-desc { font-size: 12px; color: #777; margin: 0 0 12px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.kpi-bar { margin-bottom: 10px; }
.kpi-label { display: flex; justify-content: space-between; font-size: 11px; color: #8e8e8e; margin-bottom: 5px; }
.kpi-value { font-weight: 600; color: #c0c0c0; }
.progress-track { height: 6px; background: #0f0f0f; border-radius: 3px; overflow: hidden; }
.progress-track.lg { height: 10px; border-radius: 5px; margin-top: 8px; }
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.sub-agents { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }
.sub-tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; background: #0f0f0f; color: #999; border: 1px solid #222; }
.card-footer { display: flex; justify-content: space-between; font-size: 11px; color: #666; }

.detail-panel { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
.detail-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.detail-header h2 { font-size: 20px; font-weight: 700; margin: 0 0 4px; }
.detail-header p { font-size: 13px; color: #8e8e8e; margin: 0; max-width: 600px; }
.detail-actions { display: flex; gap: 8px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.detail-section { background: #0f0f0f; border-radius: 10px; padding: 16px; }
.detail-section.full { grid-column: 1 / -1; }
.detail-section h4 { font-size: 12px; font-weight: 600; color: #8e8e8e; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 10px; }
.dep-list { display: flex; flex-wrap: wrap; gap: 6px; }
.dep-chip { font-size: 12px; padding: 4px 12px; border-radius: 6px; background: #1a1a1a; border: 1px solid; cursor: pointer; color: #c0c0c0; transition: opacity 0.2s; }
.dep-chip:hover { opacity: 0.8; }
.sub-list { display: flex; flex-direction: column; gap: 6px; }
.sub-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #c0c0c0; }
.sub-dot { width: 8px; height: 8px; border-radius: 50%; }
.kpi-detail { text-align: center; }
.kpi-big-number { font-size: 36px; font-weight: 700; line-height: 1; }
.kpi-unit { font-size: 14px; font-weight: 400; opacity: 0.7; }
.kpi-target { font-size: 12px; color: #777; margin-top: 4px; }
.kpi-update-row { display: flex; gap: 8px; align-items: center; }
.empty { font-size: 13px; color: #555; font-style: italic; }

.btn { padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity 0.2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: linear-gradient(135deg, #aaffcd, #99eaf9); color: #0f0f0f; }
.btn-ghost { background: #1f1f1f; border: 1px solid #2d2d2d; color: #c0c0c0; }
.btn.sm { padding: 6px 14px; font-size: 12px; }
.input { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 8px 12px; color: #f0f0f0; font-size: 13px; }
.input.sm { width: 120px; }
.input.flex { flex: 1; }
.select { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 8px 12px; color: #c0c0c0; font-size: 13px; min-width: 160px; }

.dep-graph-section { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 24px; }
.dep-svg { width: 100%; max-height: 500px; }
.graph-node { cursor: pointer; transition: opacity 0.2s; }
.graph-node:hover { opacity: 0.8; }
.dep-legend { text-align: center; margin-top: 12px; font-size: 12px; color: #666; }

.kpi-section { }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.kpi-card { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 10px; padding: 16px; }
.kpi-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.kpi-agent-name { font-size: 14px; font-weight: 600; }
.kpi-pct { font-size: 14px; font-weight: 700; color: #8e8e8e; }
.kpi-pct.met { color: #34d399; }
.kpi-card-metric { font-size: 12px; color: #777; margin-bottom: 8px; }
.kpi-card-numbers { font-size: 20px; font-weight: 700; color: #f0f0f0; margin-bottom: 10px; }
.kpi-card-target { font-size: 14px; font-weight: 400; color: #555; }

.sync-section { }
.sync-input-row { display: flex; gap: 8px; margin-bottom: 16px; }
.sync-feed { display: flex; flex-direction: column; gap: 8px; }
.sync-entry { display: flex; align-items: flex-start; gap: 10px; background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 8px; padding: 10px 14px; }
.sync-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.sync-content { flex: 1; }
.sync-agent { font-weight: 600; font-size: 13px; }
.sync-type { font-size: 11px; color: #666; margin-left: 8px; padding: 1px 6px; background: #0f0f0f; border-radius: 4px; }
.sync-msg { display: block; font-size: 13px; color: #c0c0c0; margin-top: 4px; }
.sync-time { font-size: 11px; color: #555; white-space: nowrap; }

@media (max-width: 900px) {
  .agents-grid { grid-template-columns: 1fr; }
  .detail-grid { grid-template-columns: 1fr; }
  .kpi-grid { grid-template-columns: 1fr; }
  .header { flex-direction: column; }
  .header-stats { flex-wrap: wrap; }
}
</style>
