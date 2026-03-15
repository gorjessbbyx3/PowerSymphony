# PowerSymphony

**An AI team orchestration platform where 8 specialized agents self-organize, debate, and build together.**

PowerSymphony gives you a team of AI agents that elect their own leaders, hold debates, flag blockers, share breakthroughs, and collaborate autonomously — all visible in real time through a mission control interface and an animated 3D office.

---

## How It Works

You describe a mission. The AI team takes it from there:

1. **Leader Election** — Agents analyze the goal and vote on who should lead based on expertise match
2. **Planning** — The team researches, debates approaches, and produces a structured plan with phases, assignments, and timelines
3. **Approval** — You review the plan and approve (or redirect)
4. **Execution** — Agents work their assignments, coordinate handoffs, raise blockers, and share progress in real time

## The Team

| Agent | Role | Specialty |
|-------|------|-----------|
| **Alex** | Team Leader | Coordination, multi-domain oversight |
| **Maya** | Market Researcher | Market analysis, competitor research, audience insights |
| **Jordan** | Product Strategist | Roadmaps, feature design, user experience |
| **Sam** | Lead Engineer | Architecture, backend/frontend, API development |
| **Riley** | Integration Engineer | DevOps, cloud infrastructure, CI/CD |
| **Casey** | QA & Compliance | Testing, security audits, GDPR compliance |
| **Taylor** | Growth & Marketing | GTM strategy, content, user acquisition |
| **Morgan** | Operations & Finance | Budgets, resource allocation, fundraising |

## Agent Behaviors

Agents don't just report status — they interact with each other through 9 distinct patterns:

- **Debates** — Two agents disagree on approach; the leader resolves with a compromise
- **Questions** — Agents ask each other for input and get substantive answers
- **Handoffs** — Clean deliverable transfers between agents with context
- **Breakthroughs** — An agent discovers something significant and the team reacts
- **Blockers** — 3-message escalation: blocked agent flags it, leader redirects, resolver unblocks
- **Collaboration** — Agents notice alignment and propose joint work
- **Thinking** — Agents share decision-making reasoning publicly for transparency
- **Progress Updates** — Percentage-based progress with task context
- **Reactions** — Agents endorse or build on each other's work

Every message includes internal thinking (visible in the UI), confidence levels, and status indicators.

## Views

### Mission Chat
Conversational interface where you interact with the team. Send messages, approve plans, and watch the agents coordinate.

### Headquarters (HQ)
A rich feed of all agent activity with:
- Color-coded message types (debates in orange, breakthroughs in gold, blockers in red)
- Confidence badges on every agent message
- Progress bars per agent
- Collaboration graph showing who's talking to whom
- Agent work streams sidebar with real-time status
- Filterable by: All, Conversations, Debates, Decisions, Thinking

### 3D Office
An animated isometric office visualization:
- Individual offices for each agent with desks and monitors
- Central meeting room that activates during planning phases
- Walking animations when agents collaborate across offices
- Speech bubbles with latest messages
- Color-coded monitor screens (green = working, blue = collaborating, red = blocked)
- Leader crown on the elected leader's office
- Click any agent for a detail panel with their thinking and latest work

### Activity Feed
Cross-mission timeline of all agent activity with debate, breakthrough, and blocker event types, filterable by category.

---

## Tech Stack

- **Frontend**: Vue 3 + Vite, Composition API, vue-router
- **Backend**: FastAPI (Python), PostgreSQL with JSONB
- **MCP Server**: Model Context Protocol server for integration with Claude and other AI clients

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Backend
uv sync

# Frontend
cd frontend && npm install
```

### Configuration

```bash
cp .env.example .env
```

Set `DATABASE_URL`, `API_KEY`, and `BASE_URL` in `.env` for your LLM provider.

### Run

```bash
# Recommended — starts both backend and frontend
make dev
```

Or manually:

```bash
# Backend
uv run python server_main.py --port 6400 --reload

# Frontend (in another terminal)
cd frontend
VITE_API_BASE_URL=http://localhost:6400 npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Docker

```bash
docker compose up --build
```

- Backend: `http://localhost:6400`
- Frontend: `http://localhost:5173`

---

## MCP Server

PowerSymphony includes a Model Context Protocol server so external AI clients (like Claude Code) can create missions, talk to the team, and monitor progress programmatically.

Available tools:
- `create_mission` / `list_missions` / `get_mission`
- `send_mission_message` / `get_mission_messages`
- `approve_mission_plan`
- `get_team` / `get_mission_votes`
- `get_orchestration_status` / `get_system_health`
- `execute_workflow` / `list_workflows` / `get_workflow`
- `list_sessions` / `get_session_status`

## Project Structure

```
PowerSymphony/
  frontend/          Vue 3 web console
    src/pages/       All page components (missions, HQ, 3D office, activity, team)
    src/router/      Vue router configuration
    src/utils/       Auth utilities
  server/            FastAPI backend
    routes/          API endpoints
    services/        Core logic (missions, agents, DB)
  mcp_server/        MCP server for AI client integration
  runtime/           Agent abstraction and tool execution
  workflow/          Multi-agent orchestration engine
  yaml_instance/     Workflow configurations
  functions/         Custom Python tools
```

## Utility Commands

```bash
make help              # Show all available commands
make sync              # Upload workflow YAMLs to database
make validate-yamls    # Validate YAML syntax and schema
```

## License

See [LICENSE](./LICENSE) for details.
