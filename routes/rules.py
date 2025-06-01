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
        
        # Convert Row objects to dictionaries for proper JSON serialization
        rules_list = [dict(rule) for rule in rules]
            
        return jsonify(rules_list)
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
            
        # Delete rule lines (enhanced functionality)
        modify_db("""
            DELETE FROM GEE_RULE_LINE_PARAMS 
            WHERE LINE_ID IN (SELECT LINE_ID FROM GEE_RULE_LINES WHERE RULE_ID = ?)
        """, (rule_id,))
        modify_db("DELETE FROM GEE_RULE_LINES WHERE RULE_ID = ?", (rule_id,))
        
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

# New endpoints for structured rule creation

@rules_bp.route('/add_rule_line', methods=['POST'])
def add_rule_line():
    try:
        data = request.json
        
        # Extract data from request
        rule_id = data.get('ruleId')
        function_id = data.get('functionId')
        is_condition = data.get('isCondition', True)
        sequence_num = data.get('sequenceNum', 0)
        parameters = data.get('parameters', [])
        
        # Validate required fields
        if not rule_id or not function_id:
            return jsonify({"success": False, "message": "Rule ID and Function ID are required"}), 400
            
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Insert new rule line
        line_id = modify_db("""
            INSERT INTO GEE_RULE_LINES 
            (RULE_ID, FUNCTION_ID, IS_CONDITION, SEQUENCE_NUM, CREATE_DATE, UPDATE_DATE)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            rule_id, 
            function_id,
            1 if is_condition else 0,
            sequence_num,
            current_time, 
            current_time
        ), get_lastrowid=True)
        
        # Insert parameters
        for i, param in enumerate(parameters):
            field_id = param.get('fieldId')
            literal_value = param.get('literalValue')
            
            modify_db("""
                INSERT INTO GEE_RULE_LINE_PARAMS 
                (LINE_ID, PARAM_INDEX, FIELD_ID, LITERAL_VALUE, CREATE_DATE, UPDATE_DATE)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                line_id,
                i,
                field_id,
                literal_value,
                current_time,
                current_time
            ))
        
        return jsonify({"success": True, "message": "Rule line added successfully", "id": line_id})
    except Exception as e:
        print(f"Error adding rule line: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@rules_bp.route('/get_rule_lines/<int:rule_id>', methods=['GET'])
def get_rule_lines(rule_id):
    try:
        db = get_db()
        lines = query_db("""
            SELECT rl.LINE_ID, rl.SEQUENCE_NUM, rl.FUNCTION_ID, rl.IS_CONDITION,
                   bf.FUNC_NAME, bf.PARAM_COUNT
            FROM GEE_RULE_LINES rl
            JOIN GEE_BASE_FUNCTIONS bf ON rl.FUNCTION_ID = bf.GBF_ID
            WHERE rl.RULE_ID = ?
            ORDER BY rl.IS_CONDITION DESC, rl.SEQUENCE_NUM ASC
        """, (rule_id,))
        
        # Handle case when no lines exist
        if lines is None:
            return jsonify([])
        
        # Convert Row objects to dictionaries
        lines_list = []
        for line in lines:
            line_dict = dict(line)
            # Get parameters for this line
            params = query_db("""
                SELECT rlp.PARAM_ID, rlp.PARAM_INDEX, rlp.FIELD_ID, rlp.LITERAL_VALUE,
                       f.GF_NAME, f.GF_TYPE
                FROM GEE_RULE_LINE_PARAMS rlp
                LEFT JOIN GEE_FIELDS f ON rlp.FIELD_ID = f.GF_ID
                WHERE rlp.LINE_ID = ?
                ORDER BY rlp.PARAM_INDEX ASC
            """, (line['LINE_ID'],))
            
            line_dict['parameters'] = [dict(param) for param in (params or [])]
            lines_list.append(line_dict)
            
        return jsonify(lines_list)
    except Exception as e:
        print(f"Error fetching rule lines: {str(e)}")
        return jsonify({"error": str(e)}), 500

@rules_bp.route('/update_rule_line', methods=['PUT'])
def update_rule_line():
    try:
        data = request.json
        
        # Extract data from request
        line_id = data.get('lineId')
        function_id = data.get('functionId')
        sequence_num = data.get('sequenceNum')
        parameters = data.get('parameters', [])
        
        # Validate required fields
        if not line_id or not function_id:
            return jsonify({"success": False, "message": "Line ID and Function ID are required"}), 400
            
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update rule line
        modify_db("""
            UPDATE GEE_RULE_LINES 
            SET FUNCTION_ID = ?, 
                SEQUENCE_NUM = ?, 
                UPDATE_DATE = ?
            WHERE LINE_ID = ?
        """, (
            function_id, 
            sequence_num, 
            current_time, 
            line_id
        ))
        
        # Delete existing parameters
        modify_db("DELETE FROM GEE_RULE_LINE_PARAMS WHERE LINE_ID = ?", (line_id,))
        
        # Insert updated parameters
        for i, param in enumerate(parameters):
            field_id = param.get('fieldId')
            literal_value = param.get('literalValue')
            
            modify_db("""
                INSERT INTO GEE_RULE_LINE_PARAMS 
                (LINE_ID, PARAM_INDEX, FIELD_ID, LITERAL_VALUE, CREATE_DATE, UPDATE_DATE)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                line_id,
                i,
                field_id,
                literal_value,
                current_time,
                current_time
            ))
        
        return jsonify({"success": True, "message": "Rule line updated successfully"})
    except Exception as e:
        print(f"Error updating rule line: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@rules_bp.route('/delete_rule_line/<int:line_id>', methods=['DELETE'])
def delete_rule_line(line_id):
    try:
        # Delete parameters first (due to foreign key constraint)
        modify_db("DELETE FROM GEE_RULE_LINE_PARAMS WHERE LINE_ID = ?", (line_id,))
        
        # Delete rule line
        modify_db("DELETE FROM GEE_RULE_LINES WHERE LINE_ID = ?", (line_id,))
        
        return jsonify({"success": True, "message": "Rule line deleted successfully"})
    except Exception as e:
        print(f"Error deleting rule line: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@rules_bp.route('/generate_code/<int:rule_id>', methods=['GET'])
def generate_code(rule_id):
    try:
        # Get all rule lines for this rule
        lines = query_db("""
            SELECT rl.LINE_ID, rl.SEQUENCE_NUM, rl.FUNCTION_ID, rl.IS_CONDITION,
                   bf.FUNC_NAME, bf.PARAM_COUNT
            FROM GEE_RULE_LINES rl
            JOIN GEE_BASE_FUNCTIONS bf ON rl.FUNCTION_ID = bf.GBF_ID
            WHERE rl.RULE_ID = ?
            ORDER BY rl.IS_CONDITION DESC, rl.SEQUENCE_NUM ASC
        """, (rule_id,))
        
        if not lines:
            return jsonify({"conditionCode": "", "actionCode": ""})
        
        condition_code = []
        action_code = []
        
        for line in lines:
            # Get parameters for this line
            params = query_db("""
                SELECT rlp.PARAM_ID, rlp.PARAM_INDEX, rlp.FIELD_ID, rlp.LITERAL_VALUE,
                       f.GF_NAME, f.GF_TYPE
                FROM GEE_RULE_LINE_PARAMS rlp
                LEFT JOIN GEE_FIELDS f ON rlp.FIELD_ID = f.GF_ID
                WHERE rlp.LINE_ID = ?
                ORDER BY rlp.PARAM_INDEX ASC
            """, (line['LINE_ID'],))
            
            # Build the function call with parameters
            param_values = []
            for param in params:
                if param['FIELD_ID']:
                    param_values.append(f"fields.{param['GF_NAME']}")
                else:
                    # Handle different types for literal values
                    literal = param['LITERAL_VALUE']
                    if param['GF_TYPE'] == 'STRING':
                        param_values.append(f"'{literal}'")
                    else:
                        param_values.append(literal)
                        
            func_call = f"{line['FUNC_NAME']}({', '.join(param_values)});"
            
            if line['IS_CONDITION']:
                condition_code.append(func_call)
            else:
                action_code.append(func_call)
                
        return jsonify({
            "conditionCode": "\n".join(condition_code),
            "actionCode": "\n".join(action_code)
        })
    except Exception as e:
        print(f"Error generating code: {str(e)}")
        return jsonify({"error": str(e)}), 500
