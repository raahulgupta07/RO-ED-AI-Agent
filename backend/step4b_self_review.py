#!/usr/bin/env python3
"""
STEP 4B: Self-Review Agent
Dash Agent reviews its own extraction output and corrects mistakes.
Common fixes: decimal vs percentage, missing units, formatting errors.
"""

import json
import time
import re
import base64
import requests
import fitz
import config

REVIEW_PROMPT = """You are a quality review agent. Below is extracted data from a Myanmar customs import document.
Review it against the document images provided and fix any issues.

COMMON ERRORS TO CHECK:
1. Customs duty rate should be DECIMAL (0.15 not 15). If > 1.0, divide by 100. If document shows "FREE" or customs duty amount is 0, rate MUST be 0.0.
2. Commercial tax % should be DECIMAL (0.05 not 5). If > 1.0, divide by 100.
3. Quantity should include UNIT (e.g., "16200KG" not "16200").
4. Invoice unit price should include the ACTUAL currency from the invoice page (e.g., "69.1358THB" if invoice is in THB, "23.2588USD" if invoice is in USD). Check the invoice to determine the correct currency — do NOT assume THB.
5. Exchange Rate should include the ACTUAL currency from the document (e.g., "THB 65.0025" or "USD 2100"). Check the declaration pages to determine the correct currency — do NOT default to THB.
6. Financial amounts in declaration should be NUMBERS (no commas, no currency symbols). Remember: commas are THOUSANDS separators in Myanmar documents (2,100 = 2100, NOT 2.1).
7. Declaration date should be YYYY-MM-DD format.
8. All fields must be non-empty. Use 0 for missing numeric fields.
9. Check if any value looks like a PLACEHOLDER or TEMPLATE text (e.g., "COMPANY NAME", "INV-001", "PRODUCT (BRAND: NAME)", "COUNTRY"). These indicate extraction failure — look at the document images and extract the REAL values.
10. Verify the Declaration No matches what is shown on THIS document's first page. Each document has a unique Declaration No.
11. Verify customs duty rate matches the document. Do NOT confuse customs duty rate with commercial tax %. They are separate fields — customs duty can be FREE (0.0) while commercial tax is 5% (0.05).

EXTRACTED DATA:
{extracted_json}

Return a JSON object with EXACTLY this structure:
{{
  "corrections": [
    {{"item_index": 0, "field": "field_name", "old_value": "old", "new_value": "corrected", "reason": "explanation"}}
  ],
  "declaration_corrections": [
    {{"field": "field_name", "old_value": "old", "new_value": "corrected", "reason": "explanation"}}
  ],
  "corrected_items": [... full corrected items array ...],
  "corrected_declaration": {{... full corrected declaration object ...}}
}}

If no corrections needed, return empty corrections arrays but still return the full data.
Return ONLY valid JSON."""


def self_review(extracted_data):
    """Review extraction output and correct common errors."""

    print("=" * 60)
    print("  STEP 4B: SELF-REVIEW AGENT")
    print("=" * 60)

    if not extracted_data:
        print("  No data to review")
        return extracted_data

    items = extracted_data.get('items', [])
    declaration = extracted_data.get('declaration', {})

    if not items and not declaration:
        print("  No items or declaration to review")
        return extracted_data

    # Build review payload
    review_data = {
        "items": items,
        "declaration": declaration
    }

    prompt = REVIEW_PROMPT.format(extracted_json=json.dumps(review_data, indent=2, default=str))

    # Build content with document images so reviewer can verify against source
    msg_content = []
    if config.PDF_PATH:
        try:
            doc = fitz.open(str(config.PDF_PATH))
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(config.EXTRACTION_RESOLUTION, config.EXTRACTION_RESOLUTION))
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                msg_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                })
            doc.close()
        except Exception:
            pass
    msg_content.append({"type": "text", "text": prompt})

    payload = {
        "model": config.REVIEW_MODEL,
        "messages": [{"role": "user", "content": msg_content}],
        "temperature": 0,
        "max_tokens": 6000
    }

    print(f"  Reviewing {len(items)} items + declaration...")
    print("  Talking to LLM...", end=" ")
    start_time = time.time()

    # Call with retry
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
        except Exception:
            pass
        if attempt < config.MAX_RETRIES - 1:
            wait = config.RETRY_BACKOFF_BASE ** (attempt + 1)
            time.sleep(wait)

    duration = time.time() - start_time

    if not response or response.status_code != 200:
        print(f"FAILED — keeping original data")
        return extracted_data

    try:
        content_text = response.json()["choices"][0]["message"]["content"]
        cleaned = re.sub(r'```json\n?|```\n?', '', content_text).strip()

        if '{' in cleaned:
            start_idx = cleaned.index('{')
            end_idx = cleaned.rindex('}') + 1
            review_result = json.loads(cleaned[start_idx:end_idx])
        else:
            print(f"No JSON in response — keeping original")
            return extracted_data

        corrections = review_result.get('corrections', [])
        decl_corrections = review_result.get('declaration_corrections', [])

        print(f"Done ({duration:.1f}s)")
        print()

        # Log corrections
        if corrections:
            print(f"  Corrections found: {len(corrections)} item fields")
            for c in corrections:
                print(f"    Item {c.get('item_index', '?')}: {c.get('field', '?')} — {c.get('old_value', '?')} → {c.get('new_value', '?')} ({c.get('reason', '')})")
        if decl_corrections:
            print(f"  Declaration corrections: {len(decl_corrections)} fields")
            for c in decl_corrections:
                print(f"    {c.get('field', '?')} — {c.get('old_value', '?')} → {c.get('new_value', '?')} ({c.get('reason', '')})")

        if not corrections and not decl_corrections:
            print("  No corrections needed — data looks clean")

        # Apply corrections
        corrected_items = review_result.get('corrected_items', items)
        corrected_declaration = review_result.get('corrected_declaration', declaration)

        # Update extracted data
        result = dict(extracted_data)
        result['items'] = corrected_items
        result['declaration'] = corrected_declaration
        result['review_corrections'] = len(corrections) + len(decl_corrections)
        result['review_details'] = corrections + decl_corrections
        result['review_duration'] = duration

        print()
        print(f"  Review complete: {len(corrections) + len(decl_corrections)} corrections applied")
        print("=" * 60)

        return result

    except Exception as e:
        print(f"Parse error: {str(e)[:100]} — keeping original data")
        return extracted_data


if __name__ == "__main__":
    # Test with existing extraction
    claude_file = config.RESULTS_DIR / 'claude_extracted.json'
    if claude_file.exists():
        with open(claude_file) as f:
            data = json.load(f)
        result = self_review(data)
        print(f"\nCorrections: {result.get('review_corrections', 0)}")
