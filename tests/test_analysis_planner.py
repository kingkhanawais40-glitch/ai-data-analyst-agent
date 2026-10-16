
from backend.analysis_planner import plan_analysis


def test_empty_question_is_rejected():
    result = plan_analysis("   ")

    assert result["success"] is False
    assert result["message"] == "Question cannot be empty."
    assert result["steps"] == []


def test_chart_and_sales_question_plans_business_analysis_and_visualization():
    result = plan_analysis("Show a chart of monthly sales")

    assert result["success"] is True
    assert result["intent"] == "multi_step_analysis"

    step_names = [step["step"] for step in result["steps"]]

    assert "business_analysis" in step_names
    assert "visualization" in step_names
    assert result["step_count"] == len(result["steps"])


def test_missing_values_and_anomalies_select_both_steps():
    result = plan_analysis(
        "Find missing values and detect anomalies"
    )

    assert result["success"] is True

    step_names = [step["step"] for step in result["steps"]]

    assert "data_quality" in step_names
    assert "anomaly_detection" in step_names
    assert result["step_count"] == len(result["steps"])


def test_plan_only_does_not_claim_execution():
    result = plan_analysis("Show a chart of monthly sales")

    assert result["execution_mode"] == "plan_only"


def test_steps_have_order_and_reason():
    result = plan_analysis("Find missing values and detect anomalies")

    assert result["success"] is True

    for step in result["steps"]:
        assert isinstance(step["order"], int)
        assert step["order"] > 0
        assert isinstance(step["reason"], str)
        assert step["reason"].strip()

def test_check_quality_and_identify_anomalies_selects_both_steps():
    result = plan_analysis("Check quality and identify anomalies")

    assert result["success"] is True

    step_names = [step["step"] for step in result["steps"]]

    assert "data_quality" in step_names
    assert "anomaly_detection" in step_names
    assert result["step_count"] == 2
