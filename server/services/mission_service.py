import json
import logging
import os
from datetime import datetime, timezone

from server.services.db import get_cursor

logger = logging.getLogger(__name__)

TEAM_AGENTS = [
    {
        "id": "team_leader",
        "name": "Alex — Team Leader",
        "role": "Chief Strategist & Project Coordinator",
        "avatar": "A",
        "color": "#58a6ff",
        "description": "Coordinates the entire team, breaks down goals into actionable plans, and ensures alignment across all departments."
    },
    {
        "id": "market_researcher",
        "name": "Maya — Market Researcher",
        "role": "Market Intelligence & Competitive Analysis",
        "avatar": "M",
        "color": "#f0883e",
        "description": "Researches target markets, identifies pain points, analyzes competitors, and validates product-market fit."
    },
    {
        "id": "product_strategist",
        "name": "Jordan — Product Strategist",
        "role": "Product Roadmap & Feature Prioritization",
        "avatar": "J",
        "color": "#a371f7",
        "description": "Defines the product vision, creates feature roadmaps, and prioritizes what to build first for maximum impact."
    },
    {
        "id": "core_engineer",
        "name": "Sam — Lead Engineer",
        "role": "Architecture & Core Development",
        "avatar": "S",
        "color": "#3fb950",
        "description": "Designs system architecture, writes core code, builds the MVP, and handles technical decisions."
    },
    {
        "id": "integration_engineer",
        "name": "Riley — Integration Engineer",
        "role": "APIs, Infrastructure & DevOps",
        "avatar": "R",
        "color": "#79c0ff",
        "description": "Handles third-party integrations, deployment infrastructure, monitoring, and system reliability."
    },
    {
        "id": "tester_compliance",
        "name": "Casey — QA & Compliance",
        "role": "Testing, Security & Regulatory Compliance",
        "avatar": "C",
        "color": "#d2a8ff",
        "description": "Ensures quality through testing, handles security audits, and manages regulatory compliance (GDPR, etc)."
    },
    {
        "id": "sales_marketing",
        "name": "Taylor — Growth & Marketing",
        "role": "User Acquisition, Branding & Sales",
        "avatar": "T",
        "color": "#f778ba",
        "description": "Creates marketing strategies, builds brand presence, acquires users, and drives growth metrics."
    },
    {
        "id": "fundraising_ops",
        "name": "Morgan — Operations & Finance",
        "role": "Business Operations, Funding & Revenue",
        "avatar": "O",
        "color": "#ffa657",
        "description": "Manages budgets, fundraising strategy, revenue models, and overall business operations."
    },
]

AGENT_MAP = {a["id"]: a for a in TEAM_AGENTS}


def create_mission(user_id: int, goal: str) -> dict:
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO missions (user_id, goal, status, context)
               VALUES (%s, %s, 'gathering_info', '{}')
               RETURNING id, user_id, goal, status, plan, context, created_at, updated_at""",
            (user_id, goal),
        )
        mission = dict(cur.fetchone())

    _add_message(mission["id"], "user", None, goal)
    leader_response = _generate_leader_response(mission, goal, [])
    _add_message(mission["id"], "agent", "team_leader", leader_response)

    return _serialize_mission(mission)


def get_mission(mission_id: int, user_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM missions WHERE id = %s AND user_id = %s",
            (mission_id, user_id),
        )
        mission = cur.fetchone()
    if not mission:
        return None
    return _serialize_mission(dict(mission))


def list_missions(user_id: int) -> list:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, goal, status, created_at, updated_at FROM missions WHERE user_id = %s ORDER BY updated_at DESC",
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_messages(mission_id: int, user_id: int) -> list | None:
    with get_cursor() as cur:
        cur.execute("SELECT id FROM missions WHERE id = %s AND user_id = %s", (mission_id, user_id))
        if not cur.fetchone():
            return None
        cur.execute(
            "SELECT id, mission_id, role, agent_name, content, metadata, created_at FROM mission_messages WHERE mission_id = %s ORDER BY created_at",
            (mission_id,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            if r.get("agent_name") and r["agent_name"] in AGENT_MAP:
                r["agent"] = AGENT_MAP[r["agent_name"]]
        return rows


APPROVAL_PHRASES = [
    "approve", "approved", "looks good", "go ahead", "let's do it",
    "proceed", "lgtm", "let's go", "do it", "i approve",
    "go for it", "make it happen", "green light",
]


def _is_approval(text: str) -> bool:
    lower = text.lower().strip().rstrip("!. ")
    if lower in ("yes", "yep", "yeah", "yup", "ok", "okay", "sure"):
        return True
    return any(phrase == lower or lower.startswith(phrase + " ") or lower.startswith(phrase + "!") or lower.startswith(phrase + ".") or lower.startswith(phrase + ",") or (" " + phrase) in (" " + lower) for phrase in APPROVAL_PHRASES)


def send_message(mission_id: int, user_id: int, content: str) -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM missions WHERE id = %s AND user_id = %s", (mission_id, user_id))
        mission = cur.fetchone()
    if not mission:
        raise ValueError("Mission not found")
    mission = dict(mission)

    _add_message(mission_id, "user", None, content)

    history = get_messages(mission_id, user_id)

    if mission["status"] == "gathering_info":
        if _is_approval(content):
            _transition_to_planning(mission, history)
        else:
            response = _generate_leader_response(mission, mission["goal"], history)
            _add_message(mission_id, "agent", "team_leader", response)

    elif mission["status"] == "awaiting_approval":
        if _is_approval(content):
            _transition_to_executing(mission)
        else:
            response = _generate_leader_response(mission, mission["goal"], history)
            _add_message(mission_id, "agent", "team_leader", response)

    elif mission["status"] == "executing":
        response = _generate_leader_response(mission, mission["goal"], history)
        _add_message(mission_id, "agent", "team_leader", response)

    return {"ok": True}


def approve_plan(mission_id: int, user_id: int) -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM missions WHERE id = %s AND user_id = %s", (mission_id, user_id))
        mission = cur.fetchone()
    if not mission:
        raise ValueError("Mission not found")
    mission = dict(mission)

    if mission["status"] != "awaiting_approval":
        raise ValueError(f"Cannot approve: mission is in '{mission['status']}' state, not 'awaiting_approval'")

    _transition_to_executing(mission)

    with get_cursor() as cur:
        cur.execute("SELECT status FROM missions WHERE id = %s", (mission_id,))
        current = cur.fetchone()
    return {"ok": True, "status": current["status"]}


def _transition_to_planning(mission: dict, history: list):
    mission_id = mission["id"]

    _add_message(mission_id, "system", None, "The team is now analyzing your goal and creating a plan...")

    _update_status(mission_id, "planning")

    team_discussion = _generate_team_discussion(mission, history)
    for msg in team_discussion:
        _add_message(mission_id, "agent", msg["agent_id"], msg["content"])

    plan = _generate_plan(mission, history)

    with get_cursor() as cur:
        cur.execute(
            "UPDATE missions SET plan = %s, status = 'awaiting_approval', updated_at = NOW() WHERE id = %s",
            (json.dumps(plan), mission_id),
        )

    plan_summary = _format_plan_for_chat(plan)
    _add_message(mission_id, "agent", "team_leader", plan_summary)


def _transition_to_executing(mission: dict):
    mission_id = mission["id"]
    _update_status(mission_id, "executing")
    _add_message(mission_id, "system", None, "Plan approved! The team is now executing the mission.")

    for agent in TEAM_AGENTS[1:]:
        phase = _get_agent_phase(agent["id"], mission.get("plan"))
        msg = f"Starting work on my assigned tasks. {phase}"
        _add_message(mission_id, "agent", agent["id"], msg)

    _add_message(
        mission_id, "agent", "team_leader",
        "All team members have been briefed and are now working on their assigned tasks. "
        "I'll coordinate their efforts and keep you updated on progress. "
        "You can check in anytime by sending a message."
    )


def _add_message(mission_id: int, role: str, agent_name: str | None, content: str, metadata: dict | None = None):
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO mission_messages (mission_id, role, agent_name, content, metadata)
               VALUES (%s, %s, %s, %s, %s)""",
            (mission_id, role, agent_name, content, json.dumps(metadata or {})),
        )
    with get_cursor() as cur:
        cur.execute("UPDATE missions SET updated_at = NOW() WHERE id = %s", (mission_id,))


def _update_status(mission_id: int, status: str):
    with get_cursor() as cur:
        cur.execute(
            "UPDATE missions SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, mission_id),
        )


def _try_llm_call(system_prompt: str, user_prompt: str) -> str | None:
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        return None


def _generate_leader_response(mission: dict, goal: str, history: list) -> str:
    conversation_text = "\n".join(
        f"{'User' if m.get('role') == 'user' else m.get('agent_name', 'System')}: {m.get('content', '')}"
        for m in history[-10:]
    )

    system_prompt = f"""You are Alex, the Team Leader of an elite AI team. Your team includes:
- Maya (Market Research), Jordan (Product Strategy), Sam (Lead Engineer), Riley (Integration/DevOps),
  Casey (QA/Compliance), Taylor (Growth/Marketing), Morgan (Operations/Finance).

The user has given the goal: "{goal}"
Current mission status: {mission.get('status', 'gathering_info')}

If status is 'gathering_info': Ask 2-3 smart, specific follow-up questions to clarify scope, target audience, 
budget constraints, timeline preferences, or technical requirements. Be conversational and enthusiastic.
Show you understand the ambition. Don't ask more than 3 questions at a time.

If status is 'awaiting_approval': Address user's concerns about the plan and offer to adjust.

If status is 'executing': Give a brief progress update on what the team is working on.

Keep responses concise (under 200 words). Be direct, confident, and show expertise."""

    result = _try_llm_call(system_prompt, conversation_text or f"New goal: {goal}")
    if result:
        return result

    if mission.get("status") == "gathering_info" and len(history) <= 2:
        return (
            f"Great goal! I'm excited to help make this happen. Before my team and I dive in, "
            f"I need to understand a few things:\n\n"
            f"1. **Target Audience** — Who is this primarily for? Do you have a specific demographic or market in mind?\n\n"
            f"2. **Timeline & Budget** — What's your ideal timeline? Are there budget constraints we should factor in?\n\n"
            f"3. **Competitive Edge** — What should make this stand out from existing solutions? Any specific features that are must-haves?\n\n"
            f"Once I have these details, I'll brief the team and we'll put together a concrete plan for you."
        )
    elif mission.get("status") == "gathering_info":
        return (
            "Thanks for those details! That gives us a much clearer picture. "
            "If you're happy with the direction, say **\"Go ahead\"** or **\"Let's do it\"** "
            "and I'll get the team together to build out a full plan with timelines and milestones."
        )
    elif mission.get("status") == "awaiting_approval":
        return (
            "I understand your concerns. I can adjust the plan — just let me know what you'd like changed. "
            "Or if you're ready, say **\"Approve\"** and we'll get started right away."
        )
    else:
        return (
            "The team is making progress! Everyone is working on their assigned tasks. "
            "I'll keep you posted on any major milestones. Feel free to ask me about any specific area."
        )


def _generate_team_discussion(mission: dict, history: list) -> list:
    goal = mission["goal"]
    messages = []

    discussion_data = [
        ("market_researcher", f"I've done preliminary research on the market for this goal. There's significant opportunity here, but we need to be strategic about positioning. The competitive landscape has some established players, but I've identified key gaps we can exploit."),
        ("product_strategist", f"Based on Maya's research, I'm thinking we should focus on a phased approach. Phase 1 should be the core value proposition — the thing that makes users say 'I need this.' We can layer on advanced features in Phase 2 and 3."),
        ("core_engineer", f"From a technical standpoint, I can architect this using modern, scalable infrastructure. I'll set up the core system in the first sprint. We'll need to make some technology choices early, but I have strong recommendations based on the requirements."),
        ("integration_engineer", f"I'll handle the deployment pipeline and make sure we have proper monitoring from day one. I've mapped out the integrations we'll need. I can have the infrastructure ready in parallel with Sam's core development."),
        ("tester_compliance", f"I'll set up automated testing from the start — that's non-negotiable for quality. I'm also reviewing any regulatory requirements. We need to be compliant from day one, not as an afterthought."),
        ("sales_marketing", f"I'm already thinking about our go-to-market strategy. We need to build buzz early. I'll create a landing page and start building an audience before the product is even ready. Community building starts now."),
        ("fundraising_ops", f"I've put together initial cost projections. I'll track our burn rate and revenue metrics closely. I'm also exploring potential revenue models that align with this type of product."),
    ]

    system_prompt = f"""You are {{agent_name}}, the {{agent_role}} on an AI team. The team goal is: "{goal}"
    
Write a brief (2-3 sentences) contribution to the team discussion from your professional perspective. 
Be specific to the goal, show expertise, and reference what you'll actually do. Be concise and actionable."""

    for agent_id, fallback in discussion_data:
        agent = AGENT_MAP[agent_id]
        result = _try_llm_call(
            system_prompt.replace("{{agent_name}}", agent["name"].split("—")[0].strip())
                        .replace("{{agent_role}}", agent["role"]),
            f"Goal: {goal}"
        )
        messages.append({
            "agent_id": agent_id,
            "content": result or fallback,
        })

    return messages


def _generate_plan(mission: dict, history: list) -> dict:
    goal = mission["goal"]

    system_prompt = f"""Create a project plan for this goal: "{goal}"

Return a JSON object with this exact structure:
{{
  "title": "Project title",
  "summary": "1-2 sentence summary",
  "timeline": "Estimated total timeline (e.g., '12 weeks')",
  "phases": [
    {{
      "name": "Phase name",
      "duration": "e.g., 2 weeks",
      "tasks": ["Task 1", "Task 2", "Task 3"],
      "assigned_to": ["agent_id1", "agent_id2"],
      "deliverables": ["Deliverable 1"]
    }}
  ],
  "risks": ["Risk 1", "Risk 2"],
  "success_metrics": ["Metric 1", "Metric 2"]
}}

Use these agent IDs: market_researcher, product_strategist, core_engineer, integration_engineer, tester_compliance, sales_marketing, fundraising_ops.
Create 4-6 phases. Be specific and realistic. Return ONLY valid JSON."""

    result = _try_llm_call(system_prompt, f"Goal: {goal}")
    if result:
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse LLM plan: {e}")

    return {
        "title": f"Mission: {goal[:80]}",
        "summary": f"A comprehensive plan to achieve: {goal}",
        "timeline": "12-16 weeks",
        "phases": [
            {
                "name": "Phase 1: Research & Discovery",
                "duration": "2 weeks",
                "tasks": [
                    "Deep market research and competitive analysis",
                    "User persona development and need validation",
                    "Technical feasibility assessment",
                    "Define core value proposition"
                ],
                "assigned_to": ["market_researcher", "product_strategist"],
                "deliverables": ["Market analysis report", "Product requirements document"]
            },
            {
                "name": "Phase 2: Architecture & Design",
                "duration": "2 weeks",
                "tasks": [
                    "System architecture design",
                    "Technology stack selection",
                    "UI/UX wireframes and prototypes",
                    "Infrastructure setup and CI/CD pipeline"
                ],
                "assigned_to": ["core_engineer", "integration_engineer", "product_strategist"],
                "deliverables": ["Architecture document", "Design prototypes", "Dev environment"]
            },
            {
                "name": "Phase 3: Core Development",
                "duration": "4 weeks",
                "tasks": [
                    "Build core product features",
                    "API development and integrations",
                    "Database design and implementation",
                    "Automated test suite setup"
                ],
                "assigned_to": ["core_engineer", "integration_engineer", "tester_compliance"],
                "deliverables": ["Working MVP", "Test coverage report"]
            },
            {
                "name": "Phase 4: Launch Preparation",
                "duration": "2 weeks",
                "tasks": [
                    "Brand identity and marketing materials",
                    "Landing page and social media presence",
                    "Beta testing with early users",
                    "Compliance and security audit"
                ],
                "assigned_to": ["sales_marketing", "tester_compliance", "fundraising_ops"],
                "deliverables": ["Marketing site", "Beta feedback report", "Compliance checklist"]
            },
            {
                "name": "Phase 5: Launch & Growth",
                "duration": "2-6 weeks",
                "tasks": [
                    "Public launch and PR push",
                    "User acquisition campaigns",
                    "Performance monitoring and optimization",
                    "Revenue model activation"
                ],
                "assigned_to": ["sales_marketing", "fundraising_ops", "integration_engineer"],
                "deliverables": ["Live product", "Growth metrics dashboard", "Revenue report"]
            }
        ],
        "risks": [
            "Market conditions may shift during development",
            "Technical complexity could extend timelines",
            "User adoption may require strategy pivots"
        ],
        "success_metrics": [
            "MVP launched within target timeline",
            "Initial user base acquired (target: 100+ users in first month)",
            "Core functionality working with 99%+ uptime",
            "Positive user feedback (NPS > 40)"
        ]
    }


def _format_plan_for_chat(plan: dict) -> str:
    lines = [
        f"## {plan.get('title', 'Mission Plan')}",
        f"\n{plan.get('summary', '')}",
        f"\n**Estimated Timeline:** {plan.get('timeline', 'TBD')}",
        "\n### Phases"
    ]
    for i, phase in enumerate(plan.get("phases", []), 1):
        assigned = ", ".join(
            AGENT_MAP.get(a, {}).get("name", a).split("—")[0].strip()
            for a in phase.get("assigned_to", [])
        )
        lines.append(f"\n**{phase['name']}** ({phase.get('duration', 'TBD')})")
        lines.append(f"Team: {assigned}")
        for task in phase.get("tasks", []):
            lines.append(f"  - {task}")

    if plan.get("success_metrics"):
        lines.append("\n### Success Metrics")
        for m in plan["success_metrics"]:
            lines.append(f"  - {m}")

    lines.append("\n---")
    lines.append("**Ready to proceed?** Say **\"Approve\"** to start execution, or let me know what you'd like to change.")
    return "\n".join(lines)


def _get_agent_phase(agent_id: str, plan) -> str:
    if not plan or not isinstance(plan, dict):
        return "Analyzing requirements and preparing my work stream."
    phases = plan.get("phases", [])
    for phase in phases:
        if agent_id in phase.get("assigned_to", []):
            return f"I'm assigned to **{phase['name']}** — working on: {', '.join(phase.get('tasks', [])[:2])}."
    return "Reviewing the plan and preparing to support the team."


def _serialize_mission(mission: dict) -> dict:
    result = {**mission}
    for key in ["created_at", "updated_at"]:
        if key in result and result[key]:
            result[key] = result[key].isoformat() if hasattr(result[key], 'isoformat') else str(result[key])
    return result
