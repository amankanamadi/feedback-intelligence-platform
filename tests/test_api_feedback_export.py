import csv
import io


def test_export_csv_has_header_row_when_empty(admin_client, mock_ai):
    response = admin_client.get("/feedback/export/csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][:3] == ["id", "raw_text", "main_category"]
    assert "recommended_action" in rows[0]
    assert "property_name" in rows[0]
    assert "property_city" in rows[0]
    assert len(rows) == 1  # header only, no data rows


def test_export_csv_includes_submitted_feedback(admin_client, db_session, mock_ai):
    from app.database.models import Property, PropertyType

    property_row = Property(
        name="Sunny Loft", host_name="Jordan Lee", city="Austin", country="USA", property_type=PropertyType.ENTIRE_HOME
    )
    db_session.add(property_row)
    db_session.commit()

    admin_client.post(
        "/feedback",
        json={"raw_text": "The apartment was dirty.", "source": "Website", "property_id": property_row.id},
    )

    response = admin_client.get("/feedback/export/csv")

    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 2
    header, data = rows
    row = dict(zip(header, data))
    assert row["raw_text"] == "The apartment was dirty."
    assert row["source"] == "Website"
    assert row["property_name"] == "Sunny Loft"
    assert row["property_city"] == "Austin"
    assert row["main_category"] == "Guest Review"
    assert row["recommended_action"]


def test_export_csv_respects_filters(admin_client, mock_ai):
    admin_client.post("/feedback", json={"raw_text": "Via email.", "source": "Email"})
    admin_client.post("/feedback", json={"raw_text": "Via the website.", "source": "Website"})

    response = admin_client.get("/feedback/export/csv", params={"source": "Email"})

    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 2
    assert rows[1][1] == "Via email."


def test_export_csv_joins_themes_and_includes_attachment_count(admin_client, mock_ai):
    created = admin_client.post("/feedback", json={"raw_text": "The apartment was dirty."}).json()
    admin_client.post(
        f"/feedback/{created['id']}/attachments",
        files={"files": ("notes.txt", b"hello", "text/plain")},
    )

    response = admin_client.get("/feedback/export/csv")

    rows = list(csv.reader(io.StringIO(response.text)))
    header, data = rows
    row = dict(zip(header, data))
    assert row["themes"] == "Dirty Apartment; Cleaning Quality"
    assert row["attachment_count"] == "1"


def test_export_pdf_returns_valid_pdf_bytes(admin_client, mock_ai):
    admin_client.post("/feedback", json={"raw_text": "The apartment was dirty."})

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
        json={"raw_text": "It’s dirty — also … the host was great! \U0001F600"},
    )

    response = admin_client.get("/feedback/export/pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_export_routes_require_manager_role(product_manager_client):
    assert product_manager_client.get("/feedback/export/csv").status_code == 403
    assert product_manager_client.get("/feedback/export/pdf").status_code == 403
