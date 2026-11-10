"""
Rewind Recording Example
========================
Demonstrates how to record an actual agent execution into the Rewind SQLite database.

Run from the project root:
    python backend/examples/recorded_agent_example.py
"""
from __future__ import annotations
import json
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.database import create_tables
from backend.services.recording_service import ExecutionRecorder


def fake_list_tables() -> list:
    """Simulated tool — returns a list of table names."""
    return ["customers", "orders", "order_items"]


def fake_describe_table(table: str) -> dict:
    """Simulated tool — returns column names for a table."""
    schemas = {
        "orders": {"columns": ["id", "customer_id", "region_id", "amount", "status", "order_date"]},
        "customers": {"columns": ["id", "name", "email", "region_id"]},
        "order_items": {"columns": ["id", "order_id", "product_id", "quantity", "price"]},
    }
    return schemas.get(table, {"columns": []})


def fake_run_sql(query: str) -> str:
    """Simulated tool — executes a SQL-like query and returns a result."""
    if "quarter" in query.lower():
        return 'ERROR: column "quarter" does not exist\nHINT: Perhaps you meant "order_date".'
    if "region_id" in query.lower() and "order_date" in query.lower():
        return json.dumps([
            {"region_id": 1, "total": 142300.50},
            {"region_id": 2, "total": 98750.25},
            {"region_id": 3, "total": 211400.00},
        ])
    return "[]"


def run_sql_agent_example():
    """
    Records a full agent execution that demonstrates the 'ignored_error' failure.
    This is an example of how you'd instrument a real agent.
    """
    print("=" * 60)
    print("Rewind Recording Example — SQL Agent")
    print("=" * 60)

    # Ensure tables exist
    create_tables()

    with ExecutionRecorder(
        agent_name="sql-agent-demo",
        task="Revenue by region for Q3",
        prompt=(
            "You are a data analyst agent. Answer questions by querying the company "
            "database with the tools provided.\nUse only tables and columns returned "
            "by describe_table.\nKeep answers short."
        ),
    ) as recorder:
        # Step 1: Plan
        recorder.record_step(
            name="plan",
            kind="llm",
            input_data="Task: Revenue by region for Q3\nTools: list_tables, describe_table, run_sql",
            output_data="1. Find the orders table\n2. Check columns\n3. Run the aggregate query",
            tokens=380,
            duration_ms=820,
        )
        print("✓ Step 1: plan")

        # Step 2: list_tables
        tables = fake_list_tables()
        recorder.record_step(
            name="list_tables",
            kind="tool",
            input_data="{}",
            output_data=tables,
            duration_ms=95,
        )
        print(f"✓ Step 2: list_tables → {tables}")

        # Step 3: describe_table
        schema = fake_describe_table("orders")
        recorder.record_step(
            name="describe_table",
            kind="tool",
            input_data={"table": "orders"},
            output_data=schema,
            duration_ms=110,
        )
        print(f"✓ Step 3: describe_table → {schema}")

        # Step 4: run_sql (with wrong column — will error)
        bad_query = "SELECT region_id, SUM(amount) FROM orders WHERE quarter = 'Q3' GROUP BY region_id"
        sql_result = fake_run_sql(bad_query)
        is_error = sql_result.startswith("ERROR")
        recorder.record_step(
            name="run_sql",
            kind="tool",
            input_data={"query": bad_query},
            output_data=sql_result,
            status="error" if is_error else "ok",
            error_message=sql_result if is_error else None,
            duration_ms=140,
        )
        print(f"✓ Step 4: run_sql → {'ERROR' if is_error else 'OK'}")

        # Step 5: LLM incorrectly interprets the error as "no data"
        # This is the failure point — the agent should retry with order_date
        recorder.record_step(
            name="respond",
            kind="llm",
            input_data=f"Tool result (run_sql):\n{sql_result}",
            output_data="The query returned no rows, so revenue for Q3 is 0 in every region.",
            status="fail",
            tokens=520,
            duration_ms=1120,
        )
        recorder.mark_failed(label="ignored_error", fail_step=5)
        print("✓ Step 5: respond (FAIL — agent ignored the error)")

    print()
    print(f"Run ID: {recorder.run_id}")
    print("✅ Execution recorded to SQLite database.")
    print()
    print("You can now:")
    print(f"  • View this run at: GET /api/runs/{recorder.run_id}")
    print(f"  • Trigger diagnosis: POST /api/runs/{recorder.run_id}/diagnose")
    print(f"  • Try a fix: POST /api/runs/{recorder.run_id}/replay")
    return recorder.run_id


if __name__ == "__main__":
    run_id = run_sql_agent_example()
    print(f"\nRecorded run ID: {run_id}")
