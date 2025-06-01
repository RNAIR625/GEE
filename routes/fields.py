from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from db_helpers import query_db, modify_db

# Create a Blueprint for fields routes
fields_bp = Blueprint('fields', __name__)

@fields_bp.route('/')
def fields_page():
    return render_template('fields.html', active_page='fields')

@fields_bp.route('/get_field_classes')
def get_field_classes():
    classes = query_db('SELECT * FROM GEE_FIELD_CLASSES')
    return jsonify([dict(cls) for cls in classes])

@fields_bp.route('/get_fields')
def get_fields():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str)
    class_filter = request.args.get('class_filter', '', type=str)
    
    # Base query for counting total records
    count_query = '''
        SELECT COUNT(*) as total
        FROM GEE_FIELDS f 
        LEFT JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID
    '''
    
    # Base query for fetching records
    base_query = '''
        SELECT f.*, fc.FIELD_CLASS_NAME, fc.CLASS_TYPE
        FROM GEE_FIELDS f 
        LEFT JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID
    '''
    
    # Build WHERE clause and parameters
    params = []
    where_conditions = []
    
    if search:
        where_conditions.append('(f.GF_NAME LIKE ? OR f.GF_TYPE LIKE ? OR f.GF_DESCRIPTION LIKE ? OR fc.FIELD_CLASS_NAME LIKE ?)')
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param, search_param])
    
    if class_filter:
        where_conditions.append('f.GFC_ID = ?')
        params.append(class_filter)
    
    where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    # Get total count
    total_query = count_query + where_clause
    total_result = query_db(total_query, params, one=True)
    total = total_result['total'] if total_result else 0
    
    # Calculate pagination
    offset = (page - 1) * per_page
    total_pages = (total + per_page - 1) // per_page
    
    # Fetch paginated data
    data_query = base_query + where_clause + '''
        ORDER BY fc.FIELD_CLASS_NAME, f.GF_NAME
        LIMIT ? OFFSET ?
    '''
    
    fields = query_db(data_query, params + [per_page, offset])
    
    return jsonify({
        'data': [dict(field) for field in fields],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    })

@fields_bp.route('/get_fields_by_class/<int:class_id>')
def get_fields_by_class(class_id):
    fields = query_db('SELECT * FROM GEE_FIELDS WHERE GFC_ID = ?', (class_id,))
    return jsonify([dict(field) for field in fields])

@fields_bp.route('/get_child_classes/<int:parent_class_id>')
def get_child_classes(parent_class_id):
    child_classes = query_db('SELECT * FROM GEE_FIELD_CLASSES WHERE PARENT_GFC_ID = ?', (parent_class_id,))
    return jsonify([dict(cls) for cls in child_classes])

@fields_bp.route('/add_field', methods=['POST'])
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

@fields_bp.route('/update_field', methods=['PUT'])
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

@fields_bp.route('/delete_field/<int:gf_id>', methods=['DELETE'])
def delete_field(gf_id):
    try:
        modify_db('DELETE FROM GEE_FIELDS WHERE GF_ID = ?', (gf_id,))
        return jsonify({'success': True, 'message': 'Field deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@fields_bp.route('/bulk_delete_fields', methods=['DELETE'])
def bulk_delete_fields():
    """Delete multiple fields"""
    try:
        data = request.json
        field_ids = data.get('field_ids', [])
        
        if not field_ids:
            return jsonify({'success': False, 'message': 'No field IDs provided'})
        
        deleted_count = 0
        errors = []
        
        for field_id in field_ids:
            try:
                # Check if field exists
                existing_field = query_db('SELECT GF_NAME FROM GEE_FIELDS WHERE GF_ID = ?', (field_id,), one=True)
                if not existing_field:
                    continue
                
                # Delete the field
                modify_db('DELETE FROM GEE_FIELDS WHERE GF_ID = ?', (field_id,))
                deleted_count += 1
                
            except Exception as e:
                errors.append(f"Error deleting field {field_id}: {str(e)}")
        
        message = f'Bulk delete completed. Deleted: {deleted_count} field(s)'
        if errors:
            message += f'. Errors: {len(errors)}'
        
        return jsonify({
            'success': True, 
            'message': message,
            'deleted_count': deleted_count,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Bulk delete failed: {str(e)}'})
