import pytest

from backend.intelligence import (
    _format_column_count,
    _format_number,
    generate_dataset_intelligence,
)


def make_validation(
    quality_score=95,
    quality_label="Excellent",
    missing_values=0,
    duplicate_rows=0,
    flagged_columns=0,
):
    return {
        "summary": {
            "quality_score": quality_score,
            "quality_label": quality_label,
            "total_missing_values": missing_values,
            "duplicate_rows": duplicate_rows,
            "flagged_columns": flagged_columns,
        }
    }


def make_anomaly_data(
    anomaly_percentage=0,
    unique_anomalous_records=0,
    total_outlier_occurrences=0,
    columns_with_anomalies=0,
    anomalies=None,
):
    return {
        "anomaly_percentage": anomaly_percentage,
        "unique_anomalous_records": unique_anomalous_records,
        "total_outlier_occurrences": total_outlier_occurrences,
        "columns_with_anomalies": columns_with_anomalies,
        "anomalies": anomalies or [],
    }


# ============================================================
# FORMAT HELPERS
# ============================================================

def test_format_number_integer_and_decimal_values():
    assert _format_number(1234) == "1,234"
    assert _format_number(1234.567) == "1,234.57"
    assert _format_number(-25) == "-25"
    assert _format_number(0.5) == "0.50"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "None"),
        ("invalid", "invalid"),
        ("12.5", "12.50"),
        ("12", "12"),
    ],
)
def test_format_number_handles_nonstandard_values(value, expected):
    assert _format_number(value) == expected


@pytest.mark.parametrize(
    ("count", "singular", "plural", "expected"),
    [
        (1, "column has", "columns have", "column has"),
        (0, "column has", "columns have", "columns have"),
        (2, "record", "records", "records"),
    ],
)
def test_format_column_count(count, singular, plural, expected):
    assert _format_column_count(count, singular, plural) == expected


# ============================================================
# DEFAULT OUTPUT AND DATA QUALITY
# ============================================================

def test_default_intelligence_result():
    result = generate_dataset_intelligence(
        validation={},
        anomaly_data={},
    )

    assert result["success"] is True
    assert result["quality_score"] == 0
    assert result["quality_status"] == "Unknown"
    assert result["anomaly_percentage"] == 0
    assert result["unique_anomalous_records"] == 0
    assert result["total_outlier_occurrences"] == 0
    assert result["columns_with_anomalies"] == 0
    assert result["most_affected_column"] is None
    assert result["severity_distribution"] == {
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    assert result["overall_risk"] == "High"
    assert result["recommendations"]


def test_excellent_quality_without_anomalies():
    result = generate_dataset_intelligence(
        make_validation(quality_score=95, quality_label=""),
        make_anomaly_data(),
    )

    assert result["quality_score"] == 95
    assert result["quality_status"] == "Excellent"
    assert result["overall_risk"] == "Low"

    quality_insight = next(
        item for item in result["insights"]
        if item["type"] == "data_quality"
    )

    assert quality_insight["severity"] == "low"
    assert (
        "an excellent data quality score of 95%"
        in quality_insight["insight"]
    )

    assert any(
        item["type"] == "missing_data"
        and item["severity"] == "low"
        for item in result["insights"]
    )

    assert any(
        item["type"] == "duplicates"
        and item["severity"] == "low"
        for item in result["insights"]
    )


@pytest.mark.parametrize(
    ("score", "expected_status", "expected_severity"),
    [
        (95, "Excellent", "low"),
        (90, "Excellent", "low"),
        (89, "Good", "medium"),
        (75, "Good", "medium"),
        (74, "Fair", "high"),
        (60, "Fair", "high"),
        (59, "Poor", "high"),
        (0, "Poor", "high"),
    ],
)
def test_quality_score_boundaries(
    score,
    expected_status,
    expected_severity,
):
    result = generate_dataset_intelligence(
        make_validation(quality_score=score, quality_label=""),
        make_anomaly_data(),
    )

    assert result["quality_status"] == expected_status

    insight = next(
        item for item in result["insights"]
        if item["type"] == "data_quality"
    )

    assert insight["severity"] == expected_severity


def test_official_quality_label_overrides_computed_status():
    result = generate_dataset_intelligence(
        make_validation(
            quality_score=95,
            quality_label="Needs Review",
        ),
        make_anomaly_data(),
    )

    assert result["quality_status"] == "Needs Review"

    insight = next(
        item for item in result["insights"]
        if item["type"] == "data_quality"
    )

    assert "a needs review data quality score" in insight["insight"]


def test_missing_values_duplicates_and_flagged_columns():
    result = generate_dataset_intelligence(
        make_validation(
            quality_score=85,
            quality_label="Good",
            missing_values=125,
            duplicate_rows=7,
            flagged_columns=2,
        ),
        make_anomaly_data(),
    )

    types = [item["type"] for item in result["insights"]]

    assert "missing_data" in types
    assert "duplicates" in types

    missing = next(
        item for item in result["insights"]
        if item["type"] == "missing_data"
    )

    assert "125 missing values" in missing["insight"]

    duplicates = next(
        item for item in result["insights"]
        if item["type"] == "duplicates"
    )

    assert "7 duplicate rows" in duplicates["insight"]

    assert any(
        "missing values" in recommendation
        for recommendation in result["recommendations"]
    )

    assert any(
        "duplicate records" in recommendation
        for recommendation in result["recommendations"]
    )

    assert any(
        "flagged columns" in recommendation
        for recommendation in result["recommendations"]
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("invalid", 0),
        (None, 0),
        (12.9, 12),
    ],
)
def test_invalid_quality_counts_are_handled(value, expected):
    result = generate_dataset_intelligence(
        {
            "summary": {
                "quality_score": "invalid",
                "quality_label": "",
                "total_missing_values": value,
                "duplicate_rows": value,
                "flagged_columns": value,
            }
        },
        make_anomaly_data(),
    )

    assert result["quality_score"] == 0
    assert result["quality_status"] == "Poor"
    assert result["insights"]

    if expected == 0:
        assert not any(
            "missing values that may affect" in item["insight"]
            for item in result["insights"]
        )


# ============================================================
# ANOMALY ANALYSIS
# ============================================================

@pytest.mark.parametrize(
    ("percentage", "expected_severity"),
    [
        (15, "high"),
        (20, "high"),
        (5, "medium"),
        (14.99, "medium"),
        (0.01, "low"),
        (0, "low"),
    ],
)
def test_anomaly_severity_boundaries(
    percentage,
    expected_severity,
):
    result = generate_dataset_intelligence(
        make_validation(),
        make_anomaly_data(
            anomaly_percentage=percentage,
            unique_anomalous_records=3 if percentage else 0,
            columns_with_anomalies=2,
        ),
    )

    anomaly_insight = next(
        item for item in result["insights"]
        if item["type"] == "anomaly"
    )

    assert anomaly_insight["severity"] == (
        expected_severity if percentage else "low"
    )


def test_anomaly_pluralization_and_recommendation():
    result = generate_dataset_intelligence(
        make_validation(),
        make_anomaly_data(
            anomaly_percentage=16.25,
            unique_anomalous_records=2,
            total_outlier_occurrences=3,
            columns_with_anomalies=2,
        ),
    )

    anomaly = next(
        item for item in result["insights"]
        if item["type"] == "anomaly"
    )

    assert "2 records (16.25%)" in anomaly["insight"]
    assert "across 2 columns" in anomaly["insight"]

    occurrences = next(
        item for item in result["insights"]
        if item["type"] == "outlier_occurrences"
    )

    assert "3 total outlier occurrences" in occurrences["insight"]

    assert any(
        "Investigate anomalous records" in recommendation
        for recommendation in result["recommendations"]
    )


def test_singular_anomaly_record_column_and_occurrence():
    result = generate_dataset_intelligence(
        make_validation(),
        make_anomaly_data(
            anomaly_percentage=2.5,
            unique_anomalous_records=1,
            total_outlier_occurrences=1,
            columns_with_anomalies=1,
        ),
    )

    anomaly = next(
        item for item in result["insights"]
        if item["type"] == "anomaly"
    )

    assert "1 record (2.50%)" in anomaly["insight"]
    assert "across 1 column" in anomaly["insight"]

    occurrences = next(
        item for item in result["insights"]
        if item["type"] == "outlier_occurrences"
    )

    assert "1 total outlier occurrence" in occurrences["insight"]


def test_zero_anomalies_and_zero_occurrences():
    result = generate_dataset_intelligence(
        make_validation(),
        make_anomaly_data(),
    )

    assert any(
        item["type"] == "anomaly"
        and item["insight"] == "No statistical anomalies were detected."
        for item in result["insights"]
    )

    assert not any(
        item["type"] == "outlier_occurrences"
        for item in result["insights"]
    )


def test_invalid_anomaly_counts_fall_back_to_zero():
    result = generate_dataset_intelligence(
        make_validation(),
        {
            "anomaly_percentage": "invalid",
            "unique_anomalous_records": "invalid",
            "total_outlier_occurrences": "invalid",
            "columns_with_anomalies": "invalid",
            "anomalies": [],
        },
    )

    assert result["anomaly_percentage"] == 0
    assert result["unique_anomalous_records"] == 0
    assert result["total_outlier_occurrences"] == 0
    assert result["columns_with_anomalies"] == 0
    assert result["most_affected_column"] is None


# ============================================================
# MOST AFFECTED COLUMN AND SEVERITY DISTRIBUTION
# ============================================================

def test_most_affected_column_and_severity_distribution():
    anomalies = [
        {
            "column": "Energy",
            "outlier_count": 12,
            "outlier_percentage": 3.5,
            "severity": "high",
        },
        {
            "column": "Temperature",
            "outlier_count": 5,
            "outlier_percentage": 1.5,
            "severity": "medium",
        },
        {
            "column": "Humidity",
            "outlier_count": 1,
            "outlier_percentage": 0.5,
            "severity": "low",
        },
    ]

    result = generate_dataset_intelligence(
        make_validation(),
        make_anomaly_data(
            anomaly_percentage=16,
            unique_anomalous_records=15,
            total_outlier_occurrences=18,
            columns_with_anomalies=3,
            anomalies=anomalies,
        ),
    )

    assert result["most_affected_column"] == "Energy"

    assert result["severity_distribution"] == {
        "high": 1,
        "medium": 1,
        "low": 1,
    }

    most_affected = next(
        item for item in result["insights"]
        if item["type"] == "most_affected_column"
    )

    assert most_affected["severity"] == "high"
    assert "Energy is the most affected column" in most_affected["insight"]
    assert "12 outliers (3.50%)" in most_affected["insight"]

    severity_insights = [
        item for item in result["insights"]
        if item["type"] == "severity"
    ]

    assert len(severity_insights) == 3

    assert any(
        "Prioritize investigation of Energy" in recommendation
        for recommendation in result["recommendations"]
    )

    assert any(
        "high-severity anomaly columns" in recommendation
        for recommendation in result["recommendations"]
    )


def test_severity_distribution_singular_and_plural():
    anomalies = [
        {"column": "A", "outlier_count": 1, "severity": "high"},
        {"column": "B", "outlier_count": 1, "severity": "medium"},
        {"column": "C", "outlier_count": 1, "severity": "medium"},
        {"column": "D", "outlier_count": 1, "severity": "low"},
        {"column": "E", "outlier_count": 1, "severity": "low"},
    ]

    result = generate_dataset_intelligence(
        make_validation(),
        make_anomaly_data(anomalies=anomalies),
    )

    severity_insights = {
        item["severity"]: item["insight"]
        for item in result["insights"]
        if item["type"] == "severity"
    }

    assert "1 column has high-severity anomalies" in severity_insights["high"]
    assert (
        "2 columns have medium-severity anomalies"
        in severity_insights["medium"]
    )
    assert (
        "2 columns have low-severity anomalies"
        in severity_insights["low"]
    )


def test_invalid_anomaly_entries_are_skipped_in_severity_count():
    anomalies = [
        "invalid",
        None,
        123,
        {"column": "Energy", "outlier_count": 4, "severity": "high"},
        {
            "column": "Temperature",
            "outlier_count": 2,
            "severity": "unknown",
        },
    ]

    result = generate_dataset_intelligence(
        make_validation(),
        make_anomaly_data(
            anomaly_percentage=7,
            unique_anomalous_records=2,
            columns_with_anomalies=1,
            anomalies=anomalies,
        ),
    )

    assert result["severity_distribution"] == {
        "high": 1,
        "medium": 0,
        "low": 0,
    }


def test_non_list_anomalies_do_not_create_most_affected_column():
    result = generate_dataset_intelligence(
        make_validation(),
        {
            "anomaly_percentage": 1,
            "unique_anomalous_records": 1,
            "total_outlier_occurrences": 0,
            "columns_with_anomalies": 1,
            "anomalies": {
                "column": "Energy",
                "outlier_count": 5,
            },
        },
    )

    assert result["most_affected_column"] is None

    assert result["severity_distribution"] == {
        "high": 0,
        "medium": 0,
        "low": 0,
    }


def test_most_affected_column_ignores_non_dict_entries():
    result = generate_dataset_intelligence(
        make_validation(),
        make_anomaly_data(
            anomalies=[
                "invalid",
                None,
                {"column": "Energy", "outlier_count": 3},
                {"column": "Temperature", "outlier_count": 8},
            ],
        ),
    )

    assert result["most_affected_column"] == "Temperature"


# ============================================================
# OVERALL RISK AND RECOMMENDATIONS
# ============================================================

@pytest.mark.parametrize(
    ("quality_score", "anomaly_percentage", "expected_risk"),
    [
        (59, 0, "High"),
        (90, 15, "High"),
        (74, 0, "Medium"),
        (90, 5, "Medium"),
        (90, 4.99, "Low"),
        (75, 0, "Low"),
    ],
)
def test_overall_risk_boundaries(
    quality_score,
    anomaly_percentage,
    expected_risk,
):
    result = generate_dataset_intelligence(
        make_validation(
            quality_score=quality_score,
            quality_label="",
        ),
        make_anomaly_data(
            anomaly_percentage=anomaly_percentage,
        ),
    )

    assert result["overall_risk"] == expected_risk


def test_risk_recommendations():
    high = generate_dataset_intelligence(
        make_validation(quality_score=40, quality_label=""),
        make_anomaly_data(),
    )

    medium = generate_dataset_intelligence(
        make_validation(quality_score=65, quality_label=""),
        make_anomaly_data(),
    )

    low = generate_dataset_intelligence(
        make_validation(quality_score=95, quality_label=""),
        make_anomaly_data(),
    )

    assert any(
        "before making important business decisions" in item
        for item in high["recommendations"]
    )

    assert any(
        "before high-impact decisions" in item
        for item in medium["recommendations"]
    )

    assert any(
        "generally suitable for analysis" in item
        for item in low["recommendations"]
    )


def test_recommendations_are_deduplicated():
    result = generate_dataset_intelligence(
        make_validation(
            quality_score=50,
            quality_label="",
            missing_values=5,
            duplicate_rows=2,
            flagged_columns=1,
        ),
        make_anomaly_data(
            anomaly_percentage=20,
            unique_anomalous_records=4,
            columns_with_anomalies=1,
            anomalies=[
                {
                    "column": "Energy",
                    "outlier_count": 4,
                    "outlier_percentage": 2.0,
                    "severity": "high",
                }
            ],
        ),
    )

    recommendations = result["recommendations"]

    assert len(recommendations) == len(set(recommendations))
