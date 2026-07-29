import csv
import io


def test_export_csv_has_header_row_when_empty(admin_client, mock_ai):
    response = admin_client.get("/feedback/export/csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][:3] == ["id", "raw_text", "main_category"]
    assert len(rows) == 1  # header only, no data rows


def test_export_csv_includes_submitted_feedback(admin_client, mock_ai):
    admin_client.post("/feedback", json={"raw_text": "Dashboard is slow.", "source": "Web Form", "product": "Reporting"})

    response = admin_client.get("/feedback/export/csv")

    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 2
    header, data = rows
    row = dict(zip(header, data))
    assert row["raw_text"] == "Dashboard is slow."
    assert row["source"] == "Web Form"
    assert row["product"] == "Reporting"
    assert row["main_category"] == "Incident"


def test_export_csv_respects_filters(admin_client, mock_ai):
    admin_client.post("/feedback", json={"raw_text": "Via email.", "source": "Email"})
    admin_client.post("/feedback", json={"raw_text": "Via web form.", "source": "Web Form"})

    response = admin_client.get("/feedback/export/csv", params={"source": "Email"})

    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 2
    assert rows[1][1] == "Via email."


def test_export_csv_joins_themes_and_includes_attachment_count(admin_client, mock_ai):
    created = admin_client.post("/feedback", json={"raw_text": "Dashboard is slow."}).json()
    admin_client.post(
        f"/feedback/{created['id']}/attachments",
        files={"files": ("notes.txt", b"hello", "text/plain")},
    )

    response = admin_client.get("/feedback/export/csv")

    rows = list(csv.reader(io.StringIO(response.text)))
    header, data = rows
    row = dict(zip(header, data))
    assert row["themes"] == "Slow Dashboard; Performance"
    assert row["attachment_count"] == "1"


def test_export_pdf_returns_valid_pdf_bytes(admin_client, mock_ai):
    admin_client.post("/feedback", json={"raw_text": "Dashboard is slow."})

    response = admin_client.get("/feedback/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert 'attachment; filename="feedback_export.pdf"' == response.headers["content-disposition"]


def test_export_pdf_works_when_empty(admin_client, mock_ai):
    response = admin_client.get("/feedback/export/pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_export_pdf_handles_non_latin1_characters(admin_client, mock_ai):
    """fpdf2's built-in helvetica font only supports Latin-1 - smart
    quotes/em-dashes/emoji in real feedback text must not crash export."""
    admin_client.post(
        "/feedback",
        json={"raw_text": "It’s broken — also … this is great! \U0001F600"},
    )

    response = admin_client.get("/feedback/export/pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
