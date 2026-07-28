import csv
import enum
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.database import crud
from app.database.models import Feedback, FeedbackSource, MainCategory, Sentiment
from app.database.session import get_db
from app.core.config import get_settings

router = APIRouter(tags=["feedback"])

_CSV_COLUMNS = [
    "id",
    "raw_text",
    "main_category",
    "sub_category",
    "sentiment",
    "priority",
    "confidence",
    "summary",
    "themes",
    "user_id",
    "name",
    "email",
    "source",
    "product",
    "module",
    "version",
    "device",
    "browser",
    "platform",
    "region",
    "attachment_count",
    "created_at",
    "updated_at",
]


def _value(field):
    return field.value if isinstance(field, enum.Enum) else field


def _feedback_to_csv_row(item: Feedback) -> list:
    return [
        item.id,
        item.raw_text,
        _value(item.main_category),
        _value(item.sub_category),
        _value(item.sentiment),
        _value(item.priority),
        item.confidence,
        item.summary,
        "; ".join(theme.name for theme in item.themes),
        item.user_id,
        item.name,
        item.email,
        _value(item.source),
        item.product,
        item.module,
        item.version,
        item.device,
        item.browser,
        item.platform,
        item.region,
        len(item.attachments),
        item.created_at.isoformat() if item.created_at else None,
        item.updated_at.isoformat() if item.updated_at else None,
    ]


def _fetch_items(
    db: Session,
    main_category: Optional[MainCategory],
    sentiment: Optional[Sentiment],
    search: Optional[str],
    source: Optional[FeedbackSource],
    product: Optional[str],
) -> list[Feedback]:
    settings = get_settings()
    return crud.list_feedback(
        db,
        limit=settings.feedback_export_max_rows,
        main_category=main_category,
        sentiment=sentiment,
        search=search,
        source=source,
        product=product,
    )


@router.get("/feedback/export/csv")
def export_feedback_csv(
    main_category: Optional[MainCategory] = Query(None),
    sentiment: Optional[Sentiment] = Query(None),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    source: Optional[FeedbackSource] = Query(None),
    product: Optional[str] = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> Response:
    items = _fetch_items(db, main_category, sentiment, search, source, product)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_CSV_COLUMNS)
    for item in items:
        writer.writerow(_feedback_to_csv_row(item))

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="feedback_export.csv"'},
    )


# fpdf2's built-in "helvetica" font only supports Latin-1 - real feedback
# text routinely contains smart quotes/em-dashes/ellipses that would
# otherwise crash the export. Built from bare codepoints (via chr()) rather
# than embedding the actual Unicode characters in this source file, same
# reasoning as app/api/schemas.py's dangerous-character handling. Anything
# still unsupported after this (e.g. emoji, CJK) is replaced rather than
# raising, since the PDF is a readable summary - the CSV export preserves
# exact text losslessly.
_PDF_UNICODE_REPLACEMENTS = {
    chr(0x2018): "'",  # left single quote
    chr(0x2019): "'",  # right single quote
    chr(0x201C): '"',  # left double quote
    chr(0x201D): '"',  # right double quote
    chr(0x2013): "-",  # en dash
    chr(0x2014): "-",  # em dash
    chr(0x2026): "...",  # ellipsis
}


def _pdf_safe_text(text) -> str:
    if text is None:
        return "-"
    text = str(text)
    for bad, good in _PDF_UNICODE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _build_feedback_pdf(items: list[Feedback]) -> bytes:
    pdf = FPDF(orientation="landscape")
    pdf.add_page()
    pdf.set_font("helvetica", size=14)
    pdf.cell(0, 10, "Feedback Export", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=9)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.cell(0, 6, f"Generated {generated_at} - {len(items)} row(s)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("helvetica", size=8)
    headers = ["ID", "Feedback", "Source", "Product", "Category", "Sentiment", "Priority", "Confidence", "Created"]
    with pdf.table(col_widths=(8, 30, 12, 12, 14, 10, 9, 9, 12)) as table:
        header_row = table.row()
        for header in headers:
            header_row.cell(header)
        for item in items:
            row = table.row()
            row.cell(str(item.id))
            row.cell(_pdf_safe_text(item.raw_text[:60]))
            row.cell(_pdf_safe_text(_value(item.source) or "-"))
            row.cell(_pdf_safe_text(item.product or "-"))
            row.cell(_pdf_safe_text(_value(item.main_category) or "-"))
            row.cell(_pdf_safe_text(_value(item.sentiment) or "-"))
            row.cell(_pdf_safe_text(_value(item.priority) or "-"))
            row.cell(str(item.confidence) if item.confidence is not None else "-")
            row.cell(item.created_at.strftime("%Y-%m-%d") if item.created_at else "-")

    return bytes(pdf.output())


@router.get("/feedback/export/pdf")
def export_feedback_pdf(
    main_category: Optional[MainCategory] = Query(None),
    sentiment: Optional[Sentiment] = Query(None),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    source: Optional[FeedbackSource] = Query(None),
    product: Optional[str] = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> Response:
    items = _fetch_items(db, main_category, sentiment, search, source, product)
    pdf_bytes = _build_feedback_pdf(items)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="feedback_export.pdf"'},
    )
