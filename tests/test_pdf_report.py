from backend.pdf_report import generate_pdf_report


def test_generate_pdf_report_returns_valid_pdf():
    """PDF report should generate successfully with sample analysis data."""

    dataset = {
        "id": 1,
        "name": "Pakistan Power Consumption",
        "file_name": "power_consumption.xlsx",
        "rows": 50000,
        "columns": 35,
    }

    validation = {
        "summary": {
            "quality_score": 94.53,
            "quality_label": "Excellent",
            "total_missing_values": 12880,
            "duplicate_rows": 0,
        }
    }

    anomalies = {
        "anomalies": {
            "anomalous_records": 7383,
            "anomaly_percentage": 14.77,
            "affected_columns": 10,
            "total_outlier_occurrences": 25206,
        }
    }

    intelligence = {
        "intelligence": {
            "insights": [
                "The dataset has a high overall quality score.",
                "Some columns contain missing values.",
            ],
            "recommendations": [
                "Review columns with missing values.",
                "Investigate detected anomalies.",
            ],
        }
    }

    historical = {
        "has_comparison": True,
        "health_change": 1.25,
        "anomaly_change": -0.50,
        "health_trend": "improving",
        "anomaly_trend": "improving",
        "history": [],
    }

    pdf_bytes = generate_pdf_report(
        dataset=dataset,
        validation=validation,
        anomalies=anomalies,
        intelligence=intelligence,
        historical=historical,
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


def test_generate_pdf_report_without_historical_comparison():
    """PDF report should generate even without historical data."""

    dataset = {
        "id": 2,
        "name": "Test Dataset",
        "file_name": "test_dataset.csv",
        "rows": 100,
        "columns": 5,
    }

    pdf_bytes = generate_pdf_report(dataset=dataset)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000
