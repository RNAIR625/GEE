#!/usr/bin/env python3
"""
Test the complete web flow for functions and parameters management
"""

import sys
import json
from datetime import datetime

def test_web_interface_flow():
    """Test the complete flow as if using the web interface"""
    
    try:
        sys.path.append('.')
        from app import app
        from routes.functions import functions_bp
        
        print("✅ Successfully imported Flask app and functions blueprint")
        
        with app.app_context():
            # Simulate web requests using the Flask test client
            client = app.test_client()
            
            print("\n=== Testing Web Interface Flow ===")
            
            # Test 1: Load functions page
            print("\n1. Testing Functions Page Load...")
            response = client.get('/functions/')
            if response.status_code == 200:
                print("✅ Functions page loads successfully")
            else:
                print(f"❌ Functions page failed to load: {response.status_code}")
                return False
            
            # Test 2: Get all functions (API call)
            print("\n2. Testing Get Functions API...")
            response = client.get('/functions/get_functions')
            if response.status_code == 200:
                functions = json.loads(response.data)
                print(f"✅ Get functions API successful - Found {len(functions)} functions")
                initial_function_count = len(functions)
            else:
                print(f"❌ Get functions API failed: {response.status_code}")
                return False
            
            # Test 3: Add a new function (simulate form submission)
            print("\n3. Testing Add Function API...")
            function_name = f"WebTestFunction_{int(datetime.now().timestamp())}"
            function_data = {
                "functionName": function_name,
                "paramCount": 0,
                "description": "Test function added via web interface simulation"
            }
            
            response = client.post('/functions/add_function',
                                 data=json.dumps(function_data),
                                 content_type='application/json')
            
            if response.status_code == 200:
                result = json.loads(response.data)
                if result.get('success'):
                    print(f"✅ Add function API successful: {result.get('message')}")
                    function_added = True
                else:
                    print(f"❌ Add function API failed: {result.get('message')}")
                    return False
            else:
                print(f"❌ Add function API failed: {response.status_code}")
                return False
            
            # Test 4: Verify function was added by getting updated list
            print("\n4. Testing Function List Update...")
            response = client.get('/functions/get_functions')
            if response.status_code == 200:
                functions = json.loads(response.data)
                new_function_count = len(functions)
                
                if new_function_count > initial_function_count:
                    print(f"✅ Function count increased from {initial_function_count} to {new_function_count}")
                    
                    # Find our new function
                    test_function = None
                    for func in functions:
                        if func['FUNC_NAME'] == function_name:
                            test_function = func
                            break
                    
                    if test_function:
                        function_id = test_function['GBF_ID']
                        print(f"✅ New function found with ID: {function_id}")
                    else:
                        print("❌ New function not found in list")
                        return False
                else:
                    print("❌ Function count did not increase")
                    return False
            else:
                print(f"❌ Failed to get updated function list: {response.status_code}")
                return False
            
            # Test 5: Add parameter to the function
            print("\n5. Testing Add Parameter API...")
            parameter_data = {
                "gbfId": function_id,
                "sequence": 1,
                "paramName": "testInput",
                "paramType": "VARCHAR",
                "paramIOType": "INPUT",
                "description": "Test input parameter added via web interface"
            }
            
            response = client.post('/functions/add_function_parameter',
                                 data=json.dumps(parameter_data),
                                 content_type='application/json')
            
            if response.status_code == 200:
                result = json.loads(response.data)
                if result.get('success'):
                    print(f"✅ Add parameter API successful: {result.get('message')}")
                else:
                    print(f"❌ Add parameter API failed: {result.get('message')}")
                    return False
            else:
                print(f"❌ Add parameter API failed: {response.status_code}")
                return False
            
            # Test 6: Get function parameters
            print("\n6. Testing Get Function Parameters API...")
            response = client.get(f'/functions/get_function_parameters/{function_id}')
            
            if response.status_code == 200:
                parameters = json.loads(response.data)
                print(f"✅ Get parameters API successful - Found {len(parameters)} parameters")
                
                if len(parameters) > 0:
                    param = parameters[0]
                    parameter_id = param['GBFP_ID']
                    print(f"✅ Parameter details:")
                    print(f"   ID: {parameter_id}")
                    print(f"   Name: {param['PARAM_NAME']}")
                    print(f"   Type: {param['PARAM_TYPE']}")
                    print(f"   I/O Type: {param['PARAM_IO_TYPE']}")
                else:
                    print("❌ No parameters found")
                    return False
            else:
                print(f"❌ Get parameters API failed: {response.status_code}")
                return False
            
            # Test 7: Add a second parameter (OUTPUT type)
            print("\n7. Testing Add Second Parameter...")
            parameter_data_2 = {
                "gbfId": function_id,
                "sequence": 2,
                "paramName": "testOutput",
                "paramType": "INTEGER",
                "paramIOType": "OUTPUT",
                "description": "Test output parameter"
            }
            
            response = client.post('/functions/add_function_parameter',
                                 data=json.dumps(parameter_data_2),
                                 content_type='application/json')
            
            if response.status_code == 200:
                result = json.loads(response.data)
                if result.get('success'):
                    print(f"✅ Add second parameter successful")
                else:
                    print(f"❌ Add second parameter failed: {result.get('message')}")
                    return False
            else:
                print(f"❌ Add second parameter failed: {response.status_code}")
                return False
            
            # Test 8: Verify parameter count updated in function list
            print("\n8. Testing Parameter Count Update...")
            response = client.get('/functions/get_functions')
            if response.status_code == 200:
                functions = json.loads(response.data)
                
                # Find our function again
                updated_function = None
                for func in functions:
                    if func['GBF_ID'] == function_id:
                        updated_function = func
                        break
                
                if updated_function:
                    param_count = updated_function['PARAM_COUNT']
                    print(f"✅ Function now shows {param_count} parameters")
                    
                    if param_count == 2:
                        print("✅ Parameter count correctly reflects added parameters")
                    else:
                        print(f"❌ Expected 2 parameters, got {param_count}")
                        return False
                else:
                    print("❌ Could not find updated function")
                    return False
            else:
                print(f"❌ Failed to get functions for parameter count check: {response.status_code}")
                return False
            
            print("\n✅ ALL WEB INTERFACE TESTS PASSED!")
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Testing Complete Web Interface Flow")
    print("=" * 50)
    
    success = test_web_interface_flow()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 WEB INTERFACE WORKING PERFECTLY!")
        print("✅ Page loading: Working")
        print("✅ Function management: Working")
        print("✅ Parameter management: Working")
        print("✅ API endpoints: Working")
        print("✅ Data persistence: Working")
        print("✅ Parameter counting: Working")
    else:
        print("❌ WEB INTERFACE ISSUES FOUND")
        print("Check the error messages above")
    
    return success

if __name__ == "__main__":
    main()