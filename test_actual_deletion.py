#!/usr/bin/env python3
"""
Test script for actual field class deletion functionality
Tests the complete workflow including the enhanced delete endpoint
"""
import requests
import json
import sqlite3

BASE_URL = "http://localhost:5002"
DB_PATH = "instance/GEE.db"

def get_class_info_from_db(gfc_id):
    """Get class information directly from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get class info
    cursor.execute("SELECT * FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?", (gfc_id,))
    class_info = cursor.fetchone()
    
    # Get field count
    cursor.execute("SELECT COUNT(*) as count FROM GEE_FIELDS WHERE GFC_ID = ?", (gfc_id,))
    field_count = cursor.fetchone()['count']
    
    # Get child classes count
    cursor.execute("SELECT COUNT(*) as count FROM GEE_FIELD_CLASSES WHERE PARENT_GFC_ID = ?", (gfc_id,))
    child_count = cursor.fetchone()['count']
    
    conn.close()
    
    return {
        'class_info': dict(class_info) if class_info else None,
        'field_count': field_count,
        'child_count': child_count
    }

def test_enhanced_deletion_workflow(gfc_id):
    """Test the complete enhanced deletion workflow"""
    print(f"\n=== Testing Enhanced Deletion Workflow for Class ID {gfc_id} ===")
    
    # Step 1: Get initial state from database
    initial_state = get_class_info_from_db(gfc_id)
    if not initial_state['class_info']:
        print(f"❌ Class {gfc_id} not found in database")
        return False
    
    class_name = initial_state['class_info']['FIELD_CLASS_NAME']
    print(f"Initial State: {class_name}")
    print(f"  - Fields: {initial_state['field_count']}")
    print(f"  - Child Classes: {initial_state['child_count']}")
    
    # Step 2: Get deletion information via API
    print("\n1. Getting deletion information...")
    info_url = f"{BASE_URL}/classes/get_class_deletion_info/{gfc_id}"
    info_response = requests.get(info_url)
    
    if info_response.status_code != 200:
        print(f"❌ Failed to get deletion info: {info_response.status_code}")
        return False
    
    info_data = info_response.json()
    if not info_data.get('success'):
        print(f"❌ Deletion info API error: {info_data.get('message')}")
        return False
    
    print("✅ Successfully retrieved deletion information")
    totals = info_data['totals']
    print(f"  - Total fields to delete: {totals['total_fields_count']}")
    print(f"  - Child classes to delete: {totals['child_classes_count']}")
    print(f"  - Rules to unlink: {totals['rules_using_count']}")
    
    # Step 3: Perform the actual deletion
    print("\n2. Performing enhanced deletion...")
    delete_url = f"{BASE_URL}/classes/delete_class_with_fields/{gfc_id}"
    delete_response = requests.delete(delete_url)
    
    if delete_response.status_code != 200:
        print(f"❌ Failed to delete: {delete_response.status_code}")
        return False
    
    delete_data = delete_response.json()
    if not delete_data.get('success'):
        print(f"❌ Deletion API error: {delete_data.get('message')}")
        return False
    
    print("✅ Successfully deleted field class")
    print(f"Message: {delete_data['message']}")
    
    if 'deleted_items' in delete_data:
        deleted = delete_data['deleted_items']
        print(f"Deleted items:")
        print(f"  - Fields: {deleted['fields']}")
        print(f"  - Child classes: {deleted['child_classes']}")
        print(f"  - Child fields: {deleted['child_fields']}")
        print(f"  - Rules unlinked: {deleted['rules']}")
    
    # Step 4: Verify deletion from database
    print("\n3. Verifying deletion...")
    final_state = get_class_info_from_db(gfc_id)
    
    if final_state['class_info'] is None:
        print("✅ Class successfully removed from database")
        return True
    else:
        print("❌ Class still exists in database")
        return False

def create_test_class_for_deletion():
    """Create a test class that we can safely delete"""
    print("\n=== Creating Test Class for Deletion ===")
    
    # Create a test class
    create_url = f"{BASE_URL}/classes/add_class"
    test_data = {
        'className': 'TestDeleteClass',
        'type': 'CUSTOM',
        'description': 'Test class for deletion testing',
        'parentGfcId': None
    }
    
    response = requests.post(create_url, json=test_data)
    if response.status_code != 200:
        print(f"❌ Failed to create test class: {response.status_code}")
        return None
    
    data = response.json()
    if not data.get('success'):
        print(f"❌ Failed to create test class: {data.get('message')}")
        return None
    
    # Get the created class ID
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = ?", ('TestDeleteClass',))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        test_class_id = result[0]
        print(f"✅ Created test class with ID: {test_class_id}")
        return test_class_id
    else:
        print("❌ Failed to find created test class")
        return None

def main():
    """Run the complete deletion test suite"""
    print("🧪 Testing Enhanced Field Class Deletion - Complete Workflow")
    print("=" * 70)
    
    # Test 1: Test deletion info for various scenarios (without deleting)
    print("\n📋 PHASE 1: Testing Deletion Information API")
    
    # Test complex parent class (but don't delete it)
    info_url = f"{BASE_URL}/classes/get_class_deletion_info/1"
    response = requests.get(info_url)
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Complex parent class deletion info works")
            totals = data['totals']
            print(f"   Would delete {totals['total_fields_count']} total fields, {totals['child_classes_count']} child classes")
        else:
            print(f"❌ Error: {data.get('message')}")
    
    # Test 2: Create and delete a test class
    print("\n🗑️  PHASE 2: Testing Actual Deletion")
    
    test_class_id = create_test_class_for_deletion()
    if test_class_id:
        success = test_enhanced_deletion_workflow(test_class_id)
        if success:
            print("✅ Test class deletion completed successfully")
        else:
            print("❌ Test class deletion failed")
    
    # Test 3: Test deletion of a real class with fields (but safe to delete)
    print("\n🎯 PHASE 3: Testing Real Class Deletion")
    
    # Find a safe class to delete (leaf node with few fields)
    safe_classes = [10, 11, 12]  # These are child classes with fields but no children
    
    for class_id in safe_classes:
        class_info = get_class_info_from_db(class_id)
        if class_info['class_info'] and class_info['child_count'] == 0:
            print(f"\nTesting deletion of class {class_id}: {class_info['class_info']['FIELD_CLASS_NAME']}")
            success = test_enhanced_deletion_workflow(class_id)
            if success:
                print(f"✅ Successfully deleted class {class_id}")
                break
            else:
                print(f"❌ Failed to delete class {class_id}")
        else:
            print(f"Skipping class {class_id} (not found or has children)")
    
    print("\n" + "=" * 70)
    print("🎯 Test Summary:")
    print("- Enhanced deletion API should provide detailed information")
    print("- Actual deletion should remove class, fields, and update related data")
    print("- Database should be consistent after deletion")
    print("- UI workflow should be smooth and informative")

if __name__ == "__main__":
    main()