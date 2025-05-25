#!/usr/bin/env python3
"""
Verification script for Canadian GST implementation
"""

import sqlite3

def verify_implementation():
    """Verify the current implementation matches requirements."""
    
    conn = sqlite3.connect('instance/GEE.db')
    cursor = conn.cursor()
    
    try:
        print("🔍 VERIFYING CANADIAN GST IMPLEMENTATION")
        print("=" * 50)
        
        # Check field classes
        cursor.execute("SELECT COUNT(*) FROM GEE_FIELD_CLASSES")
        total_classes = cursor.fetchone()[0]
        
        cursor.execute("SELECT FIELD_CLASS_NAME, CLASS_TYPE FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'CanadianGSTCalculation'")
        gst_class = cursor.fetchone()
        
        print(f"📊 FIELD CLASSES:")
        print(f"   Total Classes: {total_classes}")
        if gst_class:
            print(f"   GST Class: {gst_class[0]} ({gst_class[1]})")
            print(f"   ✅ 1 Field Class Created: PASS")
        else:
            print(f"   ❌ GST Class not found: FAIL")
            return False
        
        # Check fields
        cursor.execute("""
            SELECT f.GF_NAME, f.GF_TYPE, f.GF_SIZE, f.GF_DESCRIPTION
            FROM GEE_FIELDS f 
            JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID
            WHERE fc.FIELD_CLASS_NAME = 'CanadianGSTCalculation'
            ORDER BY f.GF_NAME
        """)
        
        fields = cursor.fetchall()
        field_count = len(fields)
        
        print(f"\n📋 FIELDS:")
        print(f"   Total Fields: {field_count}")
        
        # Expected fields
        expected_input = ['objectId', 'userPincode', 'storePincode']
        expected_output = ['objectValue', 'objectGST', 'objectHST', 'objectPST']
        
        input_fields = []
        output_fields = []
        
        for field in fields:
            field_name = field[0]
            print(f"   - {field_name} [{field[1]}({field[2]})] - {field[3]}")
            
            if field_name in expected_input:
                input_fields.append(field_name)
            elif field_name in expected_output:
                output_fields.append(field_name)
        
        print(f"\n🎯 REQUIREMENT VERIFICATION:")
        print(f"   Expected: 1 Field Class with 7 fields")
        print(f"   Current:  1 Field Class with {field_count} fields")
        
        if field_count == 7:
            print(f"   ✅ Field Count: PASS")
        else:
            print(f"   ❌ Field Count: FAIL (expected 7, got {field_count})")
        
        print(f"\n   Input Fields Required: {expected_input}")
        print(f"   Input Fields Found:    {sorted(input_fields)}")
        if sorted(input_fields) == sorted(expected_input):
            print(f"   ✅ Input Fields: PASS")
        else:
            print(f"   ❌ Input Fields: FAIL")
        
        print(f"\n   Output Fields Required: {expected_output}")
        print(f"   Output Fields Found:    {sorted(output_fields)}")
        if sorted(output_fields) == sorted(expected_output):
            print(f"   ✅ Output Fields: PASS")
        else:
            print(f"   ❌ Output Fields: FAIL")
        
        # Overall result
        print(f"\n🏆 OVERALL RESULT:")
        if (field_count == 7 and 
            sorted(input_fields) == sorted(expected_input) and 
            sorted(output_fields) == sorted(expected_output)):
            print(f"   ✅ IMPLEMENTATION MATCHES EXPECTATION")
            return True
        else:
            print(f"   ❌ IMPLEMENTATION NEEDS ADJUSTMENT")
            return False
        
    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")
        return False
        
    finally:
        conn.close()

def show_swagger_mapping():
    """Show how the fields map to the Swagger API."""
    print(f"\n🔗 SWAGGER API MAPPING:")
    print(f"   API Input (TaxCalculationRequest):")
    print(f"   ├── objectId     → CanadianGSTCalculation.objectId")
    print(f"   ├── userPincode  → CanadianGSTCalculation.userPincode")
    print(f"   └── storePincode → CanadianGSTCalculation.storePincode")
    print(f"")
    print(f"   API Output (TaxCalculationResponse):")
    print(f"   ├── objectValue  → CanadianGSTCalculation.objectValue")
    print(f"   ├── objectGST    → CanadianGSTCalculation.objectGST")
    print(f"   ├── objectHST    → CanadianGSTCalculation.objectHST")
    print(f"   └── objectPST    → CanadianGSTCalculation.objectPST")
    print(f"")
    print(f"   All 7 fields from Swagger API are now mapped")

if __name__ == "__main__":
    success = verify_implementation()
    show_swagger_mapping()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 VERIFICATION SUCCESSFUL!")
        print("   The implementation now matches the expectation:")
        print("   ✅ 1 Field Class created")
        print("   ✅ 7 Fields created (3 input + 4 output)")
    else:
        print("⚠️  VERIFICATION INCOMPLETE")
        print("   Please review the implementation details above.")