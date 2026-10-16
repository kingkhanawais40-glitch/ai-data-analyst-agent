from typing import Any, Dict, List

import pandas as pd

from backend.sql_agent import run_sql_agent
from backend.chart_generator import generate_chart


def recommend_chart(
    columns: List[str],
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Recommend a suitable visualization based on the structure
    of the analysis result.
    """

    if not columns or not results:
        return {
            "success": False,
            "message": "No result data available for visualization.",
        }

    # ---------------------------------------------------------
    # Two-column grouped result
    # ---------------------------------------------------------
    if len(columns) == 2:
        first_column = columns[0]
        second_column = columns[1]

        numeric_values = 0

        for row in results:
            value = row.get(second_column)

            if isinstance(value, (int, float)):
                numeric_values += 1

        if numeric_values == len(results):
            return {
                "success": True,
                "chart_type": "bar",
                "x_axis": first_column,
                "y_axis": second_column,
                "title": f"{second_column} by {first_column}",
                "reason": (
                    "A bar chart is suitable for comparing "
                    "numeric values across categories."
                ),
            }

    # ---------------------------------------------------------
    # Single numeric result
    # ---------------------------------------------------------
    if len(columns) == 1:
        return {
            "success": True,
            "chart_type": "indicator",
            "value": columns[0],
            "title": columns[0],
            "reason": (
                "A single numeric result is best displayed "
                "as a KPI or indicator."
            ),
        }

    # ---------------------------------------------------------
    # Fallback
    # ---------------------------------------------------------
    return {
        "success": True,
        "chart_type": "table",
        "columns": columns,
        "title": "Analysis Results",
        "reason": (
            "The result structure is better represented "
            "as a table."
        ),
    }


def analyze_and_visualize(
    dataframe: pd.DataFrame,
    question: str,
) -> Dict[str, Any]:
    """
    Complete data analysis and visualization pipeline:

    Natural language question
        ↓
    SQL Agent
        ↓
    SQL results
        ↓
    Visualization recommendation
        ↓
    Plotly chart generation
    """

    if dataframe.empty:
        return {
            "success": False,
            "message": "The dataset is empty.",
        }

    # ---------------------------------------------------------
    # Step 1 — Run SQL Agent
    # ---------------------------------------------------------
    sql_result = run_sql_agent(
        dataframe,
        question,
    )

    if not sql_result.get("success"):
        return {
            "success": False,
            "question": question,
            "message": sql_result.get(
                "message",
                "SQL analysis failed.",
            ),
        }

    columns = sql_result.get("columns", [])
    results = sql_result.get("results", [])

    # ---------------------------------------------------------
    # Step 2 — Recommend visualization
    # ---------------------------------------------------------
    visualization = recommend_chart(
        columns,
        results,
    )

    if not visualization.get("success"):
        return {
            "success": False,
            "question": question,
            "sql_result": sql_result,
            "message": visualization.get(
                "message",
                "Visualization recommendation failed.",
            ),
        }

    chart_type = visualization.get("chart_type")

    # ---------------------------------------------------------
    # Step 3 — Indicator/KPI results
    # ---------------------------------------------------------
    if chart_type == "indicator":
        return {
            "success": True,
            "question": question,
            "sql_result": sql_result,
            "visualization": visualization,
            "chart": None,
        }

    # ---------------------------------------------------------
    # Step 4 — Unsupported visual result types
    # ---------------------------------------------------------
    if chart_type in {"table", None}:
        return {
            "success": True,
            "question": question,
            "sql_result": sql_result,
            "visualization": visualization,
            "chart": None,
        }

    # ---------------------------------------------------------
    # Step 5 — Generate Plotly chart
    # ---------------------------------------------------------
    chart = generate_chart(
        chart_type=chart_type,
        columns=columns,
        results=results,
        title=visualization.get(
            "title",
            "Analysis Results",
        ),
    )

    if not chart.get("success"):
        return {
            "success": False,
            "question": question,
            "sql_result": sql_result,
            "visualization": visualization,
            "message": chart.get(
                "message",
                "Chart generation failed.",
            ),
        }

    # ---------------------------------------------------------
    # Final result
    # ---------------------------------------------------------
    return {
        "success": True,
        "question": question,
        "sql_result": sql_result,
        "visualization": visualization,
        "chart": chart,
    }