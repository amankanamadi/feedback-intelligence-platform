import pytest

from app.core.config import get_settings


@pytest.fixture
def attachments_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "attachments_dir", str(tmp_path))
    return tmp_path


def _create_feedback(client) -> int:
    response = client.post("/feedback", json={"raw_text": "Cannot export report to PDF."})
    return response.json()["id"]


def test_upload_attachment_succeeds(client, mock_ai, attachments_dir):
    feedback_id = _create_feedback(client)

    response = client.post(
        f"/feedback/{feedback_id}/attachments",
        files={"files": ("screenshot.png", b"\x89PNG fake bytes", "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["filename"] == "screenshot.png"
    assert body[0]["content_type"] == "image/png"
    assert body[0]["size_bytes"] == len(b"\x89PNG fake bytes")


def test_upload_attachment_for_missing_feedback_returns_404(client, mock_ai, attachments_dir):
    response = client.post(
        "/feedback/999999/attachments",
        files={"files": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 404


def test_upload_attachment_rejects_disallowed_extension(client, mock_ai, attachments_dir):
    feedback_id = _create_feedback(client)

    response = client.post(
        f"/feedback/{feedback_id}/attachments",
        files={"files": ("script.exe", b"MZ fake binary", "application/octet-stream")},
    )

    assert response.status_code == 422


def test_upload_attachment_rejects_oversized_file(client, mock_ai, attachments_dir, monkeypatch):
    monkeypatch.setattr(get_settings(), "attachment_max_size_bytes", 5)
    feedback_id = _create_feedback(client)

    response = client.post(
        f"/feedback/{feedback_id}/attachments",
        files={"files": ("notes.txt", b"this is definitely more than five bytes", "text/plain")},
    )

    assert response.status_code == 413


def test_upload_attachment_rejects_too_many_files(client, mock_ai, attachments_dir, monkeypatch):
    monkeypatch.setattr(get_settings(), "attachment_max_files_per_upload", 2)
    feedback_id = _create_feedback(client)

    response = client.post(
        f"/feedback/{feedback_id}/attachments",
        files=[
            ("files", ("a.txt", b"a", "text/plain")),
            ("files", ("b.txt", b"b", "text/plain")),
            ("files", ("c.txt", b"c", "text/plain")),
        ],
    )

    assert response.status_code == 422


def test_upload_partial_failure_does_not_persist_any_file(client, mock_ai, attachments_dir):
    """If one file in a multi-file upload is invalid, none of the batch
    should be written or recorded - not a partial success."""
    feedback_id = _create_feedback(client)

    response = client.post(
        f"/feedback/{feedback_id}/attachments",
        files=[
            ("files", ("good.txt", b"fine", "text/plain")),
            ("files", ("bad.exe", b"nope", "application/octet-stream")),
        ],
    )

    assert response.status_code == 422
    detail = client.get(f"/feedback/{feedback_id}").json()
    assert detail["attachments"] == []


def test_download_attachment_round_trips_bytes(client, mock_ai, attachments_dir):
    feedback_id = _create_feedback(client)
    content = b"the quick brown fox"

    upload = client.post(
        f"/feedback/{feedback_id}/attachments",
        files={"files": ("notes.txt", content, "text/plain")},
    )
    attachment_id = upload.json()[0]["id"]

    download = client.get(f"/attachments/{attachment_id}/download")

    assert download.status_code == 200
    assert download.content == content


def test_download_missing_attachment_returns_404(client, mock_ai, attachments_dir):
    response = client.get("/attachments/999999/download")

    assert response.status_code == 404


def test_malicious_filename_does_not_escape_attachments_dir(client, mock_ai, attachments_dir, db_session):
    from app.database import crud

    feedback_id = _create_feedback(client)

    response = client.post(
        f"/feedback/{feedback_id}/attachments",
        files={"files": ("../../../etc/passwd.txt", b"malicious", "text/plain")},
    )

    assert response.status_code == 201
    attachment = crud.get_attachment(db_session, response.json()[0]["id"])

    assert str(attachments_dir) in attachment.storage_path
    assert ".." not in attachment.storage_path


def test_feedback_detail_includes_attachments(client, mock_ai, attachments_dir):
    feedback_id = _create_feedback(client)
    client.post(
        f"/feedback/{feedback_id}/attachments",
        files={"files": ("notes.txt", b"hello", "text/plain")},
    )

    response = client.get(f"/feedback/{feedback_id}")

    assert response.status_code == 200
    attachments = response.json()["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "notes.txt"
