from flask import Blueprint, render_template, request, jsonify
from flask_restx import Api, Resource, fields as restx_fields
from datetime import datetime
from db_helpers import query_db, modify_db
from swagger_parser import SwaggerParser
import json

# Create a Blueprint for class routes
classes_bp = Blueprint('classes', __name__)

# Create API instance for Swagger documentation
api = Api(classes_bp, doc='/swagger/', title='Field Classes API', 
          description='API for managing field classes with Swagger support',
          prefix='/api')

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


# Swagger API endpoints for Field Classes
field_class_model = api.model('FieldClass', {
    'GFC_ID': restx_fields.Integer(description='Field Class ID'),
    'FIELD_CLASS_NAME': restx_fields.String(required=True, description='Field class name'),
    'CLASS_TYPE': restx_fields.String(required=True, description='Type of the class'),
    'DESCRIPTION': restx_fields.String(description='Description of the field class'),
    'CREATE_DATE': restx_fields.DateTime(description='Creation timestamp'),
    'UPDATE_DATE': restx_fields.DateTime(description='Last update timestamp')
})

field_class_input = api.model('FieldClassInput', {
    'FIELD_CLASS_NAME': restx_fields.String(required=True, description='Field class name'),
    'CLASS_TYPE': restx_fields.String(required=True, description='Type of the class'),
    'DESCRIPTION': restx_fields.String(description='Description of the field class')
})

@api.route('/classes')
class FieldClassesSwaggerAPI(Resource):
    @api.marshal_list_with(field_class_model)
    def get(self):
        """Get all field classes"""
        classes = query_db('SELECT * FROM GEE_FIELD_CLASSES')
        return [dict(cls) for cls in classes]
    
    @api.expect(field_class_input)
    @api.marshal_with(field_class_model, code=201)
    def post(self):
        """Create a new field class"""
        data = request.json
        try:
            cursor = modify_db(
                'INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION) VALUES (?, ?, ?)',
                (data['FIELD_CLASS_NAME'], data['CLASS_TYPE'], data.get('DESCRIPTION', ''))
            )
            
            # Get the newly created class
            new_class = query_db('SELECT * FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (cursor.lastrowid,), one=True)
            return dict(new_class), 201
        except Exception as e:
            api.abort(400, f'Error creating field class: {str(e)}')


@api.route('/classes/<int:gfc_id>')
class FieldClassSwaggerAPI(Resource):
    @api.marshal_with(field_class_model)
    def get(self, gfc_id):
        """Get a specific field class by ID"""
        cls = query_db('SELECT * FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (gfc_id,), one=True)
        if not cls:
            api.abort(404, 'Field class not found')
        return dict(cls)
    
    @api.expect(field_class_input)
    @api.marshal_with(field_class_model)
    def put(self, gfc_id):
        """Update a field class"""
        data = request.json
        try:
            modify_db(
                'UPDATE GEE_FIELD_CLASSES SET FIELD_CLASS_NAME = ?, CLASS_TYPE = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GFC_ID = ?',
                (data['FIELD_CLASS_NAME'], data['CLASS_TYPE'], data.get('DESCRIPTION', ''), datetime.now(), gfc_id)
            )
            
            # Get the updated class
            updated_class = query_db('SELECT * FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (gfc_id,), one=True)
            if not updated_class:
                api.abort(404, 'Field class not found')
            return dict(updated_class)
        except Exception as e:
            api.abort(400, f'Error updating field class: {str(e)}')
    
    def delete(self, gfc_id):
        """Delete a field class"""
        try:
            # Check if fields are using this class
            fields = query_db('SELECT COUNT(*) as count FROM GEE_FIELDS WHERE GFC_ID = ?', (gfc_id,), one=True)
            if fields['count'] > 0:
                api.abort(400, 'Cannot delete: Class is being used by fields')
            
            modify_db('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (gfc_id,))
            return {'message': 'Field class deleted successfully'}, 200
        except Exception as e:
            api.abort(400, f'Error deleting field class: {str(e)}')


# Swagger Import Models
swagger_import_model = api.model('SwaggerImport', {
    'file_content': restx_fields.String(required=True, description='Swagger file content (JSON or YAML)'),
    'file_type': restx_fields.String(required=True, description='File type: json or yaml', enum=['json', 'yaml']),
    'target_class_name': restx_fields.String(description='Specific field class to sync (optional)'),
    'sync_mode': restx_fields.String(required=True, description='Sync mode', 
                                   enum=['preview', 'execute'], default='preview')
})

swagger_sync_result = api.model('SwaggerSyncResult', {
    'success': restx_fields.Boolean(description='Whether operation was successful'),
    'operations': restx_fields.Raw(description='Operations performed or to be performed'),
    'summary': restx_fields.Raw(description='Summary of changes'),
    'errors': restx_fields.List(restx_fields.String, description='Any error messages')
})


@api.route('/swagger-import')
class SwaggerImportAPI(Resource):
    @api.expect(swagger_import_model)
    @api.marshal_with(swagger_sync_result)
    def post(self):
        """Import Swagger file and sync field classes and fields"""
        data = request.json
        
        try:
            # Parse Swagger file
            parser = SwaggerParser()
            parser.parse_file(data['file_content'], data['file_type'])
            
            # Validate Swagger file
            is_valid, validation_errors = parser.validate_swagger_file()
            if not is_valid:
                return {
                    'success': False,
                    'errors': validation_errors,
                    'operations': {},
                    'summary': {}
                }, 400
            
            # Extract field classes and fields
            extracted_models = parser.extract_field_classes_and_fields()
            
            if not extracted_models:
                return {
                    'success': False,
                    'errors': ['No field classes found in Swagger file'],
                    'operations': {},
                    'summary': {}
                }, 400
            
            # Get existing field classes
            existing_classes = [dict(row) for row in query_db('SELECT * FROM GEE_FIELD_CLASSES')]
            
            # Get sync operations
            operations = parser.get_field_class_sync_operations(
                existing_classes, 
                data.get('target_class_name')
            )
            
            # Preview mode - just return what would be done
            if data.get('sync_mode', 'preview') == 'preview':
                summary = {
                    'extracted_models': len(extracted_models),
                    'field_classes_to_insert': len(operations['field_classes']['insert']),
                    'field_classes_to_update': len(operations['field_classes']['update']),
                    'field_classes_to_delete': len(operations['field_classes']['delete']),
                    'total_fields': sum(len(fc['fields']) for fc in extracted_models.values())
                }
                
                return {
                    'success': True,
                    'operations': operations,
                    'summary': summary,
                    'errors': []
                }
            
            # Execute mode - perform the operations
            elif data.get('sync_mode') == 'execute':
                execution_result = self._execute_sync_operations(operations, extracted_models)
                return execution_result
                
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Error processing Swagger file: {str(e)}'],
                'operations': {},
                'summary': {}
            }, 500
    
    def _execute_sync_operations(self, operations, extracted_models):
        """Execute the field class and field sync operations"""
        executed_operations = {
            'field_classes_inserted': 0,
            'field_classes_updated': 0,
            'field_classes_deleted': 0,
            'fields_inserted': 0,
            'fields_updated': 0,
            'fields_deleted': 0
        }
        errors = []
        
        try:
            # Insert new field classes
            for class_op in operations['field_classes']['insert']:
                try:
                    cursor = modify_db(
                        'INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION) VALUES (?, ?, ?)',
                        (class_op['name'], class_op['type'], class_op['description'])
                    )
                    
                    new_class_id = cursor.lastrowid
                    executed_operations['field_classes_inserted'] += 1
                    
                    # Insert fields for this class
                    for field in class_op['fields']:
                        try:
                            modify_db(
                                'INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DEFAULT_VALUE, GF_DESCRIPTION) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                (new_class_id, field['name'], field['type'], field['size'], 
                                 field['precision'], field['default_value'], field['description'])
                            )
                            executed_operations['fields_inserted'] += 1
                        except Exception as e:
                            errors.append(f"Error inserting field '{field['name']}': {str(e)}")
                            
                except Exception as e:
                    errors.append(f"Error inserting field class '{class_op['name']}': {str(e)}")
            
            # Update existing field classes
            for class_op in operations['field_classes']['update']:
                try:
                    modify_db(
                        'UPDATE GEE_FIELD_CLASSES SET CLASS_TYPE = ?, DESCRIPTION = ?, UPDATE_DATE = ? WHERE GFC_ID = ?',
                        (class_op['type'], class_op['description'], datetime.now(), class_op['gfc_id'])
                    )
                    executed_operations['field_classes_updated'] += 1
                    
                    # Sync fields for this class
                    self._sync_fields_for_class(class_op['gfc_id'], class_op['name'], 
                                              extracted_models, executed_operations, errors)
                    
                except Exception as e:
                    errors.append(f"Error updating field class '{class_op['name']}': {str(e)}")
            
            # Delete field classes (only if no target class specified)
            for class_op in operations['field_classes']['delete']:
                try:
                    # First delete all fields
                    modify_db('DELETE FROM GEE_FIELDS WHERE GFC_ID = ?', (class_op['gfc_id'],))
                    
                    # Then delete the class
                    modify_db('DELETE FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (class_op['gfc_id'],))
                    executed_operations['field_classes_deleted'] += 1
                    
                except Exception as e:
                    errors.append(f"Error deleting field class '{class_op['name']}': {str(e)}")
            
            summary = {
                'operations_executed': executed_operations,
                'total_errors': len(errors),
                'success_rate': f"{((sum(executed_operations.values()) - len(errors)) / max(sum(executed_operations.values()), 1)) * 100:.1f}%"
            }
            
            return {
                'success': len(errors) == 0,
                'operations': executed_operations,
                'summary': summary,
                'errors': errors
            }
            
        except Exception as e:
            errors.append(f"Critical error during execution: {str(e)}")
            return {
                'success': False,
                'operations': executed_operations,
                'summary': {'critical_error': str(e)},
                'errors': errors
            }
    
    def _sync_fields_for_class(self, class_id, class_name, extracted_models, executed_operations, errors):
        """Sync fields for a specific field class"""
        if class_name not in extracted_models:
            return
        
        # Get existing fields for this class
        existing_fields = [dict(row) for row in query_db(
            'SELECT * FROM GEE_FIELDS WHERE GFC_ID = ?', (class_id,)
        )]
        existing_fields_map = {field['GF_NAME']: field for field in existing_fields}
        
        swagger_fields = extracted_models[class_name]['fields']
        swagger_fields_map = {field['name']: field for field in swagger_fields}
        
        # Insert new fields
        for field_name, field_def in swagger_fields_map.items():
            if field_name not in existing_fields_map:
                try:
                    modify_db(
                        'INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DEFAULT_VALUE, GF_DESCRIPTION) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (class_id, field_def['name'], field_def['type'], field_def['size'],
                         field_def['precision'], field_def['default_value'], field_def['description'])
                    )
                    executed_operations['fields_inserted'] += 1
                except Exception as e:
                    errors.append(f"Error inserting field '{field_name}' in class '{class_name}': {str(e)}")
        
        # Update existing fields
        for field_name, field_def in swagger_fields_map.items():
            if field_name in existing_fields_map:
                existing_field = existing_fields_map[field_name]
                if (existing_field['GF_TYPE'] != field_def['type'] or
                    existing_field['GF_DESCRIPTION'] != field_def['description'] or
                    existing_field['GF_SIZE'] != field_def['size']):
                    try:
                        modify_db(
                            'UPDATE GEE_FIELDS SET GF_TYPE = ?, GF_SIZE = ?, GF_PRECISION_SIZE = ?, GF_DEFAULT_VALUE = ?, GF_DESCRIPTION = ?, UPDATE_DATE = ? WHERE GF_ID = ?',
                            (field_def['type'], field_def['size'], field_def['precision'],
                             field_def['default_value'], field_def['description'], datetime.now(), existing_field['GF_ID'])
                        )
                        executed_operations['fields_updated'] += 1
                    except Exception as e:
                        errors.append(f"Error updating field '{field_name}' in class '{class_name}': {str(e)}")
        
        # Delete fields not in Swagger
        for field_name in existing_fields_map:
            if field_name not in swagger_fields_map:
                try:
                    modify_db('DELETE FROM GEE_FIELDS WHERE GF_ID = ?', (existing_fields_map[field_name]['GF_ID'],))
                    executed_operations['fields_deleted'] += 1
                except Exception as e:
                    errors.append(f"Error deleting field '{field_name}' from class '{class_name}': {str(e)}")


@api.route('/swagger-export/<int:gfc_id>')
class SwaggerExportAPI(Resource):
    def get(self, gfc_id):
        """Export field class as Swagger schema"""
        try:
            # Get field class
            field_class = query_db('SELECT * FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (gfc_id,), one=True)
            if not field_class:
                api.abort(404, 'Field class not found')
            
            # Get fields for this class
            fields = query_db('SELECT * FROM GEE_FIELDS WHERE GFC_ID = ?', (gfc_id,))
            
            # Generate Swagger schema
            swagger_schema = self._generate_swagger_schema(dict(field_class), [dict(field) for field in fields])
            
            return {
                'field_class': field_class['FIELD_CLASS_NAME'],
                'swagger_schema': swagger_schema
            }
            
        except Exception as e:
            api.abort(500, f'Error exporting field class: {str(e)}')
    
    def _generate_swagger_schema(self, field_class, fields):
        """Generate Swagger schema from field class and fields"""
        properties = {}
        required = []
        
        for field in fields:
            prop_def = self._db_field_to_swagger_property(field)
            properties[field['GF_NAME']] = prop_def
            
            # Assume required if no default value
            if not field['GF_DEFAULT_VALUE']:
                required.append(field['GF_NAME'])
        
        schema = {
            'type': 'object',
            'description': field_class['DESCRIPTION'],
            'properties': properties
        }
        
        if required:
            schema['required'] = required
        
        return schema
    
    def _db_field_to_swagger_property(self, field):
        """Convert database field to Swagger property definition"""
        db_type = field['GF_TYPE'].upper()
        
        prop = {
            'description': field.get('GF_DESCRIPTION', field['GF_NAME'])
        }
        
        if field['GF_DEFAULT_VALUE']:
            try:
                # Try to parse as appropriate type
                if db_type in ['INTEGER', 'BIGINT']:
                    prop['default'] = int(field['GF_DEFAULT_VALUE'])
                elif db_type in ['FLOAT', 'DOUBLE', 'DECIMAL']:
                    prop['default'] = float(field['GF_DEFAULT_VALUE'])
                elif db_type == 'BOOLEAN':
                    prop['default'] = field['GF_DEFAULT_VALUE'].lower() in ['true', '1', 'yes']
                else:
                    prop['default'] = field['GF_DEFAULT_VALUE']
            except (ValueError, TypeError):
                prop['default'] = field['GF_DEFAULT_VALUE']
        
        # Map database types to Swagger types
        if db_type in ['TEXT', 'VARCHAR']:
            prop['type'] = 'string'
            if field['GF_SIZE']:
                prop['maxLength'] = field['GF_SIZE']
        elif db_type in ['INTEGER', 'BIGINT']:
            prop['type'] = 'integer'
            if db_type == 'BIGINT':
                prop['format'] = 'int64'
        elif db_type in ['FLOAT', 'DOUBLE']:
            prop['type'] = 'number'
            prop['format'] = 'float' if db_type == 'FLOAT' else 'double'
        elif db_type == 'DECIMAL':
            prop['type'] = 'number'
        elif db_type == 'BOOLEAN':
            prop['type'] = 'boolean'
        elif db_type == 'DATE':
            prop['type'] = 'string'
            prop['format'] = 'date'
        elif db_type == 'DATETIME':
            prop['type'] = 'string'
            prop['format'] = 'date-time'
        elif db_type == 'JSON':
            prop['type'] = 'object'
        else:
            prop['type'] = 'string'
        
        return prop
