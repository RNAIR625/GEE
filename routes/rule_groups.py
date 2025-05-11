from flask import Blueprint, request, jsonify, render_template, g
from db_helpers import get_db, query_db, modify_db
from datetime import datetime

rule_groups_bp = Blueprint('rule_groups', __name__)

@rule_groups_bp.route('/')
def rule_groups_page():
    return render_template('rule_groups.html', active_page='rule_groups')

@rule_groups_bp.route('/get_rule_groups', methods=['GET'])
def get_rule_groups():
    try:
        db = get_db()
        rule_groups = query_db("""
            SELECT GRG_ID, GROUP_NAME, COND_TYPE, GRG_ID_PARENT, DESCRIPTION, 
                  COND_GRG_ID_START, ACT_GRG_ID_START, CREATE_DATE, UPDATE_DATE
            FROM GRG_RULE_GROUPS
            ORDER BY UPDATE_DATE DESC
        """)
        
        # Handle case when no rule groups exist yet
        if rule_groups is None:
            return jsonify([])
            
        return jsonify(rule_groups)
    except Exception as e:
        print(f"Error fetching rule groups: {str(e)}")
        return jsonify({"error": str(e)}), 500

@rule_groups_bp.route('/add_rule_group', methods=['POST'])
def add_rule_group():
    try:
        data = request.json
        
        # Extract data from request
        group_name = data.get('groupName')
        cond_type = data.get('condType')
        parent_group_id = data.get('parentGroupId')
        description = data.get('description')
        is_condition = data.get('isCondition', False)
        is_action = data.get('isAction', False)
        rules = data.get('rules', [])
        
        # Validate required fields
        if not group_name:
            return jsonify({"success": False, "message": "Group name is required"}), 400
            
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Insert new rule group
        grg_id = modify_db("""
            INSERT INTO GRG_RULE_GROUPS 
            (GROUP_NAME, COND_TYPE, GRG_ID_PARENT, DESCRIPTION, 
             COND_GRG_ID_START, ACT_GRG_ID_START, CREATE_DATE, UPDATE_DATE)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            group_name, 
            cond_type, 
            parent_group_id, 
            description, 
            1 if is_condition else 0, 
            1 if is_action else 0, 
            current_time, 
            current_time
        ), get_lastrowid=True)
        
        # Add rules if provided
        if rules and len(rules) > 0:
            for rule in rules:
                modify_db("""
                    INSERT INTO GRG_RULE_GROUP_RULES 
                    (GRG_ID, RULE_ID, SEQUENCE)
                    VALUES (?, ?, ?)
                """, (grg_id, rule.get('id'), rule.get('sequence')))
        
        return jsonify({"success": True, "message": "Rule group added successfully", "id": grg_id})
    except Exception as e:
        print(f"Error adding rule group: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@rule_groups_bp.route('/update_rule_group', methods=['PUT'])
def update_rule_group():
    try:
        data = request.json
        
        # Extract data from request
        grg_id = data.get('grgId')
        group_name = data.get('groupName')
        cond_type = data.get('condType')
        parent_group_id = data.get('parentGroupId')
        description = data.get('description')
        is_condition = data.get('isCondition', False)
        is_action = data.get('isAction', False)
        rules = data.get('rules', [])
        
        # Validate required fields
        if not grg_id:
            return jsonify({"success": False, "message": "Group ID is required"}), 400
            
        if not group_name:
            return jsonify({"success": False, "message": "Group name is required"}), 400
            
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update rule group
        modify_db("""
            UPDATE GRG_RULE_GROUPS 
            SET GROUP_NAME = ?, 
                COND_TYPE = ?, 
                GRG_ID_PARENT = ?, 
                DESCRIPTION = ?, 
                COND_GRG_ID_START = ?, 
                ACT_GRG_ID_START = ?, 
                UPDATE_DATE = ?
            WHERE GRG_ID = ?
        """, (
            group_name, 
            cond_type, 
            parent_group_id, 
            description, 
            1 if is_condition else 0, 
            1 if is_action else 0, 
            current_time, 
            grg_id
        ))
        
        # Delete existing rules for this group
        modify_db("DELETE FROM GRG_RULE_GROUP_RULES WHERE GRG_ID = ?", (grg_id,))
        
        # Add updated rules
        if rules and len(rules) > 0:
            for rule in rules:
                modify_db("""
                    INSERT INTO GRG_RULE_GROUP_RULES 
                    (GRG_ID, RULE_ID, SEQUENCE)
                    VALUES (?, ?, ?)
                """, (grg_id, rule.get('id'), rule.get('sequence')))
        
        return jsonify({"success": True, "message": "Rule group updated successfully"})
    except Exception as e:
        print(f"Error updating rule group: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@rule_groups_bp.route('/delete_rule_group/<int:grg_id>', methods=['DELETE'])
def delete_rule_group(grg_id):
    try:
        # Check if group exists
        group = query_db("SELECT GRG_ID FROM GRG_RULE_GROUPS WHERE GRG_ID = ?", (grg_id,), one=True)
        if not group:
            return jsonify({"success": False, "message": "Rule group not found"}), 404
            
        # Delete rule group rules
        modify_db("DELETE FROM GRG_RULE_GROUP_RULES WHERE GRG_ID = ?", (grg_id,))
        
        # Delete rule group
        modify_db("DELETE FROM GRG_RULE_GROUPS WHERE GRG_ID = ?", (grg_id,))
        
        return jsonify({"success": True, "message": "Rule group deleted successfully"})
    except Exception as e:
        print(f"Error deleting rule group: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

# Get rules for selection modal
@rule_groups_bp.route('/get_rules', methods=['GET'])
def get_rules():
    try:
        # This would typically fetch rules from a database
        # For demonstration, returning sample data
        rules = [
            {"id": 1, "name": "Validate Email Format"},
            {"id": 2, "name": "Check Required Fields"},
            {"id": 3, "name": "Calculate Total Amount"},
            {"id": 4, "name": "Format Phone Number"},
            {"id": 5, "name": "Verify Address"}
        ]
        return jsonify(rules)
    except Exception as e:
        print(f"Error fetching rules: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Get rules assigned to a group
@rule_groups_bp.route('/get_assigned_rules/<int:grg_id>', methods=['GET'])
def get_assigned_rules(grg_id):
    try:
        db = get_db()
        rules = query_db("""
            SELECT r.RULE_ID as id, r.RULE_NAME as name, gr.SEQUENCE as sequence
            FROM GRG_RULES r
            JOIN GRG_RULE_GROUP_RULES gr ON r.RULE_ID = gr.RULE_ID
            WHERE gr.GRG_ID = ?
            ORDER BY gr.SEQUENCE
        """, (grg_id,))
        
        # Handle case when no rules are assigned
        if rules is None:
            return jsonify([])
            
        return jsonify(rules)
    except Exception as e:
        print(f"Error fetching assigned rules: {str(e)}")
        return jsonify({"error": str(e)}), 500