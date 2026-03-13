<template>
  <div class="marketplace-view">
    <div class="hero">
      <h1>Workflow Marketplace</h1>
      <p class="hero-sub">Discover, share, and install AI workflow templates. Browse community-built pipelines or publish your own.</p>
      <div class="hero-search">
        <input v-model="search" class="search-input" placeholder="Search workflows…" @keyup.enter="loadListings" />
        <button class="btn btn-primary" @click="loadListings">Search</button>
        <button class="btn btn-ghost" @click="showPublish = true">+ Publish</button>
      </div>
    </div>

    <!-- Category pills -->
    <div class="category-row">
      <button :class="['cat-pill', {active: selectedCategory === ''}]" @click="selectedCategory = ''; loadListings()">All</button>
      <button v-for="c in categories" :key="c.name" :class="['cat-pill', {active: selectedCategory === c.name}]" @click="selectedCategory = c.name; loadListings()">
        {{ catIcon(c.name) }} {{ capitalize(c.name) }} <span class="cat-count">{{ c.count }}</span>
      </button>
    </div>

    <!-- Featured section -->
    <div v-if="!search && !selectedCategory && featured.length" class="featured-section">
      <h2 class="section-heading">⭐ Featured</h2>
      <div class="featured-grid">
        <div v-for="l in featured" :key="l.id" class="featured-card" @click="openListing(l)">
          <div class="card-cat-badge">{{ catIcon(l.category) }} {{ capitalize(l.category) }}</div>
          <div class="card-title">{{ l.name }}</div>
          <div class="card-desc">{{ l.description }}</div>
          <div class="card-footer">
            <div class="card-tags"><span v-for="t in l.tags.slice(0,3)" :key="t" class="tag">{{ t }}</span></div>
            <div class="card-stats">
              <span>⭐ {{ l.rating.toFixed(1) }}</span>
              <span>⬇ {{ l.downloads }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- All listings grid -->
    <div class="all-section">
      <h2 class="section-heading">{{ selectedCategory ? capitalize(selectedCategory) : search ? `Results for "${search}"` : 'All Workflows' }}</h2>
      <div v-if="loading" class="loading-text">Loading…</div>
      <div v-else-if="listings.length === 0" class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3>No workflows found</h3>
        <p>Try a different search or category, or publish your own workflow!</p>
      </div>
      <div v-else class="listings-grid">
        <div v-for="l in listings" :key="l.id" class="listing-card" @click="openListing(l)">
          <div class="lc-header">
            <div class="lc-cat">{{ catIcon(l.category) }}</div>
            <div class="lc-rating">⭐ {{ l.rating.toFixed(1) }}</div>
          </div>
          <div class="lc-name">{{ l.name }}</div>
          <div class="lc-desc">{{ l.description }}</div>
          <div class="lc-tags"><span v-for="t in l.tags.slice(0,3)" :key="t" class="tag">{{ t }}</span></div>
          <div class="lc-footer">
            <span class="author">by {{ l.author }}</span>
            <span>⬇ {{ l.downloads }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Listing Detail Modal -->
    <div v-if="selectedListing" class="modal-overlay" @click.self="selectedListing = null">
      <div class="modal">
        <div class="modal-header">
          <div>
            <div class="modal-cat">{{ catIcon(selectedListing.category) }} {{ capitalize(selectedListing.category) }}</div>
            <h2 class="modal-title">{{ selectedListing.name }}</h2>
            <div class="modal-meta">by {{ selectedListing.author }} · ⭐ {{ selectedListing.rating.toFixed(1) }} ({{ selectedListing.ratings_count }}) · ⬇ {{ selectedListing.downloads }}</div>
          </div>
          <button class="btn btn-ghost btn-sm close-btn" @click="selectedListing = null">✕</button>
        </div>
        <p class="modal-desc">{{ selectedListing.description }}</p>
        <div class="modal-tags"><span v-for="t in selectedListing.tags" :key="t" class="tag">{{ t }}</span></div>

        <div class="modal-actions">
          <button class="btn btn-primary" @click="downloadListing(selectedListing)" :disabled="downloading">
            {{ downloading ? 'Installing…' : '⬇ Install Workflow' }}
          </button>
          <div class="rate-section">
            <span class="rate-label">Rate this:</span>
            <button v-for="n in 5" :key="n" :class="['star-btn', {lit: n <= hoverStar || n <= myRating}]"
              @mouseover="hoverStar = n" @mouseleave="hoverStar = 0" @click="rateListingFn(selectedListing.id, n)">★</button>
          </div>
        </div>

        <div v-if="downloadSuccess" class="result-box success">
          ✓ {{ downloadSuccess }}
        </div>

        <div v-if="selectedListing.yaml_file" class="yaml-ref">
          <code>yaml_instance/{{ selectedListing.yaml_file }}</code>
        </div>
      </div>
    </div>

    <!-- Publish Modal -->
    <div v-if="showPublish" class="modal-overlay" @click.self="showPublish = false">
      <div class="modal">
        <div class="modal-header">
          <h2 class="modal-title">Publish Workflow</h2>
          <button class="btn btn-ghost btn-sm close-btn" @click="showPublish = false">✕</button>
        </div>
        <div class="form-col">
          <div class="form-group">
            <label class="label">Workflow Name</label>
            <input v-model="publishForm.name" class="input" placeholder="My Awesome Workflow" />
          </div>
          <div class="form-group">
            <label class="label">Description</label>
            <textarea v-model="publishForm.description" class="textarea" rows="3" placeholder="What does this workflow do?"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="label">Category</label>
              <select v-model="publishForm.category" class="select">
                <option value="development">Development</option>
                <option value="testing">Testing</option>
                <option value="devops">DevOps</option>
                <option value="blockchain">Blockchain</option>
                <option value="finance">Finance</option>
                <option value="travel">Travel</option>
                <option value="code-quality">Code Quality</option>
                <option value="research">Research</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div class="form-group">
              <label class="label">Your Name</label>
              <input v-model="publishForm.author" class="input" placeholder="Your name" />
            </div>
          </div>
          <div class="form-group">
            <label class="label">Tags (comma-separated)</label>
            <input v-model="publishForm.tags" class="input" placeholder="multi-agent, testing, python" />
          </div>
          <div class="form-group">
            <label class="label">YAML Content</label>
            <textarea v-model="publishForm.yaml_content" class="textarea mono" rows="12" placeholder="Paste your workflow YAML here…"></textarea>
          </div>
          <button class="btn btn-primary" @click="publishListing" :disabled="publishing">
            {{ publishing ? 'Publishing…' : 'Publish to Marketplace' }}
          </button>
          <div v-if="publishSuccess" class="result-box success">✓ {{ publishSuccess }}</div>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const search = ref('')
const selectedCategory = ref('')
const listings = ref([])
const featured = ref([])
const categories = ref([])
const loading = ref(false)
const error = ref('')
const selectedListing = ref(null)
const downloading = ref(false)
const downloadSuccess = ref('')
const hoverStar = ref(0)
const myRating = ref(0)
const showPublish = ref(false)
const publishing = ref(false)
const publishSuccess = ref('')
const publishForm = ref({ name: '', description: '', category: 'development', author: '', tags: '', yaml_content: '' })

async function api(path, opts = {}) {
  const res = await fetch(path, opts)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'API error')
  return data
}

async function loadListings() {
  loading.value = true; error.value = ''
  try {
    const params = new URLSearchParams()
    if (search.value) params.set('search', search.value)
    if (selectedCategory.value) params.set('category', selectedCategory.value)
    const data = await api(`/api/marketplace?${params}`)
    listings.value = data.listings || []
  } catch (e) { error.value = e.message } finally { loading.value = false }
}

async function loadFeatured() {
  try {
    const data = await api('/api/marketplace/featured')
    featured.value = data.listings || []
  } catch { /* non-critical */ }
}

async function loadCategories() {
  try {
    const data = await api('/api/marketplace/categories')
    categories.value = data.categories || []
  } catch { /* non-critical */ }
}

function openListing(l) {
  selectedListing.value = l
  downloadSuccess.value = ''
  myRating.value = 0
  hoverStar.value = 0
}

async function downloadListing(l) {
  downloading.value = true; downloadSuccess.value = ''
  try {
    const data = await api(`/api/marketplace/${l.id}/download`)
    const filename = data.yaml_file || `${l.id}.yaml`
    downloadSuccess.value = `Workflow "${l.name}" installed as ${filename} — now available in the Workflows page!`
    await loadListings()
  } catch (e) { error.value = e.message } finally { downloading.value = false }
}

async function rateListingFn(id, rating) {
  myRating.value = rating
  try {
    const data = await api(`/api/marketplace/${id}/rate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating }),
    })
    if (selectedListing.value) {
      selectedListing.value.rating = data.new_rating
      selectedListing.value.ratings_count = data.ratings_count
    }
  } catch (e) { error.value = e.message }
}

async function publishListing() {
  if (!publishForm.value.name || !publishForm.value.yaml_content) return
  publishing.value = true; publishSuccess.value = ''
  try {
    const data = await api('/api/marketplace/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(publishForm.value),
    })
    publishSuccess.value = `Published! Listing ID: ${data.listing_id}`
    publishForm.value = { name: '', description: '', category: 'development', author: '', tags: '', yaml_content: '' }
    await loadListings()
    await loadCategories()
  } catch (e) { error.value = e.message } finally { publishing.value = false }
}

const CAT_ICONS = { development: '💻', testing: '🧪', devops: '⚙️', blockchain: '⛓️', finance: '📈', travel: '✈️', 'code-quality': '🔍', research: '🔬', other: '📦' }
function catIcon(c) { return CAT_ICONS[c] || '📦' }
function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, ' ') : '' }

onMounted(async () => {
  await Promise.all([loadListings(), loadFeatured(), loadCategories()])
})
</script>

<style scoped>
.marketplace-view { max-width: 1200px; margin: 0 auto; padding: 32px 24px; font-family: 'Inter', sans-serif; }
.hero { text-align: center; padding: 40px 0 32px; }
.hero h1 { font-size: 36px; font-weight: 800; background: linear-gradient(90deg, #aaffcd, #99eaf9, #a0c4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 10px; }
.hero-sub { color: #8e8e8e; font-size: 15px; margin: 0 0 24px; }
.hero-search { display: flex; gap: 10px; max-width: 600px; margin: 0 auto; }
.search-input { flex: 1; background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 10px; padding: 11px 16px; color: #f0f0f0; font-size: 14px; font-family: inherit; }
.search-input:focus { outline: none; border-color: #aaffcd; }
.category-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 28px; }
.cat-pill { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 20px; padding: 6px 14px; font-size: 12px; color: #8e8e8e; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 6px; }
.cat-pill.active { border-color: #aaffcd55; background: #0d2d1a; color: #aaffcd; }
.cat-pill:hover:not(.active) { border-color: #3d3d3d; color: #c0c0c0; }
.cat-count { background: #2d2d2d; border-radius: 10px; padding: 1px 7px; font-size: 10px; }
.section-heading { font-size: 18px; font-weight: 600; color: #f0f0f0; margin: 0 0 16px; }
.featured-section { margin-bottom: 32px; }
.featured-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px,1fr)); gap: 14px; }
.featured-card { background: linear-gradient(135deg, #0d2d1a 0%, #0a1a2a 100%); border: 1px solid #1f4f3a; border-radius: 12px; padding: 20px; cursor: pointer; transition: transform 0.2s, border-color 0.2s; }
.featured-card:hover { transform: translateY(-2px); border-color: #2a7a5a; }
.card-cat-badge { font-size: 11px; color: #aaffcd; margin-bottom: 8px; }
.card-title { font-size: 15px; font-weight: 700; color: #f0f0f0; margin-bottom: 8px; }
.card-desc { font-size: 13px; color: #9e9e9e; margin-bottom: 12px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.card-footer { display: flex; justify-content: space-between; align-items: flex-end; }
.card-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.card-stats { display: flex; gap: 10px; font-size: 12px; color: #8e8e8e; white-space: nowrap; }
.listings-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px,1fr)); gap: 14px; }
.listing-card { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 18px; cursor: pointer; transition: all 0.2s; display: flex; flex-direction: column; gap: 8px; }
.listing-card:hover { border-color: #3d3d3d; transform: translateY(-1px); }
.lc-header { display: flex; justify-content: space-between; align-items: center; }
.lc-cat { font-size: 18px; }
.lc-rating { font-size: 12px; color: #ffcc88; }
.lc-name { font-size: 14px; font-weight: 600; color: #f0f0f0; }
.lc-desc { font-size: 12px; color: #8e8e8e; flex: 1; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.lc-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.lc-footer { display: flex; justify-content: space-between; font-size: 11px; color: #666; margin-top: auto; }
.author { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px; }
.tag { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 10px; padding: 2px 8px; font-size: 11px; color: #8e8e8e; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
.modal { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 16px; padding: 28px; max-width: 640px; width: 100%; max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.modal-cat { font-size: 12px; color: #8e8e8e; margin-bottom: 6px; }
.modal-title { font-size: 22px; font-weight: 700; color: #f0f0f0; margin: 0; }
.modal-meta { font-size: 12px; color: #8e8e8e; margin-top: 4px; }
.modal-desc { font-size: 14px; color: #c0c0c0; margin: 0 0 12px; line-height: 1.6; }
.modal-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 20px; }
.modal-actions { display: flex; align-items: center; gap: 20px; margin-bottom: 16px; flex-wrap: wrap; }
.rate-section { display: flex; align-items: center; gap: 6px; }
.rate-label { font-size: 12px; color: #8e8e8e; }
.star-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: #3d3d3d; transition: color 0.1s; }
.star-btn.lit { color: #ffcc88; }
.yaml-ref { margin-top: 12px; font-size: 12px; color: #666; }
.yaml-ref code { color: #99eaf9; }
.close-btn { font-size: 16px; }
.form-col { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 12px; font-weight: 500; color: #8e8e8e; }
.input { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; font-family: inherit; }
.input:focus { outline: none; border-color: #aaffcd; }
.select { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; width: 100%; }
.textarea { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; resize: vertical; font-family: inherit; }
.textarea.mono { font-family: 'Courier New', monospace; font-size: 12px; }
.btn { padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity 0.2s; white-space: nowrap; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: linear-gradient(135deg, #aaffcd, #99eaf9); color: #0f0f0f; }
.btn-ghost { background: #1f1f1f; border: 1px solid #2d2d2d; color: #c0c0c0; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.result-box { padding: 12px 16px; border-radius: 8px; font-size: 13px; }
.result-box.success { background: #0d2d1a; border: 1px solid #1f6b3a; color: #d0ffd0; }
.empty-state { text-align: center; padding: 60px 24px; }
.empty-icon { font-size: 40px; margin-bottom: 12px; }
.empty-state h3 { color: #f0f0f0; font-size: 16px; margin: 0 0 8px; }
.empty-state p { color: #8e8e8e; font-size: 13px; margin: 0; }
.loading-text { color: #8e8e8e; font-size: 13px; padding: 16px 0; }
.error-banner { background: #2d0f0f; border: 1px solid #6b1f1f; color: #ff9999; padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-top: 16px; }
</style>
