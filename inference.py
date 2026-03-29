"""
SQL Debugger — Baseline Inference Script

Runs an LLM agent against all 9 SQL debugging tasks and reports scores.
Uses OpenAI-compatible API via environment variables.

Environment variables:
    API_BASE_URL  — LLM API endpoint (default: https://router.huggingface.co/v1)
    MODEL_NAME    — Model identifier (default: Qwen/Qwen2.5-Coder-32B-Instruct)
    HF_TOKEN      — API key for authentication
"""

from __future__ import annotations

import os
import re
import sys
import time

from openai import OpenAI

from sql_debugger import SQLDebuggerClient, SQLAction

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-Coder-32B-Instruct")
API_KEY = os.getenv("HF_TOKEN", "")

ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")

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

TEMPERATURE = 0.1
MAX_TOKENS = 512
FALLBACK_QUERY = "SELECT 1;"
NUM_TASKS = 9


def extract_sql(response_text: str) -> str:
    """Extract SQL query from model response (```sql blocks or raw text)."""
    # Try ```sql blocks first
    pattern = r"```sql\s*(.*?)\s*```"
    matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[-1].strip()

    # Try ``` blocks without language tag
    pattern = r"```\s*(.*?)\s*```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return matches[-1].strip()

    # Fallback: return entire response stripped
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


def run_episode(env, client: OpenAI, seed: int) -> tuple[float, int]:
    """Run a single debugging episode. Returns (final_reward, steps_taken)."""
    result = env.reset(seed=seed)
    observation = result.observation
    history = []
    final_reward = 0.0
    steps = 0

    while not result.done:
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
            print(f"    Model request failed: {exc}. Using fallback.")
            response_text = f"```sql\n{FALLBACK_QUERY}\n```"

        query = extract_sql(response_text)
        steps += 1
        print(f"    Step {steps}: {query[:80]}{'...' if len(query) > 80 else ''}")

        result = env.step(SQLAction(query=query))
        observation = result.observation
        final_reward = result.reward or 0.0

        error_flag = f" [ERROR: {observation.execution_error[:50]}]" if observation.execution_error else ""
        history.append(f"Step {steps}: reward={final_reward:.2f}{error_flag}")

        if result.done:
            break

    return final_reward, steps


def main():
    """Run baseline inference across all tasks."""
    print("=" * 60)
    print("SQL Debugger — Baseline Inference")
    print("=" * 60)
    print(f"API: {API_BASE_URL}")
    print(f"Model: {MODEL_NAME}")
    print(f"Environment: {ENV_URL}")
    print()

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    total_reward = 0.0
    results = []
    start_time = time.time()

    with SQLDebuggerClient(base_url=ENV_URL).sync() as env:
        for seed in range(NUM_TASKS):
            result = env.reset(seed=seed)
            task_id = result.observation.task_id
            difficulty = result.observation.difficulty
            print(f"[{seed + 1}/{NUM_TASKS}] Task: {task_id} ({difficulty})")

            # Re-reset to start fresh (the above reset was just to get task info)
            reward, steps = run_episode(env, client, seed)
            total_reward += reward
            results.append((task_id, difficulty, reward, steps))
            print(f"    Result: reward={reward:.2f}, steps={steps}")
            print()

    elapsed = time.time() - start_time

    # Summary
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Task':<12} {'Difficulty':<10} {'Reward':<10} {'Steps':<6}")
    print("-" * 40)
    for task_id, difficulty, reward, steps in results:
        print(f"{task_id:<12} {difficulty:<10} {reward:<10.2f} {steps:<6}")
    print("-" * 40)
    print(f"{'TOTAL':<22} {total_reward:<10.2f}")
    print(f"{'AVERAGE':<22} {total_reward / NUM_TASKS:<10.2f}")
    print(f"\nTime elapsed: {elapsed:.1f}s")
    print(f"Max allowed: 1200s (20 min)")


if __name__ == "__main__":
    main()
