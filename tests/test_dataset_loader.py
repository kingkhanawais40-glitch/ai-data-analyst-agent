import pandas as pd
import pytest

import backend.main as main_module


class FakeDataset:
    def __init__(self, values):
        self.values = values

    def __getitem__(self, key):
        return self.values[key]


def test_load_csv_from_blob(monkeypatch):
    csv_content = b"city,usage\nKarachi,100\nLahore,200\n"

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        lambda pathname: csv_content,
    )

    dataset = FakeDataset(
        {
            "blob_pathname": "datasets/test.csv",
            "file_name": "test.csv",
            "file_type": "csv",
        }
    )

    dataframe = main_module.load_dataset_dataframe(dataset)

    assert dataframe.shape == (2, 2)
    assert dataframe["city"].tolist() == ["Karachi", "Lahore"]
    assert dataframe["usage"].tolist() == [100, 200]


def test_load_excel_from_blob(monkeypatch):
    import io

    buffer = io.BytesIO()

    pd.DataFrame(
        {"city": ["Karachi", "Lahore"], "usage": [100, 200]}
    ).to_excel(buffer, index=False)

    excel_content = buffer.getvalue()

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        lambda pathname: excel_content,
    )

    dataset = FakeDataset(
        {
            "blob_pathname": "datasets/test.xlsx",
            "file_name": "test.xlsx",
            "file_type": "xlsx",
        }
    )

    dataframe = main_module.load_dataset_dataframe(dataset)

    assert dataframe.shape == (2, 2)
    assert dataframe["city"].tolist() == ["Karachi", "Lahore"]


def test_load_local_dataset_when_blob_path_is_empty(monkeypatch, tmp_path):
    csv_path = tmp_path / "legacy.csv"
    csv_path.write_text(
        "city,usage\nKarachi,100\nLahore,200\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(main_module, "UPLOAD_DIR", tmp_path)

    def fail_if_blob_called(_pathname):
        pytest.fail("Blob should not be called for a legacy local dataset.")

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fail_if_blob_called,
    )

    dataset = FakeDataset(
        {
            "blob_pathname": None,
            "file_name": "legacy.csv",
            "file_type": "csv",
        }
    )

    dataframe = main_module.load_dataset_dataframe(dataset)

    assert dataframe.shape == (2, 2)
    assert dataframe["city"].tolist() == ["Karachi", "Lahore"]


def test_load_dataset_returns_404_for_missing_local_file(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "UPLOAD_DIR", tmp_path)

    dataset = FakeDataset(
        {
            "blob_pathname": None,
            "file_name": "missing.csv",
            "file_type": "csv",
        }
    )

    with pytest.raises(main_module.HTTPException) as error:
        main_module.load_dataset_dataframe(dataset)

    assert error.value.status_code == 404
    assert error.value.detail == "Dataset file not found."