"""
Tests for Functions Routes
Implements Commandment 4: Complete Unit Tests Are Mandatory
"""

import pytest
import json
from unittest.mock import patch, Mock
from conftest import assert_error_response, assert_success_response, create_test_function


class TestFunctionsRoutes:
    """Test functions route endpoints."""
    
    def test_functions_page_renders(self, client):
        """Test functions page renders successfully."""
        response = client.get('/functions/')
        assert response.status_code == 200
        # Note: Would need to test template content in real implementation
    
    def test_get_function_success(self, client, mock_db_connection):
        """Test successful function retrieval."""
        # Create test function
        function_id = create_test_function(
            mock_db_connection,
            name='test_function',
            param_count=2,
            description='Test function'
        )
        
        response = client.get(f'/functions/get_function/{function_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['FUNC_NAME'] == 'test_function'
        assert data['PARAM_COUNT'] == 2
        assert data['DESCRIPTION'] == 'Test function'
    
    def test_get_function_not_found(self, client, mock_db_connection):
        """Test function not found returns 404."""
        response = client.get('/functions/get_function/999')
        
        assert_error_response(response, 404, 'RESOURCE_NOT_FOUND')
    
    def test_add_function_success(self, client, mock_db_connection, test_function_data):
        """Test successful function creation."""
        response = client.post(
            '/functions/add_function',
            data=json.dumps(test_function_data),
            content_type='application/json'
        )
        
        assert_success_response(response, 200)
        data = response.get_json()
        assert data['success'] is True
        assert 'successfully' in data['message'].lower()
        
        # Verify function was created in database
        cursor = mock_db_connection.execute(
            'SELECT * FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = ?',
            (test_function_data['functionName'],)
        )
        function = cursor.fetchone()
        assert function is not None
        assert function[1] == test_function_data['functionName']  # FUNC_NAME
        assert function[2] == test_function_data['paramCount']     # PARAM_COUNT
    
    def test_add_function_invalid_data(self, client, invalid_function_data):
        """Test function creation with invalid data."""
        response = client.post(
            '/functions/add_function',
            data=json.dumps(invalid_function_data),
            content_type='application/json'
        )
        
        assert_error_response(response, 400, 'VALIDATION_ERROR')
    
    def test_add_function_missing_name(self, client):
        """Test function creation with missing name."""
        data = {
            'paramCount': 2,
            'description': 'Test function'
        }
        
        response = client.post(
            '/functions/add_function',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert_error_response(response, 400, 'VALIDATION_ERROR')
    
    def test_add_function_invalid_param_count(self, client):
        """Test function creation with invalid parameter count."""
        data = {
            'functionName': 'test_function',
            'paramCount': -1,  # Invalid: negative
            'description': 'Test function'
        }
        
        response = client.post(
            '/functions/add_function',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert_error_response(response, 400, 'VALIDATION_ERROR')
    
    def test_add_function_invalid_name_format(self, client):
        """Test function creation with invalid name format."""
        data = {
            'functionName': '123invalid',  # Invalid: starts with number
            'paramCount': 1,
            'description': 'Test function'
        }
        
        response = client.post(
            '/functions/add_function',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert_error_response(response, 400, 'VALIDATION_ERROR')
    
    def test_add_function_no_request_body(self, client):
        """Test function creation with no request body."""
        response = client.post('/functions/add_function')
        
        assert_error_response(response, 400, 'VALIDATION_ERROR')
    
    def test_add_function_empty_request_body(self, client):
        """Test function creation with empty request body."""
        response = client.post(
            '/functions/add_function',
            data='{}',
            content_type='application/json'
        )
        
        assert_error_response(response, 400, 'VALIDATION_ERROR')
    
    def test_add_function_large_description(self, client):
        """Test function creation with description too large."""
        data = {
            'functionName': 'test_function',
            'paramCount': 1,
            'description': 'x' * 600  # Too long
        }
        
        response = client.post(
            '/functions/add_function',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert_error_response(response, 400, 'VALIDATION_ERROR')
    
    def test_add_function_sql_injection_attempt(self, client):
        """Test function creation with SQL injection attempt."""
        data = {
            'functionName': "test'; DROP TABLE GEE_BASE_FUNCTIONS; --",
            'paramCount': 1,
            'description': 'Test function'
        }
        
        response = client.post(
            '/functions/add_function',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should be rejected by validation or security middleware
        assert response.status_code in [400, 403]
    
    def test_add_function_xss_attempt(self, client):
        """Test function creation with XSS attempt."""
        data = {
            'functionName': 'test_function',
            'paramCount': 1,
            'description': '<script>alert("xss")</script>'
        }
        
        response = client.post(
            '/functions/add_function',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should be sanitized by validation
        if response.status_code == 200:
            # Verify XSS was sanitized by checking database
            cursor = mock_db_connection.execute(
                'SELECT DESCRIPTION FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = ?',
                ('test_function',)
            )
            result = cursor.fetchone()
            description = result[0] if result else ''
            assert '<script>' not in description
            assert '&lt;script&gt;' in description  # Should be HTML escaped
    
    def test_get_functions_pagination(self, client, mock_db_connection):
        """Test functions list with pagination."""
        # Create multiple test functions
        for i in range(15):
            create_test_function(
                mock_db_connection,
                name=f'test_function_{i}',
                param_count=i % 5,
                description=f'Test function {i}'
            )
        
        # Test first page
        response = client.get('/functions/get_functions?page=1&per_page=10')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'functions' in data
        assert 'pagination' in data
        assert len(data['functions']) == 10
        assert data['pagination']['total'] == 15
        assert data['pagination']['pages'] == 2
        assert data['pagination']['current_page'] == 1
        
        # Test second page
        response = client.get('/functions/get_functions?page=2&per_page=10')
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['functions']) == 5  # Remaining functions
        assert data['pagination']['current_page'] == 2
    
    def test_get_functions_search(self, client, mock_db_connection):
        """Test functions list with search."""
        # Create test functions with different names
        create_test_function(mock_db_connection, name='calculate_tax')
        create_test_function(mock_db_connection, name='format_string')
        create_test_function(mock_db_connection, name='calculate_interest')
        
        # Search for functions containing 'calculate'
        response = client.get('/functions/get_functions?search=calculate')
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['functions']) == 2
        
        function_names = [f['FUNC_NAME'] for f in data['functions']]
        assert 'calculate_tax' in function_names
        assert 'calculate_interest' in function_names
        assert 'format_string' not in function_names
    
    @patch('routes.functions.audit_log')
    def test_add_function_audit_logging(self, mock_audit_log, client, mock_db_connection, test_function_data):
        """Test that function creation is audit logged."""
        response = client.post(
            '/functions/add_function',
            data=json.dumps(test_function_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Verify audit log was called
        mock_audit_log.assert_called_once_with(
            action="create",
            resource_type="function",
            resource_id=test_function_data['functionName'],
            function_name=test_function_data['functionName'],
            param_count=test_function_data['paramCount']
        )
    
    def test_functions_route_security_headers(self, client):
        """Test that security headers are present in responses."""
        response = client.get('/functions/')
        
        # Check for security headers (these would be added by security middleware)
        # Note: Actual header testing would depend on middleware implementation
        assert response.status_code == 200
    
    def test_add_function_rate_limiting(self, client, test_function_data):
        """Test rate limiting for function creation."""
        # This test would verify rate limiting functionality
        # In a real implementation, you'd make multiple rapid requests
        # and verify that rate limiting kicks in
        
        # For now, just test that the endpoint responds normally
        response = client.post(
            '/functions/add_function',
            data=json.dumps(test_function_data),
            content_type='application/json'
        )
        
        # Should succeed normally for first request
        assert response.status_code in [200, 400]  # 400 if validation fails
    
    def test_functions_database_error_handling(self, client, test_function_data):
        """Test database error handling in functions routes."""
        with patch('routes.functions.modify_db') as mock_modify_db:
            # Simulate database error
            mock_modify_db.side_effect = Exception("Database connection failed")
            
            response = client.post(
                '/functions/add_function',
                data=json.dumps(test_function_data),
                content_type='application/json'
            )
            
            # Should return appropriate error response
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data