#!/usr/bin/env python3
"""
Script to test importing US Sales Tax Calculator API with hierarchical structure.
This will test the import flow and identify any issues.
"""

import json
import sqlite3
from datetime import datetime
from swagger_parser import SwaggerParser

def test_import_us_sales_tax():
    """Test import of US Sales Tax Calculator API."""
    
    # Connect to database
    conn = sqlite3.connect('instance/GEE.db')
    cursor = conn.cursor()
    
    try:
        # Read the US Sales Tax API file
        with open('temp/US_Sales_Tax_Calculator_API.json', 'r') as f:
            content = f.read()
        
        print("📁 Reading Swagger file: US_Sales_Tax_Calculator_API.json")
        
        # Parse the Swagger file
        parser = SwaggerParser()
        swagger_data = parser.parse_file(content, 'json')
        field_classes = parser.extract_field_classes_and_fields()
        
        print(f"✅ Parsed {len(field_classes)} field classes")
        
        # Print discovered classes
        print("\n📋 Discovered Field Classes:")
        for class_name, field_class in field_classes.items():
            parent = field_class.get('parent_class', 'None')
            class_type = field_class.get('class_type', 'UNKNOWN')
            field_count = len(field_class.get('fields', []))
            print(f"   • {class_name} [{class_type}] - Parent: {parent} - Fields: {field_count}")
        
        # Cleanup existing classes with similar names
        print(f"\n🧹 Cleaning up any existing US Sales Tax related classes...")
        cleanup_classes = [
            'USSalesTaxCalculatorAPI',
            'SalesTaxRequest', 
            'SalesTaxResponse',
            'TaxJurisdiction',
            'TaxExemption',
            'TaxRatesResponse',
            'LocalTaxRate',
            'ValidationRequest',
            'ValidationResponse',
            'ErrorResponse'
        ]
        
        removed_count = 0
        for class_name in cleanup_classes:
            cursor.execute("SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = ?", (class_name,))
            result = cursor.fetchone()
            if result:
                gfc_id = result[0]
                # Delete fields first
                cursor.execute("DELETE FROM GEE_FIELDS WHERE GFC_ID = ?", (gfc_id,))
                # Delete field class
                cursor.execute("DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?", (gfc_id,))
                print(f"   🗑️  Removed: {class_name}")
                removed_count += 1
        
        if removed_count > 0:
            print(f"✅ Cleanup completed - removed {removed_count} classes")
        else:
            print("✅ No existing classes to clean up")
        
        # Create mapping to store field class IDs
        class_id_map = {}
        
        # Order classes properly (parents first, then children)
        parent_classes = [name for name, fc in field_classes.items() if not fc.get('parent_class')]
        child_classes = [name for name, fc in field_classes.items() if fc.get('parent_class')]
        
        ordered_classes = parent_classes + child_classes
        
        print(f"\n🔄 Processing {len(ordered_classes)} classes in order...")
        
        # Create field classes
        for class_name in ordered_classes:
            field_class = field_classes[class_name]
            
            # Get parent ID if this is a child class
            parent_gfc_id = None
            if field_class.get('parent_class'):
                parent_name = field_class['parent_class']
                if parent_name in class_id_map:
                    parent_gfc_id = class_id_map[parent_name]
                else:
                    print(f"❌ ERROR: Parent class '{parent_name}' not found for '{class_name}'")
                    continue
            
            # Insert field class
            cursor.execute("""
                INSERT INTO GEE_FIELD_CLASSES 
                (FIELD_CLASS_NAME, CLASS_TYPE, PARENT_GFC_ID, DESCRIPTION, CREATE_DATE, UPDATE_DATE)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                class_name,
                field_class.get('class_type', 'OBJECT'),
                parent_gfc_id,
                field_class.get('description', f'Generated from {class_name}'),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            gfc_id = cursor.lastrowid
            class_id_map[class_name] = gfc_id
            
            parent_info = f" (Parent: {field_class.get('parent_class', 'None')})" if field_class.get('parent_class') else ""
            print(f"✅ Created field class: {class_name} (ID: {gfc_id}, Type: {field_class.get('class_type', 'OBJECT')}){parent_info}")
            
            # Add fields for this class
            fields = field_class.get('fields', [])
            for field in fields:
                cursor.execute("""
                    INSERT INTO GEE_FIELDS 
                    (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_DESCRIPTION, CREATE_DATE, UPDATE_DATE)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    gfc_id,
                    field['name'],
                    field['type'],
                    field.get('max_length'),
                    field.get('description', f'Field from {class_name}'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                max_len_info = f"({field.get('max_length')})" if field.get('max_length') else "(None)"
                print(f"  ➕ Added field: {field['name']} [{field['type']}{max_len_info}] - {field.get('description', 'No description')}")
        
        # Commit changes
        conn.commit()
        
        print(f"\n🎉 SUCCESS: Created hierarchical structure with {len(field_classes)} field classes")
        parent_count = len(parent_classes)
        child_count = len(child_classes)
        print(f"   Parent Classes: {parent_count}")
        print(f"   Child Classes: {child_count}")
        
        # Verification
        print(f"\n📊 Verification:")
        for class_name in ordered_classes:
            cursor.execute("""
                SELECT fc.GFC_ID, fc.CLASS_TYPE, p.FIELD_CLASS_NAME as PARENT_NAME,
                       COUNT(f.GF_ID) as FIELD_COUNT
                FROM GEE_FIELD_CLASSES fc
                LEFT JOIN GEE_FIELD_CLASSES p ON fc.PARENT_GFC_ID = p.GFC_ID
                LEFT JOIN GEE_FIELDS f ON fc.GFC_ID = f.GFC_ID
                WHERE fc.FIELD_CLASS_NAME = ?
                GROUP BY fc.GFC_ID
            """, (class_name,))
            
            result = cursor.fetchone()
            if result:
                gfc_id, class_type, parent_name, field_count = result
                parent_info = parent_name if parent_name else "None"
                print(f"   • {class_name} [{class_type}] - Parent: {parent_info} - Fields: {field_count}")
                
                # Show field details
                cursor.execute("""
                    SELECT GF_NAME, GF_TYPE, GF_SIZE, GF_DESCRIPTION
                    FROM GEE_FIELDS 
                    WHERE GFC_ID = ? 
                    ORDER BY GF_NAME
                """, (gfc_id,))
                
                fields = cursor.fetchall()
                for field_name, data_type, max_length, description in fields:
                    max_len_str = f"({max_length})" if max_length else ""
                    print(f"     - {field_name} [{data_type}{max_len_str}] - {description}")
        
        print("=" * 70)
        print("✅ US Sales Tax API import test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR during import: {str(e)}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting US Sales Tax API Import Test")
    print("=" * 70)
    
    success = test_import_us_sales_tax()
    
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("❌ Test failed!")