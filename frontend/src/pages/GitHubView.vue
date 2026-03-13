<template>
  <div class="github-view">
    <div class="header">
      <div>
        <h1>GitHub Copilot Synergy</h1>
        <p class="subtitle">Browse repositories, search code, analyze codebases, and create PRs — all from your agent workflows</p>
      </div>
    </div>

    <!-- Repo Search -->
    <div class="section-card">
      <h2 class="section-title">Repository Explorer</h2>
      <div class="input-row">
        <input v-model="username" placeholder="GitHub username or org" class="input" @keyup.enter="fetchRepos" />
        <button class="btn btn-primary" @click="fetchRepos" :disabled="loadingRepos">
          {{ loadingRepos ? 'Loading…' : 'Load Repos' }}
        </button>
      </div>
      <div v-if="repos.length" class="repo-grid">
        <div
          v-for="repo in repos" :key="repo.full_name"
          class="repo-card"
          :class="{ active: selectedRepo === repo.full_name }"
          @click="selectRepo(repo.full_name)"
        >
          <div class="repo-name">{{ repo.name }}</div>
          <div class="repo-desc">{{ repo.description || 'No description' }}</div>
          <div class="repo-meta">
            <span class="lang-badge" v-if="repo.language">{{ repo.language }}</span>
            <span>⭐ {{ repo.stars }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- File Browser -->
    <div v-if="selectedRepo" class="section-card">
      <h2 class="section-title">📁 {{ selectedRepo }}</h2>
      <div class="breadcrumb">
        <span @click="navigateTo('')" class="crumb crumb-link">root</span>
        <template v-for="(part, i) in pathParts" :key="i">
          <span class="crumb-sep">/</span>
          <span @click="navigateTo(pathParts.slice(0,i+1).join('/'))" class="crumb crumb-link">{{ part }}</span>
        </template>
      </div>
      <div v-if="loadingFiles" class="loading-text">Loading files…</div>
      <div v-else class="file-list">
        <div
          v-for="file in files" :key="file.path"
          class="file-item"
          @click="file.type === 'dir' ? navigateTo(file.path) : readFile(file.path)"
        >
          <span class="file-icon">{{ file.type === 'dir' ? '📂' : '📄' }}</span>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size" v-if="file.size">{{ formatSize(file.size) }}</span>
        </div>
      </div>
    </div>

    <!-- File Content Viewer -->
    <div v-if="fileContent" class="section-card">
      <div class="file-header">
        <h3>{{ viewingFile }}</h3>
        <div class="file-actions">
          <button class="btn btn-sm btn-ghost" @click="copyToClipboard(fileContent.content)">Copy</button>
          <button class="btn btn-sm btn-primary" @click="analyzeFileWithAI">Analyze with AI</button>
          <button class="btn btn-sm btn-ghost" @click="fileContent = null">✕</button>
        </div>
      </div>
      <pre class="code-block"><code>{{ fileContent.content }}</code></pre>
      <div v-if="aiAnalysis" class="ai-result">
        <h4>AI Analysis</h4>
        <div class="ai-text">{{ aiAnalysis }}</div>
      </div>
    </div>

    <!-- Recent Commits -->
    <div v-if="commits.length" class="section-card">
      <h2 class="section-title">Recent Commits</h2>
      <div class="commit-list">
        <div v-for="c in commits" :key="c.sha" class="commit-item">
          <span class="commit-sha">{{ c.sha }}</span>
          <span class="commit-msg">{{ c.message }}</span>
          <span class="commit-author">{{ c.author }}</span>
          <span class="commit-date">{{ formatDate(c.date) }}</span>
        </div>
      </div>
    </div>

    <!-- Panels Row: Search + Create -->
    <div class="two-col">
      <!-- Code Search -->
      <div class="section-card">
        <h2 class="section-title">Code Search</h2>
        <div class="input-col">
          <input v-model="searchQuery" placeholder="Search code, e.g. 'def authenticate'" class="input" @keyup.enter="searchCode" />
          <input v-model="searchRepo" placeholder="Limit to repo (optional)" class="input" />
          <button class="btn btn-primary" @click="searchCode" :disabled="loadingSearch">
            {{ loadingSearch ? 'Searching…' : 'Search GitHub' }}
          </button>
        </div>
        <div v-if="searchResults.length" class="search-results">
          <div v-for="r in searchResults" :key="r.url" class="search-result">
            <a :href="r.url" target="_blank" class="result-link">{{ r.repo }} / {{ r.path }}</a>
          </div>
          <div v-if="!searchResults.length && searchDone" class="no-results">No results found.</div>
        </div>
      </div>

      <!-- Create PR / Issue -->
      <div class="section-card">
        <h2 class="section-title">Create PR / Issue</h2>
        <div class="tabs">
          <button :class="['tab', {active: prTab === 'pr'}]" @click="prTab = 'pr'">Pull Request</button>
          <button :class="['tab', {active: prTab === 'issue'}]" @click="prTab = 'issue'">Issue</button>
        </div>

        <div v-if="prTab === 'pr'" class="input-col">
          <input v-model="prForm.repo" placeholder="owner/repo" class="input" />
          <input v-model="prForm.title" placeholder="PR title" class="input" />
          <input v-model="prForm.head" placeholder="head branch (source)" class="input" />
          <input v-model="prForm.base" placeholder="base branch (default: main)" class="input" />
          <textarea v-model="prForm.body" placeholder="PR description (Markdown supported)" class="textarea" rows="4"></textarea>
          <button class="btn btn-primary" @click="createPR" :disabled="creatingPR">
            {{ creatingPR ? 'Creating…' : 'Create Pull Request' }}
          </button>
          <div v-if="prResult" class="result-box success">
            PR #{{ prResult.pr_number }} created: <a :href="prResult.url" target="_blank">{{ prResult.url }}</a>
          </div>
        </div>

        <div v-if="prTab === 'issue'" class="input-col">
          <input v-model="issueForm.repo" placeholder="owner/repo" class="input" />
          <input v-model="issueForm.title" placeholder="Issue title" class="input" />
          <input v-model="issueForm.labels" placeholder="Labels (comma-separated)" class="input" />
          <textarea v-model="issueForm.body" placeholder="Issue description (Markdown supported)" class="textarea" rows="4"></textarea>
          <button class="btn btn-primary" @click="createIssue" :disabled="creatingIssue">
            {{ creatingIssue ? 'Creating…' : 'Create Issue' }}
          </button>
          <div v-if="issueResult" class="result-box success">
            Issue #{{ issueResult.issue_number }} created: <a :href="issueResult.url" target="_blank">{{ issueResult.url }}</a>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Repo Analyzer -->
    <div class="section-card">
      <h2 class="section-title">AI Repository Analyzer</h2>
      <div class="input-row">
        <input v-model="analyzeRepo" placeholder="owner/repo to analyze" class="input" />
        <input v-model="analyzeQuestion" placeholder="What do you want to know?" class="input" />
        <button class="btn btn-primary" @click="analyzeRepository" :disabled="analyzing">
          {{ analyzing ? 'Analyzing…' : 'Analyze' }}
        </button>
      </div>
      <div v-if="analyzeResult" class="ai-result">
        <h4>Repository: {{ analyzeRepo }}</h4>
        <div class="ai-text">{{ analyzeResult }}</div>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const username = ref('')
const repos = ref([])
const selectedRepo = ref('')
const currentPath = ref('')
const files = ref([])
const commits = ref([])
const fileContent = ref(null)
const viewingFile = ref('')
const aiAnalysis = ref('')
const loadingRepos = ref(false)
const loadingFiles = ref(false)
const error = ref('')

const searchQuery = ref('')
const searchRepo = ref('')
const searchResults = ref([])
const loadingSearch = ref(false)
const searchDone = ref(false)

const prTab = ref('pr')
const prForm = ref({ repo: '', title: '', head: '', base: 'main', body: '' })
const issueForm = ref({ repo: '', title: '', labels: '', body: '' })
const prResult = ref(null)
const issueResult = ref(null)
const creatingPR = ref(false)
const creatingIssue = ref(false)

const analyzeRepo = ref('')
const analyzeQuestion = ref('Summarize the architecture and main components.')
const analyzeResult = ref('')
const analyzing = ref(false)

const pathParts = computed(() => currentPath.value ? currentPath.value.split('/') : [])

async function api(path, opts = {}) {
  const res = await fetch(path, opts)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'API error')
  return data
}

async function fetchRepos() {
  if (!username.value) return
  loadingRepos.value = true
  error.value = ''
  try {
    const data = await api(`/api/github/repos/${username.value}`)
    repos.value = Array.isArray(data.repos) ? data.repos : []
  } catch (e) { error.value = e.message } finally { loadingRepos.value = false }
}

async function selectRepo(fullName) {
  selectedRepo.value = fullName
  currentPath.value = ''
  fileContent.value = null
  aiAnalysis.value = ''
  await loadFiles('')
  await loadCommits()
  prForm.value.repo = fullName
  issueForm.value.repo = fullName
  analyzeRepo.value = fullName
}

async function loadFiles(path) {
  loadingFiles.value = true
  error.value = ''
  const [owner, repo] = selectedRepo.value.split('/')
  try {
    const data = await api(`/api/github/files/${owner}/${repo}?path=${encodeURIComponent(path)}`)
    files.value = Array.isArray(data.files) ? data.files : []
  } catch (e) { error.value = e.message } finally { loadingFiles.value = false }
}

async function loadCommits() {
  const [owner, repo] = selectedRepo.value.split('/')
  try {
    const data = await api(`/api/github/commits/${owner}/${repo}`)
    commits.value = Array.isArray(data.commits) ? data.commits : []
  } catch (e) { /* non-critical */ }
}

function navigateTo(path) {
  currentPath.value = path
  fileContent.value = null
  aiAnalysis.value = ''
  loadFiles(path)
}

async function readFile(path) {
  viewingFile.value = path
  aiAnalysis.value = ''
  const [owner, repo] = selectedRepo.value.split('/')
  try {
    const data = await api(`/api/github/file/${owner}/${repo}?path=${encodeURIComponent(path)}`)
    fileContent.value = data.file
  } catch (e) { error.value = e.message }
}

async function analyzeFileWithAI() {
  if (!fileContent.value) return
  aiAnalysis.value = 'Analyzing…'
  try {
    const data = await api('/api/github/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo: selectedRepo.value, question: `Explain what this file does:\n${fileContent.value.content?.slice(0, 3000)}` }),
    })
    aiAnalysis.value = data.answer
  } catch (e) { aiAnalysis.value = e.message }
}

async function searchCode() {
  if (!searchQuery.value) return
  loadingSearch.value = true
  searchDone.value = false
  error.value = ''
  try {
    const data = await api('/api/github/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: searchQuery.value, repo: searchRepo.value }),
    })
    const r = data.results
    searchResults.value = Array.isArray(r?.results) ? r.results : []
    searchDone.value = true
  } catch (e) { error.value = e.message } finally { loadingSearch.value = false }
}

async function createPR() {
  creatingPR.value = true
  prResult.value = null
  try {
    const data = await api('/api/github/pull-request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prForm.value),
    })
    prResult.value = data.pr
  } catch (e) { error.value = e.message } finally { creatingPR.value = false }
}

async function createIssue() {
  creatingIssue.value = true
  issueResult.value = null
  try {
    const data = await api('/api/github/issue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(issueForm.value),
    })
    issueResult.value = data.issue
  } catch (e) { error.value = e.message } finally { creatingIssue.value = false }
}

async function analyzeRepository() {
  if (!analyzeRepo.value) return
  analyzing.value = true
  analyzeResult.value = ''
  try {
    const data = await api('/api/github/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo: analyzeRepo.value, question: analyzeQuestion.value }),
    })
    analyzeResult.value = data.answer
  } catch (e) { analyzeResult.value = e.message } finally { analyzing.value = false }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).catch(() => {})
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes/1024).toFixed(1)}KB`
  return `${(bytes/1024/1024).toFixed(1)}MB`
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString()
}
</script>

<style scoped>
.github-view { max-width: 1200px; margin: 0 auto; padding: 32px 24px; font-family: 'Inter', sans-serif; }
.header { margin-bottom: 28px; }
.header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(90deg, #aaffcd, #99eaf9, #a0c4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 6px; }
.subtitle { color: #8e8e8e; margin: 0; font-size: 14px; }
.section-card { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
.section-title { font-size: 16px; font-weight: 600; color: #f0f0f0; margin: 0 0 16px; }
.input-row { display: flex; gap: 10px; align-items: center; }
.input-col { display: flex; flex-direction: column; gap: 10px; }
.input { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; font-family: inherit; flex: 1; min-width: 0; }
.input:focus { outline: none; border-color: #aaffcd; }
.textarea { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; font-family: inherit; resize: vertical; }
.btn { padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; white-space: nowrap; transition: opacity 0.2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: linear-gradient(135deg, #aaffcd, #99eaf9); color: #0f0f0f; }
.btn-ghost { background: #1f1f1f; border: 1px solid #2d2d2d; color: #c0c0c0; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.repo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap: 12px; margin-top: 16px; }
.repo-card { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 14px; cursor: pointer; transition: border-color 0.2s; }
.repo-card:hover { border-color: #aaffcd66; }
.repo-card.active { border-color: #aaffcd; }
.repo-name { font-weight: 600; font-size: 13px; color: #f0f0f0; margin-bottom: 4px; }
.repo-desc { font-size: 12px; color: #8e8e8e; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.repo-meta { display: flex; gap: 10px; align-items: center; font-size: 12px; color: #8e8e8e; }
.lang-badge { background: #1f2937; color: #93c5fd; padding: 2px 7px; border-radius: 4px; }
.breadcrumb { display: flex; align-items: center; gap: 4px; font-size: 13px; color: #8e8e8e; margin-bottom: 12px; flex-wrap: wrap; }
.crumb-link { cursor: pointer; color: #99eaf9; }
.crumb-link:hover { text-decoration: underline; }
.crumb-sep { color: #444; }
.file-list { display: flex; flex-direction: column; gap: 2px; }
.file-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.file-item:hover { background: #0f0f0f; }
.file-icon { font-size: 15px; }
.file-name { flex: 1; color: #e0e0e0; }
.file-size { color: #666; font-size: 11px; }
.file-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.file-header h3 { margin: 0; font-size: 14px; color: #99eaf9; font-family: monospace; }
.file-actions { display: flex; gap: 8px; }
.code-block { background: #0a0a0a; border: 1px solid #1f1f1f; border-radius: 8px; padding: 16px; overflow: auto; max-height: 400px; font-size: 12px; color: #e0e0e0; font-family: 'Courier New', monospace; white-space: pre; }
.commit-list { display: flex; flex-direction: column; gap: 6px; }
.commit-item { display: grid; grid-template-columns: 80px 1fr 120px 100px; gap: 12px; align-items: center; padding: 8px 10px; background: #0f0f0f; border-radius: 6px; font-size: 12px; }
.commit-sha { font-family: monospace; color: #99eaf9; }
.commit-msg { color: #e0e0e0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.commit-author { color: #8e8e8e; }
.commit-date { color: #666; text-align: right; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } }
.tabs { display: flex; gap: 2px; background: #0f0f0f; border-radius: 8px; padding: 4px; margin-bottom: 16px; }
.tab { flex: 1; padding: 7px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; background: transparent; color: #8e8e8e; transition: all 0.2s; }
.tab.active { background: #1f1f1f; color: #f0f0f0; }
.search-results { margin-top: 12px; display: flex; flex-direction: column; gap: 4px; }
.search-result { padding: 8px 10px; background: #0f0f0f; border-radius: 6px; font-size: 12px; }
.result-link { color: #99eaf9; text-decoration: none; word-break: break-all; }
.result-link:hover { text-decoration: underline; }
.no-results { color: #666; font-size: 13px; padding: 8px; }
.result-box { padding: 12px; border-radius: 8px; font-size: 13px; margin-top: 8px; }
.result-box.success { background: #0d2d1a; border: 1px solid #1f6b3a; color: #aaffcd; }
.result-box a { color: #99eaf9; }
.ai-result { margin-top: 16px; padding: 16px; background: #0a0f1a; border: 1px solid #1e3a5f; border-radius: 8px; }
.ai-result h4 { margin: 0 0 10px; font-size: 13px; color: #99eaf9; }
.ai-text { font-size: 13px; color: #d0d0d0; white-space: pre-wrap; line-height: 1.6; }
.loading-text { color: #8e8e8e; font-size: 13px; padding: 16px 0; }
.error-banner { background: #2d0f0f; border: 1px solid #6b1f1f; color: #ff9999; padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-top: 16px; }
</style>
