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

def generate_connection_handle(db_type, config_id, env_name):
    """Generate a unique connection handle for a configuration"""
    if config_id and config_id != 'temp':
        # Use actual config ID for saved configurations
        clean_name = env_name.lower().replace(' ', '_').replace('-', '_')[:20]
        return f"{db_type.lower()}_config_{config_id}_{clean_name}"
    else:
        # For unsaved configurations, create a unique hash based on connection details
        unique_string = f"{db_type}_{env_name}_{datetime.now().timestamp()}"
        hash_suffix = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        clean_name = env_name.lower().replace(' ', '_').replace('-', '_')[:15]
        return f"{db_type.lower()}_temp_{clean_name}_{hash_suffix}"

# Environment Configuration Management
@env_config_bp.route('/')
def env_config_page():
    return render_template('env_config.html', active_page='env_config')

@env_config_bp.route('/get_env_configs')
def get_env_configs():
    try:
        configs = query_db('SELECT * FROM GEE_ENV_CONFIG')
        result = [dict(config) for config in configs]
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_env_configs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@env_config_bp.route('/add_env_config', methods=['POST'])
def add_env_config():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_ENV_CONFIG (ENV_NAME, DB_NAME, DB_USERNAME, DB_HOST, DB_PASSWORD, DB_INSTANCE, DB_TYPE, DB_PORT, LINUX_USER, LINUX_PASSWORD, LINUX_HOST) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (data['envName'], data['dbName'], data.get('dbUsername'), data.get('dbHost'), data['dbPassword'], 
             data['dbInstance'], data['dbType'], data['dbPort'], data['linuxUser'], data['linuxPassword'], data['linuxHost'])
        )
        return jsonify({'success': True, 'message': 'Environment configuration added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/update_env_config', methods=['PUT'])
def update_env_config():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_ENV_CONFIG SET ENV_NAME = ?, DB_NAME = ?, DB_USERNAME = ?, DB_HOST = ?, DB_PASSWORD = ?, DB_INSTANCE = ?, DB_TYPE = ?, DB_PORT = ?, LINUX_USER = ?, LINUX_PASSWORD = ?, LINUX_HOST = ? WHERE GT_ID = ?',
            (data['envName'], data['dbName'], data.get('dbUsername'), data.get('dbHost'), data['dbPassword'], 
             data['dbInstance'], data['dbType'], data['dbPort'], data['linuxUser'], data['linuxPassword'], data['linuxHost'], data['gtId'])
        )
        return jsonify({'success': True, 'message': 'Environment configuration updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/delete_env_config/<int:gt_id>', methods=['DELETE'])
def delete_env_config(gt_id):
    try:
        modify_db('DELETE FROM GEE_ENV_CONFIG WHERE GT_ID = ?', (gt_id,))
        return jsonify({'success': True, 'message': 'Environment configuration deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/test_connection', methods=['POST'])
def test_connection():
    import time
    import os
    data = request.json
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
                
                handle = generate_connection_handle('SQLite', data.get('gtId'), data['envName'])
                return jsonify({
                    'success': True,
                    'message': f'SQLite connection successful! Version: {version}, Path: {db_path}',
                    'handle': handle
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
                
                handle = generate_connection_handle('Oracle', data.get('gtId'), data['envName'])
                return jsonify({
                    'success': True,
                    'message': f'Oracle connection successful! Server date: {server_date}, Version: {version[:50]}...',
                    'handle': handle
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
                
                handle = generate_connection_handle('Postgres', data.get('gtId'), data['envName'])
                return jsonify({
                    'success': True,
                    'message': f'PostgreSQL connection successful! Version: {version[:100]}...',
                    'handle': handle
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
                
                handle = generate_connection_handle('MySQL', data.get('gtId'), data['envName'])
                return jsonify({
                    'success': True,
                    'message': f'MySQL connection successful! Version: {version}, Database: {current_db}',
                    'handle': handle
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

@env_config_bp.route('/store_connection', methods=['POST'])
def store_connection():
    data = request.json
    handle = data.get('handle')
    config_id = data.get('configId')
    app_runtime_id = data.get('app_runtime_id')    
    #pdb.set_trace()
    
    if not handle or not config_id or not app_runtime_id:
        return jsonify({
            'success': False,
            'message': 'Handle, configuration ID, and app runtime ID are required'
        })
    
    try:
        # First, check if this handle already exists for this app runtime
        existing = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ? AND APP_RUNTIME_ID = ?', 
                           (handle, app_runtime_id), one=True)
        
        if existing:
            # Update existing connection
            modify_db(
                'UPDATE GEE_ACTIVE_CONNECTIONS SET CONFIG_ID = ?, STATUS = ?, CREATED = ? WHERE HANDLE = ? AND APP_RUNTIME_ID = ?',
                (config_id, 'active', datetime.now(), handle, app_runtime_id)
            )
        else:
            # Insert new connection with APP_RUNTIME_ID
            modify_db(
                'INSERT INTO GEE_ACTIVE_CONNECTIONS (HANDLE, CONFIG_ID, CREATED, STATUS, APP_RUNTIME_ID) VALUES (?, ?, ?, ?, ?)',
                (handle, config_id, datetime.now(), 'active', app_runtime_id)
            )
        
        # Update the in-memory dictionary for fast access
        active_connections[handle] = {
            'config_id': config_id,
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
            # Get environment name for each connection
            config = query_db('SELECT ENV_NAME, DB_TYPE FROM GEE_ENV_CONFIG WHERE GT_ID = ?',
                            (conn['CONFIG_ID'],), one=True)

            connections[conn['HANDLE']] = {
                'config_id': conn['CONFIG_ID'],
                'created': conn['CREATED'],
                'status': conn['STATUS'],
                'env_name': config['ENV_NAME'] if config else 'Unknown',
                'db_type': config['DB_TYPE'] if config else 'Unknown',
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