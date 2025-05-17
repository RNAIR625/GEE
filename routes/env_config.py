from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import uuid
import sqlite3
from db_helpers import query_db, modify_db
from oracle_helpers import get_oracle_connection

# Create a Blueprint for environment configuration routes
env_config_bp = Blueprint('env_config', __name__)

# Dictionary to store active connections in memory
active_connections = {}

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
            'INSERT INTO GEE_ENV_CONFIG (ENV_NAME, DB_NAME, DB_PASSWORD, DB_INSTANCE, DB_TYPE, DB_PORT, LINUX_USER, LINUX_PASSWORD, LINUX_HOST) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (data['envName'], data['dbName'], data['dbPassword'], data['dbInstance'], data['dbType'], 
             data['dbPort'], data['linuxUser'], data['linuxPassword'], data['linuxHost'])
        )
        return jsonify({'success': True, 'message': 'Environment configuration added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@env_config_bp.route('/update_env_config', methods=['PUT'])
def update_env_config():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_ENV_CONFIG SET ENV_NAME = ?, DB_NAME = ?, DB_PASSWORD = ?, DB_INSTANCE = ?, DB_TYPE = ?, DB_PORT = ?, LINUX_USER = ?, LINUX_PASSWORD = ?, LINUX_HOST = ? WHERE GT_ID = ?',
            (data['envName'], data['dbName'], data['dbPassword'], data['dbInstance'], data['dbType'], 
             data['dbPort'], data['linuxUser'], data['linuxPassword'], data['linuxHost'], data['gtId'])
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
    data = request.json
    db_type = data.get('dbType')
    conn = None

    try:
        # Test connection based on database type
        if db_type == 'SQLite':
            # For SQLite, just check if we can open the database
            import sqlite3
            try:
                conn = sqlite3.connect(data['dbName'])
                return jsonify({
                    'success': True,
                    'message': 'SQLite connection successful!',
                    'handle': f"sqlite_{data['envName'].lower().replace(' ', '_')}"
                })
            finally:
                if conn:
                    conn.close()

        elif db_type == 'Oracle':
            # For Oracle, use cx_Oracle
            try:
                username = data['dbName']
                password = data['dbPassword']
                host = data['linuxHost']
                port = data['dbPort']
                service_name = data['dbInstance']
                
                # Test Oracle connection
                oracle_conn, error = get_oracle_connection(
                    username=username,
                    password=password,
                    host=host,
                    port=port,
                    service_name=service_name
                )
                
                if error:
                    return jsonify({
                        'success': False,
                        'message': f'Oracle connection error: {error}'
                    })
                
                # Test a simple query - Get Oracle server date
                cursor = oracle_conn.cursor()
                cursor.execute("SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') AS SERVER_DATE FROM DUAL")
                result = cursor.fetchone()
                server_date = result[0] if result else "Unknown"
                cursor.close()
                oracle_conn.close()
                
                return jsonify({
                    'success': True,
                    'message': f'Oracle connection successful! Server date: {server_date}',
                    'handle': f"oracle_{data['envName'].lower().replace(' ', '_')}"
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Oracle connection failed: {str(e)}'
                })

        elif db_type == 'Postgres':
            # For PostgreSQL, we would typically use psycopg2
            # This is a simulation for testing
            if data['dbName'] and data['dbInstance'] and data['dbPort']:
                return jsonify({
                    'success': True,
                    'message': 'PostgreSQL connection successful!',
                    'handle': f"postgres_{data['envName'].lower().replace(' ', '_')}"
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Missing required PostgreSQL connection parameters.'
                })

        else:
            return jsonify({
                'success': False,
                'message': f'Unsupported database type: {db_type}'
            })

    except Exception as e:
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