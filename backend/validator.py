import pandas as pd


def validate_dataframe(dataframe: pd.DataFrame) -> dict:
    """
    Analyze a DataFrame for common data-quality issues.
    This function does not modify the original DataFrame.
    """

    issues = []
    warnings = []
    column_checks = []

    row_count = len(dataframe)
    column_count = len(dataframe.columns)

    # ---------------------------------------------------------
    # Dataset-level checks
    # ---------------------------------------------------------

    duplicate_rows = int(dataframe.duplicated().sum())

    if duplicate_rows > 0:
        issues.append({
            "type": "duplicate_rows",
            "severity": "high",
            "message": f"{duplicate_rows:,} duplicate rows detected.",
            "count": duplicate_rows,
        })

    total_missing = int(dataframe.isna().sum().sum())

    if total_missing > 0:
        warnings.append({
            "type": "missing_values",
            "severity": "medium",
            "message": f"{total_missing:,} missing values detected across the dataset.",
            "count": total_missing,
        })

    # ---------------------------------------------------------
    # Column-level checks
    # ---------------------------------------------------------

    for column in dataframe.columns:
        series = dataframe[column]

        missing_count = int(series.isna().sum())
        missing_percentage = (
            (missing_count / row_count) * 100
            if row_count > 0
            else 0
        )

        unique_count = int(series.nunique(dropna=True))

        check = {
            "column": str(column),
            "data_type": str(series.dtype),
            "missing_values": missing_count,
            "missing_percentage": round(missing_percentage, 2),
            "unique_values": unique_count,
            "flags": [],
        }

        # -----------------------------------------------------
        # Missing-value check
        # -----------------------------------------------------

        if missing_count > 0:
            if missing_percentage >= 50:
                severity = "high"
            elif missing_percentage >= 10:
                severity = "medium"
            else:
                severity = "low"

            check["flags"].append({
                "type": "missing_values",
                "severity": severity,
                "message": (
                    f"{missing_count:,} missing values "
                    f"({missing_percentage:.2f}%)."
                ),
            })

        # -----------------------------------------------------
        # Identifier detection
        # -----------------------------------------------------

        if row_count > 0 and unique_count == row_count:
            column_lower = str(column).lower()

            identifier_keywords = [
                "id",
                "identifier",
                "record",
                "uuid",
                "code",
                "number",
            ]

            if any(keyword in column_lower for keyword in identifier_keywords):
                check["flags"].append({
                    "type": "identifier_column",
                    "severity": "info",
                    "message": (
                        "Column appears to be an identifier and "
                        "may not be useful for statistical analysis."
                    ),
                })

        # -----------------------------------------------------
        # Constant-column detection
        # -----------------------------------------------------

        if unique_count <= 1:
            check["flags"].append({
                "type": "constant_column",
                "severity": "high",
                "message": (
                    "Column contains one or zero unique values "
                    "and may provide little analytical value."
                ),
            })

        # -----------------------------------------------------
        # High-cardinality categorical detection
        # -----------------------------------------------------

        if not pd.api.types.is_numeric_dtype(series):
            if row_count > 0:
                cardinality_percentage = (
                    unique_count / row_count
                ) * 100

                if cardinality_percentage >= 80:
                    check["flags"].append({
                        "type": "high_cardinality",
                        "severity": "medium",
                        "message": (
                            f"Very high cardinality: "
                            f"{unique_count:,} unique values "
                            f"({cardinality_percentage:.2f}% of rows)."
                        ),
                    })

        # -----------------------------------------------------
        # Numeric validation
        # -----------------------------------------------------

        if pd.api.types.is_numeric_dtype(series):
            numeric_series = series.dropna()

            if len(numeric_series) > 0:

                # Infinite values
                infinite_count = int(
                    numeric_series.isin([float("inf"), float("-inf")]).sum()
                )

                if infinite_count > 0:
                    check["flags"].append({
                        "type": "infinite_values",
                        "severity": "high",
                        "message": (
                            f"{infinite_count:,} infinite values detected."
                        ),
                    })

                # Negative values
                negative_count = int((numeric_series < 0).sum())

                if negative_count > 0:
                    check["flags"].append({
                        "type": "negative_values",
                        "severity": "medium",
                        "message": (
                            f"{negative_count:,} negative values detected."
                        ),
                    })

                # IQR outlier detection
                q1 = numeric_series.quantile(0.25)
                q3 = numeric_series.quantile(0.75)
                iqr = q3 - q1

                if iqr > 0:
                    lower_bound = q1 - (1.5 * iqr)
                    upper_bound = q3 + (1.5 * iqr)

                    outlier_count = int(
                        (
                            (numeric_series < lower_bound)
                            | (numeric_series > upper_bound)
                        ).sum()
                    )

                    if outlier_count > 0:
                        outlier_percentage = (
                            outlier_count / len(numeric_series)
                        ) * 100

                        check["outliers"] = {
                            "count": outlier_count,
                            "percentage": round(
                                outlier_percentage,
                                2
                            ),
                            "lower_bound": round(
                                float(lower_bound),
                                4
                            ),
                            "upper_bound": round(
                                float(upper_bound),
                                4
                            ),
                        }

                        if outlier_percentage >= 10:
                            check["flags"].append({
                                "type": "outliers",
                                "severity": "medium",
                                "message": (
                                    f"{outlier_count:,} potential outliers "
                                    f"detected using the IQR method."
                                ),
                            })

        column_checks.append(check)

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    flagged_columns = sum(
        1
        for column in column_checks
        if column["flags"]
    )

    high_severity = 0
    medium_severity = 0
    low_severity = 0

    for column in column_checks:
        for flag in column["flags"]:
            if flag["severity"] == "high":
                high_severity += 1
            elif flag["severity"] == "medium":
                medium_severity += 1
            elif flag["severity"] == "low":
                low_severity += 1

    quality_score = 100.0

    # Missing data penalty
    if row_count > 0 and column_count > 0:
        total_cells = row_count * column_count
        missing_percentage = (
            total_missing / total_cells
        ) * 100

        quality_score -= min(
            missing_percentage * 2,
            25
        )

    # Duplicate penalty
    if row_count > 0:
        duplicate_percentage = (
            duplicate_rows / row_count
        ) * 100

        quality_score -= min(
            duplicate_percentage * 2,
            20
        )

    # Severity penalties
    quality_score -= min(high_severity * 5, 25)
    quality_score -= min(medium_severity * 2, 15)
    quality_score -= min(low_severity * 0.5, 5)

    quality_score = max(
        0,
        min(100, round(quality_score, 2))
    )

    if quality_score >= 90:
        quality_label = "Excellent"
    elif quality_score >= 75:
        quality_label = "Good"
    elif quality_score >= 60:
        quality_label = "Fair"
    elif quality_score >= 40:
        quality_label = "Poor"
    else:
        quality_label = "Critical"


    return {
        "success": True,
        "dataset": {
            "rows": row_count,
            "columns": column_count,
        },

        "summary": {
            "duplicate_rows": duplicate_rows,
            "total_missing_values": total_missing,
            "flagged_columns": flagged_columns,
            "high_severity_flags": high_severity,
            "medium_severity_flags": medium_severity,
            "low_severity_flags": low_severity,
            "quality_score": quality_score,
            "quality_label": quality_label,
        },
        "dataset_issues": issues,
        "dataset_warnings": warnings,
        "columns": column_checks,
    }
