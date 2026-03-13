# PowerSymphony — Multi-Agent AI Workflow Orchestration Platform

## Overview

PowerSymphony is a full-stack multi-agent AI workflow orchestration SaaS platform. Define complex agent pipelines via YAML, execute them through a FastAPI backend, and manage everything via a Vue 3 frontend. Users sign up for accounts, log in, and access the platform online. Includes 10 major feature sets: multi-agent swarms, GitHub Copilot synergy, Mermaid visual debugging, real-time collaboration, CI/CD automation, domain-specific templates, live external APIs, model fine-tuning, a workflow marketplace, and full integration.

## Architecture

- **Frontend**: Vue 3 + Vite (port 5000 dev / built to `frontend/dist` for production) — `frontend/`
- **Backend**: FastAPI + uvicorn (port 8000 dev) / gunicorn (port 5000 production) — `server/`, `server_main.py`
- **Database**: PostgreSQL (Replit built-in) — users, sessions tables
- **Auth**: JWT-based authentication with bcrypt password hashing — `server/services/auth_service.py`, `server/routes/auth.py`
- **Runtime**: Multi-agent workflow engine — `runtime/`
- **Workflows**: YAML-defined agent graphs — `yaml_instance/`
- **Browser Extension**: Chrome extension for AI browser control — `browser-extension/`

## Authentication

- Signup: `POST /api/auth/signup` — email + password + optional display name
- Login: `POST /api/auth/login` — returns JWT token (72h expiry)
- Me: `GET /api/auth/me` — returns current user (requires token)
- Logout: `POST /api/auth/logout` — invalidates token
- All `/api/*` routes are protected (require `Authorization: Bearer <token>`) except auth endpoints and health checks
- Frontend uses a global fetch interceptor in `main.js` to attach tokens and handle 401 redirects
- Auth middleware: `utils/middleware.py` → `auth_middleware`

## Database

- PostgreSQL via Replit's built-in database (env: `DATABASE_URL`, `PGHOST`, etc.)
- Schema: `users` (id, email, password_hash, display_name, timestamps), `user_sessions` (id, user_id, token_hash, timestamps)
- Connection helper: `server/services/db.py`
- Schema auto-initialized on startup in `server/bootstrap.py`

## Environment Variables

- `DATABASE_URL` — PostgreSQL connection string (auto-set by Replit)
- `JWT_SECRET` — Secret key for JWT signing (required)
- `OPENWEATHERMAP_API_KEY`, `NEWSAPI_KEY`, `GITHUB_TOKEN` — Optional external API keys
- `RATE_LIMIT_MAX_REQUESTS` — Rate limit per minute per IP (default 120)

## Deployment

- **Target**: Replit Autoscale
- **Build**: `cd frontend && npm run build` (outputs to `frontend/dist`)
- **Run**: `gunicorn --bind=0.0.0.0:5000 --workers=2 --timeout=120 server.app:app -k uvicorn.workers.UvicornWorker`
- In production, FastAPI serves the built Vue SPA from `frontend/dist` via static file mounting + SPA catch-all route

## Dev Workflows (Replit)

- **Start application** — `cd frontend && npm run dev` on port 5000 (webview)
- **Backend** — `python server_main.py --host 0.0.0.0 --port 8000` (console)

## LLM Providers

Providers are registered in `runtime/node/agent/providers/builtin_providers.py`.

| Provider key | Library      | Models                                          |
|-------------|-------------|------------------------------------------------|
| `openai`    | openai       | gpt-4o, gpt-4-turbo, etc.                     |
| `claude`    | anthropic    | claude-opus-4-5, claude-sonnet-4-5, claude-haiku-3-5 |
| `gemini`    | google-genai | gemini-2.0-flash, gemini-2.5-pro, etc.        |

### Using Claude in a workflow YAML

```yaml
config:
  provider: claude
  name: claude-opus-4-5
  api_key: ${ANTHROPIC_API_KEY}
```

Set `ANTHROPIC_API_KEY` in your `.env` file (copy from `.env.example`).

## Browser Extension

Located in `browser-extension/`. Allows AI agents to control real browsers for social media automation.

### Installation (Chrome/Edge)
1. Go to `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `browser-extension/` folder
4. The extension connects to the DevAll backend at `ws://localhost:8000/ws/browser-agent`

### Browser Control API (REST)

The backend exposes REST endpoints at `/api/browser/*` that AI workers can call:

| Endpoint | Description |
|----------|-------------|
| `GET /api/browser/sessions` | List connected browser sessions |
| `GET /api/browser/tabs` | List open tabs |
| `POST /api/browser/open-tab` | Open a new tab |
| `POST /api/browser/navigate` | Navigate to URL |
| `POST /api/browser/click` | Click element by selector or coordinates |
| `POST /api/browser/type` | Type text into element |
| `POST /api/browser/fill-form` | Fill multiple form fields |
| `POST /api/browser/screenshot` | Take a screenshot |
| `POST /api/browser/get-page-content` | Get page text/HTML |
| `POST /api/browser/wait-for-selector` | Wait for DOM element |
| `POST /api/browser/scroll` | Scroll page or element |
| `POST /api/browser/eval` | Run JavaScript in tab |

## Environment Variables

See `.env.example` for all supported variables:
- `API_KEY` / `BASE_URL` — default OpenAI config
- `ANTHROPIC_API_KEY` — for Claude provider
- `SERPER_DEV_API_KEY` — web search tool
- `JINA_API_KEY` — web reading tool

## Performance Improvements

### Parallel Tool Execution
Multiple tools in the same agent node execute concurrently using `ThreadPoolExecutor` (up to 8 workers by default).
- Controlled by `DEVALL_MAX_PARALLEL_TOOLS` env var (default: `8`)
- Implemented in `runtime/node/executor/agent_executor.py` → `_execute_tool_batch`

### LLM Response Cache
Temperature-0 LLM calls are cached to disk and memory to skip redundant API calls.
- Activated when `temperature=0.0` in the node config
- Controlled by `DEVALL_LLM_CACHE` env var (default: `true`)
- Cache stored in `WareHouse/.llm_cache/`
- Cache max entries controlled by `LLM_CACHE_MAX_ENTRIES` (default: `512`)
- Implemented in `utils/llm_cache.py`

### Human Input Polling
Human-input poll interval reduced from 1.0 s to 0.05 s for near-instant UI responsiveness.

## Session Persistence

Workflow sessions are now persisted to disk in `WareHouse/.sessions/` as JSON files. This means past session metadata (status, YAML file, timestamps) survives server restarts.

- Active sessions: available via `GET /api/sessions`
- Historical sessions: also returned under `.historical` key

## Self-Improving Agents

Agents can now learn from their own outputs, score themselves with an LLM judge, evolve their prompts, and improve across every run.

### How It Works

1. **LLM-as-Judge Scoring** — An independent LLM evaluates each output on a 1–10 scale with strengths, critique, and suggestions.
2. **Iterative Refinement** — An agent critiques its own draft and rewrites it in a loop until the quality threshold is reached (default: 8.0/10).
3. **Cross-Run Memory** — Performance records (task, output, score, critique) are persisted to `WareHouse/.agent_performance/` across server restarts.
4. **Prompt Evolution** — After accumulating runs, an agent calls `improve_my_prompt` to generate a better system prompt. The new version is saved with version tracking and avg-score data.
5. **Autonomous Optimizer** — The `autonomous_optimizer.yaml` pipeline runs a 4-agent meta-loop (Analyzer → Optimizer → Validator → Deployer) to autonomously improve any agent.

### Tool Functions (add to any YAML `tools:` section)

| Function | Description |
|----------|-------------|
| `score_my_output` | LLM judge: 1–10 score + strengths + critique + suggestions |
| `run_iterative_refinement` | Refine output in up to 5 loops until quality threshold |
| `compare_outputs` | Judge which of two outputs is better |
| `improve_my_prompt` | Generate + save an improved system prompt |
| `save_performance` | Persist a run record to cross-run history |
| `get_past_runs` | Load N recent scored runs (for cross-run learning) |
| `get_best_prompt` | Get the highest-scoring evolved prompt version |

### REST API (`/api/performance/*`)

| Endpoint | Description |
|----------|-------------|
| `GET /api/performance` | List all agents with performance data |
| `GET /api/performance/{id}` | Stats + trend for one agent |
| `GET /api/performance/{id}/runs` | Recent scored runs |
| `GET /api/performance/{id}/prompt` | All prompt versions + best |
| `POST /api/performance/{id}/score` | Score an output via API |
| `POST /api/performance/{id}/refine` | Iteratively refine via API |
| `POST /api/performance/{id}/improve-prompt` | Evolve prompt via API |
| `POST /api/performance/{id}/runs` | Save a run record |
| `DELETE /api/performance/{id}` | Reset all data for agent |

### Frontend: `/performance`

The **Performance** page in the sidebar shows:
- Agent cards with avg score, run count, prompt versions, and trend bar
- Score trend chart and recent run table when an agent is selected
- Full prompt version history with avg scores per version
- "Try Refinement" button to test iterative refinement interactively

### Example Workflows

| File | Description |
|------|-------------|
| `yaml_instance/self_improving_agent.yaml` | Single agent: learns, writes, refines, saves, evolves |
| `yaml_instance/prompt_evolution_pipeline.yaml` | Two agents: Drafter + Reviewer, both improving over time |
| `yaml_instance/autonomous_optimizer.yaml` | 4-agent meta-pipeline to autonomously optimize any agent |

### Key Files

- `utils/agent_performance_store.py` — Persistent per-agent run + prompt history store
- `functions/function_calling/self_improve.py` — 7 self-improvement tool functions
- `server/routes/agent_performance.py` — REST API
- `frontend/src/pages/AgentPerformanceView.vue` — Performance dashboard

## Data Scraping

Web scraping is available as both **agent tool functions** (use in YAML workflows) and **REST API endpoints**.

### Tool functions (YAML `tools:` section)
| Function | Description |
|----------|-------------|
| `scrape_url` | Scrape a URL → title + main text. Optional CSS selector |
| `scrape_links` | Extract all hyperlinks from a page |
| `scrape_table` | Extract an HTML table as CSV |
| `extract_structured_data` | Extract fields using CSS selectors (JSON schema) |
| `batch_scrape` | Scrape up to 20 URLs concurrently |

### REST API (`/api/scrape/*`)
`POST /api/scrape/url` • `POST /api/scrape/links` • `POST /api/scrape/table` • `POST /api/scrape/extract` • `POST /api/scrape/batch`

No API key required — uses `beautifulsoup4` + `requests`.

## CRM Integration (HubSpot)

### Tool functions
| Function | Description |
|----------|-------------|
| `crm_search_contacts` | Search contacts by name/email |
| `crm_create_contact` | Create a new contact |
| `crm_update_contact` | Update contact properties |
| `crm_list_deals` | List deals (optionally by pipeline) |
| `crm_create_deal` | Create a deal and optionally link a contact |
| `crm_log_activity` | Log a note, call, or email against a contact |

### REST API (`/api/crm/*`)
`GET /api/crm/status` • `GET /api/crm/contacts/search?q=` • `POST /api/crm/contacts` • `PATCH /api/crm/contacts/{id}` • `GET /api/crm/deals` • `POST /api/crm/deals` • `POST /api/crm/contacts/{id}/activities`

**Required env var**: `HUBSPOT_API_KEY` or `HUBSPOT_ACCESS_TOKEN` (Private App token from HubSpot).

### Example workflow: `yaml_instance/crm_lead_pipeline.yaml`

## Cloud Deployments

### Tool functions
| Function | Description |
|----------|-------------|
| `deploy_to_s3` | Upload a file to AWS S3 |
| `deploy_to_gcs` | Upload a file to Google Cloud Storage |
| `deploy_to_github_release` | Create a GitHub Release with optional asset |
| `generate_static_site` | Build a static HTML site from Markdown |
| `list_deployment_history` | View past deployments (stored in `WareHouse/.deployments.jsonl`) |

### REST API (`/api/deploy/*`)
`GET /api/deploy/status` • `POST /api/deploy/s3` • `POST /api/deploy/gcs` • `POST /api/deploy/github-release` • `POST /api/deploy/generate-site` • `GET /api/deploy/history`

**Required env vars** (see `.env.example` for details):
- S3: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- GCS: `GOOGLE_APPLICATION_CREDENTIALS`
- GitHub: `GITHUB_TOKEN`

### Example workflow: `yaml_instance/cloud_deploy_pipeline.yaml`

## Example Workflows

| File | Description |
|------|-------------|
| `yaml_instance/scraping_pipeline.yaml` | Scrape URLs → AI research report |
| `yaml_instance/crm_lead_pipeline.yaml` | Research a lead → create HubSpot contact + deal |
| `yaml_instance/cloud_deploy_pipeline.yaml` | Generate content → static site → deploy to cloud |
| `yaml_instance/claude_example.yaml` | Simple Claude assistant |
| `yaml_instance/dev_swarm.yaml` | 6-agent: Plan→Code→Test→Deploy full cycle |
| `yaml_instance/code_review_swarm.yaml` | Multi-agent code review swarm |
| `yaml_instance/qa_swarm.yaml` | QA testing swarm |
| `yaml_instance/blockchain_builder.yaml` | Smart contract + dApp generator |
| `yaml_instance/tourism_app.yaml` | Geo/tourism API builder |
| `yaml_instance/fintech_api.yaml` | Financial data/payments API |
| `yaml_instance/cicd_generator.yaml` | Describe project → CI/CD pipeline YAML |

## Multi-Agent Swarm Workflows

YAML templates that orchestrate 4–6 specialized agents in series/parallel.
- `dev_swarm.yaml` — Tech Lead → Architect → Backend Dev → Frontend Dev → Test Engineer → DevOps
- `code_review_swarm.yaml` — Security Analyst + Performance Analyst + Style Reviewer → Lead Reviewer
- `qa_swarm.yaml` — Test Planner → Unit Tester + Integration Tester → QA Lead

## GitHub Copilot Synergy

REST API at `/api/github/*` and tool functions for AI agents to read/write GitHub repositories.

| Endpoint | Description |
|----------|-------------|
| `GET /api/github/repos/{owner}` | List repos for owner |
| `GET /api/github/repos/{owner}/{repo}/files` | List files in repo |
| `GET /api/github/repos/{owner}/{repo}/file` | Read file content |
| `POST /api/github/repos/{owner}/{repo}/file` | Write/update a file |
| `POST /api/github/repos/{owner}/{repo}/pr` | Create a pull request |
| `POST /api/github/repos/{owner}/{repo}/issue` | Create an issue |
| `GET /api/github/search` | Search code across GitHub |

**Required env var**: `GITHUB_TOKEN`

## Mermaid Visual Debugging

Live diagram editor at `/diagrams` with 4 modes: Live Editor, Generate from Description, Debug Flowchart, Sequence Diagram. Backend at `/api/diagrams/*`.

| Endpoint | Description |
|----------|-------------|
| `POST /api/diagrams/generate` | AI → Mermaid from text description |
| `POST /api/diagrams/debug` | Error + code → debug flowchart |
| `POST /api/diagrams/sequence` | Scenario → sequence diagram |
| `POST /api/diagrams/architecture` | System description → architecture diagram |
| `GET /api/diagrams/examples` | Pre-built example diagrams |

## Real-Time Collaboration

WebSocket-based collaboration rooms at `/collaboration`. Users can join rooms, see active participants, and broadcast shared prompts.

| Endpoint | Description |
|----------|-------------|
| `GET /api/collab/rooms` | List all active rooms |
| `POST /api/collab/rooms` | Create a room |
| `GET /api/collab/rooms/{id}` | Get room details + participants |
| `POST /api/collab/rooms/{id}/broadcast` | Broadcast a message to room |
| `WS /api/collab/rooms/{id}/ws` | WebSocket: join and receive live updates |
| `DELETE /api/collab/rooms/{id}` | Delete a room |

Rooms are in-memory (reset on server restart).

## CI/CD Automation

REST API at `/api/cicd/*` generates production-ready DevOps configs.

| Endpoint | Description |
|----------|-------------|
| `GET /api/cicd/templates` | List all templates |
| `POST /api/cicd/github-actions` | Generate GitHub Actions YAML |
| `POST /api/cicd/dockerfile` | Generate Dockerfile |
| `POST /api/cicd/docker-compose` | Generate docker-compose.yml |
| `POST /api/cicd/aws-codepipeline` | Generate AWS CodePipeline config |

Supports Python, Node.js, Go, Java, Rust. Deploy targets: Docker Hub, AWS ECR, GitHub Container Registry.

## External API Integration (Live Data)

Tool functions for real-time external data without any caching:

| Function | Description |
|----------|-------------|
| `get_weather` | Real weather via OpenWeatherMap |
| `get_crypto_price` | Live crypto prices (CoinGecko, no key) |
| `get_news_headlines` | Breaking news via NewsAPI |
| `get_stock_price` | Stock prices via Yahoo Finance |
| `geocode_address` | Address → lat/lon (OpenStreetMap) |

**Optional env vars**: `OPENWEATHERMAP_API_KEY`, `NEWSAPI_KEY`

## Model Fine-Tuning

REST API at `/api/fine-tune/*` wraps the OpenAI fine-tuning pipeline.

| Endpoint | Description |
|----------|-------------|
| `POST /api/fine-tune/upload` | Upload JSONL training file |
| `POST /api/fine-tune/create` | Start a fine-tuning job |
| `GET /api/fine-tune/jobs` | List all fine-tuning jobs |
| `GET /api/fine-tune/jobs/{id}` | Get job status |
| `POST /api/fine-tune/jobs/{id}/cancel` | Cancel a job |

**Required env var**: `OPENAI_API_KEY`

## Workflow Marketplace

Browse, publish, download, and rate community AI workflow templates at `/marketplace`. Backed by `WareHouse/.marketplace/listings.jsonl`.

| Endpoint | Description |
|----------|-------------|
| `GET /api/marketplace` | Browse all listings (with search/filter) |
| `GET /api/marketplace/featured` | Featured listings |
| `GET /api/marketplace/categories` | All categories with counts |
| `GET /api/marketplace/{id}` | Single listing detail |
| `POST /api/marketplace` | Publish a new workflow |
| `POST /api/marketplace/{id}/download` | Download YAML, increments count |
| `POST /api/marketplace/{id}/rate` | Rate 1–5 stars |
| `DELETE /api/marketplace/{id}` | Remove a listing |

8 built-in seed listings across Blockchain, Development, DevOps, Finance, Travel, Testing categories.

## System Stats & Monitoring

A new **System** page is available at `/system` in the frontend sidebar.

Backend monitoring endpoints:
| Endpoint | Description |
|----------|-------------|
| `GET /api/system/stats` | Full runtime stats (cache, sessions, providers, config) |
| `GET /api/system/health/detailed` | Component-level health checks |
| `POST /api/system/cache/clear` | Clear the LLM response cache |
| `GET /api/sessions` | List active + historical sessions |

## 8-Agent Orchestration System

8 specialized agents with interdependent roles, KPIs, and a shared sync dashboard at `/orchestration`.

| Agent | Role | KPI | Dependencies |
|-------|------|-----|-------------|
| Market Researcher | Industry analysis, pain point validation | 50 pain points/week | None (entry point) |
| Product Strategist | RICE scoring, quarterly roadmap | 20 features/quarter | Market Researcher |
| Core Engineer | Backend/frontend, RLHF | 12 features/month | Product Strategist |
| Integration Engineer | API hooks (HubSpot, GitHub, Slack) | 95% uptime, 5+ integrations | Product Strategist, Core Engineer |
| Tester & Compliance | QA, bias audit, GDPR | 0 critical bugs | Core Engineer, Integration Engineer |
| Sales & Marketing | Campaigns, A/B tests | 20 beta users (Month 2) | Market Researcher, Product Strategist |
| Fundraising & Ops | Financials, pitch decks | $1M funding (Month 3) | Market Researcher, Sales & Marketing |
| Scaler & Innovator | Performance, auto-scaling | 20% time reduction/quarter | Core Engineer, Integration Engineer, Fundraising |

### Orchestration API (`/api/orchestration/*`)

| Endpoint | Description |
|----------|-------------|
| `GET /api/orchestration/agents` | List all 8 agents with status/KPIs |
| `GET /api/orchestration/agents/{id}` | Single agent detail |
| `PATCH /api/orchestration/agents/{id}` | Update agent status/KPI |
| `POST /api/orchestration/agents/{id}/run` | Start agent run |
| `POST /api/orchestration/agents/{id}/complete` | Complete agent run |
| `GET /api/orchestration/dependencies` | Dependency graph (nodes + edges) |
| `GET /api/orchestration/kpis` | All KPI progress data |
| `GET /api/orchestration/summary` | Dashboard summary stats |
| `GET /api/orchestration/sync` | Sync log entries |
| `POST /api/orchestration/sync` | Post a sync message |

### YAML Workflows (in `yaml_instance/orchestration/`)

Each agent has a multi-node YAML workflow with specialized sub-agents:
- `market_researcher.yaml` — Industry Scanner → Pain Point Validator + Competitor Analyst → Research Synthesizer
- `product_strategist.yaml` — Feedback Collector → Feature Prioritizer → Roadmap Architect → Spec Writer
- `core_engineer.yaml` — Architecture Planner → Backend Dev + Frontend Dev → Code Reviewer
- `integration_engineer.yaml` — Integration Planner → API Builder → Health Monitor
- `tester_compliance.yaml` — Test Planner → Automated Tester + Bias Auditor → QA Reporter
- `sales_marketing.yaml` — Persona Builder → Content Engine → Campaign Optimizer
- `fundraising_ops.yaml` — Financial Modeler → Pitch Deck Generator + Metrics Monitor
- `scaler_innovator.yaml` — Performance Profiler → Auto-Scaler + Innovation Lab → Optimization Executor

## Key Files

- `runtime/node/agent/providers/` — LLM provider implementations
- `runtime/node/agent/providers/claude_provider.py` — Anthropic Claude provider
- `runtime/node/executor/agent_executor.py` — `_execute_tool_batch` (parallel tools), `_invoke_provider` (LLM cache)
- `utils/llm_cache.py` — Disk-backed LLM response cache
- `server/services/session_store.py` — Session persistence with disk snapshots
- `server/routes/system_stats.py` — System stats & monitoring API
- `server/routes/sessions.py` — Session listing API
- `server/routes/browser_agent.py` — WebSocket endpoint for browser extension
- `server/routes/browser_control.py` — REST API for browser automation
- `browser-extension/manifest.json` — Chrome extension manifest
- `yaml_instance/claude_example.yaml` — Example Claude workflow
- `frontend/src/pages/SystemStatsView.vue` — System stats page
- `frontend/src/components/Sidebar.vue` — Navigation (includes System link)
