#!/usr/bin/env python3
"""
STEP 1B: Filter Agent
Analyzes each IMAGE page via LLM to determine if it contains
useful customs data (tables, declarations, invoices) or should
be skipped (photos, stamps, signatures, blank pages).
"""

import json
import time
import base64
import requests
import fitz
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import config

FILTER_PROMPT = """Look at this scanned document page image. Classify it as one of:

USEFUL - Contains extractable data: tables, invoices, packing lists, customs declarations, shipping documents, certificates with text, forms with fields and values.

SKIP - Contains NO extractable data: photos of people/products, stamps only, signatures only, blank pages, decorative covers, logos only, handwritten notes that are illegible.

Return ONLY a JSON object:
{"classification": "USEFUL" or "SKIP", "reason": "brief reason", "content_type": "what you see on this page"}

Return ONLY valid JSON, nothing else."""


def _classify_page(page_num, pdf_path):
    """Send one page thumbnail to LLM for classification."""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        # Use low resolution for speed — we only need to see what's on the page
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        doc.close()

        content = [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            {"type": "text", "text": FILTER_PROMPT}
        ]

        payload = {
            "model": config.OCR_MODEL,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": 200
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return page_num, "USEFUL", "API error — keeping page", "unknown"

        import re
        text = response.json()["choices"][0]["message"]["content"].strip()
        cleaned = re.sub(r'```json\n?|```\n?', '', text).strip()

        if '{' in cleaned:
            start = cleaned.index('{')
            end = cleaned.rindex('}') + 1
            result = json.loads(cleaned[start:end])
            classification = result.get('classification', 'USEFUL').upper()
            reason = result.get('reason', '')
            content_type = result.get('content_type', '')
            return page_num, classification, reason, content_type
        else:
            return page_num, "USEFUL", "Could not parse — keeping page", "unknown"

    except Exception as e:
        return page_num, "USEFUL", f"Error: {str(e)[:50]} — keeping page", "unknown"


def filter_pages(metadata):
    """Run Filter Agent on all IMAGE pages. Returns updated metadata with skip info."""

    print("=" * 60)
    print("  STEP 1B: FILTER AGENT")
    print("=" * 60)

    image_pages = metadata.get('image_page_numbers', [])

    if not image_pages:
        print("  No image pages to filter")
        return metadata

    print(f"  Analyzing {len(image_pages)} image pages for relevance...")
    print(f"  Cost: ~${len(image_pages) * 0.0003:.4f}")
    print()

    start_time = time.time()
    results = {}

    # Parallel classification (up to 4 concurrent)
    max_workers = min(4, len(image_pages))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_classify_page, pg, str(config.PDF_PATH)): pg
            for pg in image_pages
        }
        for future in as_completed(futures):
            pg_num, classification, reason, content_type = future.result()
            results[pg_num] = {
                'classification': classification,
                'reason': reason,
                'content_type': content_type
            }
            status = "KEEP" if classification == "USEFUL" else "SKIP"
            print(f"  Page {pg_num}: {status} — {reason}")

    duration = time.time() - start_time

    # Update metadata with filter results
    useful_pages = [pg for pg in image_pages if results.get(pg, {}).get('classification') == 'USEFUL']
    skipped_pages = [pg for pg in image_pages if results.get(pg, {}).get('classification') == 'SKIP']

    # Update page metadata
    for p in metadata.get('pages', []):
        pg_num = p['page']
        if pg_num in results:
            p['filter_classification'] = results[pg_num]['classification']
            p['filter_reason'] = results[pg_num]['reason']
            p['filter_content_type'] = results[pg_num]['content_type']
            p['skip'] = results[pg_num]['classification'] == 'SKIP'
        else:
            p['skip'] = False

    # Update image page numbers to only include useful pages
    metadata['image_page_numbers_original'] = image_pages
    metadata['image_page_numbers'] = useful_pages
    metadata['skipped_pages'] = skipped_pages
    metadata['skipped_count'] = len(skipped_pages)
    metadata['filter_results'] = results
    metadata['image_pages'] = len(useful_pages)

    # Save updated metadata
    output = config.RESULTS_DIR / 'pdf_metadata.json'
    with open(output, 'w') as f:
        json.dump(metadata, indent=2, fp=f)

    print()
    print(f"  Useful image pages: {len(useful_pages)} {useful_pages}")
    print(f"  Skipped pages: {len(skipped_pages)} {skipped_pages}")
    if skipped_pages:
        for sp in skipped_pages:
            r = results.get(sp, {})
            print(f"    Page {sp}: {r.get('content_type', '?')} — {r.get('reason', '?')}")
    print(f"  Time: {duration:.1f}s")
    print("=" * 60)

    return metadata


if __name__ == "__main__":
    import step1_analyze_metadata
    meta = step1_analyze_metadata.analyze_pdf_metadata()
    if meta:
        filter_pages(meta)
