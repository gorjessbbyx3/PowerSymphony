<template>
  <div class="cicd-view">
    <div class="header">
      <div>
        <h1>CI/CD Automation</h1>
        <p class="subtitle">Auto-generate GitHub Actions workflows, Dockerfiles, docker-compose, and AWS pipelines — cut deployment setup time by 40%</p>
      </div>
    </div>

    <!-- Pipeline Type Tabs -->
    <div class="type-tabs">
      <button v-for="t in types" :key="t.id" :class="['type-tab', {active: activeType === t.id}]" @click="activeType = t.id">
        <span class="tab-icon">{{ t.icon }}</span>
        <span>{{ t.name }}</span>
      </button>
    </div>

    <!-- GitHub Actions -->
    <div v-if="activeType === 'github-actions'" class="generator-panel">
      <div class="form-panel">
        <h2 class="panel-title">GitHub Actions CI/CD</h2>
        <div class="form-grid">
          <div class="form-group">
            <label class="label">Project Name</label>
            <input v-model="gaForm.project_name" class="input" placeholder="my-awesome-app" />
          </div>
          <div class="form-group">
            <label class="label">Language / Framework</label>
            <select v-model="gaForm.language" class="select">
              <option value="python">Python</option>
              <option value="node">Node.js</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="java">Java</option>
              <option value="ruby">Ruby</option>
            </select>
          </div>
          <div class="form-group">
            <label class="label">Test Command</label>
            <input v-model="gaForm.test_command" class="input" placeholder="e.g. pytest or npm test" />
          </div>
          <div class="form-group">
            <label class="label">Deploy Target</label>
            <select v-model="gaForm.deploy_target" class="select">
              <option value="none">No deployment step</option>
              <option value="vercel">Vercel</option>
              <option value="netlify">Netlify</option>
              <option value="docker-hub">Docker Hub</option>
              <option value="aws-eb">AWS Elastic Beanstalk</option>
              <option value="heroku">Heroku</option>
            </select>
          </div>
          <div class="form-group">
            <label class="label">Trigger Branch</label>
            <input v-model="gaForm.branch" class="input" placeholder="main" />
          </div>
        </div>
        <button class="btn btn-primary" @click="generate('github-actions')" :disabled="loading">
          {{ loading ? 'Generating…' : 'Generate Pipeline' }}
        </button>
      </div>
      <ResultPanel v-if="result" :result="result" />
    </div>

    <!-- Dockerfile -->
    <div v-if="activeType === 'dockerfile'" class="generator-panel">
      <div class="form-panel">
        <h2 class="panel-title">Dockerfile Generator</h2>
        <div class="form-grid">
          <div class="form-group">
            <label class="label">Language</label>
            <select v-model="dfForm.language" class="select">
              <option value="python">Python</option>
              <option value="node">Node.js</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="java">Java</option>
            </select>
          </div>
          <div class="form-group">
            <label class="label">App Port</label>
            <input v-model.number="dfForm.app_port" class="input" type="number" placeholder="8000" />
          </div>
          <div class="form-group full-width">
            <label class="label">Entry Point Command</label>
            <input v-model="dfForm.entry_point" class="input" placeholder="e.g. python app.py or npm start" />
          </div>
        </div>
        <button class="btn btn-primary" @click="generate('dockerfile')" :disabled="loading">
          {{ loading ? 'Generating…' : 'Generate Dockerfile' }}
        </button>
      </div>
      <ResultPanel v-if="result" :result="result" />
    </div>

    <!-- Docker Compose -->
    <div v-if="activeType === 'docker-compose'" class="generator-panel">
      <div class="form-panel">
        <h2 class="panel-title">Docker Compose Generator</h2>
        <div class="form-grid">
          <div class="form-group full-width">
            <label class="label">Services (name:language, comma-separated)</label>
            <input v-model="dcForm.services" class="input" placeholder="api:python, frontend:node, worker:python" />
          </div>
          <div class="form-group">
            <label class="label">Add Database</label>
            <select v-model="dcForm.with_database" class="select">
              <option value="none">No database</option>
              <option value="postgres">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="mongodb">MongoDB</option>
              <option value="redis">Redis</option>
            </select>
          </div>
        </div>
        <button class="btn btn-primary" @click="generate('docker-compose')" :disabled="loading">
          {{ loading ? 'Generating…' : 'Generate docker-compose.yml' }}
        </button>
      </div>
      <ResultPanel v-if="result" :result="result" />
    </div>

    <!-- AWS CodePipeline -->
    <div v-if="activeType === 'aws'" class="generator-panel">
      <div class="form-panel">
        <h2 class="panel-title">AWS CodePipeline (CloudFormation)</h2>
        <div class="form-grid">
          <div class="form-group">
            <label class="label">Project Name</label>
            <input v-model="awsForm.project_name" class="input" placeholder="my-service" />
          </div>
          <div class="form-group">
            <label class="label">GitHub Owner / Org</label>
            <input v-model="awsForm.repo_owner" class="input" placeholder="my-github-org" />
          </div>
          <div class="form-group">
            <label class="label">Repository Name</label>
            <input v-model="awsForm.repo_name" class="input" placeholder="my-repo" />
          </div>
          <div class="form-group">
            <label class="label">Deploy To</label>
            <select v-model="awsForm.deploy_stack" class="select">
              <option value="ecs">ECS (Fargate)</option>
              <option value="lambda">Lambda</option>
              <option value="s3">S3 (static)</option>
              <option value="eb">Elastic Beanstalk</option>
            </select>
          </div>
        </div>
        <button class="btn btn-primary" @click="generate('aws')" :disabled="loading">
          {{ loading ? 'Generating…' : 'Generate CloudFormation Template' }}
        </button>
      </div>
      <ResultPanel v-if="result" :result="result" />
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, defineComponent, h } from 'vue'

const ResultPanel = defineComponent({
  props: ['result'],
  setup(props) {
    const copied = ref(false)
    function copy() {
      navigator.clipboard.writeText(props.result.content || '').then(() => { copied.value = true; setTimeout(() => copied.value = false, 2000) })
    }
    function download() {
      const blob = new Blob([props.result.content || ''], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = props.result.filename || 'pipeline.yml'; a.click()
      URL.revokeObjectURL(url)
    }
    return () => h('div', { class: 'result-panel' }, [
      h('div', { class: 'result-header' }, [
        h('span', { class: 'result-filename' }, props.result.filename || 'output'),
        h('div', { class: 'result-actions' }, [
          h('button', { class: 'btn btn-sm btn-ghost', onClick: copy }, copied.value ? '✓ Copied' : 'Copy'),
          h('button', { class: 'btn btn-sm btn-primary', onClick: download }, 'Download'),
        ]),
      ]),
      h('pre', { class: 'result-code' }, props.result.content || ''),
    ])
  },
})

const activeType = ref('github-actions')
const loading = ref(false)
const error = ref('')
const result = ref(null)

const types = [
  { id: 'github-actions', name: 'GitHub Actions', icon: '⚙️' },
  { id: 'dockerfile', name: 'Dockerfile', icon: '🐳' },
  { id: 'docker-compose', name: 'Docker Compose', icon: '🗃️' },
  { id: 'aws', name: 'AWS CodePipeline', icon: '☁️' },
]

const gaForm = ref({ project_name: '', language: 'python', test_command: '', deploy_target: 'none', branch: 'main' })
const dfForm = ref({ language: 'python', app_port: 8000, entry_point: '' })
const dcForm = ref({ services: 'api:python, frontend:node', with_database: 'none' })
const awsForm = ref({ project_name: '', repo_owner: '', repo_name: '', deploy_stack: 'ecs' })

const ENDPOINTS = {
  'github-actions': { url: '/api/cicd/github-actions', body: () => gaForm.value },
  'dockerfile': { url: '/api/cicd/dockerfile', body: () => dfForm.value },
  'docker-compose': { url: '/api/cicd/docker-compose', body: () => dcForm.value },
  'aws': { url: '/api/cicd/aws-codepipeline', body: () => awsForm.value },
}

async function generate(type) {
  const ep = ENDPOINTS[type]
  if (!ep) return
  loading.value = true; error.value = ''; result.value = null
  try {
    const res = await fetch(ep.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ep.body()),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'API error')
    result.value = { filename: data.filename, content: data.content }
  } catch (e) { error.value = e.message } finally { loading.value = false }
}

function watchType() { result.value = null; error.value = '' }
</script>

<style scoped>
.cicd-view { max-width: 1100px; margin: 0 auto; padding: 32px 24px; font-family: 'Inter', sans-serif; }
.header { margin-bottom: 24px; }
.header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(90deg, #aaffcd, #99eaf9, #a0c4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 6px; }
.subtitle { color: #8e8e8e; margin: 0; font-size: 14px; }
.type-tabs { display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap; }
.type-tab { display: flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 10px; border: 1px solid #2d2d2d; background: #1a1a1a; color: #8e8e8e; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
.type-tab.active { border-color: #aaffcd55; background: #0d2d1a; color: #aaffcd; }
.type-tab:hover:not(.active) { border-color: #3d3d3d; color: #c0c0c0; }
.tab-icon { font-size: 16px; }
.generator-panel { display: flex; flex-direction: column; gap: 20px; }
.form-panel { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 24px; }
.panel-title { font-size: 16px; font-weight: 600; color: #f0f0f0; margin: 0 0 20px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group.full-width { grid-column: 1 / -1; }
.label { font-size: 12px; font-weight: 500; color: #8e8e8e; }
.input { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; font-family: inherit; }
.input:focus { outline: none; border-color: #aaffcd; }
.select { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; width: 100%; }
.btn { padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity 0.2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: linear-gradient(135deg, #aaffcd, #99eaf9); color: #0f0f0f; }
.btn-ghost { background: #1f1f1f; border: 1px solid #2d2d2d; color: #c0c0c0; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.result-panel { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; overflow: hidden; }
.result-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid #2d2d2d; }
.result-filename { font-family: monospace; font-size: 13px; color: #99eaf9; }
.result-actions { display: flex; gap: 8px; }
.result-code { margin: 0; padding: 20px; background: #0a0a0a; font-family: 'Courier New', monospace; font-size: 12px; color: #e0e0e0; overflow: auto; max-height: 600px; white-space: pre; line-height: 1.5; }
.error-banner { background: #2d0f0f; border: 1px solid #6b1f1f; color: #ff9999; padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-top: 16px; }
@media (max-width: 700px) { .form-grid { grid-template-columns: 1fr; } }
</style>
