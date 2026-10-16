from typing import Any, Dict, List

import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json


def generate_chart(
    chart_type: str,
    columns: List[str],
    results: List[Dict[str, Any]],
    title: str = "Analysis Results",
) -> Dict[str, Any]:
    """
    Generate a Plotly chart from structured analysis results.

    The function creates the chart only from already-calculated
    deterministic results. It does not perform analysis.
    """

    if not columns:
        return {
            "success": False,
            "message": "No columns available for chart generation.",
        }

    if not results:
        return {
            "success": False,
            "message": "No result data available for chart generation.",
        }

    try:
        import pandas as pd

        dataframe = pd.DataFrame(results)

        if chart_type == "bar":
            if len(columns) < 2:
                return {
                    "success": False,
                    "message": "A bar chart requires at least two columns.",
                }

            x_column = columns[0]
            y_column = columns[1]

            figure = px.bar(
                dataframe,
                x=x_column,
                y=y_column,
                title=title,
            )

        elif chart_type == "line":
            if len(columns) < 2:
                return {
                    "success": False,
                    "message": "A line chart requires at least two columns.",
                }

            x_column = columns[0]
            y_column = columns[1]

            figure = px.line(
                dataframe,
                x=x_column,
                y=y_column,
                title=title,
                markers=True,
            )

        elif chart_type == "pie":
            if len(columns) < 2:
                return {
                    "success": False,
                    "message": "A pie chart requires at least two columns.",
                }

            name_column = columns[0]
            value_column = columns[1]

            figure = px.pie(
                dataframe,
                names=name_column,
                values=value_column,
                title=title,
            )

        elif chart_type == "scatter":
            if len(columns) < 2:
                return {
                    "success": False,
                    "message": "A scatter chart requires at least two columns.",
                }

            x_column = columns[0]
            y_column = columns[1]

            figure = px.scatter(
                dataframe,
                x=x_column,
                y=y_column,
                title=title,
            )

        else:
            return {
                "success": False,
                "message": f"Unsupported chart type: {chart_type}",
            }

        figure.update_layout(
            template="plotly_white",
            margin=dict(
                l=40,
                r=40,
                t=70,
                b=40,
            ),
        )

        # ----------------------------------------------------
        # Convert Plotly + NumPy objects to JSON-safe data
        # ----------------------------------------------------

        figure_dict = json.loads(
            json.dumps(
                figure.to_dict(),
                cls=PlotlyJSONEncoder,
            )
        )

        return {
            "success": True,
            "chart_type": chart_type,
            "title": title,
            "columns": columns,
            "figure": figure_dict,
        }

    except Exception as error:
        return {
            "success": False,
            "chart_type": chart_type,
            "message": f"Chart generation failed: {str(error)}",
        }