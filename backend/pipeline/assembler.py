#!/usr/bin/env python3
"""
Master + Column Agent Assembler
Each table has a Master Agent. Each column has its own focused instruction.
Nothing gets missed — every field has a dedicated agent responsible for finding it.
"""

import json
import re
import requests
import time
from typing import Dict, List, Optional

import config

try:
    import cost_tracker
except ImportError:
    cost_tracker = None


# ═══════════════════════════════════════════════════════════════
# LLM CALL
# ═══════════════════════════════════════════════════════════════

def _call_llm(prompt: str, data: str, model: str = None, label: str = "assembler",
              response_schema: Dict = None) -> Optional[Dict]:
    """Send prompt + data to LLM, parse JSON response.
    If response_schema provided, uses json_schema mode for guaranteed valid output.
    """
    model = model or config.EXTRACTION_MODEL

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt + "\n\n" + data}],
        "temperature": 0,
        "max_tokens": 16000,
    }

    # Add structured output if schema provided
    if response_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": response_schema,
        }

    for attempt in range(3):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {config.API_KEY}", "Content-Type": "application/json"},
                json=payload, timeout=config.API_TIMEOUT,
            )
            if resp.status_code == 200:
                result = resp.json()
                if cost_tracker:
                    cost_tracker.record(label, result, model)
                content = result["choices"][0]["message"]["content"].strip()
                # With json_schema, response is already clean JSON
                if response_schema:
                    return json.loads(content)
                # Without schema, need cleanup
                cleaned = re.sub(r'```json\n?|```\n?', '', content).strip()
                if '{' in cleaned:
                    return json.loads(cleaned[cleaned.index('{'):cleaned.rindex('}') + 1])
            elif resp.status_code == 429:
                time.sleep(2 ** (attempt + 1))
                continue
        except json.JSONDecodeError as e:
            print(f"    {label} JSON error: {e}")
        except Exception as e:
            print(f"    {label} error: {e}")
        if attempt < 2:
            time.sleep(2 ** (attempt + 1))
    return None


def _build_page_summary(page_results: List[Dict]) -> str:
    """Build compact text summary of all page extractions.
    Only includes fields, tables, and amounts — no document metadata, visual info, or entities.
    Deduplicates fields with same value but different key names.
    """
    parts = []
    for pr in page_results:
        if pr.get("status") != "ok":
            continue
        pn = pr["page_number"]
        pt = pr.get("page_type", "unknown")
        parsed = pr.get("parsed", {})
        part = f"\n--- PAGE {pn} ({pt}) ---\n"

        # Fields — deduplicate values (keep first occurrence of each unique value)
        fields = parsed.get("fields", {})
        if fields:
            seen_values = set()
            part += "Fields:\n"
            for k, v in fields.items():
                val_str = str(v).strip().lower() if v else ""
                # Skip if exact same value already added (dedup)
                dedup_key = f"{val_str}"
                if val_str and len(val_str) > 2 and dedup_key in seen_values:
                    continue
                if val_str and len(val_str) > 2:
                    seen_values.add(dedup_key)
                part += f"  {k}: {v}\n"

        # Tables — keep all (critical for items extraction)
        for ti, table in enumerate(parsed.get("tables", [])):
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            title = table.get("title", f"Table {ti+1}")
            part += f"\nTable: {title}\n"
            if headers:
                part += f"  Headers: {' | '.join(str(h) for h in headers)}\n"
            for row in rows:
                part += f"  Row: {' | '.join(str(c) for c in row)}\n"

        # Amounts — keep (useful for tax/duty values)
        amounts = parsed.get("amounts", [])
        if amounts:
            part += "Amounts:\n"
            for a in amounts:
                part += f"  {a.get('label', '?')}: {a.get('value', '?')} {a.get('currency', '')}\n"

        # REMOVED: document metadata, visual info, entities (assembler doesn't use them)
        parts.append(part)
    return "".join(parts)


def _build_corrections_prompt() -> str:
    """Query past corrections from DB as few-shot examples."""
    try:
        import database
        corrections = database.get_corrections(limit=20)
        if not corrections:
            return ""
        by_field = {}
        for c in corrections:
            field = c.get("field_key", "")
            if field not in by_field:
                by_field[field] = []
            by_field[field].append(c)
        lines = ["\n## LEARNED FROM PAST CORRECTIONS:"]
        for field, corrs in by_field.items():
            seen = set()
            for c in corrs:
                key = f"{c.get('original_value')}→{c.get('corrected_value')}"
                if key not in seen:
                    seen.add(key)
                    lines.append(f"- {field}: \"{c.get('original_value')}\" → \"{c.get('corrected_value')}\"")
                if len(seen) >= 3:
                    break
        print(f"    Injecting {len(corrections)} corrections into prompt")
        return "\n".join(lines) + "\n"
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# MASTER AGENT 1: DECLARATION (16 column agents in one call)
# ═══════════════════════════════════════════════════════════════

DECLARATION_PROMPT = """You are the DECLARATION MASTER AGENT. You have 16 column agents, each responsible for finding ONE field.

Search ALL pages and fill EVERY field. Return ONLY valid JSON.

## YOUR 16 COLUMN AGENTS — each one searches ALL pages for its specific field:

AGENT 1 — Declaration No:
  Search for: customs declaration number, entry number, release order number
  Usually on the first page. Copy the exact number.

AGENT 2 — Declaration Date:
  Search for: declaration date, entry date
  Convert to YYYY-MM-DD format.

AGENT 3 — Importer (Name):
  Search for: importer name, buyer, importing company
  Return the FULL company name, not the code/ID.

AGENT 4 — Consignor (Name):
  Search for: consignor, exporter, shipper, seller
  Return the full company name.

AGENT 5 — Invoice Number:
  Search for: invoice number, invoice no, commercial invoice
  Include any prefix (A-, B-, etc.)

AGENT 6 — Invoice Price:
  Search for: invoice price, total invoice amount, invoice value
  Return the total amount in FOREIGN currency (USD, THB, EUR, etc.), NOT in local currency (MMK/Kyat).
  Look on the customs declaration — the field labeled "Invoice Price" or "Invoice Value".
  Do NOT use CIF value — that may include insurance and freight.

AGENT 7 — Currency:
  Search for: the 3-letter currency code of the invoice price
  Examples: USD, THB, EUR, JPY, CNY, KRW, INR, SGD, etc.

AGENT 8 — Exchange Rate:
  Search for: exchange rate, conversion rate, FX rate
  This is the rate to convert foreign currency to local currency (MMK).

AGENT 9 — Total Customs Value:
  Search for: total customs value, total CIF value in local currency
  Look for the field labeled "Total Customs Value" or "Total CIF Value" on the customs declaration.
  Return the amount in local currency (MMK/Kyat) as printed on the document.

AGENT 10 — Import/Export Customs Duty:
  Search for: customs duty, import duty, duty amount
  Look in tax tables, fees sections. If duty is FREE or exempt, return 0.

AGENT 11 — Commercial Tax (CT):
  Search for: commercial tax, CT, VAT, GST, sales tax
  Look in tax tables, fees sections. If exempt, return 0.

AGENT 12 — Advance Income Tax (AT):
  Search for: advance income tax, AT, withholding tax, income tax
  Look in tax tables, fees sections.

AGENT 13 — Security Fee (SF):
  Search for: security fee, SF
  Return 0 if not present.

AGENT 14 — MACCS Service Fee (MF):
  Search for: MACCS fee, MF, system service fee, processing fee
  Return 0 if not present.

AGENT 15 — Exemption/Reduction:
  Search for: exemption, reduction, deduction, discount
  Return 0 if none.

AGENT 16 — Currency 2:
  Same as Currency (Agent 7).

## OUTPUT FORMAT:
{
  "Declaration No": <value>,
  "Declaration Date": <value>,
  "Importer (Name)": <value>,
  "Consignor (Name)": <value>,
  "Invoice Number": <value>,
  "Invoice Price": <numeric>,
  "Currency": <value>,
  "Currency 2": <value>,
  "Exchange Rate": <numeric>,
  "Total Customs Value": <numeric>,
  "Import/Export Customs Duty": <numeric>,
  "Commercial Tax (CT)": <numeric>,
  "Advance Income Tax (AT)": <numeric>,
  "Security Fee (SF)": <numeric>,
  "MACCS Service Fee (MF)": <numeric>,
  "Exemption/Reduction": <numeric>
}

RULES:
- Each agent searches ALL pages independently.
- Read EXACT values from the document. Do NOT calculate or guess.
- Taxes: read from tax tables or fee sections. Use 0 for FREE/exempt.
- Return ONLY valid JSON.

## PAGE DATA:
"""


# ═══════════════════════════════════════════════════════════════
# MASTER AGENT 2: ITEMS (9 column agents in one call)
# ═══════════════════════════════════════════════════════════════

ITEMS_PROMPT_TEMPLATE = """You are the ITEMS MASTER AGENT. You have 9 column agents, each responsible for finding ONE field for EVERY product item.

The declaration has already been extracted:
  Exchange Rate = {exchange_rate}
  Currency = {currency}

Search ALL pages and fill EVERY field for EVERY item. Return ONLY valid JSON.

## YOUR 9 COLUMN AGENTS — each searches ALL pages for its specific field:

AGENT 1 — Item name:
  Search for: product description, goods description, item name
  Look in invoices, item tables, customs declarations.
  Return an array with one name per item.

AGENT 2 — Quantity (1):
  Search for: quantity, qty, amount, pieces, weight
  Include the unit (KG, PCS, CTN, L, etc.) — e.g. "500 KG"
  Look in invoices, packing lists, item tables.

AGENT 3 — Invoice unit price:
  Search for: "Invoice unit price" field on the CUSTOMS DECLARATION pages.
  Look for the field labeled exactly "Invoice unit price" — it shows the price per unit.
  Do NOT use "Unit Cost" from invoice tables — that may be a different value (CIF/FOB cost).
  The customs declaration's "Invoice unit price" field is the most reliable source.
  If there are multiple prices, use the HIGHER one (the actual invoice price is always higher than CIF cost).
  Return in FOREIGN currency (not local/MMK).
  Read the EXACT value from the document. Do NOT calculate.

AGENT 4 — Customs Value (MMK):
  Search for: customs value per item in LOCAL currency (MMK/Kyat)
  Look in customs declaration item rows — the column labeled "Customs Value" or "CIF Value (MMK)".
  This is usually a LARGE number (millions in MMK).
  Read the EXACT value from the document. Do NOT calculate.

AGENT 5 — Customs duty rate:
  Search for: duty rate, tariff rate, import duty percentage PER ITEM
  Look for the rate printed on the customs declaration for each item row (e.g. "15%", "M-15", "5%").
  Return as DECIMAL (e.g. 0.15 for 15%, 0.05 for 5%).
  If FREE or exempt, return 0.
  Read the EXACT rate from the document. Do NOT calculate from totals.

AGENT 6 — Commercial tax %:
  Search for: commercial tax rate, CT rate PER ITEM
  Look for the tax rate printed on the customs declaration for each item row (e.g. "5%", "CT 5%").
  Return as DECIMAL (e.g. 0.05 for 5%).
  If exempt or zero, return 0.
  Read the EXACT rate from the document. Do NOT calculate from totals.

AGENT 7 — HS Code:
  Search for: HS code, tariff code, harmonized system code
  Return the FULL code with dots (e.g. "1104.12.00 00").
  Look in customs declarations, import licences.

AGENT 8 — Origin Country:
  Search for: country of origin, origin, country
  Return the full country name or 2-letter code.
  Look in customs declarations, certificates of origin, invoices.

AGENT 9 — Exchange Rate (1):
  Use the declaration exchange rate: {exchange_rate}

## OUTPUT FORMAT:
{{
  "items": [
    {{
      "Item name": "<value>",
      "Quantity (1)": "<qty with unit>",
      "Invoice unit price": <numeric>,
      "Customs Value (MMK)": <numeric>,
      "Customs duty rate": <decimal>,
      "Commercial tax %": <decimal>,
      "HS Code": "<value>",
      "Origin Country": "<value>",
      "Exchange Rate (1)": <numeric>
    }}
  ]
}}

CRITICAL RULES:
- You MUST fill ALL 9 fields for EVERY item. No nulls allowed.
- Read EVERY value directly from the document. Do NOT calculate or guess.
- Exchange Rate is ALWAYS {exchange_rate} — just copy it.
- Duty rate and tax %: READ from the customs declaration per-item rows. Do NOT divide totals.
- Return ONLY valid JSON.

## PAGE DATA:
"""




# ═══════════════════════════════════════════════════════════════
# MASTER ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

DECL_FIX_PROMPT = """You previously extracted a customs declaration but MISSED some fields.

Here is what you already found:
{existing}

These fields are STILL MISSING — you MUST find them now:
{missing_list}

Search ALL pages again. Focus ONLY on the missing fields. Return ONLY valid JSON with the missing fields filled:
{missing_json}

## PAGE DATA:
"""

ITEMS_FIX_PROMPT = """You previously extracted product items but MISSED some fields.

Declaration data:
  Exchange Rate = {exchange_rate}

Here are the items with missing fields marked as null:
{existing_items}

You MUST fill every null field. For each missing field:
- Search ALL pages again carefully for the value
- Look in customs declaration rows, invoice tables, licence documents
- Read the EXACT value from the document. Do NOT calculate or guess.
- Exchange Rate (1) = {exchange_rate} (copy this)

Return the COMPLETE items array with ALL fields filled:
{{
  "items": [<complete items with all 9 fields>]
}}

## PAGE DATA:
"""

DECL_REQUIRED = [
    "Declaration No", "Declaration Date", "Importer (Name)", "Consignor (Name)",
    "Invoice Number", "Invoice Price", "Currency", "Exchange Rate",
    "Total Customs Value", "Import/Export Customs Duty", "Commercial Tax (CT)",
    "Advance Income Tax (AT)",
]

ITEM_REQUIRED = [
    "Item name", "Quantity (1)", "Invoice unit price", "Customs Value (MMK)",
    "Customs duty rate", "Commercial tax %", "HS Code", "Origin Country",
    "Exchange Rate (1)",
]


def _qa_declaration(declaration: Dict, page_summary: str, corrections: str, model: str) -> Dict:
    """QA check declaration — re-run for missing required fields."""
    missing = [f for f in DECL_REQUIRED if declaration.get(f) is None or str(declaration.get(f, "")).strip() == ""]
    if not missing:
        print("    QA Declaration: ALL fields filled ✓")
        return declaration

    print(f"    QA Declaration: {len(missing)} missing fields — re-running: {missing}")
    missing_json = json.dumps({f: "<find this>" for f in missing}, indent=2)
    existing = json.dumps({k: v for k, v in declaration.items() if v is not None}, indent=2)

    fix_prompt = DECL_FIX_PROMPT.format(
        existing=existing, missing_list=", ".join(missing), missing_json=missing_json
    )
    fix_result = _call_llm(fix_prompt + corrections, page_summary, model, "decl_qa")

    if fix_result:
        for field in missing:
            val = fix_result.get(field)
            if val is not None and str(val).strip():
                declaration[field] = val
                print(f"      Fixed: {field} = {str(val)[:50]}")

    still_missing = [f for f in DECL_REQUIRED if declaration.get(f) is None or str(declaration.get(f, "")).strip() == ""]
    if still_missing:
        print(f"    QA Declaration: still missing {len(still_missing)}: {still_missing}")
    else:
        print("    QA Declaration: ALL fields filled after fix ✓")

    return declaration


def _qa_items(items: List[Dict], declaration: Dict, page_summary: str, corrections: str, model: str) -> List[Dict]:
    """QA check items — re-run for missing fields."""
    all_filled = True
    for i, item in enumerate(items):
        missing = [f for f in ITEM_REQUIRED if item.get(f) is None or str(item.get(f, "")).strip() == ""]
        if missing:
            all_filled = False
            print(f"    QA Item {i+1}: missing {missing}")

    if all_filled:
        print("    QA Items: ALL fields filled for all items ✓")
        return items

    print(f"    QA Items: re-running for missing fields...")
    existing_items = json.dumps(items, indent=2, ensure_ascii=False)

    fix_prompt = ITEMS_FIX_PROMPT.format(
        exchange_rate=declaration.get("Exchange Rate", 0),
        existing_items=existing_items,
    )
    fix_result = _call_llm(fix_prompt + corrections, page_summary, model, "items_qa")

    if fix_result and fix_result.get("items"):
        fixed_items = fix_result["items"]
        # Merge: only fill in what was missing
        for i, item in enumerate(items):
            if i < len(fixed_items):
                for field in ITEM_REQUIRED:
                    if (item.get(field) is None or str(item.get(field, "")).strip() == "") and fixed_items[i].get(field) is not None:
                        item[field] = fixed_items[i][field]
                        print(f"      Fixed Item {i+1}.{field} = {str(item[field])[:50]}")

    # Final check
    for i, item in enumerate(items):
        missing = [f for f in ITEM_REQUIRED if item.get(f) is None or str(item.get(f, "")).strip() == ""]
        if missing:
            print(f"    QA Item {i+1}: still missing {missing}")
        else:
            print(f"    QA Item {i+1}: ALL 9 fields filled ✓")

    return items


# ═══════════════════════════════════════════════════════════════
# MASTER ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

# JSON schemas for structured output
DECL_SCHEMA = {
    "name": "declaration",
    "schema": {
        "type": "object",
        "properties": {
            "Declaration No": {"type": ["string", "null"]},
            "Declaration Date": {"type": ["string", "null"]},
            "Importer (Name)": {"type": ["string", "null"]},
            "Consignor (Name)": {"type": ["string", "null"]},
            "Invoice Number": {"type": ["string", "null"]},
            "Invoice Price": {"type": ["number", "null"]},
            "Currency": {"type": ["string", "null"]},
            "Currency 2": {"type": ["string", "null"]},
            "Exchange Rate": {"type": ["number", "null"]},
            "Total Customs Value": {"type": ["number", "null"]},
            "Import/Export Customs Duty": {"type": ["number", "null"]},
            "Commercial Tax (CT)": {"type": ["number", "null"]},
            "Advance Income Tax (AT)": {"type": ["number", "null"]},
            "Security Fee (SF)": {"type": ["number", "null"]},
            "MACCS Service Fee (MF)": {"type": ["number", "null"]},
            "Exemption/Reduction": {"type": ["number", "null"]},
        },
        "required": ["Declaration No", "Declaration Date", "Importer (Name)", "Consignor (Name)",
                      "Invoice Number", "Invoice Price", "Currency", "Exchange Rate",
                      "Total Customs Value", "Import/Export Customs Duty", "Commercial Tax (CT)",
                      "Advance Income Tax (AT)", "Security Fee (SF)", "MACCS Service Fee (MF)",
                      "Exemption/Reduction"],
    }
}

ITEMS_SCHEMA = {
    "name": "items_result",
    "schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "Item name": {"type": ["string", "null"]},
                        "Quantity (1)": {"type": ["string", "null"]},
                        "Invoice unit price": {"type": ["number", "null"]},
                        "Customs Value (MMK)": {"type": ["number", "null"]},
                        "Customs duty rate": {"type": ["number", "null"]},
                        "Commercial tax %": {"type": ["number", "null"]},
                        "HS Code": {"type": ["string", "null"]},
                        "Origin Country": {"type": ["string", "null"]},
                        "Exchange Rate (1)": {"type": ["number", "null"]},
                    },
                    "required": ["Item name", "Quantity (1)", "Invoice unit price", "Customs Value (MMK)",
                                  "Customs duty rate", "Commercial tax %", "HS Code", "Origin Country",
                                  "Exchange Rate (1)"],
                }
            }
        },
        "required": ["items"],
    }
}

# json_schema mode — guarantees valid JSON output, all required fields present
USE_JSON_SCHEMA = True


def _cross_validate(declaration: Dict, items: List[Dict]) -> List[str]:
    """Cross-validate items against declaration totals. Returns list of warnings."""
    warnings = []
    try:
        total_cv = float(declaration.get("Total Customs Value", 0) or 0)
        if total_cv > 0 and items:
            # Check: sum of item customs values ≈ total customs value
            item_cv_sum = 0
            for item in items:
                cv = item.get("Customs Value (MMK)")
                if cv is not None:
                    item_cv_sum += float(cv)

            if item_cv_sum > 0:
                ratio = item_cv_sum / total_cv
                if ratio < 0.8 or ratio > 1.2:
                    warnings.append(f"Items customs value sum ({item_cv_sum:,.0f}) differs from declaration ({total_cv:,.0f}) by {abs(1-ratio)*100:.0f}%")
                else:
                    print(f"    Cross-check: items sum {item_cv_sum:,.0f} vs declaration {total_cv:,.0f} — OK ({ratio:.2f}x)")

        # Check: all items have same exchange rate as declaration
        decl_fx = float(declaration.get("Exchange Rate", 0) or 0)
        if decl_fx > 0:
            for i, item in enumerate(items):
                item_fx = float(item.get("Exchange Rate (1)", 0) or 0)
                if item_fx > 0 and abs(item_fx - decl_fx) > 0.01:
                    warnings.append(f"Item {i+1} exchange rate ({item_fx}) differs from declaration ({decl_fx})")
                    item["Exchange Rate (1)"] = decl_fx  # Auto-fix

        # Check: duty rates are reasonable (0 to 1)
        for i, item in enumerate(items):
            dr = item.get("Customs duty rate")
            if dr is not None and (float(dr) > 1 or float(dr) < 0):
                warnings.append(f"Item {i+1} duty rate {dr} is out of range (expected 0-1)")
            tp = item.get("Commercial tax %")
            if tp is not None and (float(tp) > 1 or float(tp) < 0):
                warnings.append(f"Item {i+1} tax % {tp} is out of range (expected 0-1)")

    except Exception as e:
        warnings.append(f"Cross-validation error: {e}")

    return warnings


def assemble(page_results: List[Dict], model: str = None) -> Dict:
    """Master orchestrator: Declaration + Items agents + QA + cross-validation."""
    print("  Assembler: Master + Column Agent + QA + Cross-Validation")

    page_summary = _build_page_summary(page_results)
    corrections = _build_corrections_prompt()
    print(f"    Page data: {len(page_summary):,} chars from {len(page_results)} pages")

    # ══════════════════════════════════════════════════════
    # Phase 1: Declaration Agent
    # ══════════════════════════════════════════════════════
    print("    Phase 1: Declaration Master (16 columns)...")
    decl_result = _call_llm(DECLARATION_PROMPT + corrections, page_summary, model, "decl_agent",
                             response_schema=DECL_SCHEMA if USE_JSON_SCHEMA else None)
    declaration = decl_result if decl_result else {}

    # Clean declaration numeric values
    for field, val in declaration.items():
        if isinstance(val, str):
            cleaned = val.replace(",", "").strip()
            try:
                declaration[field] = float(cleaned)
            except (ValueError, TypeError):
                pass

    if not declaration.get("Currency 2") and declaration.get("Currency"):
        declaration["Currency 2"] = declaration["Currency"]
    for f in ["Security Fee (SF)", "MACCS Service Fee (MF)", "Exemption/Reduction"]:
        if declaration.get(f) is None:
            declaration[f] = 0

    filled = sum(1 for v in declaration.values() if v is not None)
    print(f"    Declaration: {filled}/16 fields")

    # ── QA: Declaration ──
    declaration = _qa_declaration(declaration, page_summary, corrections, model)

    # ══════════════════════════════════════════════════════
    # Phase 2: Items Agent (needs declaration data)
    # ══════════════════════════════════════════════════════
    print("    Phase 2: Items Master (9 columns per item)...")
    items_prompt = ITEMS_PROMPT_TEMPLATE.format(
        exchange_rate=declaration.get("Exchange Rate", 0),
        currency=declaration.get("Currency", ""),
    )
    items_result = _call_llm(items_prompt + corrections, page_summary, model, "items_agent",
                              response_schema=ITEMS_SCHEMA if USE_JSON_SCHEMA else None)
    items = items_result.get("items", []) if items_result else []

    # Ensure exchange rate on every item
    for item in items:
        if not item.get("Exchange Rate (1)") and declaration.get("Exchange Rate"):
            item["Exchange Rate (1)"] = declaration["Exchange Rate"]

    print(f"    Items: {len(items)} products")

    # ── QA: Items ──
    items = _qa_items(items, declaration, page_summary, corrections, model)

    # ══════════════════════════════════════════════════════
    # Phase 3: Cross-Validation (zero cost — just math)
    # ══════════════════════════════════════════════════════
    print("    Phase 3: Cross-validation...")
    warnings = _cross_validate(declaration, items)
    if warnings:
        for w in warnings:
            print(f"    ⚠ {w}")
    else:
        print("    Cross-validation: ALL checks passed ✓")

    return {"declaration": declaration, "items": items}
