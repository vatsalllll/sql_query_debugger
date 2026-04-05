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


# ---------------------------------------------------------------------------
# E-Commerce schema (4 tables, complex relationships)
# ---------------------------------------------------------------------------

_ECOMMERCE_SCHEMA = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    joined_date TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'bronze'
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""

_ECOMMERCE_SEED = """
INSERT INTO customers VALUES (1, 'Alice', 'alice@shop.com', '2022-01-15', 'gold');
INSERT INTO customers VALUES (2, 'Bob', 'bob@shop.com', '2022-06-20', 'silver');
INSERT INTO customers VALUES (3, 'Charlie', 'charlie@shop.com', '2023-03-10', 'bronze');
INSERT INTO customers VALUES (4, 'Diana', 'diana@shop.com', '2023-07-04', 'gold');
INSERT INTO customers VALUES (5, 'Eve', 'eve@shop.com', '2023-11-11', 'bronze');
INSERT INTO customers VALUES (6, 'Frank', 'frank@shop.com', '2024-01-20', 'silver');
INSERT INTO customers VALUES (7, 'Grace', 'grace@shop.com', '2024-02-14', 'bronze');
INSERT INTO customers VALUES (8, 'Hank', 'hank@shop.com', '2024-05-01', 'bronze');

INSERT INTO products VALUES (1, 'Laptop', 'Electronics', 1000.00, 50);
INSERT INTO products VALUES (2, 'Phone', 'Electronics', 700.00, 120);
INSERT INTO products VALUES (3, 'Tablet', 'Electronics', 450.00, 75);
INSERT INTO products VALUES (4, 'Headphones', 'Electronics', 150.00, 200);
INSERT INTO products VALUES (5, 'Python Crash Course', 'Books', 40.00, 300);
INSERT INTO products VALUES (6, 'SQL Handbook', 'Books', 30.00, 250);
INSERT INTO products VALUES (7, 'Data Science Guide', 'Books', 50.00, 180);
INSERT INTO products VALUES (8, 'T-Shirt', 'Clothing', 20.00, 500);
INSERT INTO products VALUES (9, 'Jacket', 'Clothing', 90.00, 80);
INSERT INTO products VALUES (10, 'Sneakers', 'Clothing', 130.00, 60);
INSERT INTO products VALUES (11, 'Backpack', 'Accessories', 60.00, 150);
INSERT INTO products VALUES (12, 'Watch', 'Accessories', 300.00, 40);

INSERT INTO orders VALUES (1, 1, '2024-01-10', 'delivered');
INSERT INTO orders VALUES (2, 1, '2024-02-14', 'delivered');
INSERT INTO orders VALUES (3, 1, '2024-03-20', 'shipped');
INSERT INTO orders VALUES (4, 2, '2024-01-22', 'delivered');
INSERT INTO orders VALUES (5, 2, '2024-04-05', 'returned');
INSERT INTO orders VALUES (6, 3, '2024-02-28', 'delivered');
INSERT INTO orders VALUES (7, 3, '2024-05-15', 'pending');
INSERT INTO orders VALUES (8, 4, '2024-01-05', 'delivered');
INSERT INTO orders VALUES (9, 4, '2024-03-18', 'delivered');
INSERT INTO orders VALUES (10, 4, '2024-06-01', 'shipped');
INSERT INTO orders VALUES (11, 4, '2024-07-20', 'pending');
INSERT INTO orders VALUES (12, 5, '2024-02-10', 'delivered');
INSERT INTO orders VALUES (13, 5, '2024-08-01', 'pending');
INSERT INTO orders VALUES (14, 6, '2024-03-15', 'delivered');
INSERT INTO orders VALUES (15, 6, '2024-05-22', 'shipped');
INSERT INTO orders VALUES (16, 7, '2024-04-10', 'delivered');
INSERT INTO orders VALUES (17, 1, '2024-09-01', 'pending');

INSERT INTO order_items VALUES (1, 1, 1, 1, 1000.00);
INSERT INTO order_items VALUES (2, 1, 4, 2, 150.00);
INSERT INTO order_items VALUES (3, 2, 5, 1, 40.00);
INSERT INTO order_items VALUES (4, 2, 6, 1, 30.00);
INSERT INTO order_items VALUES (5, 3, 2, 1, 700.00);
INSERT INTO order_items VALUES (6, 4, 1, 1, 1000.00);
INSERT INTO order_items VALUES (7, 4, 11, 1, 60.00);
INSERT INTO order_items VALUES (8, 5, 3, 1, 450.00);
INSERT INTO order_items VALUES (9, 6, 8, 3, 20.00);
INSERT INTO order_items VALUES (10, 6, 9, 1, 90.00);
INSERT INTO order_items VALUES (11, 7, 7, 2, 50.00);
INSERT INTO order_items VALUES (12, 7, 12, 1, 300.00);
INSERT INTO order_items VALUES (13, 8, 1, 2, 1000.00);
INSERT INTO order_items VALUES (14, 8, 4, 1, 150.00);
INSERT INTO order_items VALUES (15, 9, 10, 2, 130.00);
INSERT INTO order_items VALUES (16, 9, 8, 5, 20.00);
INSERT INTO order_items VALUES (17, 10, 2, 1, 700.00);
INSERT INTO order_items VALUES (18, 10, 12, 1, 300.00);
INSERT INTO order_items VALUES (19, 11, 5, 3, 40.00);
INSERT INTO order_items VALUES (20, 11, 7, 1, 50.00);
INSERT INTO order_items VALUES (21, 12, 6, 2, 30.00);
INSERT INTO order_items VALUES (22, 12, 4, 1, 150.00);
INSERT INTO order_items VALUES (23, 13, 3, 1, 450.00);
INSERT INTO order_items VALUES (24, 14, 1, 1, 1000.00);
INSERT INTO order_items VALUES (25, 14, 9, 2, 90.00);
INSERT INTO order_items VALUES (26, 15, 11, 3, 60.00);
INSERT INTO order_items VALUES (27, 16, 10, 1, 130.00);
INSERT INTO order_items VALUES (28, 16, 8, 2, 20.00);
INSERT INTO order_items VALUES (29, 17, 12, 1, 300.00);
INSERT INTO order_items VALUES (30, 17, 4, 3, 150.00);
"""

# ---------------------------------------------------------------------------
# Project Management schema (4 tables)
# ---------------------------------------------------------------------------

_PROJECT_MGMT_SCHEMA = """
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE members (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    team_id INTEGER,
    role TEXT NOT NULL,
    hourly_rate REAL NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    budget REAL NOT NULL,
    deadline TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    assigned_to INTEGER,
    title TEXT NOT NULL,
    hours_logged REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'todo',
    priority INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (assigned_to) REFERENCES members(id)
);
"""

_PROJECT_MGMT_SEED = """
INSERT INTO teams VALUES (1, 'Backend');
INSERT INTO teams VALUES (2, 'Frontend');
INSERT INTO teams VALUES (3, 'Data Science');
INSERT INTO teams VALUES (4, 'DevOps');

INSERT INTO members VALUES (1, 'Alice', 1, 'developer', 75.0);
INSERT INTO members VALUES (2, 'Bob', 1, 'developer', 80.0);
INSERT INTO members VALUES (3, 'Charlie', 1, 'manager', 95.0);
INSERT INTO members VALUES (4, 'Diana', 2, 'developer', 70.0);
INSERT INTO members VALUES (5, 'Eve', 2, 'designer', 65.0);
INSERT INTO members VALUES (6, 'Frank', 2, 'manager', 90.0);
INSERT INTO members VALUES (7, 'Grace', 3, 'developer', 85.0);
INSERT INTO members VALUES (8, 'Hank', 3, 'developer', 82.0);
INSERT INTO members VALUES (9, 'Ivy', 3, 'qa', 60.0);
INSERT INTO members VALUES (10, 'Jack', 4, 'developer', 78.0);
INSERT INTO members VALUES (11, 'Leo', 4, 'qa', 55.0);
INSERT INTO members VALUES (12, 'Mia', NULL, 'developer', 72.0);

INSERT INTO projects VALUES (1, 'API Rewrite', 1, 50000.0, '2024-06-30', 'completed');
INSERT INTO projects VALUES (2, 'Mobile App', 2, 80000.0, '2024-09-15', 'active');
INSERT INTO projects VALUES (3, 'ML Pipeline', 3, 120000.0, '2024-12-01', 'active');
INSERT INTO projects VALUES (4, 'Dashboard', 2, 30000.0, '2024-04-01', 'overdue');
INSERT INTO projects VALUES (5, 'Infra Migration', 4, 45000.0, '2024-08-15', 'active');
INSERT INTO projects VALUES (6, 'Auth Service', 1, 25000.0, '2024-05-01', 'completed');

INSERT INTO tasks VALUES (1, 1, 1, 'Design API endpoints', 40.0, 'done', 1);
INSERT INTO tasks VALUES (2, 1, 2, 'Implement auth middleware', 35.0, 'done', 1);
INSERT INTO tasks VALUES (3, 1, 1, 'Write unit tests', 20.0, 'done', 2);
INSERT INTO tasks VALUES (4, 1, 3, 'Code review', 10.0, 'done', 2);
INSERT INTO tasks VALUES (5, 2, 4, 'Design wireframes', 25.0, 'done', 1);
INSERT INTO tasks VALUES (6, 2, 5, 'Create UI components', 60.0, 'in_progress', 1);
INSERT INTO tasks VALUES (7, 2, 4, 'Implement navigation', 15.0, 'in_progress', 2);
INSERT INTO tasks VALUES (8, 2, 6, 'Sprint planning', 8.0, 'done', 3);
INSERT INTO tasks VALUES (9, 3, 7, 'Data preprocessing', 45.0, 'done', 1);
INSERT INTO tasks VALUES (10, 3, 8, 'Model training', 80.0, 'in_progress', 1);
INSERT INTO tasks VALUES (11, 3, 7, 'Feature engineering', 30.0, 'in_progress', 2);
INSERT INTO tasks VALUES (12, 3, 9, 'Write test cases', 15.0, 'todo', 2);
INSERT INTO tasks VALUES (13, 4, 4, 'Build chart components', 50.0, 'done', 1);
INSERT INTO tasks VALUES (14, 4, 5, 'Style dashboard', 35.0, 'in_progress', 2);
INSERT INTO tasks VALUES (15, 4, 6, 'Review progress', 5.0, 'done', 3);
INSERT INTO tasks VALUES (16, 5, 10, 'Setup Kubernetes', 40.0, 'in_progress', 1);
INSERT INTO tasks VALUES (17, 5, 10, 'Migrate databases', 20.0, 'todo', 1);
INSERT INTO tasks VALUES (18, 6, 2, 'Implement OAuth', 30.0, 'done', 1);
INSERT INTO tasks VALUES (19, 6, 1, 'Token management', 25.0, 'done', 2);
INSERT INTO tasks VALUES (20, 3, 9, 'QA integration tests', 0.0, 'todo', 3);
"""


# ---------------------------------------------------------------------------
# HARD dynamic tasks — advanced SQL that LLMs commonly get wrong
# ---------------------------------------------------------------------------
#
# Order totals (order_id -> total):
#   1:1300  2:70  3:700  4:1060  5:450  6:150  7:400  8:2150
#   9:360  10:1000  11:170  12:210  13:450  14:1180  15:180  16:170  17:750
#
# Customer totals:
#   Alice(1): 1300+70+700+750=2820      (4 orders, avg 705.0)
#   Bob(2): 1060+450=1510               (2 orders, avg 755.0)
#   Charlie(3): 150+400=550             (2 orders, avg 275.0)
#   Diana(4): 2150+360+1000+170=3680    (4 orders, avg 920.0)
#   Eve(5): 210+450=660                 (2 orders, avg 330.0)
#   Frank(6): 1180+180=1360             (2 orders, avg 680.0)
#   Grace(7): 170                       (1 order,  avg 170.0)
#   Hank(8): 0                          (0 orders)
#
# Overall avg order value: (1300+70+700+1060+450+150+400+2150+360+1000+170
#   +210+450+1180+180+170+750) / 17 = 10750/17 ≈ 632.35
#
# Products ordered (product_id -> total qty):
#   1:4  2:2  3:2  4:6  5:4  6:3  7:3  8:10  9:3  10:3  11:4  12:3
#   => All 12 products have been ordered. Need an unordered product.
#   (None are unordered with this data — task 5 will return empty.
#    We intentionally keep this: NOT EXISTS returning empty is tricky.)
#
# Project Management data:
#   Team avgs: Backend(1): (75+80+95)/3=83.33  Frontend(2): (70+65+90)/3=75.0
#              DataSci(3): (85+82+60)/3=75.67   DevOps(4): (78+55)/2=66.5
#   Members above team avg:
#     Backend: Charlie(95) > 83.33 YES, Bob(80) < 83.33 NO, Alice(75) < 83.33 NO
#     Frontend: Frank(90) > 75.0 YES, Diana(70) < 75.0 NO, Eve(65) < 75.0 NO
#     DataSci: Grace(85) > 75.67 YES, Hank(82) > 75.67 YES, Ivy(60) < 75.67 NO
#     DevOps: Jack(78) > 66.5 YES, Leo(55) < 66.5 NO; Mia(NULL team) excluded
#   => Charlie(95, Backend), Frank(90, Frontend), Grace(85, Data Science),
#      Hank(82, Data Science), Jack(78, DevOps)
#
#   Project task costs (project -> sum(hours * member_rate)):
#     API Rewrite(1): tasks 1(Alice,40h*75=3000) + 2(Bob,35h*80=2800)
#                     + 3(Alice,20h*75=1500) + 4(Charlie,10h*95=950) = 8250
#                     budget=50000, remaining=41750 WITHIN
#     Mobile App(2): 5(Diana,25h*70=1750) + 6(Eve,60h*65=3900)
#                    + 7(Diana,15h*70=1050) + 8(Frank,8h*90=720) = 7420
#                    budget=80000, remaining=72580 WITHIN
#     ML Pipeline(3): 9(Grace,45h*85=3825) + 10(Hank,80h*82=6560)
#                     + 11(Grace,30h*85=2550) + 12(Ivy,15h*60=900)
#                     + 20(Ivy,0h*60=0) = 13835
#                     budget=120000, remaining=106165 WITHIN
#     Dashboard(4): 13(Diana,50h*70=3500) + 14(Eve,35h*65=2275)
#                   + 15(Frank,5h*90=450) = 6225
#                   budget=30000, remaining=23775 WITHIN
#     Infra Migration(5): 16(Jack,40h*78=3120) + 17(Jack,20h*78=1560) = 4680
#                          budget=45000, remaining=40320 WITHIN
#     Auth Service(6): 18(Bob,30h*80=2400) + 19(Alice,25h*75=1875) = 4275
#                       budget=25000, remaining=20725 WITHIN
#
#   Member total hours:
#     Alice(1): 40+20+25=85  Bob(2): 35+30=65  Charlie(3): 10
#     Diana(4): 25+15+50=90  Eve(5): 60+35=95  Frank(6): 8+5=13
#     Grace(7): 45+30=75  Hank(8): 80  Ivy(9): 15+0=15  Jack(10): 40+20=60
#     Leo(11): 0 (no tasks)  Mia(12): 0 (no tasks, NULL team)

_HARD_ECOMMERCE_TASKS: List[SQLTask] = [
    # Task 1: Window function - RANK
    SQLTask(
        task_id="dyn_hard_ecom_1", difficulty="hard",
        description=(
            "Rank customers by their total spending across all orders. "
            "Show customer name, total amount spent (rounded to 2 decimals), "
            "and their spending rank. Exclude customers with no orders."
        ),
        schema_sql=_ECOMMERCE_SCHEMA, seed_data_sql=_ECOMMERCE_SEED,
        correct_query=(
            "SELECT c.name, "
            "ROUND(SUM(oi.quantity * oi.unit_price), 2) as total_spent, "
            "RANK() OVER (ORDER BY SUM(oi.quantity * oi.unit_price) DESC) as spending_rank "
            "FROM customers c "
            "JOIN orders o ON c.id = o.customer_id "
            "JOIN order_items oi ON o.id = oi.order_id "
            "GROUP BY c.id, c.name;"
        ),
        expected_output=[
            ("Diana", 3680.0, 1),
            ("Alice", 2820.0, 2),
            ("Bob", 1510.0, 3),
            ("Frank", 1360.0, 4),
            ("Eve", 660.0, 5),
            ("Charlie", 550.0, 6),
            ("Grace", 170.0, 7),
        ],
        max_steps=15,
        hint_general="This requires a window function to assign ranks based on aggregated values.",
        hint_specific="Use RANK() OVER (ORDER BY SUM(...) DESC) with a GROUP BY on customer.",
    ),
    # Task 2: Window function - Running total
    SQLTask(
        task_id="dyn_hard_ecom_2", difficulty="hard",
        description=(
            "Show a running total of order amounts per customer, ordered by date. "
            "Display customer name, order date, the order total (rounded to 2 decimals), "
            "and the cumulative running total (rounded to 2 decimals). "
            "Order results by customer name then order date."
        ),
        schema_sql=_ECOMMERCE_SCHEMA, seed_data_sql=_ECOMMERCE_SEED,
        correct_query=(
            "SELECT c.name, o.order_date, "
            "ROUND(SUM(oi.quantity * oi.unit_price), 2) as order_total, "
            "ROUND(SUM(SUM(oi.quantity * oi.unit_price)) OVER "
            "(PARTITION BY c.id ORDER BY o.order_date), 2) as running_total "
            "FROM customers c "
            "JOIN orders o ON c.id = o.customer_id "
            "JOIN order_items oi ON o.id = oi.order_id "
            "GROUP BY c.id, c.name, o.id, o.order_date "
            "ORDER BY c.name, o.order_date;"
        ),
        expected_output=[
            ("Alice", "2024-01-10", 1300.0, 1300.0),
            ("Alice", "2024-02-14", 70.0, 1370.0),
            ("Alice", "2024-03-20", 700.0, 2070.0),
            ("Alice", "2024-09-01", 750.0, 2820.0),
            ("Bob", "2024-01-22", 1060.0, 1060.0),
            ("Bob", "2024-04-05", 450.0, 1510.0),
            ("Charlie", "2024-02-28", 150.0, 150.0),
            ("Charlie", "2024-05-15", 400.0, 550.0),
            ("Diana", "2024-01-05", 2150.0, 2150.0),
            ("Diana", "2024-03-18", 360.0, 2510.0),
            ("Diana", "2024-06-01", 1000.0, 3510.0),
            ("Diana", "2024-07-20", 170.0, 3680.0),
            ("Eve", "2024-02-10", 210.0, 210.0),
            ("Eve", "2024-08-01", 450.0, 660.0),
            ("Frank", "2024-03-15", 1180.0, 1180.0),
            ("Frank", "2024-05-22", 180.0, 1360.0),
            ("Grace", "2024-04-10", 170.0, 170.0),
        ],
        max_steps=15,
        hint_general="You need a window function with PARTITION BY and ORDER BY inside an aggregate query.",
        hint_specific="Use SUM(SUM(...)) OVER (PARTITION BY customer ORDER BY date) — the outer SUM is the window function over the inner grouped SUM.",
    ),
    # Task 3: CTE with aggregation comparison
    SQLTask(
        task_id="dyn_hard_ecom_3", difficulty="hard",
        description=(
            "Using a Common Table Expression (CTE), find customers whose average "
            "order value exceeds the overall average order value across all customers. "
            "Show customer name and their average order value (rounded to 2 decimals), "
            "ordered by average order value descending."
        ),
        schema_sql=_ECOMMERCE_SCHEMA, seed_data_sql=_ECOMMERCE_SEED,
        correct_query=(
            "WITH order_totals AS ("
            "  SELECT o.id as order_id, o.customer_id, "
            "  SUM(oi.quantity * oi.unit_price) as order_total "
            "  FROM orders o JOIN order_items oi ON o.id = oi.order_id "
            "  GROUP BY o.id, o.customer_id"
            "), customer_avg AS ("
            "  SELECT c.id, c.name, ROUND(AVG(ot.order_total), 2) as avg_order_value "
            "  FROM customers c JOIN order_totals ot ON c.id = ot.customer_id "
            "  GROUP BY c.id, c.name"
            "), overall AS ("
            "  SELECT AVG(order_total) as overall_avg FROM order_totals"
            ") "
            "SELECT ca.name, ca.avg_order_value "
            "FROM customer_avg ca, overall ov "
            "WHERE ca.avg_order_value > ov.overall_avg "
            "ORDER BY ca.avg_order_value DESC;"
        ),
        # overall avg = 10750/17 ≈ 632.35
        # Diana avg=920.0, Bob avg=755.0, Alice avg=705.0, Frank avg=680.0
        expected_output=[
            ("Diana", 920.0),
            ("Bob", 755.0),
            ("Alice", 705.0),
            ("Frank", 680.0),
        ],
        max_steps=15,
        hint_general="You need a CTE to compute per-order totals first, then compare customer averages to overall average.",
        hint_specific="Build a CTE for order totals (JOIN order_items), then a CTE for customer averages, then a CTE for overall average, and filter.",
    ),
    # Task 4: CASE WHEN with aggregation
    SQLTask(
        task_id="dyn_hard_ecom_4", difficulty="hard",
        description=(
            "Categorize each customer's orders by size: 'small' (total < 200), "
            "'medium' (200 to 500 inclusive), 'large' (> 500). Show customer name "
            "and the count of small, medium, and large orders. Order by customer name."
        ),
        schema_sql=_ECOMMERCE_SCHEMA, seed_data_sql=_ECOMMERCE_SEED,
        correct_query=(
            "SELECT c.name, "
            "SUM(CASE WHEN ot.order_total < 200 THEN 1 ELSE 0 END) as small_orders, "
            "SUM(CASE WHEN ot.order_total >= 200 AND ot.order_total <= 500 THEN 1 ELSE 0 END) as medium_orders, "
            "SUM(CASE WHEN ot.order_total > 500 THEN 1 ELSE 0 END) as large_orders "
            "FROM customers c "
            "JOIN orders o ON c.id = o.customer_id "
            "JOIN (SELECT order_id, SUM(quantity * unit_price) as order_total "
            "      FROM order_items GROUP BY order_id) ot ON o.id = ot.order_id "
            "GROUP BY c.id, c.name ORDER BY c.name;"
        ),
        # Alice orders: 1300(L), 70(S), 700(L), 750(L) -> s=1, m=0, l=3
        # Bob: 1060(L), 450(M) -> s=0, m=1, l=1
        # Charlie: 150(S), 400(M) -> s=1, m=1, l=0
        # Diana: 2150(L), 360(M), 1000(L), 170(S) -> s=1, m=1, l=2
        # Eve: 210(M), 450(M) -> s=0, m=2, l=0
        # Frank: 1180(L), 180(S) -> s=1, m=0, l=1
        # Grace: 170(S) -> s=1, m=0, l=0
        expected_output=[
            ("Alice", 1, 0, 3),
            ("Bob", 0, 1, 1),
            ("Charlie", 1, 1, 0),
            ("Diana", 1, 1, 2),
            ("Eve", 0, 2, 0),
            ("Frank", 1, 0, 1),
            ("Grace", 1, 0, 0),
        ],
        max_steps=12,
        hint_general="You need to compute order totals first (as a subquery), then use CASE WHEN inside SUM for each category.",
        hint_specific="First aggregate order_items by order_id to get order totals, then JOIN and use CASE WHEN with GROUP BY on customer.",
    ),
    # Task 5: NOT EXISTS — products never ordered
    SQLTask(
        task_id="dyn_hard_ecom_5", difficulty="hard",
        description=(
            "Find all products that have never been included in any order. "
            "Show product name and category. Use NOT EXISTS. "
            "Order by product name."
        ),
        schema_sql=_ECOMMERCE_SCHEMA, seed_data_sql=_ECOMMERCE_SEED,
        correct_query=(
            "SELECT p.name, p.category FROM products p "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM order_items oi WHERE oi.product_id = p.id"
            ") ORDER BY p.name;"
        ),
        # All 12 products appear in order_items, so result is empty
        expected_output=[],
        max_steps=12,
        hint_general="Use NOT EXISTS with a correlated subquery checking order_items for each product.",
        hint_specific="SELECT ... FROM products p WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.id). Note: all products may have been ordered.",
    ),
    # Task 6: Multi-table JOIN with HAVING and date filter
    SQLTask(
        task_id="dyn_hard_ecom_6", difficulty="hard",
        description=(
            "Find customers who placed more than 3 orders in 2024 and spent "
            "over $2000 total in that year. Show customer name, order count, "
            "and total spent (rounded to 2 decimals). Order by total spent descending."
        ),
        schema_sql=_ECOMMERCE_SCHEMA, seed_data_sql=_ECOMMERCE_SEED,
        correct_query=(
            "SELECT c.name, COUNT(DISTINCT o.id) as order_count, "
            "ROUND(SUM(oi.quantity * oi.unit_price), 2) as total_spent "
            "FROM customers c "
            "JOIN orders o ON c.id = o.customer_id "
            "JOIN order_items oi ON o.id = oi.order_id "
            "WHERE o.order_date >= '2024-01-01' AND o.order_date < '2025-01-01' "
            "GROUP BY c.id, c.name "
            "HAVING COUNT(DISTINCT o.id) > 3 AND SUM(oi.quantity * oi.unit_price) > 2000 "
            "ORDER BY total_spent DESC;"
        ),
        # Alice: 4 orders in 2024, total=2820 -> YES
        # Diana: 4 orders in 2024, total=3680 -> YES
        # Others have <=2 orders or less total
        expected_output=[
            ("Diana", 4, 3680.0),
            ("Alice", 4, 2820.0),
        ],
        max_steps=12,
        hint_general="You need JOIN across 3 tables, a WHERE for date filtering, and HAVING with two conditions on aggregates.",
        hint_specific="Use COUNT(DISTINCT o.id) for order count (not COUNT(*) which counts items). Both HAVING conditions must be met.",
    ),
    # Task 7: Subquery in SELECT — best seller per category
    SQLTask(
        task_id="dyn_hard_ecom_7", difficulty="hard",
        description=(
            "For each product category in the e-commerce database, show: "
            "category name, number of distinct products, total revenue "
            "(sum of quantity * unit_price, rounded to 2 decimals), and the "
            "name of the best-selling product (highest total quantity sold) in "
            "that category. Order by total revenue descending."
        ),
        schema_sql=_ECOMMERCE_SCHEMA, seed_data_sql=_ECOMMERCE_SEED,
        correct_query=(
            "SELECT p.category, "
            "COUNT(DISTINCT p.id) as product_count, "
            "ROUND(SUM(oi.quantity * oi.unit_price), 2) as total_revenue, "
            "(SELECT p2.name FROM products p2 "
            " JOIN order_items oi2 ON p2.id = oi2.product_id "
            " WHERE p2.category = p.category "
            " GROUP BY p2.id, p2.name "
            " ORDER BY SUM(oi2.quantity) DESC LIMIT 1) as best_seller "
            "FROM products p "
            "JOIN order_items oi ON p.id = oi.product_id "
            "GROUP BY p.category "
            "ORDER BY total_revenue DESC;"
        ),
        # Electronics: p1 qty=5(5000), p2 qty=2(1400), p3 qty=2(900), p4 qty=7(1050) -> rev=8350, best=Headphones
        # Accessories: p11 qty=4(240), p12 qty=3(900) -> rev=1140, best=Backpack
        # Clothing: p8 qty=10(200), p9 qty=3(270), p10 qty=3(390) -> rev=860, best=T-Shirt
        # Books: p5 qty=4(160), p6 qty=3(90), p7 qty=3(150) -> rev=400, best=Python Crash Course
        expected_output=[
            ("Electronics", 4, 8350.0, "Headphones"),
            ("Accessories", 2, 1140.0, "Backpack"),
            ("Clothing", 3, 860.0, "T-Shirt"),
            ("Books", 3, 400.0, "Python Crash Course"),
        ],
        max_steps=15,
        hint_general="You need a correlated subquery in SELECT to find the best-selling product per category.",
        hint_specific="Use a correlated subquery: (SELECT p2.name FROM products p2 JOIN order_items ... WHERE p2.category = p.category GROUP BY p2.id ORDER BY SUM(quantity) DESC LIMIT 1).",
    ),
    # Task 8: Window function LAG + date diff
    SQLTask(
        task_id="dyn_hard_ecom_8", difficulty="hard",
        description=(
            "For each customer with more than one order, show the customer name, "
            "each order date, and the number of days since their previous order "
            "(NULL for their first order). Use the julianday function for date "
            "difference. Order by customer name, then order date."
        ),
        schema_sql=_ECOMMERCE_SCHEMA, seed_data_sql=_ECOMMERCE_SEED,
        correct_query=(
            "SELECT name, order_date, "
            "CAST(julianday(order_date) - julianday(prev_date) AS INTEGER) as days_since_prev "
            "FROM ("
            "  SELECT c.name, c.id as cid, o.order_date, "
            "  LAG(o.order_date) OVER (PARTITION BY c.id ORDER BY o.order_date) as prev_date, "
            "  COUNT(*) OVER (PARTITION BY c.id) as order_count "
            "  FROM customers c "
            "  JOIN orders o ON c.id = o.customer_id"
            ") sub "
            "WHERE order_count > 1 "
            "ORDER BY name, order_date;"
        ),
        # Alice: 01-10(NULL), 02-14(35d), 03-20(35d), 09-01(165d)
        # Bob: 01-22(NULL), 04-05(74d)
        # Charlie: 02-28(NULL), 05-15(77d)  -- actually 2024-02-28 to 2024-05-15 = 77 days
        # Diana: 01-05(NULL), 03-18(73d), 06-01(75d), 07-20(49d)
        # Eve: 02-10(NULL), 08-01(173d)
        # Frank: 03-15(NULL), 05-22(68d)
        # Grace: only 1 order -> excluded
        expected_output=[
            ("Alice", "2024-01-10", None),
            ("Alice", "2024-02-14", 35),
            ("Alice", "2024-03-20", 35),
            ("Alice", "2024-09-01", 165),
            ("Bob", "2024-01-22", None),
            ("Bob", "2024-04-05", 74),
            ("Charlie", "2024-02-28", None),
            ("Charlie", "2024-05-15", 77),
            ("Diana", "2024-01-05", None),
            ("Diana", "2024-03-18", 73),
            ("Diana", "2024-06-01", 75),
            ("Diana", "2024-07-20", 49),
            ("Eve", "2024-02-10", None),
            ("Eve", "2024-08-01", 173),
            ("Frank", "2024-03-15", None),
            ("Frank", "2024-05-22", 68),
        ],
        max_steps=15,
        hint_general="Use LAG() window function to get the previous order date per customer, then compute the date difference.",
        hint_specific="LAG(o.order_date) OVER (PARTITION BY c.id ORDER BY o.order_date) gives the previous date. Use julianday() for date math. Filter with COUNT(*) OVER to exclude single-order customers.",
    ),
]

_HARD_PROJECT_TASKS: List[SQLTask] = [
    # Task 9: Self-referencing comparison (correlated subquery)
    SQLTask(
        task_id="dyn_hard_proj_1", difficulty="hard",
        description=(
            "Find team members who earn more than their team's average hourly rate. "
            "Show member name, hourly rate, and team name. "
            "Order by hourly rate descending."
        ),
        schema_sql=_PROJECT_MGMT_SCHEMA, seed_data_sql=_PROJECT_MGMT_SEED,
        correct_query=(
            "SELECT m.name, m.hourly_rate, t.name as team_name "
            "FROM members m "
            "JOIN teams t ON m.team_id = t.id "
            "WHERE m.hourly_rate > ("
            "  SELECT AVG(m2.hourly_rate) FROM members m2 "
            "  WHERE m2.team_id = m.team_id"
            ") ORDER BY m.hourly_rate DESC;"
        ),
        # Backend avg: (75+80+95)/3=83.33 -> Charlie(95) above
        # Frontend avg: (70+65+90)/3=75.0 -> Frank(90) above
        # DataSci avg: (85+82+60)/3=75.67 -> Grace(85), Hank(82) above
        # DevOps avg: (78+55)/2=66.5 -> Jack(78) above, Leo(55) below
        # Mia has NULL team_id, excluded by JOIN
        expected_output=[
            ("Charlie", 95.0, "Backend"),
            ("Frank", 90.0, "Frontend"),
            ("Grace", 85.0, "Data Science"),
            ("Hank", 82.0, "Data Science"),
            ("Jack", 78.0, "DevOps"),
        ],
        max_steps=15,
        hint_general="You need a correlated subquery that computes the average for each member's own team.",
        hint_specific="Use WHERE m.hourly_rate > (SELECT AVG(m2.hourly_rate) FROM members m2 WHERE m2.team_id = m.team_id).",
    ),
    # Task 8: Complex GROUP BY with multiple aggregates and budget calculation
    SQLTask(
        task_id="dyn_hard_proj_2", difficulty="hard",
        description=(
            "For each project, show: project name, team name, number of tasks, "
            "total hours logged (rounded to 1 decimal), total labor cost "
            "(sum of hours_logged * assigned member's hourly_rate, rounded to 2 decimals), "
            "and budget remaining (budget - labor cost, rounded to 2 decimals). "
            "Only include tasks that have an assigned member. "
            "Order by budget remaining ascending."
        ),
        schema_sql=_PROJECT_MGMT_SCHEMA, seed_data_sql=_PROJECT_MGMT_SEED,
        correct_query=(
            "SELECT p.name as project, tm.name as team, "
            "COUNT(t.id) as task_count, "
            "ROUND(SUM(t.hours_logged), 1) as total_hours, "
            "ROUND(SUM(t.hours_logged * m.hourly_rate), 2) as labor_cost, "
            "ROUND(p.budget - SUM(t.hours_logged * m.hourly_rate), 2) as budget_remaining "
            "FROM projects p "
            "JOIN teams tm ON p.team_id = tm.id "
            "JOIN tasks t ON p.id = t.project_id "
            "JOIN members m ON t.assigned_to = m.id "
            "GROUP BY p.id, p.name, tm.name, p.budget "
            "ORDER BY budget_remaining ASC;"
        ),
        # Auth Service: tasks 18(Bob,30*80=2400)+19(Alice,25*75=1875)=4275 cost, 55h, budget 25000, rem=20725
        # Dashboard: 13(Diana,50*70=3500)+14(Eve,35*65=2275)+15(Frank,5*90=450)=6225 cost, 90h, rem=23775
        # Infra Migration: 16(Jack,40*78=3120)+17(Jack,20*78=1560)=4680 cost, 60h, rem=40320
        # API Rewrite: 1(Alice,40*75=3000)+2(Bob,35*80=2800)+3(Alice,20*75=1500)+4(Charlie,10*95=950)=8250 cost, 105h, rem=41750
        # Mobile App: 5(Diana,25*70=1750)+6(Eve,60*65=3900)+7(Diana,15*70=1050)+8(Frank,8*90=720)=7420 cost, 108h, rem=72580
        # ML Pipeline: 9(Grace,45*85=3825)+10(Hank,80*82=6560)+11(Grace,30*85=2550)+12(Ivy,15*60=900)+20(Ivy,0*60=0)=13835, 170h, rem=106165
        expected_output=[
            ("Auth Service", "Backend", 2, 55.0, 4275.0, 20725.0),
            ("Dashboard", "Frontend", 3, 90.0, 6225.0, 23775.0),
            ("Infra Migration", "DevOps", 2, 60.0, 4680.0, 40320.0),
            ("API Rewrite", "Backend", 4, 105.0, 8250.0, 41750.0),
            ("Mobile App", "Frontend", 4, 108.0, 7420.0, 72580.0),
            ("ML Pipeline", "Data Science", 5, 170.0, 13835.0, 106165.0),
        ],
        max_steps=15,
        hint_general="You need to JOIN projects, teams, tasks, and members, then aggregate with multiple computations per group.",
        hint_specific="JOIN tasks to members to get hourly_rate, then SUM(hours_logged * hourly_rate) for labor cost. Use budget - that sum for remaining.",
    ),
    # Task 9: COALESCE with LEFT JOIN
    SQLTask(
        task_id="dyn_hard_proj_3", difficulty="hard",
        description=(
            "List ALL team members and their total hours logged across all tasks. "
            "Members with no assigned tasks should show 0 hours. "
            "Show member name and total hours (rounded to 1 decimal). "
            "Order by total hours descending, then by name ascending."
        ),
        schema_sql=_PROJECT_MGMT_SCHEMA, seed_data_sql=_PROJECT_MGMT_SEED,
        correct_query=(
            "SELECT m.name, "
            "COALESCE(ROUND(SUM(t.hours_logged), 1), 0) as total_hours "
            "FROM members m "
            "LEFT JOIN tasks t ON m.id = t.assigned_to "
            "GROUP BY m.id, m.name "
            "ORDER BY total_hours DESC, m.name ASC;"
        ),
        # Eve: 60+35=95, Diana: 25+15+50=90, Alice: 40+20+25=85,
        # Hank: 80, Grace: 45+30=75, Bob: 35+30=65, Jack: 40+20=60,
        # Ivy: 15+0=15, Frank: 8+5=13, Charlie: 10, Leo: 0, Mia: 0
        expected_output=[
            ("Eve", 95.0),
            ("Diana", 90.0),
            ("Alice", 85.0),
            ("Hank", 80.0),
            ("Grace", 75.0),
            ("Bob", 65.0),
            ("Jack", 60.0),
            ("Ivy", 15.0),
            ("Frank", 13.0),
            ("Charlie", 10.0),
            ("Leo", 0),
            ("Mia", 0),
        ],
        max_steps=12,
        hint_general="Use LEFT JOIN to include members with no tasks, and COALESCE to convert NULL sums to 0.",
        hint_specific="LEFT JOIN tasks ON m.id = t.assigned_to, then COALESCE(SUM(t.hours_logged), 0) to handle NULLs.",
    ),
]


DYNAMIC_TEMPLATES = DYNAMIC_TEMPLATES + _HARD_ECOMMERCE_TASKS + _HARD_PROJECT_TASKS

# Combine all tasks
ALL_TASKS: List[SQLTask] = STATIC_TASKS + DYNAMIC_TEMPLATES

# Total: 9 static + 14 original dynamic + 11 hard dynamic (8 e-commerce + 3 project mgmt) = 34 tasks


def get_task_by_index(index: int) -> SQLTask:
    """Get a task by index (wraps around)."""
    return ALL_TASKS[index % len(ALL_TASKS)]


def get_task_by_id(task_id: str) -> SQLTask:
    """Get a task by its ID."""
    for task in ALL_TASKS:
        if task.task_id == task_id:
            return task
    raise ValueError(f"Unknown task_id: {task_id}")
