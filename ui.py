"""
SQL Debugger — Interactive Web UI

Test the SQL debugger environment, run free-form queries, and explore schemas.
NOT part of the hackathon submission — for development/demo only.

Usage:
    source .venv/bin/activate
    python ui.py
"""

from __future__ import annotations

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
SCHEMA_NAMES = [
    "Users + Orders (users, orders)",
    "Employees + Departments (employees, departments)",
    "Employees + Orders (departments, employees, orders)",
    "Products + Reviews (categories, products, reviews)",
    "School (students, courses, enrollments)",
]
# Trim to actual count
SCHEMA_NAMES = SCHEMA_NAMES[:len(SCHEMA_OPTIONS)]


# -----------------------------------------------------------------------
# Debugger Mode — Play the environment
# -----------------------------------------------------------------------

def reset_env(task_index):
    global current_obs, episode_history
    episode_history = []

    obs = env.reset(seed=task_index)
    current_obs = obs

    state = env.state
    state_text = (
        f"**Episode:** {state.episode_id[:8]}...\n\n"
        f"**Task:** {obs.task_id} ({obs.difficulty})\n\n"
        f"**Step:** {state.step_count}\n\n"
        f"**Best Reward:** {state.best_reward:.2f}"
    )

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
    )


def submit_query(query_text):
    global current_obs, episode_history

    if current_obs is None:
        return ("Reset first!", "", "", "—", "—", "Not started", "", "*No steps yet*", query_text)

    if not query_text.strip():
        return (current_obs.hint, "", "", "—", f"**Steps Left:** {current_obs.steps_remaining}",
                "Enter a query!", get_state_text(), format_history(), query_text)

    obs = env.step(SQLAction(query=query_text.strip()))
    current_obs = obs

    reward_str = f"{obs.reward:.2f}" if obs.reward is not None else "0.00"

    if obs.done and obs.reward and obs.reward >= 0.95:
        icon, status = "✅", f"SOLVED! reward={reward_str}"
    elif obs.done:
        icon, status = "❌", f"Episode over. reward={reward_str}"
    else:
        icon, status = "🔄", f"Keep trying. reward={reward_str}"

    entry = f"**Step {env.state.step_count}** {icon} reward={reward_str}\n`{query_text.strip()[:70]}`"
    if obs.execution_error:
        entry += f"\nError: _{obs.execution_error[:60]}_"
    episode_history.append(entry)

    return (
        obs.hint,
        obs.execution_result or "(no result)",
        obs.execution_error or "",
        f"**Reward:** {reward_str}",
        f"**Steps Left:** {obs.steps_remaining}",
        f"{icon} {status}",
        get_state_text(),
        format_history(),
        "",
    )


def show_answer(task_index):
    task = get_task_by_index(task_index)
    return f"```sql\n{task.correct_query}\n```"


def get_state_text():
    state = env.state
    if current_obs is None:
        return "No active episode"
    return (
        f"**Episode:** {state.episode_id[:8]}...\n\n"
        f"**Task:** {current_obs.task_id} ({current_obs.difficulty})\n\n"
        f"**Step:** {state.step_count}\n\n"
        f"**Best Reward:** {state.best_reward:.2f}"
    )


def format_history():
    if not episode_history:
        return "*No steps yet*"
    return "\n\n---\n\n".join(reversed(episode_history))


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
        return "⚠ Load a schema first!", ""

    if not query_text.strip():
        return "Enter a SQL query.", ""

    rows, error = sandbox_engine.execute(query_text.strip())

    if error:
        return "", f"**Error:** {error}"

    if rows:
        # Format as a table
        lines = [str(row) for row in rows]
        result = f"**{len(rows)} row(s) returned:**\n\n" + "\n".join(lines)
    else:
        result = "*(empty result set)*"

    return result, ""


# -----------------------------------------------------------------------
# Build UI
# -----------------------------------------------------------------------

with gr.Blocks(title="SQL Query Debugger") as demo:

    gr.Markdown("# 🔧 SQL Query Debugger")
    gr.Markdown("Fix broken SQL queries or run free-form queries against live schemas.")

    with gr.Tabs():

        # ---- TAB 1: Debugger ----
        with gr.Tab("🎮 Debugger"):
            with gr.Row():
                with gr.Column(scale=1):
                    task_dd = gr.Dropdown(choices=get_task_choices(), value=get_task_choices()[0],
                                         type="index", label="Select Task")
                    reset_btn = gr.Button("🔄 Reset", variant="primary")
                    reveal_btn = gr.Button("👁 Show Answer")
                    correct_md = gr.Markdown()

                    gr.Markdown("---")
                    state_md = gr.Markdown(value="*Not started*")
                    reward_md = gr.Markdown(value="**Reward:** —")
                    steps_md = gr.Markdown(value="**Steps Left:** —")
                    status_md = gr.Markdown(value="Select a task and reset")

                with gr.Column(scale=2):
                    with gr.Tab("Task Info"):
                        schema_md = gr.Markdown(label="Schema")
                        broken_md = gr.Markdown(label="Broken Query")
                        expected_tb = gr.Textbox(label="Expected Output", lines=5, interactive=False)

                    with gr.Tab("Submit Fix"):
                        query_tb = gr.Textbox(label="Your SQL Query", lines=4,
                                              placeholder="Type corrected SQL here...")
                        submit_btn = gr.Button("▶ Submit", variant="primary")
                        hint_tb = gr.Textbox(label="Hint", lines=2, interactive=False)

                    with gr.Tab("Results"):
                        result_tb = gr.Textbox(label="Query Result", lines=8, interactive=False)
                        error_tb = gr.Textbox(label="Error", lines=3, interactive=False)

                    with gr.Tab("History"):
                        history_md = gr.Markdown(value="*No steps yet*")

            reset_btn.click(reset_env, [task_dd],
                [schema_md, broken_md, expected_tb, hint_tb, result_tb, error_tb,
                 reward_md, steps_md, status_md, state_md, history_md, query_tb])
            submit_btn.click(submit_query, [query_tb],
                [hint_tb, result_tb, error_tb, reward_md, steps_md, status_md,
                 state_md, history_md, query_tb])
            query_tb.submit(submit_query, [query_tb],
                [hint_tb, result_tb, error_tb, reward_md, steps_md, status_md,
                 state_md, history_md, query_tb])
            reveal_btn.click(show_answer, [task_dd], [correct_md])

        # ---- TAB 2: SQL Sandbox ----
        with gr.Tab("🧪 SQL Sandbox"):
            gr.Markdown("Run **any SQL query** against the available schemas. No scoring — just explore.")

            with gr.Row():
                with gr.Column(scale=1):
                    schema_dd = gr.Dropdown(choices=SCHEMA_NAMES,
                                            value=SCHEMA_NAMES[0] if SCHEMA_NAMES else None,
                                            type="index", label="Select Schema")
                    load_btn = gr.Button("📂 Load Schema", variant="primary")
                    sandbox_schema_md = gr.Markdown(value="*Select and load a schema*")

                with gr.Column(scale=2):
                    sandbox_query = gr.Textbox(label="SQL Query", lines=5,
                        placeholder="SELECT * FROM users;\nSELECT name, COUNT(*) FROM orders GROUP BY user_id;")
                    run_btn = gr.Button("▶ Run Query", variant="primary")
                    sandbox_result = gr.Markdown(value="")
                    sandbox_error = gr.Markdown(value="")

            load_btn.click(load_sandbox_schema, [schema_dd], [sandbox_schema_md])
            run_btn.click(run_sandbox_query, [sandbox_query], [sandbox_result, sandbox_error])
            sandbox_query.submit(run_sandbox_query, [sandbox_query], [sandbox_result, sandbox_error])

        # ---- TAB 3: Task Overview ----
        with gr.Tab("📋 All Tasks"):
            task_table = "| # | ID | Difficulty | Description | Max Steps |\n"
            task_table += "|---|-----|-----------|-------------|----------|\n"
            for i, t in enumerate(ALL_TASKS):
                mode = "🔒" if t.broken_query else "🎲"
                task_table += f"| {i} | {t.task_id} | {t.difficulty} {mode} | {t.description} | {t.max_steps} |\n"
            gr.Markdown(task_table)
            gr.Markdown("🔒 = static (predefined bug) | 🎲 = dynamic (random bug injection)")


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
