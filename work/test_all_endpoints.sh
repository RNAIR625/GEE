#!/bin/bash

echo "Testing E-commerce Loyalty System API Endpoints"
echo "=============================================="

# Base URL
BASE_URL="http://localhost:8080/ecommerce/loyalty/v1"

# Test customer ID
CUSTOMER_ID="550e8400-e29b-41d4-a716-446655440000"
ORDER_ID="123e4567-e89b-12d3-a456-426614174000"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "\n${GREEN}Testing: $method $endpoint${NC}"
    echo "Description: $description"
    
    if [ -z "$data" ]; then
        response=$(curl -s -X $method "${BASE_URL}${endpoint}")
    else
        response=$(curl -s -X $method "${BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Success${NC}"
        echo "Response: $response" | head -n 3
    else
        echo -e "${RED}✗ Failed${NC}"
    fi
}

# Test all endpoints
echo -e "\n1. LIST CUSTOMERS"
test_endpoint "GET" "/customers?page=1&limit=5" "" "List customers with pagination"

echo -e "\n2. CREATE CUSTOMER"
test_endpoint "POST" "/customers" '{
    "email": "test.user@example.com",
    "firstName": "Test",
    "lastName": "User",
    "preferences": {
        "emailNotifications": true,
        "smsNotifications": false,
        "preferredCategories": ["Electronics"]
    }
}' "Create a new customer"

echo -e "\n3. GET CUSTOMER BY ID"
test_endpoint "GET" "/customers/$CUSTOMER_ID" "" "Get customer details"

echo -e "\n4. UPDATE CUSTOMER"
test_endpoint "PUT" "/customers/$CUSTOMER_ID" '{
    "email": "updated.email@example.com",
    "firstName": "Updated",
    "lastName": "Name"
}' "Update customer information"

echo -e "\n5. PROCESS ORDER"
test_endpoint "POST" "/orders" '{
    "customerId": "'$CUSTOMER_ID'",
    "items": [{
        "productId": "PROD-001",
        "name": "Test Product",
        "price": 99.99,
        "quantity": 1,
        "category": "Electronics",
        "isPromotional": false
    }],
    "subtotal": 99.99
}' "Process a new order"

echo -e "\n6. GET ORDER DETAILS"
test_endpoint "GET" "/orders/$ORDER_ID" "" "Get order details"

echo -e "\n7. GET CUSTOMER POINTS"
test_endpoint "GET" "/customers/$CUSTOMER_ID/points" "" "Get customer points balance"

echo -e "\n8. ADJUST POINTS"
test_endpoint "POST" "/customers/$CUSTOMER_ID/points" '{
    "amount": 100,
    "reason": "Test points adjustment",
    "adminUserId": "admin-001"
}' "Manual points adjustment"

echo -e "\n9. GET CUSTOMER TIER"
test_endpoint "GET" "/customers/$CUSTOMER_ID/tier" "" "Get customer tier information"

echo -e "\n10. RECALCULATE TIER"
test_endpoint "PUT" "/customers/$CUSTOMER_ID/tier" "" "Recalculate customer tier"

echo -e "\n11. CALCULATE DISCOUNTS"
test_endpoint "POST" "/discounts/calculate" '{
    "customerId": "'$CUSTOMER_ID'",
    "items": [{
        "productId": "PROD-001",
        "name": "Test Product",
        "price": 100.00,
        "quantity": 2,
        "category": "Electronics",
        "isPromotional": true
    }],
    "subtotal": 200.00
}' "Calculate available discounts"

echo -e "\n=============================================="
echo "Testing complete!"