
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)

# Use an ID that should not exist in the project's database.
NON_EXISTENT_DATASET_ID = 999999999


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "running"
    assert data["version"] == "1.0.0"
    assert "AI Data Analyst" in data["message"]


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_profile_returns_404_for_missing_dataset():
    response = client.get(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/profile"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found."


def test_history_returns_404_for_missing_dataset():
    response = client.get(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/history"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found."


def test_business_question_returns_404_for_missing_dataset():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/business-question",
        json={
            "question": "Which city has the highest power consumption?"
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found."


def test_analyze_rejects_empty_question():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/analyze",
        json={"question": ""},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."


def test_visualize_rejects_empty_question():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/visualize",
        json={"question": ""},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."


def test_plan_endpoint_returns_404_for_missing_dataset():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/plan",
        json={"question": "Show a chart of monthly sales"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found."


def test_plan_endpoint_rejects_empty_question():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/plan",
        json={"question": ""},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."


def test_plan_endpoint_rejects_whitespace_question():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/plan",
        json={"question": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."


def test_execute_endpoint_returns_404_for_missing_dataset():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/execute",
        json={"question": "Find unusual power usage"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found."


def test_execute_endpoint_rejects_empty_question():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/execute",
        json={"question": ""},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."


def test_execute_endpoint_rejects_whitespace_question():
    response = client.post(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/execute",
        json={"question": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."



def test_execute_endpoint_returns_successful_execution(monkeypatch):
    import pandas as pd

    import backend.main as main_module

    class FakeDataset:
        def __init__(self):
            self.data = {
                "id": 123,
                "name": "Test Dataset",
                "file_name": "test_dataset.csv",
                "file_type": "csv",
                "row_count": 3,
                "column_count": 1,
            }

        def __getitem__(self, key):
            return self.data[key]

    class FakeCursor:
        def execute(self, query, params):
            pass

        def fetchone(self):
            return FakeDataset()

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(
        main_module,
        "get_connection",
        lambda: FakeConnection(),
    )

    monkeypatch.setattr(
        main_module,
        "UPLOAD_DIR",
        __import__("pathlib").Path("fake_test_uploads"),
    )

    monkeypatch.setattr(
    main_module.Path,
    "is_file",
    lambda self: True,
)

    monkeypatch.setattr(
        main_module.pd,
        "read_csv",
        lambda path: pd.DataFrame({"usage": [10, 20, 30]}),
    )

    def fake_execute_analysis_plan(dataframe, question, plan):
        assert len(dataframe) == 3
        assert question == "Check quality and identify anomalies"

        return {
            "success": True,
            "question": question,
            "intent": "data_quality_and_anomaly_detection",
            "execution_status": "completed",
            "step_count": 2,
            "completed_count": 2,
            "failed_count": 0,
            "steps": [
                {
                    "step": "data_quality",
                    "status": "completed",
                    "result": {
                        "quality_score": 94.53,
                        "missing_values": 0,
                    },
                },
                {
                    "step": "anomaly_detection",
                    "status": "completed",
                    "result": {
                        "unique_anomalous_records": 1,
                    },
                },
            ],
            "results": {
                "data_quality": {
                    "quality_score": 94.53,
                    "missing_values": 0,
                },
                "anomaly_detection": {
                    "unique_anomalous_records": 1,
                },
            },
        }

    monkeypatch.setattr(
        main_module,
        "execute_analysis_plan",
        fake_execute_analysis_plan,
    )

    response = client.post(
        "/datasets/123/execute",
        json={
            "question": "Check quality and identify anomalies"
        },
    )

    assert response.status_code == 200

    data = response.json()
    execution = data["execution"]

    assert data["success"] is True
    assert data["dataset"]["id"] == 123
    assert data["dataset"]["rows"] == 3
    assert data["dataset"]["columns"] == 1
    assert data["question"] == "Check quality and identify anomalies"
    assert data["plan"]["success"] is True

    assert execution["execution_status"] == "completed"
    assert execution["step_count"] == 2
    assert execution["completed_count"] == 2
    assert execution["failed_count"] == 0

    assert len(execution["steps"]) == 2
    assert execution["steps"][0]["step"] == "data_quality"
    assert execution["steps"][0]["status"] == "completed"
    assert execution["steps"][1]["step"] == "anomaly_detection"
    assert execution["steps"][1]["status"] == "completed"

    assert execution["results"]["data_quality"]["quality_score"] == 94.53
    assert execution["results"]["data_quality"]["missing_values"] == 0
    assert (
        execution["results"]["anomaly_detection"]
        ["unique_anomalous_records"]
        == 1
    )


def test_execute_endpoint_preserves_partial_failure(monkeypatch):
    import pandas as pd

    import backend.main as main_module

    class FakeDataset:
        data = {
            "id": 123,
            "name": "Test Dataset",
            "file_name": "test_dataset.csv",
            "file_type": "csv",
            "row_count": 3,
            "column_count": 1,
        }

        def __getitem__(self, key):
            return self.data[key]

    class FakeCursor:
        def execute(self, query, params):
            pass

        def fetchone(self):
            return FakeDataset()

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(
        main_module,
        "get_connection",
        lambda: FakeConnection(),
    )
    monkeypatch.setattr(
        main_module,
        "UPLOAD_DIR",
        __import__("pathlib").Path("fake_test_uploads"),
    )
    monkeypatch.setattr(
    main_module.Path,
    "is_file",
    lambda self: True,
)

    monkeypatch.setattr(
        main_module.pd,
        "read_csv",
        lambda path: pd.DataFrame({"usage": [10, 20, 30]}),
    )

    def fake_execute_analysis_plan(dataframe, question, plan):
        return {
            "success": True,
            "question": question,
            "intent": "data_quality_and_anomaly_detection",
            "execution_status": "partially_completed",
            "step_count": 2,
            "completed_count": 1,
            "failed_count": 1,
            "steps": [
                {
                    "step": "data_quality",
                    "status": "completed",
                    "result": {"quality_score": 94.53},
                },
                {
                    "step": "anomaly_detection",
                    "status": "failed",
                    "error": "Anomaly detection failed.",
                },
            ],
            "results": {
                "data_quality": {"quality_score": 94.53},
            },
        }

    monkeypatch.setattr(
        main_module,
        "execute_analysis_plan",
        fake_execute_analysis_plan,
    )

    response = client.post(
        "/datasets/123/execute",
        json={
            "question": "Check quality and identify anomalies"
        },
    )

    assert response.status_code == 200

    data = response.json()
    execution = data["execution"]

    assert execution["execution_status"] == "partially_completed"
    assert execution["step_count"] == 2
    assert execution["completed_count"] == 1
    assert execution["failed_count"] == 1

    assert execution["steps"][0]["status"] == "completed"
    assert execution["steps"][1]["status"] == "failed"
    assert execution["steps"][1]["error"] == "Anomaly detection failed."

    # The successful result must not be lost.
    assert execution["results"]["data_quality"]["quality_score"] == 94.53
    assert "anomaly_detection" not in execution["results"]


def test_insights_endpoint_returns_404_for_missing_dataset():
    response = client.get(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/insights"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found."


def test_insights_endpoint_returns_saved_insights_and_closes_connection(
    monkeypatch,
):
    import backend.main as main_module

    class FakeCursor:
        def __init__(self):
            self.executed_queries = []
            self.fetch_count = 0

        def execute(self, query, params):
            self.executed_queries.append((query, params))

        def fetchone(self):
            self.fetch_count += 1

            if self.fetch_count == 1:
                return {"id": 123}

            return None

        def fetchall(self):
            return [
                {
                    "id": 7,
                    "dataset_id": 123,
                    "insight": "Karachi has the highest average usage.",
                    "severity": "info",
                    "created_at": "2026-10-13 10:00:00",
                },
                {
                    "id": 6,
                    "dataset_id": 123,
                    "insight": "Two cities were compared.",
                    "severity": "info",
                    "created_at": "2026-10-13 09:00:00",
                },
            ]

    class FakeConnection:
        def __init__(self):
            self.fake_cursor = FakeCursor()
            self.closed = False

        def cursor(self):
            return self.fake_cursor

        def close(self):
            self.closed = True

    fake_connection = FakeConnection()

    monkeypatch.setattr(
        main_module,
        "get_connection",
        lambda: fake_connection,
    )

    response = client.get("/datasets/123/insights")

    assert response.status_code == 200

    data = response.json()

    assert data["dataset_id"] == 123
    assert len(data["insights"]) == 2
    assert data["insights"][0]["id"] == 7
    assert (
        data["insights"][0]["insight"]
        == "Karachi has the highest average usage."
    )
    assert data["insights"][1]["id"] == 6
    assert fake_connection.closed is True
