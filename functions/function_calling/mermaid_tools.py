"""Mermaid Diagram Generator — AI-powered diagram creation for visual debugging.

Agents can generate Mermaid-compatible diagrams to visualize:
- Code/system architecture
- Bug trace flowcharts
- Sequence diagrams for API calls
- ER diagrams for databases
- State machines
"""

import json
import os
from typing import Any, Dict


def _call_llm_for_diagram(prompt: str) -> str:
    """Use the configured LLM to generate Mermaid diagram source."""
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    system = (
        "You are a Mermaid diagram expert. Output ONLY valid Mermaid diagram source code, "
        "no explanations, no markdown fences, no backticks. Just the raw Mermaid syntax."
    )

    if not api_key and anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model=os.environ.get("DIAGRAM_MODEL", "claude-3-haiku-20240307"),
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text if msg.content else ""
        except Exception as exc:
            return f"graph TD\n  Error[\"LLM Error: {str(exc)[:80]}\"]"

    if not api_key:
        return "graph TD\n  Error[\"No API key set: configure API_KEY or ANTHROPIC_API_KEY\"]"

    import openai
    client = openai.OpenAI(
        api_key=api_key,
        base_url=os.environ.get("BASE_URL", "https://api.openai.com/v1")
    )
    try:
        resp = client.chat.completions.create(
            model=os.environ.get("DIAGRAM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        raw = resp.choices[0].message.content or ""
        # Strip any accidental fences
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
        return raw.strip()
    except Exception as exc:
        return f"graph TD\n  Error[\"{str(exc)[:80]}\"]"


def generate_mermaid_diagram(description: str, diagram_type: str = "flowchart") -> str:
    """
    Generate a Mermaid diagram from a natural language description.

    Args:
        description (str): Natural language description of what to diagram, e.g.
                           "A user authentication flow with login, JWT token generation, and refresh".
        diagram_type (str): Type of diagram: flowchart, sequence, classDiagram, erDiagram,
                            stateDiagram, gantt, pie, gitGraph. Defaults to "flowchart".

    Returns:
        str: JSON with keys: mermaid (the diagram source), diagram_type, and description.
    """
    type_hints = {
        "flowchart": "Use `flowchart TD` or `flowchart LR` syntax.",
        "sequence": "Use `sequenceDiagram` syntax with participants and arrows (->>, -->>).",
        "classDiagram": "Use `classDiagram` syntax with classes, attributes, and relationships.",
        "erDiagram": "Use `erDiagram` syntax with entity relationships.",
        "stateDiagram": "Use `stateDiagram-v2` syntax.",
        "gantt": "Use `gantt` syntax with sections and tasks.",
        "pie": "Use `pie` syntax with a title and labeled slices.",
        "gitGraph": "Use `gitGraph` syntax with commits and branches.",
    }.get(diagram_type, "")

    prompt = f"""Create a {diagram_type} Mermaid diagram for the following:

{description}

{type_hints}

Requirements:
- Use clear, descriptive node/participant labels
- Keep it focused and readable
- Use proper Mermaid syntax for the {diagram_type} type
- Output ONLY the Mermaid source code, nothing else"""

    mermaid_src = _call_llm_for_diagram(prompt)
    return json.dumps({
        "mermaid": mermaid_src,
        "diagram_type": diagram_type,
        "description": description,
    }, indent=2)


def generate_debug_flowchart(error_message: str, code_context: str, language: str = "python") -> str:
    """
    Generate a debugging flowchart that visualizes the execution path leading to an error.
    Useful for tracing bugs and understanding failure conditions.

    Args:
        error_message (str): The error message or exception, e.g. "KeyError: 'user_id'".
        code_context (str): The relevant code snippet where the error occurs.
        language (str): Programming language of the code. Defaults to "python".

    Returns:
        str: JSON with keys: mermaid (flowchart source), root_cause (analysis), fix_suggestion.
    """
    prompt = f"""Generate a Mermaid flowchart TD that traces the execution path leading to this error.

Language: {language}
Error: {error_message}

Code Context:
{code_context}

Create a flowchart showing:
1. Program entry point
2. Key decision points (conditions, branches)
3. The failing path highlighted with a distinctive node shape
4. What caused the error
5. Where execution stops

Use these styles for clarity:
- Normal nodes: rectangles [Text]
- Decisions: diamonds {{Text}}
- The error node: double rectangles [[Error: description]]
- Add edge labels where helpful

Output ONLY the Mermaid flowchart TD source."""

    mermaid_src = _call_llm_for_diagram(prompt)

    # Also generate a brief analysis
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    root_cause = "See flowchart for execution trace."
    fix_suggestion = "Review the highlighted error path in the diagram."

    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key, base_url=os.environ.get("BASE_URL", "https://api.openai.com/v1"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"In one sentence each: (1) root cause of `{error_message}` in this code: {code_context[:500]} and (2) the fix. Reply as JSON: {{\"root_cause\": \"...\", \"fix\": \"...\"}}"
                }],
                temperature=0.1, max_tokens=200,
            )
            import re
            content = resp.choices[0].message.content or "{}"
            parsed = json.loads(re.search(r'\{.*\}', content, re.DOTALL).group())
            root_cause = parsed.get("root_cause", root_cause)
            fix_suggestion = parsed.get("fix", fix_suggestion)
        except Exception:
            pass

    return json.dumps({
        "mermaid": mermaid_src,
        "root_cause": root_cause,
        "fix_suggestion": fix_suggestion,
        "error": error_message,
    }, indent=2)


def generate_sequence_diagram(participants: str, scenario: str) -> str:
    """
    Generate a Mermaid sequence diagram for API calls, service interactions, or user flows.

    Args:
        participants (str): Comma-separated list of actors/services, e.g.
                            "User, Frontend, API Server, Database, Auth Service".
        scenario (str): Description of the interaction scenario, e.g.
                        "User logs in: frontend calls auth service, which verifies credentials
                         in DB and returns JWT, which frontend stores in localStorage".

    Returns:
        str: JSON with keys: mermaid (sequence diagram source) and description.
    """
    prompt = f"""Generate a Mermaid sequenceDiagram for this scenario.

Participants: {participants}

Scenario:
{scenario}

Requirements:
- Include all relevant messages between participants
- Use ->> for async messages, -->> for responses
- Use activate/deactivate for critical sections
- Add Notes where helpful to explain key steps
- Output ONLY the sequenceDiagram Mermaid source"""

    mermaid_src = _call_llm_for_diagram(prompt)
    return json.dumps({
        "mermaid": mermaid_src,
        "participants": participants,
        "scenario": scenario,
    }, indent=2)


def generate_architecture_diagram(system_description: str, components: str = "") -> str:
    """
    Generate a system architecture diagram from a description.

    Args:
        system_description (str): High-level description of the system, e.g.
                                  "A microservices e-commerce platform with API gateway,
                                   product service, order service, and payment service".
        components (str): Optional comma-separated list of known components to include.

    Returns:
        str: JSON with keys: mermaid (graph source) and description.
    """
    components_hint = f"\nKey components to include: {components}" if components else ""
    prompt = f"""Generate a Mermaid flowchart LR (left-to-right) system architecture diagram.

System: {system_description}{components_hint}

Show:
- All major services/components as nodes
- External systems (clients, databases, third-party APIs)
- Data flow and API connections as directed arrows
- Group related services using subgraphs where appropriate

Use descriptive labels. Output ONLY the Mermaid source code."""

    mermaid_src = _call_llm_for_diagram(prompt)
    return json.dumps({
        "mermaid": mermaid_src,
        "description": system_description,
    }, indent=2)
