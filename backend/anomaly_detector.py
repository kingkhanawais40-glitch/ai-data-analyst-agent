import pandas as pd


def _is_identifier(column_name: str, series: pd.Series) -> bool:
    name = column_name.lower()

    identifier_keywords = [
        "_id",
        "id_",
        "identifier",
        "uuid",
        "record",
        "code",
    ]

    return any(keyword in name for keyword in identifier_keywords)


def _is_binary(series: pd.Series) -> bool:
    unique_values = series.dropna().unique()
    return len(unique_values) <= 2


def _is_low_cardinality(series: pd.Series) -> bool:
    unique_count = series.nunique(dropna=True)
    return unique_count <= 5


def detect_anomalies(dataframe: pd.DataFrame) -> dict:
    """
    Detect meaningful statistical anomalies using the IQR method.

    Identifier, binary, and low-cardinality numeric columns
    are excluded from statistical anomaly detection.

    A row containing anomalies in multiple columns is counted
    only once in unique_anomalous_records.
    """

    if dataframe.empty:
        return {
            "success": False,
            "message": "The dataset is empty.",
        }

    numeric_columns = dataframe.select_dtypes(
        include=["number"]
    ).columns.tolist()

    if not numeric_columns:
        return {
            "success": False,
            "message": "No numeric columns were found.",
        }

    columns_checked = []
    skipped_columns = []
    anomalies = []

    unique_anomalous_rows = set()

    for column in numeric_columns:
        series = dataframe[column].dropna()

        if series.empty:
            skipped_columns.append(
                {
                    "column": str(column),
                    "reason": "No valid numeric values",
                }
            )
            continue

        if _is_identifier(column, series):
            skipped_columns.append(
                {
                    "column": str(column),
                    "reason": "Identifier column",
                }
            )
            continue

        if _is_binary(series):
            skipped_columns.append(
                {
                    "column": str(column),
                    "reason": "Binary or boolean-like column",
                }
            )
            continue

        if _is_low_cardinality(series):
            skipped_columns.append(
                {
                    "column": str(column),
                    "reason": "Low-cardinality numeric column",
                }
            )
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1

        if iqr == 0:
            skipped_columns.append(
                {
                    "column": str(column),
                    "reason": "Zero IQR",
                }
            )
            continue

        columns_checked.append(str(column))

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        high_mask = dataframe[column] > upper_bound
        low_mask = dataframe[column] < lower_bound
        outlier_mask = high_mask | low_mask

        outlier_count = int(outlier_mask.sum())

        if outlier_count == 0:
            continue

        for index in dataframe.index[outlier_mask]:
            unique_anomalous_rows.add(index)

        outlier_percentage = round(
            (outlier_count / len(dataframe)) * 100,
            2,
        )

        high_outliers = int(high_mask.sum())
        low_outliers = int(low_mask.sum())

        if outlier_percentage >= 5:
            severity = "high"
        elif outlier_percentage >= 2:
            severity = "medium"
        else:
            severity = "low"

        anomalies.append(
            {
                "column": str(column),
                "outlier_count": outlier_count,
                "outlier_percentage": outlier_percentage,
                "high_outliers": high_outliers,
                "low_outliers": low_outliers,
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
                "severity": severity,
            }
        )

    anomalies.sort(
        key=lambda item: item["outlier_count"],
        reverse=True,
    )

    total_outlier_occurrences = int(
        sum(item["outlier_count"] for item in anomalies)
    )

    unique_anomalous_records = len(unique_anomalous_rows)

    anomaly_percentage = round(
        (unique_anomalous_records / len(dataframe)) * 100,
        2,
    )

    return {
        "success": True,
        "method": "IQR",
        "total_records": int(len(dataframe)),
        "numeric_columns_found": len(numeric_columns),
        "numeric_columns_checked": len(columns_checked),
        "skipped_columns": skipped_columns,
        "columns_with_anomalies": len(anomalies),
        "total_outlier_occurrences": total_outlier_occurrences,
        "unique_anomalous_records": unique_anomalous_records,
        "anomaly_percentage": anomaly_percentage,
        "anomalies": anomalies,
    }