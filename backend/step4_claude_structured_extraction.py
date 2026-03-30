#!/usr/bin/env python3
"""
STEP 4: Dash Agent Structured Extraction (DUAL FORMAT)
Extract Format 1 (6 item fields) + Format 2 (16 declaration fields)
"""

import json
import time
import base64
import requests
import fitz
import re
from pathlib import Path
import config

EXTRACTION_PROMPT_TEMPLATE = """Analyze this Myanmar import customs declaration document and extract TWO types of data.

DOCUMENT STRUCTURE (auto-detected from PDF analysis):
{page_structure}

═══════════════════════════════════════════════════════════════════

FORMAT 1: LINE ITEMS (Array of products)

Extract these 6 fields for EACH product item:

1. Item name: "PRODUCT NAME (CODE) (SIZE) (BRAND: NAME) (C/O: COUNTRY)"
2. Customs duty rate: DECIMAL (0.15 = 15%)
3. Quantity (1): "NUMBER+UNIT" (e.g., "16200.00KG")
4. Invoice unit price: "PRICE+UNIT" (e.g., "69.1358THB")
5. Commercial tax %: DECIMAL (0.05 = 5%)
6. Exchange Rate (1): "CURRENCY RATE" (e.g., "THB 65.0025")

═══════════════════════════════════════════════════════════════════

FORMAT 2: DOCUMENT HEADER (Single record for entire declaration)

Extract these 16 fields from the customs declaration pages:

1. Declaration No: Declaration/Entry number (numeric string found on the document)
2. Declaration Date: Date in YYYY-MM-DD format (e.g., "2025-10-14")
3. Importer (Name): Company name of importer
4. Consignor (Name): Company name of consignor/shipper
5. Invoice Number: Invoice reference number
6. Invoice Price: Total invoice amount as NUMBER (e.g., 1118432.0)
7. Currency: Invoice currency code (e.g., "THB")
8. Exchange Rate: Exchange rate as NUMBER (e.g., 65.0025)
9. Currency.1: Local currency code (e.g., "MMK")
10. Total Customs Value: Total customs value as NUMBER
11. Import/Export Customs Duty: Total customs duty as NUMBER
12. Commercial Tax (CT): Commercial tax amount as NUMBER
13. Advance Income Tax (AT): Income tax amount as NUMBER
14. Security Fee (SF): Security fee as NUMBER
15. MACCS Service Fee (MF): MACCS service fee as NUMBER
16. Exemption/Reduction: Exemption/reduction amount as NUMBER (use 0 if none)

═══════════════════════════════════════════════════════════════════

Return ONLY this exact JSON structure:

{{
  "declaration": {{
    "Declaration No": "<extract from document>",
    "Declaration Date": "<YYYY-MM-DD from document>",
    "Importer (Name)": "<extract from document>",
    "Consignor (Name)": "<extract from document>",
    "Invoice Number": "<extract from document>",
    "Invoice Price ": 0.0,
    "Currency": "<e.g. THB, USD>",
    "Exchange Rate": 0.0,
    "Currency.1": "<e.g. MMK>",
    "Total Customs Value ": 0.0,
    "Import/Export Customs Duty ": 0.0,
    "Commercial Tax (CT)": 0.0,
    "Advance Income Tax (AT)": 0.0,
    "Security Fee (SF)": 0.0,
    "MACCS Service Fee (MF)": 0.0,
    "Exemption/Reduction": 0.0
  }},
  "items": [
    {{
      "Item name": "<PRODUCT NAME (BRAND: NAME) (C/O: COUNTRY)>",
      "Customs duty rate": 0.0,
      "Quantity (1)": "<NUMBER+UNIT e.g. 2400KG>",
      "Invoice unit price": "<PRICE+UNIT e.g. 129.521THB>",
      "Commercial tax %": 0.0,
      "Exchange Rate (1)": "<CURRENCY RATE e.g. THB 64.398>"
    }}
  ]
}}

ALSO: For each item field, provide a confidence score (0.0 to 1.0) indicating how certain you are.
Add a "_confidence" key next to each field. Example: "Customs duty rate": 0.15, "Customs duty rate_confidence": 0.95

CRITICAL:
- Extract BOTH formats (declaration header + all line items)
- Use exact field names with spaces and parentheses as shown
- Declaration is SINGLE object, items is ARRAY
- Use DECIMAL for percentages (0.15 not 15)
- Use NUMBER for all financial amounts (no commas, no currency symbols)
- Include _confidence scores for each item field
- Return ONLY valid JSON"""


def build_page_structure_description(metadata):
    """Build a dynamic page structure description from step1 metadata."""
    lines = []
    text_pages = metadata.get('text_page_numbers', [])
    image_pages = metadata.get('image_page_numbers', [])

    if image_pages:
        ranges = _format_page_ranges(image_pages)
        lines.append(f"- Scanned/Image pages ({ranges}): These pages contain scanned images and require OCR. They may include delivery orders, shipping documents, certificates, or other scanned forms.")

    if text_pages:
        ranges = _format_page_ranges(text_pages)
        lines.append(f"- Text pages ({ranges}): These pages contain extractable text. They may include packing lists, invoices, import documents, customs declarations, or other structured forms.")

    lines.append(f"- Total pages: {metadata.get('total_pages', 'unknown')}")
    return "\n".join(lines)


def _format_page_ranges(page_numbers):
    """Format a list of page numbers into readable ranges like '1-5, 12-15'."""
    if not page_numbers:
        return ""
    sorted_pages = sorted(page_numbers)
    ranges = []
    start = sorted_pages[0]
    end = start
    for p in sorted_pages[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append(f"{start}" if start == end else f"{start}-{end}")
            start = p
            end = p
    ranges.append(f"{start}" if start == end else f"{start}-{end}")
    return ", ".join(ranges)

def convert_pdf_to_images(pdf_path: str, pages_to_convert=None):
    """Convert specified pages to base64 images"""
    doc = fitz.open(pdf_path)
    images = []

    if pages_to_convert is None:
        pages_to_convert = range(len(doc))

    for page_num in pages_to_convert:
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(config.EXTRACTION_RESOLUTION, config.EXTRACTION_RESOLUTION))
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        images.append(img_b64)

    doc.close()
    return images

def extract_structured_data():
    """Extract structured data by talking to LLM via Dash Agent"""

    print("="*80)
    print(" STEP 4: DASH AGENT STRUCTURED EXTRACTION")
    print("="*80)

    # Load metadata
    metadata_file = config.RESULTS_DIR / 'pdf_metadata.json'
    if not metadata_file.exists():
        print("\n❌ ERROR: Run step1_analyze_metadata.py first!")
        return None

    with open(metadata_file) as f:
        metadata = json.load(f)

    print(f"\n📊 Total pages: {metadata['total_pages']}")
    print(f"📊 Text pages: {metadata.get('text_page_numbers', [])}")
    print(f"📊 Image pages: {metadata.get('image_page_numbers', [])}")
    print(f"💰 Model: {config.EXTRACTION_MODEL}")
    print(f"💰 Estimated cost: $0.0054\n")

    # Build dynamic prompt from actual page classification
    page_structure = build_page_structure_description(metadata)
    extraction_prompt = EXTRACTION_PROMPT_TEMPLATE.format(page_structure=page_structure)
    print(f"📝 Dynamic prompt built from {metadata['total_pages']}-page analysis\n")

    # Convert all pages to images (dynamic based on actual PDF)
    print("📄 Converting pages...", end=" ")
    total_pages = metadata['total_pages']
    key_pages = list(range(total_pages))
    images = convert_pdf_to_images(str(config.PDF_PATH), key_pages)
    print(f"✓ {len(images)} pages\n")

    # Build content
    content = []
    for img_b64 in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    content.append({"type": "text", "text": extraction_prompt})

    payload = {
        "model": config.EXTRACTION_MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": 4000
    }

    print("  Talking to LLM...", end=" ")
    start_time = time.time()

    # Smart retry with backoff
    response = None
    for attempt in range(config.MAX_RETRIES):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {config.API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=config.API_TIMEOUT
            )
            if response.status_code == 200:
                break
            print(f"\n  API Error {response.status_code}", end="")
        except Exception as e:
            print(f"\n  Request error: {str(e)[:60]}", end="")

        if attempt < config.MAX_RETRIES - 1:
            wait = config.RETRY_BACKOFF_BASE ** (attempt + 1)
            print(f" — retry {attempt+2}/{config.MAX_RETRIES} in {wait}s...", end="")
            time.sleep(wait)

    duration = time.time() - start_time

    try:
        if not response or response.status_code != 200:
            print(f"\n  FAILED after {config.MAX_RETRIES} attempts")
            return None

        result = response.json()
        content_text = result["choices"][0]["message"]["content"]

        print(f"✓ ({duration:.1f}s)\n")

        # Parse JSON (now expecting {declaration: {}, items: []})
        cleaned = re.sub(r'```json\n?|```\n?', '', content_text).strip()

        declaration = {}
        items = []
        try:
            # Parse as object with declaration and items
            if '{' in cleaned and '}' in cleaned:
                start_idx = cleaned.index('{')
                end_idx = cleaned.rindex('}') + 1
                json_str = cleaned[start_idx:end_idx]
                data = json.loads(json_str)

                # Extract both formats
                declaration = data.get('declaration', {})
                items = data.get('items', [])

                # Fallback: if old format (just array), treat as items only
                if not declaration and not items and isinstance(data, list):
                    items = data
        except Exception as e:
            print(f"⚠️  JSON parse error: {str(e)[:100]}")
            return None

        # Calculate completeness
        if items:
            total_fields = len(items) * 6
            filled_fields = sum(
                1 for item in items
                for key in ['Item name', 'Customs duty rate', 'Quantity (1)',
                           'Invoice unit price', 'Commercial tax %', 'Exchange Rate (1)']
                if item.get(key) is not None and str(item.get(key)).strip() and item.get(key) != ''
            )

            completeness = (filled_fields / total_fields) * 100 if total_fields > 0 else 0

            print(f"✅ FORMAT 1 - Items extracted: {len(items)}")
            print(f"✅ FORMAT 1 - Fields filled: {filled_fields}/{total_fields}")
            print(f"✅ FORMAT 1 - Completeness: {completeness:.0f}%")

            if declaration:
                decl_fields = sum(1 for v in declaration.values() if v is not None and str(v).strip())
                print(f"✅ FORMAT 2 - Declaration extracted: {decl_fields}/16 fields")
            else:
                print("⚠️  FORMAT 2 - No declaration extracted")

            print()

            # Save results (both formats)
            output_data = {
                'pdf_name': Path(config.PDF_PATH).name,
                'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'model': config.EXTRACTION_MODEL,
                'duration_seconds': duration,
                'items_count': len(items),
                'fields_filled': filled_fields,
                'total_fields': total_fields,
                'completeness_percent': completeness,
                'declaration': declaration,  # Format 2
                'items': items  # Format 1
            }

            output_file = config.RESULTS_DIR / 'claude_extracted.json'

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"💾 Saved: {output_file}")
            print("\n✅ STEP 4 COMPLETE (DUAL FORMAT)")
            print("="*80 + "\n")

            return output_data

        else:
            print("  No items extracted — returning declaration only")
            output_data = {
                'pdf_name': Path(config.PDF_PATH).name,
                'extraction_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'model': config.EXTRACTION_MODEL,
                'duration_seconds': duration,
                'items_count': 0,
                'fields_filled': 0,
                'total_fields': 0,
                'completeness_percent': 0,
                'declaration': declaration,
                'items': []
            }

            output_file = config.RESULTS_DIR / 'claude_extracted.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            return output_data

    except Exception as e:
        print(f"✗\n❌ Error: {str(e)[:200]}")
        return None

if __name__ == "__main__":
    extract_structured_data()
