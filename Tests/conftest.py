"""
Pytest configuration and fixtures for Forge tests.
Implements Commandment 4: Complete Unit Tests Are Mandatory
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from unittest.mock import Mock, patch

# Add the Forge directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Forge'))

from config_manager import ConfigManager, ForgeConfig, AppConfig, ServerConfig, DatabaseConfig
from exceptions import ForgeError, DatabaseError, ValidationError
from logging_config import get_logger


@pytest.fixture(scope='session')
def test_config():
    """Create test configuration."""
    return ForgeConfig(
        app=AppConfig(
            name='forge-test',
            version='1.0.0-test',
            environment='test',
            secret_key='test-secret-key',
            runtime_id='test-runtime-id',
            debug=True
        ),
        server=ServerConfig(
            host='localhost',
            port=5000,
            read_timeout=30,
            write_timeout=30
        ),
        database=DatabaseConfig(
            main_path=':memory:',
            worker_path=':memory:',
            runtime_path=':memory:',
            max_connections=5
        ),
        praxis=Mock(),
        logging=Mock(),
        security=Mock(),
        external_services=Mock()
    )


@pytest.fixture
def mock_config_manager(test_config):
    """Mock configuration manager."""
    with patch('config_manager.get_config') as mock_get_config:
        mock_get_config.return_value = test_config
        yield mock_get_config


@pytest.fixture
def temp_db():
    """Create temporary in-memory database for testing."""
    conn = sqlite3.connect(':memory:')
    
    # Create test tables
    conn.execute('''
        CREATE TABLE GEE_BASE_FUNCTIONS (
            GBF_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            FUNC_NAME TEXT NOT NULL UNIQUE,
            PARAM_COUNT INTEGER NOT NULL,
            DESCRIPTION TEXT,
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE GEE_BASE_FUNCTIONS_PARAMS (
            PARAM_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            GBF_ID INTEGER NOT NULL,
            PARAM_NAME TEXT NOT NULL,
            PARAM_TYPE TEXT NOT NULL,
            PARAM_ORDER INTEGER NOT NULL,
            FOREIGN KEY (GBF_ID) REFERENCES GEE_BASE_FUNCTIONS (GBF_ID)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE GEE_ACTIVE_CONNECTIONS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            APP_RUNTIME_ID TEXT NOT NULL,
            CONNECTION_NAME TEXT NOT NULL,
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_db_connection(temp_db):
    """Mock database connection."""
    with patch('db_helpers.get_db') as mock_get_db:
        mock_get_db.return_value = temp_db
        yield temp_db


@pytest.fixture
def test_function_data():
    """Test function data for tests."""
    return {
        'functionName': 'test_function',
        'paramCount': 2,
        'description': 'A test function'
    }


@pytest.fixture
def invalid_function_data():
    """Invalid function data for testing validation."""
    return {
        'functionName': '',  # Invalid: empty name
        'paramCount': -1,    # Invalid: negative count
        'description': 'x' * 600  # Invalid: too long
    }


@pytest.fixture
def flask_app(mock_config_manager, mock_db_connection):
    """Create Flask test application."""
    # Import here to avoid circular imports
    from app import app
    
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        yield app


@pytest.fixture
def client(flask_app):
    """Create Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock()


@pytest.fixture
def sample_validation_error():
    """Sample validation error for testing."""
    return ValidationError(
        message="Test validation error",
        field="test_field",
        value="test_value",
        details={'validation_rule': 'required'}
    )


@pytest.fixture
def sample_database_error():
    """Sample database error for testing."""
    return DatabaseError(
        message="Test database error",
        operation="test_operation",
        table="test_table",
        details={'query': 'SELECT * FROM test'}
    )


class MockResponse:
    """Mock HTTP response for testing external API calls."""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_requests():
    """Mock requests library for testing external API calls."""
    with patch('requests.post') as mock_post, \
         patch('requests.get') as mock_get, \
         patch('requests.put') as mock_put, \
         patch('requests.delete') as mock_delete:
        
        # Default successful responses
        mock_post.return_value = MockResponse({'success': True})
        mock_get.return_value = MockResponse({'data': 'test'})
        mock_put.return_value = MockResponse({'updated': True})
        mock_delete.return_value = MockResponse({'deleted': True})
        
        yield {
            'post': mock_post,
            'get': mock_get,
            'put': mock_put,
            'delete': mock_delete
        }


# Test utilities

def create_test_function(db, name='test_func', param_count=1, description='Test'):
    """Helper to create test function in database."""
    cursor = db.execute(
        'INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES (?, ?, ?)',
        (name, param_count, description)
    )
    db.commit()
    return cursor.lastrowid


def assert_error_response(response, expected_code, expected_error_type=None):
    """Helper to assert error response format."""
    assert response.status_code == expected_code
    data = response.get_json()
    assert 'error' in data
    assert 'message' in data
    
    if expected_error_type:
        assert data['error'] == expected_error_type


def assert_success_response(response, expected_code=200):
    """Helper to assert success response format."""
    assert response.status_code == expected_code
    data = response.get_json()
    if 'success' in data:
        assert data['success'] is True