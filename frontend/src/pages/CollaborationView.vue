<template>
  <div class="collab-view">
    <div class="header">
      <div>
        <h1>Real-Time Collaboration</h1>
        <p class="subtitle">Create shared sessions for team prompting — like a VS Code Live Share for AI workflows</p>
      </div>
    </div>

    <!-- Room list / lobby -->
    <div v-if="!activeRoom" class="lobby">
      <div class="lobby-header">
        <h2>Collaboration Rooms</h2>
        <button class="btn btn-primary" @click="showCreateRoom = true">+ New Room</button>
      </div>

      <div v-if="showCreateRoom" class="create-room-form">
        <input v-model="newRoom.name" class="input" placeholder="Room name, e.g. 'Sprint Planning AI'" />
        <input v-model="newRoom.description" class="input" placeholder="Description (optional)" />
        <input v-model="newRoom.owner" class="input" placeholder="Your name" />
        <div class="form-row">
          <button class="btn btn-primary" @click="createRoom" :disabled="creatingRoom">
            {{ creatingRoom ? 'Creating…' : 'Create Room' }}
          </button>
          <button class="btn btn-ghost" @click="showCreateRoom = false; newRoom = { name: '', description: '', owner: '' }">Cancel</button>
        </div>
      </div>

      <div v-if="loadingRooms" class="loading-text">Loading rooms…</div>
      <div v-else-if="rooms.length === 0" class="empty-state">
        <div class="empty-icon">🤝</div>
        <h3>No rooms yet</h3>
        <p>Create a room to start collaborating with your team on AI prompts and workflows.</p>
      </div>
      <div class="rooms-grid" v-else>
        <div v-for="room in rooms" :key="room.room_id" class="room-card">
          <div class="room-info">
            <div class="room-name">{{ room.name }}</div>
            <div class="room-desc">{{ room.description }}</div>
            <div class="room-meta">
              <span class="meta-pill">👤 {{ room.owner }}</span>
              <span class="meta-pill" :class="{ active: room.user_count > 0 }">
                {{ room.user_count }} online
              </span>
              <span class="meta-pill">{{ room.history_length }} messages</span>
            </div>
          </div>
          <div class="room-actions">
            <input v-model="joinName" class="input-sm" placeholder="Your name" />
            <button class="btn btn-primary btn-sm" @click="joinRoom(room)">Join</button>
            <button class="btn btn-ghost btn-sm danger" @click="deleteRoom(room.room_id)">✕</button>
          </div>
        </div>
      </div>

      <button class="btn btn-ghost refresh-btn" @click="loadRooms">↻ Refresh</button>
    </div>

    <!-- Active room session -->
    <div v-else class="session">
      <div class="session-header">
        <div class="session-info">
          <h2>{{ activeRoom.name }}</h2>
          <span class="room-id-badge">Room: {{ activeRoom.room_id }}</span>
        </div>
        <div class="session-actions">
          <div class="users-indicator">
            <span v-for="u in activeUsers" :key="u" class="user-avatar" :title="u">{{ u[0].toUpperCase() }}</span>
          </div>
          <button class="btn btn-ghost btn-sm" @click="leaveRoom">Leave</button>
        </div>
      </div>

      <div class="session-body">
        <!-- Shared prompt editor -->
        <div class="prompt-panel">
          <div class="panel-header">
            <h3>Shared Prompt</h3>
            <span class="editing-indicator" v-if="someoneEditing">✏️ {{ editingUser }} is editing…</span>
          </div>
          <textarea
            v-model="sharedPrompt"
            class="shared-textarea"
            placeholder="Type a shared AI prompt here. All collaborators see your changes in real-time…"
            @input="onPromptInput"
            rows="8"
          ></textarea>
          <div class="prompt-actions">
            <span class="char-count">{{ sharedPrompt.length }} chars</span>
            <button class="btn btn-ghost btn-sm" @click="copyToClipboard(sharedPrompt)">Copy Prompt</button>
            <a :href="`/launch?prompt=${encodeURIComponent(sharedPrompt)}`" target="_blank" class="btn btn-primary btn-sm">
              Launch in Workflow ↗
            </a>
          </div>
        </div>

        <!-- Chat -->
        <div class="chat-panel">
          <div class="panel-header">
            <h3>Team Chat</h3>
            <span class="ws-status" :class="wsStatus">{{ wsStatus }}</span>
          </div>
          <div class="messages" ref="messagesEl">
            <div v-for="(msg, i) in messages" :key="i" class="message" :class="{ mine: msg.user_id === myUserId, system: msg.type === 'user_joined' || msg.type === 'user_left' || msg.type === 'room_closed' }">
              <template v-if="msg.type === 'message'">
                <div class="msg-meta"><span class="msg-author">{{ msg.user_id }}</span><span class="msg-time">{{ formatTime(msg.timestamp) }}</span></div>
                <div class="msg-text">{{ msg.text }}</div>
              </template>
              <template v-else-if="msg.type === 'prompt_updated'">
                <div class="msg-system">✏️ {{ msg.user_id }} updated the shared prompt</div>
              </template>
              <template v-else>
                <div class="msg-system">{{ msg.user_id }} {{ msg.type === 'user_joined' ? 'joined' : 'left' }} the room</div>
              </template>
            </div>
          </div>
          <div class="chat-input">
            <input v-model="chatMessage" class="input" placeholder="Message teammates…" @keyup.enter="sendMessage" />
            <button class="btn btn-primary btn-sm" @click="sendMessage">Send</button>
          </div>
        </div>
      </div>

      <div v-if="wsError" class="error-banner">{{ wsError }}</div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'

const rooms = ref([])
const loadingRooms = ref(false)
const showCreateRoom = ref(false)
const creatingRoom = ref(false)
const newRoom = ref({ name: '', description: '', owner: '' })
const joinName = ref('')
const error = ref('')

const activeRoom = ref(null)
const myUserId = ref('')
const messages = ref([])
const sharedPrompt = ref('')
const chatMessage = ref('')
const activeUsers = ref([])
const someoneEditing = ref(false)
const editingUser = ref('')
const ws = ref(null)
const wsStatus = ref('disconnected')
const wsError = ref('')
const messagesEl = ref(null)
let promptDebounce = null
let editingTimeout = null

async function api(path, opts = {}) {
  const res = await fetch(path, opts)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'API error')
  return data
}

async function loadRooms() {
  loadingRooms.value = true
  error.value = ''
  try {
    const data = await api('/api/collab/rooms')
    rooms.value = data.rooms || []
  } catch (e) { error.value = e.message } finally { loadingRooms.value = false }
}

async function createRoom() {
  if (!newRoom.value.name) return
  creatingRoom.value = true
  try {
    await api('/api/collab/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newRoom.value),
    })
    showCreateRoom.value = false
    newRoom.value = { name: '', description: '', owner: '' }
    await loadRooms()
  } catch (e) { error.value = e.message } finally { creatingRoom.value = false }
}

async function deleteRoom(roomId) {
  try {
    await api(`/api/collab/rooms/${roomId}`, { method: 'DELETE' })
    await loadRooms()
  } catch (e) { error.value = e.message }
}

function joinRoom(room) {
  const name = joinName.value.trim() || `user-${Math.random().toString(36).slice(2, 7)}`
  myUserId.value = name
  activeRoom.value = room
  messages.value = []
  sharedPrompt.value = room.shared_prompt || ''
  activeUsers.value = []
  connectWS(room.room_id, name)
}

function leaveRoom() {
  if (ws.value) { ws.value.close(); ws.value = null }
  activeRoom.value = null
  messages.value = []
  wsStatus.value = 'disconnected'
  loadRooms()
}

function connectWS(roomId, userId) {
  wsStatus.value = 'connecting'
  wsError.value = ''
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${proto}//${location.host}/api/collab/rooms/${roomId}/ws?user_id=${encodeURIComponent(userId)}`
  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => { wsStatus.value = 'connected' }

  ws.value.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data)
      if (msg.type === 'welcome') {
        myUserId.value = msg.user_id
        activeUsers.value = msg.room?.active_users || []
        sharedPrompt.value = msg.room?.shared_prompt || ''
        const hist = msg.history || []
        messages.value = hist.filter(m => m.type === 'message' || m.type === 'user_joined' || m.type === 'user_left' || m.type === 'prompt_updated')
        scrollToBottom()
        return
      }
      if (msg.type === 'prompt_updated' && msg.user_id !== myUserId.value) {
        sharedPrompt.value = msg.prompt || sharedPrompt.value
        someoneEditing.value = true
        editingUser.value = msg.user_id
        clearTimeout(editingTimeout)
        editingTimeout = setTimeout(() => { someoneEditing.value = false }, 2000)
        messages.value.push(msg)
        scrollToBottom()
        return
      }
      if (msg.type === 'user_joined' || msg.type === 'user_left') {
        activeUsers.value = msg.active_users || activeUsers.value
        messages.value.push(msg)
        scrollToBottom()
        return
      }
      if (msg.type === 'message') {
        messages.value.push(msg)
        scrollToBottom()
      }
    } catch { /* ignore */ }
  }

  ws.value.onerror = () => { wsError.value = 'WebSocket error — retrying…' }
  ws.value.onclose = () => { wsStatus.value = 'disconnected' }
}

function onPromptInput() {
  clearTimeout(promptDebounce)
  promptDebounce = setTimeout(() => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: 'prompt_update', prompt: sharedPrompt.value }))
    }
  }, 400)
}

function sendMessage() {
  if (!chatMessage.value.trim() || !ws.value || ws.value.readyState !== WebSocket.OPEN) return
  ws.value.send(JSON.stringify({ type: 'message', text: chatMessage.value }))
  chatMessage.value = ''
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

function copyToClipboard(text) { navigator.clipboard.writeText(text).catch(() => {}) }

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

onMounted(loadRooms)
onUnmounted(() => { if (ws.value) ws.value.close() })
</script>

<style scoped>
.collab-view { max-width: 1200px; margin: 0 auto; padding: 32px 24px; font-family: 'Inter', sans-serif; }
.header { margin-bottom: 28px; }
.header h1 { font-size: 28px; font-weight: 700; background: linear-gradient(90deg, #aaffcd, #99eaf9, #a0c4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 6px; }
.subtitle { color: #8e8e8e; margin: 0; font-size: 14px; }
.lobby-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.lobby-header h2 { margin: 0; font-size: 18px; color: #f0f0f0; }
.create-room-form { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.form-row { display: flex; gap: 10px; }
.rooms-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px,1fr)); gap: 14px; }
.room-card { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.room-name { font-size: 15px; font-weight: 600; color: #f0f0f0; margin-bottom: 4px; }
.room-desc { font-size: 13px; color: #8e8e8e; margin-bottom: 8px; }
.room-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-pill { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 20px; padding: 3px 10px; font-size: 11px; color: #8e8e8e; }
.meta-pill.active { border-color: #aaffcd55; color: #aaffcd; }
.room-actions { display: flex; gap: 8px; align-items: center; }
.input-sm { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 6px; padding: 6px 10px; color: #f0f0f0; font-size: 12px; flex: 1; min-width: 0; }
.refresh-btn { margin-top: 16px; }
.session-header { display: flex; justify-content: space-between; align-items: center; background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; }
.session-info { display: flex; align-items: center; gap: 14px; }
.session-info h2 { margin: 0; font-size: 18px; color: #f0f0f0; }
.room-id-badge { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 6px; padding: 3px 10px; font-size: 11px; color: #8e8e8e; font-family: monospace; }
.session-actions { display: flex; align-items: center; gap: 14px; }
.users-indicator { display: flex; gap: 4px; }
.user-avatar { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #aaffcd, #99eaf9); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #0f0f0f; }
.session-body { display: grid; grid-template-columns: 1fr 360px; gap: 16px; }
@media (max-width: 900px) { .session-body { grid-template-columns: 1fr; } }
.prompt-panel, .chat-panel { background: #1a1a1a; border: 1px solid #2d2d2d; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid #2d2d2d; }
.panel-header h3 { margin: 0; font-size: 13px; font-weight: 600; color: #c0c0c0; }
.editing-indicator { font-size: 12px; color: #ffcc88; }
.shared-textarea { flex: 1; background: #0a0a0a; border: none; padding: 16px; color: #f0f0f0; font-size: 14px; font-family: inherit; resize: none; outline: none; line-height: 1.6; min-height: 200px; }
.prompt-actions { display: flex; align-items: center; gap: 10px; padding: 10px 16px; border-top: 1px solid #2d2d2d; }
.char-count { font-size: 11px; color: #666; flex: 1; }
.messages { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; min-height: 300px; max-height: 420px; }
.message { display: flex; flex-direction: column; gap: 3px; }
.message.mine .msg-text { background: #0d2d1a; border-color: #1f6b3a; }
.msg-meta { display: flex; align-items: center; gap: 8px; }
.msg-author { font-size: 11px; font-weight: 600; color: #99eaf9; }
.msg-time { font-size: 10px; color: #555; }
.msg-text { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 8px 12px; font-size: 13px; color: #e0e0e0; line-height: 1.5; }
.msg-system { font-size: 11px; color: #555; text-align: center; font-style: italic; padding: 4px 0; }
.chat-input { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid #2d2d2d; }
.ws-status { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 10px; }
.ws-status.connected { background: #0d2d1a; color: #aaffcd; }
.ws-status.connecting { background: #2d1f0a; color: #ffcc88; }
.ws-status.disconnected { background: #2d0f0f; color: #ff9999; }
.input { background: #0f0f0f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 9px 12px; color: #f0f0f0; font-size: 13px; font-family: inherit; flex: 1; }
.input:focus { outline: none; border-color: #aaffcd; }
.btn { padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity 0.2s; white-space: nowrap; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: linear-gradient(135deg, #aaffcd, #99eaf9); color: #0f0f0f; }
.btn-ghost { background: #1f1f1f; border: 1px solid #2d2d2d; color: #c0c0c0; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-ghost.danger { border-color: #6b1f1f; color: #ff9999; }
.empty-state { text-align: center; padding: 60px 24px; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state h3 { color: #f0f0f0; font-size: 18px; margin: 0 0 8px; }
.empty-state p { color: #8e8e8e; font-size: 14px; margin: 0; }
.loading-text { color: #8e8e8e; font-size: 13px; padding: 16px 0; }
.error-banner { background: #2d0f0f; border: 1px solid #6b1f1f; color: #ff9999; padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-top: 16px; }
</style>
