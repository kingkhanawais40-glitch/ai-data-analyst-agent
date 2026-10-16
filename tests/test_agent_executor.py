
import pandas as pd
import pytest

import backend.agent_executor as executor


def test_successful_step_is_completed(monkeypatch):
    monkeypatch.setattr(
        executor,
        "detect_anomalies",
        lambda dataframe: {
            "success": True,
            "unique_anomalous_records": 2,
        },
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    plan = {
        "success": True,
        "intent": "anomaly_detection",
        "steps": [
            {
                "step": "anomaly_detection",
                "order": 1,
                "reason": "Find unusual records.",
            }
        ],
    }

    result = executor.execute_analysis_plan(
        dataframe,
        "Find unusual usage",
        plan,
    )

    assert result["success"] is True
    assert result["execution_status"] == "completed"
    assert result["completed_count"] == 1
    assert result["failed_count"] == 0
    assert result["steps"][0]["status"] == "completed"
    assert "anomaly_detection" in result["results"]


def test_failed_step_does_not_stop_later_steps(monkeypatch):
    def raise_error(dataframe):
        raise RuntimeError("Simulated anomaly failure")

    monkeypatch.setattr(
        executor,
        "detect_anomalies",
        raise_error,
    )

    monkeypatch.setattr(
        executor,
        "profile_dataframe",
        lambda dataframe: {"rows": len(dataframe)},
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    plan = {
        "success": True,
        "intent": "multi_step_analysis",
        "steps": [
            {
                "step": "anomaly_detection",
                "order": 1,
                "reason": "Find anomalies.",
            },
            {
                "step": "profiling",
                "order": 2,
                "reason": "Profile the dataset.",
            },
        ],
    }

    result = executor.execute_analysis_plan(
        dataframe,
        "Profile and find anomalies",
        plan,
    )

    assert result["execution_status"] == "partially_completed"
    assert result["completed_count"] == 1
    assert result["failed_count"] == 1
    assert result["steps"][0]["status"] == "failed"
    assert result["steps"][1]["status"] == "completed"
    assert result["results"]["profiling"]["rows"] == 3


def test_empty_dataframe_is_rejected():
    with pytest.raises(ValueError, match="empty dataset"):
        executor.execute_analysis_plan(
            pd.DataFrame(),
            "Find anomalies",
            {
                "success": True,
                "steps": [
                    {"step": "anomaly_detection", "order": 1}
                ],
            },
        )


def test_invalid_plan_is_rejected():
    dataframe = pd.DataFrame({"usage": [10, 20]})

    with pytest.raises(ValueError, match="successful analysis plan"):
        executor.execute_analysis_plan(
            dataframe,
            "Find anomalies",
            {"success": False, "steps": []},
        )


def test_unsupported_step_is_reported_as_failed():
    dataframe = pd.DataFrame({"usage": [10, 20]})

    plan = {
        "success": True,
        "intent": "unknown",
        "steps": [
            {
                "step": "unknown_step",
                "order": 1,
                "reason": "Unsupported test step.",
            }
        ],
    }

    result = executor.execute_analysis_plan(
        dataframe,
        "Run an unsupported step",
        plan,
    )

    assert result["execution_status"] == "failed"
    assert result["success"] is False
    assert result["failed_count"] == 1
    assert result["steps"][0]["status"] == "failed"
    assert "Unsupported analysis step" in result["steps"][0]["error"]


def test_failed_business_analysis_does_not_stop_later_steps(monkeypatch):
    def fail_business_analysis(dataframe, question):
        return {
            "success": False,
            "message": "Unsupported business question.",
        }

    monkeypatch.setattr(
        executor,
        "analyze_question",
        fail_business_analysis,
    )

    monkeypatch.setattr(
        executor,
        "profile_dataframe",
        lambda dataframe: {"rows": len(dataframe)},
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    plan = {
        "success": True,
        "intent": "multi_step_analysis",
        "steps": [
            {
                "step": "business_analysis",
                "order": 1,
                "reason": "Answer the business question.",
            },
            {
                "step": "profiling",
                "order": 2,
                "reason": "Summarize the dataset.",
            },
        ],
    }

    result = executor.execute_analysis_plan(
        dataframe,
        "Who is the CEO?",
        plan,
    )

    assert result["execution_status"] == "partially_completed"
    assert result["success"] is True
    assert result["completed_count"] == 1
    assert result["failed_count"] == 1
    assert result["steps"][0]["status"] == "failed"
    assert result["steps"][1]["status"] == "completed"
    assert result["results"]["profiling"]["rows"] == 3


def test_data_quality_and_anomaly_detection_both_execute(monkeypatch):
    executed_steps = []

    def mock_validate(dataframe):
        executed_steps.append("data_quality")
        return {
            "success": True,
            "quality_score": 95,
        }

    def mock_detect_anomalies(dataframe):
        executed_steps.append("anomaly_detection")
        return {
            "success": True,
            "unique_anomalous_records": 3,
        }

    monkeypatch.setattr(
        executor,
        "validate_dataframe",
        mock_validate,
    )
    monkeypatch.setattr(
        executor,
        "detect_anomalies",
        mock_detect_anomalies,
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30, 100]})

    plan = {
        "success": True,
        "intent": "multi_step_analysis",
        "steps": [
            {
                "step": "data_quality",
                "order": 1,
                "reason": "Validate dataset quality.",
            },
            {
                "step": "anomaly_detection",
                "order": 2,
                "reason": "Detect unusual records.",
            },
        ],
    }

    result = executor.execute_analysis_plan(
        dataframe,
        "Check quality and identify anomalies",
        plan,
    )

    assert executed_steps == [
        "data_quality",
        "anomaly_detection",
    ]
    assert result["success"] is True
    assert result["execution_status"] == "completed"
    assert result["step_count"] == 2
    assert result["completed_count"] == 2
    assert result["failed_count"] == 0
    assert all(
        step["status"] == "completed"
        for step in result["steps"]
    )
    assert "data_quality" in result["results"]
    assert "anomaly_detection" in result["results"]


def test_execution_does_not_modify_original_dataframe(monkeypatch):
    def mock_detect_anomalies(dataframe):
        dataframe["temporary_column"] = 999
        return {
            "success": True,
            "unique_anomalous_records": 1,
        }

    monkeypatch.setattr(
        executor,
        "detect_anomalies",
        mock_detect_anomalies,
    )

    dataframe = pd.DataFrame({
        "usage": [10, 20, 30],
    })
    original_dataframe = dataframe.copy(deep=True)

    plan = {
        "success": True,
        "intent": "anomaly_detection",
        "steps": [
            {
                "step": "anomaly_detection",
                "order": 1,
                "reason": "Detect unusual records.",
            }
        ],
    }

    result = executor.execute_analysis_plan(
        dataframe,
        "Find anomalies",
        plan,
    )

    pd.testing.assert_frame_equal(
        dataframe,
        original_dataframe,
    )
    assert result["success"] is True
    assert result["execution_status"] == "completed"
    assert result["completed_count"] == 1
    assert "temporary_column" not in dataframe.columns


def test_all_steps_failing_returns_failed_execution(monkeypatch):
    def raise_quality_error(dataframe):
        raise RuntimeError("Quality validation failed")

    def raise_anomaly_error(dataframe):
        raise RuntimeError("Anomaly detection failed")

    monkeypatch.setattr(
        executor,
        "validate_dataframe",
        raise_quality_error,
    )
    monkeypatch.setattr(
        executor,
        "detect_anomalies",
        raise_anomaly_error,
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    plan = {
        "success": True,
        "intent": "multi_step_analysis",
        "steps": [
            {
                "step": "data_quality",
                "order": 1,
                "reason": "Validate dataset quality.",
            },
            {
                "step": "anomaly_detection",
                "order": 2,
                "reason": "Detect anomalies.",
            },
        ],
    }

    result = executor.execute_analysis_plan(
        dataframe,
        "Check quality and detect anomalies",
        plan,
    )

    assert result["success"] is False
    assert result["execution_status"] == "failed"
    assert result["step_count"] == 2
    assert result["completed_count"] == 0
    assert result["failed_count"] == 2
    assert all(
        step["status"] == "failed"
        for step in result["steps"]
    )
    assert "Quality validation failed" in result["steps"][0]["error"]
    assert "Anomaly detection failed" in result["steps"][1]["error"]
    assert result["results"] == {}


def test_partial_failure_preserves_successful_results(monkeypatch):
    monkeypatch.setattr(
        executor,
        "validate_dataframe",
        lambda dataframe: {
            "success": True,
            "quality_score": 94.53,
        },
    )

    def raise_anomaly_error(dataframe):
        raise RuntimeError("Anomaly detection unavailable")

    monkeypatch.setattr(
        executor,
        "detect_anomalies",
        raise_anomaly_error,
    )

    dataframe = pd.DataFrame({"usage": [10, 20, 30]})

    plan = {
        "success": True,
        "intent": "multi_step_analysis",
        "steps": [
            {
                "step": "data_quality",
                "order": 1,
                "reason": "Validate data quality.",
            },
            {
                "step": "anomaly_detection",
                "order": 2,
                "reason": "Detect anomalies.",
            },
        ],
    }

    result = executor.execute_analysis_plan(
        dataframe,
        "Check quality and detect anomalies",
        plan,
    )

    assert result["success"] is True
    assert result["execution_status"] == "partially_completed"
    assert result["completed_count"] == 1
    assert result["failed_count"] == 1

    assert result["steps"][0]["status"] == "completed"
    assert result["steps"][1]["status"] == "failed"

    assert result["results"]["data_quality"]["quality_score"] == 94.53
    assert "anomaly_detection" not in result["results"]

    assert "Anomaly detection unavailable" in result["steps"][1]["error"]
