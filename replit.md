# DevAll — Workflow Orchestration Platform

## Overview

DevAll is a full-stack AI workflow orchestration platform. It lets you define multi-agent AI pipelines via YAML, execute them via a FastAPI backend, and visualize/manage them through a Vue 3 frontend.

## Architecture

- **Frontend**: Vue 3 + Vite (port 5000) — `frontend/`
- **Backend**: FastAPI + uvicorn (port 8000) — `server/`, `server_main.py`
- **Runtime**: Multi-agent workflow engine — `runtime/`
- **Workflows**: YAML-defined agent graphs — `yaml_instance/`
- **Browser Extension**: Chrome extension for AI browser control — `browser-extension/`

## Workflows (Replit)

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

## Key Files

- `runtime/node/agent/providers/` — LLM provider implementations
- `runtime/node/agent/providers/claude_provider.py` — Anthropic Claude provider
- `server/routes/browser_agent.py` — WebSocket endpoint for browser extension
- `server/routes/browser_control.py` — REST API for browser automation
- `browser-extension/manifest.json` — Chrome extension manifest
- `yaml_instance/claude_example.yaml` — Example Claude workflow
