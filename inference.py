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
API_KEY = os.getenv("HF_TOKEN", "")

IMAGE_NAME = "vatsalhf30/sql-debugger"
BENCHMARK = "sql_debugger"
TASK_NAME = "sql_debug"
MAX_STEPS = 12
MAX_TOTAL_REWARD = 1.0
SUCCESS_SCORE_THRESHOLD = 0.8
TEMPERATURE = 0.1
MAX_TOKENS = 512
FALLBACK_QUERY = "SELECT 1;"

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
    step: int,
    observation: SQLObservation,
    last_reward: float,
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
# Main — async entry point matching OpenEnv evaluation format
# ---------------------------------------------------------------------------

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = await SQLDebuggerClient.from_docker_image(IMAGE_NAME)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset()
        obs = result.observation
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            message = get_model_message(client, step, obs, last_reward, history)

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

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error (container cleanup): {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    asyncio.run(main())
