# SQL Query Debugger — OpenEnv Environment

An OpenEnv environment where an AI agent debugs broken SQL queries against a live SQLite database. The agent receives a broken query, the database schema, and expected output, then iteratively fixes the query.

## Why SQL Debugging?

SQL debugging is a genuine task that developers and data analysts perform daily. Unlike toy environments, this models a real workflow:
- Read the error or wrong output
- Understand the schema
- Identify the bug (syntax, schema mismatch, or logic error)
- Fix and re-run

This environment is ideal for training and evaluating LLM agents on structured reasoning tasks with deterministic, verifiable outcomes.

## Task Design

9 tasks across 3 difficulty levels:

| Difficulty | Tasks | Max Steps | Bug Type | Examples |
|-----------|-------|-----------|----------|----------|
| **Easy** | 3 | 5 | Syntax errors | Typos in keywords, missing commas, unclosed quotes |
| **Medium** | 3 | 8 | Schema errors | Wrong column/table names, missing JOINs |
| **Hard** | 3 | 12 | Logic errors | Wrong JOIN type, missing GROUP BY, correlated subqueries |

### Task List

| ID | Difficulty | Description |
|----|-----------|-------------|
| easy_1 | Easy | Fix typo in SELECT keyword |
| easy_2 | Easy | Fix typo in WHERE keyword |
| easy_3 | Easy | Fix unclosed string literal |
| medium_1 | Medium | Fix wrong column name |
| medium_2 | Medium | Fix wrong table name |
| medium_3 | Medium | Add missing JOIN for cross-table query |
| hard_1 | Hard | Change INNER JOIN to LEFT JOIN |
| hard_2 | Hard | Add missing GROUP BY clause |
| hard_3 | Hard | Fix global AVG to per-department correlated subquery |

## Action Space

```python
class SQLAction(Action):
    query: str  # The corrected SQL query
```

## Observation Space

```python
class SQLObservation(Observation):
    task_id: str              # Task identifier
    difficulty: str           # "easy", "medium", "hard"
    broken_query: str         # The original broken query
    schema_description: str   # CREATE TABLE DDL statements
    expected_output: str      # Expected query result rows
    execution_result: str     # Actual result of running submitted query
    execution_error: str      # Error message (empty if query succeeded)
    hint: str                 # Progressive hint (more specific after step 3)
    steps_remaining: int      # Steps left before episode ends
    done: bool                # Whether episode is complete
    reward: float             # Reward signal (0.0 - 1.0)
```

## Reward Function

Multi-signal reward with partial progress (not binary):

| Signal | Range | Description |
|--------|-------|-------------|
| **Correctness** | 0.0 - 1.0 | Query error → 0.0; partial row match → proportional; exact match → 1.0 |
| **Efficiency bonus** | 0.0 - 0.2 | Fewer steps = higher bonus |
| **Progress bonus** | 0.0 / 0.05 | Reward for improving over previous best attempt |

Correctness breakdown:
- Query fails to execute → 0.0
- Executes but empty result → 0.05
- Wrong column count → 0.1
- Partial row match → 0.1 + (matching_rows / expected_rows) * 0.8
- Exact match (order-insensitive) → 1.0

## Setup

### Prerequisites
- Python 3.10+
- Docker (optional, for containerized deployment)

### Local Development

```bash
# Install
pip install openenv-core[core]
pip install -e .

# Run server
uvicorn sql_debugger.server.app:app --host 0.0.0.0 --port 8000

# Test
curl http://localhost:8000/health
```

### Docker

```bash
docker build -t sql-debugger -f server/Dockerfile .
docker run -p 8000:8000 sql-debugger
```

### Run Inference

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-Coder-32B-Instruct"
export HF_TOKEN="your-token-here"
export ENV_URL="http://localhost:8000"

python inference.py
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_BASE_URL` | Yes | LLM API endpoint |
| `MODEL_NAME` | Yes | Model identifier |
| `HF_TOKEN` | Yes | API authentication key |
| `ENV_URL` | No | Environment server URL (default: http://localhost:8000) |

## Baseline Scores

| Task | Difficulty | Score |
|------|-----------|-------|
| easy_1 | Easy | 1.00 |
| easy_2 | Easy | 1.00 |
| easy_3 | Easy | 1.00 |
| medium_1 | Medium | 1.00 |
| medium_2 | Medium | 1.00 |
| medium_3 | Medium | 1.00 |
| hard_1 | Hard | 1.00 |
| hard_2 | Hard | 1.00 |
| hard_3 | Hard | 0.85 |
| **Average** | | **0.98** |

*Baseline model: Qwen/Qwen2.5-Coder-32B-Instruct*

## Architecture

```
sql_debugger/
├── models.py              ← Pydantic: SQLAction, SQLObservation, SQLState
├── client.py              ← WebSocket client (EnvClient subclass)
├── server/
│   ├── environment.py     ← Core logic: reset(), step(), state
│   ├── sql_engine.py      ← SQLite in-memory executor
│   ├── tasks.py           ← 9 task definitions
│   ├── grader.py          ← Multi-signal reward function
│   ├── app.py             ← FastAPI server
│   └── Dockerfile
├── openenv.yaml           ← Environment manifest
├── inference.py           ← Baseline inference script
└── README.md
```

## GRPO Training Compatibility

This environment is designed to be compatible with TRL's GRPOTrainer:
- Multi-signal rewards provide rich gradient information
- Deterministic grading enables reproducible training
- Progressive hints simulate curriculum learning
- The `reset(seed=N)` API enables deterministic task selection

To use with GRPO, implement a rollout function that maps model completions to `SQLAction` objects and feeds environment rewards back to the trainer.
