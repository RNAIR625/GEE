from flask import Blueprint, request, jsonify, render_template
from db_helpers import get_db, query_db, modify_db
from datetime import datetime
import json

flow_designer_bp = Blueprint('flow_designer', __name__)

@flow_designer_bp.route('/')
def flow_designer_page():
    return render_template('flow_designer.html', active_page='flow_designer')

# Get components for the palette

@flow_designer_bp.route('/get_palette_rule_groups', methods=['GET'])
def get_palette_rule_groups():
    try:
        db = get_db()
        rule_groups = query_db("""
            SELECT GRG_ID as id, GROUP_NAME as name, COND_TYPE, DESCRIPTION
            FROM GRG_RULE_GROUPS
            ORDER BY GROUP_NAME ASC
        """)
        
        if rule_groups is None:
            return jsonify([])
        
        rule_groups_list = [dict(group) for group in rule_groups]
        return jsonify(rule_groups_list)
    except Exception as e:
        print(f"Error fetching palette rule groups: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Flow management endpoints
@flow_designer_bp.route('/save_flow', methods=['POST'])
def save_flow():
    try:
        data = request.json
        
        flow_name = data.get('flowName')
        description = data.get('description', '')
        version = data.get('version', 1)
        user = data.get('user', 'admin')
        comments = data.get('comments', '')
        nodes = data.get('nodes', [])
        connections = data.get('connections', [])
        flow_id = data.get('flowId')
        
        if not flow_name:
            return jsonify({"success": False, "message": "Flow name is required"}), 400
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save or update flow
        if flow_id:
            # Update existing flow
            modify_db("""
                UPDATE GEE_FLOWS 
                SET FLOW_NAME = ?, DESCRIPTION = ?, VERSION = ?, 
                    LAST_EDITED_BY = ?, UPDATE_DATE = ?
                WHERE FLOW_ID = ?
            """, (flow_name, description, version, user, current_time, flow_id))
        else:
            # Create new flow
            flow_id = modify_db("""
                INSERT INTO GEE_FLOWS 
                (FLOW_NAME, DESCRIPTION, VERSION, STATUS, CREATED_BY, LAST_EDITED_BY, CREATE_DATE, UPDATE_DATE)
                VALUES (?, ?, ?, 'DRAFT', ?, ?, ?, ?)
            """, (flow_name, description, version, user, user, current_time, current_time), get_lastrowid=True)
        
        # Save flow version snapshot
        flow_data_json = json.dumps({
            "nodes": nodes,
            "connections": connections
        })
        
        modify_db("""
            INSERT INTO GEE_FLOW_VERSIONS 
            (FLOW_ID, VERSION_NUMBER, FLOW_DATA, CREATED_BY, COMMENTS, CREATE_DATE)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (flow_id, version, flow_data_json, user, comments, current_time))
        
        # Clear existing nodes and connections
        modify_db("DELETE FROM GEE_FLOW_CONNECTIONS WHERE FLOW_ID = ?", (flow_id,))
        modify_db("DELETE FROM GEE_FLOW_NODES WHERE FLOW_ID = ?", (flow_id,))
        
        # Save nodes
        node_id_map = {}
        for node in nodes:
            db_node_id = modify_db("""
                INSERT INTO GEE_FLOW_NODES 
                (FLOW_ID, NODE_TYPE, REFERENCE_ID, POSITION_X, POSITION_Y, 
                 WIDTH, HEIGHT, LABEL, CUSTOM_SETTINGS, CREATE_DATE, UPDATE_DATE)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flow_id, 
                node['type'], 
                node.get('referenceId'), 
                node['x'], 
                node['y'],
                node.get('width', 150), 
                node.get('height', 60),
                node['name'], 
                json.dumps(node.get('settings', {})),
                current_time, 
                current_time
            ), get_lastrowid=True)
            
            node_id_map[node['id']] = db_node_id
        
        # Save connections
        for connection in connections:
            source_db_id = node_id_map.get(connection['sourceId'])
            target_db_id = node_id_map.get(connection['targetId'])
            
            if source_db_id and target_db_id:
                modify_db("""
                    INSERT INTO GEE_FLOW_CONNECTIONS 
                    (FLOW_ID, SOURCE_NODE_ID, TARGET_NODE_ID, CONNECTION_TYPE, 
                     CONDITION_EXPRESSION, LABEL, CREATE_DATE, UPDATE_DATE)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    flow_id,
                    source_db_id,
                    target_db_id,
                    connection.get('type', 'DEFAULT'),
                    connection.get('condition', ''),
                    connection.get('label', ''),
                    current_time,
                    current_time
                ))
        
        return jsonify({
            "success": True, 
            "message": "Flow saved successfully",
            "flowId": flow_id
        })
        
    except Exception as e:
        print(f"Error saving flow: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@flow_designer_bp.route('/get_flow/<int:flow_id>', methods=['GET'])
def get_flow(flow_id):
    try:
        db = get_db()
        
        # Get flow details
        flow = query_db("""
            SELECT FLOW_ID, FLOW_NAME, DESCRIPTION, VERSION, STATUS, 
                   CREATED_BY, LAST_EDITED_BY, CREATE_DATE, UPDATE_DATE
            FROM GEE_FLOWS 
            WHERE FLOW_ID = ?
        """, (flow_id,), one=True)
        
        if not flow:
            return jsonify({"success": False, "message": "Flow not found"}), 404
        
        # Get nodes
        nodes = query_db("""
            SELECT NODE_ID, NODE_TYPE, REFERENCE_ID, POSITION_X, POSITION_Y,
                   WIDTH, HEIGHT, LABEL, CUSTOM_SETTINGS
            FROM GEE_FLOW_NODES 
            WHERE FLOW_ID = ?
            ORDER BY NODE_ID
        """, (flow_id,))
        
        # Get connections
        connections = query_db("""
            SELECT CONNECTION_ID, SOURCE_NODE_ID, TARGET_NODE_ID, CONNECTION_TYPE,
                   CONDITION_EXPRESSION, LABEL
            FROM GEE_FLOW_CONNECTIONS 
            WHERE FLOW_ID = ?
            ORDER BY CONNECTION_ID
        """, (flow_id,))
        
        return jsonify({
            "success": True,
            "flow": dict(flow) if flow else None,
            "nodes": [dict(node) for node in nodes] if nodes else [],
            "connections": [dict(conn) for conn in connections] if connections else []
        })
        
    except Exception as e:
        print(f"Error getting flow: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@flow_designer_bp.route('/get_flows', methods=['GET'])
def get_flows():
    try:
        db = get_db()
        flows = query_db("""
            SELECT FLOW_ID, FLOW_NAME, DESCRIPTION, VERSION, STATUS,
                   CREATED_BY, LAST_EDITED_BY, CREATE_DATE, UPDATE_DATE
            FROM GEE_FLOWS
            ORDER BY UPDATE_DATE DESC
        """)
        
        if flows is None:
            return jsonify([])
        
        flows_list = [dict(flow) for flow in flows]
        return jsonify(flows_list)
        
    except Exception as e:
        print(f"Error fetching flows: {str(e)}")
        return jsonify({"error": str(e)}), 500

@flow_designer_bp.route('/delete_flow/<int:flow_id>', methods=['DELETE'])
def delete_flow(flow_id):
    try:
        # Delete flow and all related data
        modify_db("DELETE FROM GEE_FLOW_CONNECTIONS WHERE FLOW_ID = ?", (flow_id,))
        modify_db("DELETE FROM GEE_FLOW_NODES WHERE FLOW_ID = ?", (flow_id,))
        modify_db("DELETE FROM GEE_FLOW_VERSIONS WHERE FLOW_ID = ?", (flow_id,))
        modify_db("DELETE FROM GEE_FLOWS WHERE FLOW_ID = ?", (flow_id,))
        
        return jsonify({"success": True, "message": "Flow deleted successfully"})
        
    except Exception as e:
        print(f"Error deleting flow: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500