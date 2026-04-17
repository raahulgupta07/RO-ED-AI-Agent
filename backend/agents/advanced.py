#!/usr/bin/env python3
"""
Advanced features:
T2.1 — Multi-Language Support (Myanmar/Burmese)
T2.6 — PDF Annotation (highlight source)
T4.3 — Multi-Tenant Isolation
"""

import re
import json
import os
from typing import Dict, List, Optional
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# T2.1: Multi-Language Support (Myanmar/Burmese)
# ═══════════════════════════════════════════════════════════════

MYANMAR_UNICODE_RANGE = r'[\u1000-\u109F\uAA60-\uAA7F]'

def detect_myanmar_text(text: str) -> bool:
    """Check if text contains Myanmar/Burmese characters."""
    return bool(re.search(MYANMAR_UNICODE_RANGE, text))


def build_bilingual_prompt_hint(page_text: str) -> str:
    """Build prompt hint for bilingual documents."""
    has_myanmar = detect_myanmar_text(page_text)
    if not has_myanmar:
        return ""

    return """
BILINGUAL DOCUMENT DETECTED (English + Myanmar/Burmese):
- Extract field LABELS in English (translate if needed)
- Extract field VALUES as-is (keep Myanmar text for names, keep English for numbers)
- For company names: prefer English transliteration if both are present
- Myanmar digits (၀-၉) should be converted to Arabic digits (0-9)
- Common Myanmar labels: ကုမ္ပဏီ (company), ကုန်သွယ်လုပ်ငန်းခွန် (commercial tax), အကောက်ခွန် (customs duty)
"""


def normalize_myanmar_digits(text: str) -> str:
    """Convert Myanmar digits (၀-၉) to Arabic digits (0-9)."""
    myanmar_digits = '၀၁၂၃၄၅၆၇၈၉'
    for i, md in enumerate(myanmar_digits):
        text = text.replace(md, str(i))
    return text


def get_tesseract_languages(page_text: str) -> str:
    """Determine Tesseract language config based on detected text."""
    if detect_myanmar_text(page_text):
        return "eng+mya"  # English + Myanmar
    return "eng"


# ═══════════════════════════════════════════════════════════════
# T2.6: PDF Annotation (highlight source on PDF)
# ═══════════════════════════════════════════════════════════════

def find_value_coordinates(pdf_path: str, search_value: str,
                           page_number: int = None) -> List[Dict]:
    """Find where a value appears on the PDF and return bounding box coordinates.

    Returns list of {page, x0, y0, x1, y1, text} for each match.
    """
    import fitz

    results = []
    doc = fitz.open(pdf_path)

    pages_to_search = range(len(doc))
    if page_number is not None:
        pages_to_search = [page_number - 1] if page_number - 1 < len(doc) else []

    search_str = str(search_value).strip()
    # Also try with commas for numbers
    search_variants = [search_str]
    try:
        num = float(search_str.replace(",", ""))
        search_variants.append(f"{num:,.0f}")
        search_variants.append(f"{num:,.2f}")
        search_variants.append(str(int(num)))
    except ValueError:
        pass

    for pg_idx in pages_to_search:
        page = doc[pg_idx]
        for variant in search_variants:
            rects = page.search_for(variant)
            for rect in rects:
                results.append({
                    "page": pg_idx + 1,
                    "x0": round(rect.x0, 1),
                    "y0": round(rect.y0, 1),
                    "x1": round(rect.x1, 1),
                    "y1": round(rect.y1, 1),
                    "text": variant,
                    "width": round(page.rect.width, 1),
                    "height": round(page.rect.height, 1),
                })

    doc.close()
    return results


def annotate_pdf(pdf_path: str, annotations: List[Dict], output_path: str = None) -> str:
    """Create annotated PDF with highlighted values.

    annotations: list of {page, x0, y0, x1, y1, label, color}
    Returns path to annotated PDF.
    """
    import fitz

    doc = fitz.open(pdf_path)

    for ann in annotations:
        pg_idx = ann.get("page", 1) - 1
        if pg_idx < 0 or pg_idx >= len(doc):
            continue

        page = doc[pg_idx]
        rect = fitz.Rect(ann["x0"], ann["y0"], ann["x1"], ann["y1"])

        # Highlight rectangle
        highlight = page.add_highlight_annot(rect)
        if highlight:
            color_map = {"green": (0, 1, 0), "yellow": (1, 1, 0), "red": (1, 0, 0)}
            color = color_map.get(ann.get("color", "yellow"), (1, 1, 0))
            highlight.set_colors(stroke=color)
            highlight.update()

        # Add label
        label = ann.get("label", "")
        if label:
            label_rect = fitz.Rect(ann["x1"] + 2, ann["y0"], ann["x1"] + 150, ann["y1"])
            page.insert_textbox(label_rect, label, fontsize=7, color=(0.8, 0, 0))

    if not output_path:
        output_path = pdf_path.replace(".pdf", "_annotated.pdf")

    doc.save(output_path)
    doc.close()
    return output_path


# ═══════════════════════════════════════════════════════════════
# T4.3: Multi-Tenant Isolation (schema only)
# ═══════════════════════════════════════════════════════════════

def get_tenant_filter(user: Dict) -> Optional[int]:
    """Get tenant_id for query filtering. Returns None if no multi-tenant."""
    return user.get("tenant_id")


def apply_tenant_filter(query: str, params: list, tenant_id: Optional[int],
                        table_alias: str = "") -> tuple:
    """Add tenant filter to SQL query if multi-tenant is active."""
    if tenant_id is not None:
        prefix = f"{table_alias}." if table_alias else ""
        query += f" AND {prefix}tenant_id = ?"
        params.append(tenant_id)
    return query, params


# Multi-tenant migration SQL (run when enabling multi-tenant)
MULTI_TENANT_MIGRATION = """
-- Add tenant_id to core tables
ALTER TABLE jobs ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE items ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE declarations ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE users ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE corrections ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE importer_profiles ADD COLUMN tenant_id INTEGER DEFAULT 1;

-- Create tenant table
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 1,
    settings_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_items_tenant ON items(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
"""
