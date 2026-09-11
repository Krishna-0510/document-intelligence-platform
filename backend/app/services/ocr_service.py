"""
OCR / text extraction service.

Two distinct input sources are handled differently, deliberately:

1. PDFs — checked for a native text layer first (fast path, no OCR needed).
   If absent, each page is rasterized at a fixed, controlled DPI and OCR'd
   directly with no extra preprocessing. These renders are already clean
   (consistent lighting/contrast, no skew, no background clutter), and
   testing against this project's real sample PDFs (bank-style consolidated
   balance sheet / P&L / cash flow statements) showed that aggressive
   preprocessing (adaptive thresholding) *hurts* accuracy here — it dropped
   an entire numeric column that plain OCR read correctly.

2. Uploaded raster images (JPG/PNG) — real-world photos of invoices and
   receipts, which are uncontrolled: skewed, low-res, cluttered backgrounds,
   handwriting overlays, thermal-printer fading. Testing against this
   project's real sample invoices showed plain Tesseract frequently drops or
   garbles digits here (e.g. missing amounts, "150.00" read as "}. 00"), or
   in one case produced near-total garbage on a cluttered background photo.
   These get a preprocessing pass (upscale if small, denoise, deskew,
   adaptive threshold) before OCR, which recovered the dropped amounts in
   testing. Some digit-level errors remain on very low-res thermal receipts
   even after preprocessing -- a known Tesseract ceiling, not a bug; the
   README/architecture notes this as a real limitation and where a
   vision-capable LLM would be a stronger (paid-API) alternative.

Interface kept deliberately simple: bytes in, (text, ocr_used) out, so the
extraction service doesn't need to know which path was taken.
"""
import io

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image

from app.core.exceptions import OCRProcessingError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Below this, we upscale before OCR -- small camera photos lose too much
# character detail otherwise.
_MIN_DIMENSION_FOR_OCR = 1500


def extract_text(mime_type: str, content: bytes) -> tuple[str, bool]:
    """Returns (extracted_text, ocr_used)."""
    try:
        if mime_type == "application/pdf":
            return _extract_from_pdf(content)
        return _extract_from_image(content), True
    except Exception as exc:
        logger.exception("OCR/text extraction failed")
        raise OCRProcessingError("Could not extract text from the document.") from exc


def _extract_from_pdf(content: bytes) -> tuple[str, bool]:
    doc = fitz.open(stream=content, filetype="pdf")
    native_text = "\n".join(page.get_text() for page in doc)

    if native_text.strip():
        logger.info("Native PDF text layer found; skipping OCR.")
        return native_text, False

    # No text layer -> scanned/rendered PDF -> rasterize each page and OCR
    # it directly. No extra preprocessing here -- see module docstring.
    logger.info("No native text layer; falling back to OCR per page.")
    ocr_text_parts = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        ocr_text_parts.append(pytesseract.image_to_string(img))
    return "\n".join(ocr_text_parts), True


def _extract_from_image(content: bytes) -> str:
    arr = np.frombuffer(content, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        # Fall back to PIL for formats OpenCV can't decode (e.g. some PNGs).
        pil_img = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(pil_img)

    processed = _preprocess_for_ocr(img)
    text = pytesseract.image_to_string(processed, config="--psm 6")

    # Real-world receipts are sparse and thermal-printer-faded enough that
    # --psm 6 (assume a single uniform block) occasionally returns very
    # little. Retry with default page segmentation before giving up on a
    # near-empty result.
    if len(text.strip()) < 20:
        logger.info("Preprocessed OCR returned little text; retrying with default PSM.")
        fallback = pytesseract.image_to_string(processed)
        if len(fallback.strip()) > len(text.strip()):
            text = fallback

    return text


def _preprocess_for_ocr(img: np.ndarray) -> np.ndarray:
    """Upscale, denoise, deskew and threshold a real-world document photo."""
    h, w = img.shape[:2]
    if max(h, w) < _MIN_DIMENSION_FOR_OCR:
        scale = _MIN_DIMENSION_FOR_OCR / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = _deskew(gray)

    # Edge-preserving denoise -- smooths sensor/thermal-print noise without
    # blurring character edges the way a plain Gaussian blur would.
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return thresh


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Correct small rotational skew. Coarse 90/180/270 orientation errors
    are left to Tesseract's own OSD via the --psm fallback path, since OSD
    needs enough real text to be reliable and can misfire on sparse receipts."""
    try:
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 50:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        # Only correct meaningful skew; small angle estimates on sparse
        # receipts are noise, not real skew, and rotating on that noise
        # can make things worse.
        if abs(angle) < 0.5 or abs(angle) > 15:
            return gray
        h, w = gray.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
    except Exception:
        logger.warning("Deskew step failed; continuing with un-deskewed image.")
        return gray
