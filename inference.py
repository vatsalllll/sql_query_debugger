"""
SQL Debugger — Baseline Inference Script

Runs an LLM agent against SQL debugging tasks and reports scores.
Uses structured [START], [STEP], [END] logging format required by OpenEnv evaluation.

Environment variables:
    API_BASE_URL  — LLM API endpoint (default: https://router.huggingface.co/v1)
    MODEL_NAME    — Model identifier (default: Qwen/Qwen2.5-Coder-32B-Instruct)
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

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-Coder-32B-Instruct")
API_KEY = os.getenv("HF_TOKEN", "")
ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")

BENCHMARK = "sql_debugger"
MAX_STEPS = 12
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

# Task seeds to evaluate
TASK_SEEDS = list(range(9)) + [100, 200, 300, 400, 500]


# ---------------------------------------------------------------------------
# Structured Logging — Required format for evaluation
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
    """Extract SQL query from model response (```sql blocks or raw text)."""
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


def build_prompt(observation, history: list[str]) -> str:
    """Build user prompt from current observation and history."""
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
        parts.append(f"\n## Previous Attempts\n" + "\n".join(history))

    parts.append(f"\n## Steps Remaining: {observation.steps_remaining}")
    parts.append("\nFix the broken SQL query. Return ONLY the corrected query in ```sql blocks.")

    return "\n".join(parts)


def get_model_message(
    client: OpenAI,
    observation,
    history: list[str],
) -> str:
    """Call the LLM and return the extracted SQL query."""
    user_prompt = build_prompt(observation, history)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        response_text = completion.choices[0].message.content or ""
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}. Using fallback.", flush=True)
        response_text = f"```sql\n{FALLBACK_QUERY}\n```"

    return extract_sql(response_text)


# ---------------------------------------------------------------------------
# Main — async entry point matching OpenEnv evaluation format
# ---------------------------------------------------------------------------

async def run_task(env, client: OpenAI, seed: int, task_name: str) -> float:
    """Run a single task and return the final score."""
    from sql_debugger.models import SQLAction

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = env.reset(seed=seed)
        observation = result.observation
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            query = get_model_message(client, observation, history)

            result = env.step(SQLAction(query=query))
            observation = result.observation

            reward = result.reward or 0.0
            done = result.done
            error = observation.execution_error if observation.execution_error else None

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=query, reward=reward, done=done, error=error)

            history.append(f"Step {step}: reward={reward:.2f}")
            if error:
                history[-1] += f" [ERROR: {error[:50]}]"

            if done:
                break

        max_total_reward = MAX_STEPS
        score = sum(rewards) / max_total_reward if max_total_reward > 0 else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task {task_name} error: {exc}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main() -> None:
    """Run baseline inference across all tasks."""
    from sql_debugger import SQLDebuggerClient, SQLAction

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    print(f"[DEBUG] API: {API_BASE_URL}", flush=True)
    print(f"[DEBUG] Model: {MODEL_NAME}", flush=True)
    print(f"[DEBUG] Environment: {ENV_URL}", flush=True)
    print(f"[DEBUG] Tasks: {len(TASK_SEEDS)} seeds", flush=True)

    start_time = time.time()
    all_scores = []

    with SQLDebuggerClient(base_url=ENV_URL).sync() as env:
        for seed in TASK_SEEDS:
            # Get task name via reset peek
            result = env.reset(seed=seed)
            task_name = f"{result.observation.task_id}_{result.observation.difficulty}"

            score = await run_task(env, client, seed, task_name)
            all_scores.append((seed, task_name, score))

    elapsed = time.time() - start_time

    # Summary
    print(f"\n[DEBUG] === RESULTS SUMMARY ===", flush=True)
    print(f"[DEBUG] {'Seed':<6} {'Task':<30} {'Score':<10}", flush=True)
    print(f"[DEBUG] {'-' * 46}", flush=True)
    for seed, task_name, score in all_scores:
        print(f"[DEBUG] {seed:<6} {task_name:<30} {score:<10.4f}", flush=True)
    avg = sum(s for _, _, s in all_scores) / len(all_scores) if all_scores else 0
    print(f"[DEBUG] {'-' * 46}", flush=True)
    print(f"[DEBUG] {'AVG':<36} {avg:<10.4f}", flush=True)
    print(f"[DEBUG] Time: {elapsed:.1f}s / 1200s max", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
