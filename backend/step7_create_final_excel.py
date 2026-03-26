#!/usr/bin/env python3
"""
STEP 7: Create Final Excel Output (DUAL FORMAT)
2-sheet Excel:
  Sheet 1: Product Items (6 fields)
  Sheet 2: Declaration Data (16 fields)
"""

import json
import pandas as pd
from pathlib import Path
import config

def create_final_excel(job_id=None):
    """Create comprehensive Excel output with both formats

    Args:
        job_id: Optional job ID to include in filename for persistence
    """

    print("="*80)
    print(" STEP 7: CREATE FINAL EXCEL OUTPUT (DUAL FORMAT)")
    print("="*80)

    # Load data files
    claude_file = config.RESULTS_DIR / 'claude_extracted.json'
    validation_file = config.RESULTS_DIR / 'validated_data.json'
    accuracy_file = config.RESULTS_DIR / 'accuracy_report.json'

    if not claude_file.exists():
        print("\n❌ ERROR: Run step4_claude_structured_extraction.py first!")
        return None

    print("\n📂 Loading data files...")

    with open(claude_file) as f:
        claude_data = json.load(f)

    validation_data = None
    if validation_file.exists():
        with open(validation_file) as f:
            validation_data = json.load(f)

    accuracy_data = None
    if accuracy_file.exists():
        with open(accuracy_file) as f:
            accuracy_data = json.load(f)

    print("✓ Data loaded\n")

    # Create Excel file with job_id in filename
    if job_id:
        output_file = config.RESULTS_DIR / f'final_output_{job_id}.xlsx'
    else:
        output_file = config.RESULTS_DIR / 'final_output.xlsx'

    print(f"📊 Creating Excel: {output_file}\n")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:

        # SHEET 1: Product Items (6 fields)
        print("  Sheet 1: Product Items...")
        items = claude_data.get('items', [])

        if items:
            df_items = pd.DataFrame(items)
            columns_order = [
                'Item name', 'Customs duty rate', 'Quantity (1)',
                'Invoice unit price', 'Commercial tax %', 'Exchange Rate (1)'
            ]
            df_items = df_items[columns_order]
            df_items.to_excel(writer, sheet_name='Product Items', index=False)
            print("  ✓ Created")

        # SHEET 2: Declaration Data (16 fields in single row)
        print("  Sheet 2: Declaration Data...")
        declaration = claude_data.get('declaration', {})

        if declaration:
            # Create single row with all declaration fields
            declaration_row = {
                'Declaration No': declaration.get('Declaration No', ''),
                'Declaration Date': declaration.get('Declaration Date', ''),
                'Importer (Name)': declaration.get('Importer (Name)', ''),
                'Consignor (Name)': declaration.get('Consignor (Name)', ''),
                'Invoice Number': declaration.get('Invoice Number', ''),
                'Invoice Price': declaration.get('Invoice Price ', ''),
                'Invoice Currency': declaration.get('Currency', ''),
                'Exchange Rate': declaration.get('Exchange Rate', ''),
                'Exchange Currency': declaration.get('Currency.1', ''),
                'Total Customs Value': declaration.get('Total Customs Value ', ''),
                'Customs Value Currency': 'MMK',
                'Customs Duty (CD)': declaration.get('Import/Export Customs Duty ', ''),
                'CD Currency': 'MMK',
                'Commercial Tax (CT)': declaration.get('Commercial Tax (CT)', ''),
                'CT Currency': 'MMK',
                'Advance Income Tax (AT)': declaration.get('Advance Income Tax (AT)', ''),
                'AT Currency': 'MMK',
                'Security Fee (SF)': declaration.get('Security Fee (SF)', ''),
                'SF Currency': 'MMK',
                'MACCS Service Fee (MF)': declaration.get('MACCS Service Fee (MF)', ''),
                'MF Currency': 'MMK',
                'Exemption/Reduction': declaration.get('Exemption/Reduction', ''),
                'Exemption Currency': 'MMK'
            }

            df_declaration = pd.DataFrame([declaration_row])
            df_declaration.to_excel(writer, sheet_name='Declaration Data', index=False)
            print("  ✓ Created")
        else:
            print("  ⚠️  No declaration data found, skipping")

    print(f"\n✅ Excel file created: {output_file}")
    print(f"\n📦 FORMAT 1 - Items: {claude_data.get('items_count', 0)}")
    print(f"✅ FORMAT 1 - Completeness: {claude_data.get('completeness_percent', 0):.1f}%")

    if declaration:
        decl_fields = sum(1 for v in declaration.values() if v is not None and str(v).strip())
        print(f"\n📋 FORMAT 2 - Declaration fields: {decl_fields}/16")
        print(f"✅ FORMAT 2 - Completeness: {(decl_fields/16)*100:.1f}%")

    if validation_data:
        print(f"\n✅ Overall Accuracy: {validation_data.get('overall_accuracy', 0):.1f}%")

    print("\n✅ STEP 7 COMPLETE - DUAL FORMAT EXCEL CREATED!")
    print("="*80 + "\n")

    return str(output_file)

if __name__ == "__main__":
    create_final_excel()
