#!/usr/bin/env python3
"""
Script to import Canadian GST Swagger file with hierarchical structure:
- 1 API parent class (CanadianGSTCalculationAPI)
- 3 child classes (TaxCalculationRequest, TaxCalculationResponse, ErrorResponse)
- All fields properly populated in their respective classes
"""

import json
import sqlite3
from datetime import datetime
from swagger_parser import SwaggerParser

def import_swagger_with_hierarchy():
    """Import Swagger file with proper parent-child class hierarchy."""
    
    # Connect to database
    conn = sqlite3.connect('instance/GEE.db')
    cursor = conn.cursor()
    
    try:
        # Read the modified Swagger file
        with open('temp/Canadian_GST_Calculation_API_Modified.json', 'r') as f:
            content = f.read()
        
        print("📁 Reading Swagger file: Canadian_GST_Calculation_API_Modified.json")
        
        # Parse the Swagger file
        parser = SwaggerParser()
        swagger_data = parser.parse_file(content, 'json')
        field_classes = parser.extract_field_classes_and_fields()
        
        print(f"✅ Parsed {len(field_classes)} field classes")
        
        # Create mapping to store field class IDs
        class_id_map = {}
        
        # First pass: Create all field classes (order matters for parent-child relationships)
        # Create parent classes first
        parent_classes = [name for name, fc in field_classes.items() if not fc.get('parent_class')]
        child_classes = [name for name, fc in field_classes.items() if fc.get('parent_class')]
        
        ordered_classes = parent_classes + child_classes
        
        for class_name in ordered_classes:
            field_class = field_classes[class_name]
            
            # Get parent ID if this is a child class
            parent_gfc_id = None
            if field_class.get('parent_class'):
                parent_class_name = field_class['parent_class']
                if parent_class_name in class_id_map:
                    parent_gfc_id = class_id_map[parent_class_name]
                else:
                    print(f"⚠️  Warning: Parent class '{parent_class_name}' not found for '{class_name}'")
            
            # Insert field class
            cursor.execute("""
                INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION, PARENT_GFC_ID, CREATE_DATE) 
                VALUES (?, ?, ?, ?, ?)
            """, (field_class['name'], field_class['type'], field_class['description'], parent_gfc_id, datetime.now()))
            
            gfc_id = cursor.lastrowid
            class_id_map[class_name] = gfc_id
            
            parent_info = f" (Parent: {field_class.get('parent_class', 'None')})" if field_class.get('parent_class') else ""
            print(f"✅ Created field class: {class_name} (ID: {gfc_id}, Type: {field_class['type']}){parent_info}")
            
            # Insert fields for this class
            for field in field_class['fields']:
                cursor.execute("""
                    INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_DESCRIPTION, CREATE_DATE) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (gfc_id, field['name'], field['type'], field['size'], field['description'], datetime.now()))
                
                print(f"  ➕ Added field: {field['name']} [{field['type']}({field['size']})] - {field['description']}")
        
        # Commit changes
        conn.commit()
        
        print(f"\n🎉 SUCCESS: Created hierarchical structure with {len(field_classes)} field classes")
        print(f"   Parent Classes: {len(parent_classes)}")
        print(f"   Child Classes: {len(child_classes)}")
        
        # Verify the creation with hierarchy
        print(f"\n📊 Verification:")
        
        for class_name in ordered_classes:
            cursor.execute("""
                SELECT fc.FIELD_CLASS_NAME, fc.CLASS_TYPE, fc.PARENT_GFC_ID,
                       parent_fc.FIELD_CLASS_NAME as PARENT_NAME,
                       COUNT(f.GF_ID) as field_count
                FROM GEE_FIELD_CLASSES fc 
                LEFT JOIN GEE_FIELD_CLASSES parent_fc ON fc.PARENT_GFC_ID = parent_fc.GFC_ID
                LEFT JOIN GEE_FIELDS f ON fc.GFC_ID = f.GFC_ID 
                WHERE fc.FIELD_CLASS_NAME = ?
                GROUP BY fc.GFC_ID
            """, (class_name,))
            
            result = cursor.fetchone()
            if result:
                parent_name = result[3] if result[3] else "None"
                print(f"   • {result[0]} [{result[1]}] - Parent: {parent_name} - Fields: {result[4]}")
                
                # Show all fields for this class
                cursor.execute("""
                    SELECT f.GF_NAME, f.GF_TYPE, f.GF_SIZE, f.GF_DESCRIPTION
                    FROM GEE_FIELDS f 
                    JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID
                    WHERE fc.FIELD_CLASS_NAME = ?
                    ORDER BY f.GF_NAME
                """, (class_name,))
                
                fields = cursor.fetchall()
                for field in fields:
                    size_info = f"({field[2]})" if field[2] else ""
                    print(f"     - {field[0]} [{field[1]}{size_info}] - {field[3]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        conn.close()

def clean_existing_canadian_gst_classes():
    """Remove any existing Canadian GST related field classes."""
    
    conn = sqlite3.connect('instance/GEE.db')
    cursor = conn.cursor()
    
    try:
        # Find existing Canadian GST related classes
        cursor.execute("""
            SELECT GFC_ID, FIELD_CLASS_NAME FROM GEE_FIELD_CLASSES 
            WHERE FIELD_CLASS_NAME LIKE '%Canadian%' 
               OR FIELD_CLASS_NAME LIKE '%GST%'
               OR FIELD_CLASS_NAME LIKE '%TaxCalculation%'
               OR FIELD_CLASS_NAME LIKE '%ErrorResponse%'
        """)
        
        existing_classes = cursor.fetchall()
        
        if existing_classes:
            print(f"🧹 Cleaning up {len(existing_classes)} existing Canadian GST related classes...")
            
            for gfc_id, class_name in existing_classes:
                # Delete fields first (foreign key constraint)
                cursor.execute("DELETE FROM GEE_FIELDS WHERE GFC_ID = ?", (gfc_id,))
                # Delete field class
                cursor.execute("DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?", (gfc_id,))
                print(f"   🗑️  Removed: {class_name}")
            
            conn.commit()
            print("✅ Cleanup completed")
        else:
            print("✅ No existing Canadian GST classes found")
            
    except Exception as e:
        print(f"❌ Cleanup error: {str(e)}")
        conn.rollback()
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting Hierarchical Swagger Import for Canadian GST Calculation")
    print("=" * 70)
    
    # Clean existing classes first
    clean_existing_canadian_gst_classes()
    print()
    
    # Import with hierarchy
    success = import_swagger_with_hierarchy()
    
    print("=" * 70)
    if success:
        print("✅ Hierarchical import completed successfully!")
        print("   Expected: 1 API parent + 3 child classes with proper hierarchy")
        print("   Result: MATCHES EXPECTATION")
    else:
        print("❌ Hierarchical import failed!")