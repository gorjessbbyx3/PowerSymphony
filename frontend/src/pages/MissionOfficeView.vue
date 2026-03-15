<template>
  <div class="office-page">
    <div class="office-header">
      <div class="header-left">
        <button class="back-link" @click="$router.push('/missions')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          Missions
        </button>
        <div class="header-info" v-if="mission">
          <h2 class="mission-title">{{ mission.goal }}</h2>
          <div class="mission-status-badge" :class="mission.status">
            <span class="status-dot"></span>
            {{ statusLabel(mission.status) }}
          </div>
        </div>
      </div>
      <div class="header-right">
        <button class="view-toggle-btn" @click="$router.push(`/missions/${route.params.id}`)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          Chat
        </button>
        <button
          v-if="mission?.status === 'awaiting_approval'"
          class="approve-btn"
          @click="approvePlan"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          Approve Plan
        </button>
      </div>
    </div>

    <div class="office-body" v-if="!loading && !loadError">
      <!-- Leader & Team Status Bar with live agent indicators -->
      <div class="hq-status-bar">
        <div class="leader-badge" v-if="electedLeader">
          <div class="leader-avatar" :style="{ background: electedLeader.color }">{{ electedLeader.avatar }}</div>
          <div class="leader-info">
            <div class="leader-label">Project Lead</div>
            <div class="leader-name">{{ electedLeader.name.split('—')[0].trim() }}</div>
          </div>
          <div class="leader-crown">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="#ffd700" stroke="#ffd700" stroke-width="1"><path d="M2 4l3 12h14l3-12-6 7-4-9-4 9-6-7z"/><rect x="5" y="18" width="14" height="3" rx="1"/></svg>
          </div>
        </div>
        <div class="team-status-pills">
          <div
            v-for="agent in teamAgents"
            :key="agent.id"
            class="agent-pill"
            :class="{ active: agentStatus(agent.id) === 'active', thinking: agentStatus(agent.id) === 'thinking', leader: agent.id === electedLeaderId, blocked: lastAgentStatus(agent.id) === 'blocked' }"
            @click="selectAgent(agent)"
          >
            <div class="pill-dot" :style="{ background: agent.color }">{{ agent.avatar }}</div>
            <span class="pill-status-dot" :class="agentStatus(agent.id)"></span>
            <span class="pill-name">{{ agent.name.split('—')[0].trim().split(' ')[0] }}</span>
          </div>
        </div>
        <div class="hq-stats">
          <span class="hq-stat"><strong>{{ agentMessages.length }}</strong> msgs</span>
          <span class="hq-stat"><strong>{{ conversationCount }}</strong> convos</span>
          <span class="hq-stat"><strong>{{ votes.length }}</strong> votes</span>
        </div>
      </div>

      <div class="hq-layout">
        <!-- Main feed -->
        <div class="hq-feed">
          <div class="feed-header">
            <h3 class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
              Headquarters
            </h3>
            <div class="feed-filters">
              <button v-for="f in feedFilters" :key="f.id" class="filter-chip" :class="{ active: activeFeedFilter === f.id }" @click="activeFeedFilter = f.id">
                {{ f.label }}
                <span v-if="f.count" class="filter-count">{{ f.count }}</span>
              </button>
            </div>
          </div>

          <div class="feed-list" ref="feedContainer">
            <div v-if="filteredMessages.length === 0" class="empty-feed">
              <p>Waiting for agents to start collaborating...</p>
            </div>

            <template v-for="(msg, idx) in filteredMessages" :key="msg.id">
              <!-- System messages -->
              <div v-if="msg.role === 'system'" class="feed-system-msg" :class="{ 'new-msg': idx >= animateFrom }">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                {{ msg.content }}
              </div>

              <!-- Vote messages -->
              <div v-else-if="msg.metadata?.type === 'vote' && msg.metadata?.phase === 'proposed'" class="feed-vote-card" :class="{ 'new-msg': idx >= animateFrom }">
                <div class="vote-header">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a371f7" stroke-width="2"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>
                  <span class="vote-badge">Team Vote</span>
                </div>
                <div class="vote-topic">{{ extractVoteTopic(msg.content) }}</div>
                <div class="vote-result-section" v-if="getVoteResult(msg.metadata?.vote_id)">
                  <div class="vote-bar-group">
                    <div v-for="(count, option) in getVoteResult(msg.metadata.vote_id).tally" :key="option" class="vote-bar-row">
                      <span class="vote-option-label">{{ option }}</span>
                      <div class="vote-bar-track">
                        <div class="vote-bar-fill" :style="{ width: (count / 8 * 100) + '%' }" :class="{ winner: option === getVoteResult(msg.metadata.vote_id).winner }"></div>
                      </div>
                      <span class="vote-count">{{ count }}</span>
                    </div>
                  </div>
                  <div class="vote-winner-tag">
                    Decided: <strong>{{ getVoteResult(msg.metadata.vote_id).winner }}</strong>
                  </div>
                </div>
              </div>

              <!-- Election messages -->
              <div v-else-if="msg.metadata?.type === 'election'" class="feed-election-msg" :class="{ 'new-msg': idx >= animateFrom }">
                <div class="election-badge" v-if="msg.metadata.phase === 'nomination'">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="#ffd700" stroke="#ffd700" stroke-width="1"><path d="M2 4l3 12h14l3-12-6 7-4-9-4 9-6-7z"/><rect x="5" y="18" width="14" height="3" rx="1"/></svg>
                  Leader Election
                </div>
                <div class="feed-msg-row">
                  <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">{{ getAgent(msg.agent_name)?.avatar || '?' }}</div>
                  <div class="feed-msg-body">
                    <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                    <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                  </div>
                </div>
              </div>

              <!-- Vote cast (compact) -->
              <div v-else-if="msg.metadata?.type === 'vote' && msg.metadata?.phase === 'cast'" class="feed-vote-cast">
                <div class="feed-msg-dot small" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">{{ getAgent(msg.agent_name)?.avatar || '?' }}</div>
                <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                <span class="cast-text">voted for <strong>{{ msg.metadata.choice }}</strong></span>
              </div>

              <!-- Vote result -->
              <div v-else-if="msg.metadata?.type === 'vote' && msg.metadata?.phase === 'result'" class="feed-vote-result-msg">
                <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">{{ getAgent(msg.agent_name)?.avatar || '?' }}</div>
                <div class="feed-msg-body">
                  <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                  <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                </div>
              </div>

              <!-- Debate messages — special styling for disagreements -->
              <div v-else-if="msg.metadata?.type === 'debate' || msg.metadata?.type === 'debate_resolution'" class="feed-agent-msg debate-msg" :class="{ 'is-reply': msg.metadata?.reply_to, 'is-resolution': msg.metadata?.type === 'debate_resolution' }" :style="{ '--agent-color': getAgent(msg.agent_name)?.color || '#58a6ff' }">
                <div class="debate-badge" v-if="!msg.metadata?.reply_to && msg.metadata?.type !== 'debate_resolution'">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f0883e" stroke-width="2"><path d="M4 14h6v6"/><path d="M20 10h-6V4"/><path d="M14 10l7-7"/><path d="M3 21l7-7"/></svg>
                  Debate
                </div>
                <div class="debate-badge resolution-badge" v-if="msg.metadata?.type === 'debate_resolution'">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Resolution
                </div>
                <div class="feed-msg-row">
                  <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">
                    {{ getAgent(msg.agent_name)?.avatar || '?' }}
                    <span v-if="msg.agent_name === electedLeaderId" class="mini-crown">
                      <svg width="8" height="8" viewBox="0 0 24 24" fill="#ffd700" stroke="none"><path d="M2 4l3 12h14l3-12-6 7-4-9-4 9-6-7z"/></svg>
                    </span>
                  </div>
                  <div class="feed-msg-body">
                    <div class="feed-msg-header">
                      <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                      <span v-if="msg.metadata?.to_agent" class="conversation-arrow">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#484f58" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                      </span>
                      <span v-if="msg.metadata?.to_agent" class="feed-name to-agent" :style="{ color: getAgent(msg.metadata.to_agent)?.color }">{{ getAgentShortName(msg.metadata.to_agent) }}</span>
                      <span v-if="msg.metadata?.confidence" class="confidence-badge" :class="confidenceLevel(msg.metadata.confidence)">{{ msg.metadata.confidence }}%</span>
                      <span class="feed-time">{{ formatTime(msg.created_at) }}</span>
                    </div>
                    <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                    <div class="thinking-bubble" v-if="msg.metadata?.thinking">
                      <div class="thinking-header">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                        <span>Internal thinking</span>
                        <span v-if="msg.metadata?.confidence" class="thinking-confidence">Confidence: {{ msg.metadata.confidence }}%</span>
                      </div>
                      <div class="thinking-text">{{ msg.metadata.thinking }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Breakthrough messages — highlighted -->
              <div v-else-if="msg.metadata?.type === 'breakthrough'" class="feed-agent-msg breakthrough-msg" :class="{ 'new-msg': idx >= animateFrom }">
                <div class="breakthrough-badge">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffd700" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                  Breakthrough
                </div>
                <div class="feed-msg-row">
                  <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">{{ getAgent(msg.agent_name)?.avatar || '?' }}</div>
                  <div class="feed-msg-body">
                    <div class="feed-msg-header">
                      <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                      <span v-if="msg.metadata?.confidence" class="confidence-badge high">{{ msg.metadata.confidence }}%</span>
                      <span class="feed-time">{{ formatTime(msg.created_at) }}</span>
                    </div>
                    <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                    <div class="thinking-bubble breakthrough-thinking" v-if="msg.metadata?.thinking">
                      <div class="thinking-header">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                        <span>Internal thinking</span>
                      </div>
                      <div class="thinking-text">{{ msg.metadata.thinking }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Blocker messages -->
              <div v-else-if="msg.metadata?.type === 'blocker'" class="feed-agent-msg blocker-msg" :class="{ 'new-msg': idx >= animateFrom }">
                <div class="blocker-badge">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                  Blocker
                </div>
                <div class="feed-msg-row">
                  <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">{{ getAgent(msg.agent_name)?.avatar || '?' }}</div>
                  <div class="feed-msg-body">
                    <div class="feed-msg-header">
                      <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                      <span v-if="msg.metadata?.to_agent" class="conversation-arrow">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#484f58" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                      </span>
                      <span v-if="msg.metadata?.to_agent" class="feed-name to-agent" :style="{ color: getAgent(msg.metadata.to_agent)?.color }">{{ getAgentShortName(msg.metadata.to_agent) }}</span>
                      <span class="feed-time">{{ formatTime(msg.created_at) }}</span>
                    </div>
                    <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                    <div class="thinking-bubble blocker-thinking" v-if="msg.metadata?.thinking">
                      <div class="thinking-header">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                        <span>Internal thinking</span>
                      </div>
                      <div class="thinking-text">{{ msg.metadata.thinking }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Regular agent messages (conversations, progress, reactions, etc) -->
              <div v-else-if="msg.role === 'agent'" class="feed-agent-msg" :class="msgClasses(msg)" :style="{ '--agent-color': getAgent(msg.agent_name)?.color || '#58a6ff' }">
                <div class="feed-msg-row">
                  <div class="feed-msg-dot" :style="{ background: getAgent(msg.agent_name)?.color || '#58a6ff' }">
                    {{ getAgent(msg.agent_name)?.avatar || '?' }}
                    <span v-if="msg.agent_name === electedLeaderId" class="mini-crown">
                      <svg width="8" height="8" viewBox="0 0 24 24" fill="#ffd700" stroke="none"><path d="M2 4l3 12h14l3-12-6 7-4-9-4 9-6-7z"/></svg>
                    </span>
                  </div>
                  <div class="feed-msg-body">
                    <div class="feed-msg-header">
                      <span class="feed-name" :style="{ color: getAgent(msg.agent_name)?.color }">{{ getAgentShortName(msg.agent_name) }}</span>
                      <span v-if="msg.metadata?.to_agent" class="conversation-arrow">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#484f58" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                      </span>
                      <span v-if="msg.metadata?.to_agent" class="feed-name to-agent" :style="{ color: getAgent(msg.metadata.to_agent)?.color }">{{ getAgentShortName(msg.metadata.to_agent) }}</span>
                      <span v-if="msg.metadata?.reply_to" class="reply-badge">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 14 4 9 9 4"/><path d="M20 20v-7a4 4 0 0 0-4-4H4"/></svg>
                        reply
                      </span>
                      <span v-if="msg.metadata?.confidence" class="confidence-badge" :class="confidenceLevel(msg.metadata.confidence)">{{ msg.metadata.confidence }}%</span>
                      <span class="feed-role" v-if="!msg.metadata?.to_agent && !msg.metadata?.reply_to">{{ getAgent(msg.agent_name)?.role }}</span>
                      <span class="feed-time">{{ formatTime(msg.created_at) }}</span>
                    </div>
                    <div class="feed-text" v-html="renderMarkdown(msg.content)"></div>
                    <!-- Progress bar -->
                    <div v-if="msg.metadata?.progress != null" class="progress-row">
                      <div class="progress-track">
                        <div class="progress-fill" :style="{ width: msg.metadata.progress + '%' }"></div>
                      </div>
                      <span class="progress-label">{{ msg.metadata.progress }}%</span>
                    </div>
                    <!-- Thinking bubble -->
                    <div class="thinking-bubble" v-if="msg.metadata?.thinking">
                      <div class="thinking-header">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                        <span>Internal thinking</span>
                        <span v-if="msg.metadata?.confidence" class="thinking-confidence">Confidence: {{ msg.metadata.confidence }}%</span>
                      </div>
                      <div class="thinking-text">{{ msg.metadata.thinking }}</div>
                    </div>
                    <div class="feed-reasoning" v-else-if="msg.metadata?.reasoning">
                      <button class="reasoning-toggle" @click="toggleReasoning(msg.id)">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/></svg>
                        {{ expandedReasoning.has(msg.id) ? 'Hide' : 'Show' }} thinking
                      </button>
                      <div v-if="expandedReasoning.has(msg.id)" class="reasoning-text">{{ msg.metadata.reasoning }}</div>
                    </div>
                    <div v-if="msg.metadata?.current_task" class="feed-task-tag">{{ msg.metadata.current_task }}</div>
                  </div>
                </div>
              </div>

              <!-- User messages -->
              <div v-else-if="msg.role === 'user'" class="feed-user-msg">
                <div class="user-bubble">{{ msg.content }}</div>
              </div>
            </template>
          </div>
        </div>

        <!-- Redesigned sidebar with agent work streams -->
        <div class="hq-sidebar">
          <!-- Collaboration graph -->
          <div class="collab-graph-card" v-if="collaborationEdges.length > 0 && !selectedAgent">
            <div class="detail-label">Agent Connections</div>
            <div class="collab-graph">
              <svg :viewBox="`0 0 260 180`" class="graph-svg">
                <line v-for="(edge, i) in collaborationEdges" :key="'e'+i"
                  :x1="agentGraphPos(edge.from).x" :y1="agentGraphPos(edge.from).y"
                  :x2="agentGraphPos(edge.to).x" :y2="agentGraphPos(edge.to).y"
                  :stroke="getAgent(edge.from)?.color || '#30363d'"
                  stroke-opacity="0.3" stroke-width="1.5"/>
                <g v-for="agent in teamAgents" :key="'n'+agent.id" :transform="`translate(${agentGraphPos(agent.id).x},${agentGraphPos(agent.id).y})`">
                  <circle r="14" :fill="agent.color" fill-opacity="0.15" :stroke="agent.color" stroke-opacity="0.4" stroke-width="1"/>
                  <text text-anchor="middle" dy="4" fill="#c9d1d9" font-size="9" font-weight="700">{{ agent.avatar }}</text>
                </g>
              </svg>
            </div>
          </div>

          <!-- Agent detail card when selected -->
          <div v-if="selectedAgent" class="agent-detail-card">
            <button class="detail-close" @click="selectedAgent = null">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
            <div class="detail-top">
              <AgentAvatar :agentId="selectedAgent.id" :color="selectedAgent.color" :icon="selectedAgent.icon" :letter="selectedAgent.avatar" :size="48"/>
              <div>
                <h3 class="detail-name" :style="{ color: selectedAgent.color }">{{ selectedAgent.name.split('—')[0].trim() }}</h3>
                <div class="detail-role">{{ selectedAgent.role }}</div>
                <div class="detail-leader-tag" v-if="selectedAgent.id === electedLeaderId">Project Lead</div>
              </div>
            </div>
            <p class="detail-desc">{{ selectedAgent.description }}</p>
            <!-- Agent's conversation partners -->
            <div class="agent-connections" v-if="agentConnections(selectedAgent.id).length > 0">
              <div class="detail-label">Talking With</div>
              <div class="connection-chips">
                <span v-for="cid in agentConnections(selectedAgent.id)" :key="cid" class="connection-chip" :style="{ borderColor: getAgent(cid)?.color }">
                  <span class="chip-dot" :style="{ background: getAgent(cid)?.color }">{{ getAgent(cid)?.avatar }}</span>
                  {{ getAgentShortName(cid) }}
                </span>
              </div>
            </div>
            <!-- Agent's recent messages -->
            <div class="agent-recent" v-if="agentRecentMessages(selectedAgent.id).length > 0">
              <div class="detail-label">Recent Activity</div>
              <div v-for="m in agentRecentMessages(selectedAgent.id)" :key="m.id" class="agent-recent-msg">
                <div class="recent-text">{{ m.content.substring(0, 100) }}{{ m.content.length > 100 ? '...' : '' }}</div>
                <div class="recent-time">{{ formatTime(m.created_at) }}</div>
              </div>
            </div>
          </div>

          <!-- Active work streams -->
          <div class="workstreams-card" v-if="!selectedAgent && agentWorkStreams.length > 0">
            <div class="detail-label">Active Work Streams</div>
            <div v-for="ws in agentWorkStreams" :key="ws.agentId" class="workstream-row" @click="selectAgent(agentMap[ws.agentId])">
              <div class="ws-agent-dot" :style="{ background: getAgent(ws.agentId)?.color }">{{ getAgent(ws.agentId)?.avatar }}</div>
              <div class="ws-info">
                <div class="ws-name">{{ getAgentShortName(ws.agentId) }}</div>
                <div class="ws-task">{{ ws.task }}</div>
                <div class="ws-progress-bar" v-if="ws.progress != null">
                  <div class="ws-progress-fill" :style="{ width: ws.progress + '%', background: getAgent(ws.agentId)?.color }"></div>
                </div>
              </div>
              <div class="ws-status" :class="ws.status">
                <span class="ws-status-dot"></span>
              </div>
            </div>
          </div>

          <!-- Plan card -->
          <div v-if="!selectedAgent && mission?.plan" class="plan-card">
            <div class="detail-label">Mission Plan</div>
            <div class="plan-title">{{ mission.plan.title }}</div>
            <div class="plan-timeline">{{ mission.plan.timeline }}</div>
            <div class="plan-phases-list">
              <div v-for="(phase, i) in mission.plan.phases || []" :key="i" class="plan-phase-row">
                <div class="phase-num" :class="{ active: mission.status === 'executing' && i === 0 }">{{ i + 1 }}</div>
                <div class="phase-info">
                  <div class="phase-name">{{ phase.name }}</div>
                  <div class="phase-dur">{{ phase.duration }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Decisions -->
          <div class="votes-card" v-if="!selectedAgent && votes.length > 0">
            <div class="detail-label">Decisions Made</div>
            <div v-for="v in votes" :key="v.id" class="vote-summary-row">
              <div class="vote-summary-topic">{{ v.topic }}</div>
              <div class="vote-summary-result" v-if="v.result">{{ v.result.winner }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-dots"><span></span><span></span><span></span></div>
      <p>Entering headquarters...</p>
    </div>
    <div v-if="loadError" class="error-banner">{{ loadError }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import AgentAvatar from '../components/AgentAvatar.vue'

const route = useRoute()

const mission = ref(null)
const messages = ref([])
const teamAgents = ref([])
const votes = ref([])
const selectedAgent = ref(null)
const loading = ref(true)
const loadError = ref('')
const animateFrom = ref(0)
const expandedReasoning = ref(new Set())
const feedContainer = ref(null)
const activeFeedFilter = ref('all')
let pollInterval = null

const agentMap = computed(() => {
  const map = {}
  teamAgents.value.forEach(a => { map[a.id] = a })
  return map
})

const electedLeaderId = computed(() => {
  const ctx = mission.value?.context
  if (!ctx) return 'team_leader'
  const context = typeof ctx === 'string' ? JSON.parse(ctx) : ctx
  return context?.elected_leader || 'team_leader'
})

const electedLeader = computed(() => agentMap.value[electedLeaderId.value] || null)

const agentMessages = computed(() => messages.value.filter(m => m.role === 'agent'))

const conversationCount = computed(() =>
  messages.value.filter(m => m.metadata?.type === 'conversation' || m.metadata?.type === 'debate' || m.metadata?.reply_to).length
)

const feedFilters = computed(() => [
  { id: 'all', label: 'All' },
  { id: 'conversations', label: 'Conversations', count: conversationCount.value || undefined },
  { id: 'debates', label: 'Debates' },
  { id: 'decisions', label: 'Decisions' },
  { id: 'thinking', label: 'Thinking' },
])

const filteredMessages = computed(() => {
  if (activeFeedFilter.value === 'all') return messages.value.filter(m => m.role !== 'user' || m.content)
  if (activeFeedFilter.value === 'conversations') {
    return messages.value.filter(m =>
      m.metadata?.type === 'conversation' || m.metadata?.type === 'thinking_aloud' ||
      m.metadata?.type === 'reaction' || m.metadata?.type === 'reaction_response' ||
      m.metadata?.type === 'handoff' || m.metadata?.type === 'handoff_received' ||
      m.metadata?.to_agent || m.metadata?.reply_to
    )
  }
  if (activeFeedFilter.value === 'debates') {
    return messages.value.filter(m =>
      m.metadata?.type === 'debate' || m.metadata?.type === 'debate_resolution' ||
      m.metadata?.type === 'blocker' || m.metadata?.type === 'breakthrough'
    )
  }
  if (activeFeedFilter.value === 'decisions') {
    return messages.value.filter(m =>
      m.metadata?.type === 'vote' || m.metadata?.type === 'election' || m.role === 'system'
    )
  }
  if (activeFeedFilter.value === 'thinking') {
    return messages.value.filter(m =>
      m.metadata?.thinking || m.metadata?.reasoning || m.metadata?.type === 'thinking_aloud'
    )
  }
  return messages.value
})

// Collaboration graph: edges between agents who have talked to each other
const collaborationEdges = computed(() => {
  const edgeSet = new Set()
  const edges = []
  messages.value.forEach(m => {
    if (m.agent_name && m.metadata?.to_agent) {
      const key = [m.agent_name, m.metadata.to_agent].sort().join('-')
      if (!edgeSet.has(key)) {
        edgeSet.add(key)
        edges.push({ from: m.agent_name, to: m.metadata.to_agent })
      }
    }
    if (m.agent_name && m.metadata?.reply_to) {
      const key = [m.agent_name, m.metadata.reply_to].sort().join('-')
      if (!edgeSet.has(key)) {
        edgeSet.add(key)
        edges.push({ from: m.agent_name, to: m.metadata.reply_to })
      }
    }
  })
  return edges
})

// Agent positions for graph visualization (circular layout)
const agentGraphPositions = computed(() => {
  const pos = {}
  const cx = 130, cy = 90, rx = 100, ry = 65
  teamAgents.value.forEach((a, i) => {
    const angle = (i / teamAgents.value.length) * Math.PI * 2 - Math.PI / 2
    pos[a.id] = { x: cx + rx * Math.cos(angle), y: cy + ry * Math.sin(angle) }
  })
  return pos
})

function agentGraphPos(id) {
  return agentGraphPositions.value[id] || { x: 130, y: 90 }
}

// Work streams from agent messages with progress/task metadata
const agentWorkStreams = computed(() => {
  const streams = []
  const seen = new Set()
  // Walk backwards to get latest per agent
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (m.role === 'agent' && m.agent_name && !seen.has(m.agent_name) && m.metadata) {
      seen.add(m.agent_name)
      if (m.metadata.current_task || m.metadata.progress != null || m.metadata.status) {
        streams.push({
          agentId: m.agent_name,
          task: m.metadata.current_task || m.metadata.type || 'Working...',
          progress: m.metadata.progress,
          status: m.metadata.status || 'working',
        })
      }
    }
  }
  return streams
})

function agentConnections(agentId) {
  const connected = new Set()
  messages.value.forEach(m => {
    if (m.agent_name === agentId && m.metadata?.to_agent) connected.add(m.metadata.to_agent)
    if (m.metadata?.to_agent === agentId && m.agent_name) connected.add(m.agent_name)
    if (m.agent_name === agentId && m.metadata?.reply_to) connected.add(m.metadata.reply_to)
    if (m.metadata?.reply_to === agentId && m.agent_name) connected.add(m.agent_name)
  })
  return [...connected]
}

function agentRecentMessages(agentId) {
  return messages.value.filter(m => m.agent_name === agentId).slice(-3)
}

function lastAgentStatus(agentId) {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].agent_name === agentId && messages.value[i].metadata?.status) {
      return messages.value[i].metadata.status
    }
  }
  return null
}

function msgClasses(msg) {
  return {
    'is-leader': msg.agent_name === electedLeaderId.value,
    'is-reply': msg.metadata?.reply_to,
    'is-handoff': msg.metadata?.type === 'handoff' || msg.metadata?.type === 'handoff_received',
    'is-reaction': msg.metadata?.type === 'reaction' || msg.metadata?.type === 'reaction_response',
    'is-progress': msg.metadata?.type === 'progress_update',
    'has-thinking': msg.metadata?.thinking || msg.metadata?.reasoning,
    'new-msg': false,
  }
}

function confidenceLevel(c) {
  if (c >= 85) return 'high'
  if (c >= 65) return 'medium'
  return 'low'
}

onMounted(async () => {
  await Promise.all([loadMission(), loadTeam()])
  await loadVotes()
  pollInterval = setInterval(pollForUpdates, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

async function loadMission() {
  const id = route.params.id
  loading.value = true
  loadError.value = ''
  try {
    const [mRes, msgRes] = await Promise.all([
      fetch(`/api/missions/${id}`),
      fetch(`/api/missions/${id}/messages`)
    ])
    if (!mRes.ok) throw new Error(`Mission not found (${mRes.status})`)
    if (!msgRes.ok) throw new Error(`Failed to load messages (${msgRes.status})`)
    mission.value = await mRes.json()
    const msgData = await msgRes.json()
    messages.value = msgData.messages || []
    animateFrom.value = messages.value.length
  } catch (e) {
    loadError.value = e.message || 'Failed to load mission'
  } finally {
    loading.value = false
  }
}

async function loadTeam() {
  try {
    const res = await fetch('/api/missions/team/agents')
    if (res.ok) {
      const data = await res.json()
      teamAgents.value = data.agents || []
    }
  } catch (e) { console.error(e) }
}

async function loadVotes() {
  try {
    const res = await fetch(`/api/missions/${route.params.id}/votes`)
    if (res.ok) {
      const data = await res.json()
      votes.value = data.votes || []
    }
  } catch (e) { /* ignore */ }
}

async function pollForUpdates() {
  const id = route.params.id
  try {
    const [mRes, msgRes] = await Promise.all([
      fetch(`/api/missions/${id}`),
      fetch(`/api/missions/${id}/messages`)
    ])
    if (mRes.ok) mission.value = await mRes.json()
    if (msgRes.ok) {
      const msgData = await msgRes.json()
      const newMsgs = msgData.messages || []
      if (newMsgs.length > messages.value.length) {
        animateFrom.value = messages.value.length
        messages.value = newMsgs
        await nextTick()
        if (feedContainer.value) {
          feedContainer.value.scrollTop = feedContainer.value.scrollHeight
        }
      }
    }
    await loadVotes()
  } catch (e) { /* silent */ }
}

async function approvePlan() {
  try {
    const res = await fetch(`/api/missions/${route.params.id}/approve`, { method: 'POST' })
    if (!res.ok) throw new Error('Failed to approve')
    animateFrom.value = messages.value.length
    await loadMission()
  } catch (e) { console.error(e) }
}

function selectAgent(agent) {
  if (!agent) return
  selectedAgent.value = selectedAgent.value?.id === agent.id ? null : agent
}

function agentStatus(agentId) {
  if (!mission.value) return 'idle'
  const s = mission.value.status
  if (s === 'executing') return agentHasSpoken(agentId) ? 'active' : 'idle'
  if (s === 'planning') return 'thinking'
  if (s === 'awaiting_approval') return agentHasSpoken(agentId) ? 'active' : 'idle'
  return agentHasSpoken(agentId) ? 'active' : 'idle'
}

function agentHasSpoken(agentId) {
  return messages.value.some(m => m.agent_name === agentId)
}

function getAgent(id) { return agentMap.value[id] || null }
function getAgentShortName(id) { return agentMap.value[id]?.name?.split('—')[0]?.trim() || id }

function getVoteResult(voteId) {
  if (!voteId) return null
  const v = votes.value.find(vote => vote.id === voteId)
  return v?.result || null
}

function extractVoteTopic(content) {
  const match = content.match(/\*\*Team Vote:\*\*\s*(.+?)(?:\n|$)/)
  return match ? match[1] : content.substring(0, 80)
}

function toggleReasoning(msgId) {
  const s = new Set(expandedReasoning.value)
  if (s.has(msgId)) s.delete(msgId)
  else s.add(msgId)
  expandedReasoning.value = s
}

function statusLabel(s) {
  return { gathering_info: 'Gathering Info', planning: 'Planning', awaiting_approval: 'Awaiting Approval', executing: 'Executing', completed: 'Completed' }[s] || s
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function renderMarkdown(text) {
  if (!text) return ''
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // Highlight @mentions with agent colors
  html = html.replace(/@(\w+)/g, (match, name) => {
    const agent = teamAgents.value.find(a => a.name.split('—')[0].trim().split(' ')[0].toLowerCase() === name.toLowerCase() || a.name.split('—')[0].trim().toLowerCase() === name.toLowerCase())
    if (agent) return `<span class="md-mention" style="color:${agent.color}">@${name}</span>`
    return match
  })
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h2">$1</h3>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h3">$1</h4>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/^  - (.+)$/gm, '<div class="md-li">$1</div>')
  html = html.replace(/^- (.+)$/gm, '<div class="md-li">$1</div>')
  html = html.replace(/^\d+\. (.+)$/gm, '<div class="md-li md-ol">$1</div>')
  html = html.replace(/^---$/gm, '<hr class="md-hr">')
  html = html.replace(/\n\n/g, '<br><br>')
  html = html.replace(/\n/g, '<br>')
  return html
}
</script>

<style scoped>
.office-page { height: calc(100vh - var(--topbar-h, 56px)); background: #0a0e17; overflow: hidden; font-family: 'Inter', sans-serif; display: flex; flex-direction: column; }

.office-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; border-bottom: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); backdrop-filter: blur(10px); flex-shrink: 0; gap: 16px; }
.header-left { display: flex; align-items: center; gap: 16px; min-width: 0; flex: 1; }
.back-link { display: flex; align-items: center; gap: 4px; background: none; border: none; color: #8b949e; cursor: pointer; font-size: 13px; padding: 6px 10px; border-radius: 8px; transition: all 0.2s; white-space: nowrap; }
.back-link:hover { color: #e6edf3; background: rgba(255,255,255,0.05); }
.header-info { min-width: 0; }
.mission-title { font-size: 14px; font-weight: 600; color: #e6edf3; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 400px; }
.mission-status-badge { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.mission-status-badge.gathering_info { color: #58a6ff; } .mission-status-badge.gathering_info .status-dot { background: #58a6ff; }
.mission-status-badge.planning { color: #a371f7; } .mission-status-badge.planning .status-dot { background: #a371f7; }
.mission-status-badge.awaiting_approval { color: #f0883e; } .mission-status-badge.awaiting_approval .status-dot { background: #f0883e; }
.mission-status-badge.executing { color: #3fb950; } .mission-status-badge.executing .status-dot { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.header-right { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.view-toggle-btn { display: flex; align-items: center; gap: 6px; padding: 7px 14px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); color: #c9d1d9; border-radius: 10px; font-size: 13px; cursor: pointer; transition: all 0.2s; }
.view-toggle-btn:hover { background: rgba(255,255,255,0.08); color: #e6edf3; }
.approve-btn { display: flex; align-items: center; gap: 6px; padding: 7px 18px; background: linear-gradient(135deg, #238636, #2ea043); color: #fff; border: none; border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 10px rgba(46,160,67,0.25); }
.approve-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(46,160,67,0.35); }

/* HQ Status Bar */
.hq-status-bar { display: flex; align-items: center; gap: 12px; padding: 10px 20px; border-bottom: 1px solid rgba(255,255,255,0.04); background: rgba(255,255,255,0.015); flex-shrink: 0; }
.leader-badge { display: flex; align-items: center; gap: 10px; padding: 6px 14px 6px 6px; background: rgba(255,215,0,0.06); border: 1px solid rgba(255,215,0,0.15); border-radius: 12px; }
.leader-avatar { width: 32px; height: 32px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; color: #fff; }
.leader-info { }
.leader-label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.8px; color: #ffd700; font-weight: 700; }
.leader-name { font-size: 13px; font-weight: 600; color: #e6edf3; }
.leader-crown { flex-shrink: 0; }
.team-status-pills { display: flex; gap: 3px; flex: 1; }
.agent-pill { position: relative; cursor: pointer; transition: all 0.2s; border-radius: 10px; padding: 3px 6px 3px 3px; display: flex; align-items: center; gap: 4px; }
.agent-pill:hover { background: rgba(255,255,255,0.06); }
.agent-pill.leader .pill-dot { box-shadow: 0 0 0 2px rgba(255,215,0,0.3); }
.agent-pill.blocked .pill-dot { box-shadow: 0 0 0 2px rgba(248,81,73,0.4); }
.pill-dot { width: 26px; height: 26px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 10px; color: #fff; flex-shrink: 0; }
.pill-name { font-size: 9px; color: #484f58; font-weight: 600; display: none; }
.agent-pill:hover .pill-name, .agent-pill.active .pill-name, .agent-pill.leader .pill-name { display: block; }
.pill-status-dot { position: absolute; bottom: 1px; left: 22px; width: 8px; height: 8px; border-radius: 50%; border: 2px solid #0a0e17; background: #30363d; }
.pill-status-dot.active { background: #3fb950; animation: pulse 1.5s ease-in-out infinite; }
.pill-status-dot.thinking { background: #a371f7; animation: pulse 1.5s ease-in-out infinite; }
.hq-stats { display: flex; gap: 10px; font-size: 11px; color: #484f58; flex-shrink: 0; }
.hq-stat strong { color: #8b949e; }

/* HQ Layout */
.office-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.hq-layout { flex: 1; display: flex; overflow: hidden; }
.hq-feed { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.feed-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px 8px; flex-shrink: 0; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: #e6edf3; margin: 0; }
.feed-filters { display: flex; gap: 3px; flex-wrap: wrap; }
.filter-chip { display: flex; align-items: center; gap: 4px; padding: 4px 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; color: #8b949e; font-size: 10px; cursor: pointer; transition: all 0.2s; }
.filter-chip:hover { background: rgba(255,255,255,0.06); }
.filter-chip.active { background: rgba(88,166,255,0.1); border-color: rgba(88,166,255,0.25); color: #58a6ff; }
.filter-count { background: rgba(88,166,255,0.15); color: #58a6ff; font-size: 9px; padding: 0 5px; border-radius: 8px; font-weight: 700; }

.feed-list { flex: 1; overflow-y: auto; padding: 8px 20px 20px; display: flex; flex-direction: column; gap: 6px; }
.empty-feed { text-align: center; padding: 40px; color: #484f58; font-size: 13px; }

/* Animated entrance for new messages */
.new-msg { animation: slideIn 0.35s ease-out; }
@keyframes slideIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

/* Feed message types */
.feed-system-msg { display: flex; align-items: center; gap: 6px; color: #8b949e; font-size: 12px; padding: 6px 12px; background: rgba(255,255,255,0.02); border-radius: 16px; border: 1px solid rgba(255,255,255,0.03); margin: 4px 0; }

.feed-agent-msg { padding: 10px 14px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 14px; transition: all 0.2s; }
.feed-agent-msg:hover { background: rgba(255,255,255,0.035); border-color: rgba(255,255,255,0.07); }
.feed-agent-msg.is-leader { border-left: 3px solid rgba(255,215,0,0.3); }
.feed-agent-msg.is-reply { margin-left: 24px; border-left: 2px solid rgba(88,166,255,0.15); }
.feed-agent-msg.is-handoff { border-left: 3px solid rgba(63,185,80,0.3); background: rgba(63,185,80,0.02); }
.feed-agent-msg.is-reaction { border-left: 3px solid rgba(240,136,62,0.3); background: rgba(240,136,62,0.02); }
.feed-agent-msg.is-progress { border-left: 3px solid var(--agent-color, #58a6ff); }

.feed-msg-row { display: flex; gap: 10px; }
.feed-msg-dot { width: 28px; height: 28px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 10px; color: #fff; flex-shrink: 0; position: relative; }
.feed-msg-dot.small { width: 20px; height: 20px; border-radius: 6px; font-size: 8px; }
.mini-crown { position: absolute; top: -4px; right: -4px; }
.feed-msg-body { flex: 1; min-width: 0; }
.feed-msg-header { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; flex-wrap: wrap; }
.feed-name { font-size: 13px; font-weight: 700; }
.feed-role { font-size: 10px; color: #484f58; }
.feed-time { font-size: 10px; color: #30363d; margin-left: auto; }
.feed-text { font-size: 13px; color: #c9d1d9; line-height: 1.55; }
.feed-text :deep(.md-h2) { font-size: 14px; color: #e6edf3; margin: 8px 0 4px; font-weight: 700; }
.feed-text :deep(.md-h3) { font-size: 13px; color: #e6edf3; margin: 6px 0 3px; font-weight: 600; }
.feed-text :deep(.md-li) { padding-left: 14px; position: relative; margin: 3px 0; }
.feed-text :deep(.md-li::before) { content: ''; position: absolute; left: 3px; top: 8px; width: 3px; height: 3px; border-radius: 50%; background: #484f58; }
.feed-text :deep(.md-hr) { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 10px 0; }
.feed-text :deep(.md-mention) { font-weight: 700; }

/* Conversation threading */
.conversation-arrow { display: flex; align-items: center; margin: 0 2px; }
.to-agent { font-weight: 600; font-size: 12px; }
.reply-badge { display: inline-flex; align-items: center; gap: 3px; font-size: 10px; color: #58a6ff; background: rgba(88,166,255,0.08); padding: 1px 6px; border-radius: 8px; }

/* Confidence badge */
.confidence-badge { font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 8px; }
.confidence-badge.high { color: #3fb950; background: rgba(63,185,80,0.1); }
.confidence-badge.medium { color: #f0883e; background: rgba(240,136,62,0.1); }
.confidence-badge.low { color: #f85149; background: rgba(248,81,73,0.1); }

/* Progress bar */
.progress-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.progress-track { flex: 1; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #58a6ff, #3fb950); border-radius: 2px; transition: width 0.5s ease; }
.progress-label { font-size: 10px; font-weight: 700; color: #8b949e; }

/* Debate messages */
.debate-msg { border-left: 3px solid rgba(240,136,62,0.3) !important; background: rgba(240,136,62,0.02) !important; }
.debate-msg.is-reply { margin-left: 24px; border-left: 3px solid rgba(240,136,62,0.2) !important; }
.debate-msg.is-resolution { border-left: 3px solid rgba(63,185,80,0.3) !important; background: rgba(63,185,80,0.02) !important; }
.debate-badge { display: flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #f0883e; margin-bottom: 6px; }
.resolution-badge { color: #3fb950 !important; }

/* Breakthrough messages */
.breakthrough-msg { border: 1px solid rgba(255,215,0,0.2) !important; background: rgba(255,215,0,0.03) !important; border-left: 3px solid rgba(255,215,0,0.4) !important; }
.breakthrough-badge { display: flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #ffd700; margin-bottom: 6px; }
.breakthrough-thinking { border-color: rgba(255,215,0,0.15) !important; border-left-color: rgba(255,215,0,0.3) !important; background: rgba(255,215,0,0.03) !important; }
.breakthrough-thinking .thinking-header { color: #ffd700 !important; }

/* Blocker messages */
.blocker-msg { border: 1px solid rgba(248,81,73,0.2) !important; background: rgba(248,81,73,0.03) !important; border-left: 3px solid rgba(248,81,73,0.4) !important; }
.blocker-badge { display: flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #f85149; margin-bottom: 6px; }
.blocker-thinking { border-color: rgba(248,81,73,0.15) !important; border-left-color: rgba(248,81,73,0.3) !important; background: rgba(248,81,73,0.03) !important; }
.blocker-thinking .thinking-header { color: #f85149 !important; }

/* Thinking bubbles */
.thinking-bubble { margin-top: 8px; padding: 8px 12px; background: rgba(163,113,247,0.04); border: 1px solid rgba(163,113,247,0.1); border-radius: 10px; border-left: 3px solid rgba(163,113,247,0.25); }
.thinking-header { display: flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 600; color: #a371f7; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.thinking-confidence { margin-left: auto; font-size: 9px; opacity: 0.7; }
.thinking-text { font-size: 12px; color: #8b949e; line-height: 1.5; font-style: italic; }

.feed-reasoning { margin-top: 6px; }
.reasoning-toggle { display: flex; align-items: center; gap: 4px; background: none; border: none; color: #484f58; font-size: 11px; cursor: pointer; padding: 2px 0; }
.reasoning-toggle:hover { color: #8b949e; }
.reasoning-text { font-size: 11px; color: #484f58; line-height: 1.5; font-style: italic; margin-top: 4px; padding: 6px 10px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 2px solid rgba(255,255,255,0.06); }
.feed-task-tag { display: inline-block; margin-top: 6px; font-size: 10px; background: rgba(255,255,255,0.04); color: #8b949e; padding: 2px 8px; border-radius: 6px; }

/* Election messages */
.feed-election-msg { padding: 10px 14px; background: rgba(255,215,0,0.03); border: 1px solid rgba(255,215,0,0.1); border-radius: 14px; }
.election-badge { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: #ffd700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }

/* Vote messages */
.feed-vote-card { padding: 14px 16px; background: rgba(163,113,247,0.04); border: 1px solid rgba(163,113,247,0.15); border-radius: 14px; }
.vote-header { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.vote-badge { font-size: 11px; font-weight: 700; color: #a371f7; text-transform: uppercase; letter-spacing: 0.5px; }
.vote-topic { font-size: 14px; font-weight: 600; color: #e6edf3; margin-bottom: 12px; }
.vote-result-section { margin-top: 8px; }
.vote-bar-group { display: flex; flex-direction: column; gap: 6px; }
.vote-bar-row { display: flex; align-items: center; gap: 10px; }
.vote-option-label { font-size: 11px; color: #c9d1d9; width: 200px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vote-bar-track { flex: 1; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
.vote-bar-fill { height: 100%; background: #484f58; border-radius: 3px; transition: width 0.5s ease; }
.vote-bar-fill.winner { background: linear-gradient(90deg, #a371f7, #58a6ff); }
.vote-count { font-size: 11px; color: #8b949e; width: 16px; text-align: right; }
.vote-winner-tag { margin-top: 10px; font-size: 12px; color: #a371f7; padding: 4px 10px; background: rgba(163,113,247,0.08); border-radius: 8px; display: inline-block; }

.feed-vote-cast { display: flex; align-items: center; gap: 8px; padding: 4px 12px; font-size: 12px; color: #8b949e; }
.cast-text strong { color: #c9d1d9; }
.feed-vote-result-msg { padding: 10px 14px; background: rgba(163,113,247,0.03); border: 1px solid rgba(163,113,247,0.1); border-radius: 14px; }

.feed-user-msg { display: flex; justify-content: flex-end; }
.user-bubble { padding: 8px 14px; background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.2); border-radius: 14px; color: #79c0ff; font-size: 13px; max-width: 60%; }

/* Sidebar */
.hq-sidebar { width: 320px; border-left: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.015); overflow-y: auto; padding: 16px; flex-shrink: 0; display: flex; flex-direction: column; gap: 14px; }

/* Collaboration graph */
.collab-graph-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 12px; }
.collab-graph { display: flex; justify-content: center; }
.graph-svg { width: 100%; height: 160px; }

/* Agent detail, plan, votes cards */
.agent-detail-card, .plan-card, .votes-card, .workstreams-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 16px; position: relative; }
.detail-close { position: absolute; top: 12px; right: 12px; background: none; border: none; color: #484f58; cursor: pointer; padding: 4px; border-radius: 6px; }
.detail-close:hover { color: #e6edf3; background: rgba(255,255,255,0.05); }
.detail-top { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.detail-name { font-size: 15px; font-weight: 700; margin: 0; }
.detail-role { font-size: 11px; color: #8b949e; }
.detail-leader-tag { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #ffd700; margin-top: 2px; }
.detail-desc { font-size: 12px; color: #8b949e; line-height: 1.5; margin: 0 0 12px; }
.detail-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #484f58; margin-bottom: 8px; }
.detail-kpis { }
.kpi-row { font-size: 11px; color: #8b949e; padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.03); line-height: 1.4; }

/* Agent connections */
.agent-connections { margin-top: 12px; }
.connection-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.connection-chip { display: flex; align-items: center; gap: 4px; padding: 3px 8px; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; font-size: 10px; color: #c9d1d9; }
.chip-dot { width: 14px; height: 14px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 7px; font-weight: 700; color: #fff; }

/* Agent recent messages */
.agent-recent { margin-top: 12px; }
.agent-recent-msg { padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.recent-text { font-size: 11px; color: #8b949e; line-height: 1.4; }
.recent-time { font-size: 9px; color: #30363d; margin-top: 2px; }

/* Work streams */
.workstream-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); cursor: pointer; transition: all 0.2s; }
.workstream-row:hover { background: rgba(255,255,255,0.02); margin: 0 -8px; padding: 8px 8px; border-radius: 8px; }
.ws-agent-dot { width: 24px; height: 24px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 9px; color: #fff; flex-shrink: 0; }
.ws-info { flex: 1; min-width: 0; }
.ws-name { font-size: 11px; font-weight: 700; color: #c9d1d9; }
.ws-task { font-size: 10px; color: #484f58; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ws-progress-bar { height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; margin-top: 4px; }
.ws-progress-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
.ws-status { flex-shrink: 0; }
.ws-status-dot { width: 6px; height: 6px; border-radius: 50%; display: block; background: #30363d; }
.ws-status.working .ws-status-dot { background: #3fb950; animation: pulse 1.5s infinite; }
.ws-status.collaborating .ws-status-dot { background: #58a6ff; animation: pulse 1.5s infinite; }
.ws-status.blocked .ws-status-dot { background: #f85149; }
.ws-status.handing_off .ws-status-dot { background: #a371f7; }

.plan-title { font-size: 14px; font-weight: 600; color: #e6edf3; margin-bottom: 4px; }
.plan-timeline { font-size: 12px; color: #8b949e; margin-bottom: 12px; }
.plan-phases-list { display: flex; flex-direction: column; gap: 6px; }
.plan-phase-row { display: flex; align-items: center; gap: 10px; }
.phase-num { width: 22px; height: 22px; border-radius: 50%; border: 2px solid #21262d; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #484f58; flex-shrink: 0; }
.phase-num.active { border-color: #3fb950; color: #3fb950; background: rgba(63,185,80,0.1); }
.phase-info { min-width: 0; }
.phase-name { font-size: 12px; font-weight: 600; color: #c9d1d9; }
.phase-dur { font-size: 10px; color: #484f58; }

.vote-summary-row { padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.vote-summary-topic { font-size: 12px; color: #c9d1d9; margin-bottom: 2px; }
.vote-summary-result { font-size: 11px; color: #a371f7; font-weight: 600; }

.loading-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: #8b949e; padding: 60px; flex: 1; }
.loading-dots { display: flex; gap: 6px; }
.loading-dots span { width: 10px; height: 10px; border-radius: 50%; background: #30363d; animation: loadBounce 1.4s ease-in-out infinite; }
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes loadBounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
.error-banner { color: #f85149; background: rgba(248,81,73,0.08); border: 1px solid rgba(248,81,73,0.2); padding: 10px 16px; border-radius: 10px; font-size: 13px; text-align: center; margin: 20px; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

@media (max-width: 900px) {
  .hq-sidebar { display: none; }
  .hq-status-bar { flex-wrap: wrap; }
  .vote-option-label { width: 120px; }
  .mission-title { max-width: 200px; }
  .pill-name { display: none !important; }
}
</style>
