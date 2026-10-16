import pandas as pd


def _normalize_text(text: str) -> str:
    return " ".join(str(text).lower().strip().split())


def _find_categorical_column(dataframe: pd.DataFrame, question: str):
    question_normalized = _normalize_text(question)

    categorical_columns = [
        "City",
        "Season",
        "Building_Type",
        "Weather_Condition",
        "AC_Type",
        "Efficiency_Rating",
        "Iron_Used",
    ]

    keyword_map = {
        "City": ["city", "cities"],
        "Season": ["season", "seasons"],
        "Building_Type": ["building type", "building"],
        "Weather_Condition": ["weather", "weather condition"],
        "AC_Type": ["ac type", "air conditioner type", "air conditioning type"],
        "Efficiency_Rating": [
            "efficiency",
            "efficiency rating",
            "rating",
        ],
        "Iron_Used": ["iron", "iron used"],
    }

    # Explicit grouping phrases
    grouping_phrases = [
        "by city",
        "by season",
        "by building type",
        "by building",
        "by weather",
        "by weather condition",
        "by ac type",
        "by air conditioner type",
        "by efficiency",
        "by efficiency rating",
        "by iron",
    ]

    has_grouping_phrase = any(
        phrase in question_normalized for phrase in grouping_phrases
    )

    if not has_grouping_phrase:
        return None

    for column in categorical_columns:
        if column not in dataframe.columns:
            continue

        keywords = keyword_map.get(column, [])

        for keyword in keywords:
            if keyword in question_normalized:
                return column

    return None


def _find_numeric_column(dataframe: pd.DataFrame, question: str):
    question_normalized = _normalize_text(question)

    # Highest priority: monthly bill
    if any(
        phrase in question_normalized
        for phrase in [
            "monthly bill",
            "electricity bill",
            "electric bill",
            "bill",
            "cost",
        ]
    ):
        if "Est_Monthly_Bill_PKR" in dataframe.columns:
            return "Est_Monthly_Bill_PKR"


    # Predicted consumption — check before general consumption
    if any(
        phrase in question_normalized
        for phrase in [
            "predicted consumption",
            "predicted electricity",
            "predicted energy",
            "predicted next month",
            "next month consumption",
        ]
    ):
        if "Predicted_Next_Month_kWh_Day" in dataframe.columns:
            return "Predicted_Next_Month_kWh_Day"

    # Monthly consumption — check before general consumption
    if "month 1" in question_normalized or "month1" in question_normalized:
        if "Month1_kWh_Day" in dataframe.columns:
            return "Month1_kWh_Day"

    if "month 2" in question_normalized or "month2" in question_normalized:
        if "Month2_kWh_Day" in dataframe.columns:
            return "Month2_kWh_Day"

    if "month 3" in question_normalized or "month3" in question_normalized:
        if "Month3_kWh_Day" in dataframe.columns:
            return "Month3_kWh_Day"

    # General electricity consumption — check after specific questions
    if any(
        phrase in question_normalized
        for phrase in [
            "average electricity consumption",
            "average energy consumption",
            "average power consumption",
            "electricity consumption",
            "energy consumption",
            "power consumption",
            "consumption",
        ]
    ):
        if "ThreeMonth_Avg_kWh_Day" in dataframe.columns:
            return "ThreeMonth_Avg_kWh_Day"

    # Predicted consumption
    if any(
        phrase in question_normalized
        for phrase in [
            "predicted consumption",
            "predicted electricity",
            "predicted energy",
            "predicted next month",
            "next month consumption",
        ]
    ):
        if "Predicted_Next_Month_kWh_Day" in dataframe.columns:
            return "Predicted_Next_Month_kWh_Day"

    # Monthly consumption
    if "month 1" in question_normalized or "month1" in question_normalized:
        if "Month1_kWh_Day" in dataframe.columns:
            return "Month1_kWh_Day"

    if "month 2" in question_normalized or "month2" in question_normalized:
        if "Month2_kWh_Day" in dataframe.columns:
            return "Month2_kWh_Day"

    if "month 3" in question_normalized or "month3" in question_normalized:
        if "Month3_kWh_Day" in dataframe.columns:
            return "Month3_kWh_Day"

    # NEPRA rate
    if any(
        phrase in question_normalized
        for phrase in [
            "nepra rate",
            "electricity rate",
            "rate per kwh",
            "rate",
        ]
    ):
        if "NEPRA_Rate_PKR_kWh" in dataframe.columns:
            return "NEPRA_Rate_PKR_kWh"

    # Temperature
    if any(
        phrase in question_normalized
        for phrase in [
            "temperature",
            "temp",
        ]
    ):
        if "Temperature_C" in dataframe.columns:
            return "Temperature_C"

    # Humidity
    if "humidity" in question_normalized:
        if "Humidity_Percent" in dataframe.columns:
            return "Humidity_Percent"

    # Building size
    if any(
        phrase in question_normalized
        for phrase in [
            "building size",
            "building area",
            "size of building",
        ]
    ):
        if "Building_Size_sqft" in dataframe.columns:
            return "Building_Size_sqft"

    # Residents
    if any(
        phrase in question_normalized
        for phrase in [
            "residents",
            "number of residents",
            "people",
        ]
    ):
        if "No_of_Residents" in dataframe.columns:
            return "No_of_Residents"

    # AC units
    if any(
        phrase in question_normalized
        for phrase in [
            "ac units",
            "air conditioner units",
            "number of ac",
        ]
    ):
        if "AC_Units" in dataframe.columns:
            return "AC_Units"

    # AC hours
    if any(
        phrase in question_normalized
        for phrase in [
            "ac daily hours",
            "ac hours",
            "air conditioner hours",
        ]
    ):
        if "AC_Daily_Hours" in dataframe.columns:
            return "AC_Daily_Hours"

    # AC wattage
    if any(
        phrase in question_normalized
        for phrase in [
            "ac wattage",
            "ac power",
        ]
    ):
        if "AC_Wattage_kW" in dataframe.columns:
            return "AC_Wattage_kW"

    # Fridge
    if "fridge" in question_normalized:
        if "Fridge_Count" in dataframe.columns:
            return "Fridge_Count"

    # Fans
    if "fan" in question_normalized:
        if "Fans_Count" in dataframe.columns:
            return "Fans_Count"

    # Lights
    if "light" in question_normalized:
        if "Lights_Count" in dataframe.columns:
            return "Lights_Count"

    # TV
    if any(
        phrase in question_normalized
        for phrase in [
            "tv",
            "television",
        ]
    ):
        if "TV_Count" in dataframe.columns:
            return "TV_Count"

    # Fallback to first numeric column, excluding Record_ID
    numeric_columns = dataframe.select_dtypes(include="number").columns.tolist()

    numeric_columns = [
        column
        for column in numeric_columns
        if column != "Record_ID"
    ]

    if numeric_columns:
        return numeric_columns[0]

    return None


def _find_correlation_columns(dataframe: pd.DataFrame, question: str):
    question_normalized = _normalize_text(question)

    column_keywords = {
        "Temperature_C": [
            "temperature",
            "temp",
        ],
        "ThreeMonth_Avg_kWh_Day": [
            "electricity consumption",
            "energy consumption",
            "power consumption",
            "average electricity consumption",
            "average energy consumption",
            "average power consumption",
            "consumption",
        ],
        "Humidity_Percent": [
            "humidity",
        ],
        "Building_Size_sqft": [
            "building size",
            "building area",
        ],
        "No_of_Residents": [
            "residents",
            "number of residents",
        ],
        "AC_Units": [
            "ac units",
            "air conditioner units",
        ],
        "AC_Daily_Hours": [
            "ac hours",
            "ac daily hours",
            "air conditioner hours",
        ],
        "AC_Wattage_kW": [
            "ac wattage",
            "ac power",
        ],
        "Fridge_Count": [
            "fridge",
            "refrigerator",
        ],
        "Fans_Count": [
            "fans",
            "fan count",
        ],
        "Lights_Count": [
            "lights",
            "light count",
        ],
        "TV_Count": [
            "tv",
            "television",
        ],
        "Est_Monthly_Bill_PKR": [
            "monthly bill",
            "electricity bill",
            "electric bill",
            "bill",
        ],
        "Month1_kWh_Day": [
            "month 1",
            "month1",
        ],
        "Month2_kWh_Day": [
            "month 2",
            "month2",
        ],
        "Month3_kWh_Day": [
            "month 3",
            "month3",
        ],
        "Predicted_Next_Month_kWh_Day": [
            "predicted consumption",
            "predicted next month",
            "predicted electricity",
        ],
        "NEPRA_Rate_PKR_kWh": [
            "nepra rate",
            "electricity rate",
            "rate per kwh",
        ],
    }

    detected_columns = []

    for column, keywords in column_keywords.items():
        if column not in dataframe.columns:
            continue

        for keyword in keywords:
            if keyword in question_normalized:
                if column not in detected_columns:
                    detected_columns.append(column)
                break

    # Remove duplicates while preserving order
    detected_columns = list(dict.fromkeys(detected_columns))

    if len(detected_columns) >= 2:
        return detected_columns[:2]

    return []


def _average_analysis(dataframe: pd.DataFrame, column: str):
    if column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{column}' was not found.",
        }

    series = pd.to_numeric(dataframe[column], errors="coerce").dropna()

    if series.empty:
        return {
            "success": False,
            "message": f"No numeric data available in '{column}'.",
        }

    return {
        "success": True,
        "operation": "average",
        "column": column,
        "result": round(float(series.mean()), 2),
        "count": int(series.count()),
        "minimum": round(float(series.min()), 2),
        "maximum": round(float(series.max()), 2),
    }


def _sum_analysis(dataframe: pd.DataFrame, column: str):
    if column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{column}' was not found.",
        }

    series = pd.to_numeric(dataframe[column], errors="coerce").dropna()

    if series.empty:
        return {
            "success": False,
            "message": f"No numeric data available in '{column}'.",
        }

    return {
        "success": True,
        "operation": "sum",
        "column": column,
        "result": round(float(series.sum()), 2),
        "count": int(series.count()),
    }


def _group_average_analysis(
    dataframe: pd.DataFrame,
    group_by: str,
    column: str,
):
    if group_by not in dataframe.columns:
        return {
            "success": False,
            "message": f"Grouping column '{group_by}' was not found.",
        }

    if column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{column}' was not found.",
        }

    working_dataframe = dataframe[[group_by, column]].copy()
    working_dataframe[column] = pd.to_numeric(
        working_dataframe[column],
        errors="coerce",
    )

    working_dataframe = working_dataframe.dropna(
        subset=[group_by, column]
    )

    if working_dataframe.empty:
        return {
            "success": False,
            "message": "No valid data available for grouped analysis.",
        }

    grouped = (
        working_dataframe
        .groupby(group_by)[column]
        .agg(["mean", "count"])
        .sort_values("mean", ascending=False)
    )

    result = []

    for group, row in grouped.iterrows():
        result.append(
            {
                "group": str(group),
                "average": round(float(row["mean"]), 2),
                "count": int(row["count"]),
            }
        )

    return {
        "success": True,
        "operation": "group_average",
        "group_by": group_by,
        "column": column,
        "result": result,
    }


def _group_sum_analysis(
    dataframe: pd.DataFrame,
    group_by: str,
    column: str,
):
    if group_by not in dataframe.columns:
        return {
            "success": False,
            "message": f"Grouping column '{group_by}' was not found.",
        }

    if column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{column}' was not found.",
        }

    working_dataframe = dataframe[[group_by, column]].copy()

    working_dataframe[column] = pd.to_numeric(
        working_dataframe[column],
        errors="coerce",
    )

    working_dataframe = working_dataframe.dropna(
        subset=[group_by, column]
    )

    if working_dataframe.empty:
        return {
            "success": False,
            "message": "No valid data available for grouped analysis.",
        }

    grouped = (
        working_dataframe
        .groupby(group_by)[column]
        .agg(["sum", "count"])
        .sort_values("sum", ascending=False)
    )

    result = []

    for group, row in grouped.iterrows():
        result.append(
            {
                "group": str(group),
                "total": round(float(row["sum"]), 2),
                "count": int(row["count"]),
            }
        )

    return {
        "success": True,
        "operation": "group_sum",
        "group_by": group_by,
        "column": column,
        "result": result,
    }


def _group_highest_analysis(
    dataframe: pd.DataFrame,
    group_by: str,
    column: str,
):
    if group_by not in dataframe.columns:
        return {
            "success": False,
            "message": f"Grouping column '{group_by}' was not found.",
        }

    if column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{column}' was not found.",
        }

    working_dataframe = dataframe[[group_by, column]].copy()

    working_dataframe[column] = pd.to_numeric(
        working_dataframe[column],
        errors="coerce",
    )

    working_dataframe = working_dataframe.dropna(
        subset=[group_by, column]
    )

    if working_dataframe.empty:
        return {
            "success": False,
            "message": "No valid data available for grouped analysis.",
        }

    grouped = (
        working_dataframe
        .groupby(group_by)[column]
        .agg(["mean", "count"])
        .sort_values("mean", ascending=False)
    )

    highest_group = grouped.iloc[0]

    return {
        "success": True,
        "operation": "group_highest",
        "group_by": group_by,
        "column": column,
        "result": {
            "group": str(grouped.index[0]),
            "average": round(float(highest_group["mean"]), 2),
            "count": int(highest_group["count"]),
        },
    }


def _group_lowest_analysis(
    dataframe: pd.DataFrame,
    group_by: str,
    column: str,
):
    if group_by not in dataframe.columns:
        return {
            "success": False,
            "message": f"Grouping column '{group_by}' was not found.",
        }

    if column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{column}' was not found.",
        }

    working_dataframe = dataframe[[group_by, column]].copy()

    working_dataframe[column] = pd.to_numeric(
        working_dataframe[column],
        errors="coerce",
    )

    working_dataframe = working_dataframe.dropna(
        subset=[group_by, column]
    )

    if working_dataframe.empty:
        return {
            "success": False,
            "message": "No valid data available for grouped analysis.",
        }

    grouped = (
        working_dataframe
        .groupby(group_by)[column]
        .agg(["mean", "count"])
        .sort_values("mean", ascending=True)
    )

    lowest_group = grouped.iloc[0]

    return {
        "success": True,
        "operation": "group_lowest",
        "group_by": group_by,
        "column": column,
        "result": {
            "group": str(grouped.index[0]),
            "average": round(float(lowest_group["mean"]), 2),
            "count": int(lowest_group["count"]),
        },
    }


def _top_analysis(
    dataframe: pd.DataFrame,
    column: str,
    limit: int = 10,
):
    if column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{column}' was not found.",
        }

    series = pd.to_numeric(dataframe[column], errors="coerce").dropna()

    if series.empty:
        return {
            "success": False,
            "message": f"No numeric data available in '{column}'.",
        }

    top_values = series.nlargest(limit)

    result = [
        {
            "rank": index + 1,
            "value": round(float(value), 2),
        }
        for index, value in enumerate(top_values.tolist())
    ]

    return {
        "success": True,
        "operation": "top",
        "column": column,
        "result": result,
    }


def _correlation_analysis(
    dataframe: pd.DataFrame,
    columns: list,
):
    if len(columns) != 2:
        return {
            "success": False,
            "message": "Correlation analysis requires exactly two numeric columns.",
        }

    first_column, second_column = columns

    if first_column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{first_column}' was not found.",
        }

    if second_column not in dataframe.columns:
        return {
            "success": False,
            "message": f"Column '{second_column}' was not found.",
        }

    working_dataframe = dataframe[
        [first_column, second_column]
    ].copy()

    working_dataframe[first_column] = pd.to_numeric(
        working_dataframe[first_column],
        errors="coerce",
    )

    working_dataframe[second_column] = pd.to_numeric(
        working_dataframe[second_column],
        errors="coerce",
    )

    working_dataframe = working_dataframe.dropna()

    if len(working_dataframe) < 2:
        return {
            "success": False,
            "message": "Not enough valid data for correlation analysis.",
        }

    correlation = working_dataframe[first_column].corr(
        working_dataframe[second_column]
    )

    if pd.isna(correlation):
        return {
            "success": False,
            "message": "Correlation could not be calculated.",
        }

    return {
        "success": True,
        "operation": "correlation",
        "columns": [
            first_column,
            second_column,
        ],
        "result": round(float(correlation), 4),
        "count": int(len(working_dataframe)),
    }


def analyze_question(dataframe: pd.DataFrame, question: str) -> dict:
    question_normalized = _normalize_text(question)

    # ============================================================
    # UNSUPPORTED FUTURE / PREDICTION QUESTIONS
    # ============================================================
    # These questions require a forecasting/ML model, which we
    # have not implemented yet. Do not guess or perform another
    # unrelated analysis.
    unsupported_future_terms = [
        "next year",
        "next month",
        "next week",
        "future",
        "forecast",
        "predict",
        "prediction",
        "will happen",
        "what will happen",
    ]

    if any(
        term in question_normalized
        for term in unsupported_future_terms
    ):
        return {
            "success": False,
            "question": question,
            "message": (
                "I could not determine the required analysis "
                "from this question yet."
            ),
        }

    # ============================================================
    # CORRELATION
    # ============================================================
    if (
        "correlation" in question_normalized
        or "relationship between" in question_normalized
    ):
        correlation_columns = _find_correlation_columns(
            dataframe,
            question,
        )

        if len(correlation_columns) == 2:
            return {
                "success": True,
                "question": question,
                "analysis": _correlation_analysis(
                    dataframe,
                    correlation_columns,
                ),
            }

        return {
            "success": False,
            "question": question,
            "analysis": {
                "success": False,
                "message": (
                    "I could not identify two numeric columns "
                    "for the correlation analysis."
                ),
            },
        }

    # ============================================================
    # FIND GROUPING COLUMN
    # ============================================================
    group_by = _find_categorical_column(
        dataframe,
        question,
    )

    # ============================================================
    # GROUPED HIGHEST
    # ============================================================
    if group_by is not None and any(
        phrase in question_normalized
        for phrase in [
            "highest",
            "maximum",
            "max",
            "most",
            "greatest",
            "largest",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            return {
                "success": True,
                "question": question,
                "analysis": _group_highest_analysis(
                    dataframe,
                    group_by,
                    column,
                ),
            }

    # ============================================================
    # GROUPED LOWEST
    # ============================================================
    if group_by is not None and any(
        phrase in question_normalized
        for phrase in [
            "lowest",
            "minimum",
            "min",
            "least",
            "smallest",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            return {
                "success": True,
                "question": question,
                "analysis": _group_lowest_analysis(
                    dataframe,
                    group_by,
                    column,
                ),
            }

    # ============================================================
    # GROUPED AVERAGE
    # ============================================================
    if group_by is not None and any(
        phrase in question_normalized
        for phrase in [
            "average",
            "mean",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            return {
                "success": True,
                "question": question,
                "analysis": _group_average_analysis(
                    dataframe,
                    group_by,
                    column,
                ),
            }

    # ============================================================
    # GROUPED SUM / TOTAL
    # ============================================================
    if group_by is not None and any(
        phrase in question_normalized
        for phrase in [
            "total",
            "sum",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            return {
                "success": True,
                "question": question,
                "analysis": _group_sum_analysis(
                    dataframe,
                    group_by,
                    column,
                ),
            }

    # ============================================================
    # SINGLE COLUMN HIGHEST
    # ============================================================
    if any(
        phrase in question_normalized
        for phrase in [
            "highest",
            "maximum",
            "max",
            "most",
            "greatest",
            "largest",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            series = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            ).dropna()

            if not series.empty:
                return {
                    "success": True,
                    "question": question,
                    "analysis": {
                        "success": True,
                        "operation": "highest",
                        "column": column,
                        "result": round(float(series.max()), 2),
                        "count": int(series.count()),
                    },
                }

    # ============================================================
    # SINGLE COLUMN LOWEST
    # ============================================================
    if any(
        phrase in question_normalized
        for phrase in [
            "lowest",
            "minimum",
            "min",
            "least",
            "smallest",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            series = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            ).dropna()

            if not series.empty:
                return {
                    "success": True,
                    "question": question,
                    "analysis": {
                        "success": True,
                        "operation": "lowest",
                        "column": column,
                        "result": round(float(series.min()), 2),
                        "count": int(series.count()),
                    },
                }

    # ============================================================
    # AVERAGE
    # ============================================================
    if any(
        phrase in question_normalized
        for phrase in [
            "average",
            "mean",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            return {
                "success": True,
                "question": question,
                "analysis": _average_analysis(
                    dataframe,
                    column,
                ),
            }

    # ============================================================
    # TOTAL / SUM
    # ============================================================
    if any(
        phrase in question_normalized
        for phrase in [
            "total",
            "sum",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            return {
                "success": True,
                "question": question,
                "analysis": _sum_analysis(
                    dataframe,
                    column,
                ),
            }

    # ============================================================
    # TOP VALUES
    # ============================================================
    if any(
        phrase in question_normalized
        for phrase in [
            "top",
            "highest values",
            "largest values",
        ]
    ):
        column = _find_numeric_column(
            dataframe,
            question,
        )

        if column:
            return {
                "success": True,
                "question": question,
                "analysis": _top_analysis(
                    dataframe,
                    column,
                ),
            }

    # ============================================================
    # UNSUPPORTED QUESTION
    # ============================================================
    return {
        "success": False,
        "question": question,
        "message": (
            "I could not determine the required analysis "
            "from this question yet."
        ),
    }
