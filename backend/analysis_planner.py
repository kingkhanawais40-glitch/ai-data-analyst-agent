
import re
from typing import Any, Dict, List


def plan_analysis(question: str) -> Dict[str, Any]:
    """
    Build a deterministic analysis plan from a user's question.

    This function selects analysis steps only.
    It does not execute analysis, run SQL, or modify the dataset.
    """

    if not isinstance(question, str) or not question.strip():
        return {
            "success": False,
            "message": "Question cannot be empty.",
            "intent": None,
            "steps": [],
        }

    normalized = re.sub(r"\s+", " ", question.strip().lower())

    step_reasons: Dict[str, str] = {}

    def add_step(step: str, reason: str) -> None:
        if step not in step_reasons:
            step_reasons[step] = reason

    # Comprehensive analysis requests.
    comprehensive_terms = (
        "full analysis",
        "complete analysis",
        "comprehensive analysis",
        "analyze everything",
        "analyse everything",
        "overall analysis",
        "analyze the entire dataset",
        "analyse the entire dataset",
        "analyze all data",
        "analyse all data",
        "complete dataset analysis",
        "full dataset analysis",
    )

    is_comprehensive = any(
        term in normalized
        for term in comprehensive_terms
    )

    if is_comprehensive:
        add_step(
            "profiling",
            "Understand dataset structure and statistics.",
        )
        add_step(
            "data_quality",
            "Evaluate missing values, duplicates, and data quality.",
        )
        add_step(
            "anomaly_detection",
            "Identify unusual records and outliers.",
        )
        add_step(
            "business_analysis",
            "Extract useful findings from the dataset.",
        )
        add_step(
            "visualization",
            "Prepare visual representations of relevant findings.",
        )

    else:
        # --------------------------------------------------
        # 1. DATASET PROFILING
        # --------------------------------------------------
        profiling_terms = (
            "profile",
            "profiling",
            "dataset overview",
            "data overview",
            "describe dataset",
            "summary statistics",
            "dataset summary",
            "column types",
            "dataset structure",
            "data distribution",
            "explore dataset",
            "explore data",
            "dataset information",
            "data statistics",
        )

        if any(term in normalized for term in profiling_terms):
            add_step(
                "profiling",
                "Inspect dataset structure and descriptive statistics.",
            )

        # --------------------------------------------------
        # 2. DATA QUALITY
        # --------------------------------------------------
        quality_terms = (
            "data quality",
            "dataset quality",
            "check quality",
            "check the quality",
            "missing values",
            "missing data",
            "null values",
            "nulls",
            "duplicate",
            "duplicates",
            "validate",
            "validation",
            "quality score",
            "data cleaning",
            "incomplete data",
            "invalid values",
            "empty values",
            "data errors",
            "data issues",
        )

        if any(term in normalized for term in quality_terms):
            add_step(
                "data_quality",
                "Check data quality and potential data issues.",
            )

        # --------------------------------------------------
        # 3. ANOMALY DETECTION
        # --------------------------------------------------
        anomaly_terms = (
            "anomal",
            "outlier",
            "abnormal",
            "unusual",
            "irregular",
            "unexpected values",
            "unexpected records",
            "detect exceptions",
            "anomaly detection",
            "outlier detection",
            "abnormal records",
            "abnormal values",
            "suspicious values",
        )

        if any(term in normalized for term in anomaly_terms):
            add_step(
                "anomaly_detection",
                "Investigate unusual records and statistical outliers.",
            )

        # --------------------------------------------------
        # 4. VISUALIZATION
        # --------------------------------------------------
        visualization_terms = (
            "chart",
            "charts",
            "graph",
            "graphs",
            "plot",
            "plots",
            "visualize",
            "visualise",
            "visualization",
            "visualisation",
            "show trend",
            "trend chart",
            "draw",
            "visual representation",
            "line chart",
            "bar chart",
            "pie chart",
            "scatter plot",
            "histogram",
        )

        if any(term in normalized for term in visualization_terms):
            add_step(
                "visualization",
                "Select an appropriate visual for the requested analysis.",
            )

        # --------------------------------------------------
        # 5. BUSINESS AND NUMERICAL ANALYSIS
        # --------------------------------------------------
        business_terms = (
            "total",
            "average",
            "mean",
            "median",
            "maximum",
            "minimum",
            "highest",
            "lowest",
            "top ",
            "count",
            "compare",
            "comparison",
            "correlation",
            "relationship",
            "which ",
            "how many",
            "how much",
            "by city",
            "by month",
            "by year",
            "business",
            "sales",
            "revenue",
            "profit",
            "consumption",
            "calculate",
            "percentage",
            "increase",
            "decrease",
            "growth",
            "trend",
            "rank",
            "ranking",
            "distribution",
            "bill",
            "cost",
            "amount",
        )

        if any(term in normalized for term in business_terms):
            add_step(
                "business_analysis",
                "Answer the requested business or numerical question.",
            )

        # --------------------------------------------------
        # 6. FALLBACK FOR GENERAL QUESTIONS
        # --------------------------------------------------
        if not step_reasons:
            add_step(
                "business_analysis",
                "Use the existing question-analysis workflow for this request.",
            )

    # Keep the execution order consistent.
    execution_order = [
        "profiling",
        "data_quality",
        "anomaly_detection",
        "business_analysis",
        "visualization",
    ]

    steps: List[Dict[str, Any]] = [
        {
            "step": name,
            "order": index,
            "reason": step_reasons[name],
        }
        for index, name in enumerate(execution_order, start=1)
        if name in step_reasons
    ]

    # Determine the plan intent.
    if is_comprehensive:
        intent = "comprehensive_analysis"
    elif len(steps) > 1:
        intent = "multi_step_analysis"
    else:
        intent = steps[0]["step"]

    return {
        "success": True,
        "question": question.strip(),
        "intent": intent,
        "steps": steps,
        "step_count": len(steps),
        "execution_mode": "plan_only",
    }
