import re
from typing import Any, Dict


def _normalize_question(question: str) -> str:
    """Normalize whitespace and casing in a user question."""
    return re.sub(r"\s+", " ", question.strip().lower())


def generate_sql(question: str) -> Dict[str, Any]:
    """
    Convert supported natural-language questions into safe,
    deterministic SQL queries.

    This generator only produces predefined SELECT statements.
    """
    if not question or not question.strip():
        return {
            "success": False,
            "message": "Question cannot be empty.",
        }

    normalized = _normalize_question(question)

    # 1. Highest consumption city — check before general city queries.
    if (
        ("highest" in normalized or "maximum" in normalized or "max" in normalized)
        and "consumption" in normalized
        and "city" in normalized
    ):
        return {
            "success": True,
            "intent": "highest_consumption_city",
            "sql": """
                SELECT
                    City,
                    AVG(ThreeMonth_Avg_kWh_Day) AS avg_consumption
                FROM dataset
                WHERE City IS NOT NULL
                GROUP BY City
                ORDER BY avg_consumption DESC
                LIMIT 1
            """.strip(),
        }

    # 2. Lowest consumption city.
    if (
        ("lowest" in normalized or "minimum" in normalized or "min" in normalized)
        and "consumption" in normalized
        and "city" in normalized
    ):
        return {
            "success": True,
            "intent": "lowest_consumption_city",
            "sql": """
                SELECT
                    City,
                    AVG(ThreeMonth_Avg_kWh_Day) AS avg_consumption
                FROM dataset
                WHERE City IS NOT NULL
                GROUP BY City
                ORDER BY avg_consumption ASC
                LIMIT 1
            """.strip(),
        }

    # 3. Average monthly bill.
    if (
        "average" in normalized
        and ("monthly bill" in normalized or "electricity bill" in normalized)
    ):
        return {
            "success": True,
            "intent": "average_monthly_bill",
            "sql": """
                SELECT AVG(Est_Monthly_Bill_PKR) AS average_monthly_bill
                FROM dataset
            """.strip(),
        }

    # 4. Average consumption grouped by city.
    if (
        "average" in normalized
        and "consumption" in normalized
        and ("by city" in normalized or "per city" in normalized or "each city" in normalized)
    ):
        return {
            "success": True,
            "intent": "average_consumption_by_city",
            "sql": """
                SELECT
                    City,
                    AVG(ThreeMonth_Avg_kWh_Day) AS avg_consumption
                FROM dataset
                WHERE City IS NOT NULL
                GROUP BY City
                ORDER BY avg_consumption DESC
            """.strip(),
        }

    # 5. Total consumption grouped by city.
    if (
        ("total" in normalized or "sum" in normalized)
        and "consumption" in normalized
        and ("by city" in normalized or "per city" in normalized or "each city" in normalized)
    ):
        return {
            "success": True,
            "intent": "total_consumption_by_city",
            "sql": """
                SELECT
                    City,
                    SUM(ThreeMonth_Avg_kWh_Day) AS total_consumption
                FROM dataset
                WHERE City IS NOT NULL
                GROUP BY City
                ORDER BY total_consumption DESC
            """.strip(),
        }

    # 6. Average consumption overall.
    if "average" in normalized and "consumption" in normalized:
        return {
            "success": True,
            "intent": "average_consumption",
            "sql": """
                SELECT
                    AVG(ThreeMonth_Avg_kWh_Day) AS average_consumption
                FROM dataset
            """.strip(),
        }

    return {
        "success": False,
        "message": (
            "I could not determine a supported SQL operation "
            "from this question yet."
        ),
    }