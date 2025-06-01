#!/usr/bin/env python3
"""
Test script for enhanced field class deletion functionality
"""
import requests
import json

BASE_URL = "http://localhost:5002"

def test_get_deletion_info(gfc_id):
    """Test getting deletion information for a field class"""
    print(f"\n=== Testing deletion info for class ID {gfc_id} ===")
    
    url = f"{BASE_URL}/classes/get_class_deletion_info/{gfc_id}"
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Successfully retrieved deletion info")
            
            # Display field class info
            field_class = data['field_class']
            print(f"Field Class: {field_class['FIELD_CLASS_NAME']} ({field_class['CLASS_TYPE']})")
            
            # Display totals
            totals = data['totals']
            print(f"Direct Fields: {totals['fields_count']}")
            print(f"Child Classes: {totals['child_classes_count']}")
            print(f"Child Fields: {totals['child_fields_count']}")
            print(f"Total Fields: {totals['total_fields_count']}")
            print(f"Rules Using: {totals['rules_using_count']}")
            
            # Display fields
            if data['fields']:
                print("\nDirect Fields:")
                for field in data['fields']:
                    print(f"  - {field['GF_NAME']} ({field['GF_TYPE']})")
            
            # Display child classes
            if data['child_classes']:
                print("\nChild Classes:")
                for child in data['child_classes']:
                    print(f"  - {child['FIELD_CLASS_NAME']} ({child['FIELD_COUNT']} fields)")
            
            # Display rules
            if data['rules_using_class']:
                print("\nRules Using Class:")
                for rule in data['rules_using_class']:
                    print(f"  - {rule['RULE_NAME']} (ID: {rule['RULE_ID']})")
            
            return True
        else:
            print(f"❌ Error: {data.get('message')}")
            return False
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        return False

def test_field_classes_page():
    """Test that the field classes page loads correctly"""
    print("\n=== Testing Field Classes Page ===")
    
    url = f"{BASE_URL}/classes/"
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Field classes page loads successfully")
        
        # Check if the page contains the enhanced delete modal
        content = response.text
        if 'deleteInformation' in content:
            print("✅ Enhanced delete modal HTML found")
        else:
            print("❌ Enhanced delete modal HTML not found")
        
        if 'confirmDeletionCheckbox' in content:
            print("✅ Confirmation checkbox found")
        else:
            print("❌ Confirmation checkbox not found")
        
        if 'deletionDetailsAccordion' in content:
            print("✅ Deletion details accordion found")
        else:
            print("❌ Deletion details accordion not found")
        
        return True
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        return False

def test_get_classes_api():
    """Test the get classes API endpoint"""
    print("\n=== Testing Get Classes API ===")
    
    url = f"{BASE_URL}/classes/get_classes"
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved {len(data)} field classes")
        
        # Display first few classes
        for i, cls in enumerate(data[:5]):
            parent_name = cls.get('PARENT_CLASS_NAME', 'None')
            print(f"  {i+1}. {cls['FIELD_CLASS_NAME']} ({cls['CLASS_TYPE']}) - Parent: {parent_name}")
        
        return True
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Enhanced Field Class Deletion Functionality")
    print("=" * 60)
    
    # Test 1: Check if the main page loads
    test_field_classes_page()
    
    # Test 2: Check if the API works
    test_get_classes_api()
    
    # Test 3: Test deletion info for different scenarios
    
    # Test parent class with children (CanadianGSTCalculationAPI)
    test_get_deletion_info(1)
    
    # Test child class with fields (TaxCalculationRequest)
    test_get_deletion_info(2)
    
    # Test class with many fields (SalesTaxResponse - GFC_ID 6 has 12 fields)
    test_get_deletion_info(6)
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print("- Field classes page should load with enhanced delete modal")
    print("- Deletion info API should return detailed information")
    print("- Different types of classes should show appropriate warnings")
    print("- The UI should display all information in organized sections")

if __name__ == "__main__":
    main()