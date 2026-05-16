"""
app/extraction/pdf_extractor.py
PDF → clean plain text using PyMuPDF (fitz).
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from app.extraction.text_cleaner import clean_extracted_text

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    pass


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """
    Extract and clean all text from a PDF.

    Raises:
        PDFExtractionError: file not found, wrong type, or no extractable text.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise PDFExtractionError(f"File not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise PDFExtractionError(f"Expected .pdf, got: {path.suffix}")

    pages: list[str] = []
    try:
        doc = fitz.open(str(path))
        for page in doc:
            t = page.get_text()
            if t.strip():
                pages.append(t)
        doc.close()
    except Exception as exc:
        raise PDFExtractionError(f"fitz error on {path.name}: {exc}") from exc

    if not pages:
        raise PDFExtractionError(f"No extractable text in {path.name} (may be scanned).")

    cleaned = clean_extracted_text("\n".join(pages))
    logger.info("Extracted %d chars from %s", len(cleaned), path.name)
    return cleaned
