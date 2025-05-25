from flask_restx import fields


def map_request_to_fields(request_data, field_mapping, field_classes_data, fields_data):
    """
    Maps request data to field definitions based on Swagger field mapping.
    
    Args:
        request_data (dict): The incoming request data from Swagger API
        field_mapping (dict): Mapping configuration defining how request paths map to fields
        field_classes_data (list): List of field classes from GEE_FIELD_CLASSES
        fields_data (list): List of fields from GEE_FIELDS
    
    Returns:
        dict: Mapped field values ready for processing
    """
    mapped_data = {}
    
    for field_path, field_config in field_mapping.items():
        field_class_name = field_config.get('field_class')
        field_name = field_config.get('field_name')
        request_path = field_config.get('request_path')
        
        # Find the field class
        field_class = next((fc for fc in field_classes_data if fc['FIELD_CLASS_NAME'] == field_class_name), None)
        if not field_class:
            continue
            
        # Find the specific field
        field_def = next((f for f in fields_data if f['GFC_ID'] == field_class['GFC_ID'] and f['GF_NAME'] == field_name), None)
        if not field_def:
            continue
            
        # Extract value from request using JSONPath-like syntax
        value = extract_value_from_request(request_data, request_path)
        
        if value is not None:
            # Apply type conversion based on field definition
            converted_value = convert_value_to_field_type(value, field_def)
            mapped_data[f"{field_class_name}.{field_name}"] = {
                'value': converted_value,
                'field_id': field_def['GF_ID'],
                'field_class_id': field_def['GFC_ID'],
                'field_type': field_def['GF_TYPE']
            }
    
    return mapped_data


def extract_value_from_request(request_data, path):
    """
    Extracts value from request data using JSONPath-like syntax.
    
    Args:
        request_data (dict): The request data
        path (str): JSONPath-like path (e.g., "user.profile.name" or "items[0].price")
    
    Returns:
        Any: The extracted value or None if not found
    """
    try:
        current_data = request_data
        
        # Split path by dots and handle array indexing
        parts = path.split('.')
        for part in parts:
            if '[' in part and ']' in part:
                # Handle array indexing like "items[0]"
                key = part.split('[')[0]
                index = int(part.split('[')[1].split(']')[0])
                current_data = current_data[key][index]
            else:
                current_data = current_data[part]
                
        return current_data
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def convert_value_to_field_type(value, field_def):
    """
    Converts a value to the appropriate type based on field definition.
    
    Args:
        value: The value to convert
        field_def (dict): Field definition from GEE_FIELDS
    
    Returns:
        Any: Converted value
    """
    field_type = field_def['GF_TYPE'].upper()
    
    try:
        if field_type in ['INTEGER', 'INT', 'BIGINT']:
            # Handle string numbers with currency symbols
            if isinstance(value, str):
                # Remove currency symbols and whitespace
                cleaned_value = value.replace('$', '').replace(',', '').strip()
                return int(float(cleaned_value))  # Convert via float to handle decimals
            return int(value)
            
        elif field_type in ['FLOAT', 'REAL', 'DECIMAL', 'NUMBER', 'DOUBLE']:
            # Handle string numbers with currency symbols
            if isinstance(value, str):
                # Remove currency symbols and whitespace
                cleaned_value = value.replace('$', '').replace(',', '').strip()
                return float(cleaned_value)
            return float(value)
            
        elif field_type in ['TEXT', 'VARCHAR', 'STRING']:
            return str(value)
            
        elif field_type in ['BOOLEAN', 'BOOL']:
            if isinstance(value, str):
                return value.lower() in ['true', '1', 'yes', 'on']
            return bool(value)
            
        elif field_type in ['DATE']:
            # Ensure date format is consistent
            if isinstance(value, str):
                return value  # Assume it's already in correct format
            return str(value)
            
        elif field_type in ['DATETIME']:
            # Ensure datetime format is consistent
            if isinstance(value, str):
                return value  # Assume it's already in correct format
            return str(value)
            
        elif field_type in ['JSON']:
            # Handle JSON fields
            if isinstance(value, (dict, list)):
                import json
                return json.dumps(value)
            return str(value)
            
        else:
            return str(value)  # Default to string
            
    except (ValueError, TypeError):
        # Return default value or None if conversion fails
        default_value = field_def.get('GF_DEFAULT_VALUE')
        return default_value if default_value is not None else None


def create_swagger_models_from_fields(api, field_classes_data, fields_data):
    """
    Creates Swagger models based on field classes and fields.
    
    Args:
        api: Flask-RESTX API instance
        field_classes_data (list): List of field classes
        fields_data (list): List of fields
    
    Returns:
        dict: Dictionary of Swagger models keyed by field class name
    """
    models = {}
    
    for field_class in field_classes_data:
        class_fields = [f for f in fields_data if f['GFC_ID'] == field_class['GFC_ID']]
        
        model_fields = {}
        for field in class_fields:
            swagger_type = map_field_type_to_swagger(field['GF_TYPE'])
            
            field_config = {
                'type': swagger_type,
                'description': field.get('GF_DESCRIPTION', f"Field: {field['GF_NAME']}")
            }
            
            # Add size constraints if applicable
            if field['GF_SIZE'] and swagger_type == 'string':
                field_config['maxLength'] = field['GF_SIZE']
                
            # Add default value if present
            if field['GF_DEFAULT_VALUE']:
                field_config['default'] = field['GF_DEFAULT_VALUE']
                
            model_fields[field['GF_NAME']] = fields.Raw(**field_config)
        
        # Create the model
        model_name = f"{field_class['FIELD_CLASS_NAME']}Model"
        models[field_class['FIELD_CLASS_NAME']] = api.model(model_name, model_fields)
    
    return models


def map_field_type_to_swagger(field_type):
    """
    Maps database field types to Swagger/OpenAPI types.
    
    Args:
        field_type (str): Database field type
    
    Returns:
        str: Swagger type
    """
    field_type = field_type.upper()
    
    type_mapping = {
        'INTEGER': 'integer',
        'INT': 'integer',
        'FLOAT': 'number',
        'REAL': 'number',
        'DECIMAL': 'number',
        'NUMBER': 'number',
        'TEXT': 'string',
        'VARCHAR': 'string',
        'STRING': 'string',
        'BOOLEAN': 'boolean',
        'BOOL': 'boolean',
        'DATE': 'string',
        'DATETIME': 'string',
        'TIMESTAMP': 'string'
    }
    
    return type_mapping.get(field_type, 'string')


def validate_field_mapping_config(field_mapping, field_classes_data, fields_data):
    """
    Validates field mapping configuration.
    
    Args:
        field_mapping (dict): Field mapping configuration
        field_classes_data (list): List of field classes
        fields_data (list): List of fields
    
    Returns:
        tuple: (is_valid, error_messages)
    """
    errors = []
    
    for mapping_key, mapping_config in field_mapping.items():
        # Check required keys
        required_keys = ['field_class', 'field_name', 'request_path']
        for key in required_keys:
            if key not in mapping_config:
                errors.append(f"Missing required key '{key}' in mapping '{mapping_key}'")
                continue
        
        # Validate field class exists
        field_class_name = mapping_config.get('field_class')
        field_class = next((fc for fc in field_classes_data if fc['FIELD_CLASS_NAME'] == field_class_name), None)
        if not field_class:
            errors.append(f"Field class '{field_class_name}' not found in mapping '{mapping_key}'")
            continue
            
        # Validate field exists
        field_name = mapping_config.get('field_name')
        field_def = next((f for f in fields_data if f['GFC_ID'] == field_class['GFC_ID'] and f['GF_NAME'] == field_name), None)
        if not field_def:
            errors.append(f"Field '{field_name}' not found in class '{field_class_name}' for mapping '{mapping_key}'")
    
    return len(errors) == 0, errors