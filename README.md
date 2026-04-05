---
title: SQL Query Debugger
emoji: 🔧
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
tags:
  - openenv
---

# SQL Query Debugger — OpenEnv Environment

An OpenEnv environment where AI agents debug broken SQL queries against a live SQLite database. Features composable reward rubrics, adaptive curriculum learning, multi-agent competitive/collaborative modes, and rich training analytics.

## Why SQL Debugging?

SQL debugging is a genuine task that developers and data analysts perform daily. Unlike toy environments, this models a real workflow:
- Read the error or wrong output
- Understand the schema
- Identify the bug (syntax, schema mismatch, or logic error)
- Fix and re-run

This environment is ideal for training and evaluating LLM agents on structured reasoning tasks with deterministic, verifiable outcomes.

## Task Design

34 tasks across 3 difficulty levels + an expert tier, spanning 7 database schemas:

| Difficulty | Static | Dynamic | Max Steps | Bug Type | Examples |
|-----------|--------|---------|-----------|----------|----------|
| **Easy** | 3 | 4 | 5 | Syntax errors | Typos in keywords, missing commas, unclosed quotes |
| **Medium** | 3 | 4 | 8 | Schema errors | Wrong column/table names, missing JOINs, wrong aliases |
| **Hard** | 3 | 17 | 12–15 | Logic errors | Window functions, CTEs, correlated subqueries, CASE WHEN, multi-table JOINs |
| **Expert** | — | dynamic | 15 | Multi-bug | 2+ bugs injected simultaneously from different categories |

Static tasks (seeds 0–8) have predefined bugs for deterministic baselines. Dynamic tasks use a random bug injector that makes every episode unique — essentially infinite variety.

### Advanced SQL Features (Hard Tasks)
The hard tasks test SQL patterns that LLMs commonly struggle with:
- **Window functions**: `RANK() OVER`, `SUM() OVER (PARTITION BY ... ORDER BY ...)`, `LAG()`
- **CTEs**: `WITH ... AS` for subquery decomposition
- **CASE WHEN**: Conditional aggregation and categorization
- **Correlated subqueries**: `NOT EXISTS`, per-group comparisons
- **Multi-table JOINs**: 4-table joins with HAVING and date filters
- **Complex aggregation**: Budget calculations, running totals, per-category analytics

### Dynamic Bug Injection

The `bug_injector` module provides 13 distinct bug injectors across 3 difficulty tiers:

- **Easy (4 injectors)**: keyword typos, missing commas, unclosed quotes, missing keywords
- **Medium (4 injectors)**: wrong column/table names, missing JOINs, wrong aliases
- **Hard (5 injectors)**: wrong JOIN type, missing GROUP BY, wrong aggregates, wrong operators, global vs correlated subqueries

For expert mode, `inject_multi_bug()` chains 2+ injectors on the same query, creating compound debugging challenges.

## Action Space

```python
class SQLAction(Action):
    query: str  # The corrected SQL query (validated: must not be empty)
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
    reward: float             # Composite reward signal
    metadata: Dict[str, Any]  # Rich training signals (see below)
```

### Observation Metadata

The `metadata` dict carries decomposed training signals for GRPO analysis:

```python
metadata = {
    "reward_components": {
        "correctness": 1.0,    # Row matching accuracy (0.0–1.0)
        "efficiency": 0.8,     # Step efficiency (0.0–1.0)
        "quality": 0.95,       # SQL style/quality (0.0–1.0)
        "diagnostic": 1.0,     # Bug fix quality (0.0–1.0)
        "regression": 0.05,    # Progress/regression signal
        "total": 1.0           # Weighted composite
    },
    "curriculum": {
        "current_level": 1,
        "level_name": "easy_medium",
        "is_expert_mode": False,
        "rolling_avg_reward": 0.92
    },
    "analytics": {             # Only on done=True
        "total_steps": 2,
        "final_reward": 1.0,
        "regression_count": 0,
        "was_bug_fixed": True,
        "unique_queries": 2
    },
    "multi_agent": {           # Only when group_id provided
        "mode": "competitive",
        "num_agents": 3,
        "rank": 1
    }
}
```

## Reward System — Composable Rubrics

Instead of a monolithic reward function, the environment uses 5 composable rubrics weighted into a single signal:

| Rubric | Weight | Range | Description |
|--------|--------|-------|-------------|
| **Correctness** | 0.60 | 0.0–1.0 | Row matching with ORDER BY awareness |
| **Efficiency** | 0.15 | 0.0–1.0 | Fewer steps = higher score |
| **Query Quality** | 0.10 | 0.0–1.0 | SQL style: penalizes SELECT *, missing aliases; rewards ROUND/COALESCE |
| **Diagnostic** | 0.15 | 0.0–1.0 | Did the agent fix the actual bug vs introduce new errors? |
| **Regression** | additive | -0.1/+0.05 | Penalty for making things worse; bonus for improvement |

Weights are configurable per training phase — e.g., ignore quality early, ramp it up once correctness is stable:

```python
from sql_debugger.server.rubrics import CompositeRubric
rubric = CompositeRubric(weights={"correctness": 0.8, "efficiency": 0.1, "quality": 0.0, "diagnostic": 0.1})
```

### Correctness Details

- Query fails to execute → 0.0
- Executes but empty result → 0.05
- Wrong column count → 0.1
- Partial row match → 0.1 + (matching_rows / expected_rows) × 0.8
- Exact match (order-insensitive) → 1.0
- Exact match (order-sensitive when ORDER BY present) → 1.0

## Adaptive Curriculum

When `seed=None`, the environment uses a curriculum manager that adjusts difficulty based on rolling agent performance:

| Level | Name | Task Pool | Promotion Threshold |
|-------|------|-----------|-------------------|
| 0 | easy_only | 100% easy | avg reward > 0.85 over 10 episodes |
| 1 | easy_medium | 30% easy, 70% medium | avg reward > 0.85 over 10 episodes |
| 2 | medium_hard | 30% medium, 70% hard | avg reward > 0.85 over 10 episodes |
| 3 | expert | 100% hard + multi-bug | — |

Demotion occurs if avg reward drops below 0.4 over 5 episodes. Deterministic seeds (0–8) bypass curriculum entirely for reproducible baselines.

## Multi-Agent Modes

Pass `group_id` and `mode` to `reset()` to enable multi-agent sessions:

### Competitive ("race")
```python
obs1 = env1.reset(seed=42, group_id="race1", mode="competitive")
obs2 = env2.reset(seed=42, group_id="race1", mode="competitive")
```
- Multiple agents get the same broken query
- First solver gets +0.1 time bonus
- Later solvers get diminishing bonuses (-0.03 per rank)

### Collaborative ("relay")
```python
obs = env.reset(seed=42, group_id="collab1", mode="collaborative")
```
- Agents take turns on the same query
- Each sees the previous agent's best attempt in hints
- Shared final reward — tests building on partial fixes

Single-agent mode is unchanged when no `group_id` is provided.

## Training Analytics

### Episode Metrics
Every completed episode produces detailed metrics:
- Reward trajectory (reward at each step)
- Correctness trajectory
- Regression count (times agent made things worse)
- Bug fix success rate
- Unique queries submitted

### API Endpoints
```bash
# Aggregate training stats
curl http://localhost:8000/analytics

# Current curriculum state
curl http://localhost:8000/curriculum
```

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

### Run Tests

```bash
pip install pytest
python -m pytest sql_debugger/tests/ -v
```

20 tests covering: rubrics, bug injection, grading, environment lifecycle, curriculum, multi-agent, analytics, model validation, and SQL engine.

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

| Task | Difficulty | Score | Steps |
|------|-----------|-------|-------|
| easy_1 | Easy | 1.00 | 1 |
| easy_2 | Easy | 1.00 | 1 |
| easy_3 | Easy | 1.00 | 1 |
| medium_1 | Medium | 1.00 | 1 |
| medium_2 | Medium | 1.00 | 1 |
| medium_3 | Medium | 1.00 | 1 |
| hard_1 | Hard | 1.00 | 1 |
| hard_2 | Hard | 1.00 | 1 |
| hard_3 | Hard | 1.00 | 1 |
| **Average** | | **1.00** | **1.0** |

*Baseline model: Qwen/Qwen2.5-Coder-32B-Instruct — Total time: 7.4s*

## Architecture

```
sql_debugger/
├── models.py              ← Pydantic: SQLAction (validated), SQLObservation, SQLState
├── client.py              ← WebSocket client (EnvClient subclass)
├── server/
│   ├── environment.py     ← Core orchestrator: reset(), step(), state
│   ├── rubrics.py         ← Composable reward: Correctness, Efficiency, Quality, Diagnostic, Regression
│   ├── grader.py          ← Backward-compatible wrapper for legacy callers
│   ├── sql_engine.py      ← SQLite executor with EXPLAIN, introspection, error categorization
│   ├── tasks.py           ← 34 task definitions (9 static + 25 dynamic) across 7 schemas
│   ├── bug_injector.py    ← 13 bug injectors + multi-bug chaining for expert mode
│   ├── curriculum.py      ← Adaptive difficulty with promotion/demotion thresholds
│   ├── multi_agent.py     ← Competitive (race) and collaborative (relay) session coordination
│   ├── analytics.py       ← Episode metrics, training statistics, observability
│   ├── app.py             ← FastAPI server + /analytics, /curriculum endpoints
│   └── Dockerfile
├── tests/
│   └── test_environment.py ← 20 pytest tests covering all modules
├── openenv.yaml           ← Environment manifest
├── inference.py           ← Baseline inference script (static + dynamic seeds)
└── README.md
```

## GRPO Training Compatibility

This environment is designed for TRL's GRPOTrainer with rich reward signals:

- **Decomposed rewards** — `metadata["reward_components"]` exposes individual rubric scores for training diagnostics and reward shaping
- **Deterministic grading** — reproducible via seed-based task selection
- **Adaptive curriculum** — automatic difficulty scaling based on policy performance
- **Progressive hints** — simulate curriculum learning within episodes
- **Configurable weights** — adjust rubric weights per training phase without code changes

Example GRPO integration:

```python
def compute_reward(completion: str, observation: SQLObservation) -> float:
    action = SQLAction(query=extract_sql(completion))
    result = env.step(action)

    # Use composite reward for training
    reward = result.reward

    # Log individual components for diagnostics
    components = result.metadata["reward_components"]
    wandb.log({f"reward/{k}": v for k, v in components.items()})

    return reward
```
