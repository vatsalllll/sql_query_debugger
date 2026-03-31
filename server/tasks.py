"""
SQL Debugger Task Definitions
------------------------------
Tasks with correct queries and schemas. Bug injection is handled dynamically
by bug_injector.py, making every episode unique.

Includes both:
- Static tasks (predefined broken queries for deterministic grading)
- Dynamic task templates (correct queries that get bugs injected at runtime)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SQLTask:
    task_id: str
    difficulty: str
    description: str
    schema_sql: str
    seed_data_sql: str
    correct_query: str
    expected_output: List[tuple]
    max_steps: int
    # Static broken query (optional — if None, bug_injector creates one dynamically)
    broken_query: Optional[str] = None
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

_PRODUCTS_SCHEMA = """
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE reviews (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    user_id INTEGER,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""

_PRODUCTS_SEED = """
INSERT INTO categories (id, name) VALUES (1, 'Electronics');
INSERT INTO categories (id, name) VALUES (2, 'Books');
INSERT INTO categories (id, name) VALUES (3, 'Clothing');

INSERT INTO products (id, name, category_id, price, stock) VALUES (1, 'Laptop', 1, 999.99, 50);
INSERT INTO products (id, name, category_id, price, stock) VALUES (2, 'Phone', 1, 699.99, 120);
INSERT INTO products (id, name, category_id, price, stock) VALUES (3, 'Tablet', 1, 449.99, 75);
INSERT INTO products (id, name, category_id, price, stock) VALUES (4, 'Python Crash Course', 2, 39.99, 200);
INSERT INTO products (id, name, category_id, price, stock) VALUES (5, 'SQL Handbook', 2, 29.99, 150);
INSERT INTO products (id, name, category_id, price, stock) VALUES (6, 'T-Shirt', 3, 19.99, 500);
INSERT INTO products (id, name, category_id, price, stock) VALUES (7, 'Jacket', 3, 89.99, 80);
INSERT INTO products (id, name, category_id, price, stock) VALUES (8, 'Headphones', 1, 149.99, 0);

INSERT INTO reviews (id, product_id, user_id, rating, comment) VALUES (1, 1, 1, 5, 'Great laptop');
INSERT INTO reviews (id, product_id, user_id, rating, comment) VALUES (2, 1, 2, 4, 'Good value');
INSERT INTO reviews (id, product_id, user_id, rating, comment) VALUES (3, 2, 1, 3, 'Average phone');
INSERT INTO reviews (id, product_id, user_id, rating, comment) VALUES (4, 4, 3, 5, 'Best Python book');
INSERT INTO reviews (id, product_id, user_id, rating, comment) VALUES (5, 5, 2, 4, 'Helpful SQL guide');
INSERT INTO reviews (id, product_id, user_id, rating, comment) VALUES (6, 6, 4, 2, 'Fabric quality meh');
INSERT INTO reviews (id, product_id, user_id, rating, comment) VALUES (7, 3, 5, 4, 'Nice tablet');
"""

_SCHOOL_SCHEMA = """
CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    grade_level INTEGER NOT NULL,
    gpa REAL
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    instructor TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY,
    student_id INTEGER,
    course_id INTEGER,
    score REAL,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
"""

_SCHOOL_SEED = """
INSERT INTO students (id, name, grade_level, gpa) VALUES (1, 'Alice', 12, 3.8);
INSERT INTO students (id, name, grade_level, gpa) VALUES (2, 'Bob', 11, 3.2);
INSERT INTO students (id, name, grade_level, gpa) VALUES (3, 'Charlie', 12, 3.9);
INSERT INTO students (id, name, grade_level, gpa) VALUES (4, 'Diana', 10, 2.8);
INSERT INTO students (id, name, grade_level, gpa) VALUES (5, 'Eve', 11, 3.5);

INSERT INTO courses (id, name, instructor, credits) VALUES (1, 'Calculus', 'Dr. Smith', 4);
INSERT INTO courses (id, name, instructor, credits) VALUES (2, 'Physics', 'Dr. Jones', 3);
INSERT INTO courses (id, name, instructor, credits) VALUES (3, 'English', 'Prof. Lee', 3);
INSERT INTO courses (id, name, instructor, credits) VALUES (4, 'History', 'Prof. Kim', 3);

INSERT INTO enrollments (id, student_id, course_id, score) VALUES (1, 1, 1, 95);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (2, 1, 2, 88);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (3, 2, 1, 72);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (4, 2, 3, 85);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (5, 3, 1, 98);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (6, 3, 2, 92);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (7, 4, 3, 68);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (8, 4, 4, 74);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (9, 5, 2, 90);
INSERT INTO enrollments (id, student_id, course_id, score) VALUES (10, 5, 4, 82);
"""


# ---------------------------------------------------------------------------
# STATIC TASKS — Predefined broken queries (seeds 0-8 for determinism)
# ---------------------------------------------------------------------------

STATIC_TASKS: List[SQLTask] = [
    # --- EASY ---
    SQLTask(
        task_id="easy_1", difficulty="easy",
        description="Select all users from the users table.",
        schema_sql=_USERS_SCHEMA, seed_data_sql=_USERS_SEED,
        correct_query="SELECT * FROM users;",
        broken_query="SELCT * FROM users;",
        expected_output=[(1,"Alice","alice@example.com",30),(2,"Bob","bob@example.com",25),(3,"Charlie","charlie@example.com",35),(4,"Diana","diana@example.com",28),(5,"Eve","eve@example.com",32)],
        max_steps=5,
        hint_general="Check for typos in SQL keywords.",
        hint_specific="The SELECT keyword is misspelled as 'SELCT'.",
    ),
    SQLTask(
        task_id="easy_2", difficulty="easy",
        description="Select the name and email of all users where age is greater than 25.",
        schema_sql=_USERS_SCHEMA, seed_data_sql=_USERS_SEED,
        correct_query="SELECT name, email FROM users WHERE age > 25;",
        broken_query="SELECT name, email FROM users WHER age > 25;",
        expected_output=[("Alice","alice@example.com"),("Charlie","charlie@example.com"),("Diana","diana@example.com"),("Eve","eve@example.com")],
        max_steps=5,
        hint_general="Check for typos in SQL keywords.",
        hint_specific="The WHERE keyword is misspelled as 'WHER'.",
    ),
    SQLTask(
        task_id="easy_3", difficulty="easy",
        description="Select all users named Alice.",
        schema_sql=_USERS_SCHEMA, seed_data_sql=_USERS_SEED,
        correct_query="SELECT * FROM users WHERE name = 'Alice';",
        broken_query="SELECT * FROM users WHERE name = 'Alice;",
        expected_output=[(1,"Alice","alice@example.com",30)],
        max_steps=5,
        hint_general="Check string literals for proper quoting.",
        hint_specific="The string literal 'Alice' is missing a closing single quote.",
    ),
    # --- MEDIUM ---
    SQLTask(
        task_id="medium_1", difficulty="medium",
        description="Select the names of all users.",
        schema_sql=_USERS_SCHEMA, seed_data_sql=_USERS_SEED,
        correct_query="SELECT name FROM users;",
        broken_query="SELECT username FROM users;",
        expected_output=[("Alice",),("Bob",),("Charlie",),("Diana",),("Eve",)],
        max_steps=8,
        hint_general="Check that column names match the schema exactly.",
        hint_specific="The column is called 'name', not 'username'. Check the schema.",
    ),
    SQLTask(
        task_id="medium_2", difficulty="medium",
        description="Select all orders.",
        schema_sql=_USERS_SCHEMA + _ORDERS_SCHEMA, seed_data_sql=_USERS_SEED + _ORDERS_SEED,
        correct_query="SELECT * FROM orders;",
        broken_query="SELECT * FROM order;",
        expected_output=[(1,1,"Laptop",999.99,"2024-01-15"),(2,1,"Mouse",29.99,"2024-01-20"),(3,2,"Keyboard",79.99,"2024-02-10"),(4,3,"Monitor",449.99,"2024-02-15"),(5,3,"Webcam",59.99,"2024-03-01"),(6,3,"Headset",149.99,"2024-03-05")],
        max_steps=8,
        hint_general="Check that table names match the schema exactly.",
        hint_specific="The table is called 'orders' (plural), not 'order'.",
    ),
    SQLTask(
        task_id="medium_3", difficulty="medium",
        description="Count how many orders each user has placed. Show user name and order count.",
        schema_sql=_USERS_SCHEMA + _ORDERS_SCHEMA, seed_data_sql=_USERS_SEED + _ORDERS_SEED,
        correct_query="SELECT u.name, COUNT(*) as order_count FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name;",
        broken_query="SELECT name, COUNT(*) as order_count FROM orders GROUP BY name;",
        expected_output=[("Alice",2),("Bob",1),("Charlie",3)],
        max_steps=8,
        hint_general="The column 'name' is not in the 'orders' table. You may need a JOIN.",
        hint_specific="JOIN the 'users' table to access the 'name' column.",
    ),
    # --- HARD ---
    SQLTask(
        task_id="hard_1", difficulty="hard",
        description="List ALL users and their order counts. Users with no orders should show 0.",
        schema_sql=_USERS_SCHEMA + _ORDERS_SCHEMA, seed_data_sql=_USERS_SEED + _ORDERS_SEED,
        correct_query="SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.name;",
        broken_query="SELECT u.name, COUNT(o.id) as order_count FROM users u INNER JOIN orders o ON u.id = o.user_id GROUP BY u.name;",
        expected_output=[("Alice",2),("Bob",1),("Charlie",3),("Diana",0),("Eve",0)],
        max_steps=12,
        hint_general="Think about which type of JOIN preserves all rows from the left table.",
        hint_specific="INNER JOIN excludes users with no orders. Use LEFT JOIN.",
    ),
    SQLTask(
        task_id="hard_2", difficulty="hard",
        description="Find the total spending per department. Show department name and total amount.",
        schema_sql=_EMPLOYEES_SCHEMA + _ORDERS_SCHEMA.replace("user_id INTEGER","employee_id INTEGER").replace("FOREIGN KEY (user_id) REFERENCES users(id)","FOREIGN KEY (employee_id) REFERENCES employees(id)"),
        seed_data_sql=_EMPLOYEES_SEED + """
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (1, 1, 'Laptop', 999.99, '2024-01-15');
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (2, 2, 'Server', 2499.99, '2024-01-20');
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (3, 4, 'Ads Package', 500.00, '2024-02-10');
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (4, 6, 'CRM License', 299.99, '2024-02-15');
INSERT INTO orders (id, employee_id, product, amount, order_date) VALUES (5, 7, 'Travel', 750.00, '2024-03-01');
""",
        correct_query="SELECT d.name, ROUND(SUM(o.amount), 2) as total_spending FROM departments d JOIN employees e ON d.id = e.department_id JOIN orders o ON e.id = o.employee_id GROUP BY d.name;",
        broken_query="SELECT d.name, SUM(o.amount) as total_spending FROM departments d JOIN employees e ON d.id = e.department_id JOIN orders o ON e.id = o.employee_id;",
        expected_output=[("Engineering",3499.98),("Marketing",500.00),("Sales",1049.99)],
        max_steps=12,
        hint_general="When using aggregate functions like SUM, check if GROUP BY is needed.",
        hint_specific="Missing GROUP BY d.name — without it, SUM aggregates all rows into one.",
    ),
    SQLTask(
        task_id="hard_3", difficulty="hard",
        description="Find employees who earn more than the average salary of their department.",
        schema_sql=_EMPLOYEES_SCHEMA, seed_data_sql=_EMPLOYEES_SEED,
        correct_query="SELECT e.name, e.salary, d.name as department FROM employees e JOIN departments d ON e.department_id = d.id WHERE e.salary > (SELECT AVG(e2.salary) FROM employees e2 WHERE e2.department_id = e.department_id);",
        broken_query="SELECT e.name, e.salary, d.name as department FROM employees e JOIN departments d ON e.department_id = d.id WHERE e.salary > (SELECT AVG(salary) FROM employees);",
        expected_output=[("Bob",105000.0,"Engineering"),("Eve",80000.0,"Marketing"),("Grace",90000.0,"Sales")],
        max_steps=12,
        hint_general="The subquery should compare against the department average, not the overall average.",
        hint_specific="Use a correlated subquery: WHERE e2.department_id = e.department_id.",
    ),
]


# ---------------------------------------------------------------------------
# DYNAMIC TASK TEMPLATES — Correct queries that get bugs injected at runtime
# ---------------------------------------------------------------------------

DYNAMIC_TEMPLATES: List[SQLTask] = [
    # --- Products & Reviews ---
    SQLTask(
        task_id="dyn_products_1", difficulty="easy",
        description="List all products with their prices.",
        schema_sql=_PRODUCTS_SCHEMA, seed_data_sql=_PRODUCTS_SEED,
        correct_query="SELECT name, price FROM products;",
        expected_output=[("Laptop",999.99),("Phone",699.99),("Tablet",449.99),("Python Crash Course",39.99),("SQL Handbook",29.99),("T-Shirt",19.99),("Jacket",89.99),("Headphones",149.99)],
        max_steps=5,
    ),
    SQLTask(
        task_id="dyn_products_2", difficulty="easy",
        description="Find products that cost more than 100.",
        schema_sql=_PRODUCTS_SCHEMA, seed_data_sql=_PRODUCTS_SEED,
        correct_query="SELECT name, price FROM products WHERE price > 100;",
        expected_output=[("Laptop",999.99),("Phone",699.99),("Tablet",449.99),("Headphones",149.99)],
        max_steps=5,
    ),
    SQLTask(
        task_id="dyn_products_3", difficulty="medium",
        description="Show each product with its category name.",
        schema_sql=_PRODUCTS_SCHEMA, seed_data_sql=_PRODUCTS_SEED,
        correct_query="SELECT p.name, c.name as category FROM products p JOIN categories c ON p.category_id = c.id;",
        expected_output=[("Laptop","Electronics"),("Phone","Electronics"),("Tablet","Electronics"),("Python Crash Course","Books"),("SQL Handbook","Books"),("T-Shirt","Clothing"),("Jacket","Clothing"),("Headphones","Electronics")],
        max_steps=8,
    ),
    SQLTask(
        task_id="dyn_products_4", difficulty="medium",
        description="Find out-of-stock products (stock = 0).",
        schema_sql=_PRODUCTS_SCHEMA, seed_data_sql=_PRODUCTS_SEED,
        correct_query="SELECT name, price FROM products WHERE stock = 0;",
        expected_output=[("Headphones",149.99)],
        max_steps=8,
    ),
    SQLTask(
        task_id="dyn_products_5", difficulty="hard",
        description="Show the average rating for each product. Include products with no reviews showing NULL.",
        schema_sql=_PRODUCTS_SCHEMA, seed_data_sql=_PRODUCTS_SEED,
        correct_query="SELECT p.name, ROUND(AVG(r.rating), 1) as avg_rating FROM products p LEFT JOIN reviews r ON p.id = r.product_id GROUP BY p.name;",
        expected_output=[("Headphones",None),("Jacket",None),("Laptop",4.5),("Phone",3.0),("Python Crash Course",5.0),("SQL Handbook",4.0),("T-Shirt",2.0),("Tablet",4.0)],
        max_steps=12,
    ),
    SQLTask(
        task_id="dyn_products_6", difficulty="hard",
        description="Find categories where total product value (price * stock) exceeds 10000.",
        schema_sql=_PRODUCTS_SCHEMA, seed_data_sql=_PRODUCTS_SEED,
        correct_query="SELECT c.name, ROUND(SUM(p.price * p.stock), 2) as total_value FROM categories c JOIN products p ON c.id = p.category_id GROUP BY c.name HAVING SUM(p.price * p.stock) > 10000;",
        expected_output=[("Books",12496.5),("Clothing",17194.2),("Electronics",167747.55)],
        max_steps=12,
    ),
    # --- School ---
    SQLTask(
        task_id="dyn_school_1", difficulty="easy",
        description="List all students and their GPAs.",
        schema_sql=_SCHOOL_SCHEMA, seed_data_sql=_SCHOOL_SEED,
        correct_query="SELECT name, gpa FROM students;",
        expected_output=[("Alice",3.8),("Bob",3.2),("Charlie",3.9),("Diana",2.8),("Eve",3.5)],
        max_steps=5,
    ),
    SQLTask(
        task_id="dyn_school_2", difficulty="medium",
        description="Show each student's name and the courses they're enrolled in.",
        schema_sql=_SCHOOL_SCHEMA, seed_data_sql=_SCHOOL_SEED,
        correct_query="SELECT s.name as student, c.name as course FROM students s JOIN enrollments e ON s.id = e.student_id JOIN courses c ON e.course_id = c.id;",
        expected_output=[("Alice","Calculus"),("Alice","Physics"),("Bob","Calculus"),("Bob","English"),("Charlie","Calculus"),("Charlie","Physics"),("Diana","English"),("Diana","History"),("Eve","Physics"),("Eve","History")],
        max_steps=8,
    ),
    SQLTask(
        task_id="dyn_school_3", difficulty="medium",
        description="Find students with GPA above 3.5.",
        schema_sql=_SCHOOL_SCHEMA, seed_data_sql=_SCHOOL_SEED,
        correct_query="SELECT name, gpa FROM students WHERE gpa > 3.5;",
        expected_output=[("Alice",3.8),("Charlie",3.9)],
        max_steps=8,
    ),
    SQLTask(
        task_id="dyn_school_4", difficulty="hard",
        description="Find the average score per course. Show course name, instructor, and average score.",
        schema_sql=_SCHOOL_SCHEMA, seed_data_sql=_SCHOOL_SEED,
        correct_query="SELECT c.name, c.instructor, ROUND(AVG(e.score), 1) as avg_score FROM courses c JOIN enrollments e ON c.id = e.course_id GROUP BY c.name, c.instructor;",
        expected_output=[("Calculus","Dr. Smith",88.3),("English","Prof. Lee",76.5),("History","Prof. Kim",78.0),("Physics","Dr. Jones",90.0)],
        max_steps=12,
    ),
    SQLTask(
        task_id="dyn_school_5", difficulty="hard",
        description="Find students who scored above the average in ALL their courses.",
        schema_sql=_SCHOOL_SCHEMA, seed_data_sql=_SCHOOL_SEED,
        correct_query="SELECT DISTINCT s.name FROM students s JOIN enrollments e ON s.id = e.student_id WHERE NOT EXISTS (SELECT 1 FROM enrollments e2 JOIN (SELECT course_id, AVG(score) as avg_score FROM enrollments GROUP BY course_id) ca ON e2.course_id = ca.course_id WHERE e2.student_id = s.id AND e2.score <= ca.avg_score);",
        expected_output=[("Charlie",)],
        max_steps=12,
    ),
    # --- Employees extra ---
    SQLTask(
        task_id="dyn_emp_1", difficulty="easy",
        description="List all employees sorted by salary descending.",
        schema_sql=_EMPLOYEES_SCHEMA, seed_data_sql=_EMPLOYEES_SEED,
        correct_query="SELECT name, salary FROM employees ORDER BY salary DESC;",
        expected_output=[("Bob",105000.0),("Alice",95000.0),("Grace",90000.0),("Charlie",85000.0),("Eve",80000.0),("Diana",75000.0),("Frank",70000.0),("Hank",60000.0)],
        max_steps=5,
    ),
    SQLTask(
        task_id="dyn_emp_2", difficulty="medium",
        description="Count employees per department. Include department name.",
        schema_sql=_EMPLOYEES_SCHEMA, seed_data_sql=_EMPLOYEES_SEED,
        correct_query="SELECT d.name, COUNT(e.id) as emp_count FROM departments d JOIN employees e ON d.id = e.department_id GROUP BY d.name;",
        expected_output=[("Engineering",3),("Marketing",2),("Sales",2)],
        max_steps=8,
    ),
    SQLTask(
        task_id="dyn_emp_3", difficulty="hard",
        description="Find departments where the average salary is above 80000.",
        schema_sql=_EMPLOYEES_SCHEMA, seed_data_sql=_EMPLOYEES_SEED,
        correct_query="SELECT d.name, ROUND(AVG(e.salary), 2) as avg_salary FROM departments d JOIN employees e ON d.id = e.department_id GROUP BY d.name HAVING AVG(e.salary) > 80000;",
        expected_output=[("Engineering",95000.0)],
        max_steps=12,
    ),
]

# Combine all tasks
ALL_TASKS: List[SQLTask] = STATIC_TASKS + DYNAMIC_TEMPLATES

# Total: 9 static + 14 dynamic = 23 tasks


def get_task_by_index(index: int) -> SQLTask:
    """Get a task by index (wraps around)."""
    return ALL_TASKS[index % len(ALL_TASKS)]


def get_task_by_id(task_id: str) -> SQLTask:
    """Get a task by its ID."""
    for task in ALL_TASKS:
        if task.task_id == task_id:
            return task
    raise ValueError(f"Unknown task_id: {task_id}")
