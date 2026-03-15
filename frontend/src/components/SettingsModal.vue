<template>
  <Transition name="modal-fade">
    <div v-if="isVisible" class="modal-overlay" @click.self="close">
      <div class="modal-content settings-modal">
        <div class="modal-header">
          <h3>Settings</h3>
          <button class="close-button" @click="close">&times;</button>
        </div>

        <!-- Tabs -->
        <div class="tabs-bar">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'general' }"
            @click="activeTab = 'general'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            General
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'integrations' }"
            @click="activeTab = 'integrations'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 7h3a5 5 0 0 1 0 10h-3m-6 0H6a5 5 0 0 1 0-10h3"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            Integrations
          </button>
        </div>

        <div class="modal-body">
          <!-- General Tab -->
          <div v-if="activeTab === 'general'">
            <div class="settings-item">
              <label class="checkbox-label">
                <input type="checkbox" v-model="localConfig.AUTO_SHOW_ADVANCED">
                Auto show advanced setting
              </label>
              <p class="setting-desc">Automatically expand "Advanced Settings" in configuration forms.</p>
            </div>
            <div class="settings-item">
              <label class="checkbox-label">
                <input type="checkbox" v-model="localConfig.AUTO_EXPAND_MESSAGES">
                Automatically expand messages
              </label>
              <p class="setting-desc">Automatically expand message content in the chat view.</p>
            </div>
            <div class="settings-item">
              <label class="checkbox-label">
                <input type="checkbox" v-model="localConfig.ENABLE_HELP_TOOLTIPS">
                Enable help tooltips
              </label>
              <p class="setting-desc">Show contextual help tooltips throughout the workflow interface.</p>
            </div>
          </div>

          <!-- Integrations Tab -->
          <div v-if="activeTab === 'integrations'">
            <p class="integrations-intro">Connect external services to unlock AI image generation, content creation, and more.</p>

            <!-- Adobe Firefly -->
            <div class="integration-card" :class="{ connected: integrations.adobe_firefly.connected }">
              <div class="integration-header">
                <div class="integration-icon firefly">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </div>
                <div class="integration-info">
                  <h4>Adobe Firefly</h4>
                  <p>AI image generation — create social media graphics, brand visuals, and more</p>
                </div>
                <span class="status-badge" :class="integrations.adobe_firefly.connected ? 'connected' : 'disconnected'">
                  {{ integrations.adobe_firefly.connected ? 'Connected' : 'Not connected' }}
                </span>
              </div>
              <div class="integration-body">
                <div class="input-group">
                  <label>API Key</label>
                  <div class="key-input-row">
                    <input
                      :type="integrations.adobe_firefly.showKey ? 'text' : 'password'"
                      v-model="integrations.adobe_firefly.apiKey"
                      placeholder="Enter your Adobe Firefly API key"
                      class="api-key-input"
                    />
                    <button class="toggle-vis" @click="integrations.adobe_firefly.showKey = !integrations.adobe_firefly.showKey">
                      {{ integrations.adobe_firefly.showKey ? 'Hide' : 'Show' }}
                    </button>
                  </div>
                  <p class="input-hint">Get your API key from <a href="https://developer.adobe.com/firefly-api/" target="_blank">developer.adobe.com/firefly-api</a></p>
                </div>
                <div class="integration-actions">
                  <button class="connect-btn" @click="saveIntegration('adobe_firefly', integrations.adobe_firefly)" :disabled="!integrations.adobe_firefly.apiKey">
                    {{ integrations.adobe_firefly.connected ? 'Update' : 'Connect' }}
                  </button>
                  <button v-if="integrations.adobe_firefly.connected" class="disconnect-btn" @click="removeIntegration('adobe_firefly')">
                    Disconnect
                  </button>
                </div>
              </div>
            </div>

            <!-- OpenAI DALL-E -->
            <div class="integration-card" :class="{ connected: integrations.openai_dalle.connected }">
              <div class="integration-header">
                <div class="integration-icon dalle">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/><circle cx="8.5" cy="8.5" r="1.5" fill="currentColor"/><path d="M21 15l-5-5L5 21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </div>
                <div class="integration-info">
                  <h4>OpenAI DALL-E</h4>
                  <p>Generate images with DALL-E 3</p>
                </div>
                <span class="status-badge" :class="integrations.openai_dalle.connected ? 'connected' : 'disconnected'">
                  {{ integrations.openai_dalle.connected ? 'Connected' : 'Not connected' }}
                </span>
              </div>
              <div class="integration-body">
                <div class="input-group">
                  <label>API Key</label>
                  <div class="key-input-row">
                    <input
                      :type="integrations.openai_dalle.showKey ? 'text' : 'password'"
                      v-model="integrations.openai_dalle.apiKey"
                      placeholder="Enter your OpenAI API key"
                      class="api-key-input"
                    />
                    <button class="toggle-vis" @click="integrations.openai_dalle.showKey = !integrations.openai_dalle.showKey">
                      {{ integrations.openai_dalle.showKey ? 'Hide' : 'Show' }}
                    </button>
                  </div>
                  <p class="input-hint">Get your key from <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com</a></p>
                </div>
                <div class="integration-actions">
                  <button class="connect-btn" @click="saveIntegration('openai_dalle', integrations.openai_dalle)" :disabled="!integrations.openai_dalle.apiKey">
                    {{ integrations.openai_dalle.connected ? 'Update' : 'Connect' }}
                  </button>
                  <button v-if="integrations.openai_dalle.connected" class="disconnect-btn" @click="removeIntegration('openai_dalle')">
                    Disconnect
                  </button>
                </div>
              </div>
            </div>

            <!-- Stability AI -->
            <div class="integration-card" :class="{ connected: integrations.stability_ai.connected }">
              <div class="integration-header">
                <div class="integration-icon stability">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6L5.6 18.4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                </div>
                <div class="integration-info">
                  <h4>Stability AI</h4>
                  <p>Stable Diffusion image generation</p>
                </div>
                <span class="status-badge" :class="integrations.stability_ai.connected ? 'connected' : 'disconnected'">
                  {{ integrations.stability_ai.connected ? 'Connected' : 'Not connected' }}
                </span>
              </div>
              <div class="integration-body">
                <div class="input-group">
                  <label>API Key</label>
                  <div class="key-input-row">
                    <input
                      :type="integrations.stability_ai.showKey ? 'text' : 'password'"
                      v-model="integrations.stability_ai.apiKey"
                      placeholder="Enter your Stability AI API key"
                      class="api-key-input"
                    />
                    <button class="toggle-vis" @click="integrations.stability_ai.showKey = !integrations.stability_ai.showKey">
                      {{ integrations.stability_ai.showKey ? 'Hide' : 'Show' }}
                    </button>
                  </div>
                  <p class="input-hint">Get your key from <a href="https://platform.stability.ai/" target="_blank">platform.stability.ai</a></p>
                </div>
                <div class="integration-actions">
                  <button class="connect-btn" @click="saveIntegration('stability_ai', integrations.stability_ai)" :disabled="!integrations.stability_ai.apiKey">
                    {{ integrations.stability_ai.connected ? 'Update' : 'Connect' }}
                  </button>
                  <button v-if="integrations.stability_ai.connected" class="disconnect-btn" @click="removeIntegration('stability_ai')">
                    Disconnect
                  </button>
                </div>
              </div>
            </div>

            <!-- Google Gemini -->
            <div class="integration-card" :class="{ connected: integrations.google_gemini.connected }">
              <div class="integration-header">
                <div class="integration-icon gemini">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </div>
                <div class="integration-info">
                  <h4>Google Gemini</h4>
                  <p>Gemini image generation and multimodal AI</p>
                </div>
                <span class="status-badge" :class="integrations.google_gemini.connected ? 'connected' : 'disconnected'">
                  {{ integrations.google_gemini.connected ? 'Connected' : 'Not connected' }}
                </span>
              </div>
              <div class="integration-body">
                <div class="input-group">
                  <label>API Key</label>
                  <div class="key-input-row">
                    <input
                      :type="integrations.google_gemini.showKey ? 'text' : 'password'"
                      v-model="integrations.google_gemini.apiKey"
                      placeholder="Enter your Google AI API key"
                      class="api-key-input"
                    />
                    <button class="toggle-vis" @click="integrations.google_gemini.showKey = !integrations.google_gemini.showKey">
                      {{ integrations.google_gemini.showKey ? 'Hide' : 'Show' }}
                    </button>
                  </div>
                  <p class="input-hint">Get your key from <a href="https://aistudio.google.com/apikey" target="_blank">aistudio.google.com</a></p>
                </div>
                <div class="integration-actions">
                  <button class="connect-btn" @click="saveIntegration('google_gemini', integrations.google_gemini)" :disabled="!integrations.google_gemini.apiKey">
                    {{ integrations.google_gemini.connected ? 'Update' : 'Connect' }}
                  </button>
                  <button v-if="integrations.google_gemini.connected" class="disconnect-btn" @click="removeIntegration('google_gemini')">
                    Disconnect
                  </button>
                </div>
              </div>
            </div>

            <div v-if="saveMessage" class="save-message" :class="saveMessageType">{{ saveMessage }}</div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="cancel-button" @click="close">{{ activeTab === 'general' ? 'Cancel' : 'Close' }}</button>
          <button v-if="activeTab === 'general'" class="confirm-button" @click="save">Save</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { configStore } from '../utils/configStore.js'
import { apiFetch } from '../utils/auth.js'

const props = defineProps({
  isVisible: { type: Boolean, required: true }
})

const activeTab = ref('general')
const saveMessage = ref('')
const saveMessageType = ref('success')

const localConfig = reactive({
  AUTO_SHOW_ADVANCED: false,
  AUTO_EXPAND_MESSAGES: false,
  ENABLE_HELP_TOOLTIPS: true
})

const integrations = reactive({
  adobe_firefly: { apiKey: '', connected: false, showKey: false },
  openai_dalle: { apiKey: '', connected: false, showKey: false },
  stability_ai: { apiKey: '', connected: false, showKey: false },
  google_gemini: { apiKey: '', connected: false, showKey: false },
})

watch(() => props.isVisible, async (newVal) => {
  if (newVal) {
    Object.assign(localConfig, configStore)
    await loadIntegrations()
  }
})

async function loadIntegrations() {
  try {
    const res = await apiFetch('/api/integrations')
    if (res.ok) {
      const data = await res.json()
      // Reset all
      for (const key of Object.keys(integrations)) {
        integrations[key].connected = false
        integrations[key].apiKey = ''
      }
      // Mark connected ones
      for (const item of data.integrations) {
        if (integrations[item.provider]) {
          integrations[item.provider].connected = true
          integrations[item.provider].apiKey = item.api_key_hint || ''
        }
      }
    }
  } catch (e) {
    // ignore
  }
}

async function saveIntegration(provider, config) {
  try {
    const res = await apiFetch('/api/integrations', {
      method: 'POST',
      body: JSON.stringify({
        provider,
        api_key: config.apiKey,
        enabled: true,
        label: provider.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      }),
    })
    if (res.ok) {
      config.connected = true
      showSaveMessage('Connected successfully!', 'success')
    } else {
      const data = await res.json()
      showSaveMessage(data.detail || 'Failed to save', 'error')
    }
  } catch (e) {
    showSaveMessage('Connection failed', 'error')
  }
}

async function removeIntegration(provider) {
  try {
    const res = await apiFetch(`/api/integrations/${provider}`, { method: 'DELETE' })
    if (res.ok) {
      integrations[provider].connected = false
      integrations[provider].apiKey = ''
      showSaveMessage('Disconnected', 'success')
    }
  } catch (e) {
    showSaveMessage('Failed to disconnect', 'error')
  }
}

function showSaveMessage(msg, type) {
  saveMessage.value = msg
  saveMessageType.value = type
  setTimeout(() => { saveMessage.value = '' }, 3000)
}

const emit = defineEmits(['update:isVisible', 'close'])

const close = () => {
  emit('update:isVisible', false)
  emit('close')
}

const save = () => {
  Object.assign(configStore, localConfig)
  close()
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.modal-content.settings-modal {
  width: 580px !important;
  max-width: 92vw;
  max-height: 85vh;
  background: #161b22;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.08);
  color: #e6edf3;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-button {
  background: none;
  border: none;
  color: #8b949e;
  font-size: 22px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}
.close-button:hover { color: #e6edf3; }

/* Tabs */
.tabs-bar {
  display: flex;
  gap: 2px;
  padding: 0 24px;
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #8b949e;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.tab-btn:hover { color: #c9d1d9; }
.tab-btn.active {
  color: #e6edf3;
  border-bottom-color: #58a6ff;
}

.modal-body {
  padding: 20px 24px;
  flex: 1;
  overflow-y: auto;
}

/* General tab */
.settings-item {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.settings-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e6edf3;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
  margin-bottom: 6px;
}
.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #58a6ff;
  cursor: pointer;
}

.setting-desc {
  margin-left: 26px;
  color: #8b949e;
  font-size: 12px;
  line-height: 1.4;
  margin-top: 0;
}

/* Integrations tab */
.integrations-intro {
  color: #8b949e;
  font-size: 13px;
  margin: 0 0 20px;
  line-height: 1.5;
}

.integration-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}
.integration-card.connected { border-color: rgba(63,185,80,0.3); }
.integration-card:last-of-type { margin-bottom: 0; }

.integration-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.integration-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.integration-icon.firefly { background: linear-gradient(135deg, #ff6b35, #ff2d78); color: #fff; }
.integration-icon.dalle { background: linear-gradient(135deg, #10a37f, #1a7f5a); color: #fff; }
.integration-icon.stability { background: linear-gradient(135deg, #7c3aed, #a855f7); color: #fff; }
.integration-icon.gemini { background: linear-gradient(135deg, #4285f4, #34a853); color: #fff; }

.integration-info { flex: 1; min-width: 0; }
.integration-info h4 { margin: 0; font-size: 14px; font-weight: 600; color: #e6edf3; }
.integration-info p { margin: 2px 0 0; font-size: 11px; color: #8b949e; }

.status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 10px;
  flex-shrink: 0;
}
.status-badge.connected { background: rgba(63,185,80,0.15); color: #3fb950; }
.status-badge.disconnected { background: rgba(139,148,158,0.1); color: #8b949e; }

.integration-body { padding-top: 4px; }

.input-group { margin-bottom: 12px; }
.input-group label { display: block; font-size: 12px; font-weight: 500; color: #c9d1d9; margin-bottom: 6px; }

.key-input-row { display: flex; gap: 8px; }

.api-key-input {
  flex: 1;
  padding: 8px 12px;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  color: #e6edf3;
  font-size: 13px;
  font-family: 'SF Mono', monospace;
  outline: none;
  transition: border-color 0.2s;
}
.api-key-input:focus { border-color: #58a6ff; }
.api-key-input::placeholder { color: #484f58; }

.toggle-vis {
  padding: 8px 12px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  color: #8b949e;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.toggle-vis:hover { color: #e6edf3; background: rgba(255,255,255,0.1); }

.input-hint {
  margin: 6px 0 0;
  font-size: 11px;
  color: #6e7681;
}
.input-hint a { color: #58a6ff; text-decoration: none; }
.input-hint a:hover { text-decoration: underline; }

.integration-actions { display: flex; gap: 8px; }

.connect-btn {
  padding: 7px 18px;
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}
.connect-btn:hover:not(:disabled) { opacity: 0.9; }
.connect-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.disconnect-btn {
  padding: 7px 18px;
  background: none;
  border: 1px solid rgba(248,81,73,0.3);
  color: #f85149;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.disconnect-btn:hover { background: rgba(248,81,73,0.1); }

.save-message {
  margin-top: 16px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}
.save-message.success { background: rgba(63,185,80,0.1); color: #3fb950; }
.save-message.error { background: rgba(248,81,73,0.1); color: #f85149; }

/* Footer */
.modal-footer {
  padding: 14px 24px;
  border-top: 1px solid rgba(255,255,255,0.06);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.confirm-button {
  background: #58a6ff;
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.2s;
}
.confirm-button:hover { background: #4a96ed; }

.cancel-button {
  background: transparent;
  color: #8b949e;
  border: 1px solid rgba(255,255,255,0.08);
  padding: 8px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.cancel-button:hover { color: #e6edf3; border-color: rgba(255,255,255,0.15); }

/* Transitions */
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
</style>
