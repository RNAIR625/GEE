#!/usr/bin/env python3
"""
Test script to verify function and parameter management functionality
"""

import requests
import json
import sqlite3
from datetime import datetime

def test_function_routes():
    """Test function management routes"""
    base_url = "http://localhost:5000"
    
    print("=== Testing Function Management ===")
    
    # Test 1: Add a new function
    print("\n1. Testing Add Function...")
    function_data = {
        "functionName": "TestFunction_" + str(int(datetime.now().timestamp())),
        "paramCount": 0,
        "description": "Test function for API verification"
    }
    
    try:
        response = requests.post(f"{base_url}/functions/add_function", 
                               json=function_data, 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Add function successful")
                function_added = True
            else:
                print(f"❌ Add function failed: {result.get('message')}")
                function_added = False
        else:
            print(f"❌ Add function failed with status {response.status_code}")
            function_added = False
    except Exception as e:
        print(f"❌ Add function failed with error: {e}")
        function_added = False
    
    # Test 2: Get all functions
    print("\n2. Testing Get Functions...")
    try:
        response = requests.get(f"{base_url}/functions/get_functions")
        
        if response.status_code == 200:
            functions = response.json()
            print(f"✅ Get functions successful - Found {len(functions)} functions")
            
            # Find our test function
            test_function = None
            for func in functions:
                if func['FUNC_NAME'] == function_data['functionName']:
                    test_function = func
                    break
            
            if test_function:
                print(f"✅ Test function found: ID {test_function['GBF_ID']}")
                function_id = test_function['GBF_ID']
            else:
                print("❌ Test function not found in results")
                function_id = None
        else:
            print(f"❌ Get functions failed with status {response.status_code}")
            function_id = None
    except Exception as e:
        print(f"❌ Get functions failed with error: {e}")
        function_id = None
    
    return function_added, function_id, function_data['functionName']

def test_parameter_routes(function_id, function_name):
    """Test parameter management routes"""
    if not function_id:
        print("❌ Cannot test parameters - no valid function ID")
        return False
    
    base_url = "http://localhost:5000"
    
    print(f"\n=== Testing Parameter Management for Function ID {function_id} ===")
    
    # Test 1: Add a parameter
    print("\n1. Testing Add Parameter...")
    parameter_data = {
        "gbfId": function_id,
        "sequence": 1,
        "paramName": "inputValue",
        "paramType": "VARCHAR",
        "paramIOType": "INPUT",
        "description": "Test input parameter"
    }
    
    try:
        response = requests.post(f"{base_url}/functions/add_function_parameter", 
                               json=parameter_data, 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Add parameter successful")
                parameter_added = True
            else:
                print(f"❌ Add parameter failed: {result.get('message')}")
                parameter_added = False
        else:
            print(f"❌ Add parameter failed with status {response.status_code}")
            parameter_added = False
    except Exception as e:
        print(f"❌ Add parameter failed with error: {e}")
        parameter_added = False
    
    # Test 2: Get function parameters
    print("\n2. Testing Get Function Parameters...")
    try:
        response = requests.get(f"{base_url}/functions/get_function_parameters/{function_id}")
        
        if response.status_code == 200:
            parameters = response.json()
            print(f"✅ Get parameters successful - Found {len(parameters)} parameters")
            
            # Check if our parameter exists
            test_parameter = None
            for param in parameters:
                if param['PARAM_NAME'] == parameter_data['paramName']:
                    test_parameter = param
                    break
            
            if test_parameter:
                print(f"✅ Test parameter found: ID {test_parameter['GBFP_ID']}")
                parameter_id = test_parameter['GBFP_ID']
            else:
                print("❌ Test parameter not found in results")
                parameter_id = None
        else:
            print(f"❌ Get parameters failed with status {response.status_code}")
            parameter_id = None
    except Exception as e:
        print(f"❌ Get parameters failed with error: {e}")
        parameter_id = None
    
    return parameter_added, parameter_id

def test_direct_database():
    """Test by directly querying the database"""
    print("\n=== Testing Direct Database Access ===")
    
    try:
        conn = sqlite3.connect('instance/GEE.db')
        cursor = conn.cursor()
        
        # Check functions table
        cursor.execute("SELECT COUNT(*) as count FROM GEE_BASE_FUNCTIONS")
        function_count = cursor.fetchone()[0]
        print(f"✅ Found {function_count} functions in database")
        
        # Check parameters table
        cursor.execute("SELECT COUNT(*) as count FROM GEE_BASE_FUNCTIONS_PARAMS")
        parameter_count = cursor.fetchone()[0]
        print(f"✅ Found {parameter_count} parameters in database")
        
        # Check recent functions
        cursor.execute("""
            SELECT GBF_ID, FUNC_NAME, PARAM_COUNT, DESCRIPTION 
            FROM GEE_BASE_FUNCTIONS 
            ORDER BY CREATE_DATE DESC 
            LIMIT 3
        """)
        recent_functions = cursor.fetchall()
        
        print("📋 Recent functions:")
        for func in recent_functions:
            print(f"   - ID {func[0]}: {func[1]} ({func[2]} params) - {func[3]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database access failed: {e}")
        return False

def main():
    print("🚀 Testing Functions Page Functionality")
    print("=" * 50)
    
    # Test functions first
    function_added, function_id, function_name = test_function_routes()
    
    # Test parameters if function was added successfully
    if function_added and function_id:
        parameter_added, parameter_id = test_parameter_routes(function_id, function_name)
    else:
        parameter_added = False
        parameter_id = None
    
    # Test direct database access
    db_accessible = test_direct_database()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    if function_added:
        print("✅ Function management: WORKING")
    else:
        print("❌ Function management: FAILED")
    
    if parameter_added:
        print("✅ Parameter management: WORKING")
    else:
        print("❌ Parameter management: FAILED")
    
    if db_accessible:
        print("✅ Database access: WORKING")
    else:
        print("❌ Database access: FAILED")
    
    all_working = function_added and parameter_added and db_accessible
    
    if all_working:
        print("\n🎉 ALL FUNCTIONALITY WORKING!")
    else:
        print(f"\n⚠️  SOME ISSUES FOUND - Please check the failures above")
    
    print("\nNote: Make sure the Flask application is running on http://localhost:5000")
    
    return all_working

if __name__ == "__main__":
    main()