from typing import Any, Dict, List


def _format_number(value: Any) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def generate_insights(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Convert deterministic analysis results into human-readable
    business insights.

    This function does not perform calculations itself.
    It interprets results that have already been calculated
    by the analysis engine.
    """

    if not isinstance(analysis, dict):
        return []

    if not analysis.get("success"):
        return []

    operation = analysis.get("operation")
    insights: List[Dict[str, str]] = []

    # ============================================================
    # AVERAGE
    # ============================================================
    if operation == "average":
        column = analysis.get("column", "value")
        result = analysis.get("result")
        count = analysis.get("count")

        insights.append(
            {
                "type": "summary",
                "severity": "info",
                "insight": (
                    f"The average value of {column} is "
                    f"{_format_number(result)} based on "
                    f"{_format_number(count)} records."
                ),
            }
        )

    # ============================================================
    # SUM
    # ============================================================
    elif operation == "sum":
        column = analysis.get("column", "value")
        result = analysis.get("result")
        count = analysis.get("count")

        insights.append(
            {
                "type": "summary",
                "severity": "info",
                "insight": (
                    f"The total value of {column} is "
                    f"{_format_number(result)} across "
                    f"{_format_number(count)} records."
                ),
            }
        )

    # ============================================================
    # HIGHEST
    # ============================================================
    elif operation == "highest":
        column = analysis.get("column", "value")
        result = analysis.get("result")

        insights.append(
            {
                "type": "maximum",
                "severity": "info",
                "insight": (
                    f"The highest value of {column} is "
                    f"{_format_number(result)}."
                ),
            }
        )

    # ============================================================
    # LOWEST
    # ============================================================
    elif operation == "lowest":
        column = analysis.get("column", "value")
        result = analysis.get("result")

        insights.append(
            {
                "type": "minimum",
                "severity": "info",
                "insight": (
                    f"The lowest value of {column} is "
                    f"{_format_number(result)}."
                ),
            }
        )

    # ============================================================
    # GROUP AVERAGE
    # ============================================================
    elif operation == "group_average":
        group_by = analysis.get("group_by", "group")
        column = analysis.get("column", "value")
        results = analysis.get("result", [])

        if results:
            highest = max(
                results,
                key=lambda item: item.get("average", float("-inf")),
            )

            lowest = min(
                results,
                key=lambda item: item.get("average", float("inf")),
            )

            insights.append(
                {
                    "type": "comparison",
                    "severity": "info",
                    "insight": (
                        f"{highest.get('group')} has the highest average "
                        f"{column} at "
                        f"{_format_number(highest.get('average'))}, "
                        f"while {lowest.get('group')} has the lowest "
                        f"average at "
                        f"{_format_number(lowest.get('average'))}."
                    ),
                }
            )

            insights.append(
                {
                    "type": "group_summary",
                    "severity": "info",
                    "insight": (
                        f"The analysis compares {column} across "
                        f"{len(results)} {group_by} groups."
                    ),
                }
            )

    # ============================================================
    # GROUP SUM
    # ============================================================
    elif operation == "group_sum":
        group_by = analysis.get("group_by", "group")
        column = analysis.get("column", "value")
        results = analysis.get("result", [])

        if results:
            highest = max(
                results,
                key=lambda item: item.get("total", float("-inf")),
            )

            lowest = min(
                results,
                key=lambda item: item.get("total", float("inf")),
            )

            insights.append(
                {
                    "type": "comparison",
                    "severity": "info",
                    "insight": (
                        f"{highest.get('group')} has the highest total "
                        f"{column} at "
                        f"{_format_number(highest.get('total'))}, "
                        f"while {lowest.get('group')} has the lowest "
                        f"total at "
                        f"{_format_number(lowest.get('total'))}."
                    ),
                }
            )

            insights.append(
                {
                    "type": "group_summary",
                    "severity": "info",
                    "insight": (
                        f"The analysis compares total {column} across "
                        f"{len(results)} {group_by} groups."
                    ),
                }
            )

    # ============================================================
    # GROUP HIGHEST
    # ============================================================
    elif operation == "group_highest":
        group_by = analysis.get("group_by", "group")
        column = analysis.get("column", "value")
        result = analysis.get("result", {})

        group = result.get("group")
        average = result.get("average")
        count = result.get("count")

        insights.append(
            {
                "type": "maximum",
                "severity": "high",
                "insight": (
                    f"{group} has the highest average {column} at "
                    f"{_format_number(average)} based on "
                    f"{_format_number(count)} records."
                ),
            }
        )

    # ============================================================
    # GROUP LOWEST
    # ============================================================
    elif operation == "group_lowest":
        group_by = analysis.get("group_by", "group")
        column = analysis.get("column", "value")
        result = analysis.get("result", {})

        group = result.get("group")
        average = result.get("average")
        count = result.get("count")

        insights.append(
            {
                "type": "minimum",
                "severity": "low",
                "insight": (
                    f"{group} has the lowest average {column} at "
                    f"{_format_number(average)} based on "
                    f"{_format_number(count)} records."
                ),
            }
        )

    # ============================================================
    # CORRELATION
    # ============================================================
    elif operation == "correlation":
        columns = analysis.get("columns", [])
        correlation = analysis.get("result")

        if len(columns) == 2 and correlation is not None:
            first_column = columns[0]
            second_column = columns[1]

            correlation_value = float(correlation)
            absolute_correlation = abs(correlation_value)

            if absolute_correlation < 0.20:
                strength = "very weak"
            elif absolute_correlation < 0.40:
                strength = "weak"
            elif absolute_correlation < 0.60:
                strength = "moderate"
            elif absolute_correlation < 0.80:
                strength = "strong"
            else:
                strength = "very strong"

            if correlation_value > 0:
                direction = "positive"
            elif correlation_value < 0:
                direction = "negative"
            else:
                direction = "no"

            insights.append(
                {
                    "type": "correlation",
                    "severity": "info",
                    "insight": (
                        f"There is a {strength} {direction} relationship "
                        f"between {first_column} and {second_column} "
                        f"(correlation: "
                        f"{_format_number(correlation_value)})."
                    ),
                }
            )

            insights.append(
                {
                    "type": "warning",
                    "severity": "info",
                    "insight": (
                        "Correlation indicates a statistical relationship "
                        "and does not by itself prove causation."
                    ),
                }
            )

    return insights