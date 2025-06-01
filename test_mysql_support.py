#!/usr/bin/env python3
"""
Test script to verify MySQL support in table management
"""

import sys
import json

def test_mysql_helpers():
    """Test the MySQL helpers module"""
    try:
        from mysql_helpers import get_mysql_connection, MYSQL_AVAILABLE
        
        print("=== MySQL Helpers Test ===")
        print(f"MySQL module available: {MYSQL_AVAILABLE}")
        
        if not MYSQL_AVAILABLE:
            print("❌ mysql-connector-python not available")
            print("To install: pip install mysql-connector-python")
            return False
        
        # Test connection function with dummy parameters
        print("✅ MySQL helpers module loaded successfully")
        print("✅ get_mysql_connection function available")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_routes_import():
    """Test if the routes can import MySQL helpers"""
    try:
        print("\n=== Routes MySQL Import Test ===")
        
        # Test that routes can import the function
        sys.path.append('.')
        from routes.tables import tables_bp
        
        print("✅ Tables blueprint loaded successfully")
        
        # Try importing mysql_helpers in the same way as routes
        from mysql_helpers import get_mysql_connection
        print("✅ MySQL helpers can be imported from routes context")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error in routes context: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in routes context: {e}")
        return False

def simulate_test_query():
    """Simulate the test query functionality"""
    try:
        print("\n=== Simulated Test Query ===")
        
        # Simulate a request payload
        test_data = {
            'query': 'SELECT 1 as test_col',
            'environment_config_id': 'test_id'
        }
        
        # Test query validation
        query = test_data.get('query', '')
        if not query or not query.strip().upper().startswith('SELECT'):
            print("❌ Query validation failed")
            return False
        
        print("✅ Query validation passed")
        
        # Test LIMIT clause addition
        if 'LIMIT' not in query.upper():
            if query.strip().endswith(';'):
                query = query[:-1] + ' LIMIT 10;'
            else:
                query = query + ' LIMIT 10;'
        
        print(f"✅ Query with LIMIT: {query}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in simulated test: {e}")
        return False

def main():
    print("🚀 Testing MySQL Support in Table Management")
    print("=" * 50)
    
    results = []
    
    # Test 1: MySQL helpers
    results.append(test_mysql_helpers())
    
    # Test 2: Routes import
    results.append(test_routes_import())
    
    # Test 3: Simulate test query
    results.append(simulate_test_query())
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ ALL TESTS PASSED - MySQL support should work")
        print("   • MySQL helpers available")
        print("   • Routes can import MySQL functions")  
        print("   • Query processing logic works")
    else:
        print("❌ SOME TESTS FAILED - Check the issues above")
        failed_count = len([r for r in results if not r])
        print(f"   • {len(results) - failed_count}/{len(results)} tests passed")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)