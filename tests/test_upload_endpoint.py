
import base64
import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

import backend.main as main_module


client = TestClient(main_module.app)

TEST_SECRET = "test-upload-registration-secret-1234567890"


def make_registration_token(
    monkeypatch,
    pathname="datasets/uploads/test.csv",
    file_name="test.csv",
    file_size=30,
    content_type="text/csv",
    expires_at=None,
):
    monkeypatch.setenv("UPLOAD_REGISTRATION_SECRET", TEST_SECRET)

    payload = {
        "pathname": pathname,
        "fileName": file_name,
        "fileSize": file_size,
        "contentType": content_type,
        "expiresAt": (
            expires_at
            if expires_at is not None
            else int(time.time() * 1000) + 60_000
        ),
    }

    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("ascii").rstrip("=")

    signature = hmac.new(
        TEST_SECRET.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()

    encoded_signature = base64.urlsafe_b64encode(
        signature
    ).decode("ascii").rstrip("=")

    return f"{encoded_payload}.{encoded_signature}"


def registration_payload(
    monkeypatch,
    pathname="datasets/uploads/test.csv",
    file_name="test.csv",
    file_size=30,
    content_type="text/csv",
    expires_at=None,
):
    return {
        "pathname": pathname,
        "fileName": file_name,
        "fileSize": file_size,
        "contentType": content_type,
        "registrationToken": make_registration_token(
            monkeypatch,
            pathname=pathname,
            file_name=file_name,
            file_size=file_size,
            content_type=content_type,
            expires_at=expires_at,
        ),
    }


class FakeCursor:
    def __init__(self, fail_on_execute=False):
        self.lastrowid = 456
        self.fail_on_execute = fail_on_execute
        self.query = None
        self.params = None

    def execute(self, query, params):
        if self.fail_on_execute:
            raise RuntimeError("Simulated database failure")

        self.query = query
        self.params = params


class FakeConnection:
    def __init__(self, fail_on_execute=False):
        self.fake_cursor = FakeCursor(fail_on_execute)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_upload_csv_saves_blob_pathname_to_database(monkeypatch):
    connection = FakeConnection()
    uploaded = {}

    def fake_upload_blob(pathname, content, content_type):
        uploaded["pathname"] = pathname
        uploaded["content"] = content
        uploaded["content_type"] = content_type
        return "datasets/test-unique.csv"

    monkeypatch.setattr(
        main_module,
        "upload_blob_bytes",
        fake_upload_blob,
    )
    monkeypatch.setattr(
        main_module,
        "get_connection",
        lambda: connection,
    )

    response = client.post(
        "/upload",
        files={
            "file": (
                "test.csv",
                b"city,usage\nKarachi,100\nLahore,200\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["dataset_id"] == 456
    assert data["file_name"] == "test.csv"
    assert data["rows"] == 2
    assert data["columns"] == 2

    assert uploaded["pathname"] == "datasets/test.csv"
    assert uploaded["content_type"] == "text/csv"
    assert b"Karachi" in uploaded["content"]

    assert "blob_pathname" in connection.fake_cursor.query
    assert connection.fake_cursor.params[-1] == "datasets/test-unique.csv"
    assert connection.committed is True
    assert connection.closed is True


def test_upload_rejects_unsupported_extension(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob upload should not be called.")

    monkeypatch.setattr(
        main_module,
        "upload_blob_bytes",
        fail_if_called,
    )

    response = client.post(
        "/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only CSV, XLSX, and XLS files are supported."
    )


def test_upload_rejects_empty_file(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob upload should not be called.")

    monkeypatch.setattr(
        main_module,
        "upload_blob_bytes",
        fail_if_called,
    )

    response = client.post(
        "/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty."


def test_upload_cleans_up_blob_if_database_insert_fails(monkeypatch):
    connection = FakeConnection(fail_on_execute=True)
    deleted = []

    monkeypatch.setattr(
        main_module,
        "upload_blob_bytes",
        lambda *args, **kwargs: "datasets/test-unique.csv",
    )
    monkeypatch.setattr(
        main_module,
        "delete_blob_object",
        lambda pathname: deleted.append(pathname),
    )
    monkeypatch.setattr(
        main_module,
        "get_connection",
        lambda: connection,
    )

    response = client.post(
        "/upload",
        files={
            "file": (
                "test.csv",
                b"city,usage\nKarachi,100\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Dataset upload failed: Simulated database failure"
    )

    assert deleted == ["datasets/test-unique.csv"]
    assert connection.rolled_back is True
    assert connection.committed is False
    assert connection.closed is True


def test_blob_registration_rejects_invalid_path_before_blob_access(
    monkeypatch,
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob download should not be called.")

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fail_if_called,
    )

    payload = registration_payload(
        monkeypatch,
        pathname="other-folder/test.csv",
        file_name="test.csv",
        file_size=20,
        content_type="text/csv",
    )

    response = client.post("/upload/register", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid uploaded file reference."


def test_blob_registration_rejects_unsupported_extension(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob download should not be called.")

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fail_if_called,
    )

    payload = registration_payload(
        monkeypatch,
        pathname="datasets/uploads/test.txt",
        file_name="test.txt",
        file_size=20,
        content_type="text/plain",
    )

    response = client.post("/upload/register", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only CSV, XLSX, and XLS files are supported."
    )


def test_blob_registration_rejects_oversized_file_before_blob_access(
    monkeypatch,
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob download should not be called.")

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fail_if_called,
    )

    oversized_size = 26 * 1024 * 1024

    payload = registration_payload(
        monkeypatch,
        pathname="datasets/uploads/test.csv",
        file_name="test.csv",
        file_size=oversized_size,
        content_type="text/csv",
    )

    response = client.post("/upload/register", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "File size must be between 1 byte and 25 MB."
    )


def test_blob_registration_saves_dataset_to_database(monkeypatch):
    connection = FakeConnection()
    csv_content = b"city,usage\nKarachi,100\nLahore,200\n"
    downloaded = []

    def fake_download_blob(pathname):
        downloaded.append(pathname)
        return csv_content

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fake_download_blob,
    )
    monkeypatch.setattr(
        main_module,
        "get_connection",
        lambda: connection,
    )

    payload = registration_payload(
        monkeypatch,
        pathname="datasets/uploads/test.csv",
        file_name="test.csv",
        file_size=len(csv_content),
        content_type="text/csv",
    )

    response = client.post("/upload/register", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Dataset uploaded successfully."
    assert data["dataset_id"] == 456
    assert data["file_name"] == "test.csv"
    assert data["file_type"] == "csv"
    assert data["rows"] == 2
    assert data["columns"] == 2
    assert data["column_names"] == ["city", "usage"]

    assert downloaded == ["datasets/uploads/test.csv"]
    assert "blob_pathname" in connection.fake_cursor.query
    assert connection.fake_cursor.params[-1] == "datasets/uploads/test.csv"
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True


def test_blob_registration_rejects_missing_token(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob download must not be called.")

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fail_if_called,
    )

    response = client.post(
        "/upload/register",
        json={
            "pathname": "datasets/uploads/test.csv",
            "fileName": "test.csv",
            "fileSize": 30,
            "contentType": "text/csv",
        },
    )

    assert response.status_code == 422


def test_blob_registration_rejects_tampered_token(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob download must not be called.")

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fail_if_called,
    )

    token = make_registration_token(monkeypatch)
    token = token[:-1] + ("A" if token[-1] != "A" else "B")

    response = client.post(
        "/upload/register",
        json={
            "pathname": "datasets/uploads/test.csv",
            "fileName": "test.csv",
            "fileSize": 30,
            "contentType": "text/csv",
            "registrationToken": token,
        },
    )

    assert response.status_code == 403


def test_blob_registration_rejects_expired_token(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob download must not be called.")

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fail_if_called,
    )

    token = make_registration_token(
        monkeypatch,
        expires_at=int(time.time() * 1000) - 60_000,
    )

    response = client.post(
        "/upload/register",
        json={
            "pathname": "datasets/uploads/test.csv",
            "fileName": "test.csv",
            "fileSize": 30,
            "contentType": "text/csv",
            "registrationToken": token,
        },
    )

    assert response.status_code == 403


def test_blob_registration_rejects_token_for_different_path(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Blob download must not be called.")

    monkeypatch.setattr(
        main_module,
        "download_blob_bytes",
        fail_if_called,
    )

    token = make_registration_token(
        monkeypatch,
        pathname="datasets/uploads/another.csv",
        file_name="test.csv",
        file_size=30,
        content_type="text/csv",
    )

    response = client.post(
        "/upload/register",
        json={
            "pathname": "datasets/uploads/test.csv",
            "fileName": "test.csv",
            "fileSize": 30,
            "contentType": "text/csv",
            "registrationToken": token,
        },
    )

    assert response.status_code == 403
