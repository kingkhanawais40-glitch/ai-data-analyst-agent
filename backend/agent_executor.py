from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd

from backend.profiler import profile_dataframe
from backend.validator import validate_dataframe
from backend.anomaly_detector import detect_anomalies
from backend.analyzer import analyze_question
from backend.insights import generate_insights
from backend.visualization_agent import analyze_and_visualize


# ============================================================
# AGENT EXECUTION ENGINE
# ============================================================

SUPPORTED_STEPS = {
    "profiling",
    "data_quality",
    "anomaly_detection",
    "business_analysis",
    "visualization",
}

# Supported default query for a comprehensive analysis plan.
COMPREHENSIVE_ANALYSIS_QUESTION = (
    "What is the average consumption by city?"
)


def execute_analysis_plan(
    dataframe: pd.DataFrame,
    question: str,
    plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute the steps selected by analysis_planner.

    Each step receives an individual status and result.
    A failed step does not prevent later steps from running.
    The original dataframe is not intentionally modified.

    For comprehensive analysis, business analysis and visualization
    use a supported default analytical question when the original
    question requests multiple analysis tasks at once.
    """

    # --------------------------------------------------------
    # INPUT VALIDATION
    # --------------------------------------------------------

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")

    if dataframe.empty:
        raise ValueError(
            "Cannot execute analysis on an empty dataset."
        )

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not isinstance(plan, dict) or not plan.get("success"):
        raise ValueError("A successful analysis plan is required.")

    planned_steps = plan.get("steps", [])

    if not isinstance(planned_steps, list) or not planned_steps:
        raise ValueError(
            "The analysis plan contains no executable steps."
        )

    # --------------------------------------------------------
    # EXECUTION INITIALIZATION
    # --------------------------------------------------------

    steps = []
    results = {}

    completed_count = 0
    failed_count = 0

    started_at = datetime.now(timezone.utc).isoformat()

    # Only use the default query for comprehensive plans.
    is_comprehensive = (
        plan.get("intent") == "comprehensive_analysis"
    )

    analysis_question = (
        COMPREHENSIVE_ANALYSIS_QUESTION
        if is_comprehensive
        else question.strip()
    )

    # --------------------------------------------------------
    # EXECUTE EACH PLANNED STEP
    # --------------------------------------------------------

    for planned_step in planned_steps:

        if not isinstance(planned_step, dict):
            step_result = {
                "step": None,
                "order": None,
                "reason": "",
                "status": "failed",
                "result": None,
                "error": "Invalid planned step format.",
            }

            steps.append(step_result)
            failed_count += 1
            continue

        step_name = planned_step.get("step")

        step_result = {
            "step": step_name,
            "order": planned_step.get("order"),
            "reason": planned_step.get("reason", ""),
            "status": "pending",
            "result": None,
            "error": None,
        }

        # ----------------------------------------------------
        # CHECK SUPPORTED STEP
        # ----------------------------------------------------

        if step_name not in SUPPORTED_STEPS:
            step_result["status"] = "failed"
            step_result["error"] = (
                f"Unsupported analysis step: {step_name}"
            )

            steps.append(step_result)
            failed_count += 1
            continue

        step_result["status"] = "running"

        try:
            # ------------------------------------------------
            # 1. DATASET PROFILING
            # ------------------------------------------------

            if step_name == "profiling":
                result = profile_dataframe(
                    dataframe.copy()
                )

            # ------------------------------------------------
            # 2. DATA QUALITY VALIDATION
            # ------------------------------------------------

            elif step_name == "data_quality":
                result = validate_dataframe(
                    dataframe.copy()
                )

            # ------------------------------------------------
            # 3. ANOMALY DETECTION
            # ------------------------------------------------

            elif step_name == "anomaly_detection":
                result = detect_anomalies(
                    dataframe.copy()
                )

            # ------------------------------------------------
            # 4. BUSINESS ANALYSIS
            # ------------------------------------------------

            elif step_name == "business_analysis":
                analysis = analyze_question(
                    dataframe.copy(),
                    analysis_question,
                )

                if (
                    isinstance(analysis, dict)
                    and analysis.get("success") is False
                ):
                    result = {
                        "success": False,
                        "message": analysis.get(
                            "message",
                            "Business analysis failed.",
                        ),
                        "analysis": analysis,
                    }

                else:
                    analysis_data = (
                        analysis.get("analysis", {})
                        if isinstance(analysis, dict)
                        else {}
                    )

                    insights = generate_insights(
                        analysis_data
                    )

                    result = {
                        "success": True,
                        "analysis": analysis,
                        "insights": insights,
                    }

            # ------------------------------------------------
            # 5. VISUALIZATION
            # ------------------------------------------------

            elif step_name == "visualization":
                result = analyze_and_visualize(
                    dataframe.copy(),
                    analysis_question,
                )

            # ------------------------------------------------
            # PROCESS STEP RESULT
            # ------------------------------------------------

            if (
                isinstance(result, dict)
                and result.get("success") is False
            ):
                step_result["status"] = "failed"

                step_result["error"] = result.get(
                    "message",
                    "The analysis step reported failure.",
                )

                step_result["result"] = result

                failed_count += 1

            else:
                step_result["status"] = "completed"
                step_result["result"] = result

                results[step_name] = result
                completed_count += 1

        except Exception as error:
            step_result["status"] = "failed"

            step_result["error"] = (
                f"{type(error).__name__}: {str(error)}"
            )

            failed_count += 1

        # Preserve every attempted step.
        steps.append(step_result)

    # --------------------------------------------------------
    # FINAL EXECUTION STATUS
    # --------------------------------------------------------

    finished_at = datetime.now(timezone.utc).isoformat()

    if failed_count == 0:
        overall_status = "completed"

    elif completed_count > 0:
        overall_status = "partially_completed"

    else:
        overall_status = "failed"

    # --------------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------------

    return {
        "success": completed_count > 0,
        "question": question.strip(),
        "intent": plan.get("intent"),
        "execution_status": overall_status,
        "step_count": len(steps),
        "completed_count": completed_count,
        "failed_count": failed_count,
        "started_at": started_at,
        "finished_at": finished_at,
        "steps": steps,
        "results": results,
    }
