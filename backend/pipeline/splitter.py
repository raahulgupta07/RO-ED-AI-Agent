#!/usr/bin/env python3
"""
RO-ED: HD Image Splitter
PDF → high-quality page images. No Tesseract. No text extraction.
Just sharp, clear images for vision AI.
"""

import base64
import fitz  # PyMuPDF
from io import BytesIO
from typing import Dict, List

# Try Pillow for image enhancement
try:
    from PIL import Image, ImageEnhance, ImageFilter
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


# 300 DPI = 300/72 ≈ 4.17x zoom factor
DPI_300 = 300 / 72  # ~4.17
MAX_DIMENSION = 4096  # Vision model max pixel dimension


def _enhance_image(img_bytes: bytes) -> bytes:
    """Sharpen + auto-contrast for crisp text, especially small fonts."""
    if not HAS_PILLOW:
        return img_bytes

    img = Image.open(BytesIO(img_bytes))

    # Sharpen — makes small text readable
    img = img.filter(ImageFilter.SHARPEN)

    # Contrast boost — helps scanned documents
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)

    # Brightness slight boost — helps dark scans
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.05)

    # Resize if too large for vision model
    w, h = img.size
    if max(w, h) > MAX_DIMENSION:
        scale = MAX_DIMENSION / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Save as PNG
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def split_pdf(pdf_path: str) -> List[Dict]:
    """
    Split PDF into high-quality page images.

    Returns:
        List of {page_number, image_b64, width, height}
    """
    doc = fitz.open(pdf_path)
    total = len(doc)
    pages = []

    print(f"  Splitting {doc.name.split('/')[-1]} → {total} pages at 300 DPI")

    for i in range(total):
        page = doc[i]

        # Render at 300 DPI
        mat = fitz.Matrix(DPI_300, DPI_300)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        # Enhance for clarity
        img_bytes = _enhance_image(img_bytes)

        # Encode to base64
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        pages.append({
            "page_number": i + 1,
            "image_b64": img_b64,
            "width": pix.width,
            "height": pix.height,
        })

    doc.close()
    print(f"  Done: {total} HD pages ({pages[0]['width']}x{pages[0]['height']}px)" if pages else "  No pages")

    return pages
