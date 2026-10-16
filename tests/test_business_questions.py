
import pandas as pd
import pytest

from backend.business_questions import answer_business_question


@pytest.fixture
def sample_df():
    """Create a small, predictable dataset for unit tests."""
    return pd.DataFrame(
        {
            "City": [
                "Karachi",
                "Lahore",
                "Quetta",
                "Karachi",
            ],
            "AC_Type": [
                "Inverter",
                "Conventional",
                "Inverter",
                "Conventional",
            ],
            "Month1_kWh_Day": [50.0, 40.0, 20.0, 60.0],
            "Month2_kWh_Day": [55.0, 45.0, 25.0, 65.0],
            "Month3_kWh_Day": [60.0, 50.0, 30.0, 70.0],
        }
    )


def run_question(df, question):
    """Run a question against the business questions engine."""
    return answer_business_question(df, question)


def test_empty_question(sample_df):
    result = run_question(sample_df, "")

    assert result["success"] is False


def test_unsupported_question(sample_df):
    result = run_question(
        sample_df,
        "Who is the CEO of this company?",
    )

    assert result["success"] is False
    assert "supported_analysis" in result


def test_highest_consumption_by_city(sample_df):
    result = run_question(
        sample_df,
        "Which city has the highest power consumption?",
    )

    assert result["success"] is True
    assert result["analysis"]["analysis_type"] == "grouped_average"
    assert result["analysis"]["group_column"] == "City"
    assert result["analysis"]["result"] == "Karachi"
    assert result["analysis"]["value"] == pytest.approx(60.0)
    assert "Karachi" in result["answer"]


def test_lowest_consumption_by_city(sample_df):
    result = run_question(
        sample_df,
        "Which city has the lowest power consumption?",
    )

    assert result["success"] is True
    assert result["analysis"]["analysis_type"] == "grouped_average_minimum"
    assert result["analysis"]["group_column"] == "City"
    assert result["analysis"]["result"] == "Quetta"
    assert result["analysis"]["value"] == pytest.approx(25.0)
    assert "Quetta" in result["answer"]


def test_highest_consumption_by_ac_type(sample_df):
    result = run_question(
        sample_df,
        "Which AC_Type has the highest power consumption?",
    )

    assert result["success"] is True
    assert result["analysis"]["group_column"] == "AC_Type"
    assert result["analysis"]["result"] == "Conventional"
    assert "Conventional" in result["answer"]


def test_lowest_consumption_by_ac_type(sample_df):
    result = run_question(
        sample_df,
        "Which AC_Type has the lowest power consumption?",
    )

    assert result["success"] is True
    assert result["analysis"]["group_column"] == "AC_Type"
    assert result["analysis"]["result"] == "Inverter"
    assert "Inverter" in result["answer"]



def test_average_consumption(sample_df):
    result = run_question(
        sample_df,
        "What is the average power consumption?",
    )

    expected_average = (
        sample_df[
            [
                "Month1_kWh_Day",
                "Month2_kWh_Day",
                "Month3_kWh_Day",
            ]
        ]
        .mean()
        .mean()
    )

    assert result["success"] is True
    assert result["analysis"]["analysis_type"] == "average"
    assert result["analysis"]["metric_column"] == [
        "Month1_kWh_Day",
        "Month2_kWh_Day",
        "Month3_kWh_Day",
    ]
    assert result["analysis"]["value"] == pytest.approx(expected_average)


def test_dataset_row_count(sample_df):
    result = run_question(
        sample_df,
        "How many rows are in the dataset?",
    )

    assert result["success"] is True
    assert result["dataset_summary"]["rows"] == 4
    assert "4" in result["answer"]


def test_dataset_column_count(sample_df):
    result = run_question(
        sample_df,
        "How many columns are in the dataset?",
    )

    assert result["success"] is True
    assert result["dataset_summary"]["columns"] == 5
    assert "5" in result["answer"]



def test_average_consumption_with_uneven_missing_values(sample_df):
    test_df = sample_df.copy()

    test_df["Month1_kWh_Day"] = [
        10.0, float("nan"), float("nan"), float("nan")
    ]
    test_df["Month2_kWh_Day"] = [
        20.0, 30.0, float("nan"), float("nan")
    ]
    test_df["Month3_kWh_Day"] = [
        float("nan"), float("nan"), 100.0, 200.0
    ]

    result = run_question(
        test_df,
        "What is the average power consumption?",
    )

    monthly_values = test_df[
        [
            "Month1_kWh_Day",
            "Month2_kWh_Day",
            "Month3_kWh_Day",
        ]
    ].to_numpy().flatten()

    expected_average = pd.Series(monthly_values).mean()

    assert result["success"] is True
    assert result["analysis"]["value"] == pytest.approx(72.0)
    assert result["analysis"]["value"] == pytest.approx(
        expected_average
    )

def test_average_consumption_by_city(sample_df):
    result = run_question(
        sample_df,
        "What is the average consumption by city?",
    )

    assert result["success"] is True
    assert result["analysis"]["analysis_type"] == "grouped_average"
    assert result["analysis"]["group_column"] == "City"

    grouped_results = {
        item["group"]: item["average"]
        for item in result["analysis"]["result"]
    }

    assert grouped_results["Karachi"] == pytest.approx(60.0)
    assert grouped_results["Lahore"] == pytest.approx(45.0)
    assert grouped_results["Quetta"] == pytest.approx(25.0)
