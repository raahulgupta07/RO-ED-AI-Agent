#!/usr/bin/env python3
"""
MASTER SCRIPT: Run Complete Extraction Pipeline
Execute all 7 steps sequentially with approval gates
"""

import sys
import time
from pathlib import Path

# Import all steps
import step1_analyze_metadata
import step2_extract_text_pages
import step3_ocr_image_pages
import step4_claude_structured_extraction
import step5_cross_validate
import step6_accuracy_matrix
import step7_create_final_excel

def print_banner(text):
    """Print formatted banner"""
    print("\n" + "="*80)
    print(f" {text}")
    print("="*80 + "\n")

def ask_approval(step_name):
    """Ask user for approval to continue"""
    response = input(f"\n✋ Continue to {step_name}? (yes/no): ").strip().lower()
    return response in ['yes', 'y']

def _clear_previous_results():
    """Clear previous extraction results to prevent data leakage between runs."""
    import config
    stale_files = [
        config.RESULTS_DIR / 'claude_extracted.json',
        config.RESULTS_DIR / 'validated_data.json',
        config.RESULTS_DIR / 'accuracy_report.json',
        config.RESULTS_DIR / 'pdf_metadata.json',
        config.RESULTS_DIR / 'text_extracted.json',
        config.RESULTS_DIR / 'ocr_extracted.json',
    ]
    for f in stale_files:
        if f.exists():
            f.unlink()


def run_pipeline(auto_approve=False):
    """Run complete 7-step pipeline"""

    print_banner("PDF EXTRACTION PIPELINE")
    _clear_previous_results()
    print("7-Step Process:")
    print("  1. Analyze PDF metadata")
    print("  2. Extract TEXT pages (FREE)")
    print("  3. OCR IMAGE pages (~$0.0054)")
    print("  4. Dash Agent extraction (~$0.0054)")
    print("  5. Cross-validate data")
    print("  6. Accuracy matrix")
    print("  7. Final Excel output")
    print(f"\nEstimated cost: ~$0.0108 per PDF")

    if not auto_approve:
        response = input("\n▶️  Start pipeline? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\n❌ Pipeline cancelled")
            return

    start_time = time.time()

    steps = [
        ("STEP 1/7: Analyze PDF Metadata", step1_analyze_metadata.analyze_pdf_metadata),
        ("STEP 2/7: Extract Text Pages", step2_extract_text_pages.extract_text_pages),
        ("STEP 3/7: OCR Image Pages", step3_ocr_image_pages.ocr_image_pages),
        ("STEP 4/7: Dash Agent Extraction", step4_claude_structured_extraction.extract_structured_data),
        ("STEP 5/7: Cross-Validate", step5_cross_validate.cross_validate),
        ("STEP 6/7: Accuracy Matrix", step6_accuracy_matrix.calculate_accuracy_matrix),
        ("STEP 7/7: Create Final Excel", step7_create_final_excel.create_final_excel)
    ]

    results = {}

    for i, (step_name, step_func) in enumerate(steps):
        if i > 0 and not auto_approve and not ask_approval(f"Step {i+1}"):
            print("❌ Pipeline stopped by user")
            return

        try:
            result = step_func()
            if result is None:
                print(f"❌ {step_name} failed!")
                return
            results[f'step{i+1}'] = result
        except Exception as e:
            print(f"❌ {step_name} error: {e}")
            return

    # Pipeline complete
    duration = time.time() - start_time

    print_banner("🎉 PIPELINE COMPLETE!")
    print(f"✅ All 7 steps completed successfully!")
    print(f"⏱️  Total time: {duration:.1f} seconds")
    print(f"💰 Total cost: ~$0.0108")

    if 'step4' in results:
        print(f"\n📊 Items extracted: {results['step4']['items_count']}")
        print(f"📊 Completeness: {results['step4']['completeness_percent']:.1f}%")

    if 'step5' in results:
        print(f"📊 Accuracy: {results['step5']['overall_accuracy']:.1f}%")
        print(f"📊 Valid fields: {results['step5']['valid_fields']}/{results['step5']['total_fields']}")

    if 'step7' in results:
        print(f"\n📁 Output: {results['step7']}")

    print("\n" + "="*80 + "\n")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Run complete PDF extraction pipeline')
    parser.add_argument('--auto-approve', action='store_true',
                       help='Auto-approve all steps (no manual confirmation)')

    args = parser.parse_args()

    try:
        run_pipeline(auto_approve=args.auto_approve)
    except KeyboardInterrupt:
        print("\n\n❌ Pipeline cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
