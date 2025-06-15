"""
Tests for Input Validators
Implements Commandment 4: Complete Unit Tests Are Mandatory
"""

import pytest
from marshmallow import ValidationError as MarshmallowValidationError
from validators import (
    CreateFunctionSchema, UpdateFunctionSchema, CreateRuleSchema,
    CreateFlowSchema, ConnectionConfigSchema, PaginationSchema,
    SecurityValidator, validate_with_schema
)
from exceptions import ValidationError


class TestCreateFunctionSchema:
    """Test CreateFunctionSchema validation."""
    
    def test_valid_function_data(self):
        """Test validation of valid function data."""
        schema = CreateFunctionSchema()
        data = {
            'functionName': 'calculate_tax',
            'paramCount': 3,
            'description': 'Calculate tax amount'
        }
        
        result = schema.load(data)
        
        assert result['functionName'] == 'calculate_tax'
        assert result['paramCount'] == 3
        assert result['description'] == 'Calculate tax amount'
    
    def test_function_name_validation(self):
        """Test function name validation rules."""
        schema = CreateFunctionSchema()
        
        # Test invalid names
        invalid_names = [
            '',  # Empty
            'a' * 101,  # Too long
            '123invalid',  # Starts with number
            'invalid-name',  # Contains dash
            'invalid name',  # Contains space
            'invalid.name',  # Contains dot
        ]
        
        for invalid_name in invalid_names:
            with pytest.raises(MarshmallowValidationError):
                schema.load({
                    'functionName': invalid_name,
                    'paramCount': 1
                })
    
    def test_param_count_validation(self):
        """Test parameter count validation."""
        schema = CreateFunctionSchema()
        
        # Valid parameter counts
        for count in [0, 1, 10, 20]:
            result = schema.load({
                'functionName': 'test_func',
                'paramCount': count
            })
            assert result['paramCount'] == count
        
        # Invalid parameter counts
        invalid_counts = [-1, 21, 'not_a_number', None]
        
        for invalid_count in invalid_counts:
            with pytest.raises(MarshmallowValidationError):
                schema.load({
                    'functionName': 'test_func',
                    'paramCount': invalid_count
                })
    
    def test_description_validation(self):
        """Test description validation."""
        schema = CreateFunctionSchema()
        
        # Valid descriptions
        valid_data = {
            'functionName': 'test_func',
            'paramCount': 1,
            'description': 'A' * 500  # Max length
        }
        result = schema.load(valid_data)
        assert len(result['description']) == 500
        
        # Missing description should default to empty
        minimal_data = {
            'functionName': 'test_func',
            'paramCount': 1
        }
        result = schema.load(minimal_data)
        assert result['description'] == ''
        
        # Too long description
        with pytest.raises(MarshmallowValidationError):
            schema.load({
                'functionName': 'test_func',
                'paramCount': 1,
                'description': 'A' * 501  # Too long
            })
    
    def test_required_fields(self):
        """Test required field validation."""
        schema = CreateFunctionSchema()
        
        # Missing functionName
        with pytest.raises(MarshmallowValidationError) as exc_info:
            schema.load({'paramCount': 1})
        assert 'functionName' in str(exc_info.value)
        
        # Missing paramCount
        with pytest.raises(MarshmallowValidationError) as exc_info:
            schema.load({'functionName': 'test_func'})
        assert 'paramCount' in str(exc_info.value)
    
    def test_html_sanitization(self):
        """Test that HTML is escaped in string fields."""
        schema = CreateFunctionSchema()
        data = {
            'functionName': 'test_func',
            'paramCount': 1,
            'description': '<script>alert("xss")</script>'
        }
        
        result = schema.load(data)
        
        # HTML should be escaped
        assert '<script>' not in result['description']
        assert '&lt;script&gt;' in result['description']


class TestUpdateFunctionSchema:
    """Test UpdateFunctionSchema validation."""
    
    def test_valid_update_data(self):
        """Test validation of valid update data."""
        schema = UpdateFunctionSchema()
        data = {
            'gbfId': 123,
            'functionName': 'updated_function',
            'paramCount': 2,
            'description': 'Updated description'
        }
        
        result = schema.load(data)
        
        assert result['gbfId'] == 123
        assert result['functionName'] == 'updated_function'
        assert result['paramCount'] == 2
        assert result['description'] == 'Updated description'
    
    def test_gbf_id_validation(self):
        """Test function ID validation."""
        schema = UpdateFunctionSchema()
        
        # Invalid IDs
        invalid_ids = [0, -1, 'not_a_number', None]
        
        for invalid_id in invalid_ids:
            with pytest.raises(MarshmallowValidationError):
                schema.load({
                    'gbfId': invalid_id,
                    'functionName': 'test_func',
                    'paramCount': 1
                })


class TestCreateRuleSchema:
    """Test CreateRuleSchema validation."""
    
    def test_valid_rule_data(self):
        """Test validation of valid rule data."""
        schema = CreateRuleSchema()
        data = {
            'name': 'Test Rule',
            'description': 'A test rule',
            'conditions': [{'field': 'age', 'operator': '>=', 'value': 18}],
            'actions': [{'type': 'approve'}],
            'priority': 100,
            'is_active': True
        }
        
        result = schema.load(data)
        
        assert result['name'] == 'Test Rule'
        assert len(result['conditions']) == 1
        assert len(result['actions']) == 1
        assert result['priority'] == 100
        assert result['is_active'] is True
    
    def test_conditions_validation(self):
        """Test conditions list validation."""
        schema = CreateRuleSchema()
        
        # Too many conditions
        with pytest.raises(MarshmallowValidationError):
            schema.load({
                'name': 'Test Rule',
                'conditions': [{}] * 11,  # Too many
                'actions': [{}]
            })
        
        # No conditions
        with pytest.raises(MarshmallowValidationError):
            schema.load({
                'name': 'Test Rule',
                'conditions': [],  # Empty
                'actions': [{}]
            })
    
    def test_actions_validation(self):
        """Test actions list validation."""
        schema = CreateRuleSchema()
        
        # Too many actions
        with pytest.raises(MarshmallowValidationError):
            schema.load({
                'name': 'Test Rule',
                'conditions': [{}],
                'actions': [{}] * 6  # Too many
            })
        
        # No actions
        with pytest.raises(MarshmallowValidationError):
            schema.load({
                'name': 'Test Rule',
                'conditions': [{}],
                'actions': []  # Empty
            })


class TestConnectionConfigSchema:
    """Test ConnectionConfigSchema validation."""
    
    def test_valid_connection_config(self):
        """Test validation of valid connection configuration."""
        schema = ConnectionConfigSchema()
        data = {
            'name': 'test_connection',
            'connection_type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_password'
        }
        
        result = schema.load(data)
        
        assert result['name'] == 'test_connection'
        assert result['connection_type'] == 'mysql'
        assert result['host'] == 'localhost'
        assert result['port'] == 3306
    
    def test_connection_type_validation(self):
        """Test connection type validation."""
        schema = ConnectionConfigSchema()
        
        # Valid types
        valid_types = ['mysql', 'oracle', 'postgresql', 'sqlite']
        for conn_type in valid_types:
            result = schema.load({
                'name': 'test',
                'connection_type': conn_type,
                'host': 'localhost',
                'port': 3306,
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            })
            assert result['connection_type'] == conn_type
        
        # Invalid type
        with pytest.raises(MarshmallowValidationError):
            schema.load({
                'name': 'test',
                'connection_type': 'invalid_type',
                'host': 'localhost',
                'port': 3306,
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            })
    
    def test_port_validation(self):
        """Test port number validation."""
        schema = ConnectionConfigSchema()
        
        # Valid ports
        for port in [1, 3306, 65535]:
            result = schema.load({
                'name': 'test',
                'connection_type': 'mysql',
                'host': 'localhost',
                'port': port,
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            })
            assert result['port'] == port
        
        # Invalid ports
        for port in [0, -1, 65536, 'not_a_number']:
            with pytest.raises(MarshmallowValidationError):
                schema.load({
                    'name': 'test',
                    'connection_type': 'mysql',
                    'host': 'localhost',
                    'port': port,
                    'database': 'test',
                    'username': 'user',
                    'password': 'pass'
                })


class TestPaginationSchema:
    """Test PaginationSchema validation."""
    
    def test_valid_pagination_params(self):
        """Test validation of valid pagination parameters."""
        schema = PaginationSchema()
        
        # Test with all parameters
        result = schema.load({
            'page': 5,
            'per_page': 50,
            'search': 'test query'
        })
        
        assert result['page'] == 5
        assert result['per_page'] == 50
        assert result['search'] == 'test query'
        
        # Test with defaults
        result = schema.load({})
        
        assert result['page'] == 1
        assert result['per_page'] == 10
        assert result['search'] == ''
    
    def test_pagination_limits(self):
        """Test pagination parameter limits."""
        schema = PaginationSchema()
        
        # Test page limits
        with pytest.raises(MarshmallowValidationError):
            schema.load({'page': 0})  # Too low
        
        with pytest.raises(MarshmallowValidationError):
            schema.load({'page': 1001})  # Too high
        
        # Test per_page limits
        with pytest.raises(MarshmallowValidationError):
            schema.load({'per_page': 0})  # Too low
        
        with pytest.raises(MarshmallowValidationError):
            schema.load({'per_page': 101})  # Too high
        
        # Test search length
        with pytest.raises(MarshmallowValidationError):
            schema.load({'search': 'x' * 101})  # Too long


class TestSecurityValidator:
    """Test SecurityValidator utility functions."""
    
    def test_validate_sql_input_safe(self):
        """Test SQL input validation with safe inputs."""
        validator = SecurityValidator()
        
        safe_inputs = [
            'normal text',
            'user@example.com',
            '12345',
            'Product Name',
            ''
        ]
        
        for safe_input in safe_inputs:
            assert validator.validate_sql_input(safe_input) is True
    
    def test_validate_sql_input_dangerous(self):
        """Test SQL input validation with dangerous inputs."""
        validator = SecurityValidator()
        
        dangerous_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "UNION SELECT * FROM passwords",
            "<script>alert('xss')</script>",
            "1; INSERT INTO users",
            "1 AND SLEEP(5)",
            "CHAR(65)"
        ]
        
        for dangerous_input in dangerous_inputs:
            assert validator.validate_sql_input(dangerous_input) is False
    
    def test_validate_file_path_safe(self):
        """Test file path validation with safe paths."""
        validator = SecurityValidator()
        
        safe_paths = [
            'documents/file.txt',
            'images/photo.jpg',
            'data.csv',
            'folder/subfolder/file.pdf'
        ]
        
        for safe_path in safe_paths:
            assert validator.validate_file_path(safe_path) is True
    
    def test_validate_file_path_dangerous(self):
        """Test file path validation with dangerous paths."""
        validator = SecurityValidator()
        
        dangerous_paths = [
            '../../../etc/passwd',
            '..\\..\\windows\\system32',
            '/etc/shadow',
            'c:\\windows\\system32\\config',
            '~/secret_file'
        ]
        
        for dangerous_path in dangerous_paths:
            assert validator.validate_file_path(dangerous_path) is False
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        validator = SecurityValidator()
        
        # Test normal filename
        assert validator.sanitize_filename('document.pdf') == 'document.pdf'
        
        # Test filename with dangerous characters
        result = validator.sanitize_filename('file<>name.txt')
        assert '<' not in result
        assert '>' not in result
        
        # Test very long filename
        long_name = 'a' * 200 + '.txt'
        result = validator.sanitize_filename(long_name)
        assert len(result) <= 100
        assert result.endswith('.txt')
    
    def test_validate_json_structure_safe(self):
        """Test JSON structure validation with safe structures."""
        validator = SecurityValidator()
        
        safe_structures = [
            {'key': 'value'},
            {'nested': {'key': 'value'}},
            {'list': [1, 2, 3]},
            {'mixed': {'list': [{'nested': 'value'}]}}
        ]
        
        for safe_structure in safe_structures:
            assert validator.validate_json_structure(safe_structure) is True
    
    def test_validate_json_structure_dangerous(self):
        """Test JSON structure validation with dangerous structures."""
        validator = SecurityValidator()
        
        # Test deeply nested structure
        deep_structure = {'a': {}}
        current = deep_structure['a']
        for i in range(10):  # Create very deep nesting
            current['nested'] = {}
            current = current['nested']
        
        assert validator.validate_json_structure(deep_structure, max_depth=5) is False
        
        # Test too many keys
        many_keys = {f'key_{i}': f'value_{i}' for i in range(200)}
        assert validator.validate_json_structure(many_keys, max_keys=100) is False


class TestValidateWithSchema:
    """Test validate_with_schema utility function."""
    
    def test_successful_validation(self):
        """Test successful validation with schema."""
        data = {
            'functionName': 'test_function',
            'paramCount': 2,
            'description': 'Test function'
        }
        
        result = validate_with_schema(CreateFunctionSchema, data)
        
        assert result['functionName'] == 'test_function'
        assert result['paramCount'] == 2
        assert result['description'] == 'Test function'
    
    def test_validation_error_conversion(self):
        """Test conversion of marshmallow errors to ValidationError."""
        data = {
            'functionName': '',  # Invalid
            'paramCount': -1     # Invalid
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate_with_schema(CreateFunctionSchema, data)
        
        error = exc_info.value
        assert error.error_code == 'VALIDATION_ERROR'
        assert 'validation_errors' in error.details
        assert 'failed_fields' in error.details
        assert 'functionName' in error.details['failed_fields']
        assert 'paramCount' in error.details['failed_fields']