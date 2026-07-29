import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.schemas import AttachmentRead
from app.core.config import get_settings
from app.core.security import assert_owns_or_admin, get_current_user
from app.database import crud
from app.database.models import User
from app.database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["attachments"])

_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".txt", ".log", ".csv"}


@router.post(
    "/feedback/{feedback_id}/attachments",
    response_model=list[AttachmentRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachments(
    feedback_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AttachmentRead]:
    settings = get_settings()

    feedback = crud.get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    assert_owns_or_admin(feedback.user_id, current_user)

    if not files:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one file is required.")
    if len(files) > settings.attachment_max_files_per_upload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"At most {settings.attachment_max_files_per_upload} files per upload.",
        )

    # Validate every file before writing any of them, so a bad file later in
    # the list doesn't leave earlier files persisted while the request as a
    # whole still fails.
    validated: list[tuple[UploadFile, bytes, str]] = []
    for upload in files:
        extension = Path(upload.filename or "").suffix.lower()
        if extension not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported file type: {upload.filename}",
            )
        contents = await upload.read()
        if len(contents) > settings.attachment_max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{upload.filename} exceeds the {settings.attachment_max_size_bytes} byte limit.",
            )
        validated.append((upload, contents, extension))

    base_dir = Path(settings.attachments_dir) / str(feedback_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    created: list[AttachmentRead] = []
    for upload, contents, extension in validated:
        # Server-generated name - never built from the client-supplied
        # filename, so a crafted name like "../../etc/passwd" can't escape
        # base_dir. The original filename is kept only as a DB column.
        disk_path = base_dir / f"{uuid.uuid4().hex}{extension}"
        disk_path.write_bytes(contents)

        attachment = crud.create_attachment(
            db,
            feedback_id,
            filename=upload.filename or disk_path.name,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=len(contents),
            storage_path=str(disk_path),
        )
        created.append(attachment)
        logger.info("Stored attachment %s for feedback %s", attachment.id, feedback_id)

    return created


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    attachment = crud.get_attachment(db, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    assert_owns_or_admin(attachment.feedback.user_id, current_user)

    path = Path(attachment.storage_path)
    if not path.exists():
        logger.error("Attachment %s references a missing file on disk: %s", attachment_id, path)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file is missing")

    return FileResponse(path, media_type=attachment.content_type, filename=attachment.filename)
