
import pandas as pd
import pytest

from backend.anomaly_detector import (
    _is_binary,
    _is_identifier,
    _is_low_cardinality,
    detect_anomalies,
)


def test_empty_dataframe():
    result = detect_anomalies(pd.DataFrame())

    assert result == {
        "success": False,
        "message": "The dataset is empty.",
    }


def test_dataframe_without_numeric_columns():
    dataframe = pd.DataFrame({
        "City": ["Karachi", "Lahore", "Peshawar"],
    })

    result = detect_anomalies(dataframe)

    assert result == {
        "success": False,
        "message": "No numeric columns were found.",
    }


def test_identifier_detection():
    series = pd.Series([1001, 1002, 1003])

    assert _is_identifier("customer_id", series)
    assert _is_identifier("id_customer", series)
    assert _is_identifier("record_number", series)
    assert _is_identifier("product_code", series)
    assert not _is_identifier("consumption", series)


def test_binary_detection():
    assert _is_binary(pd.Series([0, 1, 0, 1]))
    assert _is_binary(pd.Series([0, 0, 0]))
    assert _is_binary(pd.Series([1, None, 1]))
    assert not _is_binary(pd.Series([1, 2, 3]))


def test_low_cardinality_detection():
    assert _is_low_cardinality(pd.Series([1, 2, 3, 4, 5]))
    assert _is_low_cardinality(pd.Series([1, 1, 2, None]))
    assert not _is_low_cardinality(pd.Series([1, 2, 3, 4, 5, 6]))


def test_identifier_binary_and_low_cardinality_columns_are_skipped():
    dataframe = pd.DataFrame({
        "customer_id": list(range(1, 21)),
        "is_active": [0, 1] * 10,
        "rating": [1, 2, 3, 4, 5] * 4,
        "consumption": list(range(1, 21)),
    })

    result = detect_anomalies(dataframe)

    assert result["success"] is True

    skipped = {
        item["column"]: item["reason"]
        for item in result["skipped_columns"]
    }

    assert skipped["customer_id"] == "Identifier column"
    assert skipped["is_active"] == "Binary or boolean-like column"
    assert skipped["rating"] == "Low-cardinality numeric column"
    assert result["numeric_columns_checked"] == 1
    assert result["anomalies"] == []


def test_detects_high_outliers():
    values = list(range(1, 21)) + [1000]
    dataframe = pd.DataFrame({"consumption": values})

    result = detect_anomalies(dataframe)
    anomaly = result["anomalies"][0]

    assert result["success"] is True
    assert result["method"] == "IQR"
    assert result["total_records"] == 21
    assert result["numeric_columns_found"] == 1
    assert result["numeric_columns_checked"] == 1
    assert result["columns_with_anomalies"] == 1
    assert result["total_outlier_occurrences"] == 1
    assert result["unique_anomalous_records"] == 1
    assert result["anomaly_percentage"] == pytest.approx(4.76)

    assert anomaly["column"] == "consumption"
    assert anomaly["outlier_count"] == 1
    assert anomaly["high_outliers"] == 1
    assert anomaly["low_outliers"] == 0
    assert anomaly["severity"] == "medium"


def test_detects_low_outliers():
    values = [1] + list(range(100, 120))
    dataframe = pd.DataFrame({"consumption": values})

    result = detect_anomalies(dataframe)
    anomaly = result["anomalies"][0]

    assert result["success"] is True
    assert anomaly["outlier_count"] == 1
    assert anomaly["high_outliers"] == 0
    assert anomaly["low_outliers"] == 1


def test_columns_with_missing_values():
    dataframe = pd.DataFrame({
        "consumption": list(range(1, 21)) + [1000, None],
    })

    result = detect_anomalies(dataframe)

    assert result["success"] is True
    assert result["total_records"] == 22
    assert result["total_outlier_occurrences"] == 1
    assert result["unique_anomalous_records"] == 1
    assert result["anomaly_percentage"] == pytest.approx(4.55)


def test_all_missing_numeric_column_is_skipped():
    dataframe = pd.DataFrame({
        "consumption": pd.Series([None, None], dtype="float64"),
    })

    result = detect_anomalies(dataframe)

    assert result["success"] is True
    assert result["numeric_columns_found"] == 1
    assert result["numeric_columns_checked"] == 0
    assert result["skipped_columns"] == [
        {
            "column": "consumption",
            "reason": "No valid numeric values",
        }
    ]



def test_zero_iqr_column_is_skipped():
    dataframe = pd.DataFrame({
        "consumption": [10] * 10 + [20, 30, 40, 50, 60, 70],
    })

    result = detect_anomalies(dataframe)

    assert result["success"] is True
    assert result["numeric_columns_found"] == 1

    # The detector checks this column because its IQR is not zero.
    assert result["numeric_columns_checked"] == 1
    assert result["skipped_columns"] == []

def test_anomalous_rows_are_counted_once_across_columns():
    dataframe = pd.DataFrame({
        "consumption": list(range(1, 21)) + [1000],
        "temperature": list(range(1, 21)) + [2000],
    })

    result = detect_anomalies(dataframe)

    assert result["columns_with_anomalies"] == 2
    assert result["total_outlier_occurrences"] == 2
    assert result["unique_anomalous_records"] == 1
    assert result["anomaly_percentage"] == pytest.approx(4.76)


def test_anomalies_are_sorted_by_outlier_count():
    dataframe = pd.DataFrame({
        "consumption": list(range(1, 21)) + [1000, 1100, 1200],
        "temperature": list(range(1, 21)) + [1000, 1100, 1200],
    })

    result = detect_anomalies(dataframe)

    counts = [
        item["outlier_count"]
        for item in result["anomalies"]
    ]

    assert len(counts) == 2
    assert counts == sorted(counts, reverse=True)


def test_severity_thresholds():
    # 100 records: 2% is medium and 5% is high.
    medium_data = pd.DataFrame({
        "consumption": list(range(1, 99)) + [1000, 1100],
    })

    high_data = pd.DataFrame({
        "consumption": list(range(1, 96))
        + [1000, 1100, 1200, 1300, 1400],
    })

    medium_result = detect_anomalies(medium_data)
    high_result = detect_anomalies(high_data)

    assert medium_result["anomalies"][0]["outlier_percentage"] == 2.0
    assert medium_result["anomalies"][0]["severity"] == "medium"

    assert high_result["anomalies"][0]["outlier_percentage"] == 5.0
    assert high_result["anomalies"][0]["severity"] == "high"