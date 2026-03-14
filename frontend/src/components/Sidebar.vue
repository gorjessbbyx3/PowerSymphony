<template>
    <div class="sidebar">
        <div class="sidebar-brand" @click="$router.push('/')">
            <span class="brand-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="url(#brandGrad)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <defs><linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#aaffcd"/><stop offset="100%" style="stop-color:#99eaf9"/></linearGradient></defs>
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                </svg>
            </span>
            <span class="brand-name">PowerSymphony</span>
        </div>

        <nav class="sidebar-nav">
            <router-link to="/missions" class="nav-link missions-link">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                Missions
            </router-link>
            <router-link to="/activity" class="nav-link">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                Activity
            </router-link>
            <router-link to="/team" class="nav-link">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                Team
            </router-link>
        </nav>

        <div class="sidebar-actions">
            <button class="settings-nav-btn" @click="showSettingsModal = true" title="Settings">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </button>
            <div class="user-menu" v-if="authState.user">
              <button class="user-btn" @click="showUserMenu = !showUserMenu">
                {{ userInitial }}
              </button>
              <div v-if="showUserMenu" class="user-dropdown">
                <div class="user-info">{{ authState.user.email }}</div>
                <button @click="handleLogout" class="logout-btn">Sign Out</button>
              </div>
            </div>
        </div>
    </div>
    <SettingsModal
      :is-visible="showSettingsModal"
      @update:is-visible="showSettingsModal = $event"
    />
</template>

<script setup>
import { RouterLink, useRouter } from 'vue-router'
import { ref } from 'vue'
import SettingsModal from './SettingsModal.vue'
import { authState, logoutUser } from '../utils/auth'

const showSettingsModal = ref(false)
const showUserMenu = ref(false)

const router = useRouter()

const userInitial = computed(() => {
  if (authState.user?.display_name) return authState.user.display_name[0].toUpperCase()
  if (authState.user?.email) return authState.user.email[0].toUpperCase()
  return '?'
})

async function handleLogout() {
  showUserMenu.value = false
  await logoutUser()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
    width: 100%;
    background: rgba(10,14,23,0.95);
    backdrop-filter: blur(12px);
    padding: 0 20px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    height: 56px;
    position: sticky;
    top: 0;
    z-index: 100;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    margin-right: 32px;
    flex-shrink: 0;
}

.brand-icon {
    display: flex;
    align-items: center;
}

.brand-name {
    font-size: 15px;
    font-weight: 700;
    background: linear-gradient(135deg, #aaffcd, #99eaf9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.3px;
}

.sidebar-nav {
    display: flex;
    gap: 4px;
    align-items: center;
    flex: 1;
}

.nav-link {
    display: flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
    color: #8b949e;
    font-weight: 500;
    font-size: 13px;
    font-family: 'Inter', sans-serif;
    padding: 7px 12px;
    border-radius: 8px;
    transition: all 0.2s ease;
    white-space: nowrap;
}

.nav-link:hover {
    color: #e6edf3;
    background: rgba(255,255,255,0.05);
}

.nav-link.router-link-active,
.nav-link.active {
    color: #e6edf3;
    background: rgba(255,255,255,0.06);
}

.nav-link.missions-link.router-link-active {
    background: rgba(46,160,67,0.12);
    color: #3fb950;
}

.sidebar-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
    flex-shrink: 0;
}

.settings-nav-btn {
  background: transparent;
  border: none;
  color: #8b949e;
  cursor: pointer;
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s;
}

.settings-nav-btn:hover {
  color: #e6edf3;
  background: rgba(255,255,255,0.05);
}

.user-menu {
  position: relative;
  margin-left: 4px;
}

.user-btn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, #aaffcd, #99eaf9);
  color: #0d1117;
  border: none;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.user-btn:hover { opacity: 0.85; transform: scale(1.05); }

.user-dropdown {
  position: absolute;
  top: 44px;
  right: 0;
  background: #161b22;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  min-width: 200px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  z-index: 200;
  overflow: hidden;
}

.user-info {
  padding: 12px 16px;
  color: #c9d1d9;
  font-size: 13px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  word-break: break-all;
}

.logout-btn {
  width: 100%;
  padding: 10px 16px;
  background: transparent;
  border: none;
  color: #f85149;
  font-size: 14px;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: rgba(248, 81, 73, 0.1);
}

@media (max-width: 900px) {
  .nav-link svg { display: none; }
  .sidebar-nav { gap: 2px; }
  .nav-link { padding: 7px 8px; font-size: 12px; }
  .brand-name { display: none; }
}
</style>
