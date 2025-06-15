# E-commerce Loyalty System API - Test Commands

This document contains all curl commands and JSON payloads to test the E-commerce Loyalty System API endpoints served by Praxis.

## Base Information
- **Base URL**: `http://localhost:8080/ecommerce/loyalty/v1`
- **Total Endpoints**: 11
- **API Class**: E-commerce Loyalty System API
- **Database ID**: 55

---

## 1. GET /customers - List customers with pagination

### Basic Request
```bash
curl -X GET http://localhost:8080/ecommerce/loyalty/v1/customers
```

### With Query Parameters
```bash
curl -X GET "http://localhost:8080/ecommerce/loyalty/v1/customers?page=1&limit=20&tier=Gold&email=john.doe@example.com"
```

**No Request Body Required**

---

## 2. POST /customers - Create a new customer

```bash
curl -X POST http://localhost:8080/ecommerce/loyalty/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane.smith@example.com",
    "firstName": "Jane",
    "lastName": "Smith",
    "preferences": {
      "emailNotifications": true,
      "smsNotifications": false,
      "preferredCategories": ["Electronics", "Clothing"]
    }
  }'
```

### JSON Schema (CreateCustomerRequest)
```json
{
  "email": "string (required, format: email, maxLength: 255)",
  "firstName": "string (required, maxLength: 100, pattern: ^[a-zA-Z\\s\\-']+$)",
  "lastName": "string (required, maxLength: 100, pattern: ^[a-zA-Z\\s\\-']+$)",
  "preferences": {
    "emailNotifications": "boolean (default: true)",
    "smsNotifications": "boolean (default: false)", 
    "preferredCategories": "array of strings (maxItems: 10)"
  }
}
```

---

## 3. GET /customers/{customerId} - Get customer by ID

```bash
curl -X GET http://localhost:8080/ecommerce/loyalty/v1/customers/550e8400-e29b-41d4-a716-446655440000
```

**Path Parameters:**
- `customerId`: UUID format string

**No Request Body Required**

---

## 4. PUT /customers/{customerId} - Update customer information

```bash
curl -X PUT http://localhost:8080/ecommerce/loyalty/v1/customers/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane.smith.updated@example.com",
    "firstName": "Jane",
    "lastName": "Smith-Johnson",
    "preferences": {
      "emailNotifications": false,
      "smsNotifications": true,
      "preferredCategories": ["Electronics", "Home & Garden"]
    }
  }'
```

### JSON Schema (UpdateCustomerRequest)
```json
{
  "email": "string (optional, format: email, maxLength: 255)",
  "firstName": "string (optional, maxLength: 100, pattern: ^[a-zA-Z\\s\\-']+$)",
  "lastName": "string (optional, maxLength: 100, pattern: ^[a-zA-Z\\s\\-']+$)",
  "preferences": {
    "emailNotifications": "boolean",
    "smsNotifications": "boolean",
    "preferredCategories": "array of strings"
  }
}
```

---

## 5. POST /orders - Process a new order

```bash
curl -X POST http://localhost:8080/ecommerce/loyalty/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "550e8400-e29b-41d4-a716-446655440000",
    "items": [
      {
        "productId": "LAPTOP-HP-15-2024",
        "name": "HP Laptop 15-inch",
        "price": 75.00,
        "quantity": 2,
        "category": "Electronics",
        "isPromotional": true
      },
      {
        "productId": "MOUSE-LOGITECH-MX",
        "name": "Logitech MX Master Mouse",
        "price": 99.99,
        "quantity": 1,
        "category": "Electronics",
        "isPromotional": false
      }
    ],
    "subtotal": 249.99,
    "orderDate": "2024-06-08T15:30:00Z"
  }'
```

### JSON Schema (ProcessOrderRequest)
```json
{
  "customerId": "string (required, format: uuid)",
  "items": [
    {
      "productId": "string (required, maxLength: 50, pattern: ^[a-zA-Z0-9\\-_]+$)",
      "name": "string (required, maxLength: 200, minLength: 1)",
      "price": "number (required, format: decimal, minimum: 0.01, maximum: 99999.99)",
      "quantity": "integer (required, minimum: 1, maximum: 999)",
      "category": "string (required, maxLength: 50)",
      "isPromotional": "boolean (default: false)"
    }
  ],
  "subtotal": "number (required, format: decimal, minimum: 0.01, maximum: 999999.99)",
  "orderDate": "string (optional, format: date-time)"
}
```

---

## 6. GET /orders/{orderId} - Get order details

```bash
curl -X GET http://localhost:8080/ecommerce/loyalty/v1/orders/123e4567-e89b-12d3-a456-426614174000
```

**Path Parameters:**
- `orderId`: UUID format string

**No Request Body Required**

---

## 7. GET /customers/{customerId}/points - Get customer points balance

### Basic Request
```bash
curl -X GET http://localhost:8080/ecommerce/loyalty/v1/customers/550e8400-e29b-41d4-a716-446655440000/points
```

### With Query Parameters
```bash
curl -X GET "http://localhost:8080/ecommerce/loyalty/v1/customers/550e8400-e29b-41d4-a716-446655440000/points?includeHistory=true&limit=50"
```

**Query Parameters:**
- `includeHistory`: boolean (default: false)
- `limit`: integer (minimum: 1, maximum: 100, default: 50)

**No Request Body Required**

---

## 8. POST /customers/{customerId}/points - Manual points adjustment

```bash
curl -X POST http://localhost:8080/ecommerce/loyalty/v1/customers/550e8400-e29b-41d4-a716-446655440000/points \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 500,
    "reason": "Compensation for delayed shipment on order #12345",
    "adminUserId": "admin-550e8400-e29b-41d4-a716-446655440001"
  }'
```

### JSON Schema (PointsAdjustmentRequest)
```json
{
  "amount": "integer (required, minimum: -999999, maximum: 999999)",
  "reason": "string (required, maxLength: 500, minLength: 10)",
  "adminUserId": "string (optional, format: uuid)"
}
```

---

## 9. GET /customers/{customerId}/tier - Get customer tier information

```bash
curl -X GET http://localhost:8080/ecommerce/loyalty/v1/customers/550e8400-e29b-41d4-a716-446655440000/tier
```

**Path Parameters:**
- `customerId`: UUID format string

**No Request Body Required**

---

## 10. PUT /customers/{customerId}/tier - Recalculate customer tier

```bash
curl -X PUT http://localhost:8080/ecommerce/loyalty/v1/customers/550e8400-e29b-41d4-a716-446655440000/tier
```

**Path Parameters:**
- `customerId`: UUID format string

**No Request Body Required** (triggers recalculation based on current spending)

---

## 11. POST /discounts/calculate - Calculate available discounts

```bash
curl -X POST http://localhost:8080/ecommerce/loyalty/v1/discounts/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "550e8400-e29b-41d4-a716-446655440000",
    "items": [
      {
        "productId": "LAPTOP-HP-15-2024",
        "name": "HP Laptop 15-inch",
        "price": 75.00,
        "quantity": 2,
        "category": "Electronics",
        "isPromotional": true
      },
      {
        "productId": "SHIRT-NIKE-L",
        "name": "Nike Sport Shirt",
        "price": 45.00,
        "quantity": 3,
        "category": "Clothing",
        "isPromotional": false
      }
    ],
    "subtotal": 285.00
  }'
```

### JSON Schema (DiscountCalculationRequest)
```json
{
  "customerId": "string (required, format: uuid)",
  "items": [
    {
      "productId": "string (required)",
      "name": "string (required)",
      "price": "number (required, format: decimal)",
      "quantity": "integer (required)",
      "category": "string (required)",
      "isPromotional": "boolean"
    }
  ],
  "subtotal": "number (required, format: decimal, minimum: 0.01)"
}
```

---

## Sample UUIDs for Testing

Use these sample UUIDs for testing:

- **Customer ID**: `550e8400-e29b-41d4-a716-446655440000`
- **Order ID**: `123e4567-e89b-12d3-a456-426614174000`
- **Admin User ID**: `admin-550e8400-e29b-41d4-a716-446655440001`

---

## Membership Tiers

Valid membership tier values:
- `Bronze`
- `Silver` 
- `Gold`
- `Platinum`

---

## Response Format

All endpoints return JSON responses in this format:

```json
{
  "status": "success",
  "message": "Endpoint [METHOD] [PATH] processed",
  "class": "E-commerce Loyalty System API",
  "operation": null,
  "data": {
    "endpoint": { /* endpoint details */ },
    "request_data": { /* submitted data */ },
    "path_params": { /* path parameters */ },
    "query_params": { /* query parameters */ },
    "headers": { /* request headers */ },
    "class_id": 55,
    "class_name": "E-commerce Loyalty System API"
  }
}
```

---

## Authentication

Currently, the endpoints are accessible without authentication. In production, you would typically add:

- **Bearer Token**: `Authorization: Bearer <token>`
- **API Key**: `X-API-Key: <key>`

As defined in the original Swagger specification.