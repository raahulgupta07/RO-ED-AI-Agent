#!/usr/bin/env python3
"""
STEP 5: Cross-Validate Data
Verify consistency and completeness for BOTH items AND declaration
"""

import json
import re
from pathlib import Path
import config


PLACEHOLDER_PATTERNS = [
    'COMPANY NAME', 'PRODUCT (BRAND: NAME)', 'PRODUCT NAME',
    'C/O: COUNTRY', 'BRAND: NAME', 'INV-001', 'INVOICE-001',
    '<EXTRACT', '<extract', 'EXTRACT_FROM_DOCUMENT',
    'CURRENCY RATE', 'NUMBER+UNIT', 'PRICE+UNIT',
]


def _load_raw_text():
    """Load raw text from Step 2 for cross-checking LLM extraction."""
    text_file = config.RESULTS_DIR / 'text_pages_raw.json'
    if not text_file.exists():
        return ""
    try:
        with open(text_file) as f:
            data = json.load(f)
        # Combine all page text into one string
        all_text = ""
        if isinstance(data, dict):
            for key in sorted(data.keys()):
                page = data[key]
                if isinstance(page, dict):
                    all_text += page.get('text', '') + "\n"
                elif isinstance(page, str):
                    all_text += page + "\n"
        return all_text
    except Exception:
        return ""


def _find_declaration_no_in_text(raw_text):
    """Extract declaration number from raw text using regex.
    Declaration numbers are typically 12-digit numbers near 'Declaration No'."""
    # Look for 12-digit numbers near 'Declaration' keyword
    patterns = [
        r'Declaration\s*No[.\s:]*(\d{12})',
        r'Declaration\s*No[.\s:]*(\d{9,15})',
        r'\b(100\d{9})\b',  # Myanmar declaration numbers start with 100
    ]
    for pat in patterns:
        matches = re.findall(pat, raw_text, re.IGNORECASE)
        if matches:
            # Return the most common match (appears on multiple pages)
            from collections import Counter
            counter = Counter(matches)
            return counter.most_common(1)[0][0]
    return None


def _find_exchange_rate_in_text(raw_text):
    """Extract exchange rate from raw text.
    Looks for patterns like 'Exchange Rate (1) THB - 65.0025' or standalone rates."""
    # Strategy 1: Look near "Exchange Rate" keywords
    patterns = [
        r'Exchange\s*Rat\s*e\s*\(1\)\s*[A-Za-z]{2,4}\s*[-–]?\s*([\d,.]+[a-zA-Z]?)',
        r'Exchange\s*Rate\s*\(1\)\s*[A-Za-z]{2,4}\s*[-–]?\s*([\d,.]+[a-zA-Z]?)',
        r'Exchmge\s*Rat\s*e\s*\(1\)\s*\w+\s*[-–]?\s*([\d,.]+[a-zA-Z]?)',
        r'Exchange\s*Rate\s*[\s(1)]*\s*[-–:]\s*([\d,.]+[a-zA-Z]?)',
    ]
    for pat in patterns:
        matches = re.findall(pat, raw_text, re.IGNORECASE)
        if matches:
            for m in matches:
                cleaned = m.replace(',', '')
                # Handle OCR garble: trailing letter → 5 (common OCR error)
                cleaned = re.sub(r'[a-zA-Z]$', '5', cleaned)
                try:
                    val = float(cleaned)
                    if val > 1.0:
                        return val
                except ValueError:
                    continue

    # Strategy 2: Look for OCR-garbled rate patterns (XX.Xs where s is misread digit)
    # Common in scanned Myawaddy documents. THB rates are 50-70 range.
    garble_matches = re.findall(r'(\d{2}\.\d[a-zA-Z])', raw_text)
    for m in garble_matches:
        cleaned = re.sub(r'[a-zA-Z]$', '5', m)
        try:
            val = float(cleaned)
            if 50 < val < 70:  # THB exchange rate range for Myanmar
                return val
        except ValueError:
            continue

    # Strategy 3: Look for clean exchange rate numbers near currency keywords
    # USD rates are typically 2000-3000, THB rates 50-70
    for match in re.finditer(r'(THB|USD|MMK|ti\]B)', raw_text, re.IGNORECASE):
        nearby = raw_text[max(0, match.start()-50):match.end()+50]
        # Look for rate-like numbers (not prices — prices have 4+ decimals)
        nums = re.findall(r'\b(\d{2}\.\d{1,4})\b', nearby)
        for n in nums:
            try:
                val = float(n)
                if 50 < val < 70:  # THB range
                    return val
            except ValueError:
                continue
        # USD range with comma
        nums = re.findall(r'\b(\d{1,2}[,]\d{3})\b', nearby)
        for n in nums:
            try:
                val = float(n.replace(',', ''))
                if 1000 < val < 5000:
                    return val
            except ValueError:
                continue

    return None


def _find_quantities_in_text(raw_text):
    """Extract all quantity-like numbers from raw text (XXX.X KG patterns)."""
    quantities = set()
    # Match numbers followed by KG/KC/KGM (KC is OCR garble of KG)
    patterns = [
        r'([\d,]+\.?\d*)\s*K[GCg]',
        r'Quantity\s*\(1\)\s*\n?\s*([\d,.]+)\s*K[GCg]',
    ]
    for pat in patterns:
        matches = re.findall(pat, raw_text, re.IGNORECASE)
        for m in matches:
            try:
                val = float(m.replace(',', ''))
                if val > 10:
                    quantities.add(val)
            except ValueError:
                continue
    return quantities


def _find_closest_qty_in_text(extracted_qty, text_quantities, raw_text=""):
    """If extracted qty doesn't match any text qty, find the closest one.
    Returns corrected qty if a close match exists, else None.
    IMPORTANT: Only correct if the extracted value truly doesn't exist in the document."""
    if not text_quantities:
        return None

    # Check if extracted qty exists in text (exact or very close)
    for tq in text_quantities:
        if abs(extracted_qty - tq) < 0.01:
            return None  # Already correct

    # SAFETY CHECK: Before correcting, verify the extracted number
    # doesn't appear ANYWHERE in the raw text (not just near KG)
    if raw_text:
        # Check for the number in various formats: 17280, 17,280, 17280.0, 17280.0000
        ext_int = int(extracted_qty) if extracted_qty == int(extracted_qty) else None
        ext_str = f"{extracted_qty:g}"

        formats_to_check = [ext_str]
        if ext_int is not None:
            formats_to_check.append(str(ext_int))
            # With comma thousands separator
            formats_to_check.append(f"{ext_int:,}")
        # With decimals
        formats_to_check.append(f"{extracted_qty:.1f}")
        formats_to_check.append(f"{extracted_qty:.4f}")

        for fmt in formats_to_check:
            if fmt in raw_text:
                return None  # Number exists in document — don't correct

    # Find closest match within same order of magnitude
    best = None
    best_diff = float('inf')
    for tq in text_quantities:
        if tq == 0 or extracted_qty == 0:
            continue
        if min(extracted_qty, tq) < 0.001:
            continue
        ratio = max(extracted_qty, tq) / min(extracted_qty, tq)
        if ratio > 2:
            continue
        diff = abs(extracted_qty - tq)
        if diff < best_diff:
            best_diff = diff
            best = tq

    # Only correct if the difference looks like a digit misread (< 30% off)
    if best is not None and best_diff / max(extracted_qty, best) < 0.3:
        return best
    return None


def _is_placeholder(value):
    """Check if a value looks like a template placeholder."""
    s = str(value).strip().upper()
    return any(p.upper() in s for p in PLACEHOLDER_PATTERNS)


def validate_item_field(field_name, value):
    """Validate a single item field."""
    if value is None or value == '':
        return False, "Empty value"

    if _is_placeholder(value):
        return False, "Placeholder/template value detected — not extracted from document"

    if field_name == 'Item name':
        return (len(str(value)) >= 10, "Valid" if len(str(value)) >= 10 else "Too short")

    if field_name == 'Customs duty rate':
        if not isinstance(value, (int, float)):
            return False, "Not a number"
        return (0 <= value <= 1, "Valid" if 0 <= value <= 1 else "Out of range (should be 0-1)")

    if field_name == 'Quantity (1)':
        has_num = any(c.isdigit() for c in str(value))
        has_unit = any(c.isalpha() for c in str(value))
        return (has_num and has_unit, "Valid" if has_num and has_unit else "Missing number or unit")

    if field_name == 'Invoice unit price':
        has_num = any(c.isdigit() for c in str(value))
        return (has_num, "Valid" if has_num else "No price found")

    if field_name == 'Commercial tax %':
        if not isinstance(value, (int, float)):
            return False, "Not a number"
        return (0 <= value <= 1, "Valid" if 0 <= value <= 1 else "Out of range (should be 0-1)")

    if field_name == 'Exchange Rate (1)':
        s = str(value)
        has_num = any(c.isdigit() for c in s)
        if not has_num:
            return False, "No rate found"
        # Extract numeric part and check range
        import re as _re
        nums = _re.findall(r'[\d.]+', s)
        if nums:
            try:
                rate_val = float(nums[0])
                if rate_val < 1.0:
                    return False, f"Exchange rate {rate_val} is unreasonably low — check comma vs decimal"
            except ValueError:
                pass
        return True, "Valid"

    return True, "Valid"


def validate_decl_field(field_name, value):
    """Validate a single declaration field."""
    if value is None or str(value).strip() == '':
        return False, "Empty value"

    s = str(value).strip()

    if _is_placeholder(s):
        return False, "Placeholder/template value detected — not extracted from document"

    # Declaration No — should be non-empty string with digits
    if field_name == 'Declaration No':
        has_digit = any(c.isdigit() for c in s)
        return (has_digit and len(s) >= 5, "Valid" if has_digit and len(s) >= 5 else "Invalid declaration number")

    # Declaration Date — YYYY-MM-DD
    if field_name == 'Declaration Date':
        match = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', s))
        return (match, "Valid" if match else "Expected YYYY-MM-DD format")

    # Name fields — non-empty, reasonable length
    if field_name in ('Importer (Name)', 'Consignor (Name)'):
        return (len(s) >= 3, "Valid" if len(s) >= 3 else "Name too short")

    # Invoice Number — non-empty
    if field_name == 'Invoice Number':
        return (len(s) >= 2, "Valid" if len(s) >= 2 else "Too short")

    # Currency codes — 3 letters
    if field_name in ('Currency', 'Currency.1'):
        is_code = len(s) >= 2 and s.isalpha()
        return (is_code, "Valid" if is_code else "Expected currency code (e.g. THB, MMK)")

    # Exchange Rate — must be a reasonable number
    if field_name == 'Exchange Rate':
        try:
            num = float(value)
            if num < 0:
                return False, "Negative value"
            if 0 < num < 1.0:
                return False, f"Exchange rate {num} is unreasonably low — likely comma parsed as decimal (e.g., 2,100 read as 2.1)"
            return True, "Valid"
        except (ValueError, TypeError):
            # Could be a string like "THB 65.0025" — extract number
            import re as _re
            nums = _re.findall(r'[\d.]+', str(value))
            if nums:
                try:
                    num = float(nums[0])
                    if 0 < num < 1.0:
                        return False, f"Exchange rate {num} is unreasonably low"
                    return True, "Valid"
                except ValueError:
                    pass
            return False, "Not a valid number"

    # Numeric fields — must be a number >= 0
    numeric_fields = [
        'Invoice Price', 'Invoice Price ',
        'Total Customs Value', 'Total Customs Value ',
        'Import/Export Customs Duty', 'Import/Export Customs Duty ',
        'Commercial Tax (CT)', 'Advance Income Tax (AT)',
        'Security Fee (SF)', 'MACCS Service Fee (MF)', 'Exemption/Reduction'
    ]
    if field_name in numeric_fields:
        try:
            num = float(value)
            return (num >= 0, "Valid" if num >= 0 else "Negative value")
        except (ValueError, TypeError):
            return False, "Not a valid number"

    return True, "Valid"


def _get_decl_value(decl, field_name):
    """Flexible declaration field lookup (handles trailing spaces)."""
    val = decl.get(field_name)
    if val is None:
        val = decl.get(field_name + ' ')
    if val is None:
        val = decl.get(field_name.strip())
    if val is None:
        for k, v in decl.items():
            if k.strip().lower() == field_name.strip().lower():
                return v
    return val


def cross_validate():
    """Cross-validate extracted items AND declaration."""

    print("=" * 60)
    print("  STEP 5: CROSS-VALIDATE DATA (ITEMS + DECLARATION)")
    print("=" * 60)

    claude_file = config.RESULTS_DIR / 'claude_extracted.json'
    if not claude_file.exists():
        print("  ERROR: Run step4 first")
        return None

    with open(claude_file) as f:
        claude_data = json.load(f)

    items = claude_data.get('items', [])
    declaration = claude_data.get('declaration', {})

    # ── Validate Items (Format 1) ──
    item_field_names = ['Item name', 'Customs duty rate', 'Quantity (1)',
                        'Invoice unit price', 'Commercial tax %', 'Exchange Rate (1)']

    item_validations = []
    items_valid = 0
    items_total = 0

    if items:
        print(f"\n  Validating {len(items)} item(s)...")
        for i, item in enumerate(items, 1):
            item_val = {
                'item_number': i,
                'item_name': item.get('Item name', ''),
                'fields': {},
                'valid_fields': 0,
                'total_fields': 6,
                'is_valid': True
            }
            for fn in item_field_names:
                value = item.get(fn)
                is_valid, message = validate_item_field(fn, value)
                item_val['fields'][fn] = {'value': value, 'is_valid': is_valid, 'message': message}
                if is_valid:
                    item_val['valid_fields'] += 1
                else:
                    item_val['is_valid'] = False

            items_valid += item_val['valid_fields']
            items_total += 6
            item_validations.append(item_val)
            print(f"    Item {i}: {item_val['valid_fields']}/6 valid")
    else:
        print("  No items to validate")

    # ── Validate Declaration (Format 2) ──
    decl_field_names = [
        'Declaration No', 'Declaration Date', 'Importer (Name)', 'Consignor (Name)',
        'Invoice Number', 'Invoice Price', 'Currency', 'Exchange Rate', 'Currency.1',
        'Total Customs Value', 'Import/Export Customs Duty', 'Commercial Tax (CT)',
        'Advance Income Tax (AT)', 'Security Fee (SF)', 'MACCS Service Fee (MF)', 'Exemption/Reduction'
    ]

    decl_validations = {}
    decl_valid = 0
    decl_total = 0

    if declaration:
        print(f"\n  Validating declaration ({len(decl_field_names)} fields)...")
        for fn in decl_field_names:
            value = _get_decl_value(declaration, fn)
            is_valid, message = validate_decl_field(fn, value)
            decl_validations[fn] = {'value': value, 'is_valid': is_valid, 'message': message}
            decl_total += 1
            if is_valid:
                decl_valid += 1
            status = "ok" if is_valid else f"FAIL: {message}"
            print(f"    {fn}: {status}")
    else:
        print("  No declaration to validate")

    # ── Cross-field Validation ──
    cross_issues = []
    import re as _re

    if declaration and items:
        decl_currency = str(declaration.get('Currency', '')).strip().upper()
        if decl_currency:
            for i, item in enumerate(items):
                exch_str = str(item.get('Exchange Rate (1)', '')).upper()
                # Check if declared currency appears in item exchange rate
                if exch_str and decl_currency not in exch_str:
                    # Extract what currency IS in the exchange rate
                    found_curr = _re.findall(r'[A-Z]{2,4}', exch_str)
                    if found_curr and found_curr[0] != decl_currency:
                        msg = f"Item {i+1} exchange rate currency ({found_curr[0]}) doesn't match declaration currency ({decl_currency})"
                        cross_issues.append(msg)

    # Helper to extract numeric values from declaration (used in multiple sections below)
    def _get_num(key):
        if not declaration:
            return None
        val = _get_decl_value(declaration, key)
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            nums = _re.findall(r'[\d.]+', str(val))
            return float(nums[0]) if nums else None

    # Initialize variables used across sections
    total_cv = None
    customs_duty = None
    ct = None
    at = None
    exch_rate = None

    if declaration:
        # Financial sanity checks
        total_cv = _get_num('Total Customs Value')
        customs_duty = _get_num('Import/Export Customs Duty')
        ct = _get_num('Commercial Tax (CT)')
        at = _get_num('Advance Income Tax (AT)')
        exch_rate = _get_num('Exchange Rate')

        # Total Customs Value should be >= any individual tax/duty
        if total_cv is not None and customs_duty is not None:
            if customs_duty > 0 and total_cv < customs_duty:
                cross_issues.append(f"Total Customs Value ({total_cv}) is less than Customs Duty ({customs_duty}) — likely comma-as-decimal error")
        if total_cv is not None and ct is not None:
            if ct > 0 and total_cv < ct:
                cross_issues.append(f"Total Customs Value ({total_cv}) is less than Commercial Tax ({ct}) — likely comma-as-decimal error")

        # Exchange rate sanity for MMK (typically > 100)
        local_ccy = str(declaration.get('Currency.1', '')).strip().upper()
        if exch_rate is not None and exch_rate > 0:
            if local_ccy == 'MMK' and exch_rate < 100:
                cross_issues.append(f"Exchange Rate {exch_rate} for MMK is unreasonably low — commas may have been read as decimals (e.g., 2,100 → 2.1)")

        # Invoice Price sanity — should be positive
        inv_price = _get_num('Invoice Price')
        if inv_price is not None and inv_price == 0:
            cross_issues.append("Invoice Price is 0 — likely extraction error")

    # ── Text-based verification: cross-check LLM output against raw text ──
    raw_text = _load_raw_text()
    auto_fixes = []

    if raw_text and declaration:
        # FIX 0a: Declaration No — verify against raw text
        text_decl_no = _find_declaration_no_in_text(raw_text)
        extracted_decl_no = str(declaration.get('Declaration No', ''))
        if text_decl_no and text_decl_no != extracted_decl_no:
            auto_fixes.append(f"Declaration No: '{extracted_decl_no}' → '{text_decl_no}' (verified from raw text)")
            declaration['Declaration No'] = text_decl_no
            # Update validation
            if 'Declaration No' in decl_validations:
                decl_validations['Declaration No'] = {'value': text_decl_no, 'is_valid': True, 'message': 'Valid (text-verified)'}

        # FIX 0b: Exchange Rate — verify against raw text
        text_exch = _find_exchange_rate_in_text(raw_text)
        if text_exch:
            try:
                decl_exch = float(declaration.get('Exchange Rate', 0))
                # If text rate is very different from LLM rate, use text rate
                if decl_exch > 0 and text_exch > 0 and min(decl_exch, text_exch) > 0.001:
                    ratio = max(decl_exch, text_exch) / min(decl_exch, text_exch)
                    if ratio > 2:  # More than 2x difference
                        auto_fixes.append(f"Declaration Exchange Rate: {decl_exch} → {text_exch} (verified from raw text)")
                        declaration['Exchange Rate'] = text_exch
                elif decl_exch == 0 and text_exch > 0:
                    auto_fixes.append(f"Declaration Exchange Rate: 0 → {text_exch} (found in raw text)")
                    declaration['Exchange Rate'] = text_exch
            except (ValueError, TypeError):
                pass

    # ── Auto-correct: Fix items based on declaration data ──
    if declaration and items:
        decl_currency = str(declaration.get('Currency', '')).strip().upper()
        decl_exch_val = _get_num('Exchange Rate')

        for i, item in enumerate(items):
            # FIX 1: Customs duty rate — if declaration duty = 0, items should be 0.0
            if customs_duty is not None and customs_duty == 0:
                item_duty = item.get('Customs duty rate')
                if isinstance(item_duty, (int, float)) and item_duty > 0:
                    auto_fixes.append(f"Item {i+1}: Customs duty rate {item_duty} → 0.0 (declaration shows FREE/0 duty)")
                    item['Customs duty rate'] = 0.0
                    # Re-validate this field
                    for iv in item_validations:
                        if iv['item_number'] == i + 1:
                            iv['fields']['Customs duty rate'] = {'value': 0.0, 'is_valid': True, 'message': 'Valid (auto-corrected: FREE duty)'}
                            iv['valid_fields'] = sum(1 for f in iv['fields'].values() if f['is_valid'])

            # FIX 1b: Quantity — cross-check against raw text
            if raw_text:
                text_quantities = _find_quantities_in_text(raw_text)
                qty_str = str(item.get('Quantity (1)', '') or '')
                qty_nums = _re.findall(r'[\d,.]+', qty_str)
                if qty_nums and text_quantities:
                    try:
                        ext_qty = float(qty_nums[0].replace(',', ''))
                        corrected_qty = _find_closest_qty_in_text(ext_qty, text_quantities, raw_text)
                        if corrected_qty is not None:
                            unit = _re.findall(r'[A-Za-z]+', qty_str)
                            unit_str = unit[0] if unit else 'KG'
                            new_qty = f"{corrected_qty:g} {unit_str}"
                            auto_fixes.append(f"Item {i+1}: Quantity '{qty_str}' → '{new_qty}' (verified from raw text — {ext_qty} not found, closest match {corrected_qty})")
                            item['Quantity (1)'] = new_qty
                    except (ValueError, TypeError):
                        pass

            # FIX 2: Exchange Rate (1) — fix ÷1000 and wrong currency
            exch_str = str(item.get('Exchange Rate (1)', '') or '')
            exch_nums = _re.findall(r'[\d.]+', exch_str)
            if exch_nums:
                exch_val = float(exch_nums[0])
                # If exchange rate < 1.0 and declaration has a large rate, multiply by 1000
                if exch_val > 0 and exch_val < 1.0 and decl_exch_val and decl_exch_val > 100:
                    corrected = exch_val * 1000
                    new_exch = f"{decl_currency} {corrected:g}" if decl_currency else f"{corrected:g}"
                    auto_fixes.append(f"Item {i+1}: Exchange Rate (1) '{exch_str}' → '{new_exch}' (×1000 comma fix)")
                    item['Exchange Rate (1)'] = new_exch
                # If exchange rate > 1 but wrong currency vs declaration
                elif decl_currency and decl_exch_val:
                    found_curr = _re.findall(r'[A-Z]{2,4}', exch_str)
                    if found_curr and found_curr[0] != decl_currency:
                        new_exch = f"{decl_currency} {decl_exch_val:g}"
                        auto_fixes.append(f"Item {i+1}: Exchange Rate (1) currency '{found_curr[0]}' → '{decl_currency}' (match declaration)")
                        item['Exchange Rate (1)'] = new_exch

            # FIX 3: Invoice unit price currency — ensure matches declaration currency
            price_str = str(item.get('Invoice unit price', '') or '')
            if decl_currency and price_str:
                price_curr = _re.findall(r'[A-Z]{2,4}', price_str)
                if price_curr and price_curr[0] != decl_currency:
                    # Replace wrong currency with declaration currency
                    new_price = price_str.replace(price_curr[0], decl_currency)
                    auto_fixes.append(f"Item {i+1}: Invoice unit price currency '{price_curr[0]}' → '{decl_currency}' (match declaration)")
                    item['Invoice unit price'] = new_price

    # Recalculate items_valid/items_total after auto-corrections
    if auto_fixes:
        items_valid = 0
        items_total = 0
        for iv in item_validations:
            items_valid += iv['valid_fields']
            items_total += 6

    if auto_fixes:
        print(f"\n  Auto-corrections applied: {len(auto_fixes)}")
        for fix in auto_fixes:
            print(f"    FIXED: {fix}")

    if cross_issues:
        print(f"\n  Cross-validation issues:")
        for issue in cross_issues:
            print(f"    WARNING: {issue}")

    # ── Combined Stats ──
    total_fields = items_total + decl_total
    valid_fields = items_valid + decl_valid
    overall_accuracy = (valid_fields / total_fields * 100) if total_fields > 0 else 0

    items_accuracy = (items_valid / items_total * 100) if items_total > 0 else 0
    decl_accuracy = (decl_valid / decl_total * 100) if decl_total > 0 else 0

    # Field-level stats for items
    field_stats = {}
    for fn in item_field_names:
        valid = sum(1 for v in item_validations if v['fields'][fn]['is_valid'])
        total = len(item_validations) if item_validations else 0
        field_stats[fn] = {'valid': valid, 'total': total, 'accuracy': (valid / total * 100) if total > 0 else 0}

    # Add declaration field stats
    for fn, vd in decl_validations.items():
        field_stats[f"Decl: {fn}"] = {'valid': 1 if vd['is_valid'] else 0, 'total': 1, 'accuracy': 100.0 if vd['is_valid'] else 0.0}

    print(f"\n  Items accuracy: {items_accuracy:.1f}% ({items_valid}/{items_total})")
    print(f"  Declaration accuracy: {decl_accuracy:.1f}% ({decl_valid}/{decl_total})")
    print(f"  Overall accuracy: {overall_accuracy:.1f}% ({valid_fields}/{total_fields})")

    output_data = {
        'validation_timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
        'total_items': len(items),
        'total_fields': total_fields,
        'valid_fields': valid_fields,
        'overall_accuracy': overall_accuracy,
        'items_accuracy': items_accuracy,
        'items_valid': items_valid,
        'items_total': items_total,
        'decl_accuracy': decl_accuracy,
        'decl_valid': decl_valid,
        'decl_total': decl_total,
        'field_stats': field_stats,
        'item_validations': item_validations,
        'decl_validations': decl_validations,
        'cross_validation_issues': cross_issues,
    }

    # Save corrected items/declaration back to claude_extracted.json so downstream steps use fixed data
    if auto_fixes:
        claude_file = config.RESULTS_DIR / 'claude_extracted.json'
        if claude_file.exists():
            with open(claude_file) as f:
                claude_data = json.load(f)
            claude_data['items'] = items
            claude_data['declaration'] = declaration
            claude_data['auto_corrections'] = auto_fixes
            with open(claude_file, 'w', encoding='utf-8') as f:
                json.dump(claude_data, f, indent=2, ensure_ascii=False)
            print(f"  Saved {len(auto_fixes)} auto-corrections back to claude_extracted.json")

    output_file = config.RESULTS_DIR / 'validated_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {output_file}")
    print("=" * 60)

    return output_data


if __name__ == "__main__":
    cross_validate()
