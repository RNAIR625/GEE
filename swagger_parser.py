import json
import yaml
from typing import Dict, List, Tuple, Any


class SwaggerParser:
    """
    Parses Swagger/OpenAPI files and extracts field definitions for integration
    with GEE Field Classes and Fields.
    """
    
    def __init__(self):
        self.swagger_data = None
        self.extracted_models = {}
        
    def parse_file(self, file_content: str, file_type: str = 'json') -> Dict:
        """
        Parse Swagger file content (JSON or YAML)
        
        Args:
            file_content (str): Raw file content
            file_type (str): 'json' or 'yaml'
            
        Returns:
            Dict: Parsed Swagger specification
        """
        try:
            if file_type.lower() == 'json':
                self.swagger_data = json.loads(file_content)
            elif file_type.lower() in ['yaml', 'yml']:
                self.swagger_data = yaml.safe_load(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
                
            return self.swagger_data
        except Exception as e:
            raise Exception(f"Error parsing Swagger file: {str(e)}")
    
    def extract_field_classes_and_fields(self) -> Dict[str, Dict]:
        """
        Extract field classes and fields from Swagger models/schemas
        
        Returns:
            Dict: Field classes with their fields
        """
        if not self.swagger_data:
            raise Exception("No Swagger data loaded. Call parse_file() first.")
        
        field_classes = {}
        
        # Extract from OpenAPI 3.x components/schemas
        if 'components' in self.swagger_data and 'schemas' in self.swagger_data['components']:
            schemas = self.swagger_data['components']['schemas']
            for schema_name, schema_def in schemas.items():
                field_class = self._extract_field_class_from_schema(schema_name, schema_def)
                if field_class:
                    field_classes[schema_name] = field_class
        
        # Extract from Swagger 2.0 definitions
        elif 'definitions' in self.swagger_data:
            definitions = self.swagger_data['definitions']
            for def_name, def_schema in definitions.items():
                field_class = self._extract_field_class_from_schema(def_name, def_schema)
                if field_class:
                    field_classes[def_name] = field_class
        
        # Extract from paths (request/response bodies)
        if 'paths' in self.swagger_data:
            path_models = self._extract_from_paths()
            field_classes.update(path_models)
        
        self.extracted_models = field_classes
        return field_classes
    
    def _extract_field_class_from_schema(self, name: str, schema: Dict) -> Dict:
        """
        Extract field class definition from a Swagger schema
        
        Args:
            name (str): Schema name
            schema (Dict): Schema definition
            
        Returns:
            Dict: Field class with fields
        """
        if schema.get('type') != 'object' or 'properties' not in schema:
            return None
        
        field_class = {
            'name': name,
            'type': self._determine_class_type(schema),
            'description': schema.get('description', f'Field class for {name}'),
            'fields': []
        }
        
        properties = schema['properties']
        required_fields = schema.get('required', [])
        
        for prop_name, prop_def in properties.items():
            field = self._extract_field_from_property(prop_name, prop_def, prop_name in required_fields)
            if field:
                field_class['fields'].append(field)
        
        return field_class
    
    def _extract_field_from_property(self, name: str, prop_def: Dict, is_required: bool = False) -> Dict:
        """
        Extract field definition from a property
        
        Args:
            name (str): Property name
            prop_def (Dict): Property definition
            is_required (bool): Whether field is required
            
        Returns:
            Dict: Field definition
        """
        field_type, field_size, precision = self._map_swagger_type_to_db_type(prop_def)
        
        field = {
            'name': name,
            'type': field_type,
            'size': field_size,
            'precision': precision,
            'default_value': prop_def.get('default'),
            'description': prop_def.get('description', f'Field: {name}'),
            'required': is_required,
            'swagger_type': prop_def.get('type'),
            'swagger_format': prop_def.get('format'),
            'enum_values': prop_def.get('enum'),
            'min_length': prop_def.get('minLength'),
            'max_length': prop_def.get('maxLength'),
            'minimum': prop_def.get('minimum'),
            'maximum': prop_def.get('maximum')
        }
        
        return field
    
    def _map_swagger_type_to_db_type(self, prop_def: Dict) -> Tuple[str, int, int]:
        """
        Map Swagger/OpenAPI types to database types
        
        Args:
            prop_def (Dict): Property definition
            
        Returns:
            Tuple: (db_type, size, precision)
        """
        swagger_type = prop_def.get('type', 'string')
        swagger_format = prop_def.get('format')
        
        # Default values
        db_type = 'TEXT'
        size = None
        precision = None
        
        if swagger_type == 'string':
            if swagger_format == 'date':
                db_type = 'DATE'
            elif swagger_format == 'date-time':
                db_type = 'DATETIME'
            elif swagger_format == 'email':
                db_type = 'VARCHAR'
                size = 255
            elif swagger_format == 'uuid':
                db_type = 'VARCHAR'
                size = 36
            else:
                db_type = 'TEXT'
                size = prop_def.get('maxLength', 255) if prop_def.get('maxLength') else None
                
        elif swagger_type == 'integer':
            if swagger_format == 'int64':
                db_type = 'BIGINT'
            else:
                db_type = 'INTEGER'
                
        elif swagger_type == 'number':
            if swagger_format == 'float':
                db_type = 'FLOAT'
            elif swagger_format == 'double':
                db_type = 'DOUBLE'
            else:
                db_type = 'DECIMAL'
                precision = 10  # Default precision
                
        elif swagger_type == 'boolean':
            db_type = 'BOOLEAN'
            
        elif swagger_type == 'array':
            db_type = 'JSON'  # Store arrays as JSON
            
        elif swagger_type == 'object':
            db_type = 'JSON'  # Store objects as JSON
            
        return db_type, size, precision
    
    def _determine_class_type(self, schema: Dict) -> str:
        """
        Determine the field class type based on schema characteristics
        
        Args:
            schema (Dict): Schema definition
            
        Returns:
            str: Class type
        """
        # Check if it's a request/response model
        if 'example' in schema or 'examples' in schema:
            return 'API_MODEL'
        
        # Check for common patterns
        properties = schema.get('properties', {})
        
        if any(prop in properties for prop in ['id', 'uuid', 'identifier']):
            return 'ENTITY'
        elif any(prop in properties for prop in ['name', 'title', 'label']):
            return 'REFERENCE'
        elif any(prop in properties for prop in ['email', 'phone', 'address']):
            return 'CONTACT'
        elif any(prop in properties for prop in ['amount', 'price', 'cost', 'total']):
            return 'FINANCIAL'
        else:
            return 'DATA'
    
    def _extract_from_paths(self) -> Dict[str, Dict]:
        """
        Extract field classes from API paths (request/response bodies)
        
        Returns:
            Dict: Additional field classes from paths
        """
        path_models = {}
        
        if 'paths' not in self.swagger_data:
            return path_models
        
        for path, path_def in self.swagger_data['paths'].items():
            for method, method_def in path_def.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                    continue
                
                # Extract from request body
                if 'requestBody' in method_def:
                    request_models = self._extract_from_request_body(
                        f"{method.upper()}_{path.replace('/', '_')}_Request", 
                        method_def['requestBody']
                    )
                    path_models.update(request_models)
                
                # Extract from responses
                if 'responses' in method_def:
                    response_models = self._extract_from_responses(
                        f"{method.upper()}_{path.replace('/', '_')}_Response",
                        method_def['responses']
                    )
                    path_models.update(response_models)
        
        return path_models
    
    def _extract_from_request_body(self, base_name: str, request_body: Dict) -> Dict[str, Dict]:
        """Extract models from request body definition"""
        models = {}
        
        if 'content' in request_body:
            for content_type, content_def in request_body['content'].items():
                if 'schema' in content_def:
                    schema = content_def['schema']
                    if schema.get('type') == 'object' and 'properties' in schema:
                        model_name = f"{base_name}_{content_type.replace('/', '_')}"
                        model = self._extract_field_class_from_schema(model_name, schema)
                        if model:
                            models[model_name] = model
        
        return models
    
    def _extract_from_responses(self, base_name: str, responses: Dict) -> Dict[str, Dict]:
        """Extract models from response definitions"""
        models = {}
        
        for status_code, response_def in responses.items():
            if 'content' in response_def:
                for content_type, content_def in response_def['content'].items():
                    if 'schema' in content_def:
                        schema = content_def['schema']
                        if schema.get('type') == 'object' and 'properties' in schema:
                            model_name = f"{base_name}_{status_code}_{content_type.replace('/', '_')}"
                            model = self._extract_field_class_from_schema(model_name, schema)
                            if model:
                                models[model_name] = model
        
        return models
    
    def get_field_class_sync_operations(self, existing_field_classes: List[Dict], 
                                       target_class_name: str = None) -> Dict[str, List]:
        """
        Compare extracted models with existing field classes and generate sync operations
        
        Args:
            existing_field_classes (List[Dict]): Current field classes from database
            target_class_name (str): Specific class to sync (None for all)
            
        Returns:
            Dict: Operations to perform (insert, update, delete)
        """
        operations = {
            'field_classes': {
                'insert': [],
                'update': [],
                'delete': []
            },
            'fields': {
                'insert': [],
                'update': [],
                'delete': []
            }
        }
        
        if not self.extracted_models:
            return operations
        
        existing_classes_map = {cls['FIELD_CLASS_NAME']: cls for cls in existing_field_classes}
        
        # Filter models if target class specified
        models_to_process = self.extracted_models
        if target_class_name:
            models_to_process = {k: v for k, v in self.extracted_models.items() 
                               if k == target_class_name}
        
        # Check for new and updated field classes
        for model_name, model_def in models_to_process.items():
            if model_name in existing_classes_map:
                # Check if update needed
                existing_class = existing_classes_map[model_name]
                if (existing_class['CLASS_TYPE'] != model_def['type'] or 
                    existing_class['DESCRIPTION'] != model_def['description']):
                    operations['field_classes']['update'].append({
                        'gfc_id': existing_class['GFC_ID'],
                        'name': model_name,
                        'type': model_def['type'],
                        'description': model_def['description']
                    })
            else:
                # New field class
                operations['field_classes']['insert'].append({
                    'name': model_name,
                    'type': model_def['type'],
                    'description': model_def['description'],
                    'fields': model_def['fields']
                })
        
        # Check for field classes to delete (if not in Swagger)
        if not target_class_name:  # Only delete when syncing all
            for existing_name in existing_classes_map:
                if existing_name not in self.extracted_models:
                    operations['field_classes']['delete'].append({
                        'gfc_id': existing_classes_map[existing_name]['GFC_ID'],
                        'name': existing_name
                    })
        
        return operations
    
    def validate_swagger_file(self) -> Tuple[bool, List[str]]:
        """
        Validate the loaded Swagger file
        
        Returns:
            Tuple: (is_valid, error_messages)
        """
        errors = []
        
        if not self.swagger_data:
            errors.append("No Swagger data loaded")
            return False, errors
        
        # Check for required fields
        if 'openapi' not in self.swagger_data and 'swagger' not in self.swagger_data:
            errors.append("Invalid Swagger/OpenAPI file: missing version information")
        
        # Check for schemas/definitions
        has_schemas = ('components' in self.swagger_data and 
                      'schemas' in self.swagger_data['components'])
        has_definitions = 'definitions' in self.swagger_data
        
        if not has_schemas and not has_definitions:
            errors.append("No schemas or definitions found in Swagger file")
        
        # Check for paths
        if 'paths' not in self.swagger_data:
            errors.append("No paths found in Swagger file")
        
        return len(errors) == 0, errors