import io
import logging

import fitz  # PyMuPDF
import easyocr
import cv2
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

__all__ = ["extract_text_from_pdf"]


def extract_text_from_pdf(pdf_bytes: bytes, languages: list[str] | None = None) -> str:
    """Extract text from a PDF using EasyOCR.

    Args:
        pdf_bytes: PDF file contents.
        languages: Optional list of language codes for the OCR reader.

    Returns:
        The extracted text from all pages.
    """
    languages = languages or ["en"]
    reader = easyocr.Reader(languages, gpu=False)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    extracted = []
    for page in doc:
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.alpha:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        results = reader.readtext(img)
        extracted.append(" ".join(r[1] for r in results))
    return "\n".join(extracted)
