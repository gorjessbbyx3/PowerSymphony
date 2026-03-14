<template>
  <div class="team-page">
    <div class="particles-bg">
      <div class="glow glow-1"></div>
      <div class="glow glow-2"></div>
    </div>

    <div class="team-container">
      <div class="team-header">
        <div>
          <h1 class="page-title">Your AI Team</h1>
          <p class="page-subtitle">8 specialized agents that collaborate to accomplish your missions</p>
        </div>
      </div>

      <div class="team-stats-row">
        <div class="team-stat-card">
          <div class="stat-num">{{ liveAgents.filter(a => a.status === 'active').length }}</div>
          <div class="stat-label">Active Now</div>
          <div class="stat-pulse" v-if="liveAgents.some(a => a.status === 'active')"></div>
        </div>
        <div class="team-stat-card">
          <div class="stat-num">{{ totalMissions }}</div>
          <div class="stat-label">Missions Handled</div>
        </div>
        <div class="team-stat-card">
          <div class="stat-num">{{ totalTasks }}</div>
          <div class="stat-label">Tasks Completed</div>
        </div>
        <div class="team-stat-card">
          <div class="stat-num">{{ collaborations }}</div>
          <div class="stat-label">Collaborations</div>
        </div>
      </div>

      <div class="agents-grid">
        <div
          v-for="agent in liveAgents"
          :key="agent.id"
          class="agent-card glass-card"
          :class="{ active: agent.status === 'active' }"
        >
          <div class="card-header-row">
            <div class="agent-avatar-lg" :style="{ background: agent.color }">
              {{ agent.avatar }}
            </div>
            <div class="agent-status-indicator" :class="agent.status">
              <span class="status-pip"></span>
              {{ agent.status === 'active' ? 'Working' : 'Ready' }}
            </div>
          </div>
          <h3 class="agent-name">{{ agent.name }}</h3>
          <div class="agent-role">{{ agent.role }}</div>
          <p class="agent-desc">{{ agent.description }}</p>

          <div class="agent-capabilities">
            <span v-for="cap in agent.capabilities" :key="cap" class="cap-tag">{{ cap }}</span>
          </div>

          <div v-if="agent.currentTask" class="agent-current-task">
            <div class="current-label">Currently</div>
            <div class="current-task">{{ agent.currentTask }}</div>
          </div>

          <div class="agent-stats-row">
            <div class="agent-stat">
              <span class="agent-stat-val">{{ agent.tasksCompleted }}</span>
              <span class="agent-stat-lbl">Tasks</span>
            </div>
            <div class="agent-stat">
              <span class="agent-stat-val">{{ agent.collaborations }}</span>
              <span class="agent-stat-lbl">Collabs</span>
            </div>
            <div class="agent-stat">
              <span class="agent-stat-val">{{ agent.workflowsCreated }}</span>
              <span class="agent-stat-lbl">Workflows</span>
            </div>
          </div>
        </div>
      </div>

      <section class="collab-section">
        <h2 class="section-title">How They Work Together</h2>
        <p class="section-subtitle">Your agents autonomously create workflows, delegate tasks, and share progress with each other.</p>
        <div class="collab-grid">
          <div class="collab-card glass-card">
            <div class="collab-icon" style="background: rgba(63,185,80,0.15); color: #3fb950;">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            </div>
            <h3>Self-Organizing Workflows</h3>
            <p>Agents automatically design and manage execution workflows based on the mission requirements. No manual setup needed.</p>
          </div>
          <div class="collab-card glass-card">
            <div class="collab-icon" style="background: rgba(163,113,247,0.15); color: #a371f7;">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <h3>Real-Time Collaboration</h3>
            <p>Agents share findings, review each other's work, and coordinate tasks in real-time. You see it all in the activity feed.</p>
          </div>
          <div class="collab-card glass-card">
            <div class="collab-icon" style="background: rgba(88,166,255,0.15); color: #58a6ff;">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            </div>
            <h3>Continuous Progress</h3>
            <p>Every step is tracked and shared. You stay in the loop without having to manage the details yourself.</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'

const missions = ref([])
const totalMissions = ref(0)
const totalTasks = ref(0)
const collaborations = ref(0)

const agents = [
  { id: 'alex', avatar: 'A', name: 'Alex', role: 'Team Leader', color: '#58a6ff', description: 'Coordinates the team, breaks down missions into phases, and ensures everyone is aligned.', capabilities: ['Planning', 'Delegation', 'Coordination'], tasksCompleted: 0, collaborations: 0, workflowsCreated: 0 },
  { id: 'maya', avatar: 'M', name: 'Maya', role: 'Market Research', color: '#f0883e', description: 'Deep-dives into markets, competitors, and trends to inform strategy decisions.', capabilities: ['Research', 'Analysis', 'Reports'], tasksCompleted: 0, collaborations: 0, workflowsCreated: 0 },
  { id: 'jordan', avatar: 'J', name: 'Jordan', role: 'Product Strategy', color: '#a371f7', description: 'Translates research into actionable product roadmaps and feature priorities.', capabilities: ['Strategy', 'Roadmaps', 'Prioritization'], tasksCompleted: 0, collaborations: 0, workflowsCreated: 0 },
  { id: 'sam', avatar: 'S', name: 'Sam', role: 'Lead Engineer', color: '#3fb950', description: 'Architects and builds the technical solution. Writes code, designs APIs, and sets up infrastructure.', capabilities: ['Full-Stack', 'APIs', 'Architecture'], tasksCompleted: 0, collaborations: 0, workflowsCreated: 0 },
  { id: 'riley', avatar: 'R', name: 'Riley', role: 'DevOps', color: '#79c0ff', description: 'Handles deployments, CI/CD pipelines, monitoring, and infrastructure management.', capabilities: ['CI/CD', 'Deployment', 'Monitoring'], tasksCompleted: 0, collaborations: 0, workflowsCreated: 0 },
  { id: 'casey', avatar: 'C', name: 'Casey', role: 'QA & Compliance', color: '#d2a8ff', description: 'Reviews code quality, runs tests, checks compliance, and ensures everything meets standards.', capabilities: ['Testing', 'Code Review', 'Compliance'], tasksCompleted: 0, collaborations: 0, workflowsCreated: 0 },
  { id: 'taylor', avatar: 'T', name: 'Taylor', role: 'Growth', color: '#f778ba', description: 'Develops marketing strategies, content plans, and growth tactics to reach target users.', capabilities: ['Marketing', 'Content', 'SEO'], tasksCompleted: 0, collaborations: 0, workflowsCreated: 0 },
  { id: 'morgan', avatar: 'O', name: 'Morgan', role: 'Operations', color: '#ffa657', description: 'Manages resources, optimizes processes, and keeps everything running smoothly.', capabilities: ['Ops', 'Optimization', 'Scaling'], tasksCompleted: 0, collaborations: 0, workflowsCreated: 0 },
]

const liveAgents = ref(agents.map(a => ({ ...a, status: 'idle', currentTask: null })))

onMounted(async () => {
  await Promise.all([loadMissions(), loadTeamStats()])
})

async function loadMissions() {
  try {
    const res = await fetch('/api/missions')
    if (res.ok) {
      const data = await res.json()
      missions.value = data.missions || []
      totalMissions.value = missions.value.length

      // Mark agents as active if any mission is executing
      const executing = missions.value.filter(m => m.status === 'executing')
      if (executing.length > 0) {
        liveAgents.value = liveAgents.value.map((a, i) => ({
          ...a,
          status: i < 4 ? 'active' : 'idle',
          currentTask: i < 4 ? 'Working on active mission' : null,
        }))
      }
    }
  } catch { /* ignore */ }
}

async function loadTeamStats() {
  try {
    const res = await fetch('/api/team/stats')
    if (res.ok) {
      const data = await res.json()
      totalTasks.value = data.total_tasks || 0
      collaborations.value = data.collaborations || 0
      if (data.agents) {
        liveAgents.value = liveAgents.value.map(a => {
          const stats = data.agents[a.id] || {}
          return {
            ...a,
            tasksCompleted: stats.tasks_completed || a.tasksCompleted,
            collaborations: stats.collaborations || a.collaborations,
            workflowsCreated: stats.workflows_created || a.workflowsCreated,
            status: stats.status || a.status,
            currentTask: stats.current_task || a.currentTask,
          }
        })
      }
    }
  } catch { /* ignore - stats endpoint may not exist yet */ }
}
</script>

<style scoped>
.team-page {
  min-height: calc(100vh - var(--topbar-h, 56px));
  background: #0a0e17;
  color: #c9d1d9;
  padding: 40px 24px;
  position: relative;
  font-family: 'Inter', sans-serif;
}

.particles-bg { position: fixed; inset: 0; pointer-events: none; z-index: 0; }
.glow { position: absolute; border-radius: 50%; filter: blur(100px); }
.glow-1 { width: 500px; height: 500px; background: rgba(88,166,255,0.06); top: -100px; left: -100px; animation: glowDrift 15s ease-in-out infinite; }
.glow-2 { width: 400px; height: 400px; background: rgba(163,113,247,0.05); bottom: -100px; right: -100px; animation: glowDrift 18s ease-in-out infinite reverse; }
@keyframes glowDrift { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(30px, 20px); } }

.team-container { max-width: 1200px; margin: 0 auto; position: relative; z-index: 1; }

.team-header { margin-bottom: 32px; }

.page-title {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, #aaffcd, #99eaf9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 6px;
}

.page-subtitle { color: #8b949e; font-size: 15px; margin: 0; }

.team-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 36px;
}

.team-stat-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 20px;
  text-align: center;
  position: relative;
  backdrop-filter: blur(10px);
}

.stat-num { font-size: 28px; font-weight: 700; color: #e6edf3; }
.stat-label { font-size: 12px; color: #8b949e; margin-top: 2px; }
.stat-pulse { position: absolute; top: 8px; right: 8px; width: 8px; height: 8px; border-radius: 50%; background: #3fb950; animation: pulse 2s ease-in-out infinite; }

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 56px;
}

.glass-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  transition: all 0.3s;
}

.glass-card:hover {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.1);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

.agent-card { padding: 24px; }
.agent-card.active { border-color: rgba(63,185,80,0.25); }

.card-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }

.agent-avatar-lg {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  color: #fff;
}

.agent-status-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 3px 10px;
  border-radius: 10px;
}

.agent-status-indicator.active { color: #3fb950; background: rgba(63,185,80,0.1); }
.agent-status-indicator.active .status-pip { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.agent-status-indicator.idle { color: #8b949e; background: rgba(139,148,158,0.1); }
.agent-status-indicator.idle .status-pip { background: #484f58; }

.status-pip { width: 6px; height: 6px; border-radius: 50%; }

.agent-name { font-size: 18px; font-weight: 700; color: #e6edf3; margin: 0 0 2px; }
.agent-role { font-size: 13px; color: #8b949e; margin-bottom: 10px; }
.agent-desc { font-size: 13px; color: #8b949e; line-height: 1.5; margin: 0 0 14px; }

.agent-capabilities { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }

.cap-tag {
  padding: 3px 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  font-size: 11px;
  color: #8b949e;
}

.agent-current-task {
  padding: 10px 14px;
  background: rgba(63,185,80,0.06);
  border: 1px solid rgba(63,185,80,0.15);
  border-radius: 10px;
  margin-bottom: 14px;
}

.current-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #3fb950; font-weight: 600; margin-bottom: 2px; }
.current-task { font-size: 13px; color: #c9d1d9; }

.agent-stats-row {
  display: flex;
  gap: 4px;
  border-top: 1px solid rgba(255,255,255,0.04);
  padding-top: 14px;
}

.agent-stat { flex: 1; text-align: center; }
.agent-stat-val { display: block; font-size: 16px; font-weight: 700; color: #e6edf3; }
.agent-stat-lbl { font-size: 10px; color: #484f58; text-transform: uppercase; letter-spacing: 0.3px; }

/* Collaboration section */
.collab-section { margin-bottom: 48px; }

.section-title { font-size: 22px; font-weight: 700; color: #e6edf3; margin: 0 0 8px; }
.section-subtitle { font-size: 15px; color: #8b949e; margin: 0 0 24px; max-width: 600px; }

.collab-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }

.collab-card { padding: 24px; }

.collab-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.collab-card h3 { font-size: 16px; font-weight: 600; color: #e6edf3; margin: 0 0 6px; }
.collab-card p { font-size: 14px; color: #8b949e; margin: 0; line-height: 1.5; }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

@media (max-width: 900px) {
  .team-stats-row { grid-template-columns: repeat(2, 1fr); }
  .collab-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .agents-grid { grid-template-columns: 1fr; }
}
</style>
