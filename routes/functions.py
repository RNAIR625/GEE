from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from db_helpers import query_db, modify_db

# Create a Blueprint for functions routes
functions_bp = Blueprint('functions', __name__)

@functions_bp.route('/')
def functions_page():
    return render_template('function.html', active_page='function')

@functions_bp.route('/get_functions')
def get_functions():
    functions = query_db('''
        SELECT * FROM GEE_BASE_FUNCTIONS 
        ORDER BY FUNC_NAME
    ''')
    return jsonify([dict(func) for func in functions])

@functions_bp.route('/get_function/<int:function_id>')
def get_function(function_id):
    function = query_db('SELECT * FROM GEE_BASE_FUNCTIONS WHERE GBF_ID = ?', (function_id,), one=True)
    
    if not function:
        return jsonify({"error": "Function not found"}), 404
    
    return jsonify(dict(function))

@functions_bp.route('/add_function', methods=['POST'])
def add_function():
    data = request.json
    try:
        modify_db(
            'INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION, RETURN_TYPE) VALUES (?, ?, ?, ?)',
            (data['functionName'], data['paramCount'], data.get('description', ''), data.get('returnType', 'void'))
        )
        return jsonify({'success': True, 'message': 'Function added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@functions_bp.route('/update_function', methods=['PUT'])
def update_function():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_BASE_FUNCTIONS SET FUNC_NAME = ?, PARAM_COUNT = ?, DESCRIPTION = ?, RETURN_TYPE = ?, UPDATE_DATE = ? WHERE GBF_ID = ?',
            (data['functionName'], data['paramCount'], data.get('description', ''), data.get('returnType', 'void'), datetime.now(), data['functionId'])
        )
        return jsonify({'success': True, 'message': 'Function updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@functions_bp.route('/delete_function/<int:function_id>', methods=['DELETE'])
def delete_function(function_id):
    try:
        # Check if the function is used in any rules
        rule_lines = query_db('''
            SELECT COUNT(*) as count 
            FROM GEE_RULE_LINES 
            WHERE FUNCTION_ID = ?
        ''', (function_id,), one=True)
        
        if rule_lines and rule_lines['count'] > 0:
            return jsonify({
                'success': False, 
                'message': 'Cannot delete function: It is being used in one or more rules'
            })
            
        modify_db('DELETE FROM GEE_BASE_FUNCTIONS WHERE GBF_ID = ?', (function_id,))
        return jsonify({'success': True, 'message': 'Function deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})