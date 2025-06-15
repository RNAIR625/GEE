#!/bin/bash

# Canadian Tax Calculation Flow Test Script
# Tests all Canadian provinces and tax scenarios

echo "🇨🇦 Canadian Tax Calculation Flow Test Suite"
echo "============================================="

# Configuration
PRAXIS_URL="http://localhost:8080"
FLOW_ID="1"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to test postal code
test_postal_code() {
    local postal_code=$1
    local province=$2
    local expected_rate=$3
    local base_amount=$4
    
    echo -e "\n${BLUE}Testing: $postal_code ($province)${NC}"
    echo "Expected rate: $expected_rate%, Base amount: \$$base_amount"
    
    response=$(curl -s -X POST "$PRAXIS_URL/api/v1/flows/$FLOW_ID/execute" \
        -H "Content-Type: application/json" \
        -d "{\"postal_code\":\"$postal_code\",\"base_amount\":$base_amount}")
    
    if [ $? -eq 0 ]; then
        # Parse JSON response
        postal_exists=$(echo "$response" | jq -r '.result.variables.postal_code_exists // false')
        gst_rate=$(echo "$response" | jq -r '.result.variables.gst_rate // 0')
        hst_rate=$(echo "$response" | jq -r '.result.variables.hst_rate // 0')
        pst_rate=$(echo "$response" | jq -r '.result.variables.pst_rate // 0')
        total_tax=$(echo "$response" | jq -r '.result.variables.total_tax // 0')
        success=$(echo "$response" | jq -r '.success // false')
        
        if [ "$success" = "true" ] && [ "$postal_exists" = "true" ]; then
            echo -e "${GREEN}✓ Postal code validation: PASSED${NC}"
            echo "  GST: $(echo "$gst_rate * 100" | bc)%"
            echo "  HST: $(echo "$hst_rate * 100" | bc)%"
            echo "  PST: $(echo "$pst_rate * 100" | bc)%"
            echo "  Total tax: \$$total_tax"
            
            # Calculate expected tax
            expected_tax=$(echo "scale=2; $base_amount * $expected_rate / 100" | bc)
            
            # Check if calculated tax matches expected (within 0.01 tolerance)
            diff=$(echo "scale=2; $total_tax - $expected_tax" | bc)
            abs_diff=$(echo "$diff" | sed 's/-//')
            
            if (( $(echo "$abs_diff <= 0.01" | bc -l) )); then
                echo -e "${GREEN}✓ Tax calculation: PASSED (Expected: \$$expected_tax)${NC}"
            else
                echo -e "${RED}✗ Tax calculation: FAILED (Expected: \$$expected_tax, Got: \$$total_tax)${NC}"
            fi
        else
            echo -e "${RED}✗ Flow execution failed or postal code invalid${NC}"
            echo "Response: $response"
        fi
    else
        echo -e "${RED}✗ Connection failed${NC}"
    fi
}

# Function to test invalid postal codes
test_invalid_postal_code() {
    local postal_code=$1
    
    echo -e "\n${YELLOW}Testing invalid postal code: $postal_code${NC}"
    
    response=$(curl -s -X POST "$PRAXIS_URL/api/v1/flows/$FLOW_ID/execute" \
        -H "Content-Type: application/json" \
        -d "{\"postal_code\":\"$postal_code\",\"base_amount\":100}")
    
    postal_exists=$(echo "$response" | jq -r '.result.variables.postal_code_exists // false')
    errors=$(echo "$response" | jq -r '.result.errors | length')
    
    if [ "$postal_exists" = "false" ] || [ "$errors" -gt "0" ]; then
        echo -e "${GREEN}✓ Invalid postal code correctly rejected${NC}"
    else
        echo -e "${RED}✗ Invalid postal code incorrectly accepted${NC}"
    fi
}

# Check if Praxis is running
echo "Checking Praxis server status..."
if curl -s "$PRAXIS_URL/api/v1/health" > /dev/null; then
    echo -e "${GREEN}✓ Praxis server is running${NC}"
else
    echo -e "${RED}✗ Praxis server is not accessible at $PRAXIS_URL${NC}"
    echo "Please start Praxis server first."
    exit 1
fi

# Test all Canadian provinces
echo -e "\n${BLUE}=== PROVINCIAL TAX RATE TESTS ===${NC}"

# HST Provinces (replaces GST+PST)
test_postal_code "M5V" "Ontario" "13.0" "100"
test_postal_code "E1C" "New Brunswick" "15.0" "100"
test_postal_code "B3H" "Nova Scotia" "15.0" "100"
test_postal_code "C1A" "Prince Edward Island" "15.0" "100"
test_postal_code "A1C" "Newfoundland and Labrador" "15.0" "100"

# GST + PST Provinces
test_postal_code "H3A" "Quebec" "14.975" "100"  # 5% + 9.975%
test_postal_code "V6B" "British Columbia" "12.0" "100"  # 5% + 7%
test_postal_code "R3C" "Manitoba" "12.0" "100"  # 5% + 7%
test_postal_code "S4P" "Saskatchewan" "11.0" "100"  # 5% + 6%

# GST Only Provinces/Territories
test_postal_code "T2P" "Alberta" "5.0" "100"
test_postal_code "Y1A" "Yukon" "5.0" "100"
test_postal_code "X1A" "Northwest Territories" "5.0" "100"
test_postal_code "X0A" "Nunavut" "5.0" "100"

# Test different amounts
echo -e "\n${BLUE}=== AMOUNT CALCULATION TESTS ===${NC}"
test_postal_code "M5V" "Ontario" "13.0" "1000"
test_postal_code "H3A" "Quebec" "14.975" "500"
test_postal_code "T2P" "Alberta" "5.0" "250"

# Test edge cases
echo -e "\n${BLUE}=== EDGE CASE TESTS ===${NC}"
test_postal_code "M5V" "Ontario (Small amount)" "13.0" "0.01"
test_postal_code "H3A" "Quebec (Large amount)" "14.975" "10000"

# Test invalid postal codes
echo -e "\n${BLUE}=== INVALID INPUT TESTS ===${NC}"
test_invalid_postal_code "123"     # Numbers only
test_invalid_postal_code "AAA"     # Letters only  
test_invalid_postal_code "Z9Z"     # Invalid first letter
test_invalid_postal_code ""        # Empty string

# Performance test
echo -e "\n${BLUE}=== PERFORMANCE TEST ===${NC}"
echo "Running 10 concurrent requests..."
start_time=$(date +%s.%N)

for i in {1..10}; do
    (curl -s -X POST "$PRAXIS_URL/api/v1/flows/$FLOW_ID/execute" \
        -H "Content-Type: application/json" \
        -d '{"postal_code":"M5V","base_amount":100}' > /dev/null) &
done

wait  # Wait for all background processes

end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)
echo "Completed 10 requests in ${duration}s"
echo "Average: $(echo "scale=3; $duration / 10" | bc)s per request"

# System health check
echo -e "\n${BLUE}=== SYSTEM HEALTH CHECK ===${NC}"

flows_response=$(curl -s "$PRAXIS_URL/api/v1/flows")
flow_count=$(echo "$flows_response" | jq -r '.count // 0')

if [ "$flow_count" -gt "0" ]; then
    echo -e "${GREEN}✓ Flows deployed: $flow_count${NC}"
else
    echo -e "${RED}✗ No flows deployed${NC}"
fi

# Summary
echo -e "\n${BLUE}=== TEST SUMMARY ===${NC}"
echo "Tax calculation flow testing completed."
echo "Check the results above for any failures."
echo ""
echo "To view detailed execution logs:"
echo "  tail -f /Users/administrator/Downloads/GEE/Praxis/praxis.log"
echo ""
echo "To access the health dashboard:"
echo "  open /Users/administrator/Downloads/GEE/test/health_check.html"