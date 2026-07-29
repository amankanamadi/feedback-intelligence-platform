"""Shared text-sanitization primitives for Pydantic request schemas.

Extracted from app/api/schemas.py so app/api/schemas_auth.py and any
future admin-facing schemas (internal_notes, admin_response, full_name,
etc.) reuse the exact same codepoint-stripping logic rather than each
defining their own regex.
"""
from __future__ import annotations

import re

# Built from bare codepoints (via chr()) rather than embedding the actual
# invisible/control characters in this source file, which would be both
# unreadable and easy to silently corrupt in an editor.
_DANGEROUS_CODEPOINT_RANGES = [
    (0x200B, 0x200F),  # zero-width space/joiners, LRM/RLM marks (obfuscation)
    (0x202A, 0x202E),  # bidi embedding/override controls (visual spoofing)
    (0x2066, 0x2069),  # bidi isolate controls
    (0xFEFF, 0xFEFF),  # BOM / zero-width no-break space
    (0x00, 0x08),  # C0 controls before tab
    (0x0B, 0x0C),  # vertical tab, form feed
    (0x0E, 0x1F),  # C0 controls after CR, before space
    (0x7F, 0x7F),  # DEL
]
DANGEROUS_CHARS = re.compile(
    "[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in _DANGEROUS_CODEPOINT_RANGES) + "]"
)
# The same character repeated 40+ times in a row - not something legitimate
# text does, but a cheap way to waste tokens/cost on every AI call.
EXCESSIVE_REPETITION = re.compile(r"(.)\1{39,}")


def sanitize_optional_text(v: str | None) -> str | None:
    if v is None:
        return v
    cleaned = DANGEROUS_CHARS.sub("", v).strip()
    return cleaned or None


def sanitize_required_text(v: str, *, field_name: str = "text") -> str:
    cleaned = DANGEROUS_CHARS.sub("", v).strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty or whitespace-only")
    if EXCESSIVE_REPETITION.search(cleaned):
        raise ValueError(f"{field_name} contains excessive repeated characters")
    return cleaned
