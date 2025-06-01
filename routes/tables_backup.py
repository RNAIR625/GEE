from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import sqlite3
from db_helpers import query_db, modify_db
from oracle_helpers import get_oracle_connection

# Create a Blueprint for tables routes
tables_bp = Blueprint('tables', __name__)

@tables_bp.route('/')
def tables_page():
    return render_template('tables.html', active_page='tables')

@tables_bp.route('/get_tables', methods=['GET'])
def get_tables():
    conn_handle = request.args.get('connection_handle', None)
    
    try:
        if conn_handle:
            # Get active connection details
            active_connections = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?', 
                                         (conn_handle,), one=True)
            if active_connections:
                # Get config details
                config_id = active_connections['CONFIG_ID']
                env_config = query_db('SELECT * FROM GEE_ENV_CONFIG WHERE GT_ID = ?', 
                                     (config_id,), one=True)
                
                if env_config:
                    # Connect to external database based on type
                    if env_config['DB_TYPE'] == 'SQLite':
                        ext_conn = sqlite3.connect(env_config['DB_NAME'])
                        ext_conn.row_factory = sqlite3.Row
                        ext_cursor = ext_conn.cursor()
                        
                        # Get table list from the external database
                        ext_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        ext_tables = ext_cursor.fetchall()
                        
                        # Format for response
                        tables_list = []
                        for table in ext_tables:
                            tables_list.append({
                                'GEC_ID': None,
                                'TABLE_NAME': table[0],
                                'TABLE_TYPE': 'EXTERNAL',
                                'QUERY': f"SELECT * FROM {table[0]}",
                                'DESCRIPTION': f"External table from {env_config['ENV_NAME']}",
                                'SOURCE': conn_handle,
                                'CREATE_DATE': datetime.now(),
                                'UPDATE_DATE': None,
                                'IS_IMPORTABLE': True
                            })
                        
                        ext_conn.close()
                        return jsonify(tables_list)
                    
                    elif env_config['DB_TYPE'] == 'Oracle':
                        try:
                            # Connect to Oracle database
                            username = env_config['DB_NAME']
                            password = env_config['DB_PASSWORD']
                            host = env_config['LINUX_HOST']  # Use LINUX_HOST for hostname
                            port = env_config['DB_PORT']
                            service_name = env_config['DB_INSTANCE']  # Use DB_INSTANCE as service_name
                            
                            oracle_conn, error = get_oracle_connection(
                                username=username,
                                password=password,
                                host=host,
                                port=port,
                                service_name=service_name
                            )
                            
                            if error:
                                return jsonify([{
                                    'GEC_ID': None,
                                    'TABLE_NAME': f'Error connecting to Oracle: {error}',
                                    'TABLE_TYPE': 'ERROR',
                                    'QUERY': '',
                                    'DESCRIPTION': 'Connection error',
                                    'SOURCE': conn_handle,
                                    'CREATE_DATE': datetime.now(),
                                    'UPDATE_DATE': None,
                                    'IS_IMPORTABLE': False
                                }])
                            
                            # Get user tables
                            oracle_cursor = oracle_conn.cursor()
                            oracle_cursor.execute(
                                "SELECT table_name FROM user_tables ORDER BY table_name"
                            )
                            tables = oracle_cursor.fetchall()
                            
                            # Format for response
                            tables_list = []
                            for table in tables:
                                tables_list.append({
                                    'GEC_ID': None,
                                    'TABLE_NAME': table[0],
                                    'TABLE_TYPE': 'EXTERNAL',
                                    'QUERY': f'SELECT * FROM "{table[0]}"',
                                    'DESCRIPTION': f"Oracle table from {env_config['ENV_NAME']}",
                                    'SOURCE': conn_handle,
                                    'CREATE_DATE': datetime.now(),
                                    'UPDATE_DATE': None,
                                    'IS_IMPORTABLE': True
                                })
                            
                            oracle_cursor.close()
                            oracle_conn.close()
                            return jsonify(tables_list)
                        except Exception as e:
                            print(f"Oracle error: {str(e)}")
                            return jsonify([{
                                'GEC_ID': None,
                                'TABLE_NAME': f'Error: {str(e)}',
                                'TABLE_TYPE': 'ERROR',
                                'QUERY': '',
                                'DESCRIPTION': 'Oracle connection error',
                                'SOURCE': conn_handle,
                                'CREATE_DATE': datetime.now(),
                                'UPDATE_DATE': None,
                                'IS_IMPORTABLE': False
                            }])
                    
                    elif env_config['DB_TYPE'] == 'Postgres':
                        # For demo, return placeholder message - in production, implement actual connections
                        return jsonify([{
                            'GEC_ID': None,
                            'TABLE_NAME': 'Database connection not implemented',
                            'TABLE_TYPE': 'EXTERNAL',
                            'QUERY': '',
                            'DESCRIPTION': f"External {env_config['DB_TYPE']} connection not yet implemented",
                            'SOURCE': conn_handle,
                            'CREATE_DATE': datetime.now(),
                            'UPDATE_DATE': None,
                            'IS_IMPORTABLE': False
                        }])
        
        # If no connection handle or connection not found, return internal tables
        tables = query_db('SELECT * FROM GEE_TABLES')
        
        # Convert SQLite Row objects to dictionaries for JSON serialization
        if tables:
            tables_list = [dict(table) for table in tables]
            return jsonify(tables_list)
        else:
            return jsonify([])
    
    except Exception as e:
        print(f"Error in get_tables: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

@tables_bp.route('/get_active_connections_for_tables')
def get_active_connections_for_tables():
    app_runtime_id = request.args.get('app_runtime_id')
    
    if not app_runtime_id:
        return jsonify({})
        
    try:
        connections = {}
        active_conns = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE APP_RUNTIME_ID = ?', 
                               (app_runtime_id,))
        
        if active_conns:
            for conn in active_conns:
                # Get environment name for each connection
                config = query_db('SELECT ENV_NAME, DB_TYPE FROM GEE_ENV_CONFIG WHERE GT_ID = ?', 
                                (conn['CONFIG_ID'],), one=True)
                
                connections[conn['HANDLE']] = {
                    'config_id': conn['CONFIG_ID'],
                    'created': conn['CREATED'],
                    'status': conn['STATUS'],
                    'env_name': config['ENV_NAME'] if config else 'Unknown',
                    'db_type': config['DB_TYPE'] if config else 'Unknown'
                }
        
        return jsonify(connections)
    except Exception as e:
        print(f"Error getting active connections: {str(e)}")
        return jsonify({})

@tables_bp.route('/get_environment_configs')
def get_environment_configs():
    """Get all saved environment configurations for the dropdown"""
    try:
        configs = query_db('SELECT GT_ID, ENV_NAME, DB_TYPE, DB_NAME FROM GEE_ENV_CONFIG ORDER BY ENV_NAME')
        
        # Convert to list of dictionaries
        config_list = []
        for config in configs:
            config_list.append({
                'GT_ID': config['GT_ID'],
                'ENV_NAME': config['ENV_NAME'],
                'DB_TYPE': config['DB_TYPE'],
                'DB_NAME': config['DB_NAME']
            })
        
        return jsonify(config_list)
    except Exception as e:
        print(f"Error getting environment configs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@tables_bp.route('/get_tables_from_environment')
def get_tables_from_environment():
    """Get tables from a specific environment configuration"""
    config_id = request.args.get('config_id')
    
    if not config_id:
        return jsonify({'success': False, 'message': 'Environment configuration ID is required'})
    
    try:
        # Get environment configuration
        env_config = query_db('SELECT * FROM GEE_ENV_CONFIG WHERE GT_ID = ?', (config_id,), one=True)
        
        if not env_config:
            return jsonify({'success': False, 'message': 'Environment configuration not found'})
        
        tables_list = []
        
        if env_config['DB_TYPE'] == 'SQLite':
            try:
                conn = sqlite3.connect(env_config['DB_NAME'])
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = f"{env_config['ENV_NAME']}.{env_config['DB_NAME']}.{table[0]}"
                    tables_list.append({
                        'display_name': table_name,
                        'actual_name': table[0],
                        'env_name': env_config['ENV_NAME'],
                        'db_name': env_config['DB_NAME']
                    })
                
                conn.close()
                
            except Exception as e:
                return jsonify({'success': False, 'message': f'SQLite error: {str(e)}'})
        
        elif env_config['DB_TYPE'] == 'Oracle':
            try:
                from oracle_helpers import get_oracle_connection
                
                username = env_config['DB_USERNAME'] or env_config['DB_NAME']
                password = env_config['DB_PASSWORD'] or ''
                host = env_config['DB_HOST'] or env_config['LINUX_HOST']
                port = env_config['DB_PORT']
                service_name = env_config['DB_INSTANCE']
                
                oracle_conn, error = get_oracle_connection(
                    username=username,
                    password=password,
                    host=host,
                    port=port,
                    service_name=service_name
                )
                
                if error:
                    return jsonify({'success': False, 'message': f'Oracle connection error: {error}'})
                
                cursor = oracle_conn.cursor()
                cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = f"{env_config['ENV_NAME']}.{env_config['DB_NAME']}.{table[0]}"
                    tables_list.append({
                        'display_name': table_name,
                        'actual_name': table[0],
                        'env_name': env_config['ENV_NAME'],
                        'db_name': env_config['DB_NAME']
                    })
                
                cursor.close()
                oracle_conn.close()
                
            except Exception as e:
                return jsonify({'success': False, 'message': f'Oracle error: {str(e)}'})
        
        elif env_config['DB_TYPE'] == 'MySQL':
            try:
                from mysql_helpers import get_mysql_connection
                
                username = env_config['DB_USERNAME']
                password = env_config['DB_PASSWORD'] or ''
                host = env_config['DB_HOST']
                port = env_config['DB_PORT']
                database = env_config['DB_NAME']
                
                mysql_conn, error = get_mysql_connection(
                    username=username,
                    password=password,
                    host=host,
                    port=port,
                    database=database
                )
                
                if error:
                    return jsonify({'success': False, 'message': f'MySQL connection error: {error}'})
                
                cursor = mysql_conn.cursor()
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = f"{env_config['ENV_NAME']}.{env_config['DB_NAME']}.{table[0]}"
                    tables_list.append({
                        'display_name': table_name,
                        'actual_name': table[0],
                        'env_name': env_config['ENV_NAME'],
                        'db_name': env_config['DB_NAME']
                    })
                
                cursor.close()
                mysql_conn.close()
                
            except Exception as e:
                return jsonify({'success': False, 'message': f'MySQL error: {str(e)}'})
        
        elif env_config['DB_TYPE'] == 'Postgres':
            try:
                import psycopg2
                
                username = env_config['DB_USERNAME']
                password = env_config['DB_PASSWORD'] or ''
                host = env_config['DB_HOST']
                port = env_config['DB_PORT']
                database = env_config['DB_NAME']
                
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=30
                )
                
                cursor = conn.cursor()
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = f"{env_config['ENV_NAME']}.{env_config['DB_NAME']}.{table[0]}"
                    tables_list.append({
                        'display_name': table_name,
                        'actual_name': table[0],
                        'env_name': env_config['ENV_NAME'],
                        'db_name': env_config['DB_NAME']
                    })
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                return jsonify({'success': False, 'message': f'PostgreSQL error: {str(e)}'})
        
        else:
            return jsonify({'success': False, 'message': f'Database type {env_config["DB_TYPE"]} not supported'})
        
        # Convert env_config Row to dict for JSON serialization
        env_config_dict = {
            'GT_ID': env_config['GT_ID'],
            'ENV_NAME': env_config['ENV_NAME'],
            'DB_TYPE': env_config['DB_TYPE'],
            'DB_NAME': env_config['DB_NAME']
        }
        
        return jsonify({'success': True, 'tables': tables_list, 'env_config': env_config_dict})
        
    except Exception as e:
        print(f"Error getting tables from environment: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@tables_bp.route('/add_table', methods=['POST'])
def add_table():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_TABLES (TABLE_NAME, TABLE_TYPE, QUERY, DESCRIPTION) VALUES (?, ?, ?, ?)',
            (data['tableName'], data['tableType'], data['query'], data['description'])
        )
        return jsonify({'success': True, 'message': 'Table added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@tables_bp.route('/update_table', methods=['PUT'])
def update_table():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_TABLES SET TABLE_NAME = ?, TABLE_TYPE = ?, QUERY = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GEC_ID = ?',
            (data['tableName'], data['tableType'], data['query'], data['description'], datetime.now(), data['gecId'])
        )
        return jsonify({'success': True, 'message': 'Table updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@tables_bp.route('/delete_table/<int:gec_id>', methods=['DELETE'])
def delete_table(gec_id):
    try:
        modify_db('DELETE FROM GEE_TABLES WHERE GEC_ID = ?', (gec_id,))
        return jsonify({'success': True, 'message': 'Table deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@tables_bp.route('/test_query', methods=['POST'])
def test_query():
    data = request.json
    query = data.get('query', '')
    conn_handle = data.get('connection_handle', None)
    env_config_id = data.get('environment_config_id', None)

    if not query or not query.strip().upper().startswith('SELECT'):
        return jsonify({
            'success': False,
            'message': 'Only SELECT queries are allowed for testing'
        })
    
    # External database connection object
    ext_conn = None

    try:
        # If using external connection handle
        if conn_handle:
            active_conn = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?',
                                  (conn_handle,), one=True)

            if active_conn:
                config_id = active_conn['CONFIG_ID']
                env_config = query_db('SELECT * FROM GEE_ENV_CONFIG WHERE GT_ID = ?',
                                     (config_id,), one=True)

                if env_config:
                    if env_config['DB_TYPE'] == 'SQLite':
                        try:
                            # Connect to external SQLite database
                            ext_conn = sqlite3.connect(env_config['DB_NAME'])
                            ext_conn.row_factory = sqlite3.Row

                            # Limit the number of rows returned for safety
                            if 'LIMIT' not in query.upper():
                                if query.strip().endswith(';'):
                                    query = query[:-1] + ' LIMIT 10;'
                                else:
                                    query = query + ' LIMIT 10;'

                            # Execute query on external database
                            ext_cursor = ext_conn.cursor()
                            ext_cursor.execute(query)
                            results = ext_cursor.fetchall()

                            # Get column names
                            columns = [description[0] for description in ext_cursor.description]

                            # Format results
                            formatted_results = []
                            for row in results:
                                row_dict = {}
                                for i, col in enumerate(columns):
                                    row_dict[col] = row[i]
                                formatted_results.append(row_dict)

                            return jsonify({
                                'success': True,
                                'message': 'Query executed successfully on external database',
                                'columns': columns,
                                'data': formatted_results
                            })
                        finally:
                            # Ensure the connection is closed even if there's an error
                            if ext_conn:
                                ext_conn.close()
                    
                    elif env_config['DB_TYPE'] == 'Oracle':
                        try:
                            # Connect to Oracle database
                            username = env_config['DB_NAME']
                            password = env_config['DB_PASSWORD']
                            host = env_config['LINUX_HOST']
                            port = env_config['DB_PORT']
                            service_name = env_config['DB_INSTANCE']
                            
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
                                
                            # Limit rows for safety if ROWNUM not in query
                            if 'ROWNUM' not in query.upper():
                                if query.strip().endswith(';'):
                                    query = query[:-1] + ' AND ROWNUM <= 10'
                                else:
                                    query = query + ' AND ROWNUM <= 10'
                            
                            # Execute query on Oracle database
                            oracle_cursor = oracle_conn.cursor()
                            oracle_cursor.execute(query)
                            results = oracle_cursor.fetchall()
                            
                            # Get column names
                            columns = [desc[0] for desc in oracle_cursor.description]
                            
                            # Format results
                            formatted_results = []
                            for row in results:
                                row_dict = {}
                                for i, col in enumerate(columns):
                                    row_dict[col] = row[i]
                                formatted_results.append(row_dict)
                                
                            oracle_cursor.close()
                            oracle_conn.close()
                            
                            return jsonify({
                                'success': True,
                                'message': 'Query executed successfully on Oracle database',
                                'columns': columns,
                                'data': formatted_results
                            })
                            
                        except Exception as e:
                            return jsonify({
                                'success': False,
                                'message': f'Error executing Oracle query: {str(e)}'
                            })
                            
                    else:
                        return jsonify({
                            'success': False,
                            'message': f"Connection to {env_config['DB_TYPE']} database not implemented"
                        })
        
        # If using environment config ID directly (for new table creation workflow)
        elif env_config_id:
            env_config = query_db('SELECT * FROM GEE_ENV_CONFIG WHERE GT_ID = ?',
                                (env_config_id,), one=True)
            
            if not env_config:
                return jsonify({
                    'success': False,
                    'message': 'Environment configuration not found'
                })
            
            # Connect to the specified environment database
            if env_config['DB_TYPE'] == 'SQLite':
                try:
                    ext_conn = sqlite3.connect(env_config['DB_NAME'])
                    ext_conn.row_factory = sqlite3.Row
                    ext_cursor = ext_conn.cursor()
                    
                    # Limit the number of rows returned for safety
                    if 'LIMIT' not in query.upper():
                        if query.strip().endswith(';'):
                            query = query[:-1] + ' LIMIT 10;'
                        else:
                            query = query + ' LIMIT 10;'
                    
                    ext_cursor.execute(query)
                    results = ext_cursor.fetchall()
                    
                    if results:
                        formatted_results = [dict(row) for row in results]
                        columns = list(formatted_results[0].keys()) if formatted_results else []
                        
                        ext_conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': f'Query executed successfully on {env_config["ENV_NAME"]} ({len(results)} rows)',
                            'columns': columns,
                            'data': formatted_results
                        })
                    else:
                        ext_conn.close()
                        return jsonify({
                            'success': True,
                            'message': f'Query executed successfully on {env_config["ENV_NAME"]} (0 rows)',
                            'columns': [],
                            'data': []
                        })
                        
                except Exception as e:
                    if ext_conn:
                        ext_conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'SQLite error: {str(e)}'
                    })
            
            elif env_config['DB_TYPE'] == 'Oracle':
                try:
                    from oracle_helpers import get_oracle_connection
                    
                    username = env_config['DB_USERNAME'] or env_config['DB_NAME']
                    password = env_config['DB_PASSWORD'] or ''
                    host = env_config['DB_HOST'] or env_config['LINUX_HOST']
                    port = env_config['DB_PORT']
                    oracle_conn_type = env_config.get('ORACLE_CONN_TYPE', 'service')
                    instance_value = env_config['DB_INSTANCE']
                    
                    if oracle_conn_type == 'sid':
                        oracle_conn, error = get_oracle_connection(
                            username=username, password=password, host=host, port=port, sid=instance_value
                        )
                    else:
                        oracle_conn, error = get_oracle_connection(
                            username=username, password=password, host=host, port=port, service_name=instance_value
                        )
                    
                    if error:
                        return jsonify({
                            'success': False,
                            'message': f'Oracle connection error: {error}'
                        })
                    
                    cursor = oracle_conn.cursor()
                    
                    # Limit the number of rows returned for safety
                    if 'LIMIT' not in query.upper() and 'ROWNUM' not in query.upper():
                        if query.strip().endswith(';'):
                            query = query[:-1] + ' AND ROWNUM <= 10;'
                        else:
                            query = query + ' AND ROWNUM <= 10;'
                    
                    cursor.execute(query)
                    results = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    cursor.close()
                    oracle_conn.close()
                    
                    formatted_results = [dict(zip(columns, row)) for row in results]
                    
                    return jsonify({
                        'success': True,
                        'message': f'Query executed successfully on {env_config["ENV_NAME"]} ({len(results)} rows)',
                        'columns': columns,
                        'data': formatted_results
                    })
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'message': f'Oracle error: {str(e)}'
                    })
            
            elif env_config['DB_TYPE'] == 'MySQL':
                try:
                    from mysql_helpers import get_mysql_connection
                    
                    mysql_conn, error = get_mysql_connection(
                        username=env_config['DB_USERNAME'],
                        password=env_config['DB_PASSWORD'] or '',
                        host=env_config['DB_HOST'],
                        port=env_config['DB_PORT'],
                        database=env_config['DB_NAME']
                    )
                    
                    if error:
                        return jsonify({
                            'success': False,
                            'message': f'MySQL connection error: {error}'
                        })
                    
                    cursor = mysql_conn.cursor()
                    
                    # Limit the number of rows returned for safety
                    if 'LIMIT' not in query.upper():
                        if query.strip().endswith(';'):
                            query = query[:-1] + ' LIMIT 10;'
                        else:
                            query = query + ' LIMIT 10;'
                    
                    cursor.execute(query)
                    results = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    cursor.close()
                    mysql_conn.close()
                    
                    formatted_results = [dict(zip(columns, row)) for row in results]
                    
                    return jsonify({
                        'success': True,
                        'message': f'Query executed successfully on {env_config["ENV_NAME"]} ({len(results)} rows)',
                        'columns': columns,
                        'data': formatted_results
                    })
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'message': f'MySQL error: {str(e)}'
                    })
            
            elif env_config['DB_TYPE'] == 'Postgres':
                try:
                    import psycopg2
                    
                    conn = psycopg2.connect(
                        host=env_config['DB_HOST'],
                        port=env_config['DB_PORT'],
                        database=env_config['DB_NAME'],
                        user=env_config['DB_USERNAME'],
                        password=env_config['DB_PASSWORD'] or '',
                        connect_timeout=30
                    )
                    
                    cursor = conn.cursor()
                    
                    # Limit the number of rows returned for safety
                    if 'LIMIT' not in query.upper():
                        if query.strip().endswith(';'):
                            query = query[:-1] + ' LIMIT 10;'
                        else:
                            query = query + ' LIMIT 10;'
                    
                    cursor.execute(query)
                    results = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    cursor.close()
                    conn.close()
                    
                    formatted_results = [dict(zip(columns, row)) for row in results]
                    
                    return jsonify({
                        'success': True,
                        'message': f'Query executed successfully on {env_config["ENV_NAME"]} ({len(results)} rows)',
                        'columns': columns,
                        'data': formatted_results
                    })
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'message': f'PostgreSQL error: {str(e)}'
                    })
            
            else:
                return jsonify({
                    'success': False,
                    'message': f'Database type {env_config["DB_TYPE"]} not supported for testing'
                })

        # Default: Execute on internal database
        # Limit the number of rows returned for safety
        if 'LIMIT' not in query.upper():
            if query.strip().endswith(';'):
                query = query[:-1] + ' LIMIT 10;'
            else:
                query = query + ' LIMIT 10;'

        results = query_db(query)
        
        if results:
            # Convert SQLite Row objects to dictionaries for JSON serialization
            formatted_results = [dict(row) for row in results]
            columns = list(formatted_results[0].keys()) if formatted_results else []
            
            return jsonify({
                'success': True,
                'message': 'Query executed successfully',
                'columns': columns,
                'data': formatted_results
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Query executed successfully but returned no results',
                'columns': [],
                'data': []
            })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error executing query: {str(e)}'})

@tables_bp.route('/import_table_structure', methods=['POST'])
def import_table_structure():
    data = request.json
    conn_handle = data.get('connection_handle')
    table_name = data.get('table_name')

    if not conn_handle or not table_name:
        return jsonify({'success': False, 'message': 'Connection handle and table name are required'})

    # External database connection object
    ext_conn = None

    try:
        # Get the connection details
        active_conn = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?',
                              (conn_handle,), one=True)

        if not active_conn:
            return jsonify({'success': False, 'message': 'Connection not found'})

        config_id = active_conn['CONFIG_ID']
        env_config = query_db('SELECT * FROM GEE_ENV_CONFIG WHERE GT_ID = ?',
                            (config_id,), one=True)

        if not env_config:
            return jsonify({'success': False, 'message': 'Environment configuration not found'})

        # Connect to the external database
        if env_config['DB_TYPE'] == 'SQLite':
            try:
                ext_conn = sqlite3.connect(env_config['DB_NAME'])
                ext_conn.row_factory = sqlite3.Row

                # Get the table structure
                ext_cursor = ext_conn.cursor()
                ext_cursor.execute(f"PRAGMA table_info({table_name})")
                columns = ext_cursor.fetchall()

                # Create a query to fetch data
                query = f"SELECT * FROM {table_name}"

                # Store in GEE_TABLES
                modify_db(
                    'INSERT INTO GEE_TABLES (TABLE_NAME, TABLE_TYPE, QUERY, DESCRIPTION) VALUES (?, ?, ?, ?)',
                    (table_name, 'I', query, f"Imported from {env_config['ENV_NAME']}")
                )

                # Get the new table ID
                new_table = query_db('SELECT GEC_ID FROM GEE_TABLES WHERE TABLE_NAME = ? ORDER BY GEC_ID DESC LIMIT 1',
                                    (table_name,), one=True)

                # Create GEE_TABLE_COLUMNS table if it doesn't exist
                modify_db('''
                    CREATE TABLE IF NOT EXISTS GEE_TABLE_COLUMNS (
                        COLUMN_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        GEC_ID INTEGER NOT NULL,
                        COLUMN_NAME TEXT NOT NULL,
                        COLUMN_TYPE TEXT NOT NULL,
                        COLUMN_SIZE INTEGER,
                        CREATE_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UPDATE_DATE TIMESTAMP,
                        FOREIGN KEY (GEC_ID) REFERENCES GEE_TABLES(GEC_ID)
                    )
                ''')

                # Store column definitions
                column_list = []
                for col in columns:
                    column_name = col['name']
                    column_type = col['type']
                    column_size = len(column_name)  # This is a simplification; in reality, you'd determine proper size

                    modify_db(
                        'INSERT INTO GEE_TABLE_COLUMNS (GEC_ID, COLUMN_NAME, COLUMN_TYPE, COLUMN_SIZE) VALUES (?, ?, ?, ?)',
                        (new_table['GEC_ID'], column_name, column_type, column_size)
                    )

                # Format columns for response
                column_list = []
                for col in columns:
                    column_list.append({
                        'name': col['name'],
                        'type': col['type'],
                        'notnull': col['notnull'],
                        'dflt_value': col['dflt_value'],
                        'pk': col['pk']
                    })
                
                ext_conn.close()
                
                return jsonify({
                    'success': True,
                    'message': f'Table structure imported successfully for {table_name}',
                    'columns': column_list
                })
                
            except Exception as e:
                if ext_conn:
                    ext_conn.close()
                return jsonify({
                    'success': False,
                    'message': f'Error importing SQLite table structure: {str(e)}'
                })

        elif env_config['DB_TYPE'] == 'Oracle':
            try:
                # Connect to Oracle database
                username = env_config['DB_NAME']
                password = env_config['DB_PASSWORD']
                host = env_config['LINUX_HOST']
                port = env_config['DB_PORT']
                service_name = env_config['DB_INSTANCE']
                
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
                
                # Get the table structure from Oracle
                oracle_cursor = oracle_conn.cursor()
                
                # Get column information
                oracle_cursor.execute(f"""
                    SELECT 
                        column_name, 
                        data_type,
                        data_length,
                        data_precision,
                        nullable
                    FROM 
                        user_tab_columns
                    WHERE 
                        table_name = '{table_name.upper()}'
                    ORDER BY 
                        column_id
                """)
                columns = oracle_cursor.fetchall()
                
                if not columns:
                    oracle_cursor.close()
                    oracle_conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'Table {table_name} not found or no access'
                    })
                
                # Create a query to fetch data
                query = f'SELECT * FROM "{table_name}"'
                
                # Store in GEE_TABLES
                modify_db(
                    'INSERT INTO GEE_TABLES (TABLE_NAME, TABLE_TYPE, QUERY, DESCRIPTION) VALUES (?, ?, ?, ?)',
                    (table_name, 'I', query, f"Imported from Oracle - {env_config['ENV_NAME']}")
                )
                
                # Get the new table ID
                new_table = query_db('SELECT GEC_ID FROM GEE_TABLES WHERE TABLE_NAME = ? ORDER BY GEC_ID DESC LIMIT 1',
                                    (table_name,), one=True)
                
                # Create GEE_TABLE_COLUMNS table if it doesn't exist
                modify_db('''
                    CREATE TABLE IF NOT EXISTS GEE_TABLE_COLUMNS (
                        COLUMN_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        GEC_ID INTEGER NOT NULL,
                        COLUMN_NAME TEXT NOT NULL,
                        COLUMN_TYPE TEXT NOT NULL,
                        COLUMN_SIZE INTEGER,
                        CREATE_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UPDATE_DATE TIMESTAMP,
                        FOREIGN KEY (GEC_ID) REFERENCES GEE_TABLES(GEC_ID)
                    )
                ''')
                
                # Store column definitions
                column_list = []
                for col in columns:
                    column_name = col[0]
                    column_type = col[1]
                    column_size = col[2] or 0
                    
                    modify_db(
                        'INSERT INTO GEE_TABLE_COLUMNS (GEC_ID, COLUMN_NAME, COLUMN_TYPE, COLUMN_SIZE) VALUES (?, ?, ?, ?)',
                        (new_table['GEC_ID'], column_name, column_type, column_size)
                    )
                    
                    # Format for response
                    column_list.append({
                        'name': column_name,
                        'type': column_type,
                        'size': column_size,
                        'precision': col[3],
                        'nullable': 'Y' if col[4] == 'Y' else 'N'
                    })
                
                oracle_cursor.close()
                oracle_conn.close()
                
                return jsonify({
                    'success': True,
                    'message': f'Table structure imported successfully for {table_name}',
                    'columns': column_list
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error importing Oracle table structure: {str(e)}'
                })
        
        else:
            return jsonify({'success': False, 'message': f'Database type {env_config["DB_TYPE"]} not supported yet'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error importing table structure: {str(e)}'})