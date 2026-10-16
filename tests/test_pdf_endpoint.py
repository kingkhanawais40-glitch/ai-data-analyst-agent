from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)

NON_EXISTENT_DATASET_ID = 999999999


def test_pdf_endpoint_returns_404_for_missing_dataset():
    response = client.get(
        f"/datasets/{NON_EXISTENT_DATASET_ID}/report/pdf"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found."


def test_pdf_endpoint_returns_valid_pdf(monkeypatch):
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
        def execute(self, query, params=None):
            pass

        def fetchone(self):
            return FakeDataset()

        def fetchall(self):
            return []

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
        Path("fake_test_uploads"),
    )

    monkeypatch.setattr(
        Path,
        "is_file",
        lambda self: True,
    )

    monkeypatch.setattr(
        main_module.pd,
        "read_csv",
        lambda path: pd.DataFrame({"usage": [10, 20, 30]}),
    )

    monkeypatch.setattr(
        main_module,
        "validate_dataframe",
        lambda dataframe: {"summary": {"quality_score": 95}},
    )

    monkeypatch.setattr(
        main_module,
        "detect_anomalies",
        lambda dataframe: {"anomaly_percentage": 0},
    )

    monkeypatch.setattr(
        main_module,
        "generate_dataset_intelligence",
        lambda validation, anomalies: {
            "insights": [],
            "recommendations": [],
        },
    )

    monkeypatch.setattr(
        main_module,
        "generate_pdf_report",
        lambda **kwargs: b"%PDF-1.4\nMock PDF report content",
    )

    response = client.get("/datasets/123/report/pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert response.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="dataset_123_report.pdf"' == (
        response.headers["content-disposition"]
    )
