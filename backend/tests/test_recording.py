"""Tests for the recording service (ExecutionRecorder).

NOTE: These tests use the `db` fixture (in-memory SQLite) from conftest.py.
      The ExecutionRecorder normally creates its own SessionLocal; here we bypass
      that by constructing the recorder object manually and injecting the test db.
"""
import pytest
import time


def test_execution_recorder_creates_run(db):
    from backend.services.recording_service import ExecutionRecorder
    from backend import models

    recorder = ExecutionRecorder.__new__(ExecutionRecorder)
    recorder.agent_name = "test-recorder-agent"
    recorder.task = "Test recording task"
    recorder.prompt = "Be a test agent."
    recorder.run_id = "rec-test-001"
    recorder._steps = []
    recorder._step_counter = 0
    recorder._ok = True
    recorder._fail_step = None
    recorder._label = None
    recorder._db = db
    recorder._start_time = time.monotonic()

    recorder.record_step(
        name="step_one",
        kind="llm",
        input_data="Hello",
        output_data="World",
        tokens=100,
        duration_ms=200,
    )
    recorder.record_step(
        name="step_two",
        kind="tool",
        input_data={"key": "value"},
        output_data="result",
        duration_ms=50,
    )

    recorder._commit_run()

    # Verify persisted
    run = db.query(models.AgentRun).filter(models.AgentRun.id == "rec-test-001").first()
    assert run is not None
    assert run.agent == "test-recorder-agent"
    assert run.task == "Test recording task"
    assert run.ok is True

    steps = db.query(models.ExecutionStep).filter(models.ExecutionStep.run_id == "rec-test-001").all()
    assert len(steps) == 2


def test_execution_recorder_marks_failure(db):
    from backend.services.recording_service import ExecutionRecorder
    from backend import models

    recorder = ExecutionRecorder.__new__(ExecutionRecorder)
    recorder.agent_name = "failure-agent"
    recorder.task = "Fail task"
    recorder.prompt = None
    recorder.run_id = "rec-fail-001"
    recorder._steps = []
    recorder._step_counter = 0
    recorder._ok = True
    recorder._fail_step = None
    recorder._label = None
    recorder._db = db
    recorder._start_time = time.monotonic()

    recorder.record_step("broken_step", "tool",
                         input_data="{}", output_data="ERROR: something broke",
                         status="error", duration_ms=100)
    recorder.mark_failed("ignored_error", fail_step=1)

    recorder._commit_run()

    run = db.query(models.AgentRun).filter(models.AgentRun.id == "rec-fail-001").first()
    assert run is not None
    assert run.ok is False
    assert run.label == "ignored_error"
    assert run.fail_step == 1


def test_step_numbering_is_sequential(db):
    from backend.services.recording_service import ExecutionRecorder
    from backend import models

    recorder = ExecutionRecorder.__new__(ExecutionRecorder)
    recorder.agent_name = "seq-agent"
    recorder.task = "Sequential steps"
    recorder.prompt = None
    recorder.run_id = "rec-seq-001"
    recorder._steps = []
    recorder._step_counter = 0
    recorder._ok = True
    recorder._fail_step = None
    recorder._label = None
    recorder._db = db
    recorder._start_time = time.monotonic()

    for i in range(5):
        recorder.record_step(f"step_{i}", "llm", input_data="x", output_data="y")

    recorder._commit_run()

    steps = (
        db.query(models.ExecutionStep)
        .filter(models.ExecutionStep.run_id == "rec-seq-001")
        .order_by(models.ExecutionStep.step_number)
        .all()
    )
    nums = [s.step_number for s in steps]
    assert nums == [1, 2, 3, 4, 5]


def test_recorder_exception_marks_run_failed(db):
    """An exception during the with-block must mark the run as failed."""
    from backend.services.recording_service import ExecutionRecorder
    from backend import models

    # We need to override the SessionLocal to use our test db.
    # Patch the SessionLocal used by __enter__ / __exit__.
    import backend.services.recording_service as rec_mod
    original_session_local = rec_mod.SessionLocal

    class _FakeSessionLocal:
        def __call__(self):
            return db

    rec_mod.SessionLocal = _FakeSessionLocal()

    run_id = "rec-exc-001"
    try:
        with ExecutionRecorder(agent_name="exc-agent", task="Raise task",
                               run_id=run_id) as rec:
            rec.record_step("ok_step", "llm", input_data="hi", output_data="bye")
            raise RuntimeError("intentional test error")
    except RuntimeError:
        pass
    finally:
        rec_mod.SessionLocal = original_session_local

    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    assert run is not None
    assert run.ok is False  # exception must mark the run failed
