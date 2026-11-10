"""
Rewind FastAPI Backend — Main Application Entry Point
======================================================
Run with:
    uvicorn backend.main:app --reload --port 8000

Or from project root:
    python -m uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.config import ALLOWED_ORIGINS
from backend.database import create_tables, get_db
from backend import models

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("rewind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables (safe — won't drop existing data)…")
    create_tables()
    logger.info("Rewind backend ready.")
    yield


app = FastAPI(
    title="Rewind — AI Agent Debugging & Verified Repair",
    description=(
        "Official REST API for Rewind: agent execution tracing, "
        "fault localization, cached replay, and batch verification."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"http://localhost:\d+",   # any localhost port for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from backend.routers import health, runs, diagnosis, replay, batch, analytics  # noqa: E402

app.include_router(health.router)
app.include_router(runs.router)
app.include_router(diagnosis.router)
app.include_router(replay.router)
app.include_router(batch.router)
app.include_router(analytics.router)

# ---------------------------------------------------------------------------
# Dev / Seed endpoint
# (seeds the standard Rewind demo runs for immediate testing)
# ---------------------------------------------------------------------------

@app.post("/api/dev/seed", tags=["Dev"])
def seed_demo_runs(db: Session = Depends(get_db)):
    """
    Seed demonstration agent runs into the database.
    Safe to call multiple times — skips runs that already exist.
    """
    demo_runs_data = [
        {
            "id": "r-2041",
            "agent": "sql-agent",
            "task": "Revenue by region, Q3",
            "ok": False,
            "label": "ignored_error",
            "steps_count": 7,
            "cost": 0.041,
            "duration": "14.2s",
            "duration_ms": 14200,
            "started_at": "Today 10:38",
            "fail_step": 5,
            "prompt": (
                "You are a data analyst agent. Answer questions by querying the company database with the tools provided.\n"
                "Use only tables and columns returned by describe_table.\nKeep answers short."
            ),
            "suggested_fix": (
                "If a tool returns an error, never treat it as an empty result. "
                "Read the error, correct the input, and retry once. "
                "If it still fails, tell the user the query failed."
            ),
            "steps": [
                {"step_number": 1, "name": "plan", "kind": "llm", "duration_ms": 820, "tokens": 412,
                 "input": "Task: Revenue by region, Q3\nTools: list_tables, describe_table, run_sql, format_report",
                 "output": "1. Find the orders table\n2. Check its columns\n3. Aggregate amount by region for Q3\n4. Format the result",
                 "status": "ok"},
                {"step_number": 2, "name": "list_tables", "kind": "tool", "duration_ms": 96, "tokens": 0,
                 "input": "{}",
                 "output": '["customers", "orders", "order_items", "refunds", "regions"]',
                 "status": "ok"},
                {"step_number": 3, "name": "describe_table", "kind": "tool", "duration_ms": 112, "tokens": 0,
                 "input": '{"table": "orders"}',
                 "output": '{"columns": ["id", "customer_id", "region_id", "amount", "status", "order_date"]}',
                 "status": "ok"},
                {"step_number": 4, "name": "run_sql", "kind": "tool", "duration_ms": 143, "tokens": 0,
                 "input": '{"query": "SELECT region_id, SUM(amount) FROM orders WHERE quarter = \'Q3\' GROUP BY region_id"}',
                 "output": 'ERROR: column "quarter" does not exist\nHINT: Perhaps you meant "order_date".',
                 "status": "error"},
                {"step_number": 5, "name": "respond", "kind": "llm", "duration_ms": 1140, "tokens": 530,
                 "input": 'Tool result (run_sql):\nERROR: column "quarter" does not exist\nHINT: Perhaps you meant "order_date".',
                 "output": "The query returned no rows, so revenue for Q3 is 0 in every region.",
                 "status": "fail"},
                {"step_number": 6, "name": "format_report", "kind": "tool", "duration_ms": 88, "tokens": 0,
                 "input": '{"rows": [], "title": "Q3 revenue by region"}',
                 "output": "| Region | Revenue |\n|---|---|\n| (no data) | 0 |",
                 "status": "ok"},
                {"step_number": 7, "name": "final_answer", "kind": "llm", "duration_ms": 760, "tokens": 301,
                 "input": "Report: Q3 revenue by region, no data",
                 "output": "Q3 revenue was ₹0 in all regions.",
                 "status": "ok"},
            ],
            "diagnosis": {
                "failure_category": "ignored_error",
                "reason": (
                    "A database search failed at step 4, and the error message even suggested the fix. "
                    "At step 5 the agent read that failure as \"no data\" and carried on, "
                    "so the final answer was ₹0 for every region."
                ),
                "evidence": [
                    {"from": "What step 4 returned",
                     "text": 'ERROR: column "quarter" does not exist\nHINT: Perhaps you meant "order_date".'},
                    {"from": "What the agent said at step 5",
                     "text": "The query returned no rows, so revenue for Q3 is 0 in every region."},
                ],
                "fired_detectors": {
                    "Ignored tool error": "Step 4 returned an error, but step 5 answered as if nothing was wrong.",
                    "Argument absent from context": 'The column "quarter" never appeared in the table description at step 3.',
                },
                "judge_verdict": "Agrees with step 5. The error message named the right column (order_date), but the agent did not use it.",
                "relevant_step": 5,
                "confidence": 0.97,
            },
        },
        {
            "id": "r-2038",
            "agent": "trip-planner",
            "task": "3-day Jaipur plan under ₹25,000",
            "ok": False,
            "label": "infinite_loop",
            "steps_count": 8,
            "cost": 0.058,
            "duration": "21.6s",
            "duration_ms": 21600,
            "started_at": "Today 10:12",
            "fail_step": 3,
            "prompt": (
                "You are a travel planner. Build itineraries using the search tools.\n"
                "Respect the user's budget. Keep each day to at most four stops."
            ),
            "suggested_fix": (
                "If a search returns no results, change one parameter (price, dates or area) before searching again. "
                "Never repeat a search with identical arguments. "
                "After two empty searches, ask the user which constraint to relax."
            ),
            "steps": [
                {"step_number": 1, "name": "plan", "kind": "llm", "duration_ms": 910, "tokens": 480,
                 "input": "Task: 3-day Jaipur plan under ₹25,000\nTools: search_hotels, search_sights, build_plan",
                 "output": "1. Find hotels\n2. Find sights\n3. Build the day plan under budget",
                 "status": "ok"},
                {"step_number": 2, "name": "search_hotels", "kind": "tool", "duration_ms": 410, "tokens": 0,
                 "input": '{"city": "Jaipur", "max_price": 4000, "nights": 3}',
                 "output": '{"results": [], "note": "No hotels under ₹4,000/night with a 3-night minimum"}',
                 "status": "ok"},
                {"step_number": 3, "name": "decide", "kind": "llm", "duration_ms": 640, "tokens": 220,
                 "input": "Tool result (search_hotels): 0 results",
                 "output": "No results. Retrying the hotel search.",
                 "status": "fail"},
                {"step_number": 4, "name": "search_hotels", "kind": "tool", "duration_ms": 402, "tokens": 0,
                 "input": '{"city": "Jaipur", "max_price": 4000, "nights": 3}',
                 "output": '{"results": [], "note": "No hotels under ₹4,000/night with a 3-night minimum"}',
                 "status": "ok"},
                {"step_number": 5, "name": "decide", "kind": "llm", "duration_ms": 610, "tokens": 238,
                 "input": "Tool result (search_hotels): 0 results",
                 "output": "No results. Retrying the hotel search.",
                 "status": "ok"},
                {"step_number": 6, "name": "search_hotels", "kind": "tool", "duration_ms": 417, "tokens": 0,
                 "input": '{"city": "Jaipur", "max_price": 4000, "nights": 3}',
                 "output": '{"results": [], "note": "No hotels under ₹4,000/night with a 3-night minimum"}',
                 "status": "ok"},
                {"step_number": 7, "name": "decide", "kind": "llm", "duration_ms": 655, "tokens": 251,
                 "input": "Tool result (search_hotels): 0 results",
                 "output": "No results. Retrying the hotel search.",
                 "status": "ok"},
                {"step_number": 8, "name": "max_steps", "kind": "system", "duration_ms": 0, "tokens": 0,
                 "input": "step_limit = 8",
                 "output": "Run stopped: step limit (8) reached. No itinerary produced.",
                 "status": "error"},
            ],
            "diagnosis": {
                "failure_category": "infinite_loop",
                "reason": (
                    "The hotel search found nothing and said why: the price limit was too low. "
                    "At step 3 the agent chose to search the exact same way again, "
                    "and kept repeating until it ran out of steps."
                ),
                "evidence": [
                    {"from": "What step 2 returned",
                     "text": '{"results": [], "note": "No hotels under ₹4,000/night with a 3-night minimum"}'},
                    {"from": "What steps 4 and 6 asked for",
                     "text": '{"city": "Jaipur", "max_price": 4000, "nights": 3} (identical to step 2)'},
                ],
                "fired_detectors": {
                    "Repeated identical call": "The hotel search ran with identical settings at steps 2, 4 and 6.",
                    "Step or budget limit": "The run was cut off at its 8-step limit.",
                },
                "judge_verdict": "Agrees with step 3. It is the first moment the agent could have changed its search, and the result already pointed to the price limit.",
                "relevant_step": 3,
                "confidence": 0.95,
            },
        },
        {
            "id": "r-2035",
            "agent": "research-agent",
            "task": "Summarise recent solid-state battery work",
            "ok": False,
            "label": "goal_drift",
            "steps_count": 7,
            "cost": 0.047,
            "duration": "17.0s",
            "duration_ms": 17000,
            "started_at": "Today 09:40",
            "fail_step": 4,
            "prompt": (
                "You are a research assistant. Search, read sources, and write short summaries.\n"
                "Cite the sources you used."
            ),
            "suggested_fix": (
                "Every search query must serve the user's task. "
                "If a source raises a related topic, mention it in one line at most. Do not search for it."
            ),
            "steps": [
                {"step_number": 1, "name": "plan", "kind": "llm", "duration_ms": 780, "tokens": 390,
                 "input": "Task: Summarise recent work on solid-state batteries",
                 "output": "1. Search recent progress\n2. Read two sources\n3. Write a 200-word summary",
                 "status": "ok"},
                {"step_number": 2, "name": "web_search", "kind": "tool", "duration_ms": 1210, "tokens": 0,
                 "input": '{"q": "solid-state battery progress 2026"}',
                 "output": '5 results. Top: "Sulfide electrolytes close the gap on lithium-ion cost" (review, Oct 2026)',
                 "status": "ok"},
                {"step_number": 3, "name": "fetch_page", "kind": "tool", "duration_ms": 860, "tokens": 0,
                 "input": '{"url": "https://example.org/sulfide-electrolytes-review"}',
                 "output": "...sulfide electrolytes now exceed 10 mS/cm at room temperature... pilot lines depend on lithium supply, with new mining rules in Chile affecting quotas...",
                 "status": "ok"},
                {"step_number": 4, "name": "notes", "kind": "llm", "duration_ms": 980, "tokens": 402,
                 "input": "Page excerpt (fetch_page)",
                 "output": "Notes: sulfide electrolytes exceed 10 mS/cm at room temperature. The article also raises lithium supply risk. Following that thread.",
                 "status": "fail"},
                {"step_number": 5, "name": "web_search", "kind": "tool", "duration_ms": 1180, "tokens": 0,
                 "input": '{"q": "lithium mining regulations Chile 2026"}',
                 "output": '5 results. Top: "Chile revises lithium quota framework"',
                 "status": "ok"},
                {"step_number": 6, "name": "fetch_page", "kind": "tool", "duration_ms": 940, "tokens": 0,
                 "input": '{"url": "https://example.org/chile-lithium-quotas"}',
                 "output": "...the revised framework sets annual quotas by producer...",
                 "status": "ok"},
                {"step_number": 7, "name": "final_answer", "kind": "llm", "duration_ms": 1420, "tokens": 610,
                 "input": "Notes and two fetched pages",
                 "output": "Summary: The debate around solid-state batteries now centres on lithium supply, with new Chilean mining rules shaping quotas and prices.",
                 "status": "ok"},
            ],
            "diagnosis": {
                "failure_category": "goal_drift",
                "reason": (
                    "The final summary answers a different question from the one asked. "
                    "At step 4 the agent followed a side remark about lithium supply, "
                    "and never came back to the battery research."
                ),
                "evidence": [
                    {"from": "What the agent said at step 4",
                     "text": "The article also raises lithium supply risk. Following that thread."},
                    {"from": "What the agent said at step 7",
                     "text": "The debate around solid-state batteries now centres on lithium supply..."},
                ],
                "fired_detectors": {},
                "judge_verdict": "No automatic check caught this one, so the AI reviewer flagged it: the search at step 5 no longer matched the question.",
                "relevant_step": 4,
                "confidence": 0.88,
            },
        },
        {
            "id": "r-2040",
            "agent": "research-agent",
            "task": "Compare three EV charging standards",
            "ok": True,
            "label": None,
            "steps_count": 9,
            "cost": 0.052,
            "duration": "18.9s",
            "duration_ms": 18900,
            "started_at": "Today 10:31",
            "fail_step": None,
            "prompt": "You are a research assistant. Search, read sources, and write short summaries.",
            "steps": [],
            "diagnosis": None,
        },
        {
            "id": "r-2036",
            "agent": "sql-agent",
            "task": "Orders per day, last 14 days",
            "ok": True,
            "label": None,
            "steps_count": 5,
            "cost": 0.019,
            "duration": "6.4s",
            "duration_ms": 6400,
            "started_at": "Today 09:47",
            "fail_step": None,
            "prompt": "You are a data analyst agent. Answer questions by querying the company database.",
            "steps": [],
            "diagnosis": None,
        },
    ]

    seeded = 0
    skipped = 0

    for run_data in demo_runs_data:
        existing = db.query(models.AgentRun).filter(models.AgentRun.id == run_data["id"]).first()
        if existing:
            skipped += 1
            continue

        run = models.AgentRun(
            id=run_data["id"],
            agent=run_data["agent"],
            task=run_data["task"],
            ok=run_data["ok"],
            label=run_data.get("label"),
            steps_count=run_data["steps_count"],
            cost=run_data["cost"],
            duration=run_data["duration"],
            duration_ms=run_data["duration_ms"],
            started_at=run_data["started_at"],
            fail_step=run_data.get("fail_step"),
            prompt=run_data.get("prompt"),
            suggested_fix=run_data.get("suggested_fix"),
        )
        db.add(run)
        db.flush()

        for step_data in run_data.get("steps", []):
            step = models.ExecutionStep(
                run_id=run_data["id"],
                step_number=step_data["step_number"],
                name=step_data["name"],
                kind=step_data["kind"],
                duration_ms=step_data.get("duration_ms", 0),
                tokens=step_data.get("tokens", 0),
                input=step_data.get("input", ""),
                output=step_data.get("output", ""),
                status=step_data.get("status", "ok"),
            )
            db.add(step)

        if run_data.get("diagnosis"):
            d = run_data["diagnosis"]
            diag = models.Diagnosis(
                run_id=run_data["id"],
                failure_category=d["failure_category"],
                reason=d["reason"],
                relevant_step=d.get("relevant_step"),
                evidence_json=json.dumps(d.get("evidence", []), ensure_ascii=False),
                fired_detectors_json=json.dumps(d.get("fired_detectors", {}), ensure_ascii=False),
                judge_verdict=d.get("judge_verdict", ""),
                confidence=d.get("confidence"),
            )
            db.add(diag)

        seeded += 1

    db.commit()
    return {
        "seeded": seeded,
        "skipped_existing": skipped,
        "total_runs": db.query(models.AgentRun).count(),
    }
