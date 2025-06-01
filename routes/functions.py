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
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str)
    
    # Base query for counting total records
    count_query = '''
        SELECT COUNT(*) as total
        FROM GEE_BASE_FUNCTIONS gbf
    '''
    
    # Base query for fetching records
    base_query = '''
        SELECT 
            gbf.*,
            COALESCE(param_count.actual_count, 0) as ACTUAL_PARAM_COUNT
        FROM GEE_BASE_FUNCTIONS gbf
        LEFT JOIN (
            SELECT GBF_ID, COUNT(*) as actual_count 
            FROM GEE_BASE_FUNCTIONS_PARAMS 
            GROUP BY GBF_ID
        ) param_count ON gbf.GBF_ID = param_count.GBF_ID
    '''
    
    # Build WHERE clause and parameters
    params = []
    where_clause = ''
    
    if search:
        where_clause = ' WHERE gbf.FUNC_NAME LIKE ? OR gbf.FUNC_DESCRIPTION LIKE ? OR gbf.FUNC_TYPE LIKE ?'
        search_param = f'%{search}%'
        params = [search_param, search_param, search_param]
    
    # Get total count
    total_query = count_query + where_clause
    total_result = query_db(total_query, params, one=True)
    total = total_result['total'] if total_result else 0
    
    # Calculate pagination
    offset = (page - 1) * per_page
    total_pages = (total + per_page - 1) // per_page
    
    # Fetch paginated data
    data_query = base_query + where_clause + '''
        ORDER BY gbf.FUNC_NAME
        LIMIT ? OFFSET ?
    '''
    
    functions = query_db(data_query, params + [per_page, offset])
    
    # Update the PARAM_COUNT with actual count and convert to dict
    result = []
    for func in functions:
        func_dict = dict(func)
        func_dict['PARAM_COUNT'] = func_dict['ACTUAL_PARAM_COUNT']
        del func_dict['ACTUAL_PARAM_COUNT']
        result.append(func_dict)
    
    return jsonify({
        'data': result,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    })

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
            'INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES (?, ?, ?)',
            (data['functionName'], data['paramCount'], data.get('description', ''))
        )
        return jsonify({'success': True, 'message': 'Function added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@functions_bp.route('/update_function', methods=['PUT'])
def update_function():
    data = request.json
    try:
        modify_db(
            'UPDATE GEE_BASE_FUNCTIONS SET FUNC_NAME = ?, PARAM_COUNT = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GBF_ID = ?',
            (data['functionName'], data['paramCount'], data.get('description', ''), datetime.now(), data['functionId'])
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
            
        # Delete function parameters first (foreign key constraint)
        modify_db('DELETE FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBF_ID = ?', (function_id,))
        # Then delete the function
        modify_db('DELETE FROM GEE_BASE_FUNCTIONS WHERE GBF_ID = ?', (function_id,))
        return jsonify({'success': True, 'message': 'Function deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Function Parameters Routes
@functions_bp.route('/get_function_parameters/<int:function_id>')
def get_function_parameters(function_id):
    """Get all parameters for a function"""
    try:
        parameters = query_db('''
            SELECT * FROM GEE_BASE_FUNCTIONS_PARAMS 
            WHERE GBF_ID = ? 
            ORDER BY GBF_SEQ
        ''', (function_id,))
        return jsonify([dict(param) for param in parameters])
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@functions_bp.route('/add_function_parameter', methods=['POST'])
def add_function_parameter():
    """Add a new parameter to a function"""
    data = request.json
    try:
        modify_db('''
            INSERT INTO GEE_BASE_FUNCTIONS_PARAMS 
            (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, PARAM_IO_TYPE, DESCRIPTION) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['gbfId'], 
            data['sequence'], 
            data['paramName'], 
            data['paramType'], 
            data.get('paramIOType', 'INPUT'),
            data.get('description', '')
        ))
        return jsonify({'success': True, 'message': 'Parameter added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@functions_bp.route('/update_function_parameter', methods=['PUT'])
def update_function_parameter():
    """Update an existing function parameter"""
    data = request.json
    try:
        modify_db('''
            UPDATE GEE_BASE_FUNCTIONS_PARAMS 
            SET PARAM_NAME = ?, PARAM_TYPE = ?, PARAM_IO_TYPE = ?, GBF_SEQ = ?, DESCRIPTION = ?, UPDATE_DATE = ?
            WHERE GBFP_ID = ?
        ''', (
            data['paramName'], 
            data['paramType'], 
            data.get('paramIOType', 'INPUT'),
            data['sequence'], 
            data.get('description', ''), 
            datetime.now(), 
            data['gbfpId']
        ))
        return jsonify({'success': True, 'message': 'Parameter updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@functions_bp.route('/delete_function_parameter/<int:parameter_id>', methods=['DELETE'])
def delete_function_parameter(parameter_id):
    """Delete a function parameter"""
    try:
        modify_db('DELETE FROM GEE_BASE_FUNCTIONS_PARAMS WHERE GBFP_ID = ?', (parameter_id,))
        return jsonify({'success': True, 'message': 'Parameter deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@functions_bp.route('/get_function_with_parameters/<int:function_id>')
def get_function_with_parameters(function_id):
    """Get function details along with its parameters"""
    try:
        # Get function details
        function = query_db('SELECT * FROM GEE_BASE_FUNCTIONS WHERE GBF_ID = ?', (function_id,), one=True)
        
        if not function:
            return jsonify({"error": "Function not found"}), 404
        
        # Get function parameters
        parameters = query_db('''
            SELECT * FROM GEE_BASE_FUNCTIONS_PARAMS 
            WHERE GBF_ID = ? 
            ORDER BY GBF_SEQ
        ''', (function_id,))
        
        result = dict(function)
        result['parameters'] = [dict(param) for param in parameters]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})