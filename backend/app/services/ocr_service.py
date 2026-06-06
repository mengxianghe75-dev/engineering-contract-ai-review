from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from fastapi import HTTPException, status

from app.core.config import settings

try:
    import fitz
except ImportError:  # pragma: no cover - optional dependency
    fitz = None


class OcrDependencyError(RuntimeError):
    pass


@dataclass
class OcrParseResult:
    raw_text: str
    page_count: int


def ensure_ocr_dependencies() -> None:
    if fitz is None:
        raise OcrDependencyError(
            "OCR fallback requires PyMuPDF. Install backend dependencies again after adding pymupdf."
        )

    if shutil.which("tesseract") is None:
        raise OcrDependencyError(
            "OCR fallback requires the `tesseract` command. Install Tesseract OCR and Chinese language data."
        )


def extract_text_with_ocr(file_bytes: bytes) -> OcrParseResult:
    ensure_ocr_dependencies()

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # pragma: no cover - fitz exception types vary
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload failed: unable to render PDF pages for OCR. {exc}",
        ) from exc

    try:
        page_count = document.page_count
        page_texts: list[str] = []
        with TemporaryDirectory(prefix="contract-ocr-") as temp_dir:
            temp_path = Path(temp_dir)
            for page_index in range(page_count):
                page = document.load_page(page_index)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(settings.ocr_render_scale, settings.ocr_render_scale), alpha=False)
                image_path = temp_path / f"page-{page_index + 1}.png"
                pixmap.save(image_path)
                page_texts.append(_run_tesseract(image_path))
    finally:
        document.close()

    raw_text = "\n".join(text.strip() for text in page_texts if text.strip()).strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Upload failed: OCR completed but no readable text was recognized. "
                "Please confirm the scan is clear and not password-protected."
            ),
        )

    return OcrParseResult(raw_text=raw_text, page_count=page_count)


def _run_tesseract(image_path: Path) -> str:
    command = [
        "tesseract",
        str(image_path),
        "stdout",
        "-l",
        settings.ocr_language,
        "--psm",
        "6",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - guarded above
        raise OcrDependencyError(
            "OCR fallback requires the `tesseract` command. Install Tesseract OCR and Chinese language data."
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: OCR engine execution failed. {stderr or 'Unknown tesseract error.'}",
        )

    return completed.stdout or ""
