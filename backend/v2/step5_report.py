#!/usr/bin/env python3
"""
v2 Step 5: REPORTER
Save results to DB + generate Excel. Reuses v1 database functions.
"""

import json
import time
from typing import Dict

import config
import database


def save_results(job_id: str, merged: Dict, validation: Dict,
                 page_results: list, duration: float, cost: float,
                 user_id: int = None, username: str = None,
                 pipeline_mode: str = "v2", cross_validation: dict = None):
    """Save pipeline results to database."""

    decl = merged.get("declaration", {})
    items = merged.get("items", [])
    accuracy = validation.get("overall_accuracy", 0)
    pv = pipeline_mode or "ro_ed"

    # Save items
    if items:
        database.save_items(job_id, items)

    # Save declaration
    if decl:
        database.save_declarations(job_id, [decl])

    # Save v2 page extractions
    if page_results:
        database.save_page_extractions(job_id, page_results)

    # Set pipeline version
    try:
        conn = database._connect()
        conn.execute("UPDATE jobs SET pipeline_version = ? WHERE job_id = ?", (pv, job_id))
        if cross_validation:
            conn.execute("UPDATE jobs SET cross_validation_json = ? WHERE job_id = ?",
                         (json.dumps(cross_validation), job_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

    # Update job metrics
    database.update_job_metrics(job_id, duration, cost, accuracy)
    database.update_job_status(job_id, "COMPLETED")

    if user_id and username:
        action = "RUN_JOB"
        database.log_activity(user_id, username, action,
                              f"{len(items)} items, {accuracy:.1f}%")

    # Save additional tables to DB as JSON
    additional_tables = merged.get("additional_tables", [])
    if additional_tables:
        try:
            conn = database._connect()
            conn.execute("UPDATE jobs SET cross_validation_json = ? WHERE job_id = ?",
                         (json.dumps({"additional_tables": additional_tables}), job_id))
            conn.commit()
            conn.close()
        except Exception:
            pass

    # Save full extraction as JSON
    output = {
        "pipeline_version": pv,
        "extraction_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": config.OCR_MODEL,
        "duration_seconds": duration,
        "items_count": len(items),
        "declaration": decl,
        "items": items,
        "page_map": merged.get("page_map", []),
        "cross_checks": merged.get("cross_checks", []),
        "page_groups": merged.get("page_groups", {}),
        "additional_tables": additional_tables,
        "validation": validation,
    }

    output_file = config.RESULTS_DIR / f"{job_id}_extracted.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Save per-page JSON files (per-job directory for concurrency)
    pages_dir = config.RESULTS_DIR / f"pages_{job_id}"
    pages_dir.mkdir(exist_ok=True)
    for pr in page_results:
        page_file = pages_dir / f"page_{pr['page_number']:02d}.json"
        with open(page_file, "w", encoding="utf-8") as f:
            json.dump(pr.get("parsed", {}), f, indent=2, ensure_ascii=False)

    print(f"  Saved: {len(items)} items, {len(decl)} declaration fields")

    return output
