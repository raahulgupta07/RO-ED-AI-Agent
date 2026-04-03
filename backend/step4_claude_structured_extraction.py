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

Extract these 6 fields for EACH product item found in the document:

1. Item name: Full product description including brand and country of origin as shown in the document
2. Customs duty rate: DECIMAL value. 0.15 means 15%, 0.05 means 5%. If the document shows "FREE" or "0%" or customs duty amount is 0, use 0.0
3. Quantity (1): "NUMBER+UNIT" — extract the exact quantity and unit from the document
4. Invoice unit price: "PRICE+CURRENCY" — extract from the INVOICE page (the page titled "INVOICE" with columns like "UNIT COST" and "TOTAL AMOUNT"), NOT from the customs declaration page's "Unit price of customs value" which is a different CIF-adjusted number. Use the ACTUAL currency shown on the invoice (could be THB, USD, EUR, etc.)
5. Commercial tax %: DECIMAL value. 0.05 means 5%. Extract from the document, do NOT assume a value
6. Exchange Rate (1): "CURRENCY RATE" — extract the actual exchange rate and currency from each item's section in the customs declaration

IMPORTANT FOR ITEMS:
- Extract ALL product items. Each "No. 001", "No. 002", etc. in the customs declaration is a separate item. The "Total items" field on the first page tells you how many items to expect.
- Each item may have a DIFFERENT customs duty rate. Some items may be FREE (0.0) while others are 15% (0.15). Extract each item's individual rate.
- The invoice currency is determined by the invoice page — look for "UNIT COST", "TOTAL AMOUNT", or "THE SUM OF" followed by a currency code.
- Extract the ACTUAL quantity from each item section. Different items have different quantities — do NOT copy the same quantity for all items.

═══════════════════════════════════════════════════════════════════

FORMAT 2: DOCUMENT HEADER (Single record for entire declaration)

Extract these 16 fields from the customs declaration pages:

1. Declaration No: The UNIQUE declaration/entry number for THIS specific document. It is typically a 12-digit number near "Declaration No" on the first page. Each document has its own unique number — NEVER reuse a number from a different document.
2. Declaration Date: Date in YYYY-MM-DD format, extracted from THIS document
3. Importer (Name): The ACTUAL company name of importer as written in the document
4. Consignor (Name): The ACTUAL company name of consignor/shipper as written on the CUSTOMS DECLARATION page (near "Consignor" field). Do NOT use the shipper name from Form D, Certificate of Origin, or Bill of Lading — use only the customs declaration page.
5. Invoice Number: The ACTUAL invoice reference number from the document (found on the invoice page or customs declaration page)
6. Invoice Price: Total invoice amount as NUMBER — this is the TOTAL from the invoice page, usually near "TOTAL TO BE PAID", "SUB TOTAL", or "Total item value". Extract the exact number shown.
7. Currency: The invoice currency code — determine from the invoice page (THB, USD, EUR, etc.). Do NOT guess — extract it.
8. Exchange Rate: Exchange rate as NUMBER. In Myanmar documents, commas are THOUSANDS separators (e.g., "2,100" means two thousand one hundred = 2100, NOT 2.1). Extract the full number.
9. Currency.1: Local currency code (typically MMK for Myanmar)
10. Total Customs Value: Total customs value as NUMBER (commas are thousands separators)
11. Import/Export Customs Duty: Total customs duty as NUMBER. If duty is FREE/exempt, use 0
12. Commercial Tax (CT): Commercial tax amount as NUMBER
13. Advance Income Tax (AT): Income tax amount as NUMBER
14. Security Fee (SF): Security fee as NUMBER
15. MACCS Service Fee (MF): MACCS service fee as NUMBER
16. Exemption/Reduction: Exemption/reduction amount as NUMBER (use 0 if none)

═══════════════════════════════════════════════════════════════════

Return ONLY this exact JSON structure:

{{
  "declaration": {{
    "Declaration No": "<EXTRACT from this document — unique 12-digit number>",
    "Declaration Date": "<EXTRACT YYYY-MM-DD from this document>",
    "Importer (Name)": "<EXTRACT actual company name>",
    "Consignor (Name)": "<EXTRACT actual company name>",
    "Invoice Number": "<EXTRACT actual invoice number>",
    "Invoice Price ": 0.0,
    "Currency": "<EXTRACT actual currency from invoice — THB or USD or other>",
    "Exchange Rate": 0.0,
    "Currency.1": "<EXTRACT local currency>",
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
      "Item name": "<EXTRACT actual product name from document>",
      "Customs duty rate": 0.0,
      "Quantity (1)": "<EXTRACT actual quantity+unit>",
      "Invoice unit price": "<EXTRACT actual price+currency>",
      "Commercial tax %": 0.0,
      "Exchange Rate (1)": "<EXTRACT actual currency and rate>"
    }}
  ]
}}

ALSO: For each item field, provide a confidence score (0.0 to 1.0) indicating how certain you are.
Add a "_confidence" key next to each field.

CRITICAL RULES:
- Extract ALL values from THIS document only. NEVER invent, guess, or reuse values from examples.
- If a field cannot be found in the document, use null for strings or 0.0 for numbers.
- Declaration No is UNIQUE per document — extract the specific number shown on THIS document's first page.
- Commas in numbers are THOUSANDS separators in Myanmar documents (72,802,800 = 72802800, NOT 72.8028).
- Determine the ACTUAL invoice currency by reading the invoice page — do NOT assume any default currency.
- Customs duty rate: extract each item's individual rate. "FREE" = 0.0, "5%" = 0.05, "15%" = 0.15.
- Use exact field names with spaces and parentheses as shown above.
- Declaration is SINGLE object, items is ARRAY.
- Use DECIMAL for percentages (0.15 not 15).
- Use NUMBER for all financial amounts (no commas, no currency symbols).
- Include _confidence scores for each item field.
- Return ONLY valid JSON."""


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

MAX_PAGES_FOR_API = 15  # Max pages to send to LLM to stay within token limits


def _select_key_pages(pdf_path: str, total_pages: int):
    """For large PDFs, identify the most important pages to send.
    Prioritizes: declaration pages, invoice pages, item detail pages.
    Returns list of 0-indexed page numbers."""
    if total_pages <= MAX_PAGES_FOR_API:
        return list(range(total_pages))

    doc = fitz.open(pdf_path)
    page_scores = []

    for i in range(total_pages):
        text = doc[i].get_text()
        score = 0
        text_upper = text.upper()

        # Declaration pages (highest priority)
        if 'DECLARATION NO' in text_upper or 'DECLARATION DATE' in text_upper:
            score += 100
        if 'CUSTOMS DUTY' in text_upper or 'CUSTOMS VALUE' in text_upper:
            score += 80
        if 'COMMERCIAL TAX' in text_upper or 'IMPORT/EXPORT' in text_upper:
            score += 70
        if 'ITEM NAME' in text_upper or 'RECONFIRMATION' in text_upper:
            score += 90

        # Invoice pages (high priority)
        if 'INVOICE' in text_upper and ('UNIT COST' in text_upper or 'TOTAL AMOUNT' in text_upper):
            score += 95
        if 'THE SUM OF' in text_upper:
            score += 85

        # Packing list (medium priority)
        if 'PACKING' in text_upper and 'LIST' in text_upper:
            score += 50

        # Skip low-value pages
        if 'IMPORT LICENCE' in text_upper or 'IMPORT RECOMMENDATION' in text_upper:
            score += 5
        if 'CERTIFICATE OF ORIGIN' in text_upper or 'FORM D' in text_upper:
            score += 5
        if 'BILL OF LADING' in text_upper:
            score += 10
        if 'REVENUE STAMP' in text_upper or 'ONLINE FEES' in text_upper:
            score += 0

        # Minimal text = likely image with stamps/signatures
        if len(text.strip()) < 50:
            score += 2

        page_scores.append((i, score))

    doc.close()

    # Sort by score descending, take top MAX_PAGES_FOR_API
    page_scores.sort(key=lambda x: x[1], reverse=True)
    selected = sorted([p[0] for p in page_scores[:MAX_PAGES_FOR_API]])

    print(f"  Smart page selection: {total_pages} pages → sending {len(selected)} key pages: {[p+1 for p in selected]}")
    return selected


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

    # Convert pages to images (smart selection for large PDFs)
    print("📄 Converting pages...", end=" ")
    total_pages = metadata['total_pages']
    key_pages = _select_key_pages(str(config.PDF_PATH), total_pages)
    images = convert_pdf_to_images(str(config.PDF_PATH), key_pages)
    print(f"✓ {len(images)} pages\n")

    # Load raw text from Step 2 as supplementary context
    raw_text_context = ""
    text_file = config.RESULTS_DIR / 'text_pages_raw.json'
    if text_file.exists():
        try:
            with open(text_file) as f:
                text_data = json.load(f)
            text_parts = []
            for key in sorted(text_data.keys()):
                page = text_data[key]
                if isinstance(page, dict) and page.get('text', '').strip():
                    text_parts.append(f"--- Page {page.get('page_number', key)} (raw text) ---\n{page['text'][:2000]}")
            if text_parts:
                raw_text_context = "\n\nRAW TEXT EXTRACTED FROM PDF (use this to verify values you read from images):\n" + "\n".join(text_parts[:10])
                print(f"📝 Added raw text context ({len(text_parts)} pages)\n")
        except Exception:
            pass

    # Build content
    content = []
    for img_b64 in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    content.append({"type": "text", "text": extraction_prompt + raw_text_context})

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

                # ── Post-extraction normalization for declaration ──
                if declaration:
                    # Strip currency prefix from Exchange Rate (should be a number)
                    exch = declaration.get('Exchange Rate')
                    if exch is not None and isinstance(exch, str):
                        nums = re.findall(r'[\d.]+', str(exch))
                        if nums:
                            try:
                                declaration['Exchange Rate'] = float(nums[0])
                            except ValueError:
                                pass

                    # Fix comma-as-decimal in numeric fields
                    # If a value looks like it was parsed with comma-as-decimal (e.g., 2.1 instead of 2100)
                    numeric_decl_fields = [
                        'Invoice Price ', 'Exchange Rate',
                        'Total Customs Value ', 'Import/Export Customs Duty ',
                        'Commercial Tax (CT)', 'Advance Income Tax (AT)',
                        'Security Fee (SF)', 'MACCS Service Fee (MF)', 'Exemption/Reduction'
                    ]
                    for field in numeric_decl_fields:
                        val = declaration.get(field)
                        if val is None:
                            # Try without trailing space
                            val = declaration.get(field.strip())
                        if isinstance(val, str):
                            # Remove any currency text, keep numbers
                            nums = re.findall(r'[\d.]+', val)
                            if nums:
                                try:
                                    declaration[field] = float(nums[0])
                                except ValueError:
                                    pass
        except Exception as e:
            print(f"⚠️  JSON parse error: {str(e)[:100]}")
            return None

        # Filter out invalid/junk/annotation rows
        JUNK_PATTERNS = [
            'all wrong', 'all informatio', 'color lists', 'not same',
            'incomplete', 'is wrong', 'are wrong', 'n/a', 'none',
        ]

        def _is_valid_item(item):
            name = str(item.get('Item name', '') or '').strip()
            if not name or name.lower() in ('nan', ''):
                return False
            # Check if it's a junk annotation
            name_lower = name.lower()
            if any(p in name_lower for p in JUNK_PATTERNS):
                return False
            # Check if all 6 fields are empty/None
            core_fields = ['Item name', 'Customs duty rate', 'Quantity (1)',
                          'Invoice unit price', 'Commercial tax %', 'Exchange Rate (1)']
            filled = sum(1 for f in core_fields if item.get(f) is not None and str(item.get(f)).strip() not in ('', 'nan', 'None'))
            if filled < 2:  # At least item name + 1 other field
                return False
            return True

        original_count = len(items)
        items = [item for item in items if _is_valid_item(item)]
        if len(items) < original_count:
            print(f"  Filtered out {original_count - len(items)} invalid/junk rows → {len(items)} valid items remain")

        # ── Post-extraction: fix ÷1000 errors in declaration financial amounts ──
        if declaration:
            def _get_decl_num(key):
                v = declaration.get(key)
                if v is None:
                    v = declaration.get(key.strip())
                try:
                    return float(v) if v is not None else None
                except (ValueError, TypeError):
                    return None

            def _set_decl(key, val):
                if key in declaration:
                    declaration[key] = val
                elif key.strip() in declaration:
                    declaration[key.strip()] = val

            total_cv = _get_decl_num('Total Customs Value ') or _get_decl_num('Total Customs Value')
            cd = _get_decl_num('Import/Export Customs Duty ') or _get_decl_num('Import/Export Customs Duty')
            ct = _get_decl_num('Commercial Tax (CT)')
            at = _get_decl_num('Advance Income Tax (AT)')
            sf = _get_decl_num('Security Fee (SF)')
            mf = _get_decl_num('MACCS Service Fee (MF)')

            # Detect ÷1000 pattern: if sum of taxes > total customs value, amounts are ÷1000
            if total_cv is not None and cd is not None:
                tax_sum = sum(x for x in [cd, ct, at] if x is not None and x > 0)
                if tax_sum > 0 and total_cv > 0 and tax_sum > total_cv * 0.8:
                    # Taxes exceed 80% of total customs value — likely all amounts are ÷1000
                    fix_fields = [
                        'Total Customs Value ', 'Total Customs Value',
                        'Import/Export Customs Duty ', 'Import/Export Customs Duty',
                        'Commercial Tax (CT)', 'Advance Income Tax (AT)',
                        'Security Fee (SF)', 'MACCS Service Fee (MF)', 'Exemption/Reduction'
                    ]
                    for fk in fix_fields:
                        v = _get_decl_num(fk)
                        if v is not None and v > 0:
                            _set_decl(fk, v * 1000)
                    print(f"  Auto-corrected declaration amounts (×1000 — comma-as-decimal detected)")
                elif total_cv > 0 and cd is not None and cd > total_cv:
                    # Just customs duty > total value — multiply all by 1000
                    fix_fields = [
                        'Total Customs Value ', 'Total Customs Value',
                        'Import/Export Customs Duty ', 'Import/Export Customs Duty',
                        'Commercial Tax (CT)', 'Advance Income Tax (AT)',
                        'Security Fee (SF)', 'MACCS Service Fee (MF)', 'Exemption/Reduction'
                    ]
                    for fk in fix_fields:
                        v = _get_decl_num(fk)
                        if v is not None and v > 0:
                            _set_decl(fk, v * 1000)
                    print(f"  Auto-corrected declaration amounts (×1000 — duty > total value)")

        # ── Post-extraction: fix item-level issues ──
        if items and declaration:
            decl_exch = _get_decl_num('Exchange Rate') or _get_decl_num('Exchange Rate ')
            decl_ccy = str(declaration.get('Currency', '') or '').strip().upper()

            for item in items:
                # Fix Exchange Rate (1): strip trailing junk, fill in rate from declaration
                exch_str = str(item.get('Exchange Rate (1)', '') or '').strip()
                if exch_str:
                    # Remove trailing dashes, dots, spaces
                    exch_str = exch_str.rstrip('-. ')
                    # If it's just a currency code with no number, add the declaration rate
                    exch_nums = re.findall(r'[\d,.]+', exch_str)
                    if not exch_nums and decl_exch and decl_ccy:
                        exch_str = f"{decl_ccy} {decl_exch:g}"
                    elif not exch_nums and decl_exch:
                        exch_str = f"{exch_str} {decl_exch:g}"
                    item['Exchange Rate (1)'] = exch_str

                # Fix Quantity: if qty looks like ÷1000 (e.g., "4 KG" when it should be "4284 KG")
                qty_str = str(item.get('Quantity (1)', '') or '')
                qty_nums = re.findall(r'[\d,.]+', qty_str)
                if qty_nums:
                    qty_val = float(qty_nums[0].replace(',', ''))
                    # If qty < 10 and price > 1, likely ÷1000 error
                    price_str = str(item.get('Invoice unit price', '') or '')
                    price_nums = re.findall(r'[\d.]+', price_str)
                    if price_nums:
                        price_val = float(price_nums[0])
                        if qty_val < 10 and price_val > 0.5:
                            # Suspiciously small qty — check if ×1000 makes it reasonable
                            corrected = qty_val * 1000
                            unit = re.findall(r'[A-Za-z]+', qty_str)
                            unit_str = unit[0] if unit else 'KG'
                            item['Quantity (1)'] = f"{corrected:g} {unit_str}"
                            print(f"  Auto-corrected item qty: {qty_val} → {corrected} {unit_str}")

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
