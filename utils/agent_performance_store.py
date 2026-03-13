"""Persistent per-agent performance store.

Each agent gets its own JSONL run log and a JSON summary file under
WareHouse/.agent_performance/. This is the single source of truth for
cross-run learning and prompt evolution.
"""

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PERF_DIR = Path(os.environ.get("DEVALL_PERF_DIR", "WareHouse/.agent_performance"))
_PERF_DIR.mkdir(parents=True, exist_ok=True)

_MAX_RUNS_IN_MEMORY = int(os.environ.get("DEVALL_MAX_PERF_RUNS", "500"))
_LOCK = Lock()


@dataclass
class RunRecord:
    """A single agent execution with its quality score."""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)
    task: str = ""
    output: str = ""
    score: float = 0.0           # 1–10 quality score from LLM judge
    critique: str = ""           # What could be better
    strengths: str = ""          # What was done well
    prompt_version: int = 0      # Which prompt version was active
    duration_s: float = 0.0      # Execution time
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PromptVersion:
    """A versioned system prompt with performance data."""
    version: int = 0
    prompt: str = ""
    created_at: float = field(default_factory=time.time)
    run_count: int = 0
    total_score: float = 0.0
    avg_score: float = 0.0
    rationale: str = ""          # Why this prompt was created

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PromptVersion":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def record_score(self, score: float) -> None:
        self.run_count += 1
        self.total_score += score
        self.avg_score = self.total_score / self.run_count


class AgentPerformanceStore:
    """Load, save, and query the performance history for one agent."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._runs_path = _PERF_DIR / f"{agent_id}.jsonl"
        self._meta_path = _PERF_DIR / f"{agent_id}_meta.json"
        self._meta: Dict[str, Any] = self._load_meta()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_meta(self) -> Dict[str, Any]:
        if self._meta_path.exists():
            try:
                return json.loads(self._meta_path.read_text())
            except Exception:
                pass
        return {
            "agent_id": self.agent_id,
            "prompt_versions": [],
            "current_prompt_version": 0,
            "total_runs": 0,
            "total_score": 0.0,
            "best_score": 0.0,
            "created_at": time.time(),
        }

    def _save_meta(self) -> None:
        try:
            self._meta_path.write_text(json.dumps(self._meta, indent=2))
        except Exception as exc:
            logger.warning("Failed to save agent meta for %s: %s", self.agent_id, exc)

    # ------------------------------------------------------------------
    # Runs
    # ------------------------------------------------------------------

    def save_run(self, record: RunRecord) -> None:
        """Append a run record to disk and update meta stats."""
        with _LOCK:
            try:
                with self._runs_path.open("a") as f:
                    f.write(json.dumps(record.to_dict()) + "\n")
            except Exception as exc:
                logger.warning("Failed to write run for %s: %s", self.agent_id, exc)

            self._meta["total_runs"] = self._meta.get("total_runs", 0) + 1
            self._meta["total_score"] = self._meta.get("total_score", 0.0) + record.score
            if record.score > self._meta.get("best_score", 0.0):
                self._meta["best_score"] = record.score

            # Update score on current prompt version
            versions = self._meta.get("prompt_versions", [])
            for pv in versions:
                if pv.get("version") == record.prompt_version:
                    pv["run_count"] = pv.get("run_count", 0) + 1
                    pv["total_score"] = pv.get("total_score", 0.0) + record.score
                    pv["avg_score"] = pv["total_score"] / pv["run_count"]
                    break
            self._save_meta()

    def get_recent_runs(self, n: int = 10) -> List[RunRecord]:
        """Return the N most recent run records (newest first)."""
        if not self._runs_path.exists():
            return []
        try:
            lines = self._runs_path.read_text().splitlines()
            records = []
            for line in reversed(lines):
                line = line.strip()
                if line:
                    try:
                        records.append(RunRecord.from_dict(json.loads(line)))
                    except Exception:
                        pass
                if len(records) >= n:
                    break
            return records
        except Exception as exc:
            logger.warning("Failed to read runs for %s: %s", self.agent_id, exc)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics from the run history."""
        total = self._meta.get("total_runs", 0)
        total_score = self._meta.get("total_score", 0.0)
        return {
            "agent_id": self.agent_id,
            "total_runs": total,
            "avg_score": round(total_score / total, 2) if total else 0.0,
            "best_score": self._meta.get("best_score", 0.0),
            "current_prompt_version": self._meta.get("current_prompt_version", 0),
            "prompt_versions_count": len(self._meta.get("prompt_versions", [])),
        }

    def get_performance_trend(self, n: int = 10) -> Dict[str, Any]:
        """Return last-N scores and a trend label (improving/declining/stable)."""
        runs = self.get_recent_runs(n)
        scores = [r.score for r in runs]
        scores_oldest_first = list(reversed(scores))
        trend = "stable"
        if len(scores_oldest_first) >= 3:
            first_half = sum(scores_oldest_first[:len(scores_oldest_first)//2]) / max(1, len(scores_oldest_first)//2)
            second_half = sum(scores_oldest_first[len(scores_oldest_first)//2:]) / max(1, len(scores_oldest_first) - len(scores_oldest_first)//2)
            if second_half - first_half > 0.5:
                trend = "improving"
            elif first_half - second_half > 0.5:
                trend = "declining"
        return {
            "scores": scores_oldest_first,
            "trend": trend,
            "recent_avg": round(sum(scores) / len(scores), 2) if scores else 0.0,
        }

    # ------------------------------------------------------------------
    # Prompt evolution
    # ------------------------------------------------------------------

    def add_prompt_version(self, prompt: str, rationale: str = "") -> int:
        """Register a new prompt version and return its version number."""
        with _LOCK:
            versions = self._meta.setdefault("prompt_versions", [])
            version_num = (max(v.get("version", 0) for v in versions) + 1) if versions else 1
            versions.append(PromptVersion(
                version=version_num, prompt=prompt,
                rationale=rationale,
            ).to_dict())
            self._meta["current_prompt_version"] = version_num
            self._save_meta()
            return version_num

    def get_current_prompt(self) -> Optional[str]:
        """Return the currently active (latest) prompt, or None if none saved."""
        versions = self._meta.get("prompt_versions", [])
        if not versions:
            return None
        current_v = self._meta.get("current_prompt_version", 0)
        for pv in reversed(versions):
            if pv.get("version") == current_v:
                return pv.get("prompt")
        return versions[-1].get("prompt") if versions else None

    def get_best_prompt(self) -> Optional[str]:
        """Return the prompt version that has the highest average score."""
        versions = self._meta.get("prompt_versions", [])
        if not versions:
            return None
        scored = [v for v in versions if v.get("run_count", 0) > 0]
        if not scored:
            return versions[-1].get("prompt")
        best = max(scored, key=lambda v: v.get("avg_score", 0.0))
        return best.get("prompt")

    def get_all_prompt_versions(self) -> List[Dict[str, Any]]:
        return list(self._meta.get("prompt_versions", []))

    def reset(self) -> None:
        """Wipe all performance data for this agent."""
        with _LOCK:
            if self._runs_path.exists():
                self._runs_path.unlink()
            self._meta = {
                "agent_id": self.agent_id,
                "prompt_versions": [],
                "current_prompt_version": 0,
                "total_runs": 0,
                "total_score": 0.0,
                "best_score": 0.0,
                "created_at": time.time(),
            }
            self._save_meta()


# ------------------------------------------------------------------
# Module-level registry for quick lookups
# ------------------------------------------------------------------

_store_cache: Dict[str, AgentPerformanceStore] = {}
_cache_lock = Lock()


def get_store(agent_id: str) -> AgentPerformanceStore:
    """Return (and cache) the AgentPerformanceStore for an agent."""
    with _cache_lock:
        if agent_id not in _store_cache:
            _store_cache[agent_id] = AgentPerformanceStore(agent_id)
        return _store_cache[agent_id]


def list_all_agents() -> List[Dict[str, Any]]:
    """Return a summary dict for every agent that has performance data on disk."""
    agents = []
    for meta_path in sorted(_PERF_DIR.glob("*_meta.json")):
        agent_id = meta_path.stem.replace("_meta", "")
        try:
            store = get_store(agent_id)
            agents.append(store.get_stats())
        except Exception:
            pass
    return agents
