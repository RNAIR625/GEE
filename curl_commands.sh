#!/bin/bash

# E-commerce Loyalty System API - Individual Curl Commands
# Usage: source this file to get individual curl functions
# Or run: ./curl_commands.sh [function_name]

BASE_URL="http://localhost:8080/ecommerce/loyalty/v1"
CUSTOMER_ID="550e8400-e29b-41d4-a716-446655440000"
ORDER_ID="123e4567-e89b-12d3-a456-426614174000"
ADMIN_ID="admin-550e8400-e29b-41d4-a716-446655440001"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${GREEN}=== $1 ===${NC}"
}

print_command() {
    echo -e "${YELLOW}Command:${NC} $1"
}

# 1. List customers with pagination
test_list_customers() {
    print_header "1. LIST CUSTOMERS"
    
    print_command "Basic list customers"
    curl -X GET "${BASE_URL}/customers"
    echo -e "\n"
    
    print_command "List customers with filters"
    curl -X GET "${BASE_URL}/customers?page=1&limit=5&tier=Gold&email=john.doe@example.com"
    echo -e "\n"
}

# 2. Create a new customer
test_create_customer() {
    print_header "2. CREATE CUSTOMER"
    
    print_command "Create new customer"
    curl -X POST "${BASE_URL}/customers" \
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
    echo -e "\n"
}

# 3. Get customer by ID
test_get_customer() {
    print_header "3. GET CUSTOMER BY ID"
    
    print_command "Get customer details"
    curl -X GET "${BASE_URL}/customers/${CUSTOMER_ID}"
    echo -e "\n"
}

# 4. Update customer information
test_update_customer() {
    print_header "4. UPDATE CUSTOMER"
    
    print_command "Update customer information"
    curl -X PUT "${BASE_URL}/customers/${CUSTOMER_ID}" \
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
    echo -e "\n"
}

# 5. Process a new order
test_process_order() {
    print_header "5. PROCESS ORDER"
    
    print_command "Process new order"
    curl -X POST "${BASE_URL}/orders" \
      -H "Content-Type: application/json" \
      -d '{
        "customerId": "'${CUSTOMER_ID}'",
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
    echo -e "\n"
}

# 6. Get order details
test_get_order() {
    print_header "6. GET ORDER DETAILS"
    
    print_command "Get order details"
    curl -X GET "${BASE_URL}/orders/${ORDER_ID}"
    echo -e "\n"
}

# 7. Get customer points balance
test_get_points() {
    print_header "7. GET CUSTOMER POINTS"
    
    print_command "Get points balance (basic)"
    curl -X GET "${BASE_URL}/customers/${CUSTOMER_ID}/points"
    echo -e "\n"
    
    print_command "Get points with history"
    curl -X GET "${BASE_URL}/customers/${CUSTOMER_ID}/points?includeHistory=true&limit=50"
    echo -e "\n"
}

# 8. Manual points adjustment
test_adjust_points() {
    print_header "8. ADJUST CUSTOMER POINTS"
    
    print_command "Manual points adjustment"
    curl -X POST "${BASE_URL}/customers/${CUSTOMER_ID}/points" \
      -H "Content-Type: application/json" \
      -d '{
        "amount": 500,
        "reason": "Compensation for delayed shipment on order #12345",
        "adminUserId": "'${ADMIN_ID}'"
      }'
    echo -e "\n"
}

# 9. Get customer tier information
test_get_tier() {
    print_header "9. GET CUSTOMER TIER"
    
    print_command "Get tier information"
    curl -X GET "${BASE_URL}/customers/${CUSTOMER_ID}/tier"
    echo -e "\n"
}

# 10. Recalculate customer tier
test_recalculate_tier() {
    print_header "10. RECALCULATE CUSTOMER TIER"
    
    print_command "Force tier recalculation"
    curl -X PUT "${BASE_URL}/customers/${CUSTOMER_ID}/tier"
    echo -e "\n"
}

# 11. Calculate available discounts
test_calculate_discounts() {
    print_header "11. CALCULATE DISCOUNTS"
    
    print_command "Calculate available discounts"
    curl -X POST "${BASE_URL}/discounts/calculate" \
      -H "Content-Type: application/json" \
      -d '{
        "customerId": "'${CUSTOMER_ID}'",
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
    echo -e "\n"
}

# Test all endpoints
test_all() {
    echo -e "${GREEN}Testing All E-commerce Loyalty System API Endpoints${NC}"
    echo "=============================================="
    
    test_list_customers
    test_create_customer
    test_get_customer
    test_update_customer
    test_process_order
    test_get_order
    test_get_points
    test_adjust_points
    test_get_tier
    test_recalculate_tier
    test_calculate_discounts
    
    echo -e "${GREEN}=============================================="
    echo "All tests completed!${NC}"
}

# Show available functions
show_help() {
    echo -e "${GREEN}Available test functions:${NC}"
    echo "  test_list_customers     - Test GET /customers"
    echo "  test_create_customer    - Test POST /customers"
    echo "  test_get_customer       - Test GET /customers/{id}"
    echo "  test_update_customer    - Test PUT /customers/{id}"
    echo "  test_process_order      - Test POST /orders"
    echo "  test_get_order          - Test GET /orders/{id}"
    echo "  test_get_points         - Test GET /customers/{id}/points"
    echo "  test_adjust_points      - Test POST /customers/{id}/points"
    echo "  test_get_tier           - Test GET /customers/{id}/tier"
    echo "  test_recalculate_tier   - Test PUT /customers/{id}/tier"
    echo "  test_calculate_discounts - Test POST /discounts/calculate"
    echo "  test_all               - Run all tests"
    echo "  show_help              - Show this help"
    echo ""
    echo -e "${YELLOW}Usage examples:${NC}"
    echo "  ./curl_commands.sh test_all"
    echo "  ./curl_commands.sh test_list_customers"
    echo "  source curl_commands.sh && test_get_customer"
}

# Main execution
if [ $# -eq 0 ]; then
    show_help
else
    case "$1" in
        test_list_customers)     test_list_customers ;;
        test_create_customer)    test_create_customer ;;
        test_get_customer)       test_get_customer ;;
        test_update_customer)    test_update_customer ;;
        test_process_order)      test_process_order ;;
        test_get_order)          test_get_order ;;
        test_get_points)         test_get_points ;;
        test_adjust_points)      test_adjust_points ;;
        test_get_tier)           test_get_tier ;;
        test_recalculate_tier)   test_recalculate_tier ;;
        test_calculate_discounts) test_calculate_discounts ;;
        test_all)                test_all ;;
        help|--help|-h)          show_help ;;
        *)                       echo "Unknown function: $1"; show_help ;;
    esac
fi