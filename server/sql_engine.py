"""
SQLite in-memory execution engine.

Provides deterministic query execution with timeout protection.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from typing import List, Optional, Tuple


class SQLiteEngine:
    """In-memory SQLite executor with schema setup and safe query running."""

    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None
        self._create_connection()

    def _create_connection(self):
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")

    def setup(self, schema_sql: str, seed_data_sql: str) -> None:
        """Execute DDL and seed data to prepare the database."""
        cursor = self._conn.cursor()
        cursor.executescript(schema_sql)
        cursor.executescript(seed_data_sql)
        self._conn.commit()

    def execute(self, query: str, timeout_s: int = 5) -> Tuple[Optional[List[tuple]], Optional[str]]:
        """
        Execute a SQL query and return (rows, None) on success or (None, error) on failure.

        Uses SQLite's progress_handler for thread-safe timeout.
        """
        deadline = time.monotonic() + timeout_s

        def _check_timeout():
            if time.monotonic() > deadline:
                return 1  # Non-zero cancels the operation
            return 0

        try:
            # Check every 1000 SQLite VM instructions
            self._conn.set_progress_handler(_check_timeout, 1000)
            cursor = self._conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows, None
        except sqlite3.OperationalError as e:
            if "interrupted" in str(e).lower():
                return None, "Query execution timed out (exceeded 5 seconds)"
            return None, str(e)
        except sqlite3.Error as e:
            return None, str(e)
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"
        finally:
            self._conn.set_progress_handler(None, 0)

    def explain_query(self, query: str) -> Optional[str]:
        """Return the SQLite query plan for the given query as a string.

        Executes ``EXPLAIN QUERY PLAN {query}`` and formats each row of the
        plan into a human-readable string. Returns None if an error occurs.
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            rows = cursor.fetchall()
            return "\n".join(str(row) for row in rows)
        except sqlite3.Error:
            return None

    def get_table_names(self) -> List[str]:
        """Return a list of all table names in the current database."""
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_column_names(self, table_name: str) -> List[str]:
        """Return a list of column names for the given table.

        Uses ``PRAGMA table_info`` to retrieve column metadata. Returns an
        empty list if the table does not exist or an error occurs.
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    @staticmethod
    def categorize_error(error_msg: str) -> str:
        """Categorize a SQLite error message into a broad error type.

        Args:
            error_msg: The raw error string returned by SQLite.

        Returns:
            One of: "syntax", "missing_table", "missing_column",
            "ambiguous_column", "type_error", "constraint", "timeout",
            "unknown".
        """
        msg = error_msg.lower()
        if "no such table" in msg:
            return "missing_table"
        if "no such column" in msg:
            return "missing_column"
        if "ambiguous" in msg:
            return "ambiguous_column"
        if "near" in msg or "syntax error" in msg:
            return "syntax"
        if "datatype mismatch" in msg or "type" in msg:
            return "type_error"
        if "constraint" in msg or "unique" in msg or "not null" in msg or "foreign key" in msg:
            return "constraint"
        if "timed out" in msg or "timeout" in msg or "interrupted" in msg:
            return "timeout"
        return "unknown"

    def reset(self) -> None:
        """Drop the current connection and create a fresh one."""
        if self._conn:
            self._conn.close()
        self._create_connection()
