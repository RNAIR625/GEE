#!/usr/bin/env python3
"""
Direct test of functions functionality using the Flask app context
"""

import sys
import json
from datetime import datetime

def test_with_app_context():
    """Test functions functionality within Flask app context"""
    
    try:
        # Add the current directory to Python path
        sys.path.append('.')
        
        # Import Flask app and database helpers
        from app import app
        from db_helpers import query_db, modify_db
        
        print("✅ Successfully imported Flask app and database helpers")
        
        with app.app_context():
            print("\n=== Testing Function Management ===")
            
            # Test 1: Add a function
            print("\n1. Testing Add Function...")
            function_name = f"TestFunction_{int(datetime.now().timestamp())}"
            
            try:
                modify_db(
                    'INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES (?, ?, ?)',
                    (function_name, 0, 'Test function for verification')
                )
                print(f"✅ Function '{function_name}' added successfully")
                
                # Get the function ID
                function = query_db('SELECT * FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = ?', (function_name,), one=True)
                if function:
                    function_id = function['GBF_ID']
                    print(f"✅ Function ID: {function_id}")
                else:
                    print("❌ Could not retrieve function ID")
                    return False
                    
            except Exception as e:
                print(f"❌ Failed to add function: {e}")
                return False
            
            # Test 2: Add a parameter
            print("\n2. Testing Add Parameter...")
            
            try:
                modify_db('''
                    INSERT INTO GEE_BASE_FUNCTIONS_PARAMS 
                    (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, PARAM_IO_TYPE, DESCRIPTION) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (function_id, 1, 'inputValue', 'VARCHAR', 'INPUT', 'Test input parameter'))
                
                print("✅ Parameter added successfully")
                
                # Verify parameter was added
                params = query_db('SELECT * FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBF_ID = ?', (function_id,))
                print(f"✅ Found {len(params)} parameter(s) for function")
                
            except Exception as e:
                print(f"❌ Failed to add parameter: {e}")
                return False
            
            # Test 3: Get functions with parameter count
            print("\n3. Testing Get Functions Query...")
            
            try:
                functions = query_db('''
                    SELECT 
                        gbf.*,
                        COALESCE(param_count.actual_count, 0) as ACTUAL_PARAM_COUNT
                    FROM GEE_BASE_FUNCTIONS gbf
                    LEFT JOIN (
                        SELECT GBF_ID, COUNT(*) as actual_count 
                        FROM GEE_BASE_FUNCTIONS_PARAMS 
                        GROUP BY GBF_ID
                    ) param_count ON gbf.GBF_ID = param_count.GBF_ID
                    WHERE gbf.FUNC_NAME = ?
                ''', (function_name,))
                
                if functions:
                    func = functions[0]
                    print(f"✅ Function query successful:")
                    print(f"   Name: {func['FUNC_NAME']}")
                    print(f"   Stored PARAM_COUNT: {func['PARAM_COUNT']}")
                    print(f"   Actual PARAM_COUNT: {func['ACTUAL_PARAM_COUNT']}")
                else:
                    print("❌ No functions returned from query")
                    return False
                    
            except Exception as e:
                print(f"❌ Failed to query functions: {e}")
                return False
            
            # Test 4: Test parameter query
            print("\n4. Testing Get Parameters Query...")
            
            try:
                parameters = query_db('''
                    SELECT * FROM GEE_BASE_FUNCTIONS_PARAMS 
                    WHERE GBF_ID = ? 
                    ORDER BY GBF_SEQ
                ''', (function_id,))
                
                if parameters:
                    param = parameters[0]
                    print(f"✅ Parameter query successful:")
                    print(f"   Name: {param['PARAM_NAME']}")
                    print(f"   Type: {param['PARAM_TYPE']}")
                    print(f"   I/O Type: {param['PARAM_IO_TYPE']}")
                    print(f"   Sequence: {param['GBF_SEQ']}")
                else:
                    print("❌ No parameters returned from query")
                    return False
                    
            except Exception as e:
                print(f"❌ Failed to query parameters: {e}")
                return False
            
            print("\n✅ ALL TESTS PASSED - Function and parameter management working correctly!")
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the application root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    print("🚀 Direct Function Management Test")
    print("=" * 40)
    
    success = test_with_app_context()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 FUNCTION MANAGEMENT WORKING!")
        print("✅ Add function: Working")
        print("✅ Add parameter: Working") 
        print("✅ Database queries: Working")
    else:
        print("❌ FUNCTION MANAGEMENT ISSUES FOUND")
        print("Check the error messages above")
    
    return success

if __name__ == "__main__":
    main()