
import pandas as pd
import pytest

from backend.validator import validate_dataframe


def get_column(result, name):
    return next(
        column
        for column in result["columns"]
        if column["column"] == name
    )


def get_flag(column, flag_type):
    return next(
        flag
        for flag in column["flags"]
        if flag["type"] == flag_type
    )


def test_empty_dataframe():
    result = validate_dataframe(pd.DataFrame())

    assert result["dataset"] == {"rows": 0, "columns": 0}
    assert result["summary"]["duplicate_rows"] == 0
    assert result["summary"]["total_missing_values"] == 0
    assert result["summary"]["quality_score"] == 100.0
    assert result["summary"]["quality_label"] == "Excellent"
    assert result["columns"] == []
    assert result["dataset_issues"] == []
    assert result["dataset_warnings"] == []


def test_clean_dataframe():
    dataframe = pd.DataFrame({
        "consumption": [100, 120, 140, 160, 180, 200],
        "temperature": [20, 21, 22, 23, 24, 25],
    })

    result = validate_dataframe(dataframe)

    assert result["dataset"] == {"rows": 6, "columns": 2}
    assert result["summary"]["duplicate_rows"] == 0
    assert result["summary"]["total_missing_values"] == 0
    assert result["summary"]["flagged_columns"] == 0
    assert result["summary"]["quality_score"] == 100.0
    assert result["summary"]["quality_label"] == "Excellent"


def test_duplicate_rows_are_reported():
    dataframe = pd.DataFrame({
        "City": ["Karachi", "Lahore", "Karachi"],
        "consumption": [100, 200, 100],
    })

    result = validate_dataframe(dataframe)

    assert result["summary"]["duplicate_rows"] == 1
    assert result["dataset_issues"][0] == {
        "type": "duplicate_rows",
        "severity": "high",
        "message": "1 duplicate rows detected.",
        "count": 1,
    }


def test_missing_values_are_reported_at_dataset_and_column_level():
    dataframe = pd.DataFrame({
        "consumption": [100.0, None, 300.0, None],
        "temperature": [20.0, 21.0, None, 23.0],
    })

    result = validate_dataframe(dataframe)

    assert result["summary"]["total_missing_values"] == 3
    assert result["dataset_warnings"][0]["type"] == "missing_values"
    assert result["dataset_warnings"][0]["count"] == 3

    consumption = get_column(result, "consumption")
    assert consumption["missing_values"] == 2
    assert consumption["missing_percentage"] == 50.0
    assert get_flag(consumption, "missing_values")["severity"] == "high"

    temperature = get_column(result, "temperature")
    assert temperature["missing_values"] == 1
    assert temperature["missing_percentage"] == 25.0
    assert get_flag(temperature, "missing_values")["severity"] == "medium"


@pytest.mark.parametrize(
    ("values", "expected_severity"),
    [
        ([1, None, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "low"),
        ([1, None, None, 4, 5, 6, 7, 8, 9, 10], "medium"),
        ([None, None, None, None, None, 6, 7, 8, 9, 10], "high"),
    ],
)
def test_missing_value_severity_thresholds(values, expected_severity):
    result = validate_dataframe(pd.DataFrame({"value": values}))
    column = get_column(result, "value")

    assert get_flag(column, "missing_values")["severity"] == expected_severity


def test_identifier_column_is_flagged():
    dataframe = pd.DataFrame({
        "customer_id": [101, 102, 103, 104],
        "consumption": [100, 200, 300, 400],
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "customer_id")
    flag = get_flag(column, "identifier_column")

    assert flag["severity"] == "info"
    assert "identifier" in flag["message"].lower()


def test_constant_column_is_flagged():
    dataframe = pd.DataFrame({
        "constant_value": [5, 5, 5, 5],
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "constant_value")

    assert get_flag(column, "constant_column")["severity"] == "high"
    assert result["summary"]["high_severity_flags"] >= 1


def test_all_missing_column_is_flagged_as_constant():
    dataframe = pd.DataFrame({
        "empty_column": [None, None, None],
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "empty_column")

    assert column["unique_values"] == 0
    assert get_flag(column, "constant_column")["severity"] == "high"


def test_high_cardinality_text_column_is_flagged():
    dataframe = pd.DataFrame({
        "customer_name": [f"customer_{i}" for i in range(10)],
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "customer_name")
    flag = get_flag(column, "high_cardinality")

    assert flag["severity"] == "medium"
    assert "100.00%" in flag["message"]


def test_numeric_column_with_infinite_values_is_flagged():
    dataframe = pd.DataFrame({
        "measurement": [1.0, 2.0, float("inf"), float("-inf"), 3.0, 4.0],
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "measurement")
    flag = get_flag(column, "infinite_values")

    assert flag["severity"] == "high"
    assert "2 infinite values" in flag["message"]


def test_negative_numeric_values_are_flagged():
    dataframe = pd.DataFrame({
        "consumption": [-10, 10, 20, 30, 40, 50],
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "consumption")
    flag = get_flag(column, "negative_values")

    assert flag["severity"] == "medium"
    assert "1 negative values" in flag["message"]


def test_iqr_outliers_are_reported():
    dataframe = pd.DataFrame({
        "measurement": list(range(1, 21)) + [1000],
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "measurement")

    assert column["outliers"]["count"] == 1
    assert column["outliers"]["percentage"] == pytest.approx(4.76)
    assert column["outliers"]["lower_bound"] < column["outliers"]["upper_bound"]

    # Outlier flag is only added when outlier percentage reaches 10%.
    assert not any(
        flag["type"] == "outliers"
        for flag in column["flags"]
    )


def test_high_outlier_percentage_adds_outlier_flag():
    # 10 outliers among 100 valid numeric values = 10%.
    dataframe = pd.DataFrame({
        "measurement": list(range(1, 91)) + [1000] * 10,
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "measurement")

    assert column["outliers"]["count"] == 10
    assert column["outliers"]["percentage"] == 10.0
    assert get_flag(column, "outliers")["severity"] == "medium"


def test_numeric_column_with_no_valid_values_does_not_crash():
    dataframe = pd.DataFrame({
        "measurement": pd.Series([None, None, None], dtype="float64"),
    })

    result = validate_dataframe(dataframe)
    column = get_column(result, "measurement")

    assert result["summary"]["total_missing_values"] == 3
    assert column["data_type"] == "float64"
    assert column["missing_values"] == 3
    assert "outliers" not in column


def test_original_dataframe_is_not_modified():
    dataframe = pd.DataFrame({
        "measurement": [10.0, None, -5.0, 20.0],
        "City": ["Karachi", "Lahore", "Peshawar", "Quetta"],
    })
    original = dataframe.copy(deep=True)

    validate_dataframe(dataframe)

    pd.testing.assert_frame_equal(dataframe, original)


@pytest.mark.parametrize(
    ("values", "expected_label"),
    [
        ([1, 2, 3, 4], "Excellent"),
        ([1, 2, 3, None], "Fair"),
        ([None, None, 3, 4], "Poor"),
    ],
)
def test_quality_score_labels(values, expected_label):
    result = validate_dataframe(pd.DataFrame({"value": values}))

    assert result["summary"]["quality_label"] == expected_label


def test_summary_severity_counts_match_column_flags():
    dataframe = pd.DataFrame({
        "constant_a": [1, 1, 1, 1],
        "constant_b": [2, 2, 2, 2],
        "value": [1, None, 3, 4],
    })

    result = validate_dataframe(dataframe)

    all_flags = [
        flag
        for column in result["columns"]
        for flag in column["flags"]
    ]

    assert result["summary"]["high_severity_flags"] == sum(
        flag["severity"] == "high" for flag in all_flags
    )
    assert result["summary"]["medium_severity_flags"] == sum(
        flag["severity"] == "medium" for flag in all_flags
    )
    assert result["summary"]["low_severity_flags"] == sum(
        flag["severity"] == "low" for flag in all_flags
    )
    assert result["summary"]["flagged_columns"] == sum(
        bool(column["flags"]) for column in result["columns"]
    )


def test_quality_score_stays_within_zero_and_one_hundred():
    dataframe = pd.DataFrame({
        "value": [None] * 20,
        "constant": [1] * 20,
    })

    result = validate_dataframe(dataframe)
    score = result["summary"]["quality_score"]

    assert 0 <= score <= 100


def test_validator_returns_explicit_success_status():
    dataframe = pd.DataFrame({
        "city": ["Peshawar", "Lahore", "Karachi"],
        "usage": [120, 150, 180],
    })

    result = validate_dataframe(dataframe)

    assert result["success"] is True
    assert result["dataset"] == {"rows": 3, "columns": 2}
    assert "summary" in result
    assert "columns" in result
