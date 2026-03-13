<template>
  <div class="perf-view">
    <div class="header">
      <div>
        <h1>Agent Performance</h1>
        <p class="subtitle">Cross-run learning, prompt evolution, and quality trends</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" @click="loadData" :class="{ spinning: loading }">
          <span class="icon">↻</span> Refresh
        </button>
        <button class="btn btn-primary" @click="showTryRefine = true">
          Try Refinement
        </button>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <!-- Agent list -->
    <div v-if="agents.length === 0 && !loading" class="empty-state">
      <div class="empty-icon">🧠</div>
      <h3>No agent performance data yet</h3>
      <p>Run a workflow using the <code>self_improving_agent.yaml</code> or <code>prompt_evolution_pipeline.yaml</code> templates.<br/>
      Agents will automatically track their performance across runs.</p>
    </div>

    <div class="agents-grid" v-if="agents.length">
      <div
        class="agent-card"
        v-for="agent in agents"
        :key="agent.agent_id"
        :class="{ selected: selectedAgent === agent.agent_id }"
        @click="selectAgent(agent.agent_id)"
      >
        <div class="agent-header">
          <span class="agent-name">{{ agent.agent_id }}</span>
          <span class="score-badge" :class="scoreClass(agent.avg_score)">
            {{ agent.avg_score.toFixed(1) }}/10
          </span>
        </div>
        <div class="agent-meta">
          <span>{{ agent.total_runs }} runs</span>
          <span>Best: {{ agent.best_score.toFixed(1) }}</span>
          <span>{{ agent.prompt_versions_count }} prompt versions</span>
        </div>
        <!-- Mini trend bar -->
        <div class="mini-trend" v-if="trends[agent.agent_id]">
          <div
            class="mini-bar"
            v-for="(s, i) in trends[agent.agent_id].scores"
            :key="i"
            :style="{ height: (s / 10 * 40) + 'px' }"
            :class="scoreClass(s)"
          ></div>
          <span class="trend-label" :class="trends[agent.agent_id].trend">
            {{ trends[agent.agent_id].trend }}
          </span>
        </div>
      </div>
    </div>

    <!-- Detail panel for selected agent -->
    <div v-if="selectedAgent && detail" class="detail-panel">
      <div class="detail-header">
        <h2>{{ selectedAgent }}</h2>
        <div class="detail-actions">
          <button class="btn btn-sm btn-ghost" @click="showBestPrompt(selectedAgent)">
            View Best Prompt
          </button>
          <button class="btn btn-sm btn-danger" @click="resetAgent(selectedAgent)">
            Reset Data
          </button>
        </div>
      </div>

      <!-- Score trend chart -->
      <div class="trend-chart" v-if="detail.trend && detail.trend.scores.length">
        <h3>Score Trend
          <span class="trend-label" :class="detail.trend.trend">{{ detail.trend.trend }}</span>
        </h3>
        <div class="chart-bars">
          <div class="bar-col" v-for="(s, i) in detail.trend.scores" :key="i">
            <div class="bar-fill" :class="scoreClass(s)" :style="{ height: (s / 10 * 120) + 'px' }"></div>
            <span class="bar-label">{{ s.toFixed(1) }}</span>
          </div>
        </div>
      </div>

      <!-- Recent runs -->
      <div class="runs-section">
        <h3>Recent Runs</h3>
        <div class="runs-table-wrap">
          <table class="runs-table" v-if="runs.length">
            <thead>
              <tr>
                <th>Time</th>
                <th>Score</th>
                <th>Prompt v</th>
                <th>Task</th>
                <th>Critique</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="run in runs" :key="run.run_id">
                <tr class="run-row" @click="expandedRun = expandedRun === run.run_id ? null : run.run_id">
                  <td class="time-cell">{{ formatTime(run.timestamp) }}</td>
                  <td>
                    <span class="score-badge small" :class="scoreClass(run.score)">{{ run.score.toFixed(1) }}</span>
                  </td>
                  <td class="center">v{{ run.prompt_version }}</td>
                  <td class="task-cell">{{ run.task.slice(0, 80) }}{{ run.task.length > 80 ? '…' : '' }}</td>
                  <td class="critique-cell">{{ run.critique.slice(0, 100) }}{{ run.critique.length > 100 ? '…' : '' }}
                    <span class="expand-hint">{{ expandedRun === run.run_id ? '▲' : '▼' }}</span>
                  </td>
                </tr>
                <tr v-if="expandedRun === run.run_id" class="run-expanded">
                  <td colspan="5">
                    <div class="expanded-body">
                      <div class="exp-section" v-if="run.task"><strong>Full task:</strong><pre>{{ run.task }}</pre></div>
                      <div class="exp-section" v-if="run.strengths"><strong>Strengths:</strong> {{ run.strengths }}</div>
                      <div class="exp-section" v-if="run.critique"><strong>Critique:</strong> {{ run.critique }}</div>
                      <div class="exp-section" v-if="run.output_snippet"><strong>Output snippet:</strong><pre>{{ run.output_snippet }}</pre></div>
                      <div class="exp-section run-meta">
                        Run ID: <code>{{ run.run_id }}</code> &nbsp;·&nbsp;
                        {{ new Date(run.timestamp * 1000).toLocaleString() }}
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
          <div v-else class="placeholder">No runs yet for this agent.</div>
        </div>
      </div>

      <!-- Prompt versions -->
      <div class="prompt-section" v-if="promptData">
        <h3>Prompt Evolution ({{ promptData.versions.length }} versions)</h3>
        <div class="prompt-version" v-for="v in [...promptData.versions].reverse()" :key="v.version">
          <div class="pv-header">
            <span class="pv-tag">v{{ v.version }}</span>
            <span class="pv-score" v-if="v.run_count">{{ v.avg_score.toFixed(1) }}/10 avg ({{ v.run_count }} runs)</span>
            <span class="pv-new" v-else>No runs yet</span>
            <button class="btn btn-xs btn-ghost" @click="expandedPrompt = expandedPrompt === v.version ? null : v.version">
              {{ expandedPrompt === v.version ? 'Collapse' : 'View' }}
            </button>
          </div>
          <div class="pv-rationale" v-if="v.rationale">
            <strong>Changes:</strong> {{ v.rationale.slice(0, 200) }}
          </div>
          <pre class="pv-prompt" v-if="expandedPrompt === v.version">{{ v.prompt }}</pre>
        </div>
      </div>
    </div>

    <!-- Try Refinement Modal -->
    <div class="modal-overlay" v-if="showTryRefine" @click.self="showTryRefine = false">
      <div class="modal">
        <h3>Try Iterative Refinement</h3>
        <label>Agent ID
          <input v-model="refineForm.agent_id" placeholder="e.g. my_agent" />
        </label>
        <label>Task
          <textarea v-model="refineForm.task" rows="3" placeholder="The task prompt…" />
        </label>
        <label>Initial Output
          <textarea v-model="refineForm.output" rows="5" placeholder="The initial draft to refine…" />
        </label>
        <div class="form-row">
          <label>Max Iterations
            <input type="number" v-model.number="refineForm.max_iterations" min="1" max="5" />
          </label>
          <label>Quality Threshold
            <input type="number" v-model.number="refineForm.score_threshold" min="1" max="10" step="0.5" />
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="showTryRefine = false">Cancel</button>
          <button class="btn btn-primary" @click="runRefinement" :disabled="refining">
            {{ refining ? 'Refining…' : 'Run Refinement' }}
          </button>
        </div>
        <div class="refine-result" v-if="refineResult">
          <div class="result-score">
            Final score: <strong :class="scoreClass(refineResult.final_score)">{{ refineResult.final_score?.toFixed(1) }}/10</strong>
            <span v-if="refineResult.converged" class="converged-badge">✓ Converged</span>
          </div>
          <div v-for="iter in refineResult.iterations" :key="iter.iteration" class="iter-row">
            <span class="iter-num">Iter {{ iter.iteration }}</span>
            <span class="iter-score" :class="scoreClass(iter.score)">{{ iter.score.toFixed(1) }}</span>
            <span class="iter-critique">{{ iter.critique }}</span>
          </div>
          <pre class="final-output">{{ refineResult.final_output }}</pre>
        </div>
      </div>
    </div>

    <!-- Best Prompt Modal -->
    <div class="modal-overlay" v-if="bestPromptModal" @click.self="bestPromptModal = null">
      <div class="modal">
        <h3>Best Prompt — {{ bestPromptModal.agent_id }}</h3>
        <p class="hint">This is the highest-scoring evolved prompt for this agent.</p>
        <pre class="pv-prompt">{{ bestPromptModal.best_prompt || '(No evolved prompt yet — run the agent a few times first)' }}</pre>
        <button class="btn btn-ghost" @click="bestPromptModal = null">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const agents = ref([])
const trends = ref({})
const selectedAgent = ref(null)
const detail = ref(null)
const runs = ref([])
const promptData = ref(null)
const expandedRun = ref(null)
const expandedPrompt = ref(null)
const loading = ref(false)
const error = ref(null)
const showTryRefine = ref(false)
const refining = ref(false)
const refineResult = ref(null)
const bestPromptModal = ref(null)

const refineForm = ref({
  agent_id: '',
  task: '',
  output: '',
  max_iterations: 3,
  score_threshold: 8.0,
})

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch('/api/performance')
    const data = await res.json()
    agents.value = data.agents || []

    // Load trends for all agents
    await Promise.all(agents.value.map(async (a) => {
      const r = await fetch(`/api/performance/${a.agent_id}`)
      if (r.ok) {
        const d = await r.json()
        trends.value[a.agent_id] = d.trend
      }
    }))
  } catch (err) {
    error.value = `Failed to load: ${err.message}`
  } finally {
    loading.value = false
  }
}

async function selectAgent(agentId) {
  selectedAgent.value = agentId
  detail.value = null
  runs.value = []
  promptData.value = null
  expandedPrompt.value = null
  expandedRun.value = null

  const [detailRes, runsRes, promptRes] = await Promise.all([
    fetch(`/api/performance/${agentId}`),
    fetch(`/api/performance/${agentId}/runs?n=20`),
    fetch(`/api/performance/${agentId}/prompt`),
  ])
  if (detailRes.ok) detail.value = await detailRes.json()
  if (runsRes.ok) {
    const d = await runsRes.json()
    runs.value = d.runs || []
  }
  if (promptRes.ok) promptData.value = await promptRes.json()
}

async function showBestPrompt(agentId) {
  const res = await fetch(`/api/performance/${agentId}/prompt`)
  if (res.ok) {
    const data = await res.json()
    bestPromptModal.value = { agent_id: agentId, ...data }
  }
}

async function resetAgent(agentId) {
  if (!confirm(`Reset ALL performance data for "${agentId}"? This cannot be undone.`)) return
  await fetch(`/api/performance/${agentId}`, { method: 'DELETE' })
  await loadData()
  selectedAgent.value = null
  detail.value = null
}

async function runRefinement() {
  if (!refineForm.value.agent_id?.trim()) {
    error.value = 'Please enter an Agent ID before running refinement.'
    return
  }
  refining.value = true
  refineResult.value = null
  try {
    const res = await fetch(`/api/performance/${encodeURIComponent(refineForm.value.agent_id.trim())}/refine`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task: refineForm.value.task,
        initial_output: refineForm.value.output,
        max_iterations: refineForm.value.max_iterations,
        score_threshold: refineForm.value.score_threshold,
      }),
    })
    const data = await res.json()
    refineResult.value = data
    await loadData()
  } catch (err) {
    error.value = `Refinement error: ${err.message}`
  } finally {
    refining.value = false
  }
}

function scoreClass(score) {
  if (score >= 8) return 'excellent'
  if (score >= 6) return 'good'
  if (score >= 4) return 'fair'
  return 'poor'
}

function formatTime(ts) {
  return new Date(ts * 1000).toLocaleString()
}

onMounted(loadData)
</script>

<style scoped>
.perf-view { padding: 24px; max-width: 1280px; margin: 0 auto; }

.header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
.subtitle { color: var(--text-secondary, #6b7280); font-size: 0.875rem; margin: 4px 0 0; }
.header-actions { display: flex; gap: 10px; }

.btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; cursor: pointer; border: 1px solid transparent; }
.btn-ghost { background: transparent; border-color: var(--border-color, #ddd); }
.btn-primary { background: #2563eb; color: white; }
.btn-danger { background: #dc2626; color: white; }
.btn-sm { padding: 5px 10px; font-size: 0.8rem; }
.btn-xs { padding: 2px 8px; font-size: 0.75rem; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }

.spinning .icon { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.error-banner { background: #fee2e2; color: #b91c1c; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; }

.empty-state { text-align: center; padding: 80px 20px; color: var(--text-secondary, #6b7280); }
.empty-icon { font-size: 3rem; margin-bottom: 16px; }
.empty-state h3 { font-size: 1.2rem; margin-bottom: 8px; color: #374151; }
.empty-state p { font-size: 0.875rem; line-height: 1.6; }
code { background: #f3f4f6; padding: 2px 6px; border-radius: 3px; font-size: 0.85rem; }

.agents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-bottom: 32px; }

.agent-card { background: var(--card-bg, #fff); border: 2px solid var(--border-color, #e5e7eb); border-radius: 10px; padding: 16px; cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s; }
.agent-card:hover { border-color: #2563eb; box-shadow: 0 2px 8px rgba(37,99,235,0.1); }
.agent-card.selected { border-color: #2563eb; background: #eff6ff; }

.agent-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.agent-name { font-weight: 600; font-size: 0.95rem; word-break: break-all; }
.agent-meta { display: flex; gap: 12px; font-size: 0.75rem; color: var(--text-secondary, #6b7280); margin-bottom: 12px; }

.score-badge { padding: 2px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
.score-badge.small { padding: 1px 7px; font-size: 0.75rem; }
.score-badge.excellent, .bar-fill.excellent { background: #d1fae5; color: #065f46; }
.score-badge.good, .bar-fill.good { background: #dbeafe; color: #1e40af; }
.score-badge.fair, .bar-fill.fair { background: #fef3c7; color: #92400e; }
.score-badge.poor, .bar-fill.poor { background: #fee2e2; color: #991b1b; }
.mini-bar.excellent { background: #10b981; }
.mini-bar.good { background: #3b82f6; }
.mini-bar.fair { background: #f59e0b; }
.mini-bar.poor { background: #ef4444; }

.mini-trend { display: flex; align-items: flex-end; gap: 3px; height: 44px; }
.mini-bar { width: 10px; border-radius: 2px 2px 0 0; min-height: 4px; }
.trend-label { font-size: 0.7rem; font-weight: 600; margin-left: 6px; }
.trend-label.improving { color: #10b981; }
.trend-label.declining { color: #ef4444; }
.trend-label.stable { color: #6b7280; }

.detail-panel { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e5e7eb); border-radius: 12px; padding: 24px; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.detail-header h2 { font-size: 1.2rem; font-weight: 700; }
.detail-actions { display: flex; gap: 8px; }

.trend-chart { margin-bottom: 28px; }
.trend-chart h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 10px; }
.chart-bars { display: flex; align-items: flex-end; gap: 6px; height: 140px; }
.bar-col { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.bar-fill { width: 28px; border-radius: 3px 3px 0 0; min-height: 4px; transition: height 0.3s; }
.bar-label { font-size: 0.7rem; color: #6b7280; }

.runs-section h3, .prompt-section h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 14px; }
.runs-table-wrap { overflow-x: auto; }
.runs-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.runs-table th { text-align: left; padding: 8px 12px; border-bottom: 2px solid #e5e7eb; font-size: 0.72rem; text-transform: uppercase; color: #6b7280; letter-spacing: 0.05em; }
.runs-table td { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; cursor: pointer; }
.runs-table tr:hover td { background: #f9fafb; }
.time-cell { white-space: nowrap; color: #6b7280; }
.task-cell { max-width: 280px; }
.critique-cell { max-width: 300px; color: #6b7280; }
.center { text-align: center; }
.run-row { cursor: pointer; }
.expand-hint { color: #9ca3af; font-size: 0.7rem; margin-left: 6px; }
.run-expanded td { background: #f9fafb; padding: 0; }
.expanded-body { padding: 12px 16px; border-left: 3px solid #e5e7eb; margin: 4px 0; }
.exp-section { margin-bottom: 10px; font-size: 0.82rem; line-height: 1.5; }
.exp-section pre { background: #fff; border: 1px solid #e5e7eb; border-radius: 4px; padding: 8px; margin-top: 4px; white-space: pre-wrap; font-size: 0.8rem; max-height: 150px; overflow-y: auto; }
.run-meta { color: #9ca3af; font-size: 0.75rem; }
.run-meta code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; }

.prompt-section { margin-top: 28px; }
.prompt-version { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; }
.pv-header { display: flex; align-items: center; gap: 10px; }
.pv-tag { background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
.pv-score { font-size: 0.8rem; color: #374151; }
.pv-new { font-size: 0.8rem; color: #9ca3af; }
.pv-rationale { font-size: 0.8rem; color: #6b7280; margin-top: 6px; }
.pv-prompt { background: #f9fafb; padding: 12px; border-radius: 6px; font-size: 0.8rem; white-space: pre-wrap; margin-top: 8px; max-height: 300px; overflow-y: auto; }

.placeholder { color: #9ca3af; font-size: 0.875rem; padding: 16px 0; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: min(700px, 95vw); max-height: 90vh; overflow-y: auto; }
.modal h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 16px; }
.modal label { display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; font-weight: 500; margin-bottom: 12px; }
.modal input, .modal textarea { padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; font-family: inherit; }
.form-row { display: flex; gap: 16px; }
.form-row label { flex: 1; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.hint { color: #6b7280; font-size: 0.85rem; margin-bottom: 12px; }

.refine-result { margin-top: 20px; border-top: 1px solid #e5e7eb; padding-top: 16px; }
.result-score { font-size: 1rem; margin-bottom: 12px; display: flex; align-items: center; gap: 10px; }
.converged-badge { background: #d1fae5; color: #065f46; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; }
.iter-row { display: flex; align-items: baseline; gap: 10px; padding: 6px 0; border-bottom: 1px solid #f3f4f6; font-size: 0.85rem; }
.iter-num { font-weight: 600; width: 50px; }
.iter-score { font-weight: 600; width: 40px; }
.iter-critique { color: #6b7280; flex: 1; }
.final-output { background: #f9fafb; padding: 12px; border-radius: 6px; white-space: pre-wrap; font-size: 0.82rem; margin-top: 12px; max-height: 300px; overflow-y: auto; }

.excellent { color: #065f46; } .good { color: #1e40af; } .fair { color: #92400e; } .poor { color: #991b1b; }
</style>
