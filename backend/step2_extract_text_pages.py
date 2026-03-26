#!/usr/bin/env python3
"""
STEP 2: Extract Text from TEXT Pages
Use FREE PyMuPDF extraction - no AI cost
"""

import fitz
import json
from pathlib import Path
import config

def extract_text_pages():
    """Extract text directly from pages with text content"""

    print("=" * 60)
    print("  STEP 2: EXTRACT TEXT PAGES [FREE]")
    print("=" * 60)

    # Load metadata from Step 1
    metadata_file = config.RESULTS_DIR / 'pdf_metadata.json'
    if not metadata_file.exists():
        print("  ERROR: Run step1 first")
        return None

    with open(metadata_file) as f:
        metadata = json.load(f)

    text_pages = metadata['text_page_numbers']

    if not text_pages:
        print("  No text pages detected - skipping")
        output_file = config.RESULTS_DIR / 'text_pages_raw.json'
        with open(output_file, 'w') as f:
            json.dump({}, f)
        return {}

    print(f"  Text pages: {len(text_pages)} pages {text_pages}")
    print(f"  Cost: FREE")
    print()

    doc = fitz.open(config.PDF_PATH)
    extracted_data = {}

    for page_num in text_pages:
        page = doc[page_num - 1]  # 0-indexed
        text = page.get_text()

        extracted_data[f'page_{page_num}'] = {
            'page_number': page_num,
            'text': text,
            'char_count': len(text.strip())
        }
        print(f"  [Page {page_num}] {len(text.strip())} chars")

    doc.close()

    # Save extracted text
    output_file = config.RESULTS_DIR / 'text_pages_raw.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)

    total_chars = sum(p['char_count'] for p in extracted_data.values())

    print()
    print(f"  Extracted: {len(text_pages)} pages, {total_chars} chars")
    print(f"  Saved: {output_file}")
    print("=" * 60)

    return extracted_data

if __name__ == "__main__":
    extract_text_pages()
