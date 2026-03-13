# PowerSymphony — Multi-Agent AI Workflow Orchestration Platform

## Overview

PowerSymphony is a full-stack multi-agent AI workflow orchestration SaaS platform designed to enable users to define and execute complex agent pipelines. It aims to streamline the creation, management, and deployment of AI-powered workflows, offering capabilities like multi-agent swarms, real-time collaboration, CI/CD automation, and a workflow marketplace. The platform provides a user-friendly interface for defining agent logic, integrating with various external services, and observing autonomous AI operations.

## User Preferences

- I prefer clear and concise explanations.
- I expect detailed feedback on agent performance and suggestions for improvement.
- I like to have control over the agent's decision-making process, with options for manual intervention.
- I prefer iterative development, where I can see results quickly and provide feedback for refinement.
- I want to be asked before any major changes are made to the core architecture or deployed components.
- Do not make changes to the `WareHouse` directory without explicit confirmation.
- Do not make changes to files within `browser-extension/` unless specifically tasked with browser automation features.

## System Architecture

**Frontend**:
- Built with Vue 3 + Vite, residing in the `frontend/` directory.
- Serves as the primary user interface for defining, managing, and monitoring AI workflows.
- Features include a performance dashboard, system statistics, and a workflow marketplace.
- **Design System**: Dark theme (`#0a0e17` background), glassmorphism cards (`rgba(255,255,255,0.03)` + `backdrop-filter: blur(10px)`), gradient accents (`#aaffcd/#99eaf9/#a0c4ff`), Inter font. CSS variable `--topbar-h: 56px` controls header height across all pages.
- **Key Pages**: HomeView (Mission Command Center with stats/team/capabilities), MissionsView (mission list + creation with 12 templates in 4 categories), MissionChatView (conversational AI chat with team panel + plan phases), LoginView/SignupView (glassmorphism auth forms).
- **Sidebar**: Horizontal top nav bar with brand logo, nav links with icons, settings gear, user avatar with dropdown.

**Backend**:
- Developed with FastAPI and uvicorn/gunicorn, located in the `server/` directory.
- Handles API requests, authentication, database interactions, and orchestrates AI workflow execution.
- Exposes RESTful APIs for managing agents, sessions, performance data, external integrations, and collaboration.

**Multi-Agent Workflow Engine**:
- The core of the platform, defined by the `runtime/` directory.
- Supports YAML-defined agent graphs for creating complex multi-agent pipelines (`yaml_instance/`).
- Incorporates self-improving agents capable of LLM-as-Judge scoring, iterative refinement, cross-run memory, and prompt evolution.
- Enables parallel tool execution and LLM response caching for performance optimization.

**Authentication**:
- JWT-based authentication with bcrypt for secure user access.
- All API routes (except auth and health checks) are protected and require a valid token.

**Missions (Autonomous AI Team)**:
- Users give the AI team a high-level goal (e.g., "Build a cryptocurrency", "Create a social media platform").
- The Team Leader (Alex) asks follow-up questions, then coordinates 7 specialist agents in a team discussion.
- A phased plan with timelines is generated; user reviews and approves.
- Once approved, all agents begin autonomous execution of their assigned tasks.
- Mission states: gathering_info → planning → awaiting_approval → executing → completed
- Frontend: `/missions` (list/create), `/missions/:id` (chat view with team panel)
- Backend: `server/routes/missions.py`, `server/services/mission_service.py`
- DB tables: `missions`, `mission_messages`

**Database**:
- PostgreSQL is used for persistence, managing user accounts and session data.
- Schema includes `users`, `user_sessions`, `missions`, and `mission_messages` tables.

**Browser Extension**:
- A Chrome extension (`browser-extension/`) allows AI agents to control web browsers, facilitating social media automation and other web-based tasks.
- Communicates with the backend via WebSocket (`ws://localhost:8000/ws/browser-agent`) and provides a REST API for browser control actions.

**Collaboration**:
- WebSocket-based real-time collaboration rooms (`/collaboration`) allow multiple users to interact and broadcast shared prompts.

**Deployment**:
- Designed for deployment on Replit Autoscale, with FastAPI serving the built Vue SPA.

## External Dependencies

- **LLM Providers**:
    - `openai`: Supports `gpt-4o`, `gpt-4-turbo`, etc.
    - `anthropic`: Supports `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-3-5`.
    - `google-genai`: Supports `gemini-2.0-flash`, `gemini-2.5-pro`, etc.
- **Database**: PostgreSQL (Replit built-in).
- **Web Scraping**: Uses `beautifulsoup4` and `requests`.
- **CRM Integration**: HubSpot (requires `HUBSPOT_API_KEY` or `HUBSPOT_ACCESS_TOKEN`).
- **Cloud Deployments**:
    - AWS S3 (requires `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`).
    - Google Cloud Storage (requires `GOOGLE_APPLICATION_CREDENTIALS`).
    - GitHub Releases (requires `GITHUB_TOKEN`).
- **Real-Time External APIs**:
    - OpenWeatherMap (requires `OPENWEATHERMAP_API_KEY`).
    - CoinGecko (for crypto prices, no API key).
    - NewsAPI (requires `NEWSAPI_KEY`).
    - Yahoo Finance (for stock prices).
    - OpenStreetMap (for geocoding).
- **Search and Web Reading**:
    - Serper.dev (web search, requires `SERPER_DEV_API_KEY`).
    - Jina AI (web reading, requires `JINA_API_KEY`).
- **GitHub Integration**: Utilizes `GITHUB_TOKEN` for repository interactions.
- **Fine-Tuning**: OpenAI fine-tuning API (requires `OPENAI_API_KEY`).