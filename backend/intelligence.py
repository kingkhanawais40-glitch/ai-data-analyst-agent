from typing import Any, Dict, List


def _format_number(value: Any) -> str:
    try:
        number = float(value)

        if number.is_integer():
            return f"{int(number):,}"

        return f"{number:,.2f}"

    except (TypeError, ValueError):
        return str(value)


def _format_column_count(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def generate_dataset_intelligence(
    validation: Dict[str, Any],
    anomaly_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate automatic dataset intelligence from existing
    validation and anomaly detection results.

    This function does not modify or recalculate the existing
    validation or anomaly detection logic.
    """

    insights: List[Dict[str, str]] = []
    recommendations: List[str] = []

    # ---------------------------------------------------------
    # Validation / Data Quality
    # ---------------------------------------------------------

    summary = validation.get("summary", {})

    quality_score = summary.get("quality_score", 0)
    quality_label = summary.get("quality_label", "Unknown")

    missing_values = summary.get(
        "total_missing_values",
        0,
    )

    duplicate_rows = summary.get(
        "duplicate_rows",
        0,
    )

    flagged_columns = summary.get(
        "flagged_columns",
        0,
    )

    try:
        quality_score = float(quality_score)
    except (TypeError, ValueError):
        quality_score = 0.0

    try:
        missing_values = int(missing_values or 0)
    except (TypeError, ValueError):
        missing_values = 0

    try:
        duplicate_rows = int(duplicate_rows or 0)
    except (TypeError, ValueError):
        duplicate_rows = 0

    try:
        flagged_columns = int(flagged_columns or 0)
    except (TypeError, ValueError):
        flagged_columns = 0

    if quality_score >= 90:
        quality_status = "Excellent"
    elif quality_score >= 75:
        quality_status = "Good"
    elif quality_score >= 60:
        quality_status = "Fair"
    else:
        quality_status = "Poor"

    # Prefer validator's official quality label when available.
    if quality_label:
        quality_status = str(quality_label)

    quality_article = (
        "an"
        if quality_status.lower()[0] in "aeiou"
        else "a"
    )

    insights.append(
        {
            "type": "data_quality",
            "severity": (
                "low"
                if quality_score >= 90
                else "medium"
                if quality_score >= 75
                else "high"
            ),
            "insight": (
                f"The dataset has {quality_article} "
                f"{quality_status.lower()} data quality score "
                f"of {_format_number(quality_score)}%."
            ),
        }
    )

    if missing_values > 0:
        insights.append(
            {
                "type": "missing_data",
                "severity": "medium",
                "insight": (
                    f"The dataset contains {_format_number(missing_values)} "
                    "missing values that may affect downstream analysis."
                ),
            }
        )

        recommendations.append(
            "Review and handle missing values before critical business analysis."
        )
    else:
        insights.append(
            {
                "type": "missing_data",
                "severity": "low",
                "insight": "No missing values were detected in the dataset.",
            }
        )

    if duplicate_rows > 0:
        insights.append(
            {
                "type": "duplicates",
                "severity": "medium",
                "insight": (
                    f"The dataset contains {_format_number(duplicate_rows)} "
                    "duplicate rows."
                ),
            }
        )

        recommendations.append(
            "Review duplicate records to ensure they do not distort analysis."
        )
    else:
        insights.append(
            {
                "type": "duplicates",
                "severity": "low",
                "insight": "No duplicate rows were detected.",
            }
        )

    if flagged_columns > 0:
        recommendations.append(
            "Review flagged columns identified by the data quality validation."
        )

    # ---------------------------------------------------------
    # Anomaly Analysis
    # ---------------------------------------------------------

    anomaly_percentage = anomaly_data.get(
        "anomaly_percentage",
        0,
    )

    unique_anomalous_records = anomaly_data.get(
        "unique_anomalous_records",
        0,
    )

    total_outlier_occurrences = anomaly_data.get(
        "total_outlier_occurrences",
        0,
    )

    columns_with_anomalies = anomaly_data.get(
        "columns_with_anomalies",
        0,
    )

    anomalies = anomaly_data.get(
        "anomalies",
        [],
    )

    try:
        anomaly_percentage = float(anomaly_percentage)
    except (TypeError, ValueError):
        anomaly_percentage = 0.0

    try:
        unique_anomalous_records = int(
            unique_anomalous_records or 0
        )
    except (TypeError, ValueError):
        unique_anomalous_records = 0

    try:
        total_outlier_occurrences = int(
            total_outlier_occurrences or 0
        )
    except (TypeError, ValueError):
        total_outlier_occurrences = 0

    try:
        columns_with_anomalies = int(
            columns_with_anomalies or 0
        )
    except (TypeError, ValueError):
        columns_with_anomalies = 0

    if anomaly_percentage >= 15:
        anomaly_severity = "high"
    elif anomaly_percentage >= 5:
        anomaly_severity = "medium"
    elif anomaly_percentage > 0:
        anomaly_severity = "low"
    else:
        anomaly_severity = "low"

    if unique_anomalous_records > 0:
        record_word = (
            "record"
            if unique_anomalous_records == 1
            else "records"
        )

        column_word = (
            "column"
            if columns_with_anomalies == 1
            else "columns"
        )

        insights.append(
            {
                "type": "anomaly",
                "severity": anomaly_severity,
                "insight": (
                    f"{_format_number(unique_anomalous_records)} "
                    f"{record_word} "
                    f"({anomaly_percentage:.2f}%) contain detected "
                    f"anomalies across {columns_with_anomalies} "
                    f"{column_word}."
                ),
            }
        )

        recommendations.append(
            "Investigate anomalous records before relying on affected metrics."
        )
    else:
        insights.append(
            {
                "type": "anomaly",
                "severity": "low",
                "insight": "No statistical anomalies were detected.",
            }
        )

    if total_outlier_occurrences > 0:
        occurrence_word = (
            "occurrence"
            if total_outlier_occurrences == 1
            else "occurrences"
        )

        insights.append(
            {
                "type": "outlier_occurrences",
                "severity": anomaly_severity,
                "insight": (
                    f"The anomaly detector identified "
                    f"{_format_number(total_outlier_occurrences)} "
                    f"total outlier {occurrence_word}."
                ),
            }
        )

    # ---------------------------------------------------------
    # Most Affected Column
    # ---------------------------------------------------------

    most_affected_column = None

    if isinstance(anomalies, list) and anomalies:
        valid_anomalies = [
            item
            for item in anomalies
            if isinstance(item, dict)
        ]

        if valid_anomalies:
            most_affected = max(
                valid_anomalies,
                key=lambda item: item.get(
                    "outlier_count",
                    0,
                ),
            )

            most_affected_column = most_affected.get(
                "column"
            )

            outlier_count = most_affected.get(
                "outlier_count",
                0,
            )

            outlier_percentage = most_affected.get(
                "outlier_percentage",
                0,
            )

            severity = most_affected.get(
                "severity",
                "low",
            )

            outlier_word = (
                "outlier"
                if outlier_count == 1
                else "outliers"
            )

            insights.append(
                {
                    "type": "most_affected_column",
                    "severity": severity,
                    "insight": (
                        f"{most_affected_column} is the most affected "
                        f"column with {_format_number(outlier_count)} "
                        f"{outlier_word} "
                        f"({float(outlier_percentage):.2f}%)."
                    ),
                }
            )

            recommendations.append(
                f"Prioritize investigation of {most_affected_column} "
                "because it has the highest anomaly concentration."
            )

    # ---------------------------------------------------------
    # Severity Distribution
    # ---------------------------------------------------------

    high_count = 0
    medium_count = 0
    low_count = 0

    for anomaly in anomalies:
        if not isinstance(anomaly, dict):
            continue

        severity = anomaly.get("severity")

        if severity == "high":
            high_count += 1
        elif severity == "medium":
            medium_count += 1
        elif severity == "low":
            low_count += 1

    if high_count > 0:
        high_word = _format_column_count(
            high_count,
            "column has",
            "columns have",
        )

        insights.append(
            {
                "type": "severity",
                "severity": "high",
                "insight": (
                    f"{high_count} {high_word} high-severity anomalies, "
                    "indicating areas that should receive immediate review."
                ),
            }
        )

        recommendations.append(
            "Prioritize high-severity anomaly columns for investigation."
        )

    if medium_count > 0:
        medium_word = _format_column_count(
            medium_count,
            "column has",
            "columns have",
        )

        insights.append(
            {
                "type": "severity",
                "severity": "medium",
                "insight": (
                    f"{medium_count} {medium_word} medium-severity anomalies "
                    "and should be monitored."
                ),
            }
        )

    if low_count > 0:
        low_word = _format_column_count(
            low_count,
            "column has",
            "columns have",
        )

        insights.append(
            {
                "type": "severity",
                "severity": "low",
                "insight": (
                    f"{low_count} {low_word} low-severity anomalies "
                    "that should remain under observation."
                ),
            }
        )

    # ---------------------------------------------------------
    # Overall Risk
    # ---------------------------------------------------------

    if quality_score < 60 or anomaly_percentage >= 15:
        overall_risk = "High"
    elif quality_score < 75 or anomaly_percentage >= 5:
        overall_risk = "Medium"
    else:
        overall_risk = "Low"

    if overall_risk == "High":
        recommendations.append(
            "Perform data quality and anomaly investigation before "
            "making important business decisions."
        )
    elif overall_risk == "Medium":
        recommendations.append(
            "Review the main data quality and anomaly findings "
            "before high-impact decisions."
        )
    else:
        recommendations.append(
            "The dataset is generally suitable for analysis, "
            "with routine monitoring recommended."
        )

    recommendations = list(
        dict.fromkeys(recommendations)
    )

    return {
        "success": True,
        "quality_score": round(quality_score, 2),
        "quality_status": quality_status,
        "anomaly_percentage": round(anomaly_percentage, 2),
        "unique_anomalous_records": unique_anomalous_records,
        "total_outlier_occurrences": total_outlier_occurrences,
        "columns_with_anomalies": columns_with_anomalies,
        "most_affected_column": most_affected_column,
        "severity_distribution": {
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        },
        "overall_risk": overall_risk,
        "insights": insights,
        "recommendations": recommendations,
    }