from flask import Blueprint, render_template, request, jsonify
from flask_restx import Api, Resource, fields as restx_fields
from datetime import datetime
from db_helpers import query_db, modify_db
from swagger_helpers import (
    map_request_to_fields, 
    create_swagger_models_from_fields,
    validate_field_mapping_config
)

# Create a Blueprint for fields routes
fields_bp = Blueprint('fields', __name__)

# Create API instance for Swagger documentation
api = Api(fields_bp, doc='/swagger/', title='Fields API', 
          description='API for managing field classes and fields with Swagger mapping support',
          prefix='/api')

@fields_bp.route('/')
def fields_page():
    return render_template('fields.html', active_page='fields')

@fields_bp.route('/get_field_classes')
def get_field_classes():
    classes = query_db('SELECT * FROM GEE_FIELD_CLASSES')
    return jsonify([dict(cls) for cls in classes])

@fields_bp.route('/get_fields')
def get_fields():
    fields = query_db('SELECT * FROM GEE_FIELDS')
    return jsonify([dict(field) for field in fields])

@fields_bp.route('/get_fields_by_class/<int:class_id>')
def get_fields_by_class(class_id):
    fields = query_db('SELECT * FROM GEE_FIELDS WHERE GFC_ID = ?', (class_id,))
    return jsonify([dict(field) for field in fields])

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


# Swagger API endpoints
@api.route('/field-classes')
class FieldClassesAPI(Resource):
    def get(self):
        """Get all field classes with their fields"""
        classes = query_db('SELECT * FROM GEE_FIELD_CLASSES')
        result = []
        
        for cls in classes:
            cls_dict = dict(cls)
            fields = query_db('SELECT * FROM GEE_FIELDS WHERE GFC_ID = ?', (cls['GFC_ID'],))
            cls_dict['fields'] = [dict(field) for field in fields]
            result.append(cls_dict)
            
        return {'field_classes': result}


@api.route('/field-mapping')
class FieldMappingAPI(Resource):
    field_mapping_model = api.model('FieldMapping', {
        'field_class': restx_fields.String(required=True, description='Field class name'),
        'field_name': restx_fields.String(required=True, description='Field name'),
        'request_path': restx_fields.String(required=True, description='JSONPath to request data')
    })
    
    mapping_request_model = api.model('MappingRequest', {
        'field_mapping': restx_fields.Nested(field_mapping_model, as_list=True),
        'request_data': restx_fields.Raw(description='Sample request data to map')
    })
    
    @api.expect(mapping_request_model)
    def post(self):
        """Map request data to fields based on field mapping configuration"""
        data = request.json
        field_mapping_config = data.get('field_mapping', {})
        request_data = data.get('request_data', {})
        
        # Get field classes and fields data
        field_classes_data = [dict(row) for row in query_db('SELECT * FROM GEE_FIELD_CLASSES')]
        fields_data = [dict(row) for row in query_db('SELECT * FROM GEE_FIELDS')]
        
        # Validate mapping configuration
        is_valid, errors = validate_field_mapping_config(field_mapping_config, field_classes_data, fields_data)
        if not is_valid:
            return {'success': False, 'errors': errors}, 400
        
        # Perform mapping
        try:
            mapped_data = map_request_to_fields(request_data, field_mapping_config, field_classes_data, fields_data)
            return {
                'success': True,
                'mapped_data': mapped_data,
                'mapping_summary': {
                    'total_mappings': len(field_mapping_config),
                    'successful_mappings': len(mapped_data),
                    'failed_mappings': len(field_mapping_config) - len(mapped_data)
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@api.route('/swagger-models')
class SwaggerModelsAPI(Resource):
    def get(self):
        """Generate Swagger models from field definitions"""
        field_classes_data = [dict(row) for row in query_db('SELECT * FROM GEE_FIELD_CLASSES')]
        fields_data = [dict(row) for row in query_db('SELECT * FROM GEE_FIELDS')]
        
        models = create_swagger_models_from_fields(api, field_classes_data, fields_data)
        
        # Return model schemas
        model_schemas = {}
        for class_name, model in models.items():
            model_schemas[class_name] = {
                'name': model.name,
                'fields': list(model.keys()),
                'schema': model.__schema__
            }
            
        return {'swagger_models': model_schemas}


# Example mapping configuration endpoint
@api.route('/mapping-example')
class MappingExampleAPI(Resource):
    def get(self):
        """Get example field mapping configuration"""
        return {
            'example_mapping': {
                'user_profile_mapping': {
                    'field_class': 'UserProfile',
                    'field_name': 'username',
                    'request_path': 'user.profile.name'
                },
                'user_email_mapping': {
                    'field_class': 'UserProfile', 
                    'field_name': 'email',
                    'request_path': 'user.contact.email'
                },
                'order_amount_mapping': {
                    'field_class': 'OrderData',
                    'field_name': 'total_amount',
                    'request_path': 'order.summary.total'
                }
            },
            'example_request': {
                'user': {
                    'profile': {
                        'name': 'john_doe',
                        'id': 12345
                    },
                    'contact': {
                        'email': 'john@example.com',
                        'phone': '+1-555-0123'
                    }
                },
                'order': {
                    'id': 'ORD-001',
                    'summary': {
                        'total': 99.99,
                        'currency': 'USD'
                    },
                    'items': [
                        {'name': 'Product A', 'price': 49.99},
                        {'name': 'Product B', 'price': 49.99}
                    ]
                }
            }
        }


# Enhanced field models with Swagger support
field_model = api.model('Field', {
    'GF_ID': restx_fields.Integer(description='Field ID'),
    'GFC_ID': restx_fields.Integer(description='Field Class ID'),
    'GF_NAME': restx_fields.String(required=True, description='Field name'),
    'GF_TYPE': restx_fields.String(required=True, description='Field type'),
    'GF_SIZE': restx_fields.Integer(description='Field size'),
    'GF_PRECISION_SIZE': restx_fields.Integer(description='Field precision'),
    'GF_DEFAULT_VALUE': restx_fields.String(description='Default value'),
    'GF_DESCRIPTION': restx_fields.String(description='Field description'),
    'CREATE_DATE': restx_fields.DateTime(description='Creation timestamp'),
    'UPDATE_DATE': restx_fields.DateTime(description='Last update timestamp')
})

field_input = api.model('FieldInput', {
    'GFC_ID': restx_fields.Integer(required=True, description='Field Class ID'),
    'GF_NAME': restx_fields.String(required=True, description='Field name'),
    'GF_TYPE': restx_fields.String(required=True, description='Field type'),
    'GF_SIZE': restx_fields.Integer(description='Field size'),
    'GF_PRECISION_SIZE': restx_fields.Integer(description='Field precision'),
    'GF_DEFAULT_VALUE': restx_fields.String(description='Default value'),
    'GF_DESCRIPTION': restx_fields.String(description='Field description')
})


@api.route('/fields')
class FieldsSwaggerAPI(Resource):
    @api.marshal_list_with(field_model)
    def get(self):
        """Get all fields"""
        fields = query_db('SELECT * FROM GEE_FIELDS')
        return [dict(field) for field in fields]
    
    @api.expect(field_input)
    @api.marshal_with(field_model, code=201)
    def post(self):
        """Create a new field"""
        data = request.json
        try:
            cursor = modify_db(
                'INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DEFAULT_VALUE, GF_DESCRIPTION) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (data['GFC_ID'], data['GF_NAME'], data['GF_TYPE'], data.get('GF_SIZE'),
                 data.get('GF_PRECISION_SIZE'), data.get('GF_DEFAULT_VALUE'), data.get('GF_DESCRIPTION'))
            )
            
            # Get the newly created field
            new_field = query_db('SELECT * FROM GEE_FIELDS WHERE GF_ID = ?', (cursor.lastrowid,), one=True)
            return dict(new_field), 201
        except Exception as e:
            api.abort(400, f'Error creating field: {str(e)}')


@api.route('/fields/<int:gf_id>')
class FieldSwaggerAPI(Resource):
    @api.marshal_with(field_model)
    def get(self, gf_id):
        """Get a specific field by ID"""
        field = query_db('SELECT * FROM GEE_FIELDS WHERE GF_ID = ?', (gf_id,), one=True)
        if not field:
            api.abort(404, 'Field not found')
        return dict(field)
    
    @api.expect(field_input)
    @api.marshal_with(field_model)
    def put(self, gf_id):
        """Update a field"""
        data = request.json
        try:
            modify_db(
                'UPDATE GEE_FIELDS SET GFC_ID = ?, GF_NAME = ?, GF_TYPE = ?, GF_SIZE = ?, GF_PRECISION_SIZE = ?, GF_DEFAULT_VALUE = ?, GF_DESCRIPTION = ?, UPDATE_DATE = ? WHERE GF_ID = ?',
                (data['GFC_ID'], data['GF_NAME'], data['GF_TYPE'], data.get('GF_SIZE'),
                 data.get('GF_PRECISION_SIZE'), data.get('GF_DEFAULT_VALUE'), data.get('GF_DESCRIPTION'), datetime.now(), gf_id)
            )
            
            # Get the updated field
            updated_field = query_db('SELECT * FROM GEE_FIELDS WHERE GF_ID = ?', (gf_id,), one=True)
            if not updated_field:
                api.abort(404, 'Field not found')
            return dict(updated_field)
        except Exception as e:
            api.abort(400, f'Error updating field: {str(e)}')
    
    def delete(self, gf_id):
        """Delete a field"""
        try:
            modify_db('DELETE FROM GEE_FIELDS WHERE GF_ID = ?', (gf_id,))
            return {'message': 'Field deleted successfully'}, 200
        except Exception as e:
            api.abort(400, f'Error deleting field: {str(e)}')


@api.route('/fields/by-class/<int:class_id>')
class FieldsByClassAPI(Resource):
    @api.marshal_list_with(field_model)
    def get(self, class_id):
        """Get all fields for a specific field class"""
        fields = query_db('SELECT * FROM GEE_FIELDS WHERE GFC_ID = ?', (class_id,))
        return [dict(field) for field in fields]


@api.route('/generate-mapping/<int:class_id>')
class GenerateMappingAPI(Resource):
    def get(self, class_id):
        """Generate field mapping configuration for a field class"""
        try:
            # Get field class
            field_class = query_db('SELECT * FROM GEE_FIELD_CLASSES WHERE GFC_ID = ?', (class_id,), one=True)
            if not field_class:
                api.abort(404, 'Field class not found')
            
            # Get fields for this class
            fields = query_db('SELECT * FROM GEE_FIELDS WHERE GFC_ID = ?', (class_id,))
            
            # Generate mapping configuration
            field_mapping = {}
            for field in fields:
                mapping_key = f"{field_class['FIELD_CLASS_NAME']}_{field['GF_NAME']}_mapping"
                field_mapping[mapping_key] = {
                    'field_class': field_class['FIELD_CLASS_NAME'],
                    'field_name': field['GF_NAME'],
                    'request_path': f"{field_class['FIELD_CLASS_NAME'].lower()}.{field['GF_NAME']}"
                }
            
            return {
                'field_class': field_class['FIELD_CLASS_NAME'],
                'field_mapping': field_mapping,
                'usage_example': {
                    'request_data': {
                        field_class['FIELD_CLASS_NAME'].lower(): {
                            field['GF_NAME']: f"sample_{field['GF_TYPE'].lower()}_value"
                            for field in fields
                        }
                    }
                }
            }
            
        except Exception as e:
            api.abort(500, f'Error generating mapping: {str(e)}')


@api.route('/validate-mapping')
class ValidateMappingAPI(Resource):
    mapping_validation_model = api.model('MappingValidation', {
        'field_mapping': restx_fields.Raw(required=True, description='Field mapping configuration'),
        'sample_request': restx_fields.Raw(required=True, description='Sample request data')
    })
    
    @api.expect(mapping_validation_model)
    def post(self):
        """Validate field mapping configuration with sample data"""
        data = request.json
        field_mapping = data.get('field_mapping', {})
        sample_request = data.get('sample_request', {})
        
        try:
            # Get field classes and fields data
            field_classes_data = [dict(row) for row in query_db('SELECT * FROM GEE_FIELD_CLASSES')]
            fields_data = [dict(row) for row in query_db('SELECT * FROM GEE_FIELDS')]
            
            # Validate mapping configuration
            from swagger_helpers import validate_field_mapping_config, map_request_to_fields
            is_valid, errors = validate_field_mapping_config(field_mapping, field_classes_data, fields_data)
            
            validation_result = {
                'mapping_valid': is_valid,
                'validation_errors': errors,
                'mapped_fields': [],
                'unmapped_paths': []
            }
            
            if is_valid and sample_request:
                # Test mapping with sample data
                try:
                    mapped_data = map_request_to_fields(sample_request, field_mapping, field_classes_data, fields_data)
                    validation_result['mapped_fields'] = list(mapped_data.keys())
                    validation_result['mapping_success'] = True
                    validation_result['sample_output'] = mapped_data
                except Exception as e:
                    validation_result['mapping_success'] = False
                    validation_result['mapping_error'] = str(e)
            
            return validation_result
            
        except Exception as e:
            return {
                'mapping_valid': False,
                'validation_errors': [f'Error validating mapping: {str(e)}'],
                'mapped_fields': [],
                'unmapped_paths': []
            }, 500
