# E-commerce Loyalty System API Testing Guide

This directory contains comprehensive testing resources for the E-commerce Loyalty System API served by Praxis.

## Files Created

### 📋 **Documentation**
- **`ecommerce_api_tests.md`** - Complete API documentation with curl commands and JSON schemas
- **`README_API_testing.md`** - This guide

### 🚀 **Executable Scripts**  
- **`curl_commands.sh`** - Interactive script with individual test functions
- **`test_all_endpoints.sh`** - Automated script to test all endpoints

### 📊 **Data Files**
- **`json_payloads.json`** - Structured JSON file with all payloads and variations

## Quick Start

### 1. Test All Endpoints
```bash
./test_all_endpoints.sh
```

### 2. Test Individual Endpoints
```bash
# Show available functions
./curl_commands.sh

# Test specific endpoint
./curl_commands.sh test_create_customer

# Source and use interactively
source curl_commands.sh
test_get_customer
```

### 3. Check Praxis Status
```bash
# Verify Praxis is running and endpoints are loaded
curl -s http://localhost:8080/api/v1/status | python3 -m json.tool

# List all registered endpoints
curl -s http://localhost:8080/api/v1/api-endpoints | python3 -m json.tool
```

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customers` | List customers with pagination |
| POST | `/customers` | Create a new customer |
| GET | `/customers/{customerId}` | Get customer by ID |
| PUT | `/customers/{customerId}` | Update customer information |
| POST | `/orders` | Process a new order |
| GET | `/orders/{orderId}` | Get order details |
| GET | `/customers/{customerId}/points` | Get customer points balance |
| POST | `/customers/{customerId}/points` | Manual points adjustment |
| GET | `/customers/{customerId}/tier` | Get customer tier information |
| PUT | `/customers/{customerId}/tier` | Recalculate customer tier |
| POST | `/discounts/calculate` | Calculate available discounts |

**Base URL**: `http://localhost:8080/ecommerce/loyalty/v1`

## Sample Test Data

### Customer IDs
- `550e8400-e29b-41d4-a716-446655440000`

### Order IDs  
- `123e4567-e89b-12d3-a456-426614174000`

### Admin User IDs
- `admin-550e8400-e29b-41d4-a716-446655440001`

## Membership Tiers
- Bronze
- Silver
- Gold
- Platinum

## Testing After System Restart

1. **Start Services**:
   ```bash
   ./manage.sh start
   ```

2. **Verify Database Load**:
   ```bash
   curl -s http://localhost:8080/api/v1/api-endpoints | grep -c "endpoint_path"
   # Should return: 11
   ```

3. **Run Tests**:
   ```bash
   ./test_all_endpoints.sh
   ```

## Response Format

All endpoints return responses in this format:

```json
{
  "status": "success",
  "message": "Endpoint [METHOD] [PATH] processed", 
  "class": "E-commerce Loyalty System API",
  "operation": null,
  "data": {
    "endpoint": { /* endpoint metadata */ },
    "request_data": { /* your payload */ },
    "path_params": { /* URL path parameters */ },
    "query_params": { /* URL query parameters */ },
    "headers": { /* request headers */ },
    "class_id": 55,
    "class_name": "E-commerce Loyalty System API"
  }
}
```

## Troubleshooting

### If endpoints return 404:
1. Check if Praxis is running: `./manage.sh status`
2. Verify database is loaded: `curl http://localhost:8080/api/v1/status`
3. Check registered endpoints: `curl http://localhost:8080/api/v1/api-endpoints`

### If Praxis shows 0 endpoints:
1. Copy updated database: `cp Forge/instance/GEE.db Praxis/data/gee_$(date +%Y%m%d_%H%M%S)_execution_worker.db`
2. Restart Praxis: `./manage.sh praxis-restart`

### If database is missing endpoints:
1. Re-run import: `cd Forge && python import_swagger_enhanced.py ../Swagger/E-commerce_Loyalty_System_API.json`
2. Copy database to Praxis data directory

## Authentication

Currently, endpoints are accessible without authentication. In production, add:

- **Bearer Token**: `Authorization: Bearer <token>`
- **API Key**: `X-API-Key: <api-key>`

## File Structure

```
/mnt/c/Users/rnair/LinuxSharedFS/GEE/GEE_22.33_07.06/
├── ecommerce_api_tests.md      # Complete documentation
├── curl_commands.sh            # Interactive test functions  
├── test_all_endpoints.sh       # Automated test suite
├── json_payloads.json          # Structured payload data
├── README_API_TESTING.md       # This guide
├── Forge/
│   ├── instance/GEE.db         # Source database with endpoints
│   └── import_swagger_enhanced.py  # Import script (modified)
└── Praxis/
    ├── data/                   # Runtime databases
    └── internal/db/manager.go  # Endpoint loading logic (modified)
```

All testing artifacts are now persisted and ready for use after system restarts!