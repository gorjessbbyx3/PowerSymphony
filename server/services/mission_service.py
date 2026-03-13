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
        "description": "Coordinates the entire team, breaks down goals into actionable plans, and ensures alignment across all departments.",
        "kpis": [
            "100% team alignment on weekly sprint goals",
            "Daily sync completion rate > 95%",
            "Milestone delivery within 10% of timeline"
        ],
        "dependencies": ["All agents report to Alex", "Resolves cross-team blockers"],
        "icon": "crown"
    },
    {
        "id": "market_researcher",
        "name": "Maya — Market Researcher",
        "role": "Market Intelligence & Competitive Analysis",
        "avatar": "M",
        "color": "#f0883e",
        "description": "Analyzes sales data, identifies target industries (e.g., SaaS firms with 50-500 employees), maps competitive landscapes, and validates product-market fit through data-driven research.",
        "kpis": [
            "Generate 50 validated pain points/week",
            "Competitive analysis covering top 10 players",
            "TAM/SAM/SOM estimation within 2 weeks"
        ],
        "dependencies": ["Feeds insights to Jordan (Product Strategy)", "Data informs Taylor's marketing"],
        "icon": "search"
    },
    {
        "id": "product_strategist",
        "name": "Jordan — Product Strategist",
        "role": "Product Roadmap & Feature Prioritization",
        "avatar": "J",
        "color": "#a371f7",
        "description": "Defines features (e.g., lead scoring via NLP), creates quarterly roadmaps based on user feedback loops, and prioritizes what to build first for maximum impact.",
        "kpis": [
            "Roadmap with quarterly updates based on user feedback",
            "Feature prioritization score > 80% alignment with user needs",
            "PRD completion within 1 week of research handoff"
        ],
        "dependencies": ["Receives research from Maya", "Hands specs to Sam for engineering"],
        "icon": "lightbulb"
    },
    {
        "id": "core_engineer",
        "name": "Sam — Lead Engineer",
        "role": "Architecture & Core Development",
        "avatar": "S",
        "color": "#3fb950",
        "description": "Builds the orchestration engine including agent communication protocols and RLHF for self-improvement. Designs system architecture and writes core code for the MVP.",
        "kpis": [
            "Deploy MVP backend in 4 weeks",
            "Code coverage > 80%",
            "API response time < 200ms p95"
        ],
        "dependencies": ["Builds from Jordan's specs", "Riley handles deployment of Sam's code"],
        "icon": "code"
    },
    {
        "id": "integration_engineer",
        "name": "Riley — Integration Engineer",
        "role": "APIs, Infrastructure & DevOps",
        "avatar": "R",
        "color": "#79c0ff",
        "description": "Handles API hooks to tools like HubSpot/Salesforce, deployment infrastructure, monitoring, and system reliability. Manages cloud infrastructure and CI/CD pipelines.",
        "kpis": [
            "95% uptime SLA",
            "5+ integrations ready by launch",
            "Deploy pipeline under 10 minutes",
            "Auto-scaling configured for 10x traffic spikes"
        ],
        "dependencies": ["Deploys Sam's code", "Integrations feed Casey's test suite"],
        "icon": "plug"
    },
    {
        "id": "tester_compliance",
        "name": "Casey — QA & Compliance",
        "role": "Testing, Security & Regulatory Compliance",
        "avatar": "C",
        "color": "#d2a8ff",
        "description": "Simulates workflows, ensures ethical AI with bias checks and data security. Manages automated testing, security audits, and regulatory compliance.",
        "kpis": [
            "Zero critical bugs in beta release",
            "GDPR compliance certification before launch",
            "Security audit pass rate > 95%",
            "Test coverage > 85% on critical paths"
        ],
        "dependencies": ["Tests Sam and Riley's code", "Compliance sign-off needed before Taylor's launch"],
        "icon": "shield"
    },
    {
        "id": "sales_marketing",
        "name": "Taylor — Growth & Marketing",
        "role": "User Acquisition, Branding & Sales",
        "avatar": "T",
        "color": "#f778ba",
        "description": "Crafts pitches, runs A/B tests on outreach, builds brand presence, acquires users via LinkedIn/email campaigns, and drives growth metrics.",
        "kpis": [
            "Acquire 20 beta users in Month 2",
            "Email open rate > 25%",
            "Landing page conversion > 5%",
            "Social media reach: 10K impressions/week"
        ],
        "dependencies": ["Uses Maya's market data for targeting", "Needs Casey's compliance approval for campaigns"],
        "icon": "megaphone"
    },
    {
        "id": "fundraising_ops",
        "name": "Morgan — Operations & Finance",
        "role": "Business Operations, Funding & Revenue",
        "avatar": "O",
        "color": "#ffa657",
        "description": "Models financials, generates pitch decks, monitors metrics like CAC:LTV ratio. Manages budgets, fundraising strategy, and revenue model optimization.",
        "kpis": [
            "CAC:LTV ratio > 1:3",
            "Secure simulated/angel funding equivalent to $1M in Month 3",
            "Monthly burn rate tracking with < 5% variance",
            "Revenue model validated within 6 weeks"
        ],
        "dependencies": ["Financial models informed by Taylor's acquisition data", "Budget approvals for Sam's infrastructure"],
        "icon": "chart"
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
        _add_message(mission_id, "agent", msg["agent_id"], msg["content"], msg.get("metadata"))

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

    execution_msgs = _generate_execution_kickoff(mission)
    for msg in execution_msgs:
        _add_message(mission_id, "agent", msg["agent_id"], msg["content"], msg.get("metadata"))

    _add_message(
        mission_id, "agent", "team_leader",
        "All team members have been briefed and are now working on their assigned tasks. "
        "I'll coordinate their efforts and keep you updated on progress. "
        "You can check in anytime by sending a message.",
        {"reasoning": "Confirming all agents are aligned and work streams are active. Monitoring dependencies between teams."}
    )


def _generate_execution_kickoff(mission: dict) -> list:
    messages = []
    plan = mission.get("plan")

    kickoff_data = {
        "market_researcher": {
            "content": "Starting deep-dive market analysis. I'm pulling data on target industries and mapping competitor positioning. My goal is to have 50 validated pain points documented within the first week. I'll share my findings with Jordan for product strategy alignment.",
            "reasoning": "Beginning with broad market scan, then narrowing to specific segments. Using competitive intelligence frameworks to identify gaps we can exploit.",
            "task": "Market analysis & competitive research"
        },
        "product_strategist": {
            "content": "I'm defining the core feature set based on our discussions. Working on the PRD now — I'll have the initial roadmap ready for review within 3 days. Coordinating with Sam on technical feasibility for each feature.",
            "reasoning": "Prioritizing features by impact vs. effort matrix. Focusing on the 20% of features that deliver 80% of value for our target users.",
            "task": "Product roadmap & feature specification"
        },
        "core_engineer": {
            "content": "Setting up the development environment and architecting the core system. I'm going with a microservices approach for scalability. Sprint 1 focus: authentication, core data models, and the primary API endpoints. Target: MVP backend in 4 weeks.",
            "reasoning": "Chose microservices over monolith for better scaling and team parallelism. Starting with the most critical path items to unblock other team members.",
            "task": "System architecture & MVP development"
        },
        "integration_engineer": {
            "content": "Spinning up the cloud infrastructure now. CI/CD pipeline will be ready by end of day. I'm also mapping out the integration points — starting with the most critical third-party APIs. Target: 5+ integrations ready for beta.",
            "reasoning": "Infrastructure-first approach ensures Sam can deploy continuously. Prioritizing integrations by user-facing impact and technical complexity.",
            "task": "Infrastructure setup & API integrations"
        },
        "tester_compliance": {
            "content": "Setting up the automated testing framework and establishing our quality gates. I'm also starting the GDPR compliance checklist — we need to be compliant from day one, not as an afterthought. Running initial security scans on the architecture.",
            "reasoning": "Shift-left testing strategy: catch bugs early when they're cheapest to fix. Compliance requirements will shape data handling patterns across all teams.",
            "task": "QA framework & compliance audit"
        },
        "sales_marketing": {
            "content": "Building the go-to-market strategy now. Starting with our ideal customer profile based on Maya's research. I'm designing the landing page and setting up our LinkedIn outreach sequences. Target: 20 beta users in Month 2.",
            "reasoning": "Starting marketing before product is ready creates demand and validates messaging. A/B testing outreach templates to optimize conversion from day one.",
            "task": "GTM strategy & beta user acquisition"
        },
        "fundraising_ops": {
            "content": "Financial model is in progress — projecting 18-month runway scenarios. I'm tracking our burn rate from day one and building the pitch deck for potential investors. Targeting CAC:LTV ratio > 1:3 as our north star metric.",
            "reasoning": "Early financial modeling helps us make smart resource allocation decisions. Building investor materials now so we're ready when the time is right.",
            "task": "Financial modeling & fundraising prep"
        }
    }

    for agent in TEAM_AGENTS[1:]:
        data = kickoff_data.get(agent["id"], {})
        phase = _get_agent_phase(agent["id"], plan)

        if data:
            content = data["content"]
            metadata = {
                "reasoning": data["reasoning"],
                "current_task": data["task"],
                "status": "working"
            }
        else:
            content = f"Starting work on my assigned tasks. {phase}"
            metadata = {"status": "working"}

        messages.append({
            "agent_id": agent["id"],
            "content": content,
            "metadata": metadata
        })

    return messages


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
        ("market_researcher", 
         f"I've done preliminary research on the market for this goal. There's significant opportunity here, but we need to be strategic about positioning. The competitive landscape has some established players, but I've identified key gaps we can exploit. I'll have my full analysis with 50 validated pain points ready within the week.",
         "Scanning market databases and competitor APIs. Initial TAM estimate looks promising. Cross-referencing with industry reports to validate assumptions."),
        ("product_strategist", 
         f"Based on Maya's initial research, I'm thinking we should focus on a phased approach. Phase 1 should be the core value proposition — the thing that makes users say 'I need this.' I'm designing the feature roadmap now with quarterly update cycles based on user feedback loops.",
         "Evaluating Maya's market gaps against technical feasibility. Prioritizing features using RICE framework (Reach, Impact, Confidence, Effort)."),
        ("core_engineer", 
         f"From a technical standpoint, I can architect this using modern, scalable infrastructure. I'll set up the core system in the first sprint with a target of MVP backend in 4 weeks. Building with RLHF-ready agent communication protocols so we can iterate based on real usage.",
         "Evaluating microservices vs monolith tradeoffs. Leaning toward microservices for team parallelism. Will need Riley's input on deployment topology."),
        ("integration_engineer", 
         f"I'll handle the deployment pipeline and make sure we have proper monitoring from day one. I've mapped out the integrations we'll need — targeting HubSpot, Salesforce, and 3 other critical APIs for launch. I can have the infrastructure ready in parallel with Sam's core development. Targeting 95% uptime from day one.",
         "Reviewing API documentation for target integrations. CI/CD pipeline will use GitHub Actions with automated testing gates. Need Casey to define test criteria."),
        ("tester_compliance", 
         f"I'll set up automated testing from the start — that's non-negotiable for quality. I'm also reviewing GDPR and data security requirements. We need to be compliant from day one, not as an afterthought. My target: zero critical bugs in beta. Running initial bias checks on any AI components.",
         "Establishing test pyramid: unit > integration > e2e. GDPR checklist started — data mapping, consent flows, right-to-deletion. Need Sam's data model to complete DPA."),
        ("sales_marketing", 
         f"I'm already thinking about our go-to-market strategy. Based on Maya's target audience data, I'll create targeted LinkedIn and email campaigns. My target is 20 beta users in Month 2. I'll start A/B testing outreach messages this week. Community building starts now — we need buzz before launch.",
         "Designing ICP (Ideal Customer Profile) based on Maya's research. Will run 3 outreach variants simultaneously. Landing page copy needs to reflect Jordan's core value prop."),
        ("fundraising_ops", 
         f"I've put together initial cost projections and I'm modeling our CAC:LTV ratios — targeting > 1:3. I'll track our burn rate closely and have the pitch deck ready by Month 2. Also exploring revenue models that align with this type of product. Target: secure equivalent of $1M in angel funding by Month 3.",
         "Building 18-month financial model with 3 scenarios (conservative, base, optimistic). Revenue model analysis: SaaS subscription vs usage-based vs hybrid. Will need Taylor's acquisition cost data for unit economics."),
    ]

    system_prompt = f"""You are {{agent_name}}, the {{agent_role}} on an AI team. The team goal is: "{goal}"
    
Write a brief (2-3 sentences) contribution to the team discussion from your professional perspective. 
Be specific to the goal, show expertise, and reference what you'll actually do. Reference other team members by name when relevant. Be concise and actionable."""

    for agent_id, fallback, reasoning in discussion_data:
        agent = AGENT_MAP[agent_id]
        result = _try_llm_call(
            system_prompt.replace("{{agent_name}}", agent["name"].split("—")[0].strip())
                        .replace("{{agent_role}}", agent["role"]),
            f"Goal: {goal}"
        )
        messages.append({
            "agent_id": agent_id,
            "content": result or fallback,
            "metadata": {
                "reasoning": reasoning,
                "phase": "planning",
                "status": "analyzing"
            }
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
