import pandas as pd
import pytest

from backend import visualization_agent as agent


# ============================================================
# RECOMMEND CHART TESTS
# ============================================================

def test_recommend_chart_returns_bar_for_two_columns():
    columns = ["City", "consumption"]
    results = [
        {"City": "Karachi", "consumption": 120.5},
        {"City": "Lahore", "consumption": 95.0},
    ]

    result = agent.recommend_chart(columns, results)

    assert result["success"] is True
    assert result["chart_type"] == "bar"
    assert result["x_axis"] == "City"
    assert result["y_axis"] == "consumption"


def test_recommend_chart_returns_indicator_for_one_column():
    columns = ["average_consumption"]
    results = [{"average_consumption": 120.5}]

    result = agent.recommend_chart(columns, results)

    assert result["success"] is True
    assert result["chart_type"] == "indicator"


def test_recommend_chart_returns_table_for_multiple_columns():
    columns = ["City", "consumption", "category"]
    results = [
        {
            "City": "Karachi",
            "consumption": 120.5,
            "category": "Residential",
        }
    ]

    result = agent.recommend_chart(columns, results)

    assert result["success"] is True
    assert result["chart_type"] == "table"


@pytest.mark.parametrize(
    ("columns", "results"),
    [
        ([], [{"value": 10}]),
        (["value"], []),
    ],
)
def test_recommend_chart_rejects_empty_input(columns, results):
    result = agent.recommend_chart(columns, results)

    assert result["success"] is False
    assert "No result data" in result["message"]


# ============================================================
# ANALYSIS PIPELINE TESTS
# ============================================================

def test_analyze_and_visualize_returns_sql_failure(monkeypatch):
    monkeypatch.setattr(
        agent,
        "run_sql_agent",
        lambda dataframe, question: {
            "success": False,
            "message": "Unsupported question.",
        },
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    result = agent.analyze_and_visualize(
        dataframe,
        "Unsupported question",
    )

    assert result["success"] is False
    assert result["message"] == "Unsupported question."


def test_analyze_and_visualize_returns_indicator_without_chart(
    monkeypatch,
):
    monkeypatch.setattr(
        agent,
        "run_sql_agent",
        lambda dataframe, question: {
            "success": True,
            "columns": ["average_consumption"],
            "results": [{"average_consumption": 120.5}],
        },
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    result = agent.analyze_and_visualize(
        dataframe,
        "What is the average consumption?",
    )

    assert result["success"] is True
    assert result["visualization"]["chart_type"] == "indicator"
    assert result["chart"] is None


def test_analyze_and_visualize_generates_chart(monkeypatch):
    monkeypatch.setattr(
        agent,
        "run_sql_agent",
        lambda dataframe, question: {
            "success": True,
            "columns": ["City", "consumption"],
            "results": [
                {"City": "Karachi", "consumption": 120},
                {"City": "Lahore", "consumption": 95},
            ],
        },
    )

    monkeypatch.setattr(
        agent,
        "generate_chart",
        lambda chart_type, columns, results, title: {
            "success": True,
            "chart_type": chart_type,
            "title": title,
        },
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    result = agent.analyze_and_visualize(
        dataframe,
        "Show consumption by city",
    )

    assert result["success"] is True
    assert result["visualization"]["chart_type"] == "bar"
    assert result["chart"]["success"] is True


def test_analyze_and_visualize_returns_chart_generation_failure(
    monkeypatch,
):
    monkeypatch.setattr(
        agent,
        "run_sql_agent",
        lambda dataframe, question: {
            "success": True,
            "columns": ["City", "consumption"],
            "results": [
                {"City": "Karachi", "consumption": 120},
                {"City": "Lahore", "consumption": 95},
            ],
        },
    )

    monkeypatch.setattr(
        agent,
        "generate_chart",
        lambda **kwargs: {
            "success": False,
            "message": "Chart generation failed.",
        },
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    result = agent.analyze_and_visualize(
        dataframe,
        "Show consumption by city",
    )

    assert result["success"] is False
    assert result["message"] == "Chart generation failed."


def test_analyze_and_visualize_rejects_empty_dataframe():
    dataframe = pd.DataFrame()

    result = agent.analyze_and_visualize(
        dataframe,
        "Show consumption",
    )

    assert result["success"] is False
    assert result["message"] == "The dataset is empty."
