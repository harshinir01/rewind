# Rewind FastAPI Backend Reference & API Contract

This directory contains the reference FastAPI implementation for **Rewind — Debugging and Verified Repair for AI Agents**.

## How to Run FastAPI

To run the backend server:

```bash
# 1. Install dependencies
pip install fastapi uvicorn pydantic

# 2. Start the FastAPI server (use port 8081 or any open port)
uvicorn backend.main:app --reload --port 8081
```

Once running, point the Rewind frontend to `http://localhost:8081` via the in-app connection bar or by setting:

```bash
# In .env or shell:
VITE_API_BASE_URL=http://localhost:8081
```

---

## API Endpoints & Contract Specification

### 1. Health
- `GET /health` or `GET /api/health`
  - Response: `{"status": "ok", "service": "rewind-fastapi-backend", "timestamp": "...", "database_records": 0}`

### 2. Runs Management
- `GET /api/runs`
  - Query parameters:
    - `search` (string, optional): Search across ID, agent, task, or failure label
    - `status` (string, optional): `'all' | 'failed' | 'passed'`
    - `limit` (int, default 50): Page limit
    - `offset` (int, default 0): Offset for pagination
  - Response: `List[AgentRun]`

- `GET /api/runs/{run_id}`
  - Response: `RunDetail` (includes `steps: List[ExecutionStep]`, `diagnosis?: DiagnosisResult`)

- `POST /api/runs`
  - Request body: `RunDetail`
  - Response: `RunDetail` (HTTP 201)

- `DELETE /api/runs/{run_id}`
  - Response: `{"success": true, "id": run_id}`

### 3. Diagnosis
- `GET /api/runs/{run_id}/diagnosis`
  - Response: `DiagnosisResult`

- `POST /api/runs/{run_id}/diagnose`
  - Trigger fault diagnosis on a run
  - Response: `DiagnosisResult`

### 4. Replay & Repair
- `POST /api/runs/{run_id}/replay`
  - Request body:
    ```json
    {
      "prompt": "string",
      "start_step": 5,
      "replay_mode": "cached"
    }
    ```
  - Response: `ReplayResult`

### 5. Batch Verification
- `GET /api/batch/runs`
  - Response: `List[BatchItem]`

- `POST /api/batch/verify`
  - Request body:
    ```json
    {
      "run_ids": ["r-2041", "r-2029"],
      "modified_prompt": "string",
      "target_rule": "string"
    }
    ```
  - Response: `BatchVerificationResponse`

### 6. Analytics
- `GET /api/analytics/metrics`
  - Response: `AnalyticsMetrics`

### 7. Optional Seed Route
- `POST /api/dev/seed`
  - Seeds reference demo agent runs into the database for immediate testing
