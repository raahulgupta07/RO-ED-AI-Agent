#!/usr/bin/env python3
"""
STEP 1: PDF Metadata Analysis
Analyze PDF structure and classify pages as TEXT or IMAGE
"""

import fitz
import json
from pathlib import Path
import config

def classify_page_type(text_len):
    """Classify page as TEXT or IMAGE based on text length"""
    return 'TEXT' if text_len > 100 else 'IMAGE'

def analyze_pdf_metadata():
    """Analyze PDF and create metadata"""

    print("=" * 60)
    print("  STEP 1: PDF METADATA ANALYSIS")
    print("=" * 60)

    pdf_path = Path(config.PDF_PATH)
    print(f"  File: {pdf_path.name}")
    print(f"  Size: {pdf_path.stat().st_size / 1024:.2f} KB")

    doc = fitz.open(config.PDF_PATH)
    print(f"  Pages: {len(doc)}")

    page_metadata = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        text_len = len(text.strip())
        images = page.get_images()
        page_type = classify_page_type(text_len)

        page_metadata.append({
            'page': page_num + 1,
            'type': page_type,
            'text_chars': text_len,
            'images': len(images),
            'has_text': text_len > 100,
            'has_images': len(images) > 0
        })

    doc.close()

    text_pages = [p for p in page_metadata if p['type'] == 'TEXT']
    image_pages = [p for p in page_metadata if p['type'] == 'IMAGE']

    print(f"  Text pages: {len(text_pages)} {[p['page'] for p in text_pages]}")
    print(f"  Image pages: {len(image_pages)} {[p['page'] for p in image_pages]}")

    # Save metadata
    metadata = {
        'pdf_name': Path(config.PDF_PATH).name,
        'pdf_path': str(config.PDF_PATH),
        'total_pages': len(page_metadata),
        'text_pages': len(text_pages),
        'image_pages': len(image_pages),
        'pages': page_metadata,
        'text_page_numbers': [p['page'] for p in page_metadata if p['has_text']],
        'image_page_numbers': [p['page'] for p in page_metadata if not p['has_text']]
    }

    output = config.RESULTS_DIR / 'pdf_metadata.json'
    with open(output, 'w') as f:
        json.dump(metadata, indent=2, fp=f)

    print(f"  Saved: {output}")
    print("=" * 60)

    return metadata

if __name__ == "__main__":
    analyze_pdf_metadata()
