"""
SQL Debugger — Baseline Inference Script

Runs an LLM agent against SQL debugging tasks and reports scores.
Uses structured [START], [STEP], [END] logging format required by OpenEnv evaluation.

Environment variables:
    API_BASE_URL  — LLM API endpoint
    MODEL_NAME    — Model identifier
    HF_TOKEN      — API key for authentication
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from typing import List, Optional

from openai import OpenAI

from sql_debugger.client import SQLDebuggerClient
from sql_debugger.models import SQLAction, SQLObservation

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-Coder-32B-Instruct")
API_KEY = os.getenv("HF_TOKEN")

LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
IMAGE_NAME = LOCAL_IMAGE_NAME or "vatsalhf30/sql-debugger"
HF_SPACE_ID = "VatsalHF30/sql-debugger"
BENCHMARK = "sql_debugger"
MAX_STEPS = 12
MAX_TOTAL_REWARD = 1.0
SUCCESS_SCORE_THRESHOLD = 0.5
TEMPERATURE = 0.1
MAX_TOKENS = 512
FALLBACK_QUERY = "SELECT 1;"

# Tasks to run: seed -> task_name (at least 3: easy, medium, hard)
TASKS = [
    (0, "easy_1"),
    (1, "easy_2"),
    (2, "easy_3"),
    (3, "medium_1"),
    (4, "medium_2"),
    (5, "medium_3"),
    (6, "hard_1"),
    (7, "hard_2"),
    (8, "hard_3"),
]

SYSTEM_PROMPT = """You are an expert SQL debugger. You will be given:
1. A database schema (CREATE TABLE statements)
2. A broken SQL query that has an error
3. The expected output the query should produce
4. Feedback from your previous attempts (if any)

Your job is to fix the broken SQL query so it produces the expected output.

RULES:
- Return ONLY the corrected SQL query inside ```sql code blocks
- Do NOT explain your changes, just provide the fixed query
- The query must be valid SQLite syntax
- Think carefully about: typos, column names, table names, JOINs, GROUP BY, subqueries
- If you get an error, read it carefully and fix the specific issue

Example response format:
```sql
SELECT name, age FROM users WHERE age > 25;
```"""


# ---------------------------------------------------------------------------
# Structured Logging — Required [START], [STEP], [END] format
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    """Emit [START] log entry."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    """Emit [STEP] log entry."""
    print(
        f"[STEP] step={step} action={json.dumps(action)} "
        f"reward={reward:.4f} done={done} error={json.dumps(error)}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Emit [END] log entry."""
    print(
        f"[END] success={success} steps={steps} "
        f"score={score:.4f} rewards={json.dumps(rewards)}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# SQL extraction and prompt building
# ---------------------------------------------------------------------------

def extract_sql(response_text: str) -> str:
    """Extract SQL query from model response."""
    pattern = r"```sql\s*(.*?)\s*```"
    matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[-1].strip()

    pattern = r"```\s*(.*?)\s*```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return matches[-1].strip()

    cleaned = response_text.strip()
    if cleaned.upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE", "WITH", "CREATE")):
        return cleaned

    return FALLBACK_QUERY


def get_model_message(
    client: OpenAI,
    observation: SQLObservation,
    history: List[str],
) -> str:
    """Call the LLM and return the extracted SQL query."""
    parts = [
        f"## Database Schema\n```sql\n{observation.schema_description}\n```",
        f"\n## Broken Query\n```sql\n{observation.broken_query}\n```",
        f"\n## Expected Output\n```\n{observation.expected_output}\n```",
    ]

    if observation.execution_error:
        parts.append(f"\n## Error from Last Attempt\n```\n{observation.execution_error}\n```")

    if observation.execution_result:
        parts.append(f"\n## Result from Last Attempt\n```\n{observation.execution_result}\n```")

    if observation.hint:
        parts.append(f"\n## Hint\n{observation.hint}")

    if history:
        parts.append(f"\n## Previous Attempts\n" + "\n".join(history[-5:]))

    parts.append(f"\n## Steps Remaining: {observation.steps_remaining}")
    parts.append("\nFix the broken SQL query. Return ONLY the corrected query in ```sql blocks.")

    user_prompt = "\n".join(parts)

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        response_text = completion.choices[0].message.content or ""
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return FALLBACK_QUERY

    return extract_sql(response_text)


# ---------------------------------------------------------------------------
# Environment connection — try multiple methods
# ---------------------------------------------------------------------------

async def connect_env() -> SQLDebuggerClient:
    """Connect to the SQL Debugger environment."""
    # Method 1: Docker image (preferred by evaluator)
    try:
        print(f"[DEBUG] Trying from_docker_image({IMAGE_NAME})...", flush=True)
        env = await SQLDebuggerClient.from_docker_image(IMAGE_NAME)
        print(f"[DEBUG] Connected via Docker image", flush=True)
        return env
    except Exception as e:
        print(f"[DEBUG] Docker image failed: {e}", flush=True)

    # Method 2: from_env with HF Space
    try:
        print(f"[DEBUG] Trying from_env({HF_SPACE_ID})...", flush=True)
        env = await SQLDebuggerClient.from_env(HF_SPACE_ID)
        print(f"[DEBUG] Connected via from_env", flush=True)
        return env
    except Exception as e:
        print(f"[DEBUG] from_env failed: {e}", flush=True)

    # Method 3: Direct connection to running HF Space
    try:
        space_url = "https://vatsalhf30-sql-debugger.hf.space"
        print(f"[DEBUG] Trying direct connection to {space_url}...", flush=True)
        env = SQLDebuggerClient(base_url=space_url)
        await env.connect()
        print(f"[DEBUG] Connected via direct WebSocket", flush=True)
        return env
    except Exception as e:
        print(f"[DEBUG] Direct connection failed: {e}", flush=True)

    raise RuntimeError("Could not connect to SQL Debugger environment via any method")


# ---------------------------------------------------------------------------
# Run a single task episode
# ---------------------------------------------------------------------------

async def run_task(env: SQLDebuggerClient, client: OpenAI, seed: int, task_name: str) -> None:
    """Run a single task: reset with seed, step until done, emit [START]/[STEP]/[END]."""
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(seed=seed)
        obs = result.observation
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            message = get_model_message(client, obs, history)

            result = await env.step(SQLAction(query=message))
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done
            error = obs.execution_error if obs.execution_error else None

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=message, reward=reward, done=done, error=error)

            history.append(f"Step {step}: {message!r} -> reward {reward:+.2f}")

            if done:
                break

        score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Error during task {task_name}: {e}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# ---------------------------------------------------------------------------
# Main — runs ALL tasks with separate [START]/[END] for each
# ---------------------------------------------------------------------------

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = None
    try:
        env = await connect_env()
    except Exception as e:
        print(f"[DEBUG] FATAL: Could not connect to environment: {e}", flush=True)
        # Emit START/END for each task so evaluator sees them
        for seed, task_name in TASKS:
            log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
            log_end(success=False, steps=0, score=0.0, rewards=[])
        return

    try:
        for seed, task_name in TASKS:
            await run_task(env, client, seed, task_name)
    finally:
        try:
            if env is not None:
                await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
