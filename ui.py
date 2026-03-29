"""
SQL Debugger — Interactive Web UI

A local Gradio interface for testing the SQL debugger environment in real-time.
NOT part of the hackathon submission — for development/demo only.

Usage:
    source .venv/bin/activate
    pip install gradio
    python ui.py
"""

from __future__ import annotations

import json
import gradio as gr

from sql_debugger.server.environment import SQLDebuggerEnv
from sql_debugger.models import SQLAction
from sql_debugger.server.tasks import ALL_TASKS, get_task_by_index

# Global environment instance for the UI
env = SQLDebuggerEnv()
current_obs = None
episode_history = []


def get_task_choices():
    """Return task choices for the dropdown."""
    return [f"[{t.task_id}] ({t.difficulty}) {t.description}" for t in ALL_TASKS]


def reset_env(task_index):
    """Reset environment with selected task."""
    global current_obs, episode_history
    episode_history = []

    obs = env.reset(seed=task_index)
    current_obs = obs

    schema_display = f"```sql\n{obs.schema_description}\n```"
    broken_display = f"```sql\n{obs.broken_query}\n```"

    state = env.state
    state_text = (
        f"Episode: {state.episode_id[:8]}...\n"
        f"Task: {obs.task_id} ({obs.difficulty})\n"
        f"Step: {state.step_count}/{obs.steps_remaining + state.step_count}\n"
        f"Best Reward: {state.best_reward:.2f}"
    )

    return (
        schema_display,           # schema
        broken_display,           # broken query
        obs.expected_output,      # expected output
        obs.hint,                 # hint
        "",                       # execution result
        "",                       # execution error
        f"**Reward:** 0.00",      # reward
        f"**Steps Remaining:** {obs.steps_remaining}",  # steps
        "**Status:** Ready — submit your fix!",  # status
        state_text,               # state info
        format_history(),         # history
        "",                       # query input (clear it)
    )


def submit_query(query_text):
    """Submit a SQL query to the environment."""
    global current_obs, episode_history

    if current_obs is None:
        return (
            "", "", "Reset the environment first!", "",
            "**Reward:** —", "**Steps Remaining:** —",
            "**Status:** Not started", "", format_history(), query_text,
        )

    if not query_text.strip():
        return (
            current_obs.hint,
            current_obs.execution_result if current_obs.execution_result else "",
            current_obs.execution_error if current_obs.execution_error else "",
            "**Reward:** —",
            f"**Steps Remaining:** {current_obs.steps_remaining}",
            "**Status:** Enter a query!",
            get_state_text(),
            format_history(),
            query_text,
        )

    obs = env.step(SQLAction(query=query_text.strip()))
    current_obs = obs

    # Build history entry
    reward_str = f"{obs.reward:.2f}" if obs.reward is not None else "0.00"
    status_icon = "✅" if obs.done and obs.reward and obs.reward >= 0.95 else "❌" if obs.done else "🔄"
    entry = f"**Step {env.state.step_count}** {status_icon} | reward={reward_str} | `{query_text.strip()[:60]}`"
    if obs.execution_error:
        entry += f"\n  Error: {obs.execution_error[:80]}"
    episode_history.append(entry)

    # Status message
    if obs.done and obs.reward and obs.reward >= 0.95:
        status = "**Status:** ✅ SOLVED! Query produces the expected output."
    elif obs.done:
        status = f"**Status:** ❌ Episode over. Final reward: {reward_str}"
    else:
        status = f"**Status:** 🔄 Keep trying! Reward so far: {reward_str}"

    exec_result = obs.execution_result if obs.execution_result else "(no result)"
    exec_error = obs.execution_error if obs.execution_error else ""

    reward_display = f"**Reward:** {reward_str}"
    steps_display = f"**Steps Remaining:** {obs.steps_remaining}"

    return (
        obs.hint,
        exec_result,
        exec_error,
        reward_display,
        steps_display,
        status,
        get_state_text(),
        format_history(),
        "",  # clear input
    )


def get_state_text():
    state = env.state
    if current_obs is None:
        return "No active episode"
    return (
        f"Episode: {state.episode_id[:8]}...\n"
        f"Task: {current_obs.task_id} ({current_obs.difficulty})\n"
        f"Step: {state.step_count}\n"
        f"Best Reward: {state.best_reward:.2f}"
    )


def format_history():
    if not episode_history:
        return "*No steps yet*"
    return "\n\n".join(reversed(episode_history))


def show_answer(task_index):
    """Show the correct answer for the current task."""
    task = get_task_by_index(task_index)
    return f"```sql\n{task.correct_query}\n```"


# ---------------------------------------------------------------------------
# Build Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="SQL Query Debugger") as demo:
    gr.Markdown("# 🔧 SQL Query Debugger — Interactive Tester")
    gr.Markdown("Fix broken SQL queries against a live SQLite database. Select a task, read the schema, and submit your fix.")

    with gr.Row():
        with gr.Column(scale=1):
            task_dropdown = gr.Dropdown(
                choices=get_task_choices(),
                value=get_task_choices()[0],
                type="index",
                label="Select Task",
            )
            reset_btn = gr.Button("🔄 Reset Environment", variant="primary")
            reveal_btn = gr.Button("👁 Show Correct Answer", variant="secondary")
            correct_answer = gr.Markdown(label="Correct Answer", visible=True)

            gr.Markdown("---")
            state_info = gr.Markdown(label="State", value="*Not started*")
            reward_display = gr.Markdown(value="**Reward:** —")
            steps_display = gr.Markdown(value="**Steps Remaining:** —")
            status_display = gr.Markdown(value="**Status:** Select a task and reset")

        with gr.Column(scale=2):
            with gr.Tab("Task"):
                schema_display = gr.Markdown(label="Database Schema")
                broken_display = gr.Markdown(label="Broken Query")
                expected_display = gr.Textbox(label="Expected Output", lines=6, interactive=False)

            with gr.Tab("Submit Fix"):
                query_input = gr.Textbox(
                    label="Your SQL Query",
                    placeholder="Type your corrected SQL query here...",
                    lines=4,
                )
                submit_btn = gr.Button("▶ Submit Query", variant="primary")
                hint_display = gr.Textbox(label="Hint", lines=2, interactive=False)

            with gr.Tab("Results"):
                exec_result = gr.Textbox(label="Execution Result", lines=8, interactive=False)
                exec_error = gr.Textbox(label="Execution Error", lines=3, interactive=False)

            with gr.Tab("History"):
                history_display = gr.Markdown(value="*No steps yet*")

    # Wire up events
    reset_btn.click(
        fn=reset_env,
        inputs=[task_dropdown],
        outputs=[
            schema_display, broken_display, expected_display, hint_display,
            exec_result, exec_error, reward_display, steps_display,
            status_display, state_info, history_display, query_input,
        ],
    )

    submit_btn.click(
        fn=submit_query,
        inputs=[query_input],
        outputs=[
            hint_display, exec_result, exec_error,
            reward_display, steps_display, status_display,
            state_info, history_display, query_input,
        ],
    )

    # Also submit on Enter
    query_input.submit(
        fn=submit_query,
        inputs=[query_input],
        outputs=[
            hint_display, exec_result, exec_error,
            reward_display, steps_display, status_display,
            state_info, history_display, query_input,
        ],
    )

    reveal_btn.click(
        fn=show_answer,
        inputs=[task_dropdown],
        outputs=[correct_answer],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        theme=gr.themes.Soft(),
    )
