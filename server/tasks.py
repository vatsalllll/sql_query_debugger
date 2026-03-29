"""
SQL Debugger Task Definitions
------------------------------
9 tasks across 3 difficulty levels (easy, medium, hard).
Each task has a broken query, correct query, schema, seed data, and expected output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SQLTask:
    task_id: str
    difficulty: str
    description: str
    schema_sql: str
    seed_data_sql: str
    broken_query: str
    correct_query: str
    expected_output: List[tuple]
    max_steps: int
    hint_general: str = ""
    hint_specific: str = ""


# ---------------------------------------------------------------------------
# Shared schemas
# ---------------------------------------------------------------------------

_USERS_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER
);
"""

_USERS_SEED = """
INSERT INTO users (id, name, email, age) VALUES (1, 'Alice', 'alice@example.com', 30);
INSERT INTO users (id, name, email, age) VALUES (2, 'Bob', 'bob@example.com', 25);
INSERT INTO users (id, name, email, age) VALUES (3, 'Charlie', 'charlie@example.com', 35);
INSERT INTO users (id, name, email, age) VALUES (4, 'Diana', 'diana@example.com', 28);
INSERT INTO users (id, name, email, age) VALUES (5, 'Eve', 'eve@example.com', 32);
"""

_ORDERS_SCHEMA = """
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    product TEXT NOT NULL,
    amount REAL NOT NULL,
    order_date TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

_ORDERS_SEED = """
INSERT INTO orders (id, user_id, product, amount, order_date) VALUES (1, 1, 'Laptop', 999.99, '2024-01-15');
INSERT INTO orders (id, user_id, product, amount, order_date) VALUES (2, 1, 'Mouse', 29.99, '2024-01-20');
INSERT INTO orders (id, user_id, product, amount, order_date) VALUES (3, 2, 'Keyboard', 79.99, '2024-02-10');
INSERT INTO orders (id, user_id, product, amount, order_date) VALUES (4, 3, 'Monitor', 449.99, '2024-02-15');
INSERT INTO orders (id, user_id, product, amount, order_date) VALUES (5, 3, 'Webcam', 59.99, '2024-03-01');
INSERT INTO orders (id, user_id, product, amount, order_date) VALUES (6, 3, 'Headset', 149.99, '2024-03-05');
"""

_EMPLOYEES_SCHEMA = """
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER,
    salary REAL NOT NULL,
    hire_date TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);
"""

_EMPLOYEES_SEED = """
INSERT INTO departments (id, name) VALUES (1, 'Engineering');
INSERT INTO departments (id, name) VALUES (2, 'Marketing');
INSERT INTO departments (id, name) VALUES (3, 'Sales');

INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES (1, 'Alice', 1, 95000, '2020-03-15');
INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES (2, 'Bob', 1, 105000, '2019-07-01');
INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES (3, 'Charlie', 1, 85000, '2022-01-10');
INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES (4, 'Diana', 2, 75000, '2021-06-20');
INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES (5, 'Eve', 2, 80000, '2020-11-05');
INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES (6, 'Frank', 3, 70000, '2023-02-14');
INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES (7, 'Grace', 3, 90000, '2018-09-30');
INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES (8, 'Hank', NULL, 60000, '2023-08-01');
"""


# ---------------------------------------------------------------------------
# EASY TASKS — Syntax errors
# ---------------------------------------------------------------------------

EASY_1 = SQLTask(
    task_id="easy_1",
    difficulty="easy",
    description="Select all users from the users table.",
    schema_sql=_USERS_SCHEMA,
    seed_data_sql=_USERS_SEED,
    broken_query="SELCT * FROM users;",
    correct_query="SELECT * FROM users;",
    expected_output=[
        (1, "Alice", "alice@example.com", 30),
        (2, "Bob", "bob@example.com", 25),
        (3, "Charlie", "charlie@example.com", 35),
        (4, "Diana", "diana@example.com", 28),
        (5, "Eve", "eve@example.com", 32),
    ],
    max_steps=5,
    hint_general="Check for typos in SQL keywords.",
    hint_specific="The SELECT keyword is misspelled as 'SELCT'.",
)

EASY_2 = SQLTask(
    task_id="easy_2",
    difficulty="easy",
    description="Select the name and email of all users where age is greater than 25.",
    schema_sql=_USERS_SCHEMA,
    seed_data_sql=_USERS_SEED,
    broken_query="SELECT name, email FROM users WHER age > 25;",
    correct_query="SELECT name, email FROM users WHERE age > 25;",
    expected_output=[
        ("Alice", "alice@example.com"),
        ("Charlie", "charlie@example.com"),
        ("Diana", "diana@example.com"),
        ("Eve", "eve@example.com"),
    ],
    max_steps=5,
    hint_general="Check for typos in SQL keywords.",
    hint_specific="The WHERE keyword is misspelled as 'WHER'.",
)

EASY_3 = SQLTask(
    task_id="easy_3",
    difficulty="easy",
    description="Select all users named Alice.",
    schema_sql=_USERS_SCHEMA,
    seed_data_sql=_USERS_SEED,
    broken_query="SELECT * FROM users WHERE name = 'Alice;",
    correct_query="SELECT * FROM users WHERE name = 'Alice';",
    expected_output=[
        (1, "Alice", "alice@example.com", 30),
    ],
    max_steps=5,
    hint_general="Check string literals for proper quoting.",
    hint_specific="The string literal 'Alice' is missing a closing single quote.",
)


# ---------------------------------------------------------------------------
# MEDIUM TASKS — Schema errors
# ---------------------------------------------------------------------------

MEDIUM_1 = SQLTask(
    task_id="medium_1",
    difficulty="medium",
    description="Select the names of all users.",
    schema_sql=_USERS_SCHEMA,
    seed_data_sql=_USERS_SEED,
    broken_query="SELECT username FROM users;",
    correct_query="SELECT name FROM users;",
    expected_output=[
        ("Alice",),
        ("Bob",),
        ("Charlie",),
        ("Diana",),
        ("Eve",),
    ],
    max_steps=8,
    hint_general="Check that column names match the schema exactly.",
    hint_specific="The column is called 'name', not 'username'. Check the schema.",
)

MEDIUM_2 = SQLTask(
    task_id="medium_2",
    difficulty="medium",
    description="Select all orders.",
    schema_sql=_USERS_SCHEMA + _ORDERS_SCHEMA,
    seed_data_sql=_USERS_SEED + _ORDERS_SEED,
    broken_query="SELECT * FROM order;",
    correct_query="SELECT * FROM orders;",
    expected_output=[
        (1, 1, "Laptop", 999.99, "2024-01-15"),
        (2, 1, "Mouse", 29.99, "2024-01-20"),
        (3, 2, "Keyboard", 79.99, "2024-02-10"),
        (4, 3, "Monitor", 449.99, "2024-02-15"),
        (5, 3, "Webcam", 59.99, "2024-03-01"),
        (6, 3, "Headset", 149.99, "2024-03-05"),
    ],
    max_steps=8,
    hint_general="Check that table names match the schema exactly.",
    hint_specific="The table is called 'orders' (plural), not 'order'.",
)

MEDIUM_3 = SQLTask(
    task_id="medium_3",
    difficulty="medium",
    description="Count how many orders each user has placed. Show user name and order count.",
    schema_sql=_USERS_SCHEMA + _ORDERS_SCHEMA,
    seed_data_sql=_USERS_SEED + _ORDERS_SEED,
    broken_query="SELECT name, COUNT(*) as order_count FROM orders GROUP BY name;",
    correct_query="SELECT u.name, COUNT(*) as order_count FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name;",
    expected_output=[
        ("Alice", 2),
        ("Bob", 1),
        ("Charlie", 3),
    ],
    max_steps=8,
    hint_general="The column 'name' is not in the 'orders' table. You may need a JOIN.",
    hint_specific="JOIN the 'users' table to access the 'name' column: JOIN users u ON u.id = orders.user_id.",
)


# ---------------------------------------------------------------------------
# HARD TASKS — Logic errors
# ---------------------------------------------------------------------------

HARD_1 = SQLTask(
    task_id="hard_1",
    difficulty="hard",
    description="List ALL users and their order counts. Users with no orders should show 0.",
    schema_sql=_USERS_SCHEMA + _ORDERS_SCHEMA,
    seed_data_sql=_USERS_SEED + _ORDERS_SEED,
    broken_query="SELECT u.name, COUNT(o.id) as order_count FROM users u INNER JOIN orders o ON u.id = o.user_id GROUP BY u.name;",
    correct_query="SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.name;",
    expected_output=[
        ("Alice", 2),
        ("Bob", 1),
        ("Charlie", 3),
        ("Diana", 0),
        ("Eve", 0),
    ],
    max_steps=12,
    hint_general="Think about which type of JOIN preserves all rows from the left table.",
    hint_specific="INNER JOIN excludes users with no orders. Use LEFT JOIN to include all users.",
)

HARD_2 = SQLTask(
    task_id="hard_2",
    difficulty="hard",
    description="Find the total spending per department. Show department name and total amount.",
    schema_sql=_EMPLOYEES_SCHEMA + _ORDERS_SCHEMA.replace(
        "user_id INTEGER",
        "employee_id INTEGER"
    ).replace(
        "FOREIGN KEY (user_id) REFERENCES users(id)",
        "FOREIGN KEY (employee_id) REFERENCES employees(id)"
    ),
    seed_data_sql=_EMPLOYEES_SEED + """
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (1, 1, 'Laptop', 999.99, '2024-01-15');
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (2, 2, 'Server', 2499.99, '2024-01-20');
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (3, 4, 'Ads Package', 500.00, '2024-02-10');
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (4, 6, 'CRM License', 299.99, '2024-02-15');
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (5, 7, 'Travel', 750.00, '2024-03-01');
""",
    broken_query="SELECT d.name, SUM(o.amount) as total_spending FROM departments d JOIN employees e ON d.id = e.department_id JOIN orders o ON e.id = o.employee_id;",
    correct_query="SELECT d.name, ROUND(SUM(o.amount), 2) as total_spending FROM departments d JOIN employees e ON d.id = e.department_id JOIN orders o ON e.id = o.employee_id GROUP BY d.name;",
    expected_output=[
        ("Engineering", 3499.98),
        ("Marketing", 500.00),
        ("Sales", 1049.99),
    ],
    max_steps=12,
    hint_general="When using aggregate functions like SUM, check if GROUP BY is needed.",
    hint_specific="Missing GROUP BY d.name — without it, SUM aggregates all rows into one.",
)

HARD_3 = SQLTask(
    task_id="hard_3",
    difficulty="hard",
    description="Find employees who earn more than the average salary of their department.",
    schema_sql=_EMPLOYEES_SCHEMA,
    seed_data_sql=_EMPLOYEES_SEED,
    broken_query="SELECT e.name, e.salary, d.name as department FROM employees e JOIN departments d ON e.department_id = d.id WHERE e.salary > (SELECT AVG(salary) FROM employees);",
    correct_query="SELECT e.name, e.salary, d.name as department FROM employees e JOIN departments d ON e.department_id = d.id WHERE e.salary > (SELECT AVG(e2.salary) FROM employees e2 WHERE e2.department_id = e.department_id);",
    expected_output=[
        ("Bob", 105000.0, "Engineering"),
        ("Eve", 80000.0, "Marketing"),
        ("Grace", 90000.0, "Sales"),
    ],
    max_steps=12,
    hint_general="The subquery should compare against the department average, not the overall average.",
    hint_specific="Use a correlated subquery: WHERE e2.department_id = e.department_id in the AVG subquery.",
)


# ---------------------------------------------------------------------------
# Task registry
# ---------------------------------------------------------------------------

ALL_TASKS: List[SQLTask] = [
    EASY_1, EASY_2, EASY_3,
    MEDIUM_1, MEDIUM_2, MEDIUM_3,
    HARD_1, HARD_2, HARD_3,
]


def get_task_by_index(index: int) -> SQLTask:
    """Get a task by index (wraps around)."""
    return ALL_TASKS[index % len(ALL_TASKS)]


def get_task_by_id(task_id: str) -> SQLTask:
    """Get a task by its ID."""
    for task in ALL_TASKS:
        if task.task_id == task_id:
            return task
    raise ValueError(f"Unknown task_id: {task_id}")
