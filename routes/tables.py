from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import sqlite3
from db_helpers import query_db, modify_db

# Create a Blueprint for table routes
tables_bp = Blueprint('tables', __name__)

@tables_bp.route('/')
def tables_page():
    return render_template('tables.html', active_page='tables')

@tables_bp.route('/get_tables')
def get_tables():
    """Get all tables, optionally filtered by connection handle"""
    connection_handle = request.args.get('connection_handle')
    
    if connection_handle:
        # Get tables from external connection
        try:
            # Get the database config from the active connection
            active_conn = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?',
                                  (connection_handle,), one=True)
            
            if active_conn and active_conn['DB_CONFIG_ID']:
                # Get database configuration
                db_config = query_db('''SELECT dc.*, e.ENV_NAME 
                                       FROM GEE_DATABASE_CONFIGS dc 
                                       JOIN GEE_ENVIRONMENTS e ON e.ENV_ID = dc.ENV_ID 
                                       WHERE dc.DB_CONFIG_ID = ?''',
                                    (active_conn['DB_CONFIG_ID'],), one=True)
                
                if db_config:
                    if db_config['DB_TYPE'] == 'SQLite':
                        try:
                            ext_conn = sqlite3.connect(db_config['DB_NAME'])
                            cursor = ext_conn.cursor()
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            tables = cursor.fetchall()
                            cursor.close()
                            ext_conn.close()
                            
                            table_list = []
                            for table in tables:
                                table_name = f"{db_config['ENV_NAME']}.{db_config['DB_NAME']}.{table[0]}"
                                table_list.append({
                                    'TABLE_NAME': table_name,
                                    'TABLE_TYPE': 'EXTERNAL',
                                    'SOURCE': connection_handle,
                                    'DESCRIPTION': f"External table from {db_config['ENV_NAME']} - {db_config['DB_DISPLAY_NAME']}",
                                    'CREATE_DATE': datetime.now().isoformat()
                                })
                            
                            return jsonify(table_list)
                        except Exception as e:
                            return jsonify([])
                    
                    elif db_config['DB_TYPE'] == 'Oracle':
                        try:
                            from oracle_helpers import get_oracle_connection
                            
                            username = db_config['DB_USERNAME']
                            password = db_config['DB_PASSWORD'] or ''
                            host = db_config['DB_HOST']
                            port = db_config['DB_PORT']
                            oracle_conn_type = db_config.get('ORACLE_CONN_TYPE', 'service')
                            instance_value = db_config['DB_INSTANCE']
                            
                            if oracle_conn_type == 'sid':
                                oracle_conn, error = get_oracle_connection(
                                    username=username, password=password, host=host, port=port,
                                    service_name=None, sid=instance_value
                                )
                            else:
                                oracle_conn, error = get_oracle_connection(
                                    username=username, password=password, host=host, port=port,
                                    service_name=instance_value, sid=None
                                )
                            
                            if error:
                                return jsonify([])
                            
                            cursor = oracle_conn.cursor()
                            cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
                            tables = cursor.fetchall()
                            cursor.close()
                            oracle_conn.close()
                            
                            table_list = []
                            for table in tables:
                                table_name = f"{db_config['ENV_NAME']}.{db_config['DB_NAME']}.{table[0]}"
                                table_list.append({
                                    'TABLE_NAME': table_name,
                                    'TABLE_TYPE': 'EXTERNAL',
                                    'SOURCE': connection_handle,
                                    'DESCRIPTION': f"Oracle table from {db_config['ENV_NAME']} - {db_config['DB_DISPLAY_NAME']}",
                                    'CREATE_DATE': datetime.now().isoformat()
                                })
                            
                            return jsonify(table_list)
                        except Exception as e:
                            return jsonify([])
                    
                    elif db_config['DB_TYPE'] in ['MySQL', 'Postgres']:
                        # Similar implementation for MySQL and Postgres
                        table_list = [{
                            'TABLE_NAME': f"{db_config['ENV_NAME']}.{db_config['DB_NAME']}.sample_table",
                            'TABLE_TYPE': 'EXTERNAL',
                            'SOURCE': connection_handle,
                            'DESCRIPTION': f"External {db_config['DB_TYPE']} connection not yet implemented",
                            'CREATE_DATE': datetime.now().isoformat()
                        }]
                        return jsonify(table_list)
            
            return jsonify([])
        except Exception as e:
            return jsonify([])
    else:
        # Get internal tables
        try:
            tables = query_db('SELECT * FROM GEE_TABLES ORDER BY TABLE_NAME')
            result = []
            for table in tables:
                table_dict = dict(table)
                result.append(table_dict)
            return jsonify(result)
        except Exception as e:
            return jsonify([])

@tables_bp.route('/get_active_connections_for_tables')
def get_active_connections_for_tables():
    """Get active connections for tables functionality"""
    app_runtime_id = request.args.get('app_runtime_id')
    if not app_runtime_id:
        return jsonify({})
    
    try:
        connections = {}
        active_conns = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE APP_RUNTIME_ID = ?', 
                              (app_runtime_id,))

        for conn in active_conns:
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
                    env_name = 'Unknown Environment'
                    db_type = 'Unknown'
                    db_display_name = 'Unknown Database'
            else:
                # Legacy format: skip or handle differently
                continue

            connections[conn['HANDLE']] = {
                'config_id': conn['CONFIG_ID'],
                'db_config_id': conn['DB_CONFIG_ID'],
                'created': conn['CREATED'],
                'status': conn['STATUS'],
                'env_name': env_name,
                'db_type': db_type,
                'db_display_name': db_display_name
            }

        return jsonify(connections)
    except Exception as e:
        return jsonify({})

@tables_bp.route('/get_environment_configs')
def get_environment_configs():
    """Get environment configurations for table creation"""
    try:
        # Get environments with their database configurations
        environments = query_db('SELECT * FROM GEE_ENVIRONMENTS ORDER BY ENV_NAME')
        result = []
        
        for env in environments:
            # Get database configs for this environment
            db_configs = query_db('SELECT * FROM GEE_DATABASE_CONFIGS WHERE ENV_ID = ? ORDER BY IS_PRIMARY DESC, DB_DISPLAY_NAME',
                                (env['ENV_ID'],))
            
            for db_config in db_configs:
                result.append({
                    'GT_ID': db_config['DB_CONFIG_ID'],  # Use DB_CONFIG_ID as GT_ID for compatibility
                    'ENV_NAME': f"{env['ENV_NAME']} - {db_config['DB_DISPLAY_NAME']}",
                    'DB_TYPE': db_config['DB_TYPE'],
                    'DB_NAME': db_config['DB_NAME'],
                    'ENV_ID': env['ENV_ID'],
                    'DB_CONFIG_ID': db_config['DB_CONFIG_ID']
                })
        
        return jsonify(result)
    except Exception as e:
        return jsonify([])

@tables_bp.route('/get_tables_from_environment')
def get_tables_from_environment():
    """Get tables from a specific environment database configuration"""
    config_id = request.args.get('config_id')  # This is actually DB_CONFIG_ID
    
    if not config_id:
        return jsonify({'success': False, 'message': 'Configuration ID is required'})
    
    try:
        # Get database configuration
        db_config = query_db('''SELECT dc.*, e.ENV_NAME 
                               FROM GEE_DATABASE_CONFIGS dc 
                               JOIN GEE_ENVIRONMENTS e ON e.ENV_ID = dc.ENV_ID 
                               WHERE dc.DB_CONFIG_ID = ?''',
                           (config_id,), one=True)
        
        if not db_config:
            return jsonify({'success': False, 'message': 'Database configuration not found'})
        
        tables_list = []
        
        if db_config['DB_TYPE'] == 'SQLite':
            try:
                conn = sqlite3.connect(db_config['DB_NAME'])
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = cursor.fetchall()
                cursor.close()
                conn.close()
                
                for table in tables:
                    table_name = f"{db_config['ENV_NAME']}.{db_config['DB_NAME']}.{table[0]}"
                    tables_list.append({
                        'actual_name': table[0],
                        'display_name': table_name,
                        'env_name': db_config['ENV_NAME'],
                        'db_name': db_config['DB_NAME']
                    })
            except Exception as e:
                return jsonify({'success': False, 'message': f'SQLite error: {str(e)}'})
        
        elif db_config['DB_TYPE'] == 'Oracle':
            try:
                from oracle_helpers import get_oracle_connection
                
                username = db_config['DB_USERNAME']
                password = db_config['DB_PASSWORD'] or ''
                host = db_config['DB_HOST']
                port = db_config['DB_PORT']
                oracle_conn_type = db_config.get('ORACLE_CONN_TYPE', 'service')
                instance_value = db_config['DB_INSTANCE']
                
                if oracle_conn_type == 'sid':
                    oracle_conn, error = get_oracle_connection(
                        username=username, password=password, host=host, port=port,
                        service_name=None, sid=instance_value
                    )
                else:
                    oracle_conn, error = get_oracle_connection(
                        username=username, password=password, host=host, port=port,
                        service_name=instance_value, sid=None
                    )
                
                if error:
                    return jsonify({'success': False, 'message': f'Oracle connection error: {error}'})
                
                cursor = oracle_conn.cursor()
                cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
                tables = cursor.fetchall()
                cursor.close()
                oracle_conn.close()
                
                for table in tables:
                    table_name = f"{db_config['ENV_NAME']}.{db_config['DB_NAME']}.{table[0]}"
                    tables_list.append({
                        'actual_name': table[0],
                        'display_name': table_name,
                        'env_name': db_config['ENV_NAME'],
                        'db_name': db_config['DB_NAME']
                    })
            except Exception as e:
                return jsonify({'success': False, 'message': f'Oracle error: {str(e)}'})
        
        elif db_config['DB_TYPE'] == 'MySQL':
            try:
                from mysql_helpers import get_mysql_connection
                
                mysql_conn, error = get_mysql_connection(
                    username=db_config['DB_USERNAME'],
                    password=db_config['DB_PASSWORD'] or '',
                    host=db_config['DB_HOST'],
                    port=db_config['DB_PORT'],
                    database=db_config['DB_NAME']
                )
                
                if error:
                    return jsonify({'success': False, 'message': f'MySQL connection error: {error}'})
                
                cursor = mysql_conn.cursor()
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                cursor.close()
                mysql_conn.close()
                
                for table in tables:
                    table_name = f"{db_config['ENV_NAME']}.{db_config['DB_NAME']}.{table[0]}"
                    tables_list.append({
                        'actual_name': table[0],
                        'display_name': table_name,
                        'env_name': db_config['ENV_NAME'],
                        'db_name': db_config['DB_NAME']
                    })
            except Exception as e:
                return jsonify({'success': False, 'message': f'MySQL error: {str(e)}'})
        
        elif db_config['DB_TYPE'] == 'Postgres':
            try:
                import psycopg2
                
                conn = psycopg2.connect(
                    host=db_config['DB_HOST'],
                    port=db_config['DB_PORT'],
                    database=db_config['DB_NAME'],
                    user=db_config['DB_USERNAME'],
                    password=db_config['DB_PASSWORD'] or ''
                )
                
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
                tables = cursor.fetchall()
                cursor.close()
                conn.close()
                
                for table in tables:
                    table_name = f"{db_config['ENV_NAME']}.{db_config['DB_NAME']}.{table[0]}"
                    tables_list.append({
                        'actual_name': table[0],
                        'display_name': table_name,
                        'env_name': db_config['ENV_NAME'],
                        'db_name': db_config['DB_NAME']
                    })
            except Exception as e:
                return jsonify({'success': False, 'message': f'PostgreSQL error: {str(e)}'})
        else:
            return jsonify({'success': False, 'message': f'Database type {db_config["DB_TYPE"]} not supported'})
        
        # Convert db_config Row to dict for JSON serialization
        db_config_dict = {
            'DB_CONFIG_ID': db_config['DB_CONFIG_ID'],
            'ENV_NAME': db_config['ENV_NAME'],
            'DB_TYPE': db_config['DB_TYPE'],
            'DB_NAME': db_config['DB_NAME'],
            'DB_DISPLAY_NAME': db_config['DB_DISPLAY_NAME']
        }
        
        return jsonify({'success': True, 'tables': tables_list, 'db_config': db_config_dict})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@tables_bp.route('/test_query', methods=['POST'])
def test_query():
    """Test query endpoint updated for new database configuration system"""
    data = request.json
    query = data.get('query', '')
    conn_handle = data.get('connection_handle', None)
    env_config_id = data.get('environment_config_id', None)  # This is now DB_CONFIG_ID

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

            if active_conn and active_conn['DB_CONFIG_ID']:
                # Get database configuration
                db_config = query_db('''SELECT dc.*, e.ENV_NAME 
                                       FROM GEE_DATABASE_CONFIGS dc 
                                       JOIN GEE_ENVIRONMENTS e ON e.ENV_ID = dc.ENV_ID 
                                       WHERE dc.DB_CONFIG_ID = ?''',
                                    (active_conn['DB_CONFIG_ID'],), one=True)

                if db_config:
                    if db_config['DB_TYPE'] == 'SQLite':
                        try:
                            ext_conn = sqlite3.connect(db_config['DB_NAME'])
                            ext_conn.row_factory = sqlite3.Row

                            if 'LIMIT' not in query.upper():
                                if query.strip().endswith(';'):
                                    query = query[:-1] + ' LIMIT 10;'
                                else:
                                    query = query + ' LIMIT 10;'

                            ext_cursor = ext_conn.cursor()
                            ext_cursor.execute(query)
                            results = ext_cursor.fetchall()

                            columns = [description[0] for description in ext_cursor.description]
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
                            if ext_conn:
                                ext_conn.close()
                    
                    elif db_config['DB_TYPE'] == 'Oracle':
                        try:
                            from oracle_helpers import get_oracle_connection
                            
                            username = db_config['DB_USERNAME']
                            password = db_config['DB_PASSWORD'] or ''
                            host = db_config['DB_HOST']
                            port = db_config['DB_PORT']
                            oracle_conn_type = db_config.get('ORACLE_CONN_TYPE', 'service')
                            instance_value = db_config['DB_INSTANCE']
                            
                            if oracle_conn_type == 'sid':
                                oracle_conn, error = get_oracle_connection(
                                    username=username, password=password, host=host, port=port,
                                    service_name=None, sid=instance_value
                                )
                            else:
                                oracle_conn, error = get_oracle_connection(
                                    username=username, password=password, host=host, port=port,
                                    service_name=instance_value, sid=None
                                )
                            
                            if error:
                                return jsonify({
                                    'success': False,
                                    'message': f'Oracle connection error: {error}'
                                })
                                
                            if 'ROWNUM' not in query.upper():
                                if query.strip().endswith(';'):
                                    query = query[:-1] + ' AND ROWNUM <= 10'
                                else:
                                    query = query + ' AND ROWNUM <= 10'
                            
                            oracle_cursor = oracle_conn.cursor()
                            oracle_cursor.execute(query)
                            results = oracle_cursor.fetchall()
                            columns = [desc[0] for desc in oracle_cursor.description]
                            
                            oracle_cursor.close()
                            oracle_conn.close()
                            
                            formatted_results = [dict(zip(columns, row)) for row in results]
                            
                            return jsonify({
                                'success': True,
                                'message': f'Query executed successfully on {db_config["ENV_NAME"]} ({len(results)} rows)',
                                'columns': columns,
                                'data': formatted_results
                            })
                            
                        except Exception as e:
                            return jsonify({
                                'success': False,
                                'message': f'Oracle error: {str(e)}'
                            })
                    elif db_config['DB_TYPE'] == 'MySQL':
                        try:
                            from mysql_helpers import get_mysql_connection
                            
                            mysql_conn, error = get_mysql_connection(
                                username=db_config['DB_USERNAME'],
                                password=db_config['DB_PASSWORD'] or '',
                                host=db_config['DB_HOST'],
                                port=db_config['DB_PORT'],
                                database=db_config['DB_NAME']
                            )
                            
                            if error:
                                return jsonify({
                                    'success': False,
                                    'message': f'MySQL connection error: {error}'
                                })
                            
                            # Add LIMIT clause if not present
                            if 'LIMIT' not in query.upper():
                                if query.strip().endswith(';'):
                                    query = query[:-1] + ' LIMIT 10;'
                                else:
                                    query = query + ' LIMIT 10;'
                            
                            mysql_cursor = mysql_conn.cursor(dictionary=True)
                            mysql_cursor.execute(query)
                            results = mysql_cursor.fetchall()
                            
                            # Get column names
                            columns = list(results[0].keys()) if results else []
                            
                            mysql_cursor.close()
                            mysql_conn.close()
                            
                            return jsonify({
                                'success': True,
                                'message': f'Query executed successfully on {db_config["ENV_NAME"]} ({len(results)} rows)',
                                'columns': columns,
                                'data': results
                            })
                            
                        except Exception as e:
                            return jsonify({
                                'success': False,
                                'message': f'MySQL error: {str(e)}'
                            })
                    else:
                        return jsonify({
                            'success': False,
                            'message': f"Connection to {db_config['DB_TYPE']} database not implemented"
                        })
        
        # If using database config ID directly (for new table creation workflow)
        elif env_config_id:
            db_config = query_db('''SELECT dc.*, e.ENV_NAME 
                               FROM GEE_DATABASE_CONFIGS dc 
                               JOIN GEE_ENVIRONMENTS e ON e.ENV_ID = dc.ENV_ID 
                               WHERE dc.DB_CONFIG_ID = ?''',
                           (env_config_id,), one=True)
            
            if not db_config:
                return jsonify({
                    'success': False,
                    'message': 'Database configuration not found'
                })
            
            # Connect to the specified environment database
            if db_config['DB_TYPE'] == 'SQLite':
                try:
                    ext_conn = sqlite3.connect(db_config['DB_NAME'])
                    ext_conn.row_factory = sqlite3.Row
                    ext_cursor = ext_conn.cursor()
                    
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
                            'message': f'Query executed successfully on {db_config["ENV_NAME"]} - {db_config["DB_DISPLAY_NAME"]} ({len(results)} rows)',
                            'columns': columns,
                            'data': formatted_results
                        })
                    else:
                        ext_conn.close()
                        return jsonify({
                            'success': True,
                            'message': f'Query executed successfully on {db_config["ENV_NAME"]} - {db_config["DB_DISPLAY_NAME"]} (0 rows)',
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
            
            elif db_config['DB_TYPE'] == 'Oracle':
                try:
                    from oracle_helpers import get_oracle_connection
                    
                    username = db_config['DB_USERNAME']
                    password = db_config['DB_PASSWORD'] or ''
                    host = db_config['DB_HOST']
                    port = db_config['DB_PORT']
                    oracle_conn_type = db_config.get('ORACLE_CONN_TYPE', 'service')
                    instance_value = db_config['DB_INSTANCE']
                    
                    if oracle_conn_type == 'sid':
                        oracle_conn, error = get_oracle_connection(
                            username=username, password=password, host=host, port=port,
                            service_name=None, sid=instance_value
                        )
                    else:
                        oracle_conn, error = get_oracle_connection(
                            username=username, password=password, host=host, port=port,
                            service_name=instance_value, sid=None
                        )
                    
                    if error:
                        return jsonify({
                            'success': False,
                            'message': f'Oracle connection error: {error}'
                        })
                    
                    if 'ROWNUM' not in query.upper():
                        if query.strip().endswith(';'):
                            query = query[:-1] + ' AND ROWNUM <= 10'
                        else:
                            query = query + ' AND ROWNUM <= 10'
                    
                    cursor = oracle_conn.cursor()
                    cursor.execute(query)
                    results = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    cursor.close()
                    oracle_conn.close()
                    
                    formatted_results = [dict(zip(columns, row)) for row in results]
                    
                    return jsonify({
                        'success': True,
                        'message': f'Query executed successfully on {db_config["ENV_NAME"]} - {db_config["DB_DISPLAY_NAME"]} ({len(results)} rows)',
                        'columns': columns,
                        'data': formatted_results
                    })
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'message': f'Oracle error: {str(e)}'
                    })
            
            elif db_config['DB_TYPE'] == 'MySQL':
                try:
                    from mysql_helpers import get_mysql_connection
                    
                    mysql_conn, error = get_mysql_connection(
                        username=db_config['DB_USERNAME'],
                        password=db_config['DB_PASSWORD'] or '',
                        host=db_config['DB_HOST'],
                        port=db_config['DB_PORT'],
                        database=db_config['DB_NAME']
                    )
                    
                    if error:
                        return jsonify({
                            'success': False,
                            'message': f'MySQL connection error: {error}'
                        })
                    
                    # Add LIMIT clause if not present
                    if 'LIMIT' not in query.upper():
                        if query.strip().endswith(';'):
                            query = query[:-1] + ' LIMIT 10;'
                        else:
                            query = query + ' LIMIT 10;'
                    
                    mysql_cursor = mysql_conn.cursor(dictionary=True)
                    mysql_cursor.execute(query)
                    results = mysql_cursor.fetchall()
                    
                    # Get column names
                    columns = list(results[0].keys()) if results else []
                    
                    mysql_cursor.close()
                    mysql_conn.close()
                    
                    return jsonify({
                        'success': True,
                        'message': f'Query executed successfully on {db_config["ENV_NAME"]} - {db_config["DB_DISPLAY_NAME"]} ({len(results)} rows)',
                        'columns': columns,
                        'data': results
                    })
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'message': f'MySQL error: {str(e)}'
                    })
            
            else:
                return jsonify({
                    'success': False,
                    'message': f'Database type {db_config["DB_TYPE"]} not supported for testing'
                })

        # Default: Execute on internal database
        if 'LIMIT' not in query.upper():
            if query.strip().endswith(';'):
                query = query[:-1] + ' LIMIT 10;'
            else:
                query = query + ' LIMIT 10;'

        results = query_db(query)
        
        if results:
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

@tables_bp.route('/add_table', methods=['POST'])
def add_table():
    """Add a new table"""
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_TABLES (TABLE_NAME, TABLE_TYPE, QUERY, DESCRIPTION) VALUES (?, ?, ?, ?)',
            (data['tableName'], data['tableType'], data.get('query', ''), data.get('description', ''))
        )
        return jsonify({'success': True, 'message': 'Table added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@tables_bp.route('/update_table', methods=['PUT'])
def update_table():
    """Update an existing table"""
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_TABLES SET TABLE_NAME = ?, TABLE_TYPE = ?, QUERY = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GEC_ID = ?',
            (data['tableName'], data['tableType'], data.get('query', ''), data.get('description', ''), datetime.now(), data['gecId'])
        )
        return jsonify({'success': True, 'message': 'Table updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@tables_bp.route('/delete_table/<int:gec_id>', methods=['DELETE'])
def delete_table(gec_id):
    """Delete a table"""
    try:
        modify_db('DELETE FROM GEE_TABLES WHERE GEC_ID = ?', (gec_id,))
        return jsonify({'success': True, 'message': 'Table deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@tables_bp.route('/import_table_structure', methods=['POST'])
def import_table_structure():
    """Import table structure from external database"""
    data = request.json
    connection_handle = data.get('connection_handle')
    table_name = data.get('table_name')
    
    if not connection_handle or not table_name:
        return jsonify({'success': False, 'message': 'Connection handle and table name are required'})
    
    try:
        # Get the database config from the active connection
        active_conn = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?',
                              (connection_handle,), one=True)
        
        if not active_conn or not active_conn['DB_CONFIG_ID']:
            return jsonify({'success': False, 'message': 'Invalid connection handle'})
        
        # Get database configuration
        db_config = query_db('''SELECT dc.*, e.ENV_NAME 
                               FROM GEE_DATABASE_CONFIGS dc 
                               JOIN GEE_ENVIRONMENTS e ON e.ENV_ID = dc.ENV_ID 
                               WHERE dc.DB_CONFIG_ID = ?''',
                            (active_conn['DB_CONFIG_ID'],), one=True)
        
        if not db_config:
            return jsonify({'success': False, 'message': 'Database configuration not found'})
        
        if db_config['DB_TYPE'] == 'SQLite':
            try:
                ext_conn = sqlite3.connect(db_config['DB_NAME'])
                cursor = ext_conn.cursor()
                
                # Get table info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                cursor.close()
                ext_conn.close()
                
                if not columns:
                    return jsonify({
                        'success': False,
                        'message': f'Table {table_name} not found or no access'
                    })
                
                # Create a query to fetch data
                query = f'SELECT * FROM "{table_name}"'
                
                # Store in GEE_TABLES
                modify_db(
                    'INSERT INTO GEE_TABLES (TABLE_NAME, TABLE_TYPE, QUERY, DESCRIPTION) VALUES (?, ?, ?, ?)',
                    (table_name, 'I', query, f"Imported from {db_config['ENV_NAME']} - {db_config['DB_DISPLAY_NAME']}")
                )
                
                return jsonify({
                    'success': True,
                    'message': f'Table structure imported successfully for {table_name}',
                    'columns': [{'name': col[1], 'type': col[2]} for col in columns]
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error importing SQLite table structure: {str(e)}'
                })
        
        elif db_config['DB_TYPE'] == 'Oracle':
            try:
                from oracle_helpers import get_oracle_connection
                
                username = db_config['DB_USERNAME']
                password = db_config['DB_PASSWORD'] or ''
                host = db_config['DB_HOST']
                port = db_config['DB_PORT']
                oracle_conn_type = db_config.get('ORACLE_CONN_TYPE', 'service')
                instance_value = db_config['DB_INSTANCE']
                
                if oracle_conn_type == 'sid':
                    oracle_conn, error = get_oracle_connection(
                        username=username, password=password, host=host, port=port,
                        service_name=None, sid=instance_value
                    )
                else:
                    oracle_conn, error = get_oracle_connection(
                        username=username, password=password, host=host, port=port,
                        service_name=instance_value, sid=None
                    )
                
                if error:
                    return jsonify({
                        'success': False,
                        'message': f'Oracle connection error: {error}'
                    })
                
                oracle_cursor = oracle_conn.cursor()
                
                # Get table columns
                oracle_cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, NULLABLE
                    FROM USER_TAB_COLUMNS 
                    WHERE TABLE_NAME = :table_name
                    ORDER BY COLUMN_ID
                """, {'table_name': table_name.upper()})
                
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
                    (table_name, 'I', query, f"Imported from Oracle - {db_config['ENV_NAME']} - {db_config['DB_DISPLAY_NAME']}")
                )
                
                oracle_cursor.close()
                oracle_conn.close()
                
                return jsonify({
                    'success': True,
                    'message': f'Table structure imported successfully for {table_name}',
                    'columns': [{'name': col[0], 'type': col[1]} for col in columns]
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error importing Oracle table structure: {str(e)}'
                })
        
        elif db_config['DB_TYPE'] == 'MySQL':
            try:
                from mysql_helpers import get_mysql_connection
                
                mysql_conn, error = get_mysql_connection(
                    username=db_config['DB_USERNAME'],
                    password=db_config['DB_PASSWORD'] or '',
                    host=db_config['DB_HOST'],
                    port=db_config['DB_PORT'],
                    database=db_config['DB_NAME']
                )
                
                if error:
                    return jsonify({
                        'success': False,
                        'message': f'MySQL connection error: {error}'
                    })
                
                mysql_cursor = mysql_conn.cursor()
                
                # Get table structure from information_schema
                mysql_cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (db_config['DB_NAME'], table_name))
                
                columns = mysql_cursor.fetchall()
                
                if not columns:
                    mysql_cursor.close()
                    mysql_conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'Table {table_name} not found or no access'
                    })
                
                # Create a query to fetch data
                query = f'SELECT * FROM `{table_name}`'
                
                # Store in GEE_TABLES
                modify_db(
                    'INSERT INTO GEE_TABLES (TABLE_NAME, TABLE_TYPE, QUERY, DESCRIPTION) VALUES (?, ?, ?, ?)',
                    (table_name, 'I', query, f"Imported from MySQL - {db_config['ENV_NAME']} - {db_config['DB_DISPLAY_NAME']}")
                )
                
                mysql_cursor.close()
                mysql_conn.close()
                
                return jsonify({
                    'success': True,
                    'message': f'Table structure imported successfully for {table_name}',
                    'columns': [{'name': col[0], 'type': col[1]} for col in columns]
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error importing MySQL table structure: {str(e)}'
                })
        
        else:
            return jsonify({'success': False, 'message': f'Database type {db_config["DB_TYPE"]} not supported yet'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error importing table structure: {str(e)}'})