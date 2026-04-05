"""
SQL Debugger — Interactive Web UI

Test the SQL debugger environment with manual or auto-solve modes.
Explore schemas, view reward decomposition, and iterate until solved.

Usage:
    source .venv/bin/activate
    python ui.py
"""

from __future__ import annotations

import os
import re
import time

import gradio as gr

from sql_debugger.server.environment import SQLDebuggerEnv
from sql_debugger.models import SQLAction
from sql_debugger.server.tasks import ALL_TASKS, get_task_by_index
from sql_debugger.server.sql_engine import SQLiteEngine

# Global state
env = SQLDebuggerEnv()
current_obs = None
episode_history = []

# Sandbox engine for free-form queries
sandbox_engine = SQLiteEngine()
sandbox_schema_loaded = None


def get_task_choices():
    return [f"[{i}] {t.task_id} ({t.difficulty}) — {t.description}" for i, t in enumerate(ALL_TASKS)]


def get_schema_choices():
    """Get unique schemas for sandbox mode."""
    schemas = {}
    for t in ALL_TASKS:
        key = t.schema_sql.strip()[:80]
        if key not in schemas:
            schemas[key] = (t.task_id, t.schema_sql, t.seed_data_sql)
    return list(schemas.values())


SCHEMA_OPTIONS = get_schema_choices()
SCHEMA_NAMES = []
for _, schema_sql, _ in SCHEMA_OPTIONS:
    # Auto-generate schema names from CREATE TABLE statements
    tables = re.findall(r'CREATE TABLE (\w+)', schema_sql, re.IGNORECASE)
    SCHEMA_NAMES.append(", ".join(tables) if tables else "Unknown schema")


# -----------------------------------------------------------------------
# Debugger Mode — Play the environment
# -----------------------------------------------------------------------

def reset_env(task_index):
    global current_obs, episode_history
    episode_history = []

    obs = env.reset(seed=task_index)
    current_obs = obs

    state_text = get_state_text()
    components_text = ""

    return (
        f"```sql\n{obs.schema_description}\n```",
        f"```sql\n{obs.broken_query}\n```",
        obs.expected_output,
        obs.hint,
        "", "",
        "**Reward:** 0.00",
        f"**Steps Left:** {obs.steps_remaining}",
        "Ready — submit your fix!",
        state_text,
        "*No steps yet*",
        "",
        components_text,
    )


def submit_query(query_text):
    global current_obs, episode_history

    if current_obs is None:
        return ("Reset first!", "", "", "---", "---", "Not started", "", "*No steps yet*", query_text, "")

    if not query_text.strip():
        return (current_obs.hint, "", "", "---", f"**Steps Left:** {current_obs.steps_remaining}",
                "Enter a query!", get_state_text(), format_history(), query_text, "")

    obs = env.step(SQLAction(query=query_text.strip()))
    current_obs = obs

    reward_str = f"{obs.reward:.2f}" if obs.reward is not None else "0.00"

    if obs.done and obs.reward and obs.reward >= 0.95:
        icon, status = "SOLVED!", f"SOLVED! reward={reward_str}"
    elif obs.done:
        icon, status = "FAILED", f"Episode over. reward={reward_str}"
    else:
        icon, status = "...", f"Keep trying. reward={reward_str}"

    entry = f"**Step {env.state.step_count}** [{icon}] reward={reward_str}\n`{query_text.strip()[:80]}`"
    if obs.execution_error:
        entry += f"\nError: _{obs.execution_error[:80]}_"
    episode_history.append(entry)

    # Format reward components
    components = obs.metadata.get("reward_components", {})
    components_text = format_components(components)

    return (
        obs.hint,
        obs.execution_result or "(no result)",
        obs.execution_error or "",
        f"**Reward:** {reward_str}",
        f"**Steps Left:** {obs.steps_remaining}",
        f"{icon} — {status}",
        get_state_text(),
        format_history(),
        "",
        components_text,
    )


def auto_solve(task_index, max_iters):
    """Auto-iterate: reset and keep submitting the broken query with progressive fixes."""
    global current_obs, episode_history
    episode_history = []

    max_iters = int(max_iters) if max_iters else 5

    obs = env.reset(seed=task_index)
    current_obs = obs
    task = env._current_task

    # Try the correct query to show it can be solved
    # In a real scenario, an LLM would generate these attempts
    # For demo, we simulate iterative debugging:

    attempts = []

    # Attempt 1: submit the broken query as-is (shows error)
    try:
        obs = env.step(SQLAction(query=obs.broken_query))
        current_obs = obs
        reward_str = f"{obs.reward:.2f}" if obs.reward is not None else "0.00"
        attempts.append(f"**Step 1** — Submit broken query as-is\n`{obs.broken_query[:80]}`\nReward: {reward_str}")
        if obs.execution_error:
            attempts.append(f"Error: _{obs.execution_error[:80]}_")
        episode_history = list(attempts)

        if obs.done:
            return _build_auto_result(obs, attempts)
    except Exception:
        pass

    # Attempt 2+: submit the correct query (simulates the agent fixing it)
    if not current_obs.done:
        try:
            obs = env.step(SQLAction(query=task.correct_query))
            current_obs = obs
            reward_str = f"{obs.reward:.2f}" if obs.reward is not None else "0.00"
            attempts.append(f"\n**Step 2** — Submit corrected query\n`{task.correct_query[:80]}`\nReward: {reward_str}")
            episode_history = list(attempts)
        except Exception:
            pass

    return _build_auto_result(current_obs, attempts)


def _build_auto_result(obs, attempts):
    reward_str = f"{obs.reward:.2f}" if obs.reward is not None else "0.00"
    components = obs.metadata.get("reward_components", {})

    if obs.done and obs.reward and obs.reward >= 0.95:
        status = f"SOLVED in {env.state.step_count} steps! reward={reward_str}"
    elif obs.done:
        status = f"FAILED after {env.state.step_count} steps. reward={reward_str}"
    else:
        status = f"In progress... step {env.state.step_count}, reward={reward_str}"

    return (
        f"```sql\n{obs.schema_description}\n```",
        f"```sql\n{obs.broken_query if hasattr(obs, 'broken_query') else ''}\n```",
        obs.expected_output,
        obs.hint,
        obs.execution_result or "(no result)",
        obs.execution_error or "",
        f"**Reward:** {reward_str}",
        f"**Steps Left:** {obs.steps_remaining}",
        status,
        get_state_text(),
        "\n\n---\n\n".join(reversed(attempts)),
        "",
        format_components(components),
    )


def show_answer(task_index):
    task = get_task_by_index(task_index)
    return f"```sql\n{task.correct_query}\n```"


def get_state_text():
    state = env.state
    if current_obs is None:
        return "No active episode"

    analytics_text = ""
    analytics = current_obs.metadata.get("analytics", {})
    if analytics:
        analytics_text = (
            f"\n\n**Analytics:**\n"
            f"- Regressions: {analytics.get('regression_count', 0)}\n"
            f"- Unique queries: {analytics.get('unique_queries', 0)}\n"
            f"- Bug fixed: {'Yes' if analytics.get('was_bug_fixed') else 'No'}"
        )

    curriculum = current_obs.metadata.get("curriculum", {})
    curriculum_text = ""
    if curriculum:
        curriculum_text = f"\n\n**Curriculum:** Level {curriculum.get('current_level', 0)} ({curriculum.get('level_name', 'unknown')})"

    return (
        f"**Episode:** {state.episode_id[:8]}...\n\n"
        f"**Task:** {current_obs.task_id} ({current_obs.difficulty})\n\n"
        f"**Step:** {state.step_count}\n\n"
        f"**Best Reward:** {state.best_reward:.2f}"
        f"{curriculum_text}{analytics_text}"
    )


def format_history():
    if not episode_history:
        return "*No steps yet*"
    return "\n\n---\n\n".join(reversed(episode_history))


def format_components(components):
    if not components:
        return ""
    lines = ["| Component | Score |", "|-----------|-------|"]
    for k, v in components.items():
        if k == "total":
            lines.append(f"| **{k}** | **{v:.3f}** |")
        else:
            lines.append(f"| {k} | {v:.3f} |")
    return "\n".join(lines)


# -----------------------------------------------------------------------
# Sandbox Mode — Run any SQL against any schema
# -----------------------------------------------------------------------

def load_sandbox_schema(schema_index):
    global sandbox_engine, sandbox_schema_loaded
    if schema_index is None or schema_index >= len(SCHEMA_OPTIONS):
        return "Select a schema first."

    _, schema_sql, seed_sql = SCHEMA_OPTIONS[schema_index]
    sandbox_engine = SQLiteEngine()
    sandbox_engine.setup(schema_sql, seed_sql)
    sandbox_schema_loaded = schema_index

    return f"```sql\n{schema_sql.strip()}\n```"


def run_sandbox_query(query_text):
    if sandbox_schema_loaded is None:
        return "Load a schema first!", ""

    if not query_text.strip():
        return "Enter a SQL query.", ""

    rows, error = sandbox_engine.execute(query_text.strip())

    if error:
        return "", f"**Error:** {error}"

    if rows:
        lines = [str(row) for row in rows]
        result = f"**{len(rows)} row(s) returned:**\n\n" + "\n".join(lines)
    else:
        result = "*(empty result set)*"

    return result, ""


# -----------------------------------------------------------------------
# Build UI
# -----------------------------------------------------------------------

with gr.Blocks(title="SQL Query Debugger") as demo:

    gr.Markdown("# SQL Query Debugger")
    gr.Markdown(
        f"Debug broken SQL queries against live schemas. "
        f"**{len(ALL_TASKS)} tasks** across {len(set(t.difficulty for t in ALL_TASKS))} difficulty levels."
    )

    with gr.Tabs():

        # ---- TAB 1: Debugger ----
        with gr.Tab("Debugger"):
            with gr.Row():
                with gr.Column(scale=1):
                    task_dd = gr.Dropdown(choices=get_task_choices(), value=get_task_choices()[0],
                                         type="index", label="Select Task")
                    with gr.Row():
                        reset_btn = gr.Button("Reset", variant="primary")
                        reveal_btn = gr.Button("Show Answer")
                    correct_md = gr.Markdown()

                    gr.Markdown("---")
                    gr.Markdown("**Auto-Solve**")
                    max_iters_slider = gr.Slider(minimum=1, maximum=15, value=5, step=1,
                                                  label="Max Iterations")
                    auto_btn = gr.Button("Auto-Iterate", variant="secondary")

                    gr.Markdown("---")
                    state_md = gr.Markdown(value="*Not started*")
                    reward_md = gr.Markdown(value="**Reward:** ---")
                    steps_md = gr.Markdown(value="**Steps Left:** ---")
                    status_md = gr.Markdown(value="Select a task and reset")

                with gr.Column(scale=2):
                    with gr.Tab("Task Info"):
                        schema_md = gr.Markdown(label="Schema")
                        broken_md = gr.Markdown(label="Broken Query")
                        expected_tb = gr.Textbox(label="Expected Output", lines=5, interactive=False)

                    with gr.Tab("Submit Fix"):
                        query_tb = gr.Textbox(label="Your SQL Query", lines=4,
                                              placeholder="Type corrected SQL here...")
                        submit_btn = gr.Button("Submit", variant="primary")
                        hint_tb = gr.Textbox(label="Hint", lines=2, interactive=False)

                    with gr.Tab("Results"):
                        result_tb = gr.Textbox(label="Query Result", lines=8, interactive=False)
                        error_tb = gr.Textbox(label="Error", lines=3, interactive=False)

                    with gr.Tab("Reward Breakdown"):
                        components_md = gr.Markdown(value="*Submit a query to see reward breakdown*")

                    with gr.Tab("History"):
                        history_md = gr.Markdown(value="*No steps yet*")

            all_debugger_outputs = [
                schema_md, broken_md, expected_tb, hint_tb, result_tb, error_tb,
                reward_md, steps_md, status_md, state_md, history_md, query_tb,
                components_md,
            ]

            reset_btn.click(reset_env, [task_dd], all_debugger_outputs)

            submit_outputs = [
                hint_tb, result_tb, error_tb, reward_md, steps_md, status_md,
                state_md, history_md, query_tb, components_md,
            ]
            submit_btn.click(submit_query, [query_tb], submit_outputs)
            query_tb.submit(submit_query, [query_tb], submit_outputs)

            auto_btn.click(auto_solve, [task_dd, max_iters_slider], all_debugger_outputs)
            reveal_btn.click(show_answer, [task_dd], [correct_md])

        # ---- TAB 2: SQL Sandbox ----
        with gr.Tab("SQL Sandbox"):
            gr.Markdown("Run **any SQL query** against the available schemas. No scoring — just explore.")

            with gr.Row():
                with gr.Column(scale=1):
                    schema_dd = gr.Dropdown(choices=SCHEMA_NAMES,
                                            value=SCHEMA_NAMES[0] if SCHEMA_NAMES else None,
                                            type="index", label="Select Schema")
                    load_btn = gr.Button("Load Schema", variant="primary")
                    sandbox_schema_md = gr.Markdown(value="*Select and load a schema*")

                with gr.Column(scale=2):
                    sandbox_query = gr.Textbox(label="SQL Query", lines=5,
                        placeholder="SELECT * FROM users;\nSELECT name, COUNT(*) FROM orders GROUP BY user_id;")
                    run_btn = gr.Button("Run Query", variant="primary")
                    sandbox_result = gr.Markdown(value="")
                    sandbox_error = gr.Markdown(value="")

            load_btn.click(load_sandbox_schema, [schema_dd], [sandbox_schema_md])
            run_btn.click(run_sandbox_query, [sandbox_query], [sandbox_result, sandbox_error])
            sandbox_query.submit(run_sandbox_query, [sandbox_query], [sandbox_result, sandbox_error])

        # ---- TAB 3: Task Overview ----
        with gr.Tab("All Tasks"):
            # Group by difficulty
            for diff in ["easy", "medium", "hard"]:
                diff_tasks = [(i, t) for i, t in enumerate(ALL_TASKS) if t.difficulty == diff]
                gr.Markdown(f"### {diff.upper()} ({len(diff_tasks)} tasks)")
                task_table = "| # | ID | Description | Max Steps | Type |\n"
                task_table += "|---|-----|-------------|----------|------|\n"
                for i, t in diff_tasks:
                    mode = "Static" if t.broken_query else "Dynamic"
                    task_table += f"| {i} | {t.task_id} | {t.description[:60]} | {t.max_steps} | {mode} |\n"
                gr.Markdown(task_table)

        # ---- TAB 4: Analytics ----
        with gr.Tab("Analytics"):
            gr.Markdown("### Training Analytics")
            gr.Markdown("View aggregate statistics from all episodes run in this session.")

            def get_analytics_display():
                summary = SQLDebuggerEnv._analytics.get_summary()
                if summary["total_episodes"] == 0:
                    return "No episodes completed yet. Run some tasks first!"

                lines = [
                    f"**Total Episodes:** {summary['total_episodes']}",
                    f"**Average Reward:** {summary['avg_reward']:.3f}",
                    f"**Success Rate:** {summary['success_rate']:.1%}",
                    f"**Avg Regression Count:** {summary['avg_regression_count']:.2f}",
                    "",
                    "**Success Rate by Difficulty:**",
                ]
                for diff, rate in summary.get("success_rate_by_difficulty", {}).items():
                    lines.append(f"- {diff}: {rate:.1%}")

                lines.append("")
                lines.append("**Average Reward by Difficulty:**")
                for diff, avg in summary.get("avg_reward_by_difficulty", {}).items():
                    lines.append(f"- {diff}: {avg:.3f}")

                curriculum = SQLDebuggerEnv._curriculum.get_info()
                lines.extend([
                    "",
                    f"**Curriculum Level:** {curriculum['current_level']} ({curriculum['level_name']})",
                    f"**Rolling Avg Reward:** {curriculum['rolling_avg_reward']:.3f}",
                ])

                return "\n\n".join(lines)

            analytics_display = gr.Markdown(value="Click refresh to load analytics.")
            refresh_btn = gr.Button("Refresh Analytics", variant="primary")
            refresh_btn.click(get_analytics_display, [], [analytics_display])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
