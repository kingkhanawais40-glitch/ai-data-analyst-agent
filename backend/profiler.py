import pandas as pd


def profile_dataframe(dataframe: pd.DataFrame) -> dict:
    """
    Generate a comprehensive profile of a pandas DataFrame.
    """

    profile = {
        "row_count": int(dataframe.shape[0]),
        "column_count": int(dataframe.shape[1]),
        "columns": [],
        "duplicate_rows": int(dataframe.duplicated().sum()),
        "total_missing_values": int(dataframe.isna().sum().sum()),
    }

    for column in dataframe.columns:
        series = dataframe[column]

        column_info = {
            "name": str(column),
            "data_type": str(series.dtype),
            "missing_values": int(series.isna().sum()),
            "missing_percentage": round(
                float(series.isna().mean() * 100), 2
            ),
            "unique_values": int(series.nunique(dropna=True)),
        }

        if pd.api.types.is_numeric_dtype(series):
            numeric_series = series.dropna()

            if len(numeric_series) > 0:
                column_info["type"] = "numeric"
                column_info["statistics"] = {
                    "mean": round(float(numeric_series.mean()), 4),
                    "median": round(float(numeric_series.median()), 4),
                    "minimum": round(float(numeric_series.min()), 4),
                    "maximum": round(float(numeric_series.max()), 4),
                    "standard_deviation": round(
                        float(numeric_series.std()), 4
                    ),
                }
            else:
                column_info["type"] = "numeric"
                column_info["statistics"] = {}

        else:
            column_info["type"] = "categorical"

            value_counts = series.value_counts(dropna=True).head(10)

            column_info["top_values"] = [
                {
                    "value": str(value),
                    "count": int(count),
                }
                for value, count in value_counts.items()
            ]

        profile["columns"].append(column_info)

    return profile