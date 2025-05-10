from flask import Flask, render_template, request, jsonify, g
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__)
DATABASE = 'instance/SLEP.db'

# Database connection helper functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=()):
    conn = get_db()
    conn.execute(query, args)
    conn.commit()

# Ensure instance directory exists
def init_app():
    os.makedirs('instance', exist_ok=True)
    # Create tables if they don't exist
    with app.app_context():
        conn = get_db()
        with open('SQLiteTableCreate.sql', 'r') as f:
            conn.executescript(f.read())
        conn.commit()

# Routes
@app.route('/')
def home():
    return render_template('home.html', active_page='home')

# Class Management
@app.route('/class')
def class_page():
    return render_template('class.html', active_page='class')

@app.route('/get_classes')
def get_classes():
    classes = query_db('SELECT * FROM GEE_FIELD_CLASSES')
    return jsonify([dict(cls) for cls in classes])

@app.route('/add_class', methods=['POST'])
def add_class():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION) VALUES (?, ?, ?)',
            (data['className'], data['type'], data['description'])
        )
        return jsonify({'success': True, 'message': 'Class added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_class', methods=['PUT'])
def update_class():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_FIELD_CLASSES SET FIELD_CLASS_NAME = ?, CLASS_TYPE = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GFC_ID = ?',
            (data['className'], data['type'], data['description'], datetime.now(), data['gfcId'])
        )
        return jsonify({'success': True, 'message': 'Class updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_class/<int:gfc_id>', methods=['DELETE'])
def delete_class(gfc_id):
    try:
        # Check if fields are using this class
        fields = query_db('SELECT COUNT(*) as count FROM GEE_FIELDS WHERE GFC_ID = ?', (gfc_id,), one=True)
        if fields['count'] > 0:
            return jsonify({'success': False, 'message': 'Cannot delete: Class is being used by fields'})
        
        modify_db('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (gfc_id,))
        return jsonify({'success': True, 'message': 'Class deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Fields Management
@app.route('/fields')
def fields():
    return render_template('fields.html', active_page='fields')

@app.route('/get_field_classes')
def get_field_classes():
    classes = query_db('SELECT * FROM GEE_FIELD_CLASSES')
    return jsonify([dict(cls) for cls in classes])

@app.route('/get_fields')
def get_fields():
    fields = query_db('SELECT * FROM GEE_FIELDS')
    return jsonify([dict(field) for field in fields])

@app.route('/add_field', methods=['POST'])
def add_field():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DEFAULT_VALUE, GF_DESCRIPTION) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (data['gfcId'], data['fieldName'], data['type'], data['size'], data['precision'], data['defaultValue'], data['description'])
        )
        return jsonify({'success': True, 'message': 'Field added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_field', methods=['PUT'])
def update_field():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_FIELDS SET GFC_ID = ?, GF_NAME = ?, GF_TYPE = ?, GF_SIZE = ?, GF_PRECISION_SIZE = ?, GF_DEFAULT_VALUE = ?, GF_DESCRIPTION = ?, UPDATE_DATE = ? WHERE GF_ID = ?',
            (data['gfcId'], data['fieldName'], data['type'], data['size'], data['precision'], data['defaultValue'], data['description'], datetime.now(), data['gfId'])
        )
        return jsonify({'success': True, 'message': 'Field updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_field/<int:gf_id>', methods=['DELETE'])
def delete_field(gf_id):
    try:
        modify_db('DELETE FROM GEE_FIELDS WHERE GF_ID = ?', (gf_id,))
        return jsonify({'success': True, 'message': 'Field deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Function Management
@app.route('/function')
def function():
    return render_template('function.html', active_page='function')

@app.route('/get_functions')
def get_functions():
    functions = query_db('SELECT * FROM GEE_BASE_FUNCTIONS')
    return jsonify([dict(func) for func in functions])

@app.route('/add_function', methods=['POST'])
def add_function():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES (?, 0, ?)',
            (data['funcName'], data['description'])
        )
        return jsonify({'success': True, 'message': 'Function added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_function', methods=['PUT'])
def update_function():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_BASE_FUNCTIONS SET FUNC_NAME = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GBF_ID = ?',
            (data['funcName'], data['description'], datetime.now(), data['gbfId'])
        )
        return jsonify({'success': True, 'message': 'Function updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_function/<int:gbf_id>', methods=['DELETE'])
def delete_function(gbf_id):
    try:
        # Delete parameters first
        modify_db('DELETE FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBF_ID = ?', (gbf_id,))
        # Then delete function
        modify_db('DELETE FROM GEE_BASE_FUNCTIONS WHERE GBF_ID = ?', (gbf_id,))
        return jsonify({'success': True, 'message': 'Function and its parameters deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/get_function_params/<int:gbf_id>')
def get_function_params(gbf_id):
    params = query_db('SELECT * FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBF_ID = ? ORDER BY GBF_SEQ', (gbf_id,))
    return jsonify([dict(param) for param in params])

@app.route('/add_param', methods=['POST'])
def add_param():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_BASE_FUNCTIONS_PARAMS (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION) VALUES (?, ?, ?, ?, ?)',
            (data['gbfId'], data['sequence'], data['paramName'], data['paramType'], data['description'])
        )
        # Update parameter count in function
        modify_db(
            'UPDATE GEE_BASE_FUNCTIONS SET PARAM_COUNT = (SELECT COUNT(*) FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBF_ID = ?), UPDATE_DATE = ? WHERE GBF_ID = ?',
            (data['gbfId'], datetime.now(), data['gbfId'])
        )
        return jsonify({'success': True, 'message': 'Parameter added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_param', methods=['PUT'])
def update_param():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_BASE_FUNCTIONS_PARAMS SET GBF_ID = ?, GBF_SEQ = ?, PARAM_NAME = ?, PARAM_TYPE = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GBFP_ID = ?',
            (data['gbfId'], data['sequence'], data['paramName'], data['paramType'], data['description'], datetime.now(), data['gbfpId'])
        )
        return jsonify({'success': True, 'message': 'Parameter updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_param/<int:gbfp_id>', methods=['DELETE'])
def delete_param(gbfp_id):
    try:
        # Get GBF_ID first
        param = query_db('SELECT GBF_ID FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBFP_ID = ?', (gbfp_id,), one=True)
        gbf_id = param['GBF_ID']
        
        # Delete parameter
        modify_db('DELETE FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBFP_ID = ?', (gbfp_id,))
        
        # Update parameter count in function
        modify_db(
            'UPDATE GEE_BASE_FUNCTIONS SET PARAM_COUNT = (SELECT COUNT(*) FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBF_ID = ?), UPDATE_DATE = ? WHERE GBF_ID = ?',
            (gbf_id, datetime.now(), gbf_id)
        )
        return jsonify({'success': True, 'message': 'Parameter deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rules Groups
@app.route('/rule_groups')
def rule_groups():
    return render_template('rule_groups.html', active_page='rule_groups')

@app.route('/get_rule_groups')
def get_rule_groups():
    groups = query_db('SELECT * FROM GEE_RULES_GROUPS')
    return jsonify([dict(group) for group in groups])

@app.route('/add_rule_group', methods=['POST'])
def add_rule_group():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_RULES_GROUPS (GROUP_NAME, COND_TYPE, DESCRIPTION) VALUES (?, ?, ?)',
            (data['groupName'], data['condType'], data['description'])
        )
        return jsonify({'success': True, 'message': 'Rule Group added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_rule_group', methods=['PUT'])
def update_rule_group():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_RULES_GROUPS SET GROUP_NAME = ?, COND_TYPE = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GRG_ID = ?',
            (data['groupName'], data['condType'], data['description'], datetime.now(), data['grgId'])
        )
        return jsonify({'success': True, 'message': 'Rule Group updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_rule_group/<int:grg_id>', methods=['DELETE'])
def delete_rule_group(grg_id):
    try:
        modify_db('DELETE FROM GEE_RULES_GROUPS WHERE GRG_ID = ?', (grg_id,))
        return jsonify({'success': True, 'message': 'Rule Group deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Stations
@app.route('/stations')
def stations():
    return render_template('stations.html', active_page='stations')

@app.route('/get_stations')
def get_stations():
    stations = query_db('SELECT * FROM GEE_STATIONS')
    return jsonify([dict(station) for station in stations])

@app.route('/add_station', methods=['POST'])
def add_station():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_STATIONS (STATION_NAME, DESCRIPTION, STATION_TYPE, ICON, COLOR_CODE) VALUES (?, ?, ?, ?, ?)',
            (data['stationName'], data['description'], data['stationType'], data['icon'], data['colorCode'])
        )
        return jsonify({'success': True, 'message': 'Station added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_station', methods=['PUT'])
def update_station():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_STATIONS SET STATION_NAME = ?, DESCRIPTION = ?, STATION_TYPE = ?, ICON = ?, COLOR_CODE = ?, UPDATE_DATE = ? WHERE STATION_ID = ?',
            (data['stationName'], data['description'], data['stationType'], data['icon'], data['colorCode'], datetime.now(), data['stationId'])
        )
        return jsonify({'success': True, 'message': 'Station updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_station/<int:station_id>', methods=['DELETE'])
def delete_station(station_id):
    try:
        modify_db('DELETE FROM GEE_STATIONS WHERE STATION_ID = ?', (station_id,))
        return jsonify({'success': True, 'message': 'Station deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Flow Designer
@app.route('/flow_designer')
def flow_designer():
    return render_template('flow_designer.html', active_page='flow_designer')

@app.route('/get_flows')
def get_flows():
    flows = query_db('SELECT * FROM GEE_FLOWS')
    return jsonify([dict(flow) for flow in flows])

@app.route('/get_flow/<int:flow_id>')
def get_flow(flow_id):
    # Get flow details
    flow = query_db('SELECT * FROM GEE_FLOWS WHERE FLOW_ID = ?', (flow_id,), one=True)
    
    # Get nodes
    nodes = query_db('SELECT * FROM GEE_FLOW_NODES WHERE FLOW_ID = ?', (flow_id,))
    
    # Get connections
    connections = query_db('SELECT * FROM GEE_FLOW_CONNECTIONS WHERE FLOW_ID = ?', (flow_id,))
    
    return jsonify({
        'flow': dict(flow) if flow else None,
        'nodes': [dict(node) for node in nodes],
        'connections': [dict(conn) for conn in connections]
    })

@app.route('/save_flow', methods=['POST'])
def save_flow():
    data = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if flow exists
        flow = query_db('SELECT * FROM GEE_FLOWS WHERE FLOW_ID = ?', (data['flowId'],), one=True) if 'flowId' in data else None
        
        if flow:
            # Update existing flow
            cursor.execute(
                'UPDATE GEE_FLOWS SET FLOW_NAME = ?, DESCRIPTION = ?, UPDATE_DATE = ?, LAST_EDITED_BY = ? WHERE FLOW_ID = ?',
                (data['flowName'], data['description'], datetime.now(), data['user'], data['flowId'])
            )
            flow_id = data['flowId']
        else:
            # Create new flow
            cursor.execute(
                'INSERT INTO GEE_FLOWS (FLOW_NAME, DESCRIPTION, VERSION, STATUS, CREATED_BY, LAST_EDITED_BY) VALUES (?, ?, 1, "DRAFT", ?, ?)',
                (data['flowName'], data['description'], data['user'], data['user'])
            )
            flow_id = cursor.lastrowid
            
        # Save flow version
        cursor.execute(
            'INSERT INTO GEE_FLOW_VERSIONS (FLOW_ID, VERSION_NUMBER, FLOW_DATA, CREATED_BY, COMMENTS) VALUES (?, ?, ?, ?, ?)',
            (flow_id, data['version'], json.dumps(data['flowData']), data['user'], data['comments'])
        )
        
        # Clear existing nodes and connections for this flow
        cursor.execute('DELETE FROM GEE_FLOW_CONNECTIONS WHERE FLOW_ID = ?', (flow_id,))
        cursor.execute('DELETE FROM GEE_FLOW_NODES WHERE FLOW_ID = ?', (flow_id,))
        
        # Insert nodes
        for node in data['nodes']:
            cursor.execute(
                'INSERT INTO GEE_FLOW_NODES (FLOW_ID, NODE_TYPE, REFERENCE_ID, PARENT_NODE_ID, POSITION_X, POSITION_Y, WIDTH, HEIGHT, LABEL, CUSTOM_SETTINGS) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (flow_id, node['type'], node['referenceId'], node.get('parentNodeId'), node['x'], node['y'], node.get('width'), node.get('height'), node.get('label'), json.dumps(node.get('settings', {})))
            )
            node['dbId'] = cursor.lastrowid
            
        # Insert connections
        for conn in data['connections']:
            source_node_db_id = next((n['dbId'] for n in data['nodes'] if n['id'] == conn['sourceId']), None)
            target_node_db_id = next((n['dbId'] for n in data['nodes'] if n['id'] == conn['targetId']), None)
            
            if source_node_db_id and target_node_db_id:
                cursor.execute(
                    'INSERT INTO GEE_FLOW_CONNECTIONS (FLOW_ID, SOURCE_NODE_ID, TARGET_NODE_ID, CONNECTION_TYPE, CONDITION_EXPRESSION, LABEL, STYLE_SETTINGS) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (flow_id, source_node_db_id, target_node_db_id, conn.get('type', 'DEFAULT'), conn.get('condition'), conn.get('label'), json.dumps(conn.get('style', {})))
                )
                
        conn.commit()
        return jsonify({'success': True, 'message': 'Flow saved successfully!', 'flowId': flow_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Tables Management Starts


# Updated Tables routes and functionality for app.py

@app.route('/tables')
def tables():
    return render_template('tables.html', active_page='tables')

@app.route('/get_tables', methods=['GET'])
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
                    
                    elif env_config['DB_TYPE'] == 'Oracle' or env_config['DB_TYPE'] == 'Postgres':
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
        return jsonify([dict(table) for table in tables])
    
    except Exception as e:
        app.logger.error(f"Error in get_tables: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

@app.route('/get_active_connections_for_tables')
def get_active_connections_for_tables():
    try:
        connections = {}
        active_conns = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS')
        
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
        app.logger.error(f"Error getting active connections: {str(e)}")
        return jsonify({})

@app.route('/add_table', methods=['POST'])
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

@app.route('/update_table', methods=['PUT'])
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

@app.route('/delete_table/<int:gec_id>', methods=['DELETE'])
def delete_table(gec_id):
    try:
        modify_db('DELETE FROM GEE_TABLES WHERE GEC_ID = ?', (gec_id,))
        return jsonify({'success': True, 'message': 'Table deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/test_query', methods=['POST'])
def test_query():
    data = request.json
    query = data.get('query', '')
    conn_handle = data.get('connection_handle', None)
    
    if not query or not query.strip().upper().startswith('SELECT'):
        return jsonify({
            'success': False, 
            'message': 'Only SELECT queries are allowed for testing'
        })
    
    try:
        # If using external connection
        if conn_handle:
            active_conn = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?', 
                                  (conn_handle,), one=True)
            
            if active_conn:
                config_id = active_conn['CONFIG_ID']
                env_config = query_db('SELECT * FROM GEE_ENV_CONFIG WHERE GT_ID = ?', 
                                     (config_id,), one=True)
                
                if env_config and env_config['DB_TYPE'] == 'SQLite':
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
                    
                    ext_conn.close()
                    
                    return jsonify({
                        'success': True, 
                        'message': 'Query executed successfully on external database',
                        'columns': columns,
                        'data': formatted_results
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': f"Connection to {env_config['DB_TYPE'] if env_config else 'unknown'} database not implemented"
                    })
        
        # Default: Execute on internal database
        # Limit the number of rows returned for safety
        if 'LIMIT' not in query.upper():
            if query.strip().endswith(';'):
                query = query[:-1] + ' LIMIT 10;'
            else:
                query = query + ' LIMIT 10;'
                
        results = query_db(query)
        columns = results[0].keys() if results else []
        
        return jsonify({
            'success': True, 
            'message': 'Query executed successfully',
            'columns': list(columns),
            'data': [dict(row) for row in results]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error executing query: {str(e)}'})

@app.route('/import_table_structure', methods=['POST'])
def import_table_structure():
    data = request.json
    conn_handle = data.get('connection_handle')
    table_name = data.get('table_name')
    
    if not conn_handle or not table_name:
        return jsonify({'success': False, 'message': 'Connection handle and table name are required'})
    
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
                (table_name, 'I', query, f'Imported from {env_config["ENV_NAME"]}')
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
            for col in columns:
                column_name = col['name']
                column_type = col['type']
                column_size = len(column_name)  # This is a simplification; in reality, you'd determine proper size
                
                modify_db(
                    'INSERT INTO GEE_TABLE_COLUMNS (GEC_ID, COLUMN_NAME, COLUMN_TYPE, COLUMN_SIZE) VALUES (?, ?, ?, ?)',
                    (new_table['GEC_ID'], column_name, column_type, column_size)
                )
            
            ext_conn.close()
            
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
            
            return jsonify({
                'success': True, 
                'message': f'Table structure imported successfully for {table_name}',
                'columns': column_list
            })
        else:
            return jsonify({'success': False, 'message': f'Database type {env_config["DB_TYPE"]} not supported yet'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error importing table structure: {str(e)}'})
        
        
#Table Management Ends 
# Environment Configuration Management
@app.route('/env_config')
def env_config():
    return render_template('env_config.html', active_page='env_config')

@app.route('/get_env_configs')
def get_env_configs():
    print("get_env_configs route was called!")
    try:
        configs = query_db('SELECT * FROM GEE_ENV_CONFIG')
        print(f"Retrieved {len(configs)} environment configurations")
        result = [dict(config) for config in configs]
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_env_configs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/add_env_config', methods=['POST'])
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

@app.route('/update_env_config', methods=['PUT'])
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

@app.route('/delete_env_config/<int:gt_id>', methods=['DELETE'])
def delete_env_config(gt_id):
    try:
        modify_db('DELETE FROM GEE_ENV_CONFIG WHERE GT_ID = ?', (gt_id,))
        return jsonify({'success': True, 'message': 'Environment configuration deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/test_connection', methods=['POST'])
def test_connection():
    data = request.json
    db_type = data.get('dbType')
    
    try:
        # Simulate connection testing based on database type
        if db_type == 'SQLite':
            # For SQLite, just check if we can open the database
            import sqlite3
            conn = sqlite3.connect(data['dbName'])
            conn.close()
            return jsonify({
                'success': True, 
                'message': 'SQLite connection successful!',
                'handle': f"sqlite_{data['envName'].lower().replace(' ', '_')}"
            })
        
        elif db_type == 'Oracle':
            # For Oracle, we would typically use cx_Oracle
            # This is a simulation for testing
            if data['dbInstance'] and data['dbName'] and data['dbPort']:
                return jsonify({
                    'success': True, 
                    'message': 'Oracle connection successful!',
                    'handle': f"oracle_{data['envName'].lower().replace(' ', '_')}"
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Missing required Oracle connection parameters.'
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

# Store active connection handles
active_connections = {}

# In app.py - This is currently just storing in memory, not the database
@app.route('/store_connection', methods=['POST'])
def store_connection():
    data = request.json
    handle = data.get('handle')
    config_id = data.get('configId')
    
    if not handle or not config_id:
        return jsonify({
            'success': False,
            'message': 'Handle and configuration ID are required'
        })
    
    try:
        # First, check if this handle already exists
        existing = query_db('SELECT * FROM GEE_ACTIVE_CONNECTIONS WHERE HANDLE = ?', 
                           (handle,), one=True)
        
        if existing:
            # Update existing connection
            modify_db(
                'UPDATE GEE_ACTIVE_CONNECTIONS SET CONFIG_ID = ?, STATUS = ?, CREATED = ? WHERE HANDLE = ?',
                (config_id, 'active', datetime.now(), handle)
            )
        else:
            # Insert new connection
            modify_db(
                'INSERT INTO GEE_ACTIVE_CONNECTIONS (HANDLE, CONFIG_ID, CREATED, STATUS) VALUES (?, ?, ?, ?)',
                (handle, config_id, datetime.now(), 'active')
            )
        
        # Also update the in-memory dictionary for fast access
        active_connections[handle] = {
            'config_id': config_id,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'active'
        }
        
        return jsonify({
            'success': True,
            'message': f'Connection handle {handle} stored successfully'
        })
        
    except Exception as e:
        print(f"Error storing connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error storing connection: {str(e)}'
        })onnection handle {handle} stored successfully'
    })

@app.route('/get_active_connections')
def get_active_connections():
    return jsonify(active_connections)


if __name__ == '__main__':
    init_app()
    app.run(debug=True)