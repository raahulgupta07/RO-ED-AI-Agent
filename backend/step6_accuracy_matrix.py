#!/usr/bin/env python3
"""
STEP 6: Calculate Accuracy Matrix
Detailed accuracy breakdown for each field
"""

import json
from pathlib import Path
import config

def calculate_accuracy_matrix():
    """Calculate detailed accuracy matrix"""

    print("="*80)
    print(" STEP 6: ACCURACY MATRIX")
    print("="*80)

    # Load validation data
    validation_file = config.RESULTS_DIR / 'validated_data.json'

    if not validation_file.exists():
        print("\n❌ ERROR: Run step5_cross_validate.py first!")
        return None

    with open(validation_file) as f:
        validation_data = json.load(f)

    field_stats = validation_data['field_stats']
    item_validations = validation_data['item_validations']

    print(f"\n📊 Analyzing {validation_data['total_items']} item(s)\n")

    # Accuracy matrix by field
    print("ACCURACY BY FIELD:")
    print("-"*60)
    for field_name, stats in field_stats.items():
        status = '✓' if stats['accuracy'] >= 100 else '⚠'
        print(f"{status} {field_name:<25} {stats['valid']}/{stats['total']} ({stats['accuracy']:.1f}%)")

    # Overall statistics
    print(f"\nOverall Accuracy: {validation_data['overall_accuracy']:.1f}%")
    print(f"Valid fields: {validation_data['valid_fields']}/{validation_data['total_fields']}")

    # Field ranking
    ranked_fields = sorted(
        field_stats.items(),
        key=lambda x: x[1]['accuracy'],
        reverse=True
    )

    # Problem fields
    problem_fields = [
        (field_name, stats)
        for field_name, stats in field_stats.items()
        if stats['accuracy'] < 100
    ]

    if problem_fields:
        print(f"\n⚠️  Problem Fields:")
        for field_name, stats in problem_fields:
            print(f"   - {field_name}: {stats['accuracy']:.1f}%")
    else:
        print(f"\n✅ All fields have 100% accuracy!")

    # Create matrix report
    matrix_report = {
        'report_timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_items': validation_data['total_items'],
            'total_fields': validation_data['total_fields'],
            'valid_fields': validation_data['valid_fields'],
            'invalid_fields': validation_data['total_fields'] - validation_data['valid_fields'],
            'overall_accuracy': validation_data['overall_accuracy']
        },
        'field_accuracy': field_stats,
        'field_ranking': [
            {'rank': i, 'field': field_name, 'accuracy': stats['accuracy']}
            for i, (field_name, stats) in enumerate(ranked_fields, 1)
        ],
        'problem_fields': [
            {'field': field_name, 'accuracy': stats['accuracy']}
            for field_name, stats in problem_fields
        ],
        'item_breakdown': item_validations
    }

    # Save matrix report
    output_file = config.RESULTS_DIR / 'accuracy_report.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matrix_report, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Saved: {output_file}")
    print("\n✅ STEP 6 COMPLETE")
    print("="*80 + "\n")

    return matrix_report

if __name__ == "__main__":
    calculate_accuracy_matrix()
