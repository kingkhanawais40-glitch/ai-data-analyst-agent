from typing import Any, Dict

import pandas as pd


def answer_business_question(
    dataframe: pd.DataFrame,
    question: str,
) -> Dict[str, Any]:
    """
    Analyze natural-language business questions against a dataset.
    This deterministic engine does not require an external AI API.
    """

    normalized_question = question.strip().lower()

    if not normalized_question:
        return {
            "success": False,
            "question": question,
            "answer": "Please enter a business question.",
        }

    row_count = len(dataframe)
    column_count = len(dataframe.columns)

    numeric_columns = dataframe.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_columns = dataframe.select_dtypes(
        exclude="number"
    ).columns.tolist()

    # ---------------------------------------------------------
    # Helper 1: Identify actual consumption metrics
    # ---------------------------------------------------------

    def get_consumption_candidates():
        indicators = [
            "consumption",
            "kwh_day",
            "kwh/day",
            "energy_usage",
            "energy_use",
            "power_usage",
            "power_use",
        ]

        excluded_keywords = [
            "rate",
            "price",
            "bill",
            "cost",
            "predicted",
            "forecast",
            "estimate",
            "estimated",
        ]

        candidates = []

        for column in numeric_columns:
            column_lower = column.lower()

            if not any(
                keyword in column_lower
                for keyword in indicators
            ):
                continue

            if any(
                keyword in column_lower
                for keyword in excluded_keywords
            ):
                continue

            candidates.append(column)

        return candidates

    # ---------------------------------------------------------
    # Helper 2: Select grouping column from the question
    # ---------------------------------------------------------

    def get_group_column():
        question_words = (
            normalized_question.replace("_", " ").split()
        )

        for column in categorical_columns:
            if dataframe[column].nunique(dropna=True) <= 1:
                continue

            column_name = column.lower().replace("_", " ")

            if column_name in normalized_question:
                return column

            column_words = column_name.split()

            if column_words and all(
                word in question_words
                for word in column_words
            ):
                return column

        # Preserve the previous City-first default.
        if (
            "City" in dataframe.columns
            and dataframe["City"].nunique(dropna=True) > 1
        ):
            return "City"

        if (
            "city" in dataframe.columns
            and dataframe["city"].nunique(dropna=True) > 1
        ):
            return "city"

        categorical_candidates = [
            column
            for column in categorical_columns
            if dataframe[column].nunique(dropna=True) > 1
        ]

        if categorical_candidates:
            return categorical_candidates[0]

        return None

    # ---------------------------------------------------------
    # Helper 3: Select the consumption metrics to analyze
    # ---------------------------------------------------------

    def get_selected_consumption_columns(candidates):
        monthly_columns = [
            column
            for column in candidates
            if any(
                month in column.lower()
                for month in ["month1", "month2", "month3"]
            )
        ]

        return (
            monthly_columns
            if monthly_columns
            else candidates[:1]
        )

    # ---------------------------------------------------------
    # Helper 4: Convert selected metrics to numeric values
    # ---------------------------------------------------------

    def get_numeric_consumption_data(columns):
        return dataframe[columns].apply(
            pd.to_numeric,
            errors="coerce",
        )

    # ---------------------------------------------------------
    # Helper 5: Calculate combined average across observations
    # ---------------------------------------------------------

    def calculate_combined_average(numeric_dataframe):
        """
        Calculate one average across every valid observation
        in the selected columns.

        Missing and non-numeric values are ignored.
        Each valid observation receives equal weight.
        """

        combined_values = (
            numeric_dataframe.to_numpy().flatten()
        )

        numeric_values = pd.Series(
            combined_values,
            dtype="float64",
        ).dropna()

        if numeric_values.empty:
            return None

        return float(numeric_values.mean())


    # ---------------------------------------------------------
    # Helper 5B: Calculate average consumption for every group
    # ---------------------------------------------------------

    def analyze_average_by_group(selected_columns):
        group_column = get_group_column()

        if not group_column:
            return None

        working_dataframe = dataframe[
            [group_column] + selected_columns
        ].copy()

        working_dataframe[selected_columns] = (
            get_numeric_consumption_data(selected_columns)
        )

        working_dataframe["_business_consumption"] = (
            working_dataframe[selected_columns].mean(axis=1)
        )

        valid_rows = working_dataframe.dropna(
            subset=[group_column, "_business_consumption"]
        )

        grouped = (
            valid_rows.groupby(group_column)["_business_consumption"]
            .agg(["mean", "count"])
            .sort_values("mean", ascending=False)
        )

        if grouped.empty:
            return None

        results = [
            {
                "group": str(category),
                "average": round(float(row["mean"]), 2),
                "count": int(row["count"]),
            }
            for category, row in grouped.iterrows()
        ]

        metric_description = ", ".join(selected_columns)

        result_text = "; ".join(
            f"{item['group']}: {item['average']:.2f}"
            for item in results
        )

        return {
            "success": True,
            "question": question,
            "answer": (
                f"Average power consumption by {group_column}, "
                f"based on {metric_description}: {result_text}."
            ),
            "analysis": {
                "analysis_type": "grouped_average",
                "group_column": group_column,
                "metric_column": selected_columns,
                "result": results,
            },
            "dataset_summary": {
                "rows": row_count,
                "columns": column_count,
            },
        }


    # ---------------------------------------------------------
    # Helper 6: Shared highest / lowest consumption analysis
    # ---------------------------------------------------------

    def analyze_grouped_consumption(find_highest: bool):
        candidates = get_consumption_candidates()

        if not candidates:
            return None

        selected_columns = get_selected_consumption_columns(
            candidates
        )

        group_column = get_group_column()

        if not group_column:
            return None

        working_dataframe = dataframe.copy()

        working_dataframe[selected_columns] = (
            get_numeric_consumption_data(selected_columns)
        )

        working_dataframe["_business_consumption"] = (
            working_dataframe[selected_columns].mean(axis=1)
        )

        grouped = (
            working_dataframe.groupby(group_column)[
                "_business_consumption"
            ]
            .mean()
            .dropna()
            .sort_values(ascending=not find_highest)
        )

        if grouped.empty:
            return None

        category = grouped.index[0]
        value = float(grouped.iloc[0])

        metric_description = (
            "average of " + ", ".join(selected_columns)
            if len(selected_columns) > 1
            else selected_columns[0]
        )

        if find_highest:
            comparison = "highest"
            analysis_type = "grouped_average"
        else:
            comparison = "lowest"
            analysis_type = "grouped_average_minimum"

        return {
            "success": True,
            "question": question,
            "answer": (
                f"{category} has the {comparison} average power "
                f"consumption based on {metric_description}, "
                f"at approximately {value:,.2f}."
            ),
            "analysis": {
                "analysis_type": analysis_type,
                "group_column": group_column,
                "metric_column": selected_columns,
                "result": str(category),
                "value": round(value, 2),
            },
            "dataset_summary": {
                "rows": row_count,
                "columns": column_count,
            },
        }

    # ---------------------------------------------------------
    # Highest / maximum consumption questions
    # ---------------------------------------------------------

    highest_keywords = [
        "highest",
        "maximum",
        "max",
        "largest",
        "most",
    ]

    power_keywords = [
        "power consumption",
        "electricity consumption",
        "energy consumption",
        "power usage",
        "electricity usage",
        "energy usage",
        "consumption",
    ]

    if (
        any(
            keyword in normalized_question
            for keyword in highest_keywords
        )
        and any(
            keyword in normalized_question
            for keyword in power_keywords
        )
    ):
        result = analyze_grouped_consumption(
            find_highest=True
        )

        if result is not None:
            return result

    # ---------------------------------------------------------
    # Lowest / minimum consumption questions
    # ---------------------------------------------------------

    lowest_keywords = [
        "lowest",
        "minimum",
        "min",
        "smallest",
        "least",
    ]

    if (
        any(
            keyword in normalized_question
            for keyword in lowest_keywords
        )
        and any(
            keyword in normalized_question
            for keyword in power_keywords
        )
    ):
        result = analyze_grouped_consumption(
            find_highest=False
        )

        if result is not None:
            return result


    # ---------------------------------------------------------
    # Average consumption questions
    # ---------------------------------------------------------

    average_keywords = [
        "average",
        "mean",
        "avg",
    ]

    if any(
        keyword in normalized_question
        for keyword in average_keywords
    ):
        consumption_candidates = get_consumption_candidates()

        if consumption_candidates:
            selected_columns = get_selected_consumption_columns(
                consumption_candidates
            )

            # Group only when the question explicitly requests it.
            grouping_requested = (
                " by " in f" {normalized_question} "
                or " for each " in f" {normalized_question} "
                or " per " in f" {normalized_question} "
            )

            if grouping_requested:
                grouped_result = analyze_average_by_group(
                    selected_columns
                )

                if grouped_result is not None:
                    return grouped_result

            # Preserve the existing overall-average behavior.
            numeric_data = get_numeric_consumption_data(
                selected_columns
            )

            average_value = calculate_combined_average(
                numeric_data
            )

            if average_value is not None:
                metric_description = (
                    ", ".join(selected_columns)
                    if len(selected_columns) > 1
                    else selected_columns[0]
                )

                return {
                    "success": True,
                    "question": question,
                    "answer": (
                        f"The average power consumption across "
                        f"{metric_description} is "
                        f"{average_value:,.2f}."
                    ),
                    "analysis": {
                        "analysis_type": "average",
                        "metric_column": selected_columns,
                        "value": round(average_value, 2),
                    },
                    "dataset_summary": {
                        "rows": row_count,
                        "columns": column_count,
                    },
                }

    # ---------------------------------------------------------
    # Dataset size questions
    # ---------------------------------------------------------

    if (
        "how many rows" in normalized_question
        or "number of rows" in normalized_question
        or "how many records" in normalized_question
        or "number of records" in normalized_question
    ):
        return {
            "success": True,
            "question": question,
            "answer": (
                f"The dataset contains {row_count:,} rows "
                f"across {column_count} columns."
            ),
            "analysis": {
                "analysis_type": "dataset_size",
                "rows": row_count,
                "columns": column_count,
            },
            "dataset_summary": {
                "rows": row_count,
                "columns": column_count,
            },
        }

    # ---------------------------------------------------------
    # Column questions
    # ---------------------------------------------------------

    if (
        "how many columns" in normalized_question
        or "number of columns" in normalized_question
        or "what columns" in normalized_question
        or "which columns" in normalized_question
    ):
        return {
            "success": True,
            "question": question,
            "answer": (
                f"The dataset contains {column_count} columns."
            ),
            "analysis": {
                "analysis_type": "columns",
                "columns": dataframe.columns.tolist(),
            },
            "dataset_summary": {
                "rows": row_count,
                "columns": column_count,
            },
        }

    # ---------------------------------------------------------
    # Fallback
    # ---------------------------------------------------------

    return {
        "success": False,
        "question": question,
        "answer": (
            "I could not determine the required analysis from this "
            "question yet. Try asking about averages, highest "
            "consumption, rows, records, or columns."
        ),
        "supported_analysis": [
            "Highest or maximum consumption",
            "Lowest or minimum consumption",
            "Average or mean values",
            "Number of rows or records",
            "Number of columns",
        ],
        "dataset_summary": {
            "rows": row_count,
            "columns": column_count,
        },
    }
