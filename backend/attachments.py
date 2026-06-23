"""Extract readable text from user-uploaded attachments so the LLM can analyze
them (labs, PDFs, photos). Uploaded files live under health_root/uploads/.

Supports: plain text/CSV/markdown, PDF (pypdf), and images via on-device OCR
(ocrmac, macOS). Each extraction is capped so the prompt stays bounded.
"""

from __future__ import annotations

from pathlib import Path

from backend.paths import health_root

MAX_CHARS_PER_FILE = 6000
TEXT_EXT = {".txt", ".md", ".csv", ".tsv", ".json", ".log"}
PDF_EXT = {".pdf"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".heic", ".heif", ".webp", ".tiff", ".bmp", ".gif"}


def _resolve(path: str, profile_id: str | None = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    # Paths come in as "uploads/<name>" relative to the health root.
    return health_root(profile_id) / p


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def _extract_image(path: Path) -> str:
    try:
        from ocrmac import ocrmac

        result = ocrmac.OCR(str(path)).recognize()
        return "\n".join(item[0] for item in result if item and item[0])
    except Exception:
        return ""


def extract_one(path: str, profile_id: str | None = None) -> str:
    f = _resolve(path, profile_id)
    if not f.exists():
        return ""
    ext = f.suffix.lower()
    if ext in TEXT_EXT:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""
    elif ext in PDF_EXT:
        text = _extract_pdf(f)
    elif ext in IMAGE_EXT:
        text = _extract_image(f)
    else:
        text = ""
    text = text.strip()
    return text[:MAX_CHARS_PER_FILE]


def attachments_context(attachments: list[str] | None, profile_id: str | None = None) -> str:
    """Build a prompt block with the extracted content of each attachment.

    Returns "" when there is nothing to add. Lists the filename even when content
    could not be extracted, so the model knows a file was provided.
    """
    if not attachments:
        return ""
    blocks: list[str] = []
    for path in attachments:
        name = Path(path).name
        content = extract_one(path, profile_id)
        if content:
            blocks.append(f"### {name}\n{content}")
        else:
            blocks.append(f"### {name}\n(could not read this file automatically)")
    return "\n\n".join(blocks)
