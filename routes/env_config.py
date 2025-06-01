from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import uuid
import sqlite3
import hashlib
from db_helpers import query_db, modify_db
from oracle_helpers import get_oracle_connection
from mysql_helpers import get_mysql_connection

# Create a Blueprint for environment configuration routes
env_config_bp = Blueprint('env_config', __name__)

# Dictionary to store active connections in memory
active_connections = {}

def generate_connection_handle(db_type, db_config_id, env_name, db_display_name):
    """Generate a unique connection handle for a database configuration"""
    if db_config_id and db_config_id != 'temp':
        # Use actual database config ID for saved configurations
        clean_env = env_name.lower().replace(' ', '_').replace('-', '_')[:15]
        clean_db = db_display_name.lower().replace(' ', '_').replace('-', '_')[:15]
        return f"{db_type.lower()}_db_{db_config_id}_{clean_env}_{clean_db}"
    else:
        # For unsaved configurations, create a unique hash based on connection details
        unique_string = f"{db_type}_{env_name}_{db_display_name}_{datetime.now().timestamp()}"
        hash_suffix = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        clean_env = env_name.lower().replace(' ', '_').replace('-', '_')[:10]
        clean_db = db_display_name.lower().replace(' ', '_').replace('-', '_')[:10]
        return f"{db_type.lower()}_temp_{clean_env}_{clean_db}_{hash_suffix}"

def update_last_tested(db_config_id):
    """Update the LAST_TESTED timestamp for a database configuration"""
    if db_config_id and db_config_id != 'temp':
        try:
            modify_db('UPDATE GEE_DATABASE_CONFIGS SET LAST_TESTED = ? WHERE DB_CONFIG_ID = ?', 
                     (datetime.now(), db_config_id))
        except Exception as e:
            print(f"Error updating last tested time: {str(e)}")

def auto_store_connection_for_saved_config(handle, db_config_id, app_runtime_id):
    """Automatically store connection for saved database configurations"""
    if db_config_id and db_config_id != 'temp':
        try:
            # Check if this exact handle already exists (globally)
            existing = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?', 
                               (handle,), one=True)
            
            actual_handle = handle  # Track the actual handle used
            
            if existing:
                # If it's the same app runtime, update it
                if existing['APP_RUNTIME_ID'] == app_runtime_id:
                    modify_db(
                        'UPDATE GEE_ACTIVE_CONNECTIONS SET DB_CONFIG_ID = ?, CONFIG_ID = ?, STATUS = ?, CREATED = ? WHERE HANDLE = ?',
                        (db_config_id, db_config_id, 'active', datetime.now(), handle)  # Keep CONFIG_ID for backward compatibility
                    )
                else:
                    # If different app runtime, create a unique handle by appending app runtime suffix
                    unique_handle = f"{handle}_{app_runtime_id[:8]}"
                    actual_handle = unique_handle
                    
                    # Check if this unique handle exists
                    existing_unique = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?', 
                                             (unique_handle,), one=True)
                    if existing_unique:
                        # Update the existing unique handle
                        modify_db(
                            'UPDATE GEE_ACTIVE_CONNECTIONS SET DB_CONFIG_ID = ?, CONFIG_ID = ?, STATUS = ?, CREATED = ? WHERE HANDLE = ?',
                            (db_config_id, db_config_id, 'active', datetime.now(), unique_handle)
                        )
                    else:
                        # Insert with unique handle
                        modify_db(
                            'INSERT INTO GEE_ACTIVE_CONNECTIONS (HANDLE, DB_CONFIG_ID, CONFIG_ID, CREATED, STATUS, APP_RUNTIME_ID) VALUES (?, ?, ?, ?, ?, ?)',
                            (unique_handle, db_config_id, db_config_id, datetime.now(), 'active', app_runtime_id)
                        )
            else:
                # Handle doesn't exist, insert new connection
                modify_db(
                    'INSERT INTO GEE_ACTIVE_CONNECTIONS (HANDLE, DB_CONFIG_ID, CONFIG_ID, CREATED, STATUS, APP_RUNTIME_ID) VALUES (?, ?, ?, ?, ?, ?)',
                    (handle, db_config_id, db_config_id, datetime.now(), 'active', app_runtime_id)
                )
            return (True, actual_handle)
        except Exception as e:
            print(f"Error auto-storing connection: {str(e)}")
            return (False, handle)
    return (False, handle)

def test_connection_internal(data):
    """Internal function to test database connections"""
    import time
    import os
    
    db_type = data.get('dbType')
    start_time = time.time()
    TIMEOUT_SECONDS = 30

    try:
        # Validate required fields based on database type
        if db_type == 'SQLite':
            required_fields = ['dbName']
        elif db_type in ['Oracle', 'Postgres', 'MySQL']:
            required_fields = ['dbName', 'dbUsername', 'dbHost', 'dbPort']
        else:
            return jsonify({'success': False, 'message': f'Unsupported database type: {db_type}'})
        
        # Check for missing required fields
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'success': False, 
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            })

        # Test connection based on database type
        if db_type == 'SQLite':
            # Enhanced SQLite validation
            try:
                import sqlite3
                db_path = data['dbName']
                
                # Validate file path
                if not db_path:
                    return jsonify({
                        'success': False,
                        'message': 'Database file path is required for SQLite'
                    })
                
                # Check if path is absolute or make it relative to app
                if not os.path.isabs(db_path):
                    db_path = os.path.join(os.getcwd(), db_path)
                
                # Check if directory exists
                db_dir = os.path.dirname(db_path)
                if not os.path.exists(db_dir):
                    return jsonify({
                        'success': False,
                        'message': f'Directory does not exist: {db_dir}'
                    })
                
                # Test SQLite connection with timeout
                conn = sqlite3.connect(db_path, timeout=30)
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version();")
                version = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                
                # Generate handle based on whether this is a saved config or temp
                env_name = data.get('envName', 'Unknown')
                db_display_name = data.get('dbDisplayName', data.get('dbName', 'Unknown'))
                db_config_id = data.get('dbConfigId', data.get('gtId'))
                
                handle = generate_connection_handle('SQLite', db_config_id, env_name, db_display_name)
                
                # Update last tested time and auto-store for saved configs
                update_last_tested(db_config_id)
                
                # Get app_runtime_id from the request session or generate one
                app_runtime_id = request.args.get('app_runtime_id') or data.get('app_runtime_id', 'default')
                auto_stored, actual_handle = auto_store_connection_for_saved_config(handle, db_config_id, app_runtime_id)
                
                message = f'SQLite connection successful! Version: {version}, Path: {db_path}'
                if auto_stored:
                    message += ' (Connection stored automatically)'
                
                return jsonify({
                    'success': True,
                    'message': message,
                    'handle': actual_handle,
                    'auto_stored': auto_stored
                })
                
            except sqlite3.OperationalError as e:
                return jsonify({
                    'success': False,
                    'message': f'SQLite connection failed: {str(e)}'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'SQLite error: {str(e)}'
                })
        
        elif db_type == 'Oracle':
            # Enhanced Oracle connection with better error handling
            try:
                username = data['dbUsername']
                password = data.get('dbPassword', '')
                host = data['dbHost']
                port = data['dbPort']
                oracle_conn_type = data.get('oracleConnType', 'service')
                instance_value = data.get('dbInstance', data['dbName'])
                
                # Determine if we're using SID or Service Name
                if oracle_conn_type == 'sid':
                    # Use SID connection
                    oracle_conn, error = get_oracle_connection(
                        username=username,
                        password=password,
                        host=host,
                        port=port,
                        service_name=None,
                        sid=instance_value
                    )
                else:
                    # Use Service Name connection (default)
                    oracle_conn, error = get_oracle_connection(
                        username=username,
                        password=password,
                        host=host,
                        port=port,
                        service_name=instance_value,
                        sid=None
                    )
                
                if error:
                    return jsonify({
                        'success': False,
                        'message': f'Oracle connection error: {error}'
                    })
                
                # Test a simple query - Get Oracle server date and version
                cursor = oracle_conn.cursor()
                cursor.execute("SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') AS SERVER_DATE, BANNER FROM V$VERSION WHERE ROWNUM = 1")
                result = cursor.fetchone()
                server_date = result[0] if result else "Unknown"
                version = result[1] if len(result) > 1 else "Unknown Version"
                cursor.close()
                oracle_conn.close()
                
                # Generate handle based on whether this is a saved config or temp
                env_name = data.get('envName', 'Unknown')
                db_display_name = data.get('dbDisplayName', data.get('dbName', 'Unknown'))
                db_config_id = data.get('dbConfigId', data.get('gtId'))
                
                handle = generate_connection_handle('Oracle', db_config_id, env_name, db_display_name)
                
                # Update last tested time and auto-store for saved configs
                update_last_tested(db_config_id)
                
                app_runtime_id = request.args.get('app_runtime_id') or data.get('app_runtime_id', 'default')
                auto_stored, actual_handle = auto_store_connection_for_saved_config(handle, db_config_id, app_runtime_id)
                
                message = f'Oracle connection successful! Server date: {server_date}, Version: {version[:50]}...'
                if auto_stored:
                    message += ' (Connection stored automatically)'
                
                return jsonify({
                    'success': True,
                    'message': message,
                    'handle': actual_handle,
                    'auto_stored': auto_stored
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Oracle connection failed: {str(e)}'
                })

        elif db_type == 'Postgres':
            # Real PostgreSQL connection testing
            try:
                try:
                    import psycopg2
                    from psycopg2 import OperationalError
                except ImportError:
                    return jsonify({
                        'success': False,
                        'message': 'psycopg2 library not installed. Please install psycopg2-binary.'
                    })
                
                username = data['dbUsername']
                password = data.get('dbPassword', '')
                host = data['dbHost']
                port = data['dbPort']
                database = data['dbName']
                
                # Validate required parameters
                if not all([username, host, port, database]):
                    return jsonify({
                        'success': False,
                        'message': 'Missing required fields: username, host, port, database'
                    })
                
                # Test PostgreSQL connection with timeout
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=30
                )
                
                # Test with a simple query
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                
                # Generate handle based on whether this is a saved config or temp
                env_name = data.get('envName', 'Unknown')
                db_display_name = data.get('dbDisplayName', data.get('dbName', 'Unknown'))
                db_config_id = data.get('dbConfigId', data.get('gtId'))
                
                handle = generate_connection_handle('Postgres', db_config_id, env_name, db_display_name)
                
                # Update last tested time and auto-store for saved configs
                update_last_tested(db_config_id)
                
                app_runtime_id = request.args.get('app_runtime_id') or data.get('app_runtime_id', 'default')
                auto_stored, actual_handle = auto_store_connection_for_saved_config(handle, db_config_id, app_runtime_id)
                
                message = f'PostgreSQL connection successful! Version: {version[:100]}...'
                if auto_stored:
                    message += ' (Connection stored automatically)'
                
                return jsonify({
                    'success': True,
                    'message': message,
                    'handle': actual_handle,
                    'auto_stored': auto_stored
                })
                
            except OperationalError as e:
                return jsonify({
                    'success': False,
                    'message': f'PostgreSQL connection failed: {str(e)}'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'PostgreSQL connection error: {str(e)}'
                })

        elif db_type == 'MySQL':
            # Enhanced MySQL connection with better error handling
            try:
                username = data['dbUsername']
                password = data.get('dbPassword', '')
                host = data['dbHost']
                port = data['dbPort']
                database = data['dbName']
                
                # Test MySQL connection
                mysql_conn, error = get_mysql_connection(
                    username=username,
                    password=password,
                    host=host,
                    port=port,
                    database=database
                )
                
                if error:
                    return jsonify({
                        'success': False,
                        'message': f'MySQL connection error: {error}'
                    })
                
                # Test a simple query - Get MySQL server version and current database
                cursor = mysql_conn.cursor()
                cursor.execute("SELECT VERSION(), DATABASE();")
                result = cursor.fetchone()
                version = result[0] if result else "Unknown"
                current_db = result[1] if len(result) > 1 else "Unknown"
                cursor.close()
                mysql_conn.close()
                
                # Generate handle based on whether this is a saved config or temp
                env_name = data.get('envName', 'Unknown')
                db_display_name = data.get('dbDisplayName', data.get('dbName', 'Unknown'))
                db_config_id = data.get('dbConfigId', data.get('gtId'))
                
                handle = generate_connection_handle('MySQL', db_config_id, env_name, db_display_name)
                
                # Update last tested time and auto-store for saved configs
                update_last_tested(db_config_id)
                
                app_runtime_id = request.args.get('app_runtime_id') or data.get('app_runtime_id', 'default')
                auto_stored, actual_handle = auto_store_connection_for_saved_config(handle, db_config_id, app_runtime_id)
                
                message = f'MySQL connection successful! Version: {version}, Database: {current_db}'
                if auto_stored:
                    message += ' (Connection stored automatically)'
                
                return jsonify({
                    'success': True,
                    'message': message,
                    'handle': actual_handle,
                    'auto_stored': auto_stored
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'MySQL connection failed: {str(e)}'
                })

        else:
            return jsonify({
                'success': False,
                'message': f'Unsupported database type: {db_type}'
            })
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT_SECONDS:
            return jsonify({
                'success': False,
                'message': 'Connection timed out after 30 seconds'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Connection failed: {str(e)}'
            })

# Environment Configuration Management
@env_config_bp.route('/')
def env_config_page():
    return render_template('env_config_redesigned.html', active_page='env_config')

@env_config_bp.route('/get_env_configs')
def get_env_configs():
    try:
        # Get environments with their database configurations in nested format
        environments = query_db('SELECT * FROM GEE_ENVIRONMENTS ORDER BY ENV_NAME')
        result = []
        
        for env in environments:
            env_dict = dict(env)
            # Get all database configs for this environment
            db_configs = query_db(
                'SELECT * FROM GEE_DATABASE_CONFIGS WHERE ENV_ID = ? ORDER BY IS_PRIMARY DESC, DB_DISPLAY_NAME',
                (env['ENV_ID'],)
            )
            env_dict['databases'] = [dict(db) for db in db_configs]
            result.append(env_dict)
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_env_configs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@env_config_bp.route('/add_environment', methods=['POST'])
def add_environment():
    """Add a new environment (without database configs)"""
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_ENVIRONMENTS (ENV_NAME, ENV_TYPE, DESCRIPTION) VALUES (?, ?, ?)',
            (data['envName'], data.get('envType', 'DEV'), data.get('description', ''))
        )
        return jsonify({'success': True, 'message': 'Environment added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/add_database_config', methods=['POST'])
def add_database_config():
    """Add a database configuration to an existing environment"""
    data = request.json
    try:
        # If adding to new environment, check if primary database
        is_primary = data.get('isPrimary', False)
        env_id = data['envId']
        
        # Check if this is the first database for the environment
        existing_dbs = query_db('SELECT COUNT(*) as count FROM GEE_DATABASE_CONFIGS WHERE ENV_ID = ?', (env_id,), one=True)
        if existing_dbs['count'] == 0:
            is_primary = True  # First database is automatically primary
        elif is_primary:
            # If setting as primary, unset other primary flags
            modify_db('UPDATE GEE_DATABASE_CONFIGS SET IS_PRIMARY = 0 WHERE ENV_ID = ?', (env_id,))
        
        modify_db(
            '''INSERT INTO GEE_DATABASE_CONFIGS 
               (ENV_ID, DB_NAME, DB_DISPLAY_NAME, DB_TYPE, DB_HOST, DB_PORT, DB_USERNAME, 
                DB_PASSWORD, DB_INSTANCE, ORACLE_CONN_TYPE, LINUX_USER, LINUX_PASSWORD, 
                LINUX_HOST, IS_PRIMARY, STATUS) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (env_id, data['dbName'], data['dbDisplayName'], data['dbType'], 
             data.get('dbHost'), data.get('dbPort'), data.get('dbUsername'),
             data.get('dbPassword'), data.get('dbInstance'), data.get('oracleConnType', 'service'),
             data.get('linuxUser'), data.get('linuxPassword'), data.get('linuxHost'),
             is_primary, data.get('status', 'active'))
        )
        return jsonify({'success': True, 'message': 'Database configuration added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/update_environment', methods=['PUT'])
def update_environment():
    """Update environment details"""
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_ENVIRONMENTS SET ENV_NAME = ?, ENV_TYPE = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE ENV_ID = ?',
            (data['envName'], data.get('envType'), data.get('description'), datetime.now(), data['envId'])
        )
        return jsonify({'success': True, 'message': 'Environment updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/update_database_config', methods=['PUT'])
def update_database_config():
    """Update database configuration"""
    data = request.json
    try:
        db_config_id = data['dbConfigId']
        env_id = data['envId']
        is_primary = data.get('isPrimary', False)
        
        # If setting as primary, unset other primary flags in the same environment
        if is_primary:
            modify_db('UPDATE GEE_DATABASE_CONFIGS SET IS_PRIMARY = 0 WHERE ENV_ID = ? AND DB_CONFIG_ID != ?', 
                     (env_id, db_config_id))
        
        modify_db(
            '''UPDATE GEE_DATABASE_CONFIGS SET 
               DB_NAME = ?, DB_DISPLAY_NAME = ?, DB_TYPE = ?, DB_HOST = ?, DB_PORT = ?, 
               DB_USERNAME = ?, DB_PASSWORD = ?, DB_INSTANCE = ?, ORACLE_CONN_TYPE = ?, 
               LINUX_USER = ?, LINUX_PASSWORD = ?, LINUX_HOST = ?, IS_PRIMARY = ?, 
               STATUS = ?, UPDATE_DATE = ?
               WHERE DB_CONFIG_ID = ?''',
            (data['dbName'], data['dbDisplayName'], data['dbType'], data.get('dbHost'), 
             data.get('dbPort'), data.get('dbUsername'), data.get('dbPassword'), 
             data.get('dbInstance'), data.get('oracleConnType', 'service'), data.get('linuxUser'), 
             data.get('linuxPassword'), data.get('linuxHost'), is_primary, 
             data.get('status', 'active'), datetime.now(), db_config_id)
        )
        return jsonify({'success': True, 'message': 'Database configuration updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/delete_environment/<int:env_id>', methods=['DELETE'])
def delete_environment(env_id):
    """Delete an entire environment and all its database configurations"""
    try:
        # Delete database configurations first (cascade should handle this, but be explicit)
        modify_db('DELETE FROM GEE_DATABASE_CONFIGS WHERE ENV_ID = ?', (env_id,))
        # Delete the environment
        modify_db('DELETE FROM GEE_ENVIRONMENTS WHERE ENV_ID = ?', (env_id,))
        return jsonify({'success': True, 'message': 'Environment and all its database configurations deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/delete_database_config/<int:db_config_id>', methods=['DELETE'])
def delete_database_config(db_config_id):
    """Delete a specific database configuration"""
    try:
        # Get environment info before deletion to check if this was the primary
        db_config = query_db('SELECT ENV_ID, IS_PRIMARY FROM GEE_DATABASE_CONFIGS WHERE DB_CONFIG_ID = ?', 
                            (db_config_id,), one=True)
        
        if not db_config:
            return jsonify({'success': False, 'message': 'Database configuration not found'})
        
        # Delete the database configuration
        modify_db('DELETE FROM GEE_DATABASE_CONFIGS WHERE DB_CONFIG_ID = ?', (db_config_id,))
        
        # If this was the primary database, make another one primary if any exist
        if db_config['IS_PRIMARY']:
            remaining_db = query_db('SELECT DB_CONFIG_ID FROM GEE_DATABASE_CONFIGS WHERE ENV_ID = ? LIMIT 1', 
                                   (db_config['ENV_ID'],), one=True)
            if remaining_db:
                modify_db('UPDATE GEE_DATABASE_CONFIGS SET IS_PRIMARY = 1 WHERE DB_CONFIG_ID = ?', 
                         (remaining_db['DB_CONFIG_ID'],))
        
        return jsonify({'success': True, 'message': 'Database configuration deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/test_database_connection', methods=['POST'])
def test_database_connection():
    """Test connection for a specific database configuration"""
    import time
    import os
    data = request.json
    db_config_id = data.get('dbConfigId')
    
    if not db_config_id:
        return jsonify({'success': False, 'message': 'Database configuration ID is required'})
    
    try:
        # Get the database configuration
        db_config = query_db('SELECT dc.*, e.ENV_NAME FROM GEE_DATABASE_CONFIGS dc JOIN GEE_ENVIRONMENTS e ON e.ENV_ID = dc.ENV_ID WHERE dc.DB_CONFIG_ID = ?', 
                            (db_config_id,), one=True)
        
        if not db_config:
            return jsonify({'success': False, 'message': 'Database configuration not found'})
        
        # Extract connection details
        db_type = db_config['DB_TYPE']
        env_name = db_config['ENV_NAME']
        db_display_name = db_config['DB_DISPLAY_NAME']
        
        # Convert to format expected by existing test logic
        test_data = {
            'dbType': db_type,
            'envName': env_name,
            'dbDisplayName': db_display_name,
            'dbName': db_config['DB_NAME'],
            'dbUsername': db_config['DB_USERNAME'],
            'dbHost': db_config['DB_HOST'],
            'dbPort': db_config['DB_PORT'],
            'dbPassword': db_config['DB_PASSWORD'],
            'dbInstance': db_config['DB_INSTANCE'],
            'oracleConnType': db_config['ORACLE_CONN_TYPE'],
            'linuxUser': db_config['LINUX_USER'],
            'linuxPassword': db_config['LINUX_PASSWORD'],
            'linuxHost': db_config['LINUX_HOST'],
            'dbConfigId': db_config_id,
            'app_runtime_id': data.get('app_runtime_id', 'default')
        }
        
        # Use existing test connection logic (adapted)
        return test_connection_internal(test_data)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error testing connection: {str(e)}'})

@env_config_bp.route('/test_connection', methods=['POST'])
def test_connection():
    """Test connection for legacy format (direct form data)"""
    data = request.json
    
    # Add default display name for legacy calls
    if 'dbDisplayName' not in data:
        data['dbDisplayName'] = f"{data.get('dbType', 'Unknown')} Database"
    
    return test_connection_internal(data)

@env_config_bp.route('/store_connection', methods=['POST'])
def store_connection():
    data = request.json
    handle = data.get('handle')
    config_id = data.get('configId')  # Legacy compatibility
    db_config_id = data.get('dbConfigId')  # New database config ID
    app_runtime_id = data.get('app_runtime_id')    
    
    # Use db_config_id if provided, otherwise fall back to legacy config_id
    effective_config_id = db_config_id or config_id
    
    if not handle or not effective_config_id or not app_runtime_id:
        return jsonify({
            'success': False,
            'message': 'Handle, configuration ID, and app runtime ID are required'
        })
    
    try:
        # Check if this exact handle already exists (globally)
        existing = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?', 
                           (handle,), one=True)
        
        if existing:
            # If it's the same app runtime, update it
            if existing['APP_RUNTIME_ID'] == app_runtime_id:
                modify_db(
                    'UPDATE GEE_ACTIVE_CONNECTIONS SET CONFIG_ID = ?, DB_CONFIG_ID = ?, STATUS = ?, CREATED = ? WHERE HANDLE = ?',
                    (config_id or effective_config_id, db_config_id, 'active', datetime.now(), handle)
                )
            else:
                # If different app runtime, create a unique handle by appending app runtime suffix
                unique_handle = f"{handle}_{app_runtime_id[:8]}"
                handle = unique_handle  # Update the handle variable for response
                
                # Check if this unique handle exists
                existing_unique = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?', 
                                         (unique_handle,), one=True)
                if existing_unique:
                    # Update the existing unique handle
                    modify_db(
                        'UPDATE GEE_ACTIVE_CONNECTIONS SET CONFIG_ID = ?, DB_CONFIG_ID = ?, STATUS = ?, CREATED = ? WHERE HANDLE = ?',
                        (config_id or effective_config_id, db_config_id, 'active', datetime.now(), unique_handle)
                    )
                else:
                    # Insert with unique handle
                    modify_db(
                        'INSERT INTO GEE_ACTIVE_CONNECTIONS (HANDLE, CONFIG_ID, DB_CONFIG_ID, CREATED, STATUS, APP_RUNTIME_ID) VALUES (?, ?, ?, ?, ?, ?)',
                        (unique_handle, config_id or effective_config_id, db_config_id, datetime.now(), 'active', app_runtime_id)
                    )
        else:
            # Handle doesn't exist, insert new connection
            modify_db(
                'INSERT INTO GEE_ACTIVE_CONNECTIONS (HANDLE, CONFIG_ID, DB_CONFIG_ID, CREATED, STATUS, APP_RUNTIME_ID) VALUES (?, ?, ?, ?, ?, ?)',
                (handle, config_id or effective_config_id, db_config_id, datetime.now(), 'active', app_runtime_id)
            )
        
        # Update the in-memory dictionary for fast access
        active_connections[handle] = {
            'config_id': config_id or effective_config_id,
            'db_config_id': db_config_id,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'active',
            'app_runtime_id': app_runtime_id
        }
        
        return jsonify({
            'success': True,
            'message': f'Connection handle {handle} stored successfully',
            'app_runtime_id': app_runtime_id
        })
        
    except Exception as e:
        print(f"Error storing connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error storing connection: {str(e)}'
        })

@env_config_bp.route('/get_active_connections')
def get_active_connections():
    app_runtime_id = request.args.get('app_runtime_id')
    if not app_runtime_id:
        return jsonify({
            'success': False,
            'message': 'App runtime ID is required'
        })
    
    try:
        connections = {}
        # Only get connections created by this app instance
        active_conns = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE APP_RUNTIME_ID = ?', 
                              (app_runtime_id,))

        for conn in active_conns:
            # Get environment and database config names for each connection
            if conn['DB_CONFIG_ID']:
                # New format: use DB_CONFIG_ID
                config = query_db('''SELECT e.ENV_NAME, dc.DB_TYPE, dc.DB_DISPLAY_NAME 
                                     FROM GEE_DATABASE_CONFIGS dc 
                                     JOIN GEE_ENVIRONMENTS e ON e.ENV_ID = dc.ENV_ID 
                                     WHERE dc.DB_CONFIG_ID = ?''',
                                (conn['DB_CONFIG_ID'],), one=True)
                if config:
                    env_name = config['ENV_NAME']
                    db_type = config['DB_TYPE']
                    db_display_name = config['DB_DISPLAY_NAME']
                else:
                    # DB_CONFIG_ID exists but config not found (might be deleted)
                    env_name = 'Unknown Environment (Deleted)'
                    db_type = 'Unknown'
                    db_display_name = 'Unknown Database (Deleted)'
            else:
                # Legacy format: use CONFIG_ID (for backward compatibility)
                config = query_db('SELECT ENV_NAME, DB_TYPE FROM GEE_ENV_CONFIG WHERE GT_ID = ?',
                                (conn['CONFIG_ID'],), one=True)
                if config:
                    env_name = config['ENV_NAME']
                    db_type = config['DB_TYPE']
                    db_display_name = f"{db_type} Database (Legacy)"
                else:
                    # CONFIG_ID exists but config not found (might be deleted)
                    env_name = 'Unknown Environment (Legacy)'
                    db_type = 'Unknown'
                    db_display_name = 'Unknown Database (Legacy)'

            connections[conn['HANDLE']] = {
                'config_id': conn['CONFIG_ID'],
                'db_config_id': conn['DB_CONFIG_ID'],
                'created': conn['CREATED'],
                'status': conn['STATUS'],
                'env_name': env_name,
                'db_type': db_type,
                'db_display_name': db_display_name,
                'app_runtime_id': app_runtime_id
            }

        return jsonify(connections)
    except Exception as e:
        print(f"Error getting active connections: {str(e)}")
        # Fall back to the in-memory connections if there's an error
        return jsonify(active_connections)
        
# Add a cleanup route to close connections
@env_config_bp.route('/cleanup_connections')
def cleanup_connections():
    app_runtime_id = request.args.get('app_runtime_id')
    if not app_runtime_id:
        return jsonify({
            'success': False,
            'message': 'App runtime ID is required'
        })
        
    try:
        # Clean up old connections that belong to this app instance
        modify_db('DELETE FROM GEE_ACTIVE_CONNECTIONS WHERE APP_RUNTIME_ID = ?', (app_runtime_id,))
        active_connections.clear()
        return jsonify({
            'success': True,
            'message': f'Successfully cleaned up connections for app instance {app_runtime_id}'
        })
    except Exception as e:
        print(f"Error cleaning up connections: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error cleaning up connections: {str(e)}'
        })