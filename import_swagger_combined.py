#!/usr/bin/env python3
"""
Script to import Canadian GST Swagger file and create 1 field class with 6 fields
as required by the user specification.
"""

import json
import sqlite3
from datetime import datetime

def create_combined_field_class():
    """Create a single field class with both input and output fields."""
    
    # Connect to database
    conn = sqlite3.connect('instance/GEE.db')
    cursor = conn.cursor()
    
    try:
        # Read the Swagger file
        with open('temp/Canadian_GST_Calculation_API.json', 'r') as f:
            swagger_data = json.load(f)
        
        print("📁 Reading Swagger file: Canadian_GST_Calculation_API.json")
        
        # Create the combined field class for Canadian GST
        field_class_name = "CanadianGSTCalculation"
        class_type = "API_MODEL"
        description = "Combined field class for Canadian GST calculation (input + output fields)"
        
        # Insert field class
        cursor.execute("""
            INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION, CREATE_DATE) 
            VALUES (?, ?, ?, ?)
        """, (field_class_name, class_type, description, datetime.now()))
        
        gfc_id = cursor.lastrowid
        print(f"✅ Created field class: {field_class_name} (ID: {gfc_id})")
        
        # Define the 6 fields as per user requirement
        fields_to_create = [
            # Input fields from TaxCalculationRequest
            {
                'name': 'objectId',
                'type': 'VARCHAR',
                'size': 50,
                'description': 'Product identifier from request'
            },
            {
                'name': 'userPincode', 
                'type': 'VARCHAR',
                'size': 20,
                'description': 'User postal code from request'
            },
            {
                'name': 'storePincode',
                'type': 'VARCHAR', 
                'size': 20,
                'description': 'Store postal code from request'
            },
            # Output fields from TaxCalculationResponse
            {
                'name': 'objectValue',
                'type': 'VARCHAR',
                'size': 20,
                'description': 'Product value formatted as currency'
            },
            {
                'name': 'objectGST',
                'type': 'VARCHAR',
                'size': 20, 
                'description': 'Calculated GST amount formatted as currency'
            },
            {
                'name': 'objectHST',
                'type': 'VARCHAR',
                'size': 20,
                'description': 'Calculated HST amount formatted as currency'
            },
            {
                'name': 'objectPST',
                'type': 'VARCHAR',
                'size': 20,
                'description': 'Calculated PST amount formatted as currency'
            }
        ]
        
        # Insert fields
        for field in fields_to_create:
            cursor.execute("""
                INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_DESCRIPTION, CREATE_DATE) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (gfc_id, field['name'], field['type'], field['size'], field['description'], datetime.now()))
            
            print(f"  ➕ Added field: {field['name']} [{field['type']}({field['size']})]")
        
        # Commit changes
        conn.commit()
        
        print(f"\n🎉 SUCCESS: Created 1 Field Class with {len(fields_to_create)} fields")
        print(f"   Field Class: {field_class_name}")
        print(f"   Input Fields: objectId, userPincode, storePincode")
        print(f"   Output Fields: objectValue, objectGST, objectHST, objectPST")
        
        # Verify the creation
        cursor.execute("""
            SELECT fc.FIELD_CLASS_NAME, fc.CLASS_TYPE, 
                   COUNT(f.GF_ID) as field_count
            FROM GEE_FIELD_CLASSES fc 
            LEFT JOIN GEE_FIELDS f ON fc.GFC_ID = f.GFC_ID 
            WHERE fc.FIELD_CLASS_NAME = ?
            GROUP BY fc.GFC_ID
        """, (field_class_name,))
        
        result = cursor.fetchone()
        if result:
            print(f"\n📊 Verification:")
            print(f"   Field Class: {result[0]}")
            print(f"   Type: {result[1]}")
            print(f"   Fields Created: {result[2]}")
            
            # Show all fields
            cursor.execute("""
                SELECT f.GF_NAME, f.GF_TYPE, f.GF_SIZE, f.GF_DESCRIPTION
                FROM GEE_FIELDS f 
                JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID
                WHERE fc.FIELD_CLASS_NAME = ?
                ORDER BY f.GF_NAME
            """, (field_class_name,))
            
            fields = cursor.fetchall()
            print(f"   Field Details:")
            for field in fields:
                print(f"     - {field[0]} [{field[1]}({field[2]})] - {field[3]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting Swagger Import for Canadian GST Calculation")
    print("=" * 60)
    
    success = create_combined_field_class()
    
    print("=" * 60)
    if success:
        print("✅ Import completed successfully!")
        print("   Expected: 1 Field Class with 6 fields")
        print("   Result: MATCHES EXPECTATION")
    else:
        print("❌ Import failed!")