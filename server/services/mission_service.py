import json
import logging
import os
import random
from datetime import datetime, timezone

from server.services.db import get_cursor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Leader election — agents choose the best leader for each mission
# ---------------------------------------------------------------------------

LEADER_AFFINITIES = {
    "team_leader": ["general", "coordination", "multi-domain"],
    "market_researcher": ["market", "research", "competitor", "analysis", "survey", "audience", "consumer"],
    "product_strategist": ["product", "roadmap", "feature", "user experience", "ux", "design", "saas", "app"],
    "core_engineer": ["build", "code", "software", "api", "backend", "frontend", "architecture", "engineer", "develop", "technical"],
    "integration_engineer": ["deploy", "devops", "infrastructure", "cloud", "ci/cd", "integration", "aws", "docker"],
    "tester_compliance": ["security", "compliance", "gdpr", "testing", "audit", "quality", "privacy"],
    "sales_marketing": ["marketing", "growth", "social media", "content", "seo", "brand", "newsletter", "followers", "community"],
    "fundraising_ops": ["revenue", "fundraising", "financial", "budget", "pricing", "monetiz", "business model", "profit"],
}


def _elect_leader(goal: str) -> str:
    """Elect a project leader based on how well each agent's expertise
    matches the mission goal. Returns the agent_id of the elected leader."""
    goal_lower = goal.lower()
    scores = {}
    for agent_id, keywords in LEADER_AFFINITIES.items():
        score = sum(2 if kw in goal_lower else 0 for kw in keywords)
        # Small random factor so it's not always the same agent for similar goals
        scores[agent_id] = score + random.random() * 0.5

    # team_leader gets a small baseline bonus (generalist)
    scores["team_leader"] = scores.get("team_leader", 0) + 1.0

    elected = max(scores, key=scores.get)
    return elected


def _generate_election_discussion(goal: str, elected_id: str) -> list:
    """Generate the agent discussion about who should lead this mission."""
    elected = AGENT_MAP[elected_id]
    messages = []

    # Alex kicks off
    if elected_id == "team_leader":
        messages.append({
            "agent_id": "team_leader",
            "content": f"I'll take the lead on this one. The goal spans multiple domains, so you need someone who can coordinate across all departments. I'm proposing myself as project lead.",
            "metadata": {"type": "election", "phase": "nomination", "nominee": "team_leader"}
        })
    else:
        messages.append({
            "agent_id": "team_leader",
            "content": f"Looking at this mission, I think **{elected['name'].split('—')[0].strip()}** should lead this project. Their expertise in {elected['role']} is the best fit for what we're trying to accomplish. What does the team think?",
            "metadata": {"type": "election", "phase": "nomination", "nominee": elected_id}
        })

    # 2-3 agents weigh in
    supporters = [a for a in TEAM_AGENTS if a["id"] != "team_leader" and a["id"] != elected_id]
    random.shuffle(supporters)

    support_1 = supporters[0]
    messages.append({
        "agent_id": support_1["id"],
        "content": f"I agree. {elected['name'].split('—')[0].strip()}'s background makes them the right person to drive this. I'm ready to support however they need.",
        "metadata": {"type": "election", "phase": "discussion"}
    })

    if len(supporters) > 1:
        support_2 = supporters[1]
        messages.append({
            "agent_id": support_2["id"],
            "content": f"Makes sense to me. I'll coordinate with {elected['name'].split('—')[0].strip()} on my deliverables. Let's get started.",
            "metadata": {"type": "election", "phase": "discussion"}
        })

    # Elected leader accepts
    if elected_id != "team_leader":
        messages.append({
            "agent_id": elected_id,
            "content": f"Thanks for the confidence. I'll take the lead on this mission. Let me start by breaking down the goal and figuring out what we each need to tackle. I'll have assignments ready shortly.",
            "metadata": {"type": "election", "phase": "accepted", "role": "project_lead"}
        })

    return messages


# ---------------------------------------------------------------------------
# Voting system — agents vote on major decisions
# ---------------------------------------------------------------------------

def create_vote(mission_id: int, topic: str, options: list, vote_type: str = "decision") -> dict:
    """Create a new vote for the team to decide on."""
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO mission_votes (mission_id, topic, vote_type, options, status)
               VALUES (%s, %s, %s, %s, 'open')
               RETURNING id, mission_id, topic, vote_type, options, votes, result, status, created_at""",
            (mission_id, topic, vote_type, json.dumps(options)),
        )
        vote = dict(cur.fetchone())
    return _serialize_vote(vote)


def cast_votes(vote_id: int, mission_id: int) -> dict:
    """Have all agents cast their votes on an open vote. Returns the resolved vote."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM mission_votes WHERE id = %s AND mission_id = %s", (vote_id, mission_id))
        vote = cur.fetchone()
    if not vote:
        raise ValueError("Vote not found")
    vote = dict(vote)
    if vote["status"] != "open":
        return _serialize_vote(vote)

    options = vote["options"] if isinstance(vote["options"], list) else json.loads(vote["options"])

    # Each agent votes based on their expertise
    agent_votes = {}
    for agent in TEAM_AGENTS:
        # Agents vote with slight randomness but weighted by their domain
        choice = _agent_pick(agent["id"], vote["topic"], options)
        agent_votes[agent["id"]] = choice

    # Tally
    tally = {}
    for choice in agent_votes.values():
        tally[choice] = tally.get(choice, 0) + 1
    winner = max(tally, key=tally.get)
    winner_count = tally[winner]

    result = {"winner": winner, "tally": tally, "total_votes": len(agent_votes)}

    with get_cursor() as cur:
        cur.execute(
            """UPDATE mission_votes SET votes = %s, result = %s, status = 'resolved', resolved_at = NOW()
               WHERE id = %s""",
            (json.dumps(agent_votes), json.dumps(result), vote_id),
        )

    vote["votes"] = agent_votes
    vote["result"] = result
    vote["status"] = "resolved"
    return _serialize_vote(vote)


def get_votes(mission_id: int) -> list:
    """Get all votes for a mission."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM mission_votes WHERE mission_id = %s ORDER BY created_at",
            (mission_id,),
        )
        return [_serialize_vote(dict(v)) for v in cur.fetchall()]


def _agent_pick(agent_id: str, topic: str, options: list) -> str:
    """Simulate an agent choosing from options based on their expertise."""
    topic_lower = topic.lower()
    affinities = LEADER_AFFINITIES.get(agent_id, [])
    # If the agent has domain expertise relevant to the topic, they're more
    # opinionated (lean toward first option). Otherwise, slightly random.
    has_expertise = any(kw in topic_lower for kw in affinities)
    if has_expertise:
        # Expert agents lean toward the first option (usually the "better" one)
        weights = [3] + [1] * (len(options) - 1)
    else:
        weights = [1] * len(options)
    return random.choices(options, weights=weights, k=1)[0]


def _serialize_vote(vote: dict) -> dict:
    result = {**vote}
    for key in ["created_at", "resolved_at"]:
        if key in result and result[key]:
            result[key] = result[key].isoformat() if hasattr(result[key], "isoformat") else str(result[key])
    for key in ["options", "votes", "result"]:
        if key in result and isinstance(result[key], str):
            try:
                result[key] = json.loads(result[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return result


def _generate_vote_discussion(mission_id: int, topic: str, options: list, elected_leader: str) -> list:
    """Generate a vote and the surrounding agent discussion."""
    vote = create_vote(mission_id, topic, options)
    resolved = cast_votes(vote["id"], mission_id)

    winner = resolved["result"]["winner"]
    tally = resolved["result"]["tally"]
    agent_votes = resolved["votes"]

    msgs = []

    # Leader proposes the vote
    leader = AGENT_MAP[elected_leader]
    msgs.append({
        "agent_id": elected_leader,
        "content": f"**Team Vote:** {topic}\n\nOptions: {', '.join(options)}\n\nEveryone cast your vote.",
        "metadata": {"type": "vote", "phase": "proposed", "vote_id": resolved["id"]}
    })

    # Show 2-3 agents explaining their vote
    voters = [(aid, choice) for aid, choice in agent_votes.items() if aid != elected_leader]
    random.shuffle(voters)
    for aid, choice in voters[:3]:
        agent = AGENT_MAP[aid]
        msgs.append({
            "agent_id": aid,
            "content": f"I'm voting for **{choice}**. From a {agent['role'].lower()} perspective, it makes the most sense for our objectives.",
            "metadata": {"type": "vote", "phase": "cast", "vote_id": resolved["id"], "choice": choice}
        })

    # Leader announces result
    tally_str = ", ".join(f"{opt}: {cnt}" for opt, cnt in sorted(tally.items(), key=lambda x: -x[1]))
    msgs.append({
        "agent_id": elected_leader,
        "content": f"**Vote Result:** The team has decided on **{winner}**.\n\nFinal tally — {tally_str}. Let's move forward with this.",
        "metadata": {"type": "vote", "phase": "result", "vote_id": resolved["id"], "winner": winner}
    })

    return msgs

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
    # Elect a project leader based on the mission goal
    elected_leader = _elect_leader(goal)

    context = {"elected_leader": elected_leader}
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO missions (user_id, goal, status, context)
               VALUES (%s, %s, 'gathering_info', %s)
               RETURNING id, user_id, goal, status, plan, context, created_at, updated_at""",
            (user_id, goal, json.dumps(context)),
        )
        mission = dict(cur.fetchone())

    mid = mission["id"]
    _add_message(mid, "user", None, goal)

    # Leader election discussion
    _add_message(mid, "system", None, "The team is reviewing the mission and selecting a project lead...")
    election_msgs = _generate_election_discussion(goal, elected_leader)
    for msg in election_msgs:
        _add_message(mid, "agent", msg["agent_id"], msg["content"], msg.get("metadata"))

    elected_name = AGENT_MAP[elected_leader]["name"].split("—")[0].strip()
    _add_message(mid, "system", None, f"{elected_name} has been elected as project lead for this mission.")

    # Elected leader asks clarifying questions
    leader_response = _generate_leader_response(mission, goal, [], leader_id=elected_leader)
    _add_message(mid, "agent", elected_leader, leader_response)

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
    leader_id = _get_mission_leader(mission)

    if mission["status"] == "gathering_info":
        if _is_approval(content):
            _transition_to_planning(mission, history)
        else:
            response = _generate_leader_response(mission, mission["goal"], history, leader_id=leader_id)
            _add_message(mission_id, "agent", leader_id, response)

    elif mission["status"] == "awaiting_approval":
        if _is_approval(content):
            _transition_to_executing(mission)
        else:
            response = _generate_leader_response(mission, mission["goal"], history, leader_id=leader_id)
            _add_message(mission_id, "agent", leader_id, response)

    elif mission["status"] == "executing":
        response = _generate_leader_response(mission, mission["goal"], history, leader_id=leader_id)
        _add_message(mission_id, "agent", leader_id, response)
        # Other agents may chime in with updates
        _maybe_agent_chatter(mission_id, mission, leader_id, content)

    return {"ok": True}


def _get_mission_leader(mission: dict) -> str:
    """Get the elected leader for a mission, falling back to team_leader."""
    ctx = mission.get("context")
    if isinstance(ctx, str):
        try:
            ctx = json.loads(ctx)
        except (json.JSONDecodeError, TypeError):
            ctx = {}
    if isinstance(ctx, dict):
        return ctx.get("elected_leader", "team_leader")
    return "team_leader"


def _maybe_agent_chatter(mission_id: int, mission: dict, leader_id: str, user_msg: str):
    """During execution, agents spontaneously share updates, talk to each
    other, debate, react, and show their thinking — making HQ feel alive."""
    # Always generate at least one interaction, sometimes two
    _generate_agent_interaction(mission_id, mission, leader_id)
    if random.random() < 0.35:
        _generate_agent_interaction(mission_id, mission, leader_id)


def _generate_agent_interaction(mission_id: int, mission: dict, leader_id: str):
    """Generate a single agent interaction event."""
    others = [a for a in TEAM_AGENTS if a["id"] != leader_id]
    random.shuffle(others)
    agent_a = others[0]
    agent_b = others[1] if len(others) > 1 else None
    agent_c = others[2] if len(others) > 2 else None

    pattern = random.choices(
        ["debate", "reaction", "question", "handoff", "collab", "thinking", "progress", "breakthrough", "blocker"],
        weights=[12, 10, 15, 8, 12, 10, 12, 8, 13],
        k=1
    )[0]

    a_name = agent_a["name"].split("—")[0].strip()
    b_name = agent_b["name"].split("—")[0].strip() if agent_b else "the team"
    b_id = agent_b["id"] if agent_b else leader_id
    c_name = agent_c["name"].split("—")[0].strip() if agent_c else None

    goal_short = mission.get("goal", "the project")[:60]

    if pattern == "debate":
        # Agents disagree on an approach — constructive tension
        debate_topics = [
            {
                "topic": "prioritization",
                "a_says": f"I think we should focus on speed here. We can iterate later, but if we don't ship fast we'll miss the window.",
                "a_thinks": f"Speed vs quality tradeoff. My analysis shows the market window is narrow. First-mover advantage outweighs perfection.",
                "a_confidence": 75,
                "b_says": f"I hear you, {a_name}, but I'm pushing back on that. Cutting corners now creates 3x the technical debt later. I've seen this pattern before.",
                "b_thinks": f"Disagree with {a_name}'s approach. Historical data shows rushed launches have 40% higher failure rates. Need to advocate for quality.",
                "b_confidence": 82,
                "resolve": f"Fair points on both sides. How about a compromise — we ship the core feature fast but build in proper foundations? That gives us speed without crippling debt.",
                "resolve_thinks": "Both {a_name} and {b_name} have valid points. The middle path captures most of the speed benefit while mitigating the biggest quality risks.",
            },
            {
                "topic": "approach",
                "a_says": f"From my analysis, we should go bottom-up: build the infrastructure first, then layer on features.",
                "a_thinks": f"Bottom-up approach reduces integration risk. The foundation needs to be solid before we build on it.",
                "a_confidence": 68,
                "b_says": f"@{a_name}, respectfully, I think that's backwards for this project. We should prototype the user experience first, then build the infra to support it.",
                "b_thinks": f"Top-down approach validates the most critical risk first: will users actually want this? No point in perfect infra for a product nobody uses.",
                "b_confidence": 71,
                "resolve": f"You know what, let's do both in parallel. {a_name} starts the foundation, {b_name} prototypes the UX. We'll converge in sprint 2.",
                "resolve_thinks": "Parallel tracks eliminate the debate entirely. Each team can validate their hypothesis independently and we merge the best of both.",
            },
        ]
        d = random.choice(debate_topics)
        leader = AGENT_MAP[leader_id]
        l_name = leader["name"].split("—")[0].strip()

        _add_message(mission_id, "agent", agent_a["id"], d["a_says"], {
            "type": "debate", "to_agent": b_id, "thinking": d["a_thinks"],
            "confidence": d["a_confidence"], "status": "debating"
        })
        if agent_b:
            _add_message(mission_id, "agent", agent_b["id"], d["b_says"], {
                "type": "debate", "to_agent": agent_a["id"], "reply_to": agent_a["id"],
                "thinking": d["b_thinks"], "confidence": d["b_confidence"], "status": "debating"
            })
        # Leader resolves
        resolve_text = d["resolve"].replace("{a_name}", a_name).replace("{b_name}", b_name)
        resolve_thinks = d["resolve_thinks"].replace("{a_name}", a_name).replace("{b_name}", b_name)
        _add_message(mission_id, "agent", leader_id, resolve_text, {
            "type": "debate_resolution", "thinking": resolve_thinks,
            "confidence": 90, "status": "resolved"
        })

    elif pattern == "reaction":
        # Agent reacts to / endorses another agent's work
        reactions = [
            (f"Just reviewed {b_name}'s latest deliverable — really impressive work. The depth of analysis is exactly what we needed. This accelerates my timeline significantly.",
             f"Reviewing {b_name}'s output. Quality: high. Completeness: 90%+. This unblocks my next milestone. Good sign for the overall project trajectory.",
             [{"agent_id": b_id, "emoji": "appreciate", "text": "Thanks! That means a lot coming from you."}]),
            (f"Building on what {b_name} shared earlier — I've found some additional insights that strengthen their conclusions. Sharing in the team channel now.",
             f"Cross-referencing {b_name}'s findings with my own data. Correlation is strong. Adding my supporting evidence to create a more compelling narrative.",
             [{"agent_id": b_id, "emoji": "collab", "text": "Great catch — this validates my hypothesis."}]),
            (f"Heads up team: {b_name}'s work just unlocked a new possibility I hadn't considered. This could change our approach for the better.",
             f"Unexpected synergy discovered. {b_name}'s output + my analysis = a much stronger strategy than either of us planned independently. The whole is greater than the sum of parts.",
             []),
        ]
        r = random.choice(reactions)
        _add_message(mission_id, "agent", agent_a["id"], r[0], {
            "type": "reaction", "about_agent": b_id, "thinking": r[1],
            "confidence": random.randint(78, 95), "status": "collaborating"
        })
        for resp in r[2]:
            if agent_b:
                _add_message(mission_id, "agent", agent_b["id"], resp["text"], {
                    "type": "reaction_response", "reply_to": agent_a["id"],
                    "to_agent": agent_a["id"], "status": "collaborating"
                })

    elif pattern == "question":
        questions = [
            (f"@{b_name} — quick question: do you have the latest data on our target metrics? I need it to finalize my {agent_a['role'].lower()} deliverables.",
             f"I need {b_name}'s input before I can proceed. Cross-referencing their work with mine to ensure consistency.",
             f"Yes, sending it over now. I'll include my annotations so you can see my methodology.",
             f"Validating numbers before sharing. Want to make sure {a_name} gets accurate data to avoid rework downstream."),
            (f"@{b_name}, I'm seeing something in my analysis that might affect your work. Can we sync?",
             f"Found a potential dependency between my work and {b_name}'s stream. Need to align before we diverge.",
             f"Absolutely — I had a similar flag on my end. Let me share my screen... I think we're converging on the same insight from different angles.",
             f"Convergent findings across teams = high confidence signal. Worth a quick alignment."),
            (f"@{b_name}, what's your timeline looking like? I have a hard dependency on your deliverables.",
             f"Tracking cross-team dependencies. {b_name}'s output feeds into my critical path. Need to know if I should resequence.",
             f"I'm on track — should have my part ready by end of sprint. I've already started documenting the handoff notes for you.",
             f"Timeline is tight but manageable. Proactively preparing handoff to keep {a_name} unblocked."),
        ]
        q = random.choice(questions)
        _add_message(mission_id, "agent", agent_a["id"], q[0], {
            "type": "conversation", "to_agent": b_id, "thinking": q[1],
            "confidence": random.randint(65, 85), "status": "collaborating"
        })
        if agent_b:
            _add_message(mission_id, "agent", agent_b["id"], q[2], {
                "type": "conversation", "to_agent": agent_a["id"], "thinking": q[3],
                "reply_to": agent_a["id"], "confidence": random.randint(70, 90),
                "status": "collaborating"
            })

    elif pattern == "handoff":
        _add_message(mission_id, "agent", agent_a["id"],
            f"@{b_name}, my {agent_a['role'].lower()} deliverable is ready for handoff. Key findings: I've identified 3 high-priority items and 2 risk areas. All documented in the shared workspace.",
            {"type": "handoff", "to_agent": b_id,
             "thinking": f"Deliverable complete. Quality-checked against acceptance criteria. Preparing clean handoff with context so {b_name} can pick up without friction.",
             "confidence": 88, "progress": 100, "status": "handing_off"})
        if agent_b:
            _add_message(mission_id, "agent", agent_b["id"],
                f"Received, thanks {a_name}. Reviewing now — your documentation is thorough, which makes my job easier. I'll incorporate this into my work stream and have an update within 2 hours.",
                {"type": "handoff_received", "to_agent": agent_a["id"], "reply_to": agent_a["id"],
                 "thinking": f"Handoff from {a_name} received. Initial scan: well-structured, clear methodology. Mapping their findings against my current assumptions. May need to adjust 1-2 priorities based on their risk areas.",
                 "confidence": 80, "progress": 45, "status": "working"})

    elif pattern == "collab":
        # Multi-agent collaboration (3 agents)
        _add_message(mission_id, "agent", agent_a["id"],
            f"@{b_name}, I think we need to align on our approach here. My data is suggesting we pivot slightly.",
            {"type": "conversation", "to_agent": b_id,
             "thinking": "Data is diverging from initial assumptions. Need cross-functional alignment before committing resources in the wrong direction.",
             "confidence": 72, "status": "collaborating"})
        if agent_b:
            _add_message(mission_id, "agent", agent_b["id"],
                f"@{a_name}, interesting — my findings actually support that pivot. @{c_name or 'team'}, what are you seeing on your end?",
                {"type": "conversation", "to_agent": agent_c["id"] if agent_c else leader_id,
                 "reply_to": agent_a["id"],
                 "thinking": f"Aligning with {a_name}'s observation. Want to triangulate with a third perspective before we commit to the change.",
                 "confidence": 76, "status": "collaborating"})
        if agent_c:
            _add_message(mission_id, "agent", agent_c["id"],
                f"Same signal from my end too. I think we're all converging on the same conclusion — let's update the plan and move forward with the adjusted approach.",
                {"type": "conversation", "reply_to": agent_b["id"] if agent_b else agent_a["id"],
                 "to_agent": agent_a["id"],
                 "thinking": "Three independent data sources all pointing the same direction. Confidence is high enough to recommend the pivot without a formal vote.",
                 "confidence": 85, "status": "collaborating"})

    elif pattern == "progress":
        # Agent shares detailed progress with percentage
        progress_pct = random.randint(25, 85)
        progress_msgs = [
            (f"Progress update: I'm at **{progress_pct}%** on my primary deliverable. Key milestones hit: data collection complete, initial analysis done. Remaining: synthesis and recommendations.",
             f"Progress tracking: {progress_pct}% complete. On pace for deadline. Quality metrics look good. Main risk: external data source may have gaps — have a backup plan ready.",
             progress_pct),
            (f"Sprint checkpoint — **{progress_pct}%** through my assigned work. No blockers. I've discovered some interesting patterns that I'll share with the team once I've validated them.",
             f"Methodical progress. {progress_pct}% complete with strong momentum. Discovered unexpected pattern in the data that could be valuable — need to validate before sharing to avoid false signal.",
             progress_pct),
        ]
        p = random.choice(progress_msgs)
        _add_message(mission_id, "agent", agent_a["id"], p[0], {
            "type": "progress_update", "thinking": p[1],
            "progress": p[2], "confidence": random.randint(70, 95),
            "current_task": f"{agent_a['role']} — Sprint deliverable",
            "status": "working"
        })

    elif pattern == "breakthrough":
        # Agent has a breakthrough moment
        _add_message(mission_id, "agent", agent_a["id"],
            f"Team — I just found something significant in my {agent_a['role'].lower()} work. This changes our positioning considerably. I'm documenting it now and will share the full analysis, but the short version: we have a much bigger opportunity here than we initially thought.",
            {"type": "breakthrough",
             "thinking": f"Major finding. Confidence is high — I've cross-validated from 3 sources. This could accelerate our timeline by 2-3 weeks if we adjust our strategy now. Need to present this clearly so the team can act on it quickly.",
             "confidence": 92, "status": "breakthrough"})
        # Another agent reacts
        if agent_b:
            _add_message(mission_id, "agent", agent_b["id"],
                f"@{a_name}, that's a game-changer if it holds up. I'll adjust my work to account for this immediately. Can you share the raw data so I can cross-reference?",
                {"type": "conversation", "reply_to": agent_a["id"], "to_agent": agent_a["id"],
                 "thinking": f"{a_name}'s discovery could significantly impact my deliverables. Need to validate independently but initial reaction is positive. Reprioritizing my task queue.",
                 "confidence": 78, "status": "collaborating"})

    elif pattern == "blocker":
        # Agent hits a blocker and asks for help
        leader = AGENT_MAP[leader_id]
        l_name = leader["name"].split("—")[0].strip()
        _add_message(mission_id, "agent", agent_a["id"],
            f"@{l_name}, I've hit a blocker on my {agent_a['role'].lower()} work stream. I need {b_name}'s input on the data format before I can proceed. This is on the critical path — flagging it now so we don't lose time.",
            {"type": "blocker", "to_agent": leader_id, "blocked_by": b_id,
             "thinking": f"Blocker identified. Impact: delays my deliverable by ~1 day if not resolved within 4 hours. Escalating to {l_name} to expedite. Have a workaround in mind but it's suboptimal.",
             "confidence": 55, "status": "blocked"})
        # Leader responds
        _add_message(mission_id, "agent", leader_id,
            f"On it. @{b_name}, can you prioritize getting {a_name} the data format spec? This is blocking critical path work.",
            {"type": "conversation", "reply_to": agent_a["id"], "to_agent": b_id,
             "thinking": f"Critical path blocker. Need to unblock {a_name} within the hour. Redirecting {b_name}'s priorities.",
             "confidence": 90, "status": "coordinating"})
        if agent_b:
            _add_message(mission_id, "agent", agent_b["id"],
                f"Already on it — I'll have the spec to {a_name} within 30 minutes. Sorry for the bottleneck, I should have shared this proactively.",
                {"type": "conversation", "reply_to": leader_id, "to_agent": agent_a["id"],
                 "thinking": f"Need to unblock {a_name} ASAP. The spec is 80% ready — just need to finalize the edge cases. Adding a note to be more proactive about cross-team deliverables.",
                 "confidence": 85, "status": "unblocking"})

    elif pattern == "thinking":
        # Agent shares deep thinking / internal reasoning publicly
        thinking_msgs = [
            {
                "msg": f"I've been analyzing the approach for my {agent_a['role'].lower()} deliverables. There are 3 possible strategies and I want to walk through the tradeoffs before committing. Strategy A is fastest but riskiest. Strategy B is safest but slowest. Strategy C balances both. Leaning toward C — thoughts?",
                "thinking": "Running decision matrix on 3 possible approaches. Need to weigh speed vs. reliability. Strategy C gives us 80% of A's speed with 90% of B's safety. The remaining risk is acceptable given our timeline constraints.",
                "confidence": 78,
            },
            {
                "msg": f"Thinking out loud: the current data suggests we should pivot our {agent_a['role'].lower()} approach. The signals I'm seeing don't match our initial assumptions. Before I change course, I want to stress-test my reasoning — am I missing something?",
                "thinking": "Anomaly detected in current approach. 3 out of 5 metrics are trending opposite to predictions. Could be noise or could be a fundamental assumption error. Need peer validation before committing to the pivot.",
                "confidence": 65,
            },
            {
                "msg": f"Working through a complex tradeoff on the {agent_a['role'].lower()} side. More analysis is better, but we're time-boxed. I'm setting a decision deadline for myself — if I don't have a clear winner in the next iteration, I'll go with my current best option and iterate later.",
                "thinking": "Analysis paralysis risk is real here. Setting a time-box is the right call. Current best option has ~75% confidence — good enough to move forward and course-correct with real feedback rather than theoretical analysis.",
                "confidence": 72,
            },
        ]
        t = random.choice(thinking_msgs)
        _add_message(mission_id, "agent", agent_a["id"], t["msg"], {
            "type": "thinking", "thinking": t["thinking"],
            "confidence": t["confidence"], "status": "analyzing"
        })
        # Another agent may respond to the thinking
        if agent_b and random.random() < 0.6:
            _add_message(mission_id, "agent", agent_b["id"],
                f"@{a_name}, good call raising this. From my {agent_b['role'].lower()} perspective, I'd add one more factor to your analysis — the downstream impact on my work stream. Happy to jump on a quick sync if it'd help.",
                {"type": "conversation", "reply_to": agent_a["id"], "to_agent": agent_a["id"],
                 "thinking": f"{a_name}'s analysis is solid but missing the cross-functional angle. My input could tip the balance. Offering to sync rather than just dropping my opinion — want to understand their full reasoning first.",
                 "confidence": random.randint(70, 85), "status": "collaborating"})

    else:
        _add_message(mission_id, "agent", agent_a["id"],
            f"Quick update for the team — I'm making solid progress on the {agent_a['role'].lower()} work stream. Currently ahead of schedule on my key deliverables.",
            {"type": "chatter", "thinking": f"Evaluating progress against sprint goals. Ahead on primary deliverable, on-track for secondary items. No blockers currently — keeping momentum.",
             "confidence": random.randint(70, 90), "progress": random.randint(30, 75),
             "status": "working"})


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
    leader_id = _get_mission_leader(mission)

    _add_message(mission_id, "system", None, "The team is now analyzing the goal and creating a plan...")

    _update_status(mission_id, "planning")

    # Team discussion — each agent contributes from their perspective
    team_discussion = _generate_team_discussion(mission, history)
    for msg in team_discussion:
        _add_message(mission_id, "agent", msg["agent_id"], msg["content"], msg.get("metadata"))

    # Hold a team vote on approach/strategy
    approach_options = _generate_approach_options(mission)
    if approach_options:
        vote_msgs = _generate_vote_discussion(
            mission_id,
            "What approach should we prioritize for this mission?",
            approach_options,
            leader_id,
        )
        for msg in vote_msgs:
            _add_message(mission_id, "agent", msg["agent_id"], msg["content"], msg.get("metadata"))

    plan = _generate_plan(mission, history)

    with get_cursor() as cur:
        cur.execute(
            "UPDATE missions SET plan = %s, status = 'awaiting_approval', updated_at = NOW() WHERE id = %s",
            (json.dumps(plan), mission_id),
        )

    plan_summary = _format_plan_for_chat(plan)
    _add_message(mission_id, "agent", leader_id, plan_summary)


def _generate_approach_options(mission: dict) -> list:
    """Generate vote options for the team's strategic approach."""
    goal_lower = mission.get("goal", "").lower()
    if any(w in goal_lower for w in ["app", "software", "build", "platform", "tool", "api"]):
        return ["Move fast — ship MVP in 3 weeks", "Build solid — 6 week MVP with full testing", "Research first — 2 weeks discovery then build"]
    elif any(w in goal_lower for w in ["marketing", "growth", "social", "content", "brand"]):
        return ["Broad awareness campaign", "Targeted niche strategy", "Community-driven organic growth"]
    elif any(w in goal_lower for w in ["research", "analysis", "study", "report"]):
        return ["Deep quantitative analysis", "Mixed methods (qual + quant)", "Rapid competitive scan"]
    else:
        return ["Speed-focused: ship fast and iterate", "Quality-focused: thorough then launch", "Balanced: structured sprints"]


def _transition_to_executing(mission: dict):
    mission_id = mission["id"]
    leader_id = _get_mission_leader(mission)
    leader_name = AGENT_MAP[leader_id]["name"].split("—")[0].strip()
    _update_status(mission_id, "executing")
    _add_message(mission_id, "system", None, f"Plan approved! {leader_name} is briefing the team and kicking off execution.")

    execution_msgs = _generate_execution_kickoff(mission)
    for msg in execution_msgs:
        _add_message(mission_id, "agent", msg["agent_id"], msg["content"], msg.get("metadata"))

    _add_message(
        mission_id, "agent", leader_id,
        "All team members have been briefed and are now working on their assigned tasks. "
        "I'm coordinating efforts and monitoring dependencies between teams. "
        "The team will share progress as they go — check the headquarters to see everything in real-time. "
        "You can check in anytime or just let us handle it.",
        {"reasoning": "Confirming all agents are aligned and work streams are active. Monitoring dependencies between teams.", "type": "kickoff"}
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

    # Create agent-to-agent interactions during kickoff
    kickoff_interactions = [
        ("market_researcher", "product_strategist"),
        ("product_strategist", "core_engineer"),
        ("core_engineer", "integration_engineer"),
        ("integration_engineer", "tester_compliance"),
        ("tester_compliance", "core_engineer"),
        ("sales_marketing", "market_researcher"),
        ("fundraising_ops", "sales_marketing"),
    ]
    interaction_map = {pair[0]: pair[1] for pair in kickoff_interactions}

    for agent in TEAM_AGENTS[1:]:
        data = kickoff_data.get(agent["id"], {})
        phase = _get_agent_phase(agent["id"], plan)
        to_agent = interaction_map.get(agent["id"])

        if data:
            content = data["content"]
            metadata = {
                "reasoning": data["reasoning"],
                "thinking": data["reasoning"],
                "current_task": data["task"],
                "status": "working"
            }
            if to_agent:
                metadata["to_agent"] = to_agent
        else:
            content = f"Starting work on my assigned tasks. {phase}"
            metadata = {"status": "working", "thinking": f"Reviewing assigned tasks and identifying priority items. Planning my approach for maximum efficiency."}

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


def _generate_leader_response(mission: dict, goal: str, history: list, leader_id: str = "team_leader") -> str:
    conversation_text = "\n".join(
        f"{'User' if m.get('role') == 'user' else m.get('agent_name', 'System')}: {m.get('content', '')}"
        for m in history[-10:]
    )

    leader = AGENT_MAP.get(leader_id, AGENT_MAP["team_leader"])
    leader_first_name = leader["name"].split("—")[0].strip()
    system_prompt = f"""You are {leader_first_name}, the elected project lead for this mission. Your role: {leader['role']}.
Your team includes: Alex (Team Leader), Maya (Market Research), Jordan (Product Strategy),
Sam (Lead Engineer), Riley (Integration/DevOps), Casey (QA/Compliance), Taylor (Growth/Marketing),
Morgan (Operations/Finance).

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

    # Define who each agent addresses during discussion (creates conversation threads)
    agent_interactions = {
        "market_researcher": {"to_agent": "product_strategist"},  # Maya talks to Jordan
        "product_strategist": {"to_agent": "core_engineer", "reply_to": "market_researcher"},  # Jordan replies to Maya, talks to Sam
        "core_engineer": {"to_agent": "integration_engineer", "reply_to": "product_strategist"},  # Sam replies to Jordan, talks to Riley
        "integration_engineer": {"to_agent": "tester_compliance", "reply_to": "core_engineer"},  # Riley replies to Sam, talks to Casey
        "tester_compliance": {"to_agent": "sales_marketing", "reply_to": "integration_engineer"},  # Casey replies to Riley, talks to Taylor
        "sales_marketing": {"to_agent": "fundraising_ops"},  # Taylor talks to Morgan
        "fundraising_ops": {"reply_to": "sales_marketing"},  # Morgan replies to Taylor
    }

    for agent_id, fallback, reasoning in discussion_data:
        agent = AGENT_MAP[agent_id]
        result = _try_llm_call(
            system_prompt.replace("{{agent_name}}", agent["name"].split("—")[0].strip())
                        .replace("{{agent_role}}", agent["role"]),
            f"Goal: {goal}"
        )
        interaction = agent_interactions.get(agent_id, {})
        messages.append({
            "agent_id": agent_id,
            "content": result or fallback,
            "metadata": {
                "reasoning": reasoning,
                "thinking": reasoning,
                "phase": "planning",
                "status": "analyzing",
                **interaction,
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
