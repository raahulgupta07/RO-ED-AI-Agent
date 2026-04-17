#!/usr/bin/env python3
"""
v2 Step 4: VALIDATOR
Cross-validate merged output. Reuses v1 business rules.
No LLM call.
"""

from typing import Dict, List


def validate(merged: Dict) -> Dict:
    """Validate merged declaration + items. Returns validation result with accuracy."""
    decl = merged.get("declaration", {})
    items = merged.get("items", [])
    cross_checks = merged.get("cross_checks", [])

    valid_fields = 0
    total_fields = 0
    issues = []

    # Declaration fields that are legitimately optional (may not exist on all documents)
    optional_decl_fields = {
        "Exemption/Reduction",   # most documents have 0 or no exemption
        "Security Fee (SF)",     # not all customs stations charge SF
        "Commercial Tax (CT)",   # some items/declarations are CT-exempt
    }

    # Validate declaration fields
    for key, val in decl.items():
        total_fields += 1
        if val is not None:
            valid_fields += 1
        elif key in optional_decl_fields:
            # Optional field — null is acceptable, count as valid
            valid_fields += 1
        else:
            issues.append(f"Declaration missing: {key}")

    # Validate items
    item_fields = ["Item name", "Customs duty rate", "Quantity (1)",
                   "Invoice unit price", "Commercial tax %", "Exchange Rate (1)"]
    for i, item in enumerate(items):
        for f in item_fields:
            total_fields += 1
            val = item.get(f)
            if val is not None and str(val).strip():
                valid_fields += 1
            else:
                issues.append(f"Item {i+1} missing: {f}")

    accuracy = (valid_fields / total_fields * 100) if total_fields > 0 else 0

    # Add cross-check results
    for cc in cross_checks:
        if isinstance(cc, dict) and cc.get("status") == "fail":
            issues.append(f"Cross-check failed: {cc.get('detail', '')}")
        elif isinstance(cc, str):
            issues.append(f"Cross-check: {cc}")

    print(f"  Validation: {valid_fields}/{total_fields} fields ({accuracy:.1f}%)")
    if issues:
        print(f"  Issues: {len(issues)}")
        for issue in issues[:5]:
            print(f"    - {issue}")

    return {
        "valid_fields": valid_fields,
        "total_fields": total_fields,
        "overall_accuracy": accuracy,
        "issues": issues,
        "cross_checks": cross_checks,
    }
