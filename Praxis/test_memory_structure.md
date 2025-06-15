# Praxis Memory Structure Implementation

## Overview
This document shows how the GEE flow-related data is loaded into Praxis memory and the structure in which it's organized.

## Memory Structure Implementation

### 1. Models Updated
- **Flow**: Represents GEE_FLOWS table with steps
- **FlowStep**: Represents GEE_FLOW_STEPS with rule associations  
- **Rule**: Represents GEE_RULES table
- **RuleGroup**: Represents GEE_RULES_GROUPS table
- **APIEndpoint**: Represents GEE_API_ENDPOINTS table
- **BaseFunction**: Represents GEE_BASE_FUNCTIONS table
- **AutoFunction**: Enhanced with table metadata

### 2. Cache Structure
```go
type DataCache struct {
    // Existing fields...
    
    // Flow cache for API endpoint processing
    FlowsByID           map[int64]*Flow               
    FlowsByName         map[string]*Flow              
    FlowsByEndpoint     map[string]*Flow              // Key: "METHOD path"
    AllFlows            []*Flow                       
    
    // Rule cache for flow processing
    RuleGroupsByID      map[int64]*RuleGroup          
    RuleGroupsByName    map[string]*RuleGroup         
    RulesByID           map[int64]*Rule               
    RulesByGroup        map[int64][]*Rule             
    
    // API Endpoint cache
    APIEndpointsByID    map[int64]*APIEndpoint        
    APIEndpointsByPath  map[string]*APIEndpoint       // Key: "METHOD path"
    AllAPIEndpoints     []*APIEndpoint                
    
    // Base Function cache
    BaseFunctionsByID   map[int64]*BaseFunction       
    BaseFunctionsByName map[string]*BaseFunction      
    AllBaseFunctions    []*BaseFunction               
}
```

### 3. Loading Process

#### ForgeLoader Methods:
- `LoadFlows()` - Loads flows with their steps and associated rules
- `LoadRuleGroups()` - Loads rule groups with their rules
- `LoadAllRules()` - Loads all rules and associates them with groups
- `LoadAPIEndpoints()` - Loads API endpoints and associates with flows
- `LoadBaseFunctions()` - Loads base functions for calculations

#### Loading Sequence:
1. **Tables & Columns** → Basic table metadata
2. **Auto-Functions** → Generated table accessor functions  
3. **Rule Groups** → Logical groupings of business rules
4. **Rules** → Individual business logic expressions
5. **Flows** → Request-to-response processing sequences
6. **API Endpoints** → REST API definitions with flow associations

### 4. Memory Structure Example

```json
{
  "cache_stats": {
    "is_loaded": true,
    "flows_count": 9,
    "rule_groups_count": 9, 
    "rules_count": 40,
    "api_endpoints_count": 8,
    "auto_functions_count": 24,
    "tables_count": 4
  },
  "flow_structure": {
    "LOYALTY_GET_CUSTOMER_FLOW": {
      "flow_id": 1,
      "flow_name": "LOYALTY_GET_CUSTOMER_FLOW",
      "flow_type": "API",
      "endpoint_path": "/ecommerce/loyalty/v1/customers/{customerId}",
      "http_method": "GET",
      "steps_count": 1,
      "steps": [
        {
          "step_id": 1,
          "step_order": 1,
          "step_name": "Process Customer Request",
          "rule_group_id": 1,
          "rules_count": 5,
          "rules": [
            {
              "rule_id": 1,
              "rule_name": "VALIDATE_GET_CUSTOMER_REQUEST",
              "rule_type": "VALIDATION",
              "rule_priority": 1
            },
            {
              "rule_id": 2, 
              "rule_name": "EXTRACT_CUSTOMER_ID",
              "rule_type": "EXTRACTION",
              "rule_priority": 2
            },
            {
              "rule_id": 3,
              "rule_name": "LOOKUP_CUSTOMER_DATA", 
              "rule_type": "LOOKUP",
              "rule_priority": 3
            },
            {
              "rule_id": 4,
              "rule_name": "CALCULATE_CUSTOMER_TIER",
              "rule_type": "BUSINESS", 
              "rule_priority": 4
            },
            {
              "rule_id": 5,
              "rule_name": "POPULATE_GET_CUSTOMER_RESPONSE",
              "rule_type": "RESPONSE",
              "rule_priority": 5
            }
          ]
        }
      ]
    }
  },
  "index_structure": {
    "flows_by_endpoint": [
      "GET /ecommerce/loyalty/v1/customers/{customerId}",
      "PUT /ecommerce/loyalty/v1/customers/{customerId}",
      "GET /ecommerce/loyalty/v1/orders",
      "GET /ecommerce/loyalty/v1/orders/{orderId}",
      "GET /ecommerce/loyalty/v1/customers/{customerId}/points",
      "PUT /ecommerce/loyalty/v1/customers/{customerId}/points",
      "GET /ecommerce/loyalty/v1/customers/{customerId}/tier", 
      "PUT /ecommerce/loyalty/v1/customers/{customerId}/tier",
      "POST /ecommerce/loyalty/v1/discounts/calculate"
    ],
    "rule_groups_by_name": [
      "LOYALTY_GET_CUSTOMER",
      "LOYALTY_UPDATE_CUSTOMER", 
      "LOYALTY_GET_ORDERS",
      "LOYALTY_GET_ORDER",
      "LOYALTY_GET_POINTS",
      "LOYALTY_UPDATE_POINTS",
      "LOYALTY_GET_TIER", 
      "LOYALTY_UPDATE_TIER",
      "LOYALTY_CALCULATE_DISCOUNT"
    ]
  }
}
```

### 5. API Endpoints for Testing

#### Memory Structure Inspection:
- `GET /api/v1/memory/structure` - Complete memory structure
- `GET /api/v1/flows/cached` - All cached flows with steps and rules
- `GET /api/v1/rules/groups` - All rule groups with rules
- `GET /api/v1/rules` - All individual rules
- `GET /api/v1/auto-functions` - All auto-generated table functions

#### Loyalty-Specific Endpoints:
- `GET /api/v1/loyalty/endpoints` - Loyalty API endpoints with flows
- `POST /api/v1/loyalty/reload` - Reload all loyalty data
- `GET /api/v1/base-functions` - Base functions for calculations

#### Auto-Function Testing:
- `GET /api/v1/auto-functions` - List all table functions
- `POST /api/v1/auto-functions/execute/{functionName}` - Execute function
- `POST /api/v1/auto-functions/reload` - Reload from Forge

### 6. Flow Execution Structure

Each loyalty API endpoint follows this pattern:

1. **Flow Identification**: Match HTTP method + path to flow
2. **Step Execution**: Execute flow steps in order
3. **Rule Processing**: Execute rules within each step by priority:
   - **VALIDATION** (Priority 1): Validate request data
   - **EXTRACTION** (Priority 2): Extract data into GEE_WORK fields  
   - **LOOKUP** (Priority 3): Query external databases via auto-functions
   - **BUSINESS** (Priority 4): Apply business logic calculations
   - **RESPONSE** (Priority 5): Populate response structure

4. **Auto-Function Integration**: Rules call generated functions like:
   - `CUSTOMERS_pk_exists(customerId)` - Check if customer exists
   - `CUSTOMERS_get_email(customerId)` - Get customer email
   - `CALCULATE_TIER(totalSpent)` - Calculate membership tier

### 7. Implementation Benefits

- **Performance**: All data loaded in memory for fast access
- **Consistency**: Single source of truth from Forge database
- **Flexibility**: Dynamic rule changes without code deployment  
- **Scalability**: Hierarchical caching with O(1) lookups
- **Debugging**: Complete structure visibility via API endpoints
- **Auto-Functions**: Generated table accessors with caching

The implementation successfully bridges Forge's rule-based configuration with Praxis's high-performance execution engine.