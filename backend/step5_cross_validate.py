#!/usr/bin/env python3
"""
STEP 5: Cross-Validate Data
Verify consistency and completeness for BOTH items AND declaration
"""

import json
import re
from pathlib import Path
import config


def validate_item_field(field_name, value):
    """Validate a single item field."""
    if value is None or value == '':
        return False, "Empty value"

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
        has_num = any(c.isdigit() for c in str(value))
        return (has_num, "Valid" if has_num else "No rate found")

    return True, "Valid"


def validate_decl_field(field_name, value):
    """Validate a single declaration field."""
    if value is None or str(value).strip() == '':
        return False, "Empty value"

    s = str(value).strip()

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

    # Numeric fields — must be a number >= 0
    numeric_fields = [
        'Invoice Price', 'Invoice Price ', 'Exchange Rate',
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
    }

    output_file = config.RESULTS_DIR / 'validated_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {output_file}")
    print("=" * 60)

    return output_data


if __name__ == "__main__":
    cross_validate()
