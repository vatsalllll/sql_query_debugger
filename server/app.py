"""
FastAPI application for the SQL Debugger Environment.
"""

from sql_debugger.models import SQLAction, SQLObservation
from sql_debugger.server.environment import SQLDebuggerEnv
from openenv.core.env_server import create_app

app = create_app(SQLDebuggerEnv, SQLAction, SQLObservation, env_name="sql_debugger")


@app.get("/analytics")
def get_analytics():
    """Return aggregate training statistics across all episodes."""
    return SQLDebuggerEnv._analytics.get_summary()


@app.get("/curriculum")
def get_curriculum():
    """Return current curriculum state."""
    return SQLDebuggerEnv._curriculum.get_info()


def main():
    """Main entry point for running the server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
