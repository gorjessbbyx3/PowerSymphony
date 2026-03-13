<template>
  <div class="diagram-view">
    <div class="header">
      <div>
        <h1>Visual Debugging</h1>
        <p class="subtitle">AI-generated Mermaid diagrams for architecture visualization, bug tracing, and workflow documentation</p>
      </div>
    </div>

    <!-- Mode Tabs -->
    <div class="mode-tabs">
      <button :class="['mode-tab', {active: mode === 'editor'}]" @click="mode = 'editor'">Live Editor</button>
      <button :class="['mode-tab', {active: mode === 'generate'}]" @click="mode = 'generate'">Generate from Description</button>
      <button :class="['mode-tab', {active: mode === 'debug'}]" @click="mode = 'debug'">Debug Flowchart</button>
      <button :class="['mode-tab', {active: mode === 'sequence'}]" @click="mode = 'sequence'">Sequence Diagram</button>
    </div>

    <!-- Live Editor Mode -->
    <div v-if="mode === 'editor'" class="split-panel">
      <div class="panel-left">
        <div class="panel-header">
          <h3>Mermaid Source</h3>
          <div class="panel-actions">
            <select v-model="diagramType" class="select" @change="insertTemplate">
              <option value="">— Insert Template —</option>
              <option value="flowchart">Flowchart</option>
              <option value="sequence">Sequence</option>
              <option value="classDiagram">Class Diagram</option>
              <option value="erDiagram">ER Diagram</option>
              <option value="stateDiagram">State Machine</option>
              <option value="gantt">Gantt Chart</option>
              <option value="pie">Pie Chart</option>
              <option value="gitGraph">Git Graph</option>
            </select>
          </div>
        </div>
        <textarea
          v-model="mermaidSource"
          class="code-input"
          placeholder="Enter Mermaid diagram source here…"
          @input="renderDiagram"
          spellcheck="false"
        ></textarea>
      </div>
      <div class="panel-right">
        <div class="panel-header">
          <h3>Preview</h3>
          <button class="btn btn-sm btn-ghost" @click="exportSVG">Export SVG</button>
        </div>
        <div class="diagram-container" id="mermaid-preview">
          <div v-if="renderError" class="render-error">{{ renderError }}</div>
          <div v-else-if="!renderedSVG" class="diagram-placeholder">Start typing Mermaid source to see the diagram</div>
          <div v-else v-html="renderedSVG" class="svg-output"></div>
        </div>
      </div>
    </div>

    <!-- Generate from Description Mode -->
    <div v-if="mode === 'generate'" class="section-card">
      <h2 class="section-title">Generate Diagram from Description</h2>
      <div class="form-grid">
        <div class="form-group">
          <label class="label">Diagram Type</label>
          <select v-model="genType" class="select full">
            <option value="flowchart">Flowchart</option>
            <option value="sequence">Sequence Diagram</option>
            <option value="classDiagram">Class Diagram</option>
            <option value="erDiagram">ER Diagram</option>
            <option value="stateDiagram">State Machine</option>
            <option value="architecture">Architecture (flowchart LR)</option>
          </select>
        </div>
        <div class="form-group full-width">
          <label class="label">Description</label>
          <textarea
            v-model="genDescription"
            class="textarea"
            rows="4"
            placeholder="Describe what you want to diagram, e.g. 'A user authentication flow with login, JWT token generation, and refresh token rotation'"
          ></textarea>
        </div>
        <button class="btn btn-primary" @click="generateDiagram" :disabled="generating">
          {{ generating ? 'Generating…' : 'Generate Diagram' }}
        </button>
      </div>

      <div v-if="generated.mermaid" class="generated-result">
        <div class="split-panel compact">
          <div class="panel-left">
            <div class="panel-header"><h3>Generated Source</h3>
              <button class="btn btn-sm btn-ghost" @click="useInEditor(generated.mermaid)">Open in Editor</button>
            </div>
            <pre class="code-block">{{ generated.mermaid }}</pre>
          </div>
          <div class="panel-right">
            <div class="panel-header"><h3>Preview</h3></div>
            <div class="diagram-container">
              <div v-if="generated.svg" v-html="generated.svg" class="svg-output"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Debug Flowchart Mode -->
    <div v-if="mode === 'debug'" class="section-card">
      <h2 class="section-title">Debug Flowchart Generator</h2>
      <p class="mode-desc">Paste an error and the code context — get an AI-generated flowchart tracing the bug</p>
      <div class="form-grid">
        <div class="form-group">
          <label class="label">Error Message</label>
          <input v-model="debugForm.error" class="input" placeholder="e.g. KeyError: 'user_id' or TypeError: cannot read property 'map'" />
        </div>
        <div class="form-group">
          <label class="label">Language</label>
          <select v-model="debugForm.language" class="select full">
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="go">Go</option>
            <option value="java">Java</option>
            <option value="rust">Rust</option>
          </select>
        </div>
        <div class="form-group full-width">
          <label class="label">Code Context (paste the relevant code)</label>
          <textarea v-model="debugForm.code" class="textarea" rows="8" placeholder="Paste the code where the error occurs…"></textarea>
        </div>
        <button class="btn btn-primary" @click="generateDebugChart" :disabled="debugging">
          {{ debugging ? 'Analyzing…' : 'Generate Debug Flowchart' }}
        </button>
      </div>
      <div v-if="debugResult.mermaid" class="generated-result">
        <div class="debug-analysis" v-if="debugResult.root_cause">
          <div class="analysis-item">
            <span class="analysis-label">Root Cause</span>
            <span class="analysis-value">{{ debugResult.root_cause }}</span>
          </div>
          <div class="analysis-item">
            <span class="analysis-label">Fix</span>
            <span class="analysis-value fix">{{ debugResult.fix_suggestion }}</span>
          </div>
        </div>
        <div class="split-panel compact">
          <div class="panel-left">
            <div class="panel-header"><h3>Debug Flowchart Source</h3>
              <button class="btn btn-sm btn-ghost" @click="useInEditor(debugResult.mermaid)">Open in Editor</button>
            </div>
            <pre class="code-block">{{ debugResult.mermaid }}</pre>
          </div>
          <div class="panel-right">
            <div class="panel-header"><h3>Preview</h3></div>
            <div class="diagram-container">
              <div v-if="debugResult.svg" v-html="debugResult.svg" class="svg-output"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Sequence Diagram Mode -->
    <div v-if="mode === 'sequence'" class="section-card">
      <h2 class="section-title">Sequence Diagram Generator</h2>
      <div class="form-grid">
        <div class="form-group full-width">
          <label class="label">Participants (comma-separated)</label>
          <input v-model="seqForm.participants" class="input" placeholder="e.g. User, Frontend, API Server, Database, Auth Service" />
        </div>
        <div class="form-group full-width">
          <label class="label">Scenario Description</label>
          <textarea v-model="seqForm.scenario" class="textarea" rows="5" placeholder="Describe the interaction flow, e.g. 'User submits login form → Frontend sends POST /auth/login → API verifies credentials in Database → Returns JWT → Frontend stores in localStorage'"></textarea>
        </div>
        <button class="btn btn-primary" @click="generateSequence" :disabled="sequencing">
          {{ sequencing ? 'Generating…' : 'Generate Sequence Diagram' }}
        </button>
      </div>
      <div v-if="seqResult.mermaid" class="generated-result">
        <div class="split-panel compact">
          <div class="panel-left">
            <div class="panel-header"><h3>Source</h3>
              <button class="btn btn-sm btn-ghost" @click="useInEditor(seqResult.mermaid)">Open in Editor</button>
            </div>
            <pre class="code-block">{{ seqResult.mermaid }}</pre>
          </div>
          <div class="panel-right">
            <div class="panel-header"><h3>Preview</h3></div>
            <div class="diagram-container">
              <div v-if="seqResult.svg" v-html="seqResult.svg" class="svg-output"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="apiError" class="error-banner">{{ apiError }}</div>
    <!-- hidden mermaid render target required by mermaid v10+ -->
    <div id="mermaid-render-target" style="position:fixed;left:-9999px;top:-9999px;visibility:hidden;pointer-events:none;"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import mermaid from 'mermaid'

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: { primaryColor: '#1a1a2e', edgeLabelBackground: '#1a1a1a', fontSize: '14px' },
  securityLevel: 'loose',
})

const mode = ref('editor')
const mermaidSource = ref(`flowchart TD
  A([Start]) --> B{User logged in?}
  B -- Yes --> C[Load Dashboard]
  B -- No --> D[Redirect to Login]
  D --> E[Submit Credentials]
  E --> F{Valid?}
  F -- Yes --> G[Create JWT Token]
  G --> C
  F -- No --> H[Show Error]
  H --> D
  C --> I([End])`)
const renderedSVG = ref('')
const renderError = ref('')
const diagramType = ref('')
const apiError = ref('')

const generating = ref(false)
const genType = ref('flowchart')
const genDescription = ref('')
const generated = ref({ mermaid: '', svg: '' })

const debugging = ref(false)
const debugForm = ref({ error: '', language: 'python', code: '' })
const debugResult = ref({ mermaid: '', svg: '', root_cause: '', fix_suggestion: '' })

const sequencing = ref(false)
const seqForm = ref({ participants: '', scenario: '' })
const seqResult = ref({ mermaid: '', svg: '' })

const TEMPLATES = {
  flowchart: `flowchart TD\n  A[Start] --> B{Decision?}\n  B -- Yes --> C[Process]\n  B -- No --> D[End]\n  C --> D`,
  sequence: `sequenceDiagram\n  participant User\n  participant Server\n  participant DB\n  User->>Server: POST /login\n  Server->>DB: Query user\n  DB-->>Server: User record\n  Server-->>User: JWT token`,
  classDiagram: `classDiagram\n  class Animal {\n    +String name\n    +int age\n    +speak() void\n  }\n  class Dog {\n    +fetch() void\n  }\n  Animal <|-- Dog`,
  erDiagram: `erDiagram\n  USER {\n    int id PK\n    string name\n    string email\n  }\n  ORDER {\n    int id PK\n    int user_id FK\n    float total\n  }\n  USER ||--o{ ORDER : places`,
  stateDiagram: `stateDiagram-v2\n  [*] --> Idle\n  Idle --> Processing : start\n  Processing --> Success : done\n  Processing --> Failed : error\n  Success --> [*]\n  Failed --> Idle : retry`,
  gantt: `gantt\n  title Project Timeline\n  dateFormat YYYY-MM-DD\n  section Planning\n    Requirements : a1, 2024-01-01, 7d\n    Design : a2, after a1, 5d\n  section Development\n    Backend : b1, after a2, 14d\n    Frontend : b2, after a2, 14d`,
  pie: `pie title Browser Share\n  "Chrome" : 65.5\n  "Firefox" : 15.2\n  "Safari" : 12.1\n  "Edge" : 7.2`,
  gitGraph: `gitGraph\n  commit id: "Initial"\n  branch develop\n  checkout develop\n  commit id: "Feature"\n  checkout main\n  merge develop\n  commit id: "Release v1"`,
}

function insertTemplate() {
  if (diagramType.value && TEMPLATES[diagramType.value]) {
    mermaidSource.value = TEMPLATES[diagramType.value]
    diagramType.value = ''
    renderDiagram()
  }
}

function getRenderContainer() {
  return document.getElementById('mermaid-render-target')
}

async function renderDiagram() {
  const src = mermaidSource.value.trim()
  if (!src) { renderedSVG.value = ''; renderError.value = ''; return }
  renderError.value = ''
  try {
    const id = 'mermaid-' + Date.now()
    const container = getRenderContainer()
    const { svg } = await mermaid.render(id, src, container)
    renderedSVG.value = svg
  } catch (e) {
    renderError.value = e.message || 'Invalid Mermaid syntax'
    renderedSVG.value = ''
  }
}

async function renderToSVG(src) {
  if (!src?.trim()) return ''
  try {
    const id = 'mermaid-gen-' + Date.now()
    const container = getRenderContainer()
    const { svg } = await mermaid.render(id, src, container)
    return svg
  } catch { return '' }
}

async function postApi(path, body) {
  const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'API error')
  return data
}

async function generateDiagram() {
  if (!genDescription.value) return
  generating.value = true
  apiError.value = ''
  generated.value = { mermaid: '', svg: '' }
  try {
    const data = await postApi('/api/diagrams/generate', { description: genDescription.value, diagram_type: genType.value })
    const src = data.mermaid || ''
    generated.value.mermaid = src
    generated.value.svg = await renderToSVG(src)
  } catch (e) { apiError.value = e.message } finally { generating.value = false }
}

async function generateDebugChart() {
  if (!debugForm.value.error || !debugForm.value.code) return
  debugging.value = true
  apiError.value = ''
  debugResult.value = { mermaid: '', svg: '', root_cause: '', fix_suggestion: '' }
  try {
    const data = await postApi('/api/diagrams/debug', debugForm.value)
    debugResult.value.mermaid = data.mermaid || ''
    debugResult.value.root_cause = data.root_cause || ''
    debugResult.value.fix_suggestion = data.fix_suggestion || ''
    debugResult.value.svg = await renderToSVG(debugResult.value.mermaid)
  } catch (e) { apiError.value = e.message } finally { debugging.value = false }
}

async function generateSequence() {
  if (!seqForm.value.participants || !seqForm.value.scenario) return
  sequencing.value = true
  apiError.value = ''
  seqResult.value = { mermaid: '', svg: '' }
  try {
    const data = await postApi('/api/diagrams/sequence', seqForm.value)
    seqResult.value.mermaid = data.mermaid || ''
    seqResult.value.svg = await renderToSVG(seqResult.value.mermaid)
  } catch (e) { apiError.value = e.message } finally { sequencing.value = false }
}

function useInEditor(src) {
  mermaidSource.value = src
  mode.value = 'editor'
  renderDiagram()
}

function exportSVG() {
  if (!renderedSVG.value) return
  const blob = new Blob([renderedSVG.value], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'diagram.svg'; a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => renderDiagram())
</script>

<style scoped>
.diagram-view { max-width: 1400px; margin: 0 auto; padding: 32px 24px; font-family: 'Inter', sans-serif; }
.header { margin-bottom: 24px; }
.header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(90deg, #aaffcd, #99eaf9, #a0c4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 6px; }
.subtitle { color: #8e8e8e; margin: 0; font-size: 14px; }
.mode-tabs { display: flex; gap: 4px; background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 10px; padding: 5px; margin-bottom: 20px; }
.mode-tab { flex: 1; padding: 9px; border-radius: 7px; border: none; cursor: pointer; font-size: 13px; background: transparent; color: #8e8e8e; transition: all 0.2s; }
.mode-tab.active { background: #2d2d2d; color: #f0f0f0; }
.split-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; min-height: 500px; }
.split-panel.compact { min-height: 300px; margin-top: 16px; }
.panel-left, .panel-right { display: flex; flex-direction: column; background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 10px; overflow: hidden; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid #2d2d2d; }
.panel-header h3 { margin: 0; font-size: 13px; font-weight: 600; color: #c0c0c0; }
.panel-actions { display: flex; gap: 8px; align-items: center; }
.select { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 6px; color: #c0c0c0; padding: 5px 8px; font-size: 12px; }
.select.full { width: 100%; }
.code-input { flex: 1; background: #0a0a0a; border: none; padding: 16px; color: #e0e0e0; font-family: 'Courier New', monospace; font-size: 13px; resize: none; outline: none; line-height: 1.5; }
.diagram-container { flex: 1; padding: 16px; overflow: auto; display: flex; align-items: flex-start; justify-content: center; }
.diagram-placeholder { color: #555; font-size: 13px; margin: auto; }
.render-error { color: #ff9999; font-size: 12px; font-family: monospace; padding: 8px; }
.svg-output { width: 100%; }
.svg-output :deep(svg) { max-width: 100%; height: auto; }
.section-card { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
.section-title { font-size: 16px; font-weight: 600; color: #f0f0f0; margin: 0 0 8px; }
.mode-desc { font-size: 13px; color: #8e8e8e; margin: 0 0 20px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: start; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group.full-width { grid-column: 1 / -1; }
.label { font-size: 12px; font-weight: 500; color: #8e8e8e; }
.input { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; font-family: inherit; }
.input:focus { outline: none; border-color: #aaffcd; }
.textarea { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; font-family: inherit; resize: vertical; }
.textarea:focus { outline: none; border-color: #aaffcd; }
.btn { padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity 0.2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: linear-gradient(135deg, #aaffcd, #99eaf9); color: #0f0f0f; }
.btn-ghost { background: #1f1f1f; border: 1px solid #2d2d2d; color: #c0c0c0; }
.btn-sm { padding: 5px 11px; font-size: 12px; }
.generated-result { margin-top: 20px; }
.code-block { background: #0a0a0a; border: 1px solid #1f1f1f; border-radius: 8px; padding: 14px 16px; font-size: 12px; color: #e0e0e0; font-family: 'Courier New', monospace; overflow: auto; max-height: 300px; white-space: pre; margin: 0; }
.debug-analysis { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.analysis-item { background: #0f0f0f; border-radius: 8px; padding: 12px; }
.analysis-label { display: block; font-size: 11px; font-weight: 600; color: #8e8e8e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.analysis-value { font-size: 13px; color: #e0e0e0; line-height: 1.5; }
.analysis-value.fix { color: #aaffcd; }
.error-banner { background: #2d0f0f; border: 1px solid #6b1f1f; color: #ff9999; padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-top: 16px; }
@media (max-width: 900px) {
  .split-panel { grid-template-columns: 1fr; }
  .form-grid { grid-template-columns: 1fr; }
  .debug-analysis { grid-template-columns: 1fr; }
}
</style>
