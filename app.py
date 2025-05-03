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
        with open('schema.sql', 'r') as f:
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

if __name__ == '__main__':
    init_app()
    app.run(debug=True)