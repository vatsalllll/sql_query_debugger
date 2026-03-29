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

    def reset(self) -> None:
        """Drop the current connection and create a fresh one."""
        if self._conn:
            self._conn.close()
        self._create_connection()
