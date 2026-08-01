"""Parse an uploaded CSV or JSON file into feedback item dicts, ready to be
validated by BulkFeedbackCreate. Column/key names must match
FeedbackCreate's field names exactly - no fuzzy header matching, keeps
parsing predictable.
"""

from __future__ import annotations

import csv
import io
import json

_ALLOWED_FIELDS = {
    "raw_text",
    "submitter_user_id_legacy",
    "name",
    "email",
    "source",
    "property_id",
    "version",
    "device",
    "browser",
    "platform",
}


def _clean_row(row: dict) -> dict:
    """Keep only recognized fields; blank cells become "not provided"
    rather than an empty string, so e.g. an empty `source` cell doesn't
    get rejected as an invalid enum value."""
    cleaned = {}
    for key, value in row.items():
        if key not in _ALLOWED_FIELDS or value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        cleaned[key] = value
    return cleaned


def parse_bulk_upload_file(filename: str, raw_bytes: bytes) -> list[dict]:
    if not filename:
        raise ValueError("Uploaded file has no filename.")
    lower = filename.lower()

    if lower.endswith(".json"):
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError(f"Could not decode file as UTF-8: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        if not isinstance(data, list):
            raise ValueError('JSON file must contain a list of feedback items, or {"items": [...]}.')

        rows = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Item {i} in the JSON file is not an object.")
            rows.append(_clean_row(item))
        return rows

    if lower.endswith(".csv"):
        try:
            text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Could not decode file as UTF-8: {exc}") from exc

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "raw_text" not in reader.fieldnames:
            raise ValueError("CSV file must have a 'raw_text' column header.")
        return [_clean_row(row) for row in reader]

    raise ValueError("Unsupported file type - upload a .csv or .json file.")
