"""
Tests for Configuration Manager
Implements Commandment 4: Complete Unit Tests Are Mandatory
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, mock_open
from config_manager import ConfigManager, ConfigurationError, ForgeConfig


class TestConfigManager:
    """Test configuration manager functionality."""
    
    def test_load_config_success(self):
        """Test successful configuration loading."""
        config_data = {
            'app': {
                'name': 'test-forge',
                'version': '1.0.0',
                'environment': 'test',
                'secret_key': 'test-secret',
                'runtime_id': 'test-id',
                'debug': 'true'
            },
            'server': {
                'host': 'localhost',
                'port': '5000',
                'read_timeout': '30',
                'write_timeout': '30'
            },
            'database': {
                'main': {'path': 'test.db', 'max_connections': '5'},
                'worker': {'path': 'worker.db'},
                'runtime': {'path': 'runtime.db'}
            },
            'praxis': {
                'url': 'http://localhost:8080',
                'api_key': 'test-key',
                'timeout': '30',
                'max_retries': '3'
            },
            'logging': {
                'level': 'INFO',
                'format': 'json',
                'output': 'stdout',
                'correlation_enabled': 'true'
            },
            'security': {
                'max_request_size': '1048576',
                'rate_limit_per_minute': '60',
                'jwt_secret': 'jwt-secret',
                'jwt_expiry_hours': '24'
            },
            'external_services': {
                'mysql': {
                    'enabled': 'false',
                    'host': 'localhost',
                    'port': '3306',
                    'database': '',
                    'username': '',
                    'password': ''
                },
                'oracle': {
                    'enabled': 'false',
                    'host': 'localhost',
                    'port': '1521',
                    'service_name': '',
                    'username': '',
                    'password': ''
                }
            }
        }
        
        yaml_content = yaml.dump(config_data)
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.exists', return_value=True):
                manager = ConfigManager('test_config.yaml')
                config = manager.load_config()
                
                assert isinstance(config, ForgeConfig)
                assert config.app.name == 'test-forge'
                assert config.app.debug is True
                assert config.server.port == 5000
                assert config.database.max_connections == 5
    
    def test_load_config_file_not_found(self):
        """Test configuration loading when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            manager = ConfigManager('nonexistent.yaml')
            
            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()
            
            assert "Configuration file not found" in str(exc_info.value)
    
    def test_load_config_invalid_yaml(self):
        """Test configuration loading with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["
        
        with patch('builtins.open', mock_open(read_data=invalid_yaml)):
            with patch('os.path.exists', return_value=True):
                manager = ConfigManager('test_config.yaml')
                
                with pytest.raises(ConfigurationError) as exc_info:
                    manager.load_config()
                
                assert "Invalid YAML configuration" in str(exc_info.value)
    
    def test_environment_variable_expansion(self):
        """Test environment variable expansion in configuration."""
        config_content = """
        app:
          name: "${APP_NAME:default-name}"
          port: "${PORT:5000}"
        """
        
        with patch.dict(os.environ, {'APP_NAME': 'test-app', 'PORT': '8080'}):
            with patch('builtins.open', mock_open(read_data=config_content)):
                with patch('os.path.exists', return_value=True):
                    manager = ConfigManager('test_config.yaml')
                    expanded = manager._expand_environment_variables(config_content)
                    
                    assert 'test-app' in expanded
                    assert '8080' in expanded
    
    def test_environment_variable_defaults(self):
        """Test environment variable defaults when not set."""
        config_content = """
        app:
          name: "${UNSET_VAR:default-value}"
        """
        
        with patch.dict(os.environ, {}, clear=True):
            manager = ConfigManager()
            expanded = manager._expand_environment_variables(config_content)
            
            assert 'default-value' in expanded
    
    def test_validation_missing_secret_key(self):
        """Test validation fails when secret key is missing."""
        config_data = {
            'app': {
                'name': 'test',
                'version': '1.0.0',
                'environment': 'test',
                'secret_key': '',  # Empty secret key
                'runtime_id': 'test',
                'debug': 'false'
            },
            'server': {'host': 'localhost', 'port': '5000', 'read_timeout': '30', 'write_timeout': '30'},
            'database': {
                'main': {'path': 'test.db', 'max_connections': '5'},
                'worker': {'path': 'worker.db'},
                'runtime': {'path': 'runtime.db'}
            },
            'praxis': {'url': 'http://localhost:8080', 'api_key': '', 'timeout': '30', 'max_retries': '3'},
            'logging': {'level': 'INFO', 'format': 'json', 'output': 'stdout', 'correlation_enabled': 'true'},
            'security': {'max_request_size': '1048576', 'rate_limit_per_minute': '60', 'jwt_secret': '', 'jwt_expiry_hours': '24'},
            'external_services': {
                'mysql': {'enabled': 'false', 'host': 'localhost', 'port': '3306', 'database': '', 'username': '', 'password': ''},
                'oracle': {'enabled': 'false', 'host': 'localhost', 'port': '1521', 'service_name': '', 'username': '', 'password': ''}
            }
        }
        
        yaml_content = yaml.dump(config_data)
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.exists', return_value=True):
                manager = ConfigManager('test_config.yaml')
                
                with pytest.raises(ConfigurationError) as exc_info:
                    manager.load_config()
                
                assert "Flask secret key is required" in str(exc_info.value)
    
    def test_validation_invalid_port(self):
        """Test validation fails for invalid port."""
        config_data = {
            'app': {
                'name': 'test',
                'version': '1.0.0',
                'environment': 'test',
                'secret_key': 'test-secret',
                'runtime_id': 'test',
                'debug': 'false'
            },
            'server': {'host': 'localhost', 'port': '70000', 'read_timeout': '30', 'write_timeout': '30'},  # Invalid port
            'database': {
                'main': {'path': 'test.db', 'max_connections': '5'},
                'worker': {'path': 'worker.db'},
                'runtime': {'path': 'runtime.db'}
            },
            'praxis': {'url': 'http://localhost:8080', 'api_key': '', 'timeout': '30', 'max_retries': '3'},
            'logging': {'level': 'INFO', 'format': 'json', 'output': 'stdout', 'correlation_enabled': 'true'},
            'security': {'max_request_size': '1048576', 'rate_limit_per_minute': '60', 'jwt_secret': '', 'jwt_expiry_hours': '24'},
            'external_services': {
                'mysql': {'enabled': 'false', 'host': 'localhost', 'port': '3306', 'database': '', 'username': '', 'password': ''},
                'oracle': {'enabled': 'false', 'host': 'localhost', 'port': '1521', 'service_name': '', 'username': '', 'password': ''}
            }
        }
        
        yaml_content = yaml.dump(config_data)
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.exists', return_value=True):
                manager = ConfigManager('test_config.yaml')
                
                with pytest.raises(ConfigurationError) as exc_info:
                    manager.load_config()
                
                assert "Invalid server port" in str(exc_info.value)
    
    def test_get_config_loads_if_not_loaded(self):
        """Test get_config loads configuration if not already loaded."""
        config_data = {
            'app': {'name': 'test', 'version': '1.0.0', 'environment': 'test', 'secret_key': 'test', 'runtime_id': 'test', 'debug': 'false'},
            'server': {'host': 'localhost', 'port': '5000', 'read_timeout': '30', 'write_timeout': '30'},
            'database': {'main': {'path': 'test.db', 'max_connections': '5'}, 'worker': {'path': 'worker.db'}, 'runtime': {'path': 'runtime.db'}},
            'praxis': {'url': 'http://localhost:8080', 'api_key': '', 'timeout': '30', 'max_retries': '3'},
            'logging': {'level': 'INFO', 'format': 'json', 'output': 'stdout', 'correlation_enabled': 'true'},
            'security': {'max_request_size': '1048576', 'rate_limit_per_minute': '60', 'jwt_secret': '', 'jwt_expiry_hours': '24'},
            'external_services': {'mysql': {'enabled': 'false', 'host': 'localhost', 'port': '3306', 'database': '', 'username': '', 'password': ''}, 'oracle': {'enabled': 'false', 'host': 'localhost', 'port': '1521', 'service_name': '', 'username': '', 'password': ''}}
        }
        
        yaml_content = yaml.dump(config_data)
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.exists', return_value=True):
                with patch('os.makedirs'):
                    manager = ConfigManager('test_config.yaml')
                    
                    # First call should load config
                    config1 = manager.get_config()
                    assert config1.app.name == 'test'
                    
                    # Second call should return cached config
                    config2 = manager.get_config()
                    assert config1 is config2
    
    def test_reload_config(self):
        """Test configuration reloading."""
        config_data = {
            'app': {'name': 'test', 'version': '1.0.0', 'environment': 'test', 'secret_key': 'test', 'runtime_id': 'test', 'debug': 'false'},
            'server': {'host': 'localhost', 'port': '5000', 'read_timeout': '30', 'write_timeout': '30'},
            'database': {'main': {'path': 'test.db', 'max_connections': '5'}, 'worker': {'path': 'worker.db'}, 'runtime': {'path': 'runtime.db'}},
            'praxis': {'url': 'http://localhost:8080', 'api_key': '', 'timeout': '30', 'max_retries': '3'},
            'logging': {'level': 'INFO', 'format': 'json', 'output': 'stdout', 'correlation_enabled': 'true'},
            'security': {'max_request_size': '1048576', 'rate_limit_per_minute': '60', 'jwt_secret': '', 'jwt_expiry_hours': '24'},
            'external_services': {'mysql': {'enabled': 'false', 'host': 'localhost', 'port': '3306', 'database': '', 'username': '', 'password': ''}, 'oracle': {'enabled': 'false', 'host': 'localhost', 'port': '1521', 'service_name': '', 'username': '', 'password': ''}}
        }
        
        yaml_content = yaml.dump(config_data)
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('os.path.exists', return_value=True):
                with patch('os.makedirs'):
                    manager = ConfigManager('test_config.yaml')
                    
                    # Load initial config
                    config1 = manager.get_config()
                    
                    # Reload should create new instance
                    config2 = manager.reload_config()
                    
                    assert config1 is not config2
                    assert config2.app.name == 'test'
    
    def test_to_bool_conversion(self):
        """Test boolean conversion utility."""
        manager = ConfigManager()
        
        # Test true values
        assert manager._to_bool('true') is True
        assert manager._to_bool('True') is True
        assert manager._to_bool('1') is True
        assert manager._to_bool('yes') is True
        assert manager._to_bool('on') is True
        
        # Test false values
        assert manager._to_bool('false') is False
        assert manager._to_bool('False') is False
        assert manager._to_bool('0') is False
        assert manager._to_bool('no') is False
        assert manager._to_bool('off') is False
        assert manager._to_bool('anything_else') is False