"""
Tests for Exception Hierarchy
Implements Commandment 4: Complete Unit Tests Are Mandatory
"""

import pytest
from exceptions import (
    ForgeError, ConfigurationError, DatabaseError, DatabaseConnectionError,
    ValidationError, AuthenticationError, AuthorizationError,
    PraxisCommunicationError, ExecutionError, ResourceNotFoundError,
    BusinessLogicError, ExternalServiceError, handle_database_error,
    handle_validation_error, wrap_exception
)


class TestForgeError:
    """Test base ForgeError functionality."""
    
    def test_basic_error_creation(self):
        """Test basic error creation."""
        error = ForgeError("Test error message")
        
        assert str(error) == "FORGEERROR: Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "FORGEERROR"
        assert error.details == {}
        assert error.cause is None
    
    def test_error_with_code_and_details(self):
        """Test error creation with custom code and details."""
        details = {'field': 'value', 'count': 42}
        error = ForgeError(
            message="Custom error",
            error_code="CUSTOM_ERROR",
            details=details
        )
        
        assert error.error_code == "CUSTOM_ERROR"
        assert error.details == details
        assert "field=value" in str(error)
        assert "count=42" in str(error)
    
    def test_error_with_cause(self):
        """Test error creation with cause."""
        original_error = ValueError("Original error")
        error = ForgeError("Wrapped error", cause=original_error)
        
        assert error.cause == original_error
        assert "Caused by: Original error" in str(error)
    
    def test_to_dict(self):
        """Test error dictionary serialization."""
        details = {'field': 'value'}
        original_error = ValueError("Original")
        error = ForgeError(
            message="Test error",
            error_code="TEST_ERROR",
            details=details,
            cause=original_error
        )
        
        error_dict = error.to_dict()
        
        assert error_dict['error'] == "TEST_ERROR"
        assert error_dict['message'] == "Test error"
        assert error_dict['details'] == details
        assert error_dict['caused_by'] == "Original"


class TestDatabaseError:
    """Test DatabaseError functionality."""
    
    def test_database_error_creation(self):
        """Test database error creation with operation details."""
        error = DatabaseError(
            message="Database operation failed",
            operation="INSERT",
            table="users"
        )
        
        assert error.error_code == "DATABASE_ERROR"
        assert error.details['operation'] == "INSERT"
        assert error.details['table'] == "users"
    
    def test_database_connection_error(self):
        """Test database connection error."""
        error = DatabaseConnectionError(
            message="Connection failed",
            connection_string="mysql://localhost:3306/test"
        )
        
        assert error.error_code == "DATABASE_CONNECTION_ERROR"
        assert error.details['connection_type'] == "mysql"


class TestValidationError:
    """Test ValidationError functionality."""
    
    def test_validation_error_creation(self):
        """Test validation error creation."""
        error = ValidationError(
            message="Field validation failed",
            field="email",
            value="invalid-email"
        )
        
        assert error.error_code == "VALIDATION_ERROR"
        assert error.details['field'] == "email"
        assert error.details['value'] == "invalid-email"
    
    def test_validation_error_long_value_truncation(self):
        """Test that long values are truncated for security."""
        long_value = "x" * 200
        error = ValidationError(
            message="Long value test",
            field="data",
            value=long_value
        )
        
        assert len(error.details['value']) <= 103  # 100 + "..."
        assert error.details['value'].endswith('...')


class TestAuthenticationError:
    """Test AuthenticationError functionality."""
    
    def test_authentication_error_creation(self):
        """Test authentication error creation."""
        error = AuthenticationError(
            message="Invalid credentials",
            user_id="user123"
        )
        
        assert error.error_code == "AUTHENTICATION_ERROR"
        assert error.details['user_id'] == "user123"


class TestAuthorizationError:
    """Test AuthorizationError functionality."""
    
    def test_authorization_error_creation(self):
        """Test authorization error creation."""
        error = AuthorizationError(
            message="Access denied",
            user_id="user123",
            required_permission="admin:read"
        )
        
        assert error.error_code == "AUTHORIZATION_ERROR"
        assert error.details['user_id'] == "user123"
        assert error.details['required_permission'] == "admin:read"


class TestPraxisCommunicationError:
    """Test PraxisCommunicationError functionality."""
    
    def test_praxis_communication_error_creation(self):
        """Test Praxis communication error creation."""
        error = PraxisCommunicationError(
            message="API call failed",
            endpoint="/api/v1/execute",
            status_code=500
        )
        
        assert error.error_code == "PRAXIS_COMMUNICATION_ERROR"
        assert error.details['endpoint'] == "/api/v1/execute"
        assert error.details['status_code'] == 500


class TestExecutionError:
    """Test ExecutionError functionality."""
    
    def test_execution_error_creation(self):
        """Test execution error creation."""
        error = ExecutionError(
            message="Rule execution failed",
            execution_id="exec123",
            rule_id="rule456",
            flow_id="flow789",
            phase="validation"
        )
        
        assert error.error_code == "EXECUTION_ERROR"
        assert error.details['execution_id'] == "exec123"
        assert error.details['rule_id'] == "rule456"
        assert error.details['flow_id'] == "flow789"
        assert error.details['phase'] == "validation"


class TestResourceNotFoundError:
    """Test ResourceNotFoundError functionality."""
    
    def test_resource_not_found_error_creation(self):
        """Test resource not found error creation."""
        error = ResourceNotFoundError(
            message="Resource not found",
            resource_type="function",
            resource_id="func123"
        )
        
        assert error.error_code == "RESOURCE_NOT_FOUND"
        assert error.details['resource_type'] == "function"
        assert error.details['resource_id'] == "func123"


class TestBusinessLogicError:
    """Test BusinessLogicError functionality."""
    
    def test_business_logic_error_creation(self):
        """Test business logic error creation."""
        error = BusinessLogicError(
            message="Business rule violated",
            rule_violation="maximum_amount_exceeded"
        )
        
        assert error.error_code == "BUSINESS_LOGIC_ERROR"
        assert error.details['rule_violation'] == "maximum_amount_exceeded"


class TestExternalServiceError:
    """Test ExternalServiceError functionality."""
    
    def test_external_service_error_creation(self):
        """Test external service error creation."""
        error = ExternalServiceError(
            message="External service unavailable",
            service_name="payment_gateway",
            endpoint="/api/charge"
        )
        
        assert error.error_code == "EXTERNAL_SERVICE_ERROR"
        assert error.details['service_name'] == "payment_gateway"
        assert error.details['endpoint'] == "/api/charge"


class TestErrorHandlingUtilities:
    """Test error handling utility functions."""
    
    def test_handle_database_error_sqlite(self):
        """Test handling SQLite errors."""
        import sqlite3
        
        # Test table not found error
        original_error = sqlite3.Error("no such table: test_table")
        handled_error = handle_database_error("SELECT", original_error, table="test_table")
        
        assert isinstance(handled_error, DatabaseError)
        assert "Table does not exist" in handled_error.message
        assert handled_error.details['table'] == "test_table"
        
        # Test database locked error
        original_error = sqlite3.Error("database is locked")
        handled_error = handle_database_error("UPDATE", original_error)
        
        assert "Database is locked" in handled_error.message
    
    def test_handle_validation_error(self):
        """Test validation error handling utility."""
        error = handle_validation_error(
            field="email",
            value="invalid@",
            validation_rule="must be valid email format"
        )
        
        assert isinstance(error, ValidationError)
        assert error.details['field'] == "email"
        assert error.details['value'] == "invalid@"
        assert error.details['validation_rule'] == "must be valid email format"
    
    def test_wrap_exception_forge_error(self):
        """Test wrapping ForgeError returns original."""
        original_error = ValidationError("Original validation error")
        wrapped_error = wrap_exception(original_error)
        
        assert wrapped_error is original_error
    
    def test_wrap_exception_generic_error(self):
        """Test wrapping generic exception."""
        original_error = ValueError("Generic error")
        wrapped_error = wrap_exception(
            cause=original_error,
            error_type=ValidationError,
            message="Wrapped validation error"
        )
        
        assert isinstance(wrapped_error, ValidationError)
        assert wrapped_error.cause == original_error
        assert wrapped_error.message == "Wrapped validation error"
    
    def test_wrap_exception_default_message(self):
        """Test wrapping exception with default message."""
        original_error = RuntimeError("Runtime issue")
        wrapped_error = wrap_exception(cause=original_error)
        
        assert isinstance(wrapped_error, ForgeError)
        assert "Operation failed: Runtime issue" in wrapped_error.message