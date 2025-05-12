from flask import Blueprint, request, jsonify, render_template
from db_helpers import get_db, query_db, modify_db
from datetime import datetime
import json

rules_bp = Blueprint('rules', __name__)

@rules_bp.route('/')
def rules_page():
    return render_template('rules.html', active_page='rules')

@rules_bp.route('/get_rules', methods=['GET'])
def get_rules():
    try:
        db = get_db()
        rules = query_db("""
            SELECT RULE_ID, RULE_NAME, GFC_ID, RULE_TYPE, DESCRIPTION, 
                   CONDITION_CODE, ACTION_CODE, CREATE_DATE, UPDATE_DATE
            FROM GEE_RULES
            ORDER BY UPDATE_DATE DESC
        """)
        
        # Handle case when no rules exist yet
        if rules is None:
            return jsonify([])
            
        return jsonify(rules)
    except Exception as e:
        print(f"Error fetching rules: {str(e)}")
        return jsonify({"error": str(e)}), 500

@rules_bp.route('/add_rule', methods=['POST'])
def add_rule():
    try:
        data = request.json
        
        # Extract data from request
        rule_name = data.get('ruleName')
        class_id = data.get('classId') or None
        rule_type = data.get('ruleType')
        description = data.get('description')
        condition_code = data.get('conditionCode')
        action_code = data.get('actionCode')
        
        # Validate required fields
        if not rule_name:
            return jsonify({"success": False, "message": "Rule name is required"}), 400
            
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Insert new rule
        rule_id = modify_db("""
            INSERT INTO GEE_RULES 
            (RULE_NAME, GFC_ID, RULE_TYPE, DESCRIPTION, CONDITION_CODE, ACTION_CODE, CREATE_DATE, UPDATE_DATE)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule_name, 
            class_id, 
            rule_type, 
            description, 
            condition_code, 
            action_code, 
            current_time, 
            current_time
        ), get_lastrowid=True)
        
        return jsonify({"success": True, "message": "Rule added successfully", "id": rule_id})
    except Exception as e:
        print(f"Error adding rule: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@rules_bp.route('/update_rule', methods=['PUT'])
def update_rule():
    try:
        data = request.json
        
        # Extract data from request
        rule_id = data.get('ruleId')
        rule_name = data.get('ruleName')
        class_id = data.get('classId') or None
        rule_type = data.get('ruleType')
        description = data.get('description')
        condition_code = data.get('conditionCode')
        action_code = data.get('actionCode')
        
        # Validate required fields
        if not rule_id:
            return jsonify({"success": False, "message": "Rule ID is required"}), 400
            
        if not rule_name:
            return jsonify({"success": False, "message": "Rule name is required"}), 400
            
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update rule
        modify_db("""
            UPDATE GEE_RULES 
            SET RULE_NAME = ?, 
                GFC_ID = ?, 
                RULE_TYPE = ?, 
                DESCRIPTION = ?, 
                CONDITION_CODE = ?, 
                ACTION_CODE = ?, 
                UPDATE_DATE = ?
            WHERE RULE_ID = ?
        """, (
            rule_name, 
            class_id, 
            rule_type, 
            description, 
            condition_code, 
            action_code, 
            current_time, 
            rule_id
        ))
        
        return jsonify({"success": True, "message": "Rule updated successfully"})
    except Exception as e:
        print(f"Error updating rule: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@rules_bp.route('/delete_rule/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    try:
        # Check if rule exists
        rule = query_db("SELECT RULE_ID FROM GEE_RULES WHERE RULE_ID = ?", (rule_id,), one=True)
        if not rule:
            return jsonify({"success": False, "message": "Rule not found"}), 404
            
        # Check if rule is used in rule groups
        rule_usages = query_db("SELECT COUNT(*) as count FROM GRG_RULE_GROUP_RULES WHERE RULE_ID = ?", (rule_id,), one=True)
        
        if rule_usages and rule_usages['count'] > 0:
            return jsonify({"success": False, "message": "Cannot delete rule: It is being used in rule groups"}), 400
            
        # Delete rule
        modify_db("DELETE FROM GEE_RULES WHERE RULE_ID = ?", (rule_id,))
        
        return jsonify({"success": True, "message": "Rule deleted successfully"})
    except Exception as e:
        print(f"Error deleting rule: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@rules_bp.route('/test_code', methods=['POST'])
def test_code():
    """Test rule code execution with sample data"""
    try:
        data = request.json
        code = data.get('code', '')
        code_type = data.get('type', 'condition')
        
        if not code:
            return jsonify({"success": False, "error": "No code provided"})
        
        # Create a safe testing environment (this would be more complex in a real implementation)
        # In a real system, you would use a sandboxed execution environment
        
        # Mock data for testing
        mock_data = {
            "fields": {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com",
                "age": 30,
                "amount": 100.50
            },
            "tables": {
                "customers": [
                    {"id": 1, "name": "John Doe", "email": "john@example.com"},
                    {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
                ]
            },
            "functions": {
                "validateEmail": lambda email: "@" in email and "." in email.split("@")[1],
                "calculateTotal": lambda amount, tax: amount * (1 + tax/100),
                "formatName": lambda first, last: f"{first} {last}"
            }
        }
        
        # In a real system, you would evaluate this safely, possibly on the server side
        # This is a simplified example - in production, you'd use a proper sandboxed environment
        result = {"success": True, "result": "Code would execute here with mock data"}
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
