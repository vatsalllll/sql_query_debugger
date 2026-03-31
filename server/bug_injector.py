"""
Random SQL Bug Injector
-----------------------
Takes a correct SQL query and injects random bugs at various difficulty levels.
Makes every episode unique — essentially infinite task variety.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class InjectedBug:
    difficulty: str
    bug_type: str
    description: str
    hint_general: str
    hint_specific: str


# ---------------------------------------------------------------------------
# Easy bugs — Syntax errors
# ---------------------------------------------------------------------------

def _inject_keyword_typo(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Introduce a typo in a SQL keyword."""
    typos = {
        "SELECT": ["SELCT", "SELCET", "SEELCT", "SELET"],
        "FROM": ["FORM", "FRON", "FRMM"],
        "WHERE": ["WHER", "WHRE", "WEHRE"],
        "GROUP BY": ["GROP BY", "GROUP BT", "GRUOP BY"],
        "ORDER BY": ["ORDR BY", "ORDER BT", "ORDE BY"],
        "HAVING": ["HAVNG", "HAVIG", "HAVVING"],
        "INSERT": ["INSRT", "INSER", "INSRET"],
        "UPDATE": ["UPDTE", "UPDAE", "UPATE"],
        "DELETE": ["DELTE", "DELET", "DELEET"],
        "JOIN": ["JION", "JOING", "JION"],
        "LEFT JOIN": ["LFET JOIN", "LEFT JION", "LETF JOIN"],
        "INNER JOIN": ["INNR JOIN", "INNER JION", "INER JOIN"],
    }

    upper_query = query.upper()
    candidates = [(k, v) for k, v in typos.items() if k in upper_query]
    if not candidates:
        return _inject_missing_comma(query, rng)

    keyword, replacements = rng.choice(candidates)
    typo = rng.choice(replacements)

    # Find the keyword case-insensitively and replace first occurrence
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    broken = pattern.sub(typo, query, count=1)

    return broken, InjectedBug(
        difficulty="easy",
        bug_type="keyword_typo",
        description=f"Typo in SQL keyword: '{keyword}' → '{typo}'",
        hint_general="Check for typos in SQL keywords.",
        hint_specific=f"The keyword '{keyword}' is misspelled as '{typo}'.",
    )


def _inject_missing_comma(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Remove a comma from the SELECT clause."""
    # Find commas in the query (before FROM)
    from_match = re.search(r'\bFROM\b', query, re.IGNORECASE)
    if not from_match:
        return _inject_unclosed_quote(query, rng)

    select_part = query[:from_match.start()]
    comma_positions = [i for i, c in enumerate(select_part) if c == ',']

    if not comma_positions:
        return _inject_unclosed_quote(query, rng)

    pos = rng.choice(comma_positions)
    broken = query[:pos] + query[pos + 1:]

    return broken, InjectedBug(
        difficulty="easy",
        bug_type="missing_comma",
        description="Missing comma between column names in SELECT clause.",
        hint_general="Check the column list for missing punctuation.",
        hint_specific="A comma is missing between columns in the SELECT clause.",
    )


def _inject_unclosed_quote(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Remove a closing single quote from a string literal."""
    # Find string literals
    quote_pairs = []
    i = 0
    while i < len(query):
        if query[i] == "'":
            start = i
            i += 1
            while i < len(query) and query[i] != "'":
                i += 1
            if i < len(query):
                quote_pairs.append((start, i))
            i += 1
        else:
            i += 1

    if not quote_pairs:
        # Fallback: add a random semicolon in the middle
        mid = len(query) // 2
        broken = query[:mid] + ";" + query[mid:]
        return broken, InjectedBug(
            difficulty="easy",
            bug_type="extra_semicolon",
            description="Extra semicolon in the middle of the query.",
            hint_general="Check for misplaced punctuation.",
            hint_specific="There's an extra semicolon breaking the query.",
        )

    _, close_pos = rng.choice(quote_pairs)
    broken = query[:close_pos] + query[close_pos + 1:]

    return broken, InjectedBug(
        difficulty="easy",
        bug_type="unclosed_quote",
        description="Missing closing quote in a string literal.",
        hint_general="Check string literals for proper quoting.",
        hint_specific="A string literal is missing its closing single quote.",
    )


def _inject_missing_semicolon_keyword(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Remove a critical keyword like AS, ON, or BY."""
    removable = [
        (r'\bAS\b', 'AS', "alias keyword 'AS'"),
        (r'\bON\b', 'ON', "join condition keyword 'ON'"),
        (r'\bBY\b', 'BY', "grouping keyword 'BY'"),
    ]
    rng.shuffle(removable)
    for pattern, keyword, desc in removable:
        if re.search(pattern, query, re.IGNORECASE):
            broken = re.sub(pattern, '', query, count=1, flags=re.IGNORECASE)
            return broken, InjectedBug(
                difficulty="easy",
                bug_type="missing_keyword",
                description=f"Missing {desc}.",
                hint_general="Check for missing SQL keywords.",
                hint_specific=f"The {desc} is missing from the query.",
            )
    return _inject_keyword_typo(query, rng)


EASY_INJECTORS = [
    _inject_keyword_typo,
    _inject_missing_comma,
    _inject_unclosed_quote,
    _inject_missing_semicolon_keyword,
]


# ---------------------------------------------------------------------------
# Medium bugs — Schema errors
# ---------------------------------------------------------------------------

def _inject_wrong_column(query: str, rng: random.Random, schema_columns: List[str]) -> Tuple[str, InjectedBug]:
    """Replace a column name with a plausible but wrong name."""
    wrong_names = {
        "name": ["username", "full_name", "user_name", "nama"],
        "email": ["mail", "email_address", "e_mail"],
        "age": ["years", "user_age", "ages"],
        "salary": ["wage", "pay", "income", "sal"],
        "amount": ["total", "price", "cost", "value"],
        "product": ["item", "product_name", "prod"],
        "order_date": ["date", "created_at", "ordered_at"],
        "hire_date": ["start_date", "joined_at", "hired_at"],
        "department_id": ["dept_id", "dep_id", "department"],
        "user_id": ["uid", "userid", "usr_id"],
        "employee_id": ["emp_id", "eid", "employeeid"],
    }

    for col, alternatives in wrong_names.items():
        pattern = re.compile(r'\b' + re.escape(col) + r'\b', re.IGNORECASE)
        if pattern.search(query):
            wrong = rng.choice(alternatives)
            broken = pattern.sub(wrong, query, count=1)
            return broken, InjectedBug(
                difficulty="medium",
                bug_type="wrong_column",
                description=f"Wrong column name: '{col}' → '{wrong}'",
                hint_general="Check that column names match the schema exactly.",
                hint_specific=f"The column is called '{col}', not '{wrong}'. Check the schema.",
            )

    return _inject_wrong_table(query, rng)


def _inject_wrong_table(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Replace a table name with a plausible but wrong name."""
    wrong_tables = {
        "users": ["user", "usr", "accounts"],
        "orders": ["order", "purchases", "transactions"],
        "employees": ["employee", "emp", "staff"],
        "departments": ["department", "dept", "depts"],
        "products": ["product", "items", "goods"],
        "customers": ["customer", "clients", "buyers"],
    }

    for table, alternatives in wrong_tables.items():
        pattern = re.compile(r'\b' + re.escape(table) + r'\b', re.IGNORECASE)
        if pattern.search(query):
            wrong = rng.choice(alternatives)
            broken = pattern.sub(wrong, query, count=1)
            return broken, InjectedBug(
                difficulty="medium",
                bug_type="wrong_table",
                description=f"Wrong table name: '{table}' → '{wrong}'",
                hint_general="Check that table names match the schema exactly.",
                hint_specific=f"The table is called '{table}', not '{wrong}'.",
            )

    # Fallback to column error
    return _inject_wrong_column(query, rng, [])


def _inject_missing_join(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Remove a JOIN clause, leaving a cross-reference that will fail."""
    join_pattern = re.compile(
        r'\b(LEFT\s+|RIGHT\s+|INNER\s+|OUTER\s+|CROSS\s+)?JOIN\s+\w+(\s+\w+)?\s+ON\s+[^)]+?(?=\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|\bHAVING\b|;|\s*$)',
        re.IGNORECASE
    )
    match = join_pattern.search(query)
    if match:
        broken = query[:match.start()] + query[match.end():]
        return broken, InjectedBug(
            difficulty="medium",
            bug_type="missing_join",
            description="Missing JOIN clause for cross-table reference.",
            hint_general="You're referencing columns from a table that isn't joined.",
            hint_specific="Add the appropriate JOIN clause to connect the tables.",
        )

    return _inject_wrong_column(query, rng, [])


def _inject_wrong_alias(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Change a table alias to break references."""
    # Find aliases like "users u" or "users AS u"
    alias_pattern = re.compile(r'(\w+)\s+(?:AS\s+)?([a-z])\b', re.IGNORECASE)
    matches = list(alias_pattern.finditer(query))
    if matches:
        match = rng.choice(matches)
        old_alias = match.group(2)
        new_alias = rng.choice([c for c in 'xyzwvq' if c != old_alias.lower()])
        # Replace only the alias definition, not its usages
        broken = query[:match.start(2)] + new_alias + query[match.end(2):]
        return broken, InjectedBug(
            difficulty="medium",
            bug_type="wrong_alias",
            description=f"Table alias '{old_alias}' defined but references use the old alias.",
            hint_general="Check that table aliases are consistent throughout the query.",
            hint_specific=f"The alias '{old_alias}' was changed to '{new_alias}' in the definition but not in references.",
        )

    return _inject_wrong_table(query, rng)


MEDIUM_INJECTORS = [
    lambda q, r: _inject_wrong_column(q, r, []),
    _inject_wrong_table,
    _inject_missing_join,
    _inject_wrong_alias,
]


# ---------------------------------------------------------------------------
# Hard bugs — Logic errors
# ---------------------------------------------------------------------------

def _inject_wrong_join_type(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Change LEFT JOIN to INNER JOIN or vice versa."""
    if re.search(r'\bLEFT\s+JOIN\b', query, re.IGNORECASE):
        broken = re.sub(r'\bLEFT\s+JOIN\b', 'INNER JOIN', query, count=1, flags=re.IGNORECASE)
        return broken, InjectedBug(
            difficulty="hard",
            bug_type="wrong_join_type",
            description="INNER JOIN used instead of LEFT JOIN — drops unmatched rows.",
            hint_general="Think about which type of JOIN preserves all rows from the left table.",
            hint_specific="INNER JOIN excludes rows with no match. Use LEFT JOIN to include all rows from the left table.",
        )

    if re.search(r'\bINNER\s+JOIN\b', query, re.IGNORECASE):
        broken = re.sub(r'\bINNER\s+JOIN\b', 'LEFT JOIN', query, count=1, flags=re.IGNORECASE)
        return broken, InjectedBug(
            difficulty="hard",
            bug_type="wrong_join_type",
            description="LEFT JOIN used instead of INNER JOIN — includes unwanted NULL rows.",
            hint_general="Think about whether you want rows that have no match.",
            hint_specific="LEFT JOIN includes rows with no match (NULLs). Use INNER JOIN if you only want matched rows.",
        )

    if re.search(r'\bJOIN\b', query, re.IGNORECASE):
        broken = re.sub(r'\bJOIN\b', 'LEFT JOIN', query, count=1, flags=re.IGNORECASE)
        return broken, InjectedBug(
            difficulty="hard",
            bug_type="wrong_join_type",
            description="LEFT JOIN used instead of INNER JOIN.",
            hint_general="Check whether the JOIN type matches the expected result.",
            hint_specific="Use INNER JOIN (or plain JOIN) instead of LEFT JOIN.",
        )

    return _inject_missing_group_by(query, rng)


def _inject_missing_group_by(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Remove GROUP BY clause."""
    pattern = re.compile(r'\bGROUP\s+BY\b[^;]*?(?=\bHAVING\b|\bORDER\b|\bLIMIT\b|;|\s*$)', re.IGNORECASE)
    match = pattern.search(query)
    if match:
        broken = query[:match.start()] + query[match.end():]
        return broken, InjectedBug(
            difficulty="hard",
            bug_type="missing_group_by",
            description="Missing GROUP BY clause with aggregate function.",
            hint_general="When using aggregate functions like SUM/COUNT/AVG, check if GROUP BY is needed.",
            hint_specific="Add GROUP BY clause to group the aggregation by the non-aggregate columns.",
        )

    return _inject_wrong_aggregate(query, rng)


def _inject_wrong_aggregate(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Swap aggregate functions: COUNT↔SUM, AVG↔MAX, etc."""
    swaps = [
        ("COUNT", "SUM"), ("SUM", "COUNT"),
        ("AVG", "MAX"), ("MAX", "AVG"),
        ("MIN", "MAX"), ("MAX", "MIN"),
        ("COUNT", "AVG"), ("AVG", "COUNT"),
    ]

    for orig, replacement in swaps:
        pattern = re.compile(r'\b' + orig + r'\s*\(', re.IGNORECASE)
        if pattern.search(query):
            broken = pattern.sub(replacement + '(', query, count=1)
            return broken, InjectedBug(
                difficulty="hard",
                bug_type="wrong_aggregate",
                description=f"Wrong aggregate function: {orig}() → {replacement}()",
                hint_general="Check that the aggregate function matches what you need.",
                hint_specific=f"Use {orig}() instead of {replacement}().",
            )

    return _inject_wrong_where(query, rng)


def _inject_wrong_where(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Change comparison operator in WHERE clause."""
    op_swaps = [
        (r'>\s', '< ', '>', '<'),
        (r'<\s', '> ', '<', '>'),
        (r'>=', '<', '>=', '<'),
        (r'<=', '>', '<=', '>'),
        (r'=\s', '!= ', '=', '!='),
    ]

    for pattern, replacement, orig_desc, new_desc in op_swaps:
        where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)
        if where_match:
            after_where = query[where_match.end():]
            if re.search(pattern, after_where):
                fixed_after = re.sub(pattern, replacement, after_where, count=1)
                broken = query[:where_match.end()] + fixed_after
                return broken, InjectedBug(
                    difficulty="hard",
                    bug_type="wrong_operator",
                    description=f"Wrong comparison operator: '{orig_desc}' → '{new_desc}'",
                    hint_general="Check the comparison operators in the WHERE clause.",
                    hint_specific=f"The operator should be '{orig_desc}', not '{new_desc}'.",
                )

    return _inject_wrong_join_type(query, rng)


def _inject_global_vs_correlated(query: str, rng: random.Random) -> Tuple[str, InjectedBug]:
    """Turn a correlated subquery into a global one (or vice versa)."""
    # Look for correlated subquery pattern
    corr_pattern = re.compile(
        r'WHERE\s+\w+\.\w+\s*=\s*\w+\.\w+\s*\)',
        re.IGNORECASE
    )
    match = corr_pattern.search(query)
    if match:
        # Remove the correlation condition
        broken = re.sub(
            r'WHERE\s+\w+\.\w+\s*=\s*\w+\.\w+',
            '',
            query,
            count=1,
            flags=re.IGNORECASE
        )
        return broken, InjectedBug(
            difficulty="hard",
            bug_type="global_vs_correlated",
            description="Subquery computes a global aggregate instead of per-group.",
            hint_general="The subquery should be correlated to the outer query.",
            hint_specific="Add a WHERE clause inside the subquery to correlate it with the outer query's group.",
        )

    return _inject_wrong_aggregate(query, rng)


HARD_INJECTORS = [
    _inject_wrong_join_type,
    _inject_missing_group_by,
    _inject_wrong_aggregate,
    _inject_wrong_where,
    _inject_global_vs_correlated,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inject_bug(query: str, difficulty: str, seed: int | None = None) -> Tuple[str, InjectedBug]:
    """
    Inject a random bug into a correct SQL query.

    Args:
        query: A correct SQL query
        difficulty: "easy", "medium", or "hard"
        seed: Optional seed for reproducibility

    Returns:
        (broken_query, bug_info)
    """
    rng = random.Random(seed)

    injectors = {
        "easy": EASY_INJECTORS,
        "medium": MEDIUM_INJECTORS,
        "hard": HARD_INJECTORS,
    }

    pool = injectors.get(difficulty, EASY_INJECTORS)
    rng.shuffle(pool)

    for injector in pool:
        try:
            if difficulty == "medium":
                broken, bug = injector(query, rng)
            else:
                broken, bug = injector(query, rng)

            # Verify the bug actually changed something
            if broken.strip() != query.strip():
                return broken, bug
        except Exception:
            continue

    # Fallback: keyword typo always works
    return _inject_keyword_typo(query, rng)
