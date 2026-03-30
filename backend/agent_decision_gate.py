#!/usr/bin/env python3
"""
AGENT: Decision Gate
After validation, decides: ACCEPT / FIX_FIELDS / FULL_RETRY / ESCALATE
Then executes the chosen action (re-extraction, field fixes, etc.)
"""

import json
import time
import re
import requests
import base64
import fitz
import config

# Field-specific re-extraction prompt
FIX_FIELDS_PROMPT = """You previously extracted data from a Myanmar customs document but some fields failed validation.

ORIGINAL EXTRACTION:
{original_json}

FAILED FIELDS:
{failed_fields}

Please re-extract ONLY the failed fields listed above. Look carefully at the document images and correct the values.

Return a JSON object with ONLY the corrected fields:
{{
  "fixed_items": [
    {{"item_index": 0, "field": "Customs duty rate", "corrected_value": 0.15}}
  ],
  "fixed_declaration": [
    {{"field": "Exchange Rate", "corrected_value": 65.0025}}
  ]
}}

Return ONLY valid JSON."""


def _check_low_confidence_fields(extracted_data):
    """Count fields with confidence below threshold."""
    low_conf = []
    for i, item in enumerate(extracted_data.get('items', [])):
        for key in ['Item name', 'Customs duty rate', 'Quantity (1)',
                     'Invoice unit price', 'Commercial tax %', 'Exchange Rate (1)']:
            conf_key = f"{key}_confidence"
            conf = item.get(conf_key)
            if conf is not None and float(conf) < config.CONFIDENCE_THRESHOLD:
                low_conf.append({'item_index': i, 'field': key, 'confidence': conf})
    return low_conf


def decide(validation_result, extracted_data=None):
    """Decide what action to take based on validation accuracy + confidence scores."""
    accuracy = validation_result.get('overall_accuracy', 0)

    # Check confidence scores — downgrade decision if many low-confidence fields
    low_conf = []
    if extracted_data:
        low_conf = _check_low_confidence_fields(extracted_data)
        if low_conf and accuracy >= config.ACCURACY_ACCEPT:
            # High accuracy but low confidence — trust the validation less, fix those fields
            return "FIX_FIELDS", f"Accuracy {accuracy:.1f}% but {len(low_conf)} low-confidence fields — fixing"

    if accuracy >= config.ACCURACY_ACCEPT:
        return "ACCEPT", f"Accuracy {accuracy:.1f}% >= {config.ACCURACY_ACCEPT}% threshold"
    elif accuracy >= config.ACCURACY_FIX:
        return "FIX_FIELDS", f"Accuracy {accuracy:.1f}% — fixing invalid fields"
    elif accuracy >= config.ACCURACY_RETRY:
        return "FULL_RETRY", f"Accuracy {accuracy:.1f}% — full re-extraction needed"
    else:
        return "ESCALATE", f"Accuracy {accuracy:.1f}% < {config.ACCURACY_RETRY}% — needs human review"


def get_failed_fields(validation_result, extracted_data=None):
    """Extract list of failed fields from validation result + low-confidence fields."""
    failed = []
    seen = set()

    for item_val in validation_result.get('item_validations', []):
        item_num = item_val.get('item_number', 0)
        for field_name, field_data in item_val.get('fields', {}).items():
            if not field_data.get('is_valid', True):
                failed.append({
                    'item_index': item_num - 1,
                    'field': field_name,
                    'current_value': field_data.get('value', ''),
                    'reason': field_data.get('message', '')
                })
                seen.add((item_num - 1, field_name))

    # Also include low-confidence fields that passed validation
    if extracted_data:
        for lc in _check_low_confidence_fields(extracted_data):
            key = (lc['item_index'], lc['field'])
            if key not in seen:
                items = extracted_data.get('items', [])
                idx = lc['item_index']
                failed.append({
                    'item_index': idx,
                    'field': lc['field'],
                    'current_value': items[idx].get(lc['field'], '') if idx < len(items) else '',
                    'reason': f"Low confidence ({lc['confidence']:.2f})"
                })

    return failed


def _get_pdf_images():
    """Load all PDF pages as base64 images for LLM context."""
    if not config.PDF_PATH:
        return []
    try:
        doc = fitz.open(str(config.PDF_PATH))
        images = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(config.EXTRACTION_RESOLUTION, config.EXTRACTION_RESOLUTION))
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            images.append(img_b64)
        doc.close()
        return images
    except Exception:
        return []


def fix_fields(extracted_data, failed_fields, images_content=None):
    """Re-extract only the failed fields via targeted LLM call with document images."""

    failed_desc = json.dumps(failed_fields, indent=2, default=str)
    original = json.dumps({
        'items': extracted_data.get('items', []),
        'declaration': extracted_data.get('declaration', {})
    }, indent=2, default=str)

    prompt = FIX_FIELDS_PROMPT.format(
        original_json=original,
        failed_fields=failed_desc
    )

    # Build content with document images so LLM can see the source
    content = []
    pdf_images = images_content or _get_pdf_images()
    for img_b64 in pdf_images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": config.EXTRACTION_MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": 4000
    }

    print("  Talking to LLM (targeted fix)...", end=" ")

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
            time.sleep(config.RETRY_BACKOFF_BASE ** (attempt + 1))

    if not response or response.status_code != 200:
        print("FAILED")
        return extracted_data, 0

    try:
        content_text = response.json()["choices"][0]["message"]["content"]
        cleaned = re.sub(r'```json\n?|```\n?', '', content_text).strip()

        if '{' in cleaned:
            start_idx = cleaned.index('{')
            end_idx = cleaned.rindex('}') + 1
            fix_result = json.loads(cleaned[start_idx:end_idx])
        else:
            print("No JSON — keeping original")
            return extracted_data, 0

        # Apply item fixes
        items = extracted_data.get('items', [])
        fixes_applied = 0

        for fix in fix_result.get('fixed_items', []):
            idx = fix.get('item_index', -1)
            field = fix.get('field', '')
            value = fix.get('corrected_value')
            if 0 <= idx < len(items) and field:
                items[idx][field] = value
                fixes_applied += 1
                print(f"\n    Fixed item {idx}: {field} = {value}", end="")

        # Apply declaration fixes
        declaration = extracted_data.get('declaration', {})
        for fix in fix_result.get('fixed_declaration', []):
            field = fix.get('field', '')
            value = fix.get('corrected_value')
            if field:
                declaration[field] = value
                fixes_applied += 1
                print(f"\n    Fixed declaration: {field} = {value}", end="")

        print(f"\n  Applied {fixes_applied} fixes")

        result = dict(extracted_data)
        result['items'] = items
        result['declaration'] = declaration
        return result, fixes_applied

    except Exception as e:
        print(f"Parse error: {str(e)[:80]}")
        return extracted_data, 0


def run_decision_gate(extracted_data, validation_result, cross_validate_func, accuracy_func):
    """
    Run the decision gate agent.
    Returns: (final_extracted_data, final_validation, final_accuracy, gate_log)
    """

    gate_log = []
    action, reason = decide(validation_result, extracted_data)
    gate_log.append(f"Decision: {action} — {reason}")

    # Log low-confidence fields if any
    low_conf = _check_low_confidence_fields(extracted_data)
    if low_conf:
        gate_log.append(f"Low-confidence fields: {len(low_conf)}")
        for lc in low_conf[:5]:
            gate_log.append(f"  Item {lc['item_index']}: {lc['field']} (conf: {lc['confidence']:.2f})")

    if action == "ACCEPT":
        gate_log.append("Accepted — no further action needed")
        accuracy = accuracy_func()
        return extracted_data, validation_result, accuracy, gate_log

    elif action == "FIX_FIELDS":
        failed = get_failed_fields(validation_result, extracted_data)
        gate_log.append(f"Failed fields: {len(failed)}")

        for cycle in range(config.MAX_FIX_CYCLES):
            gate_log.append(f"Fix cycle {cycle + 1}/{config.MAX_FIX_CYCLES}")

            extracted_data, fixes = fix_fields(extracted_data, failed)
            gate_log.append(f"Applied {fixes} fixes")

            if fixes == 0:
                gate_log.append("No fixes applied — accepting current result")
                break

            # Save updated extraction and re-validate
            _save_extraction(extracted_data)
            validation_result = cross_validate_func()
            new_accuracy = validation_result.get('overall_accuracy', 0)
            gate_log.append(f"New accuracy: {new_accuracy:.1f}%")

            if new_accuracy >= config.ACCURACY_ACCEPT:
                gate_log.append(f"Accuracy now >= {config.ACCURACY_ACCEPT}% — accepted")
                break

            # Update failed fields for next cycle
            failed = get_failed_fields(validation_result, extracted_data)
            if not failed:
                break

        accuracy = accuracy_func()
        return extracted_data, validation_result, accuracy, gate_log

    elif action == "FULL_RETRY":
        import step4_claude_structured_extraction
        import step4b_self_review

        for retry in range(config.MAX_FULL_RETRIES):
            gate_log.append(f"Full re-extraction attempt {retry + 1}/{config.MAX_FULL_RETRIES}")

            new_extracted = step4_claude_structured_extraction.extract_structured_data()
            if not new_extracted:
                gate_log.append("Re-extraction failed — keeping previous result")
                break

            new_extracted = step4b_self_review.self_review(new_extracted)
            _save_extraction(new_extracted)
            validation_result = cross_validate_func()
            new_accuracy = validation_result.get('overall_accuracy', 0)
            gate_log.append(f"Re-extraction accuracy: {new_accuracy:.1f}%")

            # Compare against previous validation accuracy, not completeness
            prev_accuracy = validation_result.get('overall_accuracy', 0)
            if new_accuracy > prev_accuracy:
                extracted_data = new_extracted
                gate_log.append("Re-extraction improved results — accepted")
            else:
                gate_log.append("Re-extraction did not improve — keeping previous result")
                _save_extraction(extracted_data)
                validation_result = cross_validate_func()

            if new_accuracy >= config.ACCURACY_ACCEPT:
                gate_log.append(f"Accuracy now >= {config.ACCURACY_ACCEPT}% — accepted")
                break

        accuracy = accuracy_func()
        return extracted_data, validation_result, accuracy, gate_log

    else:  # ESCALATE
        gate_log.append("Flagged for human review — saving partial results")
        accuracy = accuracy_func()
        return extracted_data, validation_result, accuracy, gate_log


def _save_extraction(extracted_data):
    """Save updated extraction data to disk for downstream steps."""
    output_file = config.RESULTS_DIR / 'claude_extracted.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
