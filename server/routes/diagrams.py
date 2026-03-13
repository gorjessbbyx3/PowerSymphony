"""Visual Debugging — REST API for AI-generated Mermaid diagrams."""

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/diagrams", tags=["diagrams"])


class GenerateRequest(BaseModel):
    description: str
    diagram_type: str = "flowchart"


class DebugRequest(BaseModel):
    error: str
    code: str
    language: str = "python"


class SequenceRequest(BaseModel):
    participants: str
    scenario: str


class ArchitectureRequest(BaseModel):
    system_description: str
    components: str = ""


def _run_tool(func_name: str, **kwargs) -> Any:
    try:
        import importlib
        mod = importlib.import_module("functions.function_calling.mermaid_tools")
        fn = getattr(mod, func_name)
        result = fn(**kwargs)
        return json.loads(result) if isinstance(result, str) else result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/generate")
async def generate_diagram(req: GenerateRequest) -> Dict[str, Any]:
    """Generate a Mermaid diagram from a natural language description."""
    result = _run_tool("generate_mermaid_diagram",
                        description=req.description, diagram_type=req.diagram_type)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"ok": True, **result}


@router.post("/debug")
async def generate_debug_flowchart(req: DebugRequest) -> Dict[str, Any]:
    """Generate a debug flowchart for an error and code context."""
    result = _run_tool("generate_debug_flowchart",
                        error_message=req.error, code_context=req.code, language=req.language)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"ok": True, **result}


@router.post("/sequence")
async def generate_sequence(req: SequenceRequest) -> Dict[str, Any]:
    """Generate a Mermaid sequence diagram for a given scenario."""
    result = _run_tool("generate_sequence_diagram",
                        participants=req.participants, scenario=req.scenario)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"ok": True, **result}


@router.post("/architecture")
async def generate_architecture(req: ArchitectureRequest) -> Dict[str, Any]:
    """Generate a system architecture diagram."""
    result = _run_tool("generate_architecture_diagram",
                        system_description=req.system_description, components=req.components)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"ok": True, **result}


@router.get("/examples")
async def list_examples() -> Dict[str, Any]:
    """Return example Mermaid diagrams for the editor."""
    return {
        "ok": True,
        "examples": [
            {
                "name": "Auth Flow",
                "type": "flowchart",
                "source": """flowchart TD
  A([User]) --> B{Logged in?}
  B -- Yes --> C[Load Dashboard]
  B -- No --> D[Login Page]
  D --> E[Submit Credentials]
  E --> F{Valid?}
  F -- Yes --> G[Create JWT]
  G --> C
  F -- No --> H[Show Error]
  H --> D
  C --> I([Done])""",
            },
            {
                "name": "API Request Flow",
                "type": "sequence",
                "source": """sequenceDiagram
  participant Client
  participant API
  participant Auth
  participant DB
  Client->>API: POST /api/data
  API->>Auth: Verify JWT
  Auth-->>API: Valid token, user_id=42
  API->>DB: SELECT * FROM data WHERE user_id=42
  DB-->>API: [{id:1, value:'hello'}]
  API-->>Client: 200 OK {data: [...]}""",
            },
            {
                "name": "Microservices Architecture",
                "type": "flowchart",
                "source": """flowchart LR
  subgraph Client
    A[Web App]
    B[Mobile App]
  end
  subgraph Gateway
    C[API Gateway]
    D[Load Balancer]
  end
  subgraph Services
    E[Auth Service]
    F[User Service]
    G[Product Service]
    H[Order Service]
  end
  subgraph Data
    I[(Postgres)]
    J[(Redis Cache)]
    K[(MongoDB)]
  end
  A & B --> C --> D
  D --> E & F & G & H
  E & F --> I
  G --> K
  H --> I & J""",
            },
        ],
    }
