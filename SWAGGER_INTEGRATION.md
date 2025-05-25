# Swagger Integration for Field Classes and Fields

## Overview

The application now includes comprehensive Swagger/OpenAPI integration for Field Classes and Fields management. This allows you to import Swagger files to automatically create/update/delete field classes and fields, as well as generate mapping configurations for REST API integration.

## Features Added

### 1. Field Classes Screen (`/classes/`)

#### Swagger Documentation
- **URL**: `/classes/swagger/`
- **API Endpoints**: `/classes/api/*`

#### Core Functionality
- **CRUD Operations**: Full Create, Read, Update, Delete operations with Swagger documentation
- **Swagger Import**: Import Swagger/OpenAPI files to sync field classes and fields
- **Swagger Export**: Export existing field classes as Swagger schemas

#### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/classes/api/classes` | Get all field classes |
| POST | `/classes/api/classes` | Create new field class |
| GET | `/classes/api/classes/{id}` | Get specific field class |
| PUT | `/classes/api/classes/{id}` | Update field class |
| DELETE | `/classes/api/classes/{id}` | Delete field class |
| POST | `/classes/api/swagger-import` | **Import Swagger file** |
| GET | `/classes/api/swagger-export/{id}` | Export field class as Swagger |

### 2. Fields Screen (`/fields/`)

#### Swagger Documentation
- **URL**: `/fields/swagger/`
- **API Endpoints**: `/fields/api/*`

#### Enhanced Functionality
- **Full CRUD**: Complete field management with Swagger documentation
- **Field Mapping**: Advanced request-to-field mapping with JSONPath support
- **Mapping Generation**: Auto-generate mapping configurations
- **Mapping Validation**: Validate mappings with sample data

#### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/fields/api/fields` | Get all fields |
| POST | `/fields/api/fields` | Create new field |
| GET | `/fields/api/fields/{id}` | Get specific field |
| PUT | `/fields/api/fields/{id}` | Update field |
| DELETE | `/fields/api/fields/{id}` | Delete field |
| GET | `/fields/api/fields/by-class/{class_id}` | Get fields by class |
| POST | `/fields/api/field-mapping` | **Map request data to fields** |
| GET | `/fields/api/generate-mapping/{class_id}` | Generate mapping config |
| POST | `/fields/api/validate-mapping` | Validate mapping with sample data |
| GET | `/fields/api/swagger-models` | Get dynamic Swagger models |
| GET | `/fields/api/mapping-example` | Get mapping examples |

## Swagger Import Feature

### How It Works

1. **File Upload**: Submit Swagger/OpenAPI file (JSON or YAML)
2. **Parsing**: Extracts field classes and fields from schemas/definitions
3. **Preview Mode**: Shows what changes would be made
4. **Execute Mode**: Performs the actual insert/update/delete operations

### Import Request Format

```json
{
  "file_content": "{ swagger file content as string }",
  "file_type": "json", // or "yaml"
  "target_class_name": "SpecificClass", // optional - sync only this class
  "sync_mode": "preview" // or "execute"
}
```

### Supported Swagger Features

- **OpenAPI 3.x**: `components/schemas`
- **Swagger 2.0**: `definitions`
- **Path Extraction**: Request/response body schemas
- **Type Mapping**: Automatic conversion from Swagger types to database types

### Type Mappings

| Swagger Type | Swagger Format | Database Type |
|--------------|----------------|---------------|
| string | - | TEXT |
| string | email | VARCHAR(255) |
| string | uuid | VARCHAR(36) |
| string | date | DATE |
| string | date-time | DATETIME |
| integer | - | INTEGER |
| integer | int64 | BIGINT |
| number | float | FLOAT |
| number | double | DOUBLE |
| number | - | DECIMAL |
| boolean | - | BOOLEAN |
| array | - | JSON |
| object | - | JSON |

## Field Mapping Feature

### JSONPath Support

Map request data to fields using JSONPath-like syntax:

```json
{
  "field_mapping": {
    "user_name_mapping": {
      "field_class": "UserProfile",
      "field_name": "username",
      "request_path": "user.profile.name"
    },
    "order_total_mapping": {
      "field_class": "OrderData",
      "field_name": "total_amount",
      "request_path": "order.summary.total"
    },
    "item_price_mapping": {
      "field_class": "ItemData",
      "field_name": "price",
      "request_path": "items[0].price"
    }
  },
  "request_data": {
    "user": {
      "profile": {
        "name": "john_doe"
      }
    },
    "order": {
      "summary": {
        "total": 99.99
      }
    },
    "items": [
      {"price": 49.99}
    ]
  }
}
```

### Output Format

```json
{
  "success": true,
  "mapped_data": {
    "UserProfile.username": {
      "value": "john_doe",
      "field_id": 1,
      "field_class_id": 1,
      "field_type": "TEXT"
    },
    "OrderData.total_amount": {
      "value": 99.99,
      "field_id": 2,
      "field_class_id": 2,
      "field_type": "DECIMAL"
    }
  }
}
```

## Usage Examples

### 1. Import Swagger File (Preview)

```bash
curl -X POST "http://localhost:5000/classes/api/swagger-import" \
     -H "Content-Type: application/json" \
     -d '{
       "file_content": "{ \"openapi\": \"3.0.0\", \"components\": { \"schemas\": { \"User\": { \"type\": \"object\", \"properties\": { \"id\": { \"type\": \"integer\" }, \"name\": { \"type\": \"string\" } } } } } }",
       "file_type": "json",
       "sync_mode": "preview"
     }'
```

### 2. Execute Swagger Import

```bash
curl -X POST "http://localhost:5000/classes/api/swagger-import" \
     -H "Content-Type: application/json" \
     -d '{
       "file_content": "...",
       "file_type": "json",
       "sync_mode": "execute"
     }'
```

### 3. Map Request Data to Fields

```bash
curl -X POST "http://localhost:5000/fields/api/field-mapping" \
     -H "Content-Type: application/json" \
     -d '{
       "field_mapping": {
         "user_mapping": {
           "field_class": "User",
           "field_name": "name",
           "request_path": "user.name"
         }
       },
       "request_data": {
         "user": {
           "name": "John Doe"
         }
       }
     }'
```

### 4. Generate Mapping Configuration

```bash
curl -X GET "http://localhost:5000/fields/api/generate-mapping/1"
```

### 5. Export Field Class as Swagger

```bash
curl -X GET "http://localhost:5000/classes/api/swagger-export/1"
```

## Database Operations

### Sync Operations Performed

1. **Insert**: New field classes and fields from Swagger
2. **Update**: Modified field classes and fields
3. **Delete**: Field classes and fields not in Swagger (when syncing all)

### Field Class Auto-Classification

The system automatically determines field class types based on field patterns:

- **ENTITY**: Contains id, uuid, identifier fields
- **REFERENCE**: Contains name, title, label fields  
- **CONTACT**: Contains email, phone, address fields
- **FINANCIAL**: Contains amount, price, cost, total fields
- **API_MODEL**: Contains example/examples
- **DATA**: Default type

## Error Handling

The system provides comprehensive error handling:

- **Validation Errors**: Invalid Swagger files
- **Mapping Errors**: Invalid field mappings
- **Database Errors**: Constraint violations
- **Type Conversion Errors**: Invalid data types

## Security Considerations

- File content is processed in-memory (no file system storage)
- SQL injection protection through parameterized queries
- Input validation on all API endpoints
- Error messages don't expose internal details

## Dependencies Added

- `flask-restx==1.3.0`: Swagger/OpenAPI support
- `PyYAML==6.0.1`: YAML file parsing

## Access URLs

- **Field Classes Swagger**: `http://localhost:5000/classes/swagger/`
- **Fields Swagger**: `http://localhost:5000/fields/swagger/`
- **Field Classes Page**: `http://localhost:5000/classes/`
- **Fields Page**: `http://localhost:5000/fields/`