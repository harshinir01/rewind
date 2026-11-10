"""
Execution recording service for Rewind.
Provides a decorator and utilities to capture agent execution steps.
"""
from __future__ import annotations
import functools
import json
import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend import models

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ExecutionRecorder:
    """
    Context manager for recording an agent execution run.
    
    Usage:
        with ExecutionRecorder(agent_name="MyAgent", task="Do something") as rec:
            rec.record_step("plan", "llm", input_data="...", output_data="...")
            rec.record_step("search", "tool", input_data="...", output_data="...")
        # run is committed to DB on context exit
    """

    def __init__(
        self,
        agent_name: str,
        task: str,
        prompt: Optional[str] = None,
        run_id: Optional[str] = None,
    ):
        self.agent_name = agent_name
        self.task = task
        self.prompt = prompt
        self.run_id = run_id or str(uuid.uuid4())
        self._steps: List[Dict] = []
        self._start_time = time.monotonic()
        self._step_counter = 0
        self._db: Optional[Session] = None
        self._ok = True
        self._fail_step: Optional[int] = None
        self._label: Optional[str] = None

    def __enter__(self) -> "ExecutionRecorder":
        self._db = SessionLocal()
        self._start_time = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._commit_run(failed_by_exception=exc_type is not None)
        finally:
            if self._db:
                self._db.close()
        return False  # Don't suppress exceptions

    def record_step(
        self,
        name: str,
        kind: str,
        *,
        input_data: Any = "",
        output_data: Any = "",
        tool_name: Optional[str] = None,
        status: str = "ok",
        tokens: int = 0,
        cost: float = 0.0,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> int:
        """Record a single execution step. Returns the step number."""
        self._step_counter += 1
        step_num = self._step_counter

        # Serialize non-string input/output
        if not isinstance(input_data, str):
            input_data = json.dumps(input_data, ensure_ascii=False)
        if not isinstance(output_data, str):
            output_data = json.dumps(output_data, ensure_ascii=False)

        if status in ("error", "fail"):
            self._ok = False
            if self._fail_step is None:
                self._fail_step = step_num

        self._steps.append({
            "step_number": step_num,
            "name": name,
            "kind": kind,
            "tool_name": tool_name,
            "input": input_data,
            "output": output_data,
            "status": status,
            "tokens": tokens,
            "cost": cost,
            "error_message": error_message,
            "duration_ms": duration_ms or 0,
        })
        return step_num

    def mark_failed(self, label: str, fail_step: Optional[int] = None):
        """Explicitly mark the run as failed with a failure category."""
        self._ok = False
        self._label = label
        if fail_step is not None:
            self._fail_step = fail_step

    def _commit_run(self, failed_by_exception: bool = False):
        """Write the run and all steps to SQLite."""
        if not self._db:
            return

        elapsed = time.monotonic() - self._start_time
        duration_ms = int(elapsed * 1000)
        duration_str = f"{elapsed:.1f}s"

        total_tokens = sum(s["tokens"] for s in self._steps)
        total_cost = sum(s["cost"] for s in self._steps)

        if failed_by_exception:
            self._ok = False

        run = models.AgentRun(
            id=self.run_id,
            agent=self.agent_name,
            task=self.task,
            ok=self._ok,
            label=self._label,
            steps_count=len(self._steps),
            cost=round(total_cost, 6),
            duration=duration_str,
            duration_ms=duration_ms,
            started_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            fail_step=self._fail_step,
            prompt=self.prompt,
        )
        self._db.add(run)

        for s in self._steps:
            step = models.ExecutionStep(
                run_id=self.run_id,
                step_number=s["step_number"],
                name=s["name"],
                kind=s["kind"],
                tool_name=s.get("tool_name"),
                input=s["input"],
                output=s["output"],
                status=s["status"],
                tokens=s["tokens"],
                cost=s["cost"],
                duration_ms=s["duration_ms"],
                error_message=s.get("error_message"),
            )
            self._db.add(step)

        try:
            self._db.commit()
        except Exception as e:
            logger.error(f"Failed to commit run {self.run_id}: {e}")
            self._db.rollback()
            raise


def record_execution(
    agent_name: str,
    task: Optional[str] = None,
    kind: str = "tool",
    *,
    capture_exceptions: bool = True,
):
    """
    Decorator for recording individual function calls as execution steps.
    
    Usage:
        @record_execution(agent_name="MyAgent", task="Process data")
        def my_tool(query: str) -> dict:
            return {"result": "..."}
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            step_name = task or func.__name__
            input_repr = json.dumps(
                {"args": [str(a)[:200] for a in args], "kwargs": {k: str(v)[:200] for k, v in kwargs.items()}},
                ensure_ascii=False,
            )
            t0 = time.monotonic()
            status = "ok"
            output_repr = ""
            error_msg = None
            result = None

            try:
                result = func(*args, **kwargs)
                output_repr = (
                    json.dumps(result, ensure_ascii=False)
                    if not isinstance(result, str)
                    else result
                )[:500]
                return result
            except Exception as e:
                status = "error"
                error_msg = str(e)
                output_repr = f"ERROR: {error_msg}"
                if not capture_exceptions:
                    raise
                return None
            finally:
                duration_ms = int((time.monotonic() - t0) * 1000)
                logger.debug(
                    f"[Rewind] {agent_name}/{step_name} → {status} in {duration_ms}ms"
                )

        return wrapper  # type: ignore
    return decorator
