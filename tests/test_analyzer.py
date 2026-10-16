import pandas as pd
import pytest

from backend.analyzer import (
    _normalize_text,
    _find_categorical_column,
    _find_numeric_column,
    _find_correlation_columns,
    _average_analysis,
    _sum_analysis,
    _group_average_analysis,
    _group_sum_analysis,
    _group_highest_analysis,
    _group_lowest_analysis,
    _top_analysis,
    _correlation_analysis,
    analyze_question,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "City": ["Karachi", "Lahore", "Karachi", "Peshawar"],
            "Season": ["Summer", "Winter", "Summer", "Winter"],
            "Building_Type": [
                "Residential",
                "Commercial",
                "Residential",
                "Commercial",
            ],
            "Weather_Condition": [
                "Hot",
                "Cold",
                "Hot",
                "Mild",
            ],
            "AC_Type": ["Split", "Window", "Split", "Window"],
            "Efficiency_Rating": ["A", "B", "A", "C"],
            "Iron_Used": ["Yes", "No", "Yes", "No"],
            "Temperature_C": [30.0, 20.0, 35.0, 25.0],
            "Humidity_Percent": [60.0, 40.0, 70.0, 50.0],
            "Building_Size_sqft": [1000, 2000, 1500, 2500],
            "ThreeMonth_Avg_kWh_Day": [10.0, 20.0, 30.0, 40.0],
            "Month1_kWh_Day": [8.0, 18.0, 28.0, 38.0],
            "Month2_kWh_Day": [9.0, 19.0, 29.0, 39.0],
            "Month3_kWh_Day": [13.0, 23.0, 33.0, 43.0],
            "Predicted_Next_Month_kWh_Day": [
                12.0, 22.0, 32.0, 42.0
            ],
            "Est_Monthly_Bill_PKR": [
                3000.0, 5000.0, 7000.0, 9000.0
            ],
            "AC_Power_Watt": [1000, 1500, 2000, 2500],
            "Record_ID": [1, 2, 3, 4],
        }
    )


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def test_normalize_text_lowercase():
    assert _normalize_text("HELLO WORLD") == "hello world"


def test_normalize_text_strips_whitespace():
    assert _normalize_text("  hello world  ") == "hello world"


def test_normalize_text_collapses_spaces():
    assert _normalize_text("hello    world") == "hello world"


def test_normalize_text_converts_non_string():
    assert _normalize_text(123) == "123"


# ============================================================
# CATEGORICAL COLUMN DETECTION
# ============================================================

@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is the average consumption by city?", "City"),
        ("Show electricity consumption by season", "City"),
        ("Compare consumption by building type", "Building_Type"),
        ("Show consumption by building", "Building_Type"),
        ("Compare usage by weather", "Weather_Condition"),
        ("Show usage by AC type", "AC_Type"),
        ("Compare consumption by efficiency rating", "Efficiency_Rating"),
        ("Show consumption by iron", "Iron_Used"),
    ],
)
def test_find_categorical_column_supported_questions(
    sample_df, question, expected
):
    assert _find_categorical_column(sample_df, question) == expected


@pytest.mark.parametrize(
    "question",
    [
        "What is the average consumption?",
        "Show me the cities",
        "What is the total electricity bill?",
        "Which city has the highest consumption?",
    ],
)
def test_find_categorical_column_requires_grouping_phrase(
    sample_df, question
):
    assert _find_categorical_column(sample_df, question) is None


def test_find_categorical_column_missing_column():
    dataframe = pd.DataFrame({"Temperature_C": [20, 30]})

    assert (
        _find_categorical_column(
            dataframe,
            "Show consumption by city",
        )
        is None
    )


# ============================================================
# NUMERIC COLUMN DETECTION
# ============================================================

@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is the monthly bill?", "Est_Monthly_Bill_PKR"),
        (
            "What is the average electricity consumption?",
            "ThreeMonth_Avg_kWh_Day",
        ),
        (
            "Show predicted consumption",
            "Predicted_Next_Month_kWh_Day",
        ),
        ("What is the consumption in month 1?", "Month1_kWh_Day"),
        ("What is the consumption in month 2?", "Month2_kWh_Day"),
        ("What is the consumption in month 3?", "Month3_kWh_Day"),
        ("What is the temperature?", "Temperature_C"),
        ("What is the humidity?", "Humidity_Percent"),
        ("What is the building size?", "Building_Size_sqft"),
    ],
)
def test_find_numeric_column_supported_questions(
    sample_df, question, expected
):
    assert _find_numeric_column(sample_df, question) == expected


def test_find_numeric_column_fallback():
    dataframe = pd.DataFrame(
        {
            "Record_ID": [1, 2],
            "Custom_Value": [10, 20],
        }
    )

    assert _find_numeric_column(dataframe, "Explain the data") == "Custom_Value"


def test_find_numeric_column_excludes_record_id():
    dataframe = pd.DataFrame({"Record_ID": [1, 2]})

    assert _find_numeric_column(dataframe, "Explain the data") is None


def test_find_numeric_column_no_numeric_data():
    dataframe = pd.DataFrame({"City": ["Karachi", "Lahore"]})

    assert _find_numeric_column(dataframe, "Explain the data") is None


# ============================================================
# CORRELATION COLUMN DETECTION
# ============================================================

def test_find_correlation_columns_temperature_and_humidity(sample_df):
    result = _find_correlation_columns(
        sample_df,
        "Show correlation between temperature and humidity",
    )

    assert result == ["Temperature_C", "Humidity_Percent"]


def test_find_correlation_columns_temperature_and_consumption(sample_df):
    result = _find_correlation_columns(
        sample_df,
        "Show correlation between temperature and electricity consumption",
    )

    assert result == [
        "Temperature_C",
        "ThreeMonth_Avg_kWh_Day",
    ]


def test_find_correlation_columns_returns_empty_for_one_column(sample_df):
    result = _find_correlation_columns(
        sample_df,
        "Show correlation between temperature and weather",
    )

    assert result == []


def test_find_correlation_columns_returns_empty_for_no_columns(sample_df):
    result = _find_correlation_columns(
        sample_df,
        "Show correlation between unknown factors",
    )

    assert result == []


def test_find_correlation_columns_ignores_missing_columns():
    dataframe = pd.DataFrame({"Temperature_C": [20, 30]})

    result = _find_correlation_columns(
        dataframe,
        "Show correlation between temperature and humidity",
    )

    assert result == []


# ============================================================
# AVERAGE ANALYSIS
# ============================================================

def test_average_analysis_success(sample_df):
    result = _average_analysis(
        sample_df,
        "Temperature_C",
    )

    assert result["success"] is True
    assert result["operation"] == "average"
    assert result["column"] == "Temperature_C"
    assert result["result"] == 27.5
    assert result["count"] == 4
    assert result["minimum"] == 20.0
    assert result["maximum"] == 35.0


def test_average_analysis_missing_column(sample_df):
    result = _average_analysis(sample_df, "Missing_Column")

    assert result["success"] is False
    assert "was not found" in result["message"]


def test_average_analysis_non_numeric_values():
    dataframe = pd.DataFrame({"Value": ["bad", "invalid"]})

    result = _average_analysis(dataframe, "Value")

    assert result["success"] is False
    assert "No numeric data" in result["message"]


def test_average_analysis_ignores_invalid_values():
    dataframe = pd.DataFrame({"Value": [10, "bad", 20, None]})

    result = _average_analysis(dataframe, "Value")

    assert result["success"] is True
    assert result["result"] == 15.0
    assert result["count"] == 2


# ============================================================
# SUM ANALYSIS
# ============================================================

def test_sum_analysis_success(sample_df):
    result = _sum_analysis(sample_df, "Temperature_C")

    assert result["success"] is True
    assert result["operation"] == "sum"
    assert result["column"] == "Temperature_C"
    assert result["result"] == 110.0
    assert result["count"] == 4


def test_sum_analysis_missing_column(sample_df):
    result = _sum_analysis(sample_df, "Missing_Column")

    assert result["success"] is False
    assert "was not found" in result["message"]


def test_sum_analysis_non_numeric_values():
    dataframe = pd.DataFrame({"Value": ["bad", "invalid"]})

    result = _sum_analysis(dataframe, "Value")

    assert result["success"] is False
    assert "No numeric data" in result["message"]


def test_sum_analysis_ignores_invalid_values():
    dataframe = pd.DataFrame({"Value": [10, "bad", 20, None]})

    result = _sum_analysis(dataframe, "Value")

    assert result["success"] is True
    assert result["result"] == 30.0
    assert result["count"] == 2


# ============================================================
# GROUP AVERAGE ANALYSIS
# ============================================================

def test_group_average_analysis_success(sample_df):
    result = _group_average_analysis(
        sample_df,
        "City",
        "Temperature_C",
    )

    assert result["success"] is True
    assert result["operation"] == "group_average"
    assert result["group_by"] == "City"
    assert result["column"] == "Temperature_C"

    groups = {item["group"]: item for item in result["result"]}

    assert groups["Karachi"]["average"] == 32.5
    assert groups["Karachi"]["count"] == 2
    assert groups["Peshawar"]["average"] == 25.0
    assert groups["Lahore"]["average"] == 20.0


def test_group_average_analysis_missing_group_column(sample_df):
    result = _group_average_analysis(
        sample_df,
        "Missing_Group",
        "Temperature_C",
    )

    assert result["success"] is False
    assert "Grouping column" in result["message"]


def test_group_average_analysis_missing_value_column(sample_df):
    result = _group_average_analysis(
        sample_df,
        "City",
        "Missing_Value",
    )

    assert result["success"] is False
    assert "Column" in result["message"]


def test_group_average_analysis_no_valid_data():
    dataframe = pd.DataFrame(
        {
            "City": [None, None],
            "Value": ["bad", "invalid"],
        }
    )

    result = _group_average_analysis(dataframe, "City", "Value")

    assert result["success"] is False


# ============================================================
# GROUP SUM ANALYSIS
# ============================================================

def test_group_sum_analysis_success(sample_df):
    result = _group_sum_analysis(
        sample_df,
        "City",
        "Temperature_C",
    )

    assert result["success"] is True
    assert result["operation"] == "group_sum"

    groups = {item["group"]: item for item in result["result"]}

    assert groups["Karachi"]["total"] == 65.0
    assert groups["Karachi"]["count"] == 2
    assert groups["Peshawar"]["total"] == 25.0


def test_group_sum_analysis_missing_group_column(sample_df):
    result = _group_sum_analysis(
        sample_df,
        "Missing_Group",
        "Temperature_C",
    )

    assert result["success"] is False


def test_group_sum_analysis_missing_value_column(sample_df):
    result = _group_sum_analysis(
        sample_df,
        "City",
        "Missing_Value",
    )

    assert result["success"] is False


def test_group_sum_analysis_no_valid_data():
    dataframe = pd.DataFrame(
        {
            "City": [None, None],
            "Value": ["bad", "invalid"],
        }
    )

    result = _group_sum_analysis(dataframe, "City", "Value")

    assert result["success"] is False


# ============================================================
# GROUP HIGHEST ANALYSIS
# ============================================================

def test_group_highest_analysis_success(sample_df):
    result = _group_highest_analysis(
        sample_df,
        "City",
        "Temperature_C",
    )

    assert result["success"] is True
    assert result["operation"] == "group_highest"
    assert result["result"]["group"] == "Karachi"
    assert result["result"]["average"] == 32.5
    assert result["result"]["count"] == 2


def test_group_highest_analysis_missing_group(sample_df):
    result = _group_highest_analysis(
        sample_df,
        "Missing_Group",
        "Temperature_C",
    )

    assert result["success"] is False


def test_group_highest_analysis_missing_value(sample_df):
    result = _group_highest_analysis(
        sample_df,
        "City",
        "Missing_Value",
    )

    assert result["success"] is False


def test_group_highest_analysis_no_valid_data():
    dataframe = pd.DataFrame(
        {
            "City": [None, None],
            "Value": ["bad", "invalid"],
        }
    )

    result = _group_highest_analysis(dataframe, "City", "Value")

    assert result["success"] is False


# ============================================================
# GROUP LOWEST ANALYSIS
# ============================================================

def test_group_lowest_analysis_success(sample_df):
    result = _group_lowest_analysis(
        sample_df,
        "City",
        "Temperature_C",
    )

    assert result["success"] is True
    assert result["operation"] == "group_lowest"
    assert result["result"]["group"] == "Lahore"
    assert result["result"]["average"] == 20.0
    assert result["result"]["count"] == 1


def test_group_lowest_analysis_missing_group(sample_df):
    result = _group_lowest_analysis(
        sample_df,
        "Missing_Group",
        "Temperature_C",
    )

    assert result["success"] is False


def test_group_lowest_analysis_missing_value(sample_df):
    result = _group_lowest_analysis(
        sample_df,
        "City",
        "Missing_Value",
    )

    assert result["success"] is False


def test_group_lowest_analysis_no_valid_data():
    dataframe = pd.DataFrame(
        {
            "City": [None, None],
            "Value": ["bad", "invalid"],
        }
    )

    result = _group_lowest_analysis(dataframe, "City", "Value")

    assert result["success"] is False


# ============================================================
# TOP ANALYSIS
# ============================================================

def test_top_analysis_success(sample_df):
    result = _top_analysis(
        sample_df,
        "Temperature_C",
        limit=2,
    )

    assert result["success"] is True
    assert result["operation"] == "top"
    assert result["column"] == "Temperature_C"
    assert result["result"] == [
        {"rank": 1, "value": 35.0},
        {"rank": 2, "value": 30.0},
    ]


def test_top_analysis_missing_column(sample_df):
    result = _top_analysis(sample_df, "Missing_Column")

    assert result["success"] is False


def test_top_analysis_non_numeric_data():
    dataframe = pd.DataFrame({"Value": ["bad", "invalid"]})

    result = _top_analysis(dataframe, "Value")

    assert result["success"] is False


def test_top_analysis_limit(sample_df):
    result = _top_analysis(
        sample_df,
        "Temperature_C",
        limit=1,
    )

    assert len(result["result"]) == 1
    assert result["result"][0]["value"] == 35.0


# ============================================================
# CORRELATION ANALYSIS
# ============================================================

def test_correlation_analysis_success(sample_df):
    result = _correlation_analysis(
        sample_df,
        ["Temperature_C", "Humidity_Percent"],
    )

    assert result["success"] is True
    assert result["operation"] == "correlation"
    assert result["columns"] == [
        "Temperature_C",
        "Humidity_Percent",
    ]
    assert result["result"] == 1.0
    assert result["count"] == 4


def test_correlation_analysis_requires_two_columns(sample_df):
    result = _correlation_analysis(
        sample_df,
        ["Temperature_C"],
    )

    assert result["success"] is False
    assert "exactly two" in result["message"]


def test_correlation_analysis_rejects_three_columns(sample_df):
    result = _correlation_analysis(
        sample_df,
        [
            "Temperature_C",
            "Humidity_Percent",
            "Building_Size_sqft",
        ],
    )

    assert result["success"] is False


def test_correlation_analysis_missing_first_column(sample_df):
    result = _correlation_analysis(
        sample_df,
        ["Missing_Column", "Humidity_Percent"],
    )

    assert result["success"] is False


def test_correlation_analysis_missing_second_column(sample_df):
    result = _correlation_analysis(
        sample_df,
        ["Temperature_C", "Missing_Column"],
    )

    assert result["success"] is False


def test_correlation_analysis_insufficient_valid_data():
    dataframe = pd.DataFrame(
        {
            "A": [10, None, None],
            "B": [20, 30, None],
        }
    )

    result = _correlation_analysis(dataframe, ["A", "B"])

    assert result["success"] is False
    assert "Not enough valid data" in result["message"]


def test_correlation_analysis_constant_column():
    dataframe = pd.DataFrame(
        {
            "A": [5, 5, 5],
            "B": [10, 20, 30],
        }
    )

    result = _correlation_analysis(dataframe, ["A", "B"])

    assert result["success"] is False
    assert "could not be calculated" in result["message"]


def test_correlation_analysis_ignores_invalid_values():
    dataframe = pd.DataFrame(
        {
            "A": [1, 2, "bad", 4],
            "B": [2, 4, 6, 8],
        }
    )

    result = _correlation_analysis(dataframe, ["A", "B"])

    assert result["success"] is True
    assert result["count"] == 3
    assert result["result"] == 1.0


# ============================================================
# COMPLETE QUESTION ANALYSIS
# ============================================================

def test_analyze_question_average(sample_df):
    result = analyze_question(
        sample_df,
        "What is the average temperature?",
    )

    assert result["success"] is True
    assert result["analysis"]["success"] is True
    assert result["analysis"]["operation"] == "average"
    assert result["analysis"]["result"] == 27.5


def test_analyze_question_total_bill(sample_df):
    result = analyze_question(
        sample_df,
        "What is the total monthly bill?",
    )

    assert result["success"] is True
    assert result["analysis"]["operation"] == "sum"
    assert result["analysis"]["result"] == 24000.0


def test_analyze_question_highest_temperature(sample_df):
    result = analyze_question(
        sample_df,
        "What is the highest temperature?",
    )

    assert result["success"] is True
    assert result["analysis"]["operation"] == "highest"
    assert result["analysis"]["result"] == 35.0


def test_analyze_question_lowest_temperature(sample_df):
    result = analyze_question(
        sample_df,
        "What is the lowest temperature?",
    )

    assert result["success"] is True
    assert result["analysis"]["operation"] == "lowest"
    assert result["analysis"]["result"] == 20.0


def test_analyze_question_average_by_city(sample_df):
    result = analyze_question(
        sample_df,
        "What is the average temperature by city?",
    )

    assert result["success"] is True
    assert result["analysis"]["operation"] == "group_average"
    assert result["analysis"]["group_by"] == "City"


def test_analyze_question_highest_by_city(sample_df):
    result = analyze_question(
        sample_df,
        "Which city has the highest temperature by city?",
    )

    assert result["success"] is True
    assert result["analysis"]["operation"] == "group_highest"
    assert result["analysis"]["result"]["group"] == "Karachi"


def test_analyze_question_lowest_by_city(sample_df):
    result = analyze_question(
        sample_df,
        "Which city has the lowest temperature by city?",
    )

    assert result["success"] is True
    assert result["analysis"]["operation"] == "group_lowest"
    assert result["analysis"]["result"]["group"] == "Lahore"


def test_analyze_question_total_by_city(sample_df):
    result = analyze_question(
        sample_df,
        "What is the total temperature by city?",
    )

    assert result["success"] is True
    assert result["analysis"]["operation"] == "group_sum"


def test_analyze_question_correlation(sample_df):
    result = analyze_question(
        sample_df,
        "Show correlation between temperature and humidity",
    )

    assert result["success"] is True
    assert result["analysis"]["success"] is True
    assert result["analysis"]["operation"] == "correlation"
    assert result["analysis"]["result"] == 1.0


@pytest.mark.parametrize(
    "question",
    [
        "What will happen next month?",
        "Predict electricity consumption",
        "Give me a forecast for next year",
        "What is the future consumption?",
    ],
)
def test_analyze_question_rejects_unsupported_predictions(
    sample_df, question
):
    result = analyze_question(sample_df, question)

    assert result["success"] is False
    assert "message" in result


def test_analyze_question_unsupported_question(sample_df):
    result = analyze_question(
        sample_df,
        "Tell me a story about the weather",
    )

    assert result["success"] is False
    assert "message" in result


def test_analyze_question_preserves_original_question(sample_df):
    question = "What is the average temperature?"

    result = analyze_question(sample_df, question)

    assert result["question"] == question