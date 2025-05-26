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
    classes = query_db('SELECT * FROM GEE_FIELD_CLASSES')
    return jsonify([dict(cls) for cls in classes])

@classes_bp.route('/add_class', methods=['POST'])
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

@classes_bp.route('/update_class', methods=['PUT'])
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
        
        # Parse the Swagger file
        swagger_data = parser.parse_file(file_content, file_type)
        
        # Validate the file
        is_valid, errors = parser.validate_swagger_file()
        if not is_valid:
            return jsonify({'success': False, 'message': 'Invalid Swagger file: ' + ', '.join(errors)})
        
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
        
        # Create main field class from API info
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
        
        # Add input fields
        input_fields = swagger_data.get('input_fields', [])
        for field in input_fields:
            modify_db(
                'INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DEFAULT_VALUE, GF_DESCRIPTION) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    main_class_id,
                    f"input_{field['name']}",
                    field['type'],
                    field.get('size'),
                    field.get('precision'),
                    field.get('default_value'),
                    f"Input: {field.get('description', field['name'])}"
                )
            )
            stats['fields_created'] += 1
        
        # Add output fields
        output_fields = swagger_data.get('output_fields', [])
        for field in output_fields:
            modify_db(
                'INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DEFAULT_VALUE, GF_DESCRIPTION) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    main_class_id,
                    f"output_{field['name']}",
                    field['type'],
                    field.get('size'),
                    field.get('precision'),
                    field.get('default_value'),
                    f"Output: {field.get('description', field['name'])}"
                )
            )
            stats['fields_created'] += 1
        
        # Create additional field classes for complex schemas if they don't exist
        field_classes = swagger_data.get('field_classes', [])
        for fc in field_classes:
            # Skip if this is the main class we already created
            if fc['name'] == class_name:
                continue
                
            fc_name = f"{class_name}_{fc['name']}"
            existing_fc = query_db(
                'SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = ?', 
                (fc_name,), one=True
            )
            
            if not existing_fc:
                fc_id = modify_db(
                    'INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION) VALUES (?, ?, ?)',
                    (fc_name, fc['type'], fc['description']),
                    get_lastrowid=True
                )
                stats['classes_created'] += 1
                
                # Add fields for this class
                for field in fc['fields']:
                    modify_db(
                        'INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DEFAULT_VALUE, GF_DESCRIPTION) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (
                            fc_id,
                            field['name'],
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
