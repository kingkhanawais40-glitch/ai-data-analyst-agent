import pytest

from backend.sql_generator import generate_sql, _normalize_question


@pytest.mark.parametrize(
    ("question", "expected_intent"),
    [
        ("What is the average consumption by city?", "average_consumption_by_city"),
        ("Show total consumption by city", "total_consumption_by_city"),
        ("Calculate sum consumption for each city", "total_consumption_by_city"),
        ("What is the average monthly bill?", "average_monthly_bill"),
        ("What is the average electricity bill?", "average_monthly_bill"),
        ("Which city has the highest consumption?", "highest_consumption_city"),
        ("Which city has the maximum consumption?", "highest_consumption_city"),
        ("Which city has the lowest consumption?", "lowest_consumption_city"),
        ("Which city has the minimum consumption?", "lowest_consumption_city"),
        ("What is the average consumption?", "average_consumption"),
    ],
)
def test_supported_questions_return_expected_intent(question, expected_intent):
    result = generate_sql(question)

    assert result["success"] is True
    assert result["intent"] == expected_intent
    assert isinstance(result["sql"], str)
    assert result["sql"].strip()
    assert "FROM dataset" in result["sql"]


@pytest.mark.parametrize("question", ["", " ", "\t", "\n", "   \t\n   "])
def test_empty_or_whitespace_question_is_rejected(question):
    result = generate_sql(question)

    assert result == {
        "success": False,
        "message": "Question cannot be empty.",
    }


def test_normalize_question_trims_and_collapses_whitespace():
    result = _normalize_question(
        "  WHAT   is \n the   AVERAGE   consumption?  "
    )

    assert result == "what is the average consumption?"


def test_average_consumption_by_city_sql():
    result = generate_sql("What is the average consumption by city?")

    assert result["success"] is True
    assert result["intent"] == "average_consumption_by_city"
    assert "AVG(ThreeMonth_Avg_kWh_Day)" in result["sql"]
    assert "GROUP BY City" in result["sql"]
    assert "ORDER BY avg_consumption DESC" in result["sql"]


def test_total_consumption_by_city_sql():
    result = generate_sql("Show total consumption by city")

    assert result["success"] is True
    assert result["intent"] == "total_consumption_by_city"
    assert "SUM(ThreeMonth_Avg_kWh_Day)" in result["sql"]
    assert "GROUP BY City" in result["sql"]
    assert "ORDER BY total_consumption DESC" in result["sql"]


def test_average_monthly_bill_sql():
    result = generate_sql("What is the average monthly bill?")

    assert result["success"] is True
    assert result["intent"] == "average_monthly_bill"
    assert "AVG(Est_Monthly_Bill_PKR)" in result["sql"]
    assert "FROM dataset" in result["sql"]


def test_highest_consumption_city_sql():
    result = generate_sql("Which city has the highest consumption?")

    assert result["success"] is True
    assert result["intent"] == "highest_consumption_city"
    assert "ORDER BY avg_consumption DESC" in result["sql"]
    assert "LIMIT 1" in result["sql"]


def test_lowest_consumption_city_sql():
    result = generate_sql("Which city has the lowest consumption?")

    assert result["success"] is True
    assert result["intent"] == "lowest_consumption_city"
    assert "ORDER BY avg_consumption ASC" in result["sql"]
    assert "LIMIT 1" in result["sql"]


def test_average_consumption_sql():
    result = generate_sql("What is the average consumption?")

    assert result["success"] is True
    assert result["intent"] == "average_consumption"
    assert "AVG(ThreeMonth_Avg_kWh_Day) AS average_consumption" in result["sql"]


@pytest.mark.parametrize(
    "question",
    [
        "Show me the weather forecast",
        "How many customers are there?",
        "List all available columns",
        "What is the population of Pakistan?",
    ],
)
def test_unsupported_questions_return_clear_error(question):
    result = generate_sql(question)

    assert result["success"] is False
    assert result["message"] == (
        "I could not determine a supported SQL operation "
        "from this question yet."
    )


def test_question_matching_is_case_insensitive():
    result = generate_sql("WHAT IS THE AVERAGE CONSUMPTION BY CITY?")

    assert result["success"] is True
    assert result["intent"] == "average_consumption_by_city"


def test_question_matching_handles_extra_whitespace():
    result = generate_sql(
        "  What   is the   average consumption   by city?  "
    )

    assert result["success"] is True
    assert result["intent"] == "average_consumption_by_city"


def test_generated_queries_are_select_queries():
    questions = [
        "What is the average consumption by city?",
        "Show total consumption by city",
        "What is the average monthly bill?",
        "Which city has the highest consumption?",
        "Which city has the lowest consumption?",
        "What is the average consumption?",
    ]

    for question in questions:
        result = generate_sql(question)

        assert result["success"] is True
        assert result["sql"].lstrip().upper().startswith("SELECT")
        assert "INSERT " not in result["sql"].upper()
        assert "UPDATE " not in result["sql"].upper()
        assert "DELETE " not in result["sql"].upper()
