#!/usr/bin/env python3
"""
STEP 3: OCR Image Pages (Parallel + Retry + Adaptive Resolution)
Uses Dash Agent Vision for OCR of scanned pages.
- Parallel execution (up to 4 concurrent)
- Smart retry with exponential backoff
- Adaptive resolution: auto-upgrades to high-res if OCR yields few chars
"""

import json
import time
import base64
import requests
import fitz
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import config

OCR_PROMPT = """Extract ALL text from this scanned document image.

Return the complete text content exactly as it appears.
Maintain formatting, line breaks, and structure.
Include all numbers, dates, addresses, and product information.

Return ONLY the extracted text, nothing else."""


def convert_page_to_image(pdf_path: str, page_num: int, resolution=None):
    """Convert single page to base64 image at given resolution."""
    res = resolution or config.OCR_RESOLUTION
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(res, res))
    img_bytes = pix.tobytes("png")
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
    doc.close()
    return img_b64


def _call_ocr_api(img_b64):
    """Single OCR API call. Returns text or None."""
    content = [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
        {"type": "text", "text": OCR_PROMPT}
    ]
    payload = {
        "model": config.OCR_MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": 4000
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=config.API_TIMEOUT
    )
    if response.status_code != 200:
        return None
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def ocr_single_page_with_retry(page_num: int, pdf_path: str):
    """OCR one page with retry + adaptive resolution."""

    # Attempt at default resolution with retries
    for attempt in range(config.MAX_RETRIES):
        try:
            img_b64 = convert_page_to_image(pdf_path, page_num, config.OCR_RESOLUTION)
            text = _call_ocr_api(img_b64)
            if text is not None:
                # Adaptive: if too few chars, try higher resolution
                if len(text) < config.OCR_MIN_CHARS and attempt == 0:
                    print(f"  [Page {page_num}] Low quality ({len(text)} chars), trying high-res...")
                    img_b64_hires = convert_page_to_image(pdf_path, page_num, config.OCR_HIRES_RESOLUTION)
                    text_hires = _call_ocr_api(img_b64_hires)
                    if text_hires and len(text_hires) > len(text):
                        print(f"  [Page {page_num}] High-res improved: {len(text)} → {len(text_hires)} chars")
                        return page_num, text_hires, "high-res"
                return page_num, text, "ok"
        except Exception as e:
            pass

        # Backoff before retry
        if attempt < config.MAX_RETRIES - 1:
            wait = config.RETRY_BACKOFF_BASE ** (attempt + 1)
            print(f"  [Page {page_num}] Retry {attempt+2}/{config.MAX_RETRIES} in {wait}s...")
            time.sleep(wait)

    return page_num, None, "failed"


def _ocr_page_task(args):
    """Wrapper for parallel execution."""
    page_num, pdf_path = args
    return ocr_single_page_with_retry(page_num, pdf_path)


def ocr_image_pages():
    """OCR all image pages in parallel with retry + adaptive resolution."""

    print("=" * 60)
    print("  STEP 3: OCR IMAGE PAGES (PARALLEL + RETRY)")
    print("=" * 60)

    metadata_file = config.RESULTS_DIR / 'pdf_metadata.json'
    if not metadata_file.exists():
        print("  ERROR: Run step1 first")
        return None

    with open(metadata_file) as f:
        metadata = json.load(f)

    image_pages = metadata['image_page_numbers']

    if not image_pages:
        print("  No image pages detected — skipping OCR")
        output_file = config.RESULTS_DIR / 'image_pages_ocr.json'
        with open(output_file, 'w') as f:
            json.dump({}, f)
        return {}

    print(f"  Image pages: {len(image_pages)} pages")
    print(f"  Cost estimate: ${len(image_pages) * 0.0006:.4f}")
    print(f"  Mode: Parallel (up to 4) + Retry ({config.MAX_RETRIES}x) + Adaptive resolution")
    print()

    start_time = time.time()
    ocr_data = {}
    failed_pages = []
    hires_pages = []

    max_workers = min(4, len(image_pages))
    tasks = [(pg, str(config.PDF_PATH)) for pg in image_pages]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_ocr_page_task, t): t[0] for t in tasks}

        for future in as_completed(futures):
            page_num, ocr_text, status = future.result()
            if ocr_text:
                print(f"  [Page {page_num}] Done ({len(ocr_text)} chars) [{status}]")
                ocr_data[f'page_{page_num}'] = {
                    'page_number': page_num,
                    'ocr_text': ocr_text,
                    'char_count': len(ocr_text),
                    'ocr_status': status
                }
                if status == "high-res":
                    hires_pages.append(page_num)
            else:
                print(f"  [Page {page_num}] FAILED after {config.MAX_RETRIES} attempts")
                failed_pages.append(page_num)

    duration = time.time() - start_time

    # Save results
    output_file = config.RESULTS_DIR / 'image_pages_ocr.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ocr_data, f, indent=2, ensure_ascii=False)

    total_chars = sum(p['char_count'] for p in ocr_data.values())

    print()
    print(f"  OCR complete: {len(ocr_data)}/{len(image_pages)} pages")
    print(f"  Total chars: {total_chars}")
    if hires_pages:
        print(f"  High-res upgrades: pages {hires_pages}")
    if failed_pages:
        print(f"  Failed pages: {failed_pages}")
    print(f"  Time: {duration:.1f}s")
    print("=" * 60)

    return ocr_data


if __name__ == "__main__":
    ocr_image_pages()
