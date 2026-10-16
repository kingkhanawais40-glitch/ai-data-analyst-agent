
import pandas as pd
import pytest

from backend.profiler import profile_dataframe


def test_profile_row_and_column_counts():
    dataframe = pd.DataFrame({
        "City": ["Karachi", "Lahore", "Peshawar"],
        "Consumption": [100, 200, 300],
    })

    profile = profile_dataframe(dataframe)

    assert profile["row_count"] == 3
    assert profile["column_count"] == 2
    assert len(profile["columns"]) == 2


def test_profile_duplicate_rows():
    dataframe = pd.DataFrame({
        "City": ["Karachi", "Lahore", "Karachi"],
        "Consumption": [100, 200, 100],
    })

    profile = profile_dataframe(dataframe)

    assert profile["duplicate_rows"] == 1


def test_profile_missing_values():
    dataframe = pd.DataFrame({
        "City": ["Karachi", None, "Lahore", None],
        "Consumption": [100, 200, None, 400],
    })

    profile = profile_dataframe(dataframe)

    assert profile["total_missing_values"] == 3

    city = next(
        column for column in profile["columns"]
        if column["name"] == "City"
    )
    consumption = next(
        column for column in profile["columns"]
        if column["name"] == "Consumption"
    )

    assert city["missing_values"] == 2
    assert city["missing_percentage"] == 50.0
    assert consumption["missing_values"] == 1
    assert consumption["missing_percentage"] == 25.0


def test_profile_numeric_statistics():
    dataframe = pd.DataFrame({
        "Consumption": [10, 20, 30, 40],
    })

    profile = profile_dataframe(dataframe)
    column = profile["columns"][0]

    assert column["type"] == "numeric"
    assert column["statistics"]["mean"] == 25.0
    assert column["statistics"]["median"] == 25.0
    assert column["statistics"]["minimum"] == 10.0
    assert column["statistics"]["maximum"] == 40.0
    assert column["statistics"]["standard_deviation"] == pytest.approx(
        12.9099, abs=0.0001
    )


def test_profile_numeric_column_with_missing_values():
    dataframe = pd.DataFrame({
        "Consumption": [10.0, None, 30.0],
    })

    profile = profile_dataframe(dataframe)
    column = profile["columns"][0]

    assert column["type"] == "numeric"
    assert column["statistics"]["mean"] == 20.0
    assert column["missing_values"] == 1
    assert column["unique_values"] == 2


def test_profile_all_missing_numeric_column():
    dataframe = pd.DataFrame({
        "Consumption": pd.Series([None, None], dtype="float64"),
    })

    profile = profile_dataframe(dataframe)
    column = profile["columns"][0]

    assert column["type"] == "numeric"
    assert column["statistics"] == {}
    assert column["missing_values"] == 2
    assert column["missing_percentage"] == 100.0


def test_profile_categorical_top_values():
    dataframe = pd.DataFrame({
        "City": [
            "Karachi",
            "Lahore",
            "Karachi",
            "Peshawar",
            "Karachi",
            "Lahore",
        ],
    })

    profile = profile_dataframe(dataframe)
    column = profile["columns"][0]

    assert column["type"] == "categorical"
    assert column["unique_values"] == 3
    assert column["top_values"][0] == {
        "value": "Karachi",
        "count": 3,
    }
    assert column["top_values"][1] == {
        "value": "Lahore",
        "count": 2,
    }


def test_profile_categorical_column_ignores_missing_values():
    dataframe = pd.DataFrame({
        "City": ["Karachi", None, "Karachi", "Lahore"],
    })

    profile = profile_dataframe(dataframe)
    column = profile["columns"][0]

    assert column["unique_values"] == 2
    assert column["missing_values"] == 1
    assert column["top_values"] == [
        {"value": "Karachi", "count": 2},
        {"value": "Lahore", "count": 1},
    ]


def test_profile_empty_dataframe():
    dataframe = pd.DataFrame()

    profile = profile_dataframe(dataframe)

    assert profile["row_count"] == 0
    assert profile["column_count"] == 0
    assert profile["columns"] == []
    assert profile["duplicate_rows"] == 0
    assert profile["total_missing_values"] == 0


def test_profile_empty_numeric_column():
    dataframe = pd.DataFrame({
        "Consumption": pd.Series([], dtype="float64"),
    })

    profile = profile_dataframe(dataframe)
    column = profile["columns"][0]

    assert profile["row_count"] == 0
    assert profile["column_count"] == 1
    assert column["type"] == "numeric"
    assert column["statistics"] == {}
    assert column["unique_values"] == 0