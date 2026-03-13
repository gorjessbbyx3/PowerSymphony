"""Self-improvement tool functions for workflow agents.

These functions enable agents to:
1. Score their own output using an LLM judge
2. Critique and iteratively refine their responses
3. Evolve their system prompts based on accumulated experience
4. Learn from past runs and apply cross-run knowledge

Usage in a YAML node:
  tools:
    - name: score_my_output
    - name: run_iterative_refinement
    - name: improve_my_prompt
    - name: save_performance
    - name: get_past_runs
    - name: get_best_prompt
    - name: compare_outputs
"""

import json
import os
import time
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Internal: LLM judge helper
# ---------------------------------------------------------------------------

def _call_judge(prompt: str) -> str:
    """Call an LLM with a judge prompt and return its response text."""
    import openai

    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("JUDGE_MODEL", "gpt-4o-mini")

    if not api_key:
        return json.dumps({"error": "No API_KEY set for LLM judge calls."})

    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _parse_json_safe(text: str) -> Dict[str, Any]:
    """Try to parse JSON from LLM output, stripping markdown fences if needed."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        stripped = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {"raw": stripped}


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def score_my_output(task: str, output: str, criteria: str = "") -> str:
    """
    Score an agent's output on a 1–10 quality scale using an impartial LLM judge.
    Returns a JSON object with 'score', 'strengths', 'critique', and 'suggestions'.

    Args:
        task (str): The original task or instruction given to the agent.
        output (str): The agent's output to evaluate.
        criteria (str): Optional comma-separated quality criteria to focus on,
                        e.g. 'accuracy,clarity,completeness,conciseness'.

    Returns:
        str: JSON with keys: score (float 1–10), strengths (str), critique (str),
             suggestions (str), grade (letter A–F).
    """
    criteria_line = f"\nEvaluation criteria: {criteria}" if criteria else ""
    prompt = f"""You are an impartial quality judge. Evaluate the following agent output.{criteria_line}

TASK:
{task}

AGENT OUTPUT:
{output}

Return ONLY valid JSON in this exact format:
{{
  "score": <number from 1.0 to 10.0>,
  "grade": "<A/B/C/D/F>",
  "strengths": "<one sentence about what was done well>",
  "critique": "<one to two sentences about specific weaknesses>",
  "suggestions": "<one to two concrete improvement suggestions>"
}}"""

    raw = _call_judge(prompt)
    result = _parse_json_safe(raw)
    if "error" in result:
        return json.dumps(result)

    # Normalize score
    try:
        result["score"] = float(result.get("score", 5.0))
    except (TypeError, ValueError):
        result["score"] = 5.0

    return json.dumps(result, ensure_ascii=False, indent=2)


def run_iterative_refinement(task: str, initial_output: str,
                             max_iterations: int = 3,
                             score_threshold: float = 8.0) -> str:
    """
    Iteratively refine an output until its quality score reaches a threshold.
    Each iteration scores the current output, then rewrites it based on the critique.

    Args:
        task (str): The original task or instruction.
        initial_output (str): The first draft output to start refining.
        max_iterations (int): Maximum refinement cycles (1–5). Defaults to 3.
        score_threshold (float): Stop early when score >= this value (1–10). Defaults to 8.0.

    Returns:
        str: JSON with keys: final_output, final_score, iterations (list of
             {iteration, score, critique, output}).
    """
    max_iterations = max(1, min(int(max_iterations), 5))
    score_threshold = max(1.0, min(float(score_threshold), 10.0))

    current_output = initial_output
    history = []

    for i in range(1, max_iterations + 1):
        # Score current output
        score_json = json.loads(score_my_output(task, current_output))
        if "error" in score_json:
            break
        score = float(score_json.get("score", 5.0))
        critique = score_json.get("critique", "")
        suggestions = score_json.get("suggestions", "")

        history.append({
            "iteration": i,
            "score": score,
            "critique": critique,
            "suggestions": suggestions,
            "output": current_output[:2000],  # truncate for storage
        })

        if score >= score_threshold:
            break

        if i < max_iterations:
            # Rewrite based on critique
            refine_prompt = f"""You are revising an agent's response based on a quality critique.

ORIGINAL TASK:
{task}

CURRENT RESPONSE (score {score}/10):
{current_output}

CRITIQUE:
{critique}

IMPROVEMENT SUGGESTIONS:
{suggestions}

Write an improved version that directly addresses the critique. Output ONLY the improved response, with no explanation or preamble."""
            current_output = _call_judge(refine_prompt)
            if not current_output or current_output.startswith('{"error"'):
                break

    return json.dumps({
        "final_output": current_output,
        "final_score": history[-1]["score"] if history else 0.0,
        "iterations": history,
        "converged": len(history) > 0 and history[-1]["score"] >= score_threshold,
    }, ensure_ascii=False, indent=2)


def compare_outputs(task: str, output_a: str, output_b: str) -> str:
    """
    Compare two agent outputs for the same task and decide which is better.

    Args:
        task (str): The task both outputs are responding to.
        output_a (str): First output to compare.
        output_b (str): Second output to compare.

    Returns:
        str: JSON with keys: winner ('A' or 'B'), score_a, score_b, reasoning.
    """
    prompt = f"""You are an expert evaluator comparing two responses to the same task.

TASK: {task}

RESPONSE A:
{output_a}

RESPONSE B:
{output_b}

Evaluate both responses. Return ONLY valid JSON:
{{
  "score_a": <1.0–10.0>,
  "score_b": <1.0–10.0>,
  "winner": "<A or B>",
  "reasoning": "<one to two sentences explaining the choice>"
}}"""

    raw = _call_judge(prompt)
    result = _parse_json_safe(raw)
    return json.dumps(result, ensure_ascii=False, indent=2)


def improve_my_prompt(agent_id: str, current_role: str,
                      task_examples: str, critique_examples: str) -> str:
    """
    Generate an improved system prompt for an agent based on past critique patterns.
    The improved prompt is automatically saved as a new prompt version.

    Args:
        agent_id (str): Identifier for the agent (used to persist prompt versions).
        current_role (str): The agent's current system prompt / role description.
        task_examples (str): 1–3 representative task descriptions the agent handles.
        critique_examples (str): 1–3 critique patterns from recent run evaluations.

    Returns:
        str: JSON with keys: new_prompt, version, improvements_made.
    """
    from utils.agent_performance_store import get_store

    prompt = f"""You are a prompt engineer improving an AI agent's system prompt.

CURRENT SYSTEM PROMPT:
{current_role}

REPRESENTATIVE TASKS:
{task_examples}

RECURRING CRITIQUE PATTERNS:
{critique_examples}

Write an improved system prompt that:
1. Preserves what already works well
2. Directly addresses each critique pattern
3. Is clear, specific, and actionable
4. Is written in the same style as the original

Return ONLY valid JSON:
{{
  "new_prompt": "<the improved system prompt>",
  "improvements_made": "<bulleted list of specific changes made>"
}}"""

    raw = _call_judge(prompt)
    result = _parse_json_safe(raw)
    if "error" in result or "new_prompt" not in result:
        return json.dumps({"error": "Failed to generate improved prompt", "raw": raw[:500]})

    new_prompt = result["new_prompt"]
    rationale = result.get("improvements_made", "")
    store = get_store(agent_id)
    version = store.add_prompt_version(new_prompt, rationale=rationale)

    return json.dumps({
        "new_prompt": new_prompt,
        "version": version,
        "improvements_made": rationale,
        "agent_id": agent_id,
    }, ensure_ascii=False, indent=2)


def save_performance(agent_id: str, task: str, output: str,
                     score: float, critique: str = "",
                     strengths: str = "", prompt_version: int = 0) -> str:
    """
    Save a completed run's performance data to the agent's persistent history.
    Call this after scoring an output to build the cross-run learning record.

    Args:
        agent_id (str): The agent's identifier.
        task (str): The task that was executed.
        output (str): The agent's final output.
        score (float): The quality score (1–10).
        critique (str): Any critique or weaknesses identified.
        strengths (str): Any strengths identified.
        prompt_version (int): Which prompt version was active (0 = initial/unknown).

    Returns:
        str: JSON with keys: ok, run_id, total_runs, avg_score.
    """
    from utils.agent_performance_store import get_store, RunRecord

    store = get_store(agent_id)
    record = RunRecord(
        agent_id=agent_id,
        task=task,
        output=output[:4000],  # Trim for storage
        score=float(score),
        critique=critique,
        strengths=strengths,
        prompt_version=int(prompt_version),
        timestamp=time.time(),
    )
    store.save_run(record)
    stats = store.get_stats()
    return json.dumps({
        "ok": True,
        "run_id": record.run_id,
        "total_runs": stats["total_runs"],
        "avg_score": stats["avg_score"],
    })


def get_past_runs(agent_id: str, n: int = 5) -> str:
    """
    Retrieve the N most recent scored run records for an agent.
    Use this to understand patterns in past performance before starting a new task.

    Args:
        agent_id (str): The agent's identifier.
        n (int): Number of recent runs to return (1–20). Defaults to 5.

    Returns:
        str: JSON array of run records with task, output_snippet, score, critique,
             strengths, and timestamp fields.
    """
    from utils.agent_performance_store import get_store

    n = max(1, min(int(n), 20))
    store = get_store(agent_id)
    runs = store.get_recent_runs(n)
    summary = []
    for r in runs:
        summary.append({
            "run_id": r.run_id,
            "timestamp": r.timestamp,
            "score": r.score,
            "task": r.task[:300],
            "output_snippet": r.output[:400],
            "critique": r.critique,
            "strengths": r.strengths,
            "prompt_version": r.prompt_version,
        })
    return json.dumps(summary, ensure_ascii=False, indent=2)


def get_best_prompt(agent_id: str) -> str:
    """
    Get the best-performing evolved prompt for an agent.
    Returns the prompt version with the highest average quality score, or
    a message if no versions have been saved yet.

    Args:
        agent_id (str): The agent's identifier.

    Returns:
        str: JSON with keys: prompt (str or null), version, avg_score, total_versions.
    """
    from utils.agent_performance_store import get_store

    store = get_store(agent_id)
    best_prompt = store.get_best_prompt()
    all_versions = store.get_all_prompt_versions()
    best_version = None
    best_avg = 0.0

    for pv in all_versions:
        if pv.get("avg_score", 0.0) >= best_avg:
            best_avg = pv["avg_score"]
            best_version = pv.get("version", 0)

    return json.dumps({
        "agent_id": agent_id,
        "prompt": best_prompt,
        "version": best_version,
        "avg_score": round(best_avg, 2),
        "total_versions": len(all_versions),
    }, ensure_ascii=False, indent=2)
