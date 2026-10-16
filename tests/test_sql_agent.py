import sqlite3

import pandas as pd
import pytest

from backend.sql_agent import (
    validate_sql,
    execute_sql,
    run_sql_agent,
)


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame(
        {
            "City": ["Peshawar", "Lahore", "Karachi"],
            "ThreeMonth_Avg_kWh_Day": [12.0, 20.0, 15.0],
            "Est_Monthly_Bill_PKR": [5000, 8000, 6500],
        }
    )


# ==========================================
# validate_sql() TESTS
# ==========================================

@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM dataset",
        " select City from dataset ",
        "SELECT COUNT(*) FROM dataset;",
        (
            "SELECT City, AVG(ThreeMonth_Avg_kWh_Day) "
            "FROM dataset GROUP BY City"
        ),
    ],
)
def test_validate_sql_accepts_select_queries(query):
    result = validate_sql(query)

    assert result["safe"] is True
    assert result["message"] == (
        "SQL query passed security validation."
    )


@pytest.mark.parametrize(
    "query",
    ["", " ", "\t", "\n"],
)
def test_validate_sql_rejects_empty_queries(query):
    result = validate_sql(query)

    assert result == {
        "safe": False,
        "message": "SQL query cannot be empty.",
    }


@pytest.mark.parametrize(
    ("keyword", "query"),
    [
        ("DROP", "SELECT * FROM dataset; DROP TABLE dataset"),
        ("DELETE", "SELECT * FROM dataset WHERE 1=1 OR DELETE=1"),
        ("UPDATE", "SELECT UPDATE FROM dataset"),
        ("INSERT", "SELECT INSERT FROM dataset"),
        ("ALTER", "SELECT ALTER FROM dataset"),
        ("TRUNCATE", "SELECT TRUNCATE FROM dataset"),
        ("REPLACE", "SELECT REPLACE FROM dataset"),
        ("ATTACH", "SELECT ATTACH FROM dataset"),
        ("DETACH", "SELECT DETACH FROM dataset"),
        ("PRAGMA", "SELECT PRAGMA FROM dataset"),
    ],
)
def test_validate_sql_rejects_forbidden_keywords(keyword, query):
    result = validate_sql(query)

    assert result["safe"] is False
    assert keyword in result["message"]


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE dataset SET City='Test'",
        "DELETE FROM dataset",
        "DROP TABLE dataset",
        "INSERT INTO dataset VALUES ('Test', 1, 2)",
        (
            "WITH records AS (SELECT * FROM dataset) "
            "SELECT * FROM records"
        ),
    ],
)
def test_validate_sql_rejects_non_select_statements(query):
    result = validate_sql(query)

    assert result["safe"] is False
    assert result["message"] == (
        "Only SELECT queries are allowed."
    )


def test_validate_sql_rejects_multiple_statements():
    result = validate_sql(
        "SELECT * FROM dataset; SELECT * FROM dataset"
    )

    assert result["safe"] is False
    assert result["message"] == (
        "Multiple SQL statements are not allowed."
    )


# ==========================================
# execute_sql() TESTS
# ==========================================

def test_execute_sql_returns_dataframe_records(sample_dataframe):
    result = execute_sql(
        sample_dataframe,
        "SELECT City FROM dataset ORDER BY City",
    )

    assert result["success"] is True
    assert result["row_count"] == 3
    assert result["columns"] == ["City"]
    assert result["results"] == [
        {"City": "Karachi"},
        {"City": "Lahore"},
        {"City": "Peshawar"},
    ]


def test_execute_sql_returns_aggregate_result(sample_dataframe):
    result = execute_sql(
        sample_dataframe,
        (
            "SELECT AVG(ThreeMonth_Avg_kWh_Day) "
            "AS average_consumption FROM dataset"
        ),
    )

    assert result["success"] is True
    assert result["row_count"] == 1
    assert result["columns"] == ["average_consumption"]
    assert result["results"][0]["average_consumption"] == pytest.approx(
        47 / 3
    )


def test_execute_sql_rejects_empty_dataframe():
    result = execute_sql(
        pd.DataFrame(),
        "SELECT * FROM dataset",
    )

    assert result == {
        "success": False,
        "message": "The dataset is empty.",
    }


def test_execute_sql_rejects_unsafe_query(sample_dataframe):
    result = execute_sql(
        sample_dataframe,
        "DELETE FROM dataset",
    )

    assert result["success"] is False
    assert result["message"] == (
        "Only SELECT queries are allowed."
    )


def test_execute_sql_reports_invalid_column(sample_dataframe):
    query = "SELECT missing_column FROM dataset"

    result = execute_sql(sample_dataframe, query)

    assert result["success"] is False
    assert result["query"] == query
    assert result["message"].startswith(
        "SQL execution failed:"
    )


def test_execute_sql_closes_database_connection_on_failure(
    sample_dataframe,
    monkeypatch,
):
    connections = []
    original_connect = sqlite3.connect

    def tracked_connect(database):
        connection = original_connect(database)
        connections.append(connection)
        return connection

    monkeypatch.setattr(
        "backend.sql_agent.sqlite3.connect",
        tracked_connect,
    )

    result = execute_sql(
        sample_dataframe,
        "SELECT missing_column FROM dataset",
    )

    assert result["success"] is False
    assert len(connections) == 1

    with pytest.raises(sqlite3.ProgrammingError):
        connections[0].execute("SELECT 1")


# ==========================================
# run_sql_agent() TESTS
# ==========================================

def test_run_sql_agent_average_consumption(sample_dataframe):
    result = run_sql_agent(
        sample_dataframe,
        "What is the average consumption?",
    )

    assert result["success"] is True
    assert result["intent"] == "average_consumption"
    assert result["row_count"] == 1
    assert result["columns"] == ["average_consumption"]
    assert result["results"][0]["average_consumption"] == pytest.approx(
        47 / 3
    )


def test_run_sql_agent_highest_consumption_city(sample_dataframe):
    result = run_sql_agent(
        sample_dataframe,
        "Which city has the highest consumption?",
    )

    assert result["success"] is True
    assert result["intent"] == "highest_consumption_city"
    assert result["results"][0]["City"] == "Lahore"


def test_run_sql_agent_lowest_consumption_city(sample_dataframe):
    result = run_sql_agent(
        sample_dataframe,
        "Which city has the lowest consumption?",
    )

    assert result["success"] is True
    assert result["intent"] == "lowest_consumption_city"
    assert result["results"][0]["City"] == "Peshawar"


def test_run_sql_agent_rejects_empty_dataframe():
    result = run_sql_agent(
        pd.DataFrame(),
        "What is the average consumption?",
    )

    assert result == {
        "success": False,
        "message": "The dataset is empty.",
    }


def test_run_sql_agent_returns_unsupported_question_error(
    sample_dataframe,
):
    question = "What is the weather tomorrow?"

    result = run_sql_agent(
        sample_dataframe,
        question,
    )

    assert result["success"] is False
    assert result["question"] == question
    assert result["message"] == (
        "I could not determine a supported SQL operation "
        "from this question yet."
    )


def test_run_sql_agent_preserves_generated_question(
    sample_dataframe,
):
    question = "What is the average monthly bill?"

    result = run_sql_agent(
        sample_dataframe,
        question,
    )

    assert result["success"] is True
    assert result["question"] == question
    assert result["intent"] == "average_monthly_bill"
    assert result["row_count"] == 1
    assert result["results"][0]["average_monthly_bill"] == pytest.approx(
        6500
    )
