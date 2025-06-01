#!/usr/bin/env python3
"""Verify the hierarchical structure was created correctly."""

import sqlite3

def verify_hierarchy():
    conn = sqlite3.connect('instance/GEE.db')
    cursor = conn.cursor()

    print('=== HIERARCHICAL STRUCTURE VERIFICATION ===')

    cursor.execute('''
        SELECT 
            fc.GFC_ID,
            fc.FIELD_CLASS_NAME,
            fc.CLASS_TYPE,
            fc.PARENT_GFC_ID,
            parent.FIELD_CLASS_NAME as PARENT_NAME,
            COUNT(f.GF_ID) as FIELD_COUNT
        FROM GEE_FIELD_CLASSES fc
        LEFT JOIN GEE_FIELD_CLASSES parent ON fc.PARENT_GFC_ID = parent.GFC_ID
        LEFT JOIN GEE_FIELDS f ON fc.GFC_ID = f.GFC_ID
        WHERE fc.FIELD_CLASS_NAME IN ('CanadianGSTCalculationAPI', 'TaxCalculationRequest', 'TaxCalculationResponse', 'ErrorResponse')
        GROUP BY fc.GFC_ID
        ORDER BY fc.PARENT_GFC_ID IS NULL DESC, fc.GFC_ID
    ''')

    results = cursor.fetchall()

    for row in results:
        gfc_id, class_name, class_type, parent_id, parent_name, field_count = row
        parent_info = f' -> Parent: {parent_name}' if parent_name else ' (ROOT)'
        print(f'{class_name} [{class_type}]{parent_info} - {field_count} fields')

    print('\n=== FIELD DETAILS ===')

    cursor.execute('''
        SELECT 
            fc.FIELD_CLASS_NAME,
            f.GF_NAME,
            f.GF_TYPE,
            f.GF_SIZE,
            f.GF_DESCRIPTION
        FROM GEE_FIELD_CLASSES fc
        JOIN GEE_FIELDS f ON fc.GFC_ID = f.GFC_ID
        WHERE fc.FIELD_CLASS_NAME IN ('CanadianGSTCalculationAPI', 'TaxCalculationRequest', 'TaxCalculationResponse', 'ErrorResponse')
        ORDER BY fc.FIELD_CLASS_NAME, f.GF_NAME
    ''')

    fields = cursor.fetchall()

    current_class = None
    for field in fields:
        class_name, field_name, field_type, field_size, field_desc = field
        if class_name != current_class:
            print(f'\n{class_name}:')
            current_class = class_name
        size_info = f'({field_size})' if field_size else ''
        print(f'  • {field_name} [{field_type}{size_info}] - {field_desc}')

    conn.close()
    
    print('\n✅ Verification complete!')

if __name__ == "__main__":
    verify_hierarchy()