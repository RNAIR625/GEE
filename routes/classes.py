from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename
from db_helpers import query_db, modify_db
from swagger_parser import SwaggerParser

# Create a Blueprint for class routes
classes_bp = Blueprint('classes', __name__)

@classes_bp.route('/')
def class_page():
    return render_template('class.html', active_page='class')

@classes_bp.route('/get_classes')
def get_classes():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str)
    
    # Base query for counting total records
    count_query = '''
        SELECT COUNT(*) as total
        FROM GEE_FIELD_CLASSES gfc
        LEFT JOIN GEE_FIELD_CLASSES parent ON gfc.PARENT_GFC_ID = parent.GFC_ID
    '''
    
    # Base query for fetching records
    base_query = '''
        SELECT 
            gfc.*,
            parent.FIELD_CLASS_NAME as PARENT_CLASS_NAME,
            (SELECT COUNT(*) FROM GEE_FIELD_CLASSES child WHERE child.PARENT_GFC_ID = gfc.GFC_ID) as CHILD_COUNT
        FROM GEE_FIELD_CLASSES gfc
        LEFT JOIN GEE_FIELD_CLASSES parent ON gfc.PARENT_GFC_ID = parent.GFC_ID
    '''
    
    # Add search filter if provided
    params = []
    where_clause = ''
    if search:
        where_clause = ' WHERE gfc.FIELD_CLASS_NAME LIKE ? OR gfc.CLASS_TYPE LIKE ? OR gfc.DESCRIPTION LIKE ?'
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
        ORDER BY 
            CASE WHEN gfc.PARENT_GFC_ID IS NULL THEN gfc.GFC_ID ELSE gfc.PARENT_GFC_ID END,
            gfc.PARENT_GFC_ID IS NOT NULL,
            gfc.FIELD_CLASS_NAME
        LIMIT ? OFFSET ?
    '''
    
    classes = query_db(data_query, params + [per_page, offset])
    
    return jsonify({
        'data': [dict(cls) for cls in classes],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    })

@classes_bp.route('/add_class', methods=['POST'])
def add_class():
    data = request.json
    try:
        parent_id = data.get('parentGfcId') if data.get('parentGfcId') else None
        modify_db(
            'INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION, PARENT_GFC_ID) VALUES (?, ?, ?, ?)',
            (data['className'], data['type'], data['description'], parent_id)
        )
        return jsonify({'success': True, 'message': 'Class added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@classes_bp.route('/update_class', methods=['PUT'])
def update_class():
    data = request.json
    try:
        parent_id = data.get('parentGfcId') if data.get('parentGfcId') else None
        modify_db(
            'UPDATE GEE_FIELD_CLASSES SET FIELD_CLASS_NAME = ?, CLASS_TYPE = ?, DESCRIPTION = ?, PARENT_GFC_ID = ?, UPDATE_DATE = ? WHERE GFC_ID = ?',
            (data['className'], data['type'], data['description'], parent_id, datetime.now(), data['gfcId'])
        )
        return jsonify({'success': True, 'message': 'Class updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@classes_bp.route('/delete_class/<int:gfc_id>', methods=['DELETE'])
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

@classes_bp.route('/get_class_deletion_info/<int:gfc_id>', methods=['GET'])
def get_class_deletion_info(gfc_id):
    """Get information about what will be deleted when removing a field class"""
    try:
        # Get field class information
        field_class = query_db('''
            SELECT fc.*, parent.FIELD_CLASS_NAME as PARENT_CLASS_NAME
            FROM GEE_FIELD_CLASSES fc
            LEFT JOIN GEE_FIELD_CLASSES parent ON fc.PARENT_GFC_ID = parent.GFC_ID
            WHERE fc.GFC_ID = ?
        ''', (gfc_id,), one=True)
        
        if not field_class:
            return jsonify({'success': False, 'message': 'Field class not found'})
        
        # Get associated fields
        fields = query_db('''
            SELECT GF_ID, GF_NAME, GF_TYPE, GF_DESCRIPTION
            FROM GEE_FIELDS 
            WHERE GFC_ID = ?
            ORDER BY GF_NAME
        ''', (gfc_id,))
        
        # Get child classes
        child_classes = query_db('''
            SELECT GFC_ID, FIELD_CLASS_NAME, CLASS_TYPE,
                   (SELECT COUNT(*) FROM GEE_FIELDS WHERE GFC_ID = fc.GFC_ID) as FIELD_COUNT
            FROM GEE_FIELD_CLASSES fc
            WHERE PARENT_GFC_ID = ?
            ORDER BY FIELD_CLASS_NAME
        ''', (gfc_id,))
        
        # Calculate total fields that will be deleted (including from child classes)
        total_fields = len(fields) if fields else 0
        child_fields_total = 0
        
        for child in (child_classes or []):
            child_fields_total += child['FIELD_COUNT']
        
        total_fields += child_fields_total
        
        # Get rules that might be using this class
        rules_using_class = query_db('''
            SELECT r.RULE_ID, r.RULE_NAME, r.RULE_TYPE
            FROM GEE_RULES r
            WHERE r.GFC_ID = ?
            ORDER BY r.RULE_NAME
        ''', (gfc_id,))
        
        deletion_info = {
            'success': True,
            'field_class': dict(field_class),
            'fields': [dict(field) for field in fields] if fields else [],
            'child_classes': [dict(child) for child in child_classes] if child_classes else [],
            'rules_using_class': [dict(rule) for rule in rules_using_class] if rules_using_class else [],
            'totals': {
                'fields_count': len(fields) if fields else 0,
                'child_classes_count': len(child_classes) if child_classes else 0,
                'child_fields_count': child_fields_total,
                'total_fields_count': total_fields,
                'rules_using_count': len(rules_using_class) if rules_using_class else 0
            }
        }
        
        return jsonify(deletion_info)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@classes_bp.route('/delete_class_with_fields/<int:gfc_id>', methods=['DELETE'])
def delete_class_with_fields(gfc_id):
    """Delete a field class along with all its associated fields and child classes"""
    try:
        # Get field class information for confirmation
        field_class = query_db('''
            SELECT FIELD_CLASS_NAME, CLASS_TYPE
            FROM GEE_FIELD_CLASSES
            WHERE GFC_ID = ?
        ''', (gfc_id,), one=True)
        
        if not field_class:
            return jsonify({'success': False, 'message': 'Field class not found'})
        
        # Start transaction-like deletion (SQLite autocommit, but we'll track what we delete)
        deleted_items = {
            'fields': 0,
            'child_fields': 0,
            'child_classes': 0,
            'rules': 0
        }
        
        # First, recursively delete child classes and their fields
        child_classes = query_db('''
            SELECT GFC_ID, FIELD_CLASS_NAME
            FROM GEE_FIELD_CLASSES
            WHERE PARENT_GFC_ID = ?
        ''', (gfc_id,))
        
        for child in (child_classes or []):
            # Delete fields of child class
            child_fields_count = query_db('''
                SELECT COUNT(*) as count FROM GEE_FIELDS WHERE GFC_ID = ?
            ''', (child['GFC_ID'],), one=True)
            
            if child_fields_count and child_fields_count['count'] > 0:
                modify_db('DELETE FROM GEE_FIELDS WHERE GFC_ID = ?', (child['GFC_ID'],))
                deleted_items['child_fields'] += child_fields_count['count']
            
            # Delete child class
            modify_db('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (child['GFC_ID'],))
            deleted_items['child_classes'] += 1
        
        # Delete rules that use this class (set GFC_ID to NULL or delete if required)
        rules_using_class = query_db('''
            SELECT COUNT(*) as count FROM GEE_RULES WHERE GFC_ID = ?
        ''', (gfc_id,), one=True)
        
        if rules_using_class and rules_using_class['count'] > 0:
            # Set GFC_ID to NULL instead of deleting rules
            modify_db('UPDATE GEE_RULES SET GFC_ID = NULL WHERE GFC_ID = ?', (gfc_id,))
            deleted_items['rules'] = rules_using_class['count']
        
        # Delete fields of the main class
        fields_count = query_db('''
            SELECT COUNT(*) as count FROM GEE_FIELDS WHERE GFC_ID = ?
        ''', (gfc_id,), one=True)
        
        if fields_count and fields_count['count'] > 0:
            modify_db('DELETE FROM GEE_FIELDS WHERE GFC_ID = ?', (gfc_id,))
            deleted_items['fields'] = fields_count['count']
        
        # Finally, delete the main field class
        modify_db('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (gfc_id,))
        
        # Create summary message
        summary_parts = []
        if deleted_items['fields'] > 0:
            summary_parts.append(f"{deleted_items['fields']} field(s)")
        if deleted_items['child_classes'] > 0:
            summary_parts.append(f"{deleted_items['child_classes']} child class(es)")
        if deleted_items['child_fields'] > 0:
            summary_parts.append(f"{deleted_items['child_fields']} child field(s)")
        if deleted_items['rules'] > 0:
            summary_parts.append(f"{deleted_items['rules']} rule(s) unlinked")
        
        summary_message = f"Field class '{field_class['FIELD_CLASS_NAME']}' deleted successfully"
        if summary_parts:
            summary_message += f" along with {', '.join(summary_parts)}"
        
        return jsonify({
            'success': True, 
            'message': summary_message,
            'deleted_items': deleted_items
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@classes_bp.route('/get_swagger_files')
def get_swagger_files():
    """Get list of available Swagger files from temp directory"""
    try:
        swagger_files = []
        temp_dir = 'temp'
        
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if filename.lower().endswith(('.json', '.yaml', '.yml')):
                    file_path = os.path.join(temp_dir, filename)
                    swagger_files.append({
                        'name': filename,
                        'path': file_path
                    })
        
        return jsonify({'success': True, 'files': swagger_files})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'files': []})

@classes_bp.route('/parse_swagger', methods=['POST'])
def parse_swagger():
    """Parse a Swagger file and extract field definitions"""
    try:
        parser = SwaggerParser()
        
        # Check if file was uploaded or existing file selected
        if 'swagger_file' in request.files:
            file = request.files['swagger_file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'})
            
            # Read file content
            file_content = file.read().decode('utf-8')
            file_type = 'json' if file.filename.lower().endswith('.json') else 'yaml'
            
        elif 'existing_file_path' in request.form:
            file_path = request.form['existing_file_path']
            if not os.path.exists(file_path):
                return jsonify({'success': False, 'message': 'File not found'})
            
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            file_type = 'json' if file_path.lower().endswith('.json') else 'yaml'
            
        else:
            return jsonify({'success': False, 'message': 'No file provided'})
        
        # Check if file_content is valid
        if not file_content or file_content.strip() == '':
            return jsonify({'success': False, 'message': 'File is empty or could not be read'})
        
        # Parse the Swagger file
        try:
            swagger_data = parser.parse_file(file_content, file_type)
            if not swagger_data:
                return jsonify({'success': False, 'message': 'Failed to parse file content - file may be corrupted or invalid'})
        except Exception as parse_error:
            return jsonify({'success': False, 'message': f'Error parsing file: {str(parse_error)}'})
        
        # Validate the file
        try:
            is_valid, errors = parser.validate_swagger_file()
            if not is_valid:
                return jsonify({'success': False, 'message': 'Invalid Swagger file: ' + ', '.join(errors)})
        except Exception as validation_error:
            return jsonify({'success': False, 'message': f'Error validating file: {str(validation_error)}'})
        
        # Extract field classes and fields
        field_classes = parser.extract_field_classes_and_fields()
        
        # Extract API info
        api_info = {
            'title': swagger_data.get('info', {}).get('title', 'Unknown API'),
            'description': swagger_data.get('info', {}).get('description', ''),
            'version': swagger_data.get('info', {}).get('version', '1.0.0')
        }
        
        # Group fields into input and output based on schema names/types
        input_fields = []
        output_fields = []
        
        for class_name, class_def in field_classes.items():
            for field in class_def['fields']:
                field_copy = field.copy()
                field_copy['class_name'] = class_name
                
                # Determine if it's input or output based on class name/type
                if ('request' in class_name.lower() or 
                    'input' in class_name.lower() or 
                    class_def['type'] == 'REQUEST'):
                    input_fields.append(field_copy)
                elif ('response' in class_name.lower() or 
                      'output' in class_name.lower() or 
                      class_def['type'] == 'RESPONSE'):
                    output_fields.append(field_copy)
                else:
                    # Default to input for ambiguous fields
                    input_fields.append(field_copy)
        
        # Generate suggested class name
        suggested_name = api_info['title'].replace(' API', '').replace(' ', '_').replace('-', '_')
        suggested_name = ''.join(c for c in suggested_name if c.isalnum() or c == '_') or 'ImportedAPI'
        
        result = {
            'success': True,
            'api_info': api_info,
            'field_classes': list(field_classes.values()),
            'input_fields': input_fields,
            'output_fields': output_fields,
            'suggested_class_name': suggested_name
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error parsing Swagger file: {str(e)}'})

@classes_bp.route('/import_swagger', methods=['POST'])
def import_swagger():
    """Import field classes and fields from parsed Swagger data"""
    try:
        data = request.json
        class_name = data.get('class_name')
        cleanup_existing = data.get('cleanup_existing', False)
        swagger_data = data.get('swagger_data')
        
        if not class_name or not swagger_data:
            return jsonify({'success': False, 'message': 'Missing required data'})
        
        stats = {
            'classes_created': 0,
            'fields_created': 0,
            'classes_updated': 0,
            'fields_deleted': 0
        }
        
        # Clean up existing class and fields if requested
        if cleanup_existing:
            # Check if class exists
            existing_class = query_db(
                'SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = ?', 
                (class_name,), one=True
            )
            
            if existing_class:
                # Delete fields first (due to foreign key constraint)
                modify_db('DELETE FROM GEE_FIELDS WHERE GFC_ID = ?', (existing_class['GFC_ID'],))
                
                # Count deleted fields for stats
                deleted_count = query_db(
                    'SELECT COUNT(*) as count FROM GEE_FIELDS WHERE GFC_ID = ?', 
                    (existing_class['GFC_ID'],), one=True
                )
                stats['fields_deleted'] = deleted_count['count'] if deleted_count else 0
                
                # Delete the class
                modify_db('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (existing_class['GFC_ID'],))
        
        # Create main field class from API info (summary only - no fields)
        api_info = swagger_data.get('api_info', {})
        main_class_description = f"API: {api_info.get('title', 'Unknown')} - {api_info.get('description', '')}"
        
        # Check if main class already exists
        existing_main_class = query_db(
            'SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = ?', 
            (class_name,), one=True
        )
        
        if existing_main_class:
            main_class_id = existing_main_class['GFC_ID']
            stats['classes_updated'] += 1
        else:
            main_class_id = modify_db(
                'INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION) VALUES (?, ?, ?)',
                (class_name, 'API', main_class_description),
                get_lastrowid=True
            )
            stats['classes_created'] += 1
        
        # Create schema-specific field classes as children of the main API class
        field_classes = swagger_data.get('field_classes', [])
        for fc in field_classes:
            # Create class name with schema suffix
            fc_name = f"{class_name}_{fc['name']}"
            existing_fc = query_db(
                'SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = ?', 
                (fc_name,), one=True
            )
            
            if not existing_fc:
                # Set the parent_id to the main API class for REQUEST/RESPONSE/ERROR classes
                parent_id = main_class_id if fc['type'] in ['REQUEST', 'RESPONSE', 'ERROR'] else None
                
                fc_id = modify_db(
                    'INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION, PARENT_GFC_ID) VALUES (?, ?, ?, ?)',
                    (fc_name, fc['type'], fc['description'], parent_id),
                    get_lastrowid=True
                )
                stats['classes_created'] += 1
                
                # Add fields for this specific schema class only
                for field in fc['fields']:
                    modify_db(
                        'INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DEFAULT_VALUE, GF_DESCRIPTION) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (
                            fc_id,
                            field['name'],  # Use original field name, not prefixed
                            field['type'],
                            field.get('size'),
                            field.get('precision'),
                            field.get('default_value'),
                            field.get('description', field['name'])
                        )
                    )
                    stats['fields_created'] += 1
        
        return jsonify({
            'success': True, 
            'message': 'Swagger import completed successfully',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Import failed: {str(e)}'})

@classes_bp.route('/bulk_delete_classes', methods=['DELETE'])
def bulk_delete_classes():
    """Delete multiple field classes"""
    try:
        data = request.json
        class_ids = data.get('class_ids', [])
        
        if not class_ids:
            return jsonify({'success': False, 'message': 'No class IDs provided'})
        
        deleted_count = 0
        skipped_count = 0
        errors = []
        
        for class_id in class_ids:
            try:
                # Check if fields are using this class
                fields = query_db('SELECT COUNT(*) as count FROM GEE_FIELDS WHERE GFC_ID = ?', (class_id,), one=True)
                if fields and fields['count'] > 0:
                    skipped_count += 1
                    continue
                
                # Check if class exists
                existing_class = query_db('SELECT FIELD_CLASS_NAME FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (class_id,), one=True)
                if not existing_class:
                    skipped_count += 1
                    continue
                
                # Delete the class
                modify_db('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (class_id,))
                deleted_count += 1
                
            except Exception as e:
                errors.append(f"Error deleting class {class_id}: {str(e)}")
                skipped_count += 1
        
        message = f'Bulk delete completed. Deleted: {deleted_count}, Skipped: {skipped_count}'
        if errors:
            message += f'. Errors: {len(errors)}'
        
        return jsonify({
            'success': True, 
            'message': message,
            'deleted_count': deleted_count,
            'skipped_count': skipped_count,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Bulk delete failed: {str(e)}'})