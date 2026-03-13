<template>
  <div class="finetune-view">
    <div class="header">
      <div>
        <h1>Model Fine-Tuning</h1>
        <p class="subtitle">Personalize LLMs on your domain data using OpenAI fine-tuning — improving suggestions 20-30% for specialized tasks</p>
      </div>
      <button class="btn btn-ghost" @click="loadJobs">↻ Refresh</button>
    </div>

    <div class="tabs">
      <button v-for="t in tabs" :key="t.id" :class="['tab', {active: activeTab === t.id}]" @click="activeTab = t.id">{{ t.label }}</button>
    </div>

    <!-- Upload Dataset -->
    <div v-if="activeTab === 'upload'" class="section-card">
      <h2 class="section-title">Upload Training Dataset</h2>
      <p class="section-desc">
        Training data must be in JSONL format — one JSON object per line. Each object must have a <code>messages</code> array with system, user, and assistant turns.
      </p>

      <div class="example-banner" @click="loadExample">
        <span>📋 Load example dataset</span>
        <span class="example-arrow">→</span>
      </div>

      <div class="form-col">
        <div class="form-group">
          <label class="label">Dataset Filename</label>
          <input v-model="upload.filename" class="input" placeholder="training_data.jsonl" />
        </div>
        <div class="form-group">
          <label class="label">Training Data (JSONL)</label>
          <textarea
            v-model="upload.training_data"
            class="textarea mono"
            rows="14"
            placeholder='{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}'
          ></textarea>
          <div class="line-count">{{ upload.training_data.split('\n').filter(l => l.trim()).length }} examples</div>
        </div>
        <button class="btn btn-primary" @click="uploadDataset" :disabled="uploading">
          {{ uploading ? 'Uploading…' : 'Upload to OpenAI' }}
        </button>
        <div v-if="uploadResult" class="result-box success">
          <strong>✓ Uploaded successfully</strong><br/>
          File ID: <code>{{ uploadResult.file_id }}</code><br/>
          Size: {{ uploadResult.bytes }} bytes · Status: {{ uploadResult.status }}
          <br/><br/>
          <button class="btn btn-sm btn-primary" @click="startJob(uploadResult.file_id)">Start Fine-Tuning Job →</button>
        </div>
      </div>
    </div>

    <!-- Create Job -->
    <div v-if="activeTab === 'create-job'" class="section-card">
      <h2 class="section-title">Create Fine-Tuning Job</h2>
      <div class="form-col">
        <div class="form-group">
          <label class="label">Training File ID</label>
          <input v-model="jobForm.file_id" class="input" placeholder="file-abc123... (from upload step)" />
        </div>
        <div class="form-group">
          <label class="label">Base Model</label>
          <select v-model="jobForm.base_model" class="select">
            <option value="gpt-4o-mini">gpt-4o-mini (recommended, fastest)</option>
            <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
            <option value="gpt-4o-mini-2024-07-18">gpt-4o-mini-2024-07-18</option>
          </select>
        </div>
        <div class="form-group">
          <label class="label">Training Epochs</label>
          <input v-model.number="jobForm.n_epochs" class="input" type="number" min="1" max="10" />
          <span class="hint">1–10. More epochs = better fit but risk of overfitting. Start with 3.</span>
        </div>
        <div class="form-group">
          <label class="label">Model Suffix (optional)</label>
          <input v-model="jobForm.suffix" class="input" placeholder="e.g. my-domain-expert" maxlength="18" />
          <span class="hint">Added to the model name. Max 18 characters.</span>
        </div>
        <button class="btn btn-primary" @click="createJob" :disabled="creatingJob">
          {{ creatingJob ? 'Starting…' : 'Start Fine-Tuning Job' }}
        </button>
        <div v-if="jobResult" class="result-box success">
          <strong>✓ Job started</strong><br/>
          Job ID: <code>{{ jobResult.job_id }}</code><br/>
          Base Model: {{ jobResult.model }} · Status: <span :class="statusClass(jobResult.status)">{{ jobResult.status }}</span>
        </div>
      </div>
    </div>

    <!-- Jobs List -->
    <div v-if="activeTab === 'jobs'" class="section-card">
      <div class="jobs-header">
        <h2 class="section-title" style="margin:0">Fine-Tuning Jobs</h2>
        <button class="btn btn-ghost btn-sm" @click="loadJobs">↻ Refresh</button>
      </div>
      <div v-if="loadingJobs" class="loading-text">Loading jobs…</div>
      <div v-else-if="jobs.length === 0" class="empty-state">
        <div class="empty-icon">🎯</div>
        <h3>No fine-tuning jobs yet</h3>
        <p>Upload a dataset and create a job to start personalizing your model.</p>
      </div>
      <div v-else class="jobs-list">
        <div v-for="job in jobs" :key="job.job_id" class="job-card" @click="selectJob(job)">
          <div class="job-header">
            <code class="job-id">{{ job.job_id }}</code>
            <span :class="['status-badge', statusClass(job.status)]">{{ job.status }}</span>
          </div>
          <div class="job-meta">
            <span>Base: {{ job.model }}</span>
            <span v-if="job.trained_tokens">Tokens: {{ job.trained_tokens?.toLocaleString() }}</span>
            <span>Created: {{ formatDate(job.created_at) }}</span>
          </div>
          <div v-if="job.fine_tuned_model" class="fine-tuned-model">
            ✓ Fine-tuned model: <code>{{ job.fine_tuned_model }}</code>
          </div>
          <div class="job-actions">
            <button v-if="job.status === 'running' || job.status === 'queued'" class="btn btn-sm btn-ghost danger" @click.stop="cancelJob(job.job_id)">Cancel</button>
            <button class="btn btn-sm btn-ghost" @click.stop="selectJob(job)">View Details</button>
          </div>
        </div>
      </div>

      <!-- Job detail -->
      <div v-if="selectedJob" class="job-detail">
        <div class="detail-header">
          <h3>Job Details: {{ selectedJob.job_id }}</h3>
          <button class="btn btn-sm btn-ghost" @click="selectedJob = null">✕</button>
        </div>
        <div class="detail-grid">
          <div><span class="dl">Status</span><span :class="['dv', statusClass(selectedJob.status)]">{{ selectedJob.status }}</span></div>
          <div><span class="dl">Base Model</span><span class="dv">{{ selectedJob.model }}</span></div>
          <div><span class="dl">Fine-Tuned Model</span><span class="dv">{{ selectedJob.fine_tuned_model || '—' }}</span></div>
          <div><span class="dl">Tokens Trained</span><span class="dv">{{ selectedJob.trained_tokens?.toLocaleString() || '—' }}</span></div>
          <div><span class="dl">Created</span><span class="dv">{{ formatDate(selectedJob.created_at) }}</span></div>
          <div><span class="dl">Finished</span><span class="dv">{{ formatDate(selectedJob.finished_at) || '—' }}</span></div>
        </div>
        <div v-if="selectedJob.recent_events?.length" class="events">
          <h4>Recent Events</h4>
          <div v-for="e in selectedJob.recent_events" :key="e.created_at" class="event-item" :class="e.level">
            <span class="event-level">{{ e.level }}</span>
            <span class="event-msg">{{ e.message }}</span>
          </div>
        </div>
        <div v-if="selectedJob.fine_tuned_model" class="usage-example">
          <h4>Using Your Fine-Tuned Model</h4>
          <pre class="code-block">import openai
client = openai.OpenAI()
response = client.chat.completions.create(
    model="{{ selectedJob.fine_tuned_model }}",
    messages=[{"role": "user", "content": "Your prompt here"}]
)</pre>
        </div>
      </div>
    </div>

    <!-- Models -->
    <div v-if="activeTab === 'models'" class="section-card">
      <div class="jobs-header">
        <h2 class="section-title" style="margin:0">Fine-Tuned Models</h2>
        <button class="btn btn-ghost btn-sm" @click="loadModels">↻ Refresh</button>
      </div>
      <div v-if="loadingModels" class="loading-text">Loading models…</div>
      <div v-else-if="models.length === 0" class="empty-state">
        <div class="empty-icon">🤖</div>
        <h3>No fine-tuned models yet</h3>
        <p>Complete a fine-tuning job to see your custom models here.</p>
      </div>
      <div v-else class="models-list">
        <div v-for="m in models" :key="m.id" class="model-card">
          <code class="model-id">{{ m.id }}</code>
          <span class="model-meta">Owned by: {{ m.owned_by }}</span>
          <button class="btn btn-sm btn-ghost" @click="copyToClipboard(m.id)">Copy ID</button>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const tabs = [
  { id: 'upload', label: '1. Upload Dataset' },
  { id: 'create-job', label: '2. Create Job' },
  { id: 'jobs', label: 'Jobs' },
  { id: 'models', label: 'Fine-Tuned Models' },
]
const activeTab = ref('upload')
const error = ref('')
const uploading = ref(false)
const creatingJob = ref(false)
const loadingJobs = ref(false)
const loadingModels = ref(false)
const upload = ref({ filename: 'training_data.jsonl', training_data: '' })
const uploadResult = ref(null)
const jobForm = ref({ file_id: '', base_model: 'gpt-4o-mini', n_epochs: 3, suffix: '' })
const jobResult = ref(null)
const jobs = ref([])
const models = ref([])
const selectedJob = ref(null)

async function api(path, opts = {}) {
  const res = await fetch(path, opts)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'API error')
  return data
}

async function loadExample() {
  try {
    const data = await api('/api/fine-tuning/example-data')
    upload.value.training_data = data.example_jsonl || ''
  } catch (e) { error.value = e.message }
}

async function uploadDataset() {
  if (!upload.value.training_data.trim()) return
  uploading.value = true; error.value = ''; uploadResult.value = null
  try {
    const data = await api('/api/fine-tuning/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(upload.value),
    })
    uploadResult.value = data
  } catch (e) { error.value = e.message } finally { uploading.value = false }
}

function startJob(fileId) {
  jobForm.value.file_id = fileId
  activeTab.value = 'create-job'
}

async function createJob() {
  if (!jobForm.value.file_id) return
  creatingJob.value = true; error.value = ''; jobResult.value = null
  try {
    const data = await api('/api/fine-tuning/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(jobForm.value),
    })
    jobResult.value = data
    await loadJobs()
  } catch (e) { error.value = e.message } finally { creatingJob.value = false }
}

async function loadJobs() {
  loadingJobs.value = true; error.value = ''
  try {
    const data = await api('/api/fine-tuning/jobs?limit=20')
    jobs.value = data.jobs || []
  } catch (e) { error.value = e.message } finally { loadingJobs.value = false }
}

async function loadModels() {
  loadingModels.value = true
  try {
    const data = await api('/api/fine-tuning/models')
    models.value = data.fine_tuned_models || []
  } catch (e) { error.value = e.message } finally { loadingModels.value = false }
}

async function cancelJob(jobId) {
  try {
    await api(`/api/fine-tuning/jobs/${jobId}`, { method: 'DELETE' })
    await loadJobs()
  } catch (e) { error.value = e.message }
}

async function selectJob(job) {
  try {
    const data = await api(`/api/fine-tuning/jobs/${job.job_id}`)
    selectedJob.value = data
  } catch { selectedJob.value = job }
}

function statusClass(status) {
  return { 'status-running': status === 'running', 'status-done': status === 'succeeded', 'status-failed': status === 'failed', 'status-queued': status === 'queued' || status === 'validating_files', 'status-cancelled': status === 'cancelled' }
}

function formatDate(ts) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString()
}

function copyToClipboard(text) { navigator.clipboard.writeText(text).catch(() => {}) }

onMounted(() => { loadJobs(); loadModels() })
</script>

<style scoped>
.finetune-view { max-width: 960px; margin: 0 auto; padding: 32px 24px; font-family: 'Inter', sans-serif; }
.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; }
.header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(90deg, #aaffcd, #99eaf9, #a0c4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 6px; }
.subtitle { color: #8e8e8e; margin: 0; font-size: 14px; }
.tabs { display: flex; gap: 4px; background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 10px; padding: 5px; margin-bottom: 20px; }
.tab { flex: 1; padding: 9px; border-radius: 7px; border: none; cursor: pointer; font-size: 13px; background: transparent; color: #8e8e8e; transition: all 0.2s; }
.tab.active { background: #2d2d2d; color: #f0f0f0; }
.section-card { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
.section-title { font-size: 16px; font-weight: 600; color: #f0f0f0; margin: 0 0 8px; }
.section-desc { font-size: 13px; color: #8e8e8e; margin: 0 0 16px; line-height: 1.6; }
.section-desc code { background: #0f0f0f; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #99eaf9; }
.example-banner { background: #0a1a2a; border: 1px solid #1e3a5f; border-radius: 8px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; margin-bottom: 16px; font-size: 13px; color: #99eaf9; }
.example-banner:hover { border-color: #99eaf9; }
.form-col { display: flex; flex-direction: column; gap: 14px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 12px; font-weight: 500; color: #8e8e8e; }
.hint { font-size: 11px; color: #666; }
.input { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; font-family: inherit; }
.input:focus { outline: none; border-color: #aaffcd; }
.select { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; width: 100%; }
.textarea { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; resize: vertical; }
.textarea.mono { font-family: 'Courier New', monospace; font-size: 12px; }
.line-count { font-size: 11px; color: #666; }
.btn { padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity 0.2s; white-space: nowrap; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: linear-gradient(135deg, #aaffcd, #99eaf9); color: #0f0f0f; }
.btn-ghost { background: #1f1f1f; border: 1px solid #2d2d2d; color: #c0c0c0; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.result-box { padding: 14px 16px; border-radius: 8px; font-size: 13px; line-height: 1.7; }
.result-box.success { background: #0d2d1a; border: 1px solid #1f6b3a; color: #d0ffd0; }
.result-box code { background: #0a2d1a; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
.jobs-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.jobs-list { display: flex; flex-direction: column; gap: 10px; }
.job-card { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 10px; padding: 14px 16px; cursor: pointer; transition: border-color 0.2s; }
.job-card:hover { border-color: #3d3d3d; }
.job-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.job-id { font-size: 12px; color: #99eaf9; }
.job-meta { display: flex; gap: 16px; font-size: 12px; color: #8e8e8e; margin-bottom: 8px; flex-wrap: wrap; }
.fine-tuned-model { font-size: 12px; color: #aaffcd; margin-bottom: 8px; }
.fine-tuned-model code { font-size: 11px; }
.job-actions { display: flex; gap: 8px; }
.status-badge { padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.status-running { background: #0a1f2a; color: #99eaf9; }
.status-done { background: #0d2d1a; color: #aaffcd; }
.status-failed { background: #2d0f0f; color: #ff9999; }
.status-queued { background: #1f1a0a; color: #ffcc88; }
.status-cancelled { background: #1a1a1a; color: #666; }
.job-detail { margin-top: 20px; background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 10px; padding: 20px; }
.detail-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.detail-header h3 { margin: 0; font-size: 14px; color: #f0f0f0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }
.detail-grid > div { display: flex; flex-direction: column; gap: 3px; }
.dl { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
.dv { font-size: 13px; color: #e0e0e0; }
.events { margin-bottom: 16px; }
.events h4 { font-size: 13px; color: #c0c0c0; margin: 0 0 10px; }
.event-item { display: flex; gap: 12px; padding: 7px 10px; border-radius: 6px; margin-bottom: 4px; background: #0a0a0a; font-size: 12px; }
.event-item.error { background: #1a0f0f; }
.event-level { font-weight: 600; text-transform: uppercase; font-size: 10px; min-width: 45px; color: #8e8e8e; }
.event-msg { color: #d0d0d0; flex: 1; }
.usage-example h4 { font-size: 13px; color: #c0c0c0; margin: 0 0 10px; }
.code-block { background: #0a0a0a; border: 1px solid #1f1f1f; border-radius: 8px; padding: 14px 16px; font-size: 12px; color: #e0e0e0; font-family: 'Courier New', monospace; overflow: auto; white-space: pre; margin: 0; }
.models-list { display: flex; flex-direction: column; gap: 8px; }
.model-card { display: flex; align-items: center; gap: 14px; background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 12px 16px; }
.model-id { font-size: 12px; color: #99eaf9; flex: 1; word-break: break-all; }
.model-meta { font-size: 11px; color: #666; white-space: nowrap; }
.btn-ghost.danger { border-color: #6b1f1f; color: #ff9999; }
.empty-state { text-align: center; padding: 40px 24px; }
.empty-icon { font-size: 40px; margin-bottom: 12px; }
.empty-state h3 { color: #f0f0f0; font-size: 16px; margin: 0 0 8px; }
.empty-state p { color: #8e8e8e; font-size: 13px; margin: 0; }
.loading-text { color: #8e8e8e; font-size: 13px; padding: 16px 0; }
.error-banner { background: #2d0f0f; border: 1px solid #6b1f1f; color: #ff9999; padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-top: 16px; }
</style>
