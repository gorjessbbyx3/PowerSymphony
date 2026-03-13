"""Session persistence primitives for workflow runs."""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Event
from typing import Any, Dict, Optional

from server.services.artifact_events import ArtifactEventQueue

_SESSION_STORE_DIR = Path("WareHouse/.sessions")
_SESSION_STORE_DIR.mkdir(parents=True, exist_ok=True)


class SessionStatus(Enum):
    """Lifecycle states for a workflow session."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class WorkflowSession:
    """Mutable record describing a workflow session."""

    session_id: str
    yaml_file: str
    task_prompt: str
    task_attachments: list[str] = field(default_factory=list)
    status: SessionStatus = SessionStatus.IDLE
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    # Execution metadata
    executor: Optional[Any] = None
    graph: Optional[Any] = None
    current_node_id: Optional[str] = None

    # Human input tracking
    waiting_for_input: bool = False
    input_promise: Optional[Any] = None
    pending_input_data: Optional[Dict[str, Any]] = None
    human_input_future: Optional[Any] = None
    human_input_value: Optional[str] = None

    # Results + errors
    results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    # Artifact streaming
    artifact_queue: ArtifactEventQueue = field(default_factory=ArtifactEventQueue)

    # Cancellation tracking
    cancel_event: Event = field(default_factory=Event)
    cancel_reason: Optional[str] = None


class WorkflowSessionStore:
    """In-memory registry that tracks workflow session metadata."""

    def __init__(self) -> None:
        self._sessions: Dict[str, WorkflowSession] = {}
        self.logger = logging.getLogger(__name__)

    def _persist(self, session: "WorkflowSession") -> None:
        """Write lightweight session metadata to disk for crash recovery."""
        try:
            record = {
                "session_id": session.session_id,
                "yaml_file": session.yaml_file,
                "task_prompt": session.task_prompt,
                "task_attachments": session.task_attachments,
                "status": session.status.value,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "current_node_id": session.current_node_id,
                "error_message": session.error_message,
            }
            path = _SESSION_STORE_DIR / f"{session.session_id}.json"
            path.write_text(json.dumps(record, indent=2))
        except Exception as exc:
            self.logger.debug("Session persist failed for %s: %s", session.session_id, exc)

    def load_historical_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Return metadata for all sessions persisted to disk (past runs)."""
        historical: Dict[str, Dict[str, Any]] = {}
        for path in _SESSION_STORE_DIR.glob("*.json"):
            try:
                record = json.loads(path.read_text())
                sid = record.get("session_id")
                if sid and sid not in self._sessions:
                    historical[sid] = record
            except Exception:
                pass
        return historical

    def create_session(
        self,
        *,
        yaml_file: str,
        task_prompt: str,
        session_id: str,
        attachments: Optional[list[str]] = None,
    ) -> WorkflowSession:
        session = WorkflowSession(
            session_id=session_id,
            yaml_file=yaml_file,
            task_prompt=task_prompt,
            task_attachments=list(attachments or []),
        )
        self._sessions[session_id] = session
        self._persist(session)
        self.logger.info("Created session %s for workflow %s", session_id, yaml_file)
        return session

    def get_session(self, session_id: str) -> Optional[WorkflowSession]:
        return self._sessions.get(session_id)

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    def update_session_status(self, session_id: str, status: SessionStatus, **kwargs: Any) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        session.status = status
        session.updated_at = time.time()
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        self._persist(session)
        self.logger.info("Updated session %s status to %s", session_id, status.value)

    def set_session_error(self, session_id: str, error_message: str) -> None:
        self.update_session_status(session_id, SessionStatus.ERROR, error_message=error_message)

    def complete_session(self, session_id: str, results: Dict[str, Any]) -> None:
        self.update_session_status(session_id, SessionStatus.COMPLETED, results=results)

    def pop_session(self, session_id: str) -> Optional[WorkflowSession]:
        return self._sessions.pop(session_id, None)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        return {
            "session_id": session.session_id,
            "yaml_file": session.yaml_file,
            "status": session.status.value,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "current_node_id": session.current_node_id,
            "waiting_for_input": session.waiting_for_input,
            "error_message": session.error_message,
        }

    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        return {session_id: self.get_session_info(session_id) for session_id in self._sessions.keys()}

    def get_artifact_queue(self, session_id: str) -> Optional[ArtifactEventQueue]:
        session = self._sessions.get(session_id)
        return session.artifact_queue if session else None
