#!/usr/bin/env python3
"""
Enhanced test script that creates a proper hierarchical structure:
- 1 API parent class (e.g., USSalesTaxCalculatorAPI)
- All other classes as children of the API class
"""

import json
import sqlite3
from datetime import datetime
from swagger_parser import SwaggerParser

def create_hierarchical_structure(swagger_file, api_name):
    """Create a hierarchical structure from swagger file."""
    
    # Connect to database
    conn = sqlite3.connect('instance/GEE.db')
    cursor = conn.cursor()
    
    try:
        # Read the Swagger file
        with open(swagger_file, 'r') as f:
            content = f.read()
        
        print(f"📁 Reading Swagger file: {swagger_file}")
        
        # Parse the Swagger file
        parser = SwaggerParser()
        swagger_data = parser.parse_file(content, 'json')
        field_classes = parser.extract_field_classes_and_fields()
        
        print(f"✅ Parsed {len(field_classes)} field classes")
        
        # Cleanup existing classes
        api_class_name = api_name.replace(' ', '').replace('-', '') + 'API'
        cleanup_classes = [api_class_name] + list(field_classes.keys())
        
        print(f"\n🧹 Cleaning up any existing classes...")
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
        
        # Step 1: Create the API parent class
        cursor.execute("""
            INSERT INTO GEE_FIELD_CLASSES 
            (FIELD_CLASS_NAME, CLASS_TYPE, PARENT_GFC_ID, DESCRIPTION, CREATE_DATE, UPDATE_DATE)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            api_class_name,
            'API',
            None,
            f'API class for {api_name}',
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        api_gfc_id = cursor.lastrowid
        class_id_map[api_class_name] = api_gfc_id
        
        print(f"\n✅ Created API parent class: {api_class_name} (ID: {api_gfc_id}, Type: API)")
        
        # Add API-level fields
        api_info = swagger_data.get('info', {})
        api_fields = [
            {'name': 'apiName', 'type': 'TEXT', 'description': f'API identifier: {api_info.get("title", api_name)}'},
            {'name': 'apiVersion', 'type': 'TEXT', 'description': f'API version: {api_info.get("version", "1.0.0")}'},
            {'name': 'endpoint', 'type': 'TEXT', 'description': 'API endpoint path'}
        ]
        
        for field in api_fields:
            cursor.execute("""
                INSERT INTO GEE_FIELDS 
                (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_DESCRIPTION, CREATE_DATE, UPDATE_DATE)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                api_gfc_id,
                field['name'],
                field['type'],
                None,
                field['description'],
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            print(f"  ➕ Added field: {field['name']} [{field['type']}] - {field['description']}")
        
        # Step 2: Create child classes
        print(f"\n🔄 Processing {len(field_classes)} child classes...")
        
        for class_name, field_class in field_classes.items():
            # Determine class type based on name patterns
            class_type = 'OBJECT'
            if 'Request' in class_name:
                class_type = 'REQUEST'
            elif 'Response' in class_name:
                class_type = 'RESPONSE'
            elif 'Error' in class_name:
                class_type = 'ERROR'
            
            # Insert field class as child of API class
            cursor.execute("""
                INSERT INTO GEE_FIELD_CLASSES 
                (FIELD_CLASS_NAME, CLASS_TYPE, PARENT_GFC_ID, DESCRIPTION, CREATE_DATE, UPDATE_DATE)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                class_name,
                class_type,
                api_gfc_id,  # All classes are children of the API class
                field_class.get('description', f'Generated from {class_name}'),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            gfc_id = cursor.lastrowid
            class_id_map[class_name] = gfc_id
            
            print(f"✅ Created child class: {class_name} (ID: {gfc_id}, Type: {class_type}) (Parent: {api_class_name})")
            
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
                
                max_len_info = f"({field.get('max_length')})" if field.get('max_length') else ""
                print(f"  ➕ Added field: {field['name']} [{field['type']}{max_len_info}] - {field.get('description', 'No description')}")
        
        # Commit changes
        conn.commit()
        
        total_classes = len(field_classes) + 1  # +1 for API class
        print(f"\n🎉 SUCCESS: Created hierarchical structure with {total_classes} field classes")
        print(f"   API Parent Class: 1")
        print(f"   Child Classes: {len(field_classes)}")
        
        # Verification
        print(f"\n📊 Verification:")
        
        # Show API class first
        cursor.execute("""
            SELECT fc.GFC_ID, fc.CLASS_TYPE, COUNT(f.GF_ID) as FIELD_COUNT
            FROM GEE_FIELD_CLASSES fc
            LEFT JOIN GEE_FIELDS f ON fc.GFC_ID = f.GFC_ID
            WHERE fc.FIELD_CLASS_NAME = ?
            GROUP BY fc.GFC_ID
        """, (api_class_name,))
        
        result = cursor.fetchone()
        if result:
            gfc_id, class_type, field_count = result
            print(f"   • {api_class_name} [{class_type}] - Parent: None - Fields: {field_count}")
            
            # Show API fields
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
        
        # Show child classes
        for class_name in field_classes.keys():
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
                print(f"   • {class_name} [{class_type}] - Parent: {parent_name} - Fields: {field_count}")
                
                # Show first few fields
                cursor.execute("""
                    SELECT GF_NAME, GF_TYPE, GF_SIZE, GF_DESCRIPTION
                    FROM GEE_FIELDS 
                    WHERE GFC_ID = ? 
                    ORDER BY GF_NAME
                    LIMIT 3
                """, (gfc_id,))
                
                fields = cursor.fetchall()
                for field_name, data_type, max_length, description in fields:
                    max_len_str = f"({max_length})" if max_length else ""
                    print(f"     - {field_name} [{data_type}{max_len_str}] - {description[:50]}...")
        
        print("=" * 70)
        print("✅ Hierarchical import completed successfully!")
        print(f"   Result: 1 API parent + {len(field_classes)} child classes with proper hierarchy")
        
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
    print("🚀 Starting Enhanced Hierarchical Import Test")
    print("=" * 70)
    
    # Test with US Sales Tax API
    success = create_hierarchical_structure(
        'temp/US_Sales_Tax_Calculator_API.json',
        'US Sales Tax Calculator'
    )
    
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("❌ Test failed!")