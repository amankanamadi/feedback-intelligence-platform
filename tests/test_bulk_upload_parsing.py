import pytest

from app.api.bulk_upload_parsing import parse_bulk_upload_file


def test_parses_valid_csv_with_required_and_optional_columns():
    csv_bytes = (
        b"raw_text,source,product\n"
        b'"Dashboard is slow.",Web Form,Reporting\n'
        b'"Please add dark mode.",Email,\n'
    )

    rows = parse_bulk_upload_file("feedback.csv", csv_bytes)

    assert rows == [
        {"raw_text": "Dashboard is slow.", "source": "Web Form", "product": "Reporting"},
        {"raw_text": "Please add dark mode.", "source": "Email"},
    ]


def test_csv_missing_raw_text_column_raises():
    csv_bytes = b"source,product\nWeb Form,Reporting\n"

    with pytest.raises(ValueError, match="raw_text"):
        parse_bulk_upload_file("feedback.csv", csv_bytes)


def test_csv_ignores_unrecognized_columns():
    csv_bytes = b"raw_text,unknown_column\nSlow dashboard.,whatever\n"

    rows = parse_bulk_upload_file("feedback.csv", csv_bytes)

    assert rows == [{"raw_text": "Slow dashboard."}]


def test_parses_bare_json_array():
    json_bytes = b'[{"raw_text": "Slow dashboard."}, {"raw_text": "Add dark mode.", "source": "Chatbot"}]'

    rows = parse_bulk_upload_file("feedback.json", json_bytes)

    assert rows == [
        {"raw_text": "Slow dashboard."},
        {"raw_text": "Add dark mode.", "source": "Chatbot"},
    ]


def test_parses_json_with_items_wrapper():
    json_bytes = b'{"items": [{"raw_text": "Slow dashboard."}]}'

    rows = parse_bulk_upload_file("feedback.json", json_bytes)

    assert rows == [{"raw_text": "Slow dashboard."}]


def test_json_array_with_non_object_item_raises():
    json_bytes = b'["not an object"]'

    with pytest.raises(ValueError, match="not an object"):
        parse_bulk_upload_file("feedback.json", json_bytes)


def test_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_bulk_upload_file("feedback.json", b"{not valid json")


def test_unsupported_extension_raises():
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_bulk_upload_file("feedback.txt", b"raw_text\nsomething\n")


def test_no_filename_raises():
    with pytest.raises(ValueError, match="no filename"):
        parse_bulk_upload_file("", b"raw_text\nsomething\n")
