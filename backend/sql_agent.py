
import re
import sqlite3
from typing import Any, Dict

import pandas as pd

from backend.sql_generator import generate_sql


FORBIDDEN_SQL_KEYWORDS = [
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
]


def _mask_sql_literals_and_comments(sql: str) -> str:
    """
    Mask SQL string literals, quoted identifiers and comments.
    Preserves character positions for reliable syntax checks.
    """
    result = list(sql)
    length = len(sql)
    i = 0

    while i < length:
        char = sql[i]

        # Single, double or backtick quoted content.
        if char in ("'", '"', "`"):
            quote = char
            result[i] = " "
            i += 1

            while i < length:
                current = sql[i]
                result[i] = " "

                if current == quote:
                    if i + 1 < length and sql[i + 1] == quote:
                        result[i + 1] = " "
                        i += 2
                        continue

                    i += 1
                    break

                if current == "\\" and i + 1 < length:
                    result[i + 1] = " "
                    i += 2
                else:
                    i += 1

            else:
                raise ValueError("Unterminated quoted SQL value.")

            continue

        # Bracket-quoted identifiers.
        if char == "[":
            result[i] = " "
            i += 1

            while i < length:
                current = sql[i]
                result[i] = " "

                if current == "]":
                    i += 1
                    break

                i += 1
            else:
                raise ValueError("Unterminated quoted SQL identifier.")

            continue

        # Single-line comments.
        if sql.startswith("--", i):
            while i < length and sql[i] not in "\r\n":
                result[i] = " "
                i += 1
            continue

        # Block comments.
        if sql.startswith("/*", i):
            result[i] = " "
            result[i + 1] = " "
            i += 2

            closed = False

            while i < length:
                if sql.startswith("*/", i):
                    result[i] = " "
                    result[i + 1] = " "
                    i += 2
                    closed = True
                    break

                result[i] = " "
                i += 1

            if not closed:
                raise ValueError("Unterminated SQL comment.")

            continue

        i += 1

    return "".join(result)


def validate_sql(sql_query: str) -> Dict[str, Any]:
    """
    Validate one read-only SELECT statement.
    Actual database operations are restricted by SQLite authorizer too.
    """
    if not isinstance(sql_query, str) or not sql_query.strip():
        return {
            "safe": False,
            "message": "SQL query cannot be empty.",
        }

    sql = sql_query.strip()

    try:
        masked_sql = _mask_sql_literals_and_comments(sql)
    except ValueError as error:
        return {
            "safe": False,
            "message": str(error),
        }

    syntax = masked_sql.strip()

    if not re.match(r"(?is)^SELECT\b", syntax):
        return {
            "safe": False,
            "message": "Only SELECT queries are allowed.",
        }

    # Detect forbidden operations before reporting multiple statements,
    # so a query containing DROP reports the unsafe operation.
    normalized_sql = re.sub(r"\s+", " ", syntax.upper()).strip()

    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized_sql):
            return {
                "safe": False,
                "message": f"Unsafe SQL operation detected: {keyword}",
            }

    # Permit one optional trailing semicolon.
    statement = syntax.rstrip()

    if statement.endswith(";"):
        statement = statement[:-1].rstrip()

    if ";" in statement:
        return {
            "safe": False,
            "message": "Multiple SQL statements are not allowed.",
        }

    if not statement:
        return {
            "safe": False,
            "message": "SQL query cannot be empty.",
        }

    return {
        "safe": True,
        "message": "SQL query passed security validation.",
    }


def _sqlite_read_only_authorizer(
    action: int,
    arg1: Any,
    arg2: Any,
    database_name: Any,
    trigger_name: Any,
) -> int:
    """
    Permit read-only SELECT queries against the dataset table.
    Deny other SQLite actions.
    """
    del database_name, trigger_name

    allowed_actions = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
    }

    recursive_action = getattr(sqlite3, "SQLITE_RECURSIVE", None)

    if recursive_action is not None:
        allowed_actions.add(recursive_action)

    if action not in allowed_actions:
        return sqlite3.SQLITE_DENY

    if action == sqlite3.SQLITE_READ:
        if arg1 != "dataset":
            return sqlite3.SQLITE_DENY

    if action == sqlite3.SQLITE_FUNCTION:
        # SQLite versions may supply the function name in either argument.
        function_name = str(arg2 or arg1 or "").lower()

        if function_name == "load_extension":
            return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


def execute_sql(
    dataframe: pd.DataFrame,
    sql_query: str,
) -> Dict[str, Any]:
    """
    Execute a validated SELECT query against a DataFrame
    using a temporary in-memory SQLite database.
    """
    validation = validate_sql(sql_query)

    if not validation["safe"]:
        return {
            "success": False,
            "message": validation["message"],
        }

    if dataframe.empty:
        return {
            "success": False,
            "message": "The dataset is empty.",
        }

    connection = sqlite3.connect(":memory:")

    try:
        dataframe.to_sql(
            "dataset",
            connection,
            index=False,
            if_exists="replace",
        )

        # Install after loading the DataFrame so setup writes can complete.
        connection.set_authorizer(_sqlite_read_only_authorizer)

        result_dataframe = pd.read_sql_query(
            sql_query,
            connection,
        )

        return {
            "success": True,
            "query": sql_query,
            "row_count": int(len(result_dataframe)),
            "columns": result_dataframe.columns.tolist(),
            "results": result_dataframe.to_dict(orient="records"),
        }

    except Exception as error:
        return {
            "success": False,
            "query": sql_query,
            "message": f"SQL execution failed: {str(error)}",
        }

    finally:
        connection.close()


def run_sql_agent(
    dataframe: pd.DataFrame,
    question: str,
) -> Dict[str, Any]:
    """
    Natural language question -> SQL generation -> validation
    -> execution -> structured result.
    """
    if dataframe.empty:
        return {
            "success": False,
            "message": "The dataset is empty.",
        }

    generated = generate_sql(question)

    if not generated.get("success"):
        return {
            "success": False,
            "question": question,
            "message": generated.get(
                "message",
                "Could not generate SQL.",
            ),
        }

    sql_query = generated["sql"]
    validation = validate_sql(sql_query)

    if not validation["safe"]:
        return {
            "success": False,
            "question": question,
            "sql": sql_query,
            "message": validation["message"],
        }

    execution = execute_sql(dataframe, sql_query)

    if not execution.get("success"):
        return {
            "success": False,
            "question": question,
            "intent": generated.get("intent"),
            "sql": sql_query,
            "message": execution.get(
                "message",
                "SQL execution failed.",
            ),
        }

    return {
        "success": True,
        "question": question,
        "intent": generated.get("intent"),
        "sql": sql_query,
        "row_count": execution["row_count"],
        "columns": execution["columns"],
        "results": execution["results"],
    }