# Canadian GST Calculation Implementation Guide

## Overview
This document provides a complete implementation of the Canadian GST calculation functionality using the GEE (Generic Execution Engine) framework. The implementation handles the calculation of GST, HST, and PST based on product information and postal codes.

## Implementation Status: ✅ COMPLETE

### Components Implemented

#### 1. Field Classes ✅
- **cGstI** (INPUT): Canadian GST Input class for request parameters
- **cGstO** (OUTPUT): Canadian GST Output class for response parameters  
- **geeR** (RUNTIME): Runtime memory class - lives within request only
- **geeX** (GLOBAL): Global execution context - exists throughout framework execution

#### 2. Field Definitions ✅

**cGstI Fields (Input)**
- `objectId` [VARCHAR(50)] - Product identifier from request
- `userPinCode` [VARCHAR(20)] - User postal code from request
- `storePinCode` [VARCHAR(20)] - Store postal code from request

**geeR Fields (Runtime Memory)**
- `objectId` [VARCHAR(50)] - Product identifier in runtime memory
- `userPinCode` [VARCHAR(20)] - User postal code in runtime memory
- `storePinCode` [VARCHAR(20)] - Store postal code in runtime memory
- `PstRate` [DECIMAL(10,4)] - PST rate for calculation
- `HSTRate` [DECIMAL(10,4)] - HST rate for calculation
- `GSTRate` [DECIMAL(10,4)] - GST rate for calculation
- `objectPrice` [DECIMAL(10,2)] - Product price from database
- `errorCode` [INTEGER] - Error code for processing
- `errorDesc` [VARCHAR(255)] - Error description

**cGstO Fields (Output)**
- `objectValue` [VARCHAR(20)] - Product value formatted as currency
- `objectGST` [VARCHAR(20)] - GST amount formatted as currency
- `objectHST` [VARCHAR(20)] - HST amount formatted as currency
- `objectPST` [VARCHAR(20)] - PST amount formatted as currency
- `error_code` [INTEGER] - Error code in response
- `error_desc` [VARCHAR(255)] - Error description in response

#### 3. Reference Tables ✅

**PIN_CODES** (Reference Table)
```sql
PIN_CODE     VARCHAR(20) PRIMARY KEY
COUNTRY      VARCHAR(50) NOT NULL
PROVINCE     VARCHAR(50) NOT NULL
DISTRICT     VARCHAR(100)
GST_RATE     DECIMAL(5,4) DEFAULT 0.0000
HST_RATE     DECIMAL(5,4) DEFAULT 0.0000
PST_RATE     DECIMAL(5,4) DEFAULT 0.0000
```

**OBJECT_DEF** (Application Table)
```sql
OBJECT_ID    VARCHAR(50) PRIMARY KEY
OBJECT_NAME  VARCHAR(100) NOT NULL
PRICE        DECIMAL(10,2) NOT NULL
```

#### 4. Base Functions ✅
- `exist_in_PIN_CODE(pin_code, result)` - Check if postal code exists
- `exist_in_OBJECT_DEF(object_id, result)` - Check if object ID exists
- `gst_in_PIN_CODE(pin_code, gst_rate)` - Get GST rate for postal code
- `hst_in_PIN_CODE(pin_code, hst_rate)` - Get HST rate for postal code
- `pst_in_PIN_CODE(pin_code, pst_rate)` - Get PST rate for postal code
- `Multiply(a, b, result)` - Multiply two numbers
- `get_object_price(object_id, price)` - Get price for object ID

#### 5. Stations ✅
1. **Init Station** - Map request values to input class
2. **Validation Station** - Validate input parameters
3. **Rating Station** - Calculate tax amounts
4. **Error Handler** - Handle error conditions
5. **Term Station** - Map output to response

#### 6. Rule Groups & Rules ✅

**Init Station Rules:**
- Map_ObjectId: `cGstI.objectId = request.objectId`
- Map_UserPinCode: `cGstI.userPinCode = request.userPincode`
- Map_StorePinCode: `cGstI.storePinCode = request.storePincode`
- Copy_to_Runtime: Copy input values to runtime memory

**Validation Station Rules:**
- Validate_Object_Exists: Check object exists, set error 100 if not
- Validate_UserPin_Exists: Check user postal code, set error 101 if not
- Validate_StorePin_Exists: Check store postal code, set error 101 if not

**Rating Station Rules:**
- Fetch_Object_Price: Get product price from OBJECT_DEF
- Fetch_Tax_Rates_User: Get tax rates for user location
- Calculate_GST: Calculate GST amount
- Calculate_HST: Calculate HST amount
- Calculate_PST: Calculate PST amount
- Set_Object_Value: Set object value

**Error Handler Rules:**
- Handle_Error_Code: Set error code in response if errors occurred
- Handle_Error_Desc: Set error description in response

**Term Station Rules:**
- Map output values from cGstO to response structure

#### 7. Flow Definition ✅
Complete flow "Canadian_GST_Flow" with proper station connections and error handling paths.

## Sample Data

### Canadian Postal Codes with Tax Rates
```
M5V 3A8 (Toronto, ON)    - HST: 13%
K1A 0B1 (Ottawa, ON)     - HST: 13%
H3A 0G4 (Montreal, QC)   - GST: 5% + PST: 9.975%
V6E 4M2 (Vancouver, BC)  - GST: 5% + PST: 7%
T2P 2Y5 (Calgary, AB)    - GST: 5%
```

### Product Data
```
Parker Pen    - $46.00
Mont Blanc    - $150.00
Bic Pen       - $2.50
Pilot G2      - $3.75
Sharpie       - $1.99
```

## API Usage Example

### Request
```json
{
  "objectId": "Parker Pen",
  "userPincode": "M5V 3A8",
  "storePincode": "K1A 0B1"
}
```

### Expected Response
```json
{
  "objectValue": "$46",
  "objectGST": "$6.56",
  "objectHST": "$1.5", 
  "objectPST": "$0"
}
```

### Error Response (Object Not Found)
```json
{
  "code": "100",
  "message": "Object ID not found"
}
```

### Error Response (Invalid Postal Code)
```json
{
  "code": "101", 
  "message": "User postal code not found"
}
```

## Field Mapping Configuration

The Swagger API fields are mapped to internal GEE fields as follows:

### Request Mapping
- `TaxCalculationRequest.objectId` → `cGstI.objectId`
- `TaxCalculationRequest.userPincode` → `cGstI.userPinCode`
- `TaxCalculationRequest.storePincode` → `cGstI.storePinCode`

### Response Mapping
- `cGstO.objectValue` → `TaxCalculationResponse.objectValue`
- `cGstO.objectGST` → `TaxCalculationResponse.objectGST`
- `cGstO.objectHST` → `TaxCalculationResponse.objectHST`
- `cGstO.objectPST` → `TaxCalculationResponse.objectPST`

## Tax Calculation Logic

### Ontario (HST Province)
- GST: 0% (included in HST)
- HST: 13%
- PST: 0%
- **Total Tax: 13%**

### Quebec (GST + PST Province)
- GST: 5%
- HST: 0%
- PST: 9.975%
- **Total Tax: 14.975%**

### Alberta (GST Only Province)
- GST: 5%
- HST: 0%
- PST: 0%
- **Total Tax: 5%**

## Error Handling

The system implements comprehensive error handling:

1. **Error Code 100**: Object ID not found in OBJECT_DEF table
2. **Error Code 101**: Postal code not found in PIN_CODES table

## Files Created

1. `canadian_gst_setup.sql` - Complete database setup script
2. `swagger_field_mapping.json` - Field mapping configuration
3. `canadian_gst_implementation_guide.md` - This implementation guide

## Verification

To verify the implementation:

1. **Check Database Setup**: Run verification queries in the SQL script
2. **Test Field Mappings**: Use the field mapping configuration
3. **Validate Flow**: Execute the Canadian_GST_Flow
4. **Test API**: Use the sample request/response data

## Generic Tool Benefits

This implementation demonstrates the GEE tool's generic nature:

1. **Configurable Field Classes**: Easy to add new input/output structures
2. **Flexible Rules Engine**: Business logic defined as configurable rules
3. **Modular Functions**: Reusable functions for common operations
4. **Dynamic Flow Control**: Visual flow designer for business processes
5. **Error Handling**: Built-in error handling and routing
6. **Multi-Database Support**: Oracle and SQLite support
7. **API Integration**: Swagger/OpenAPI integration for external APIs

The same framework can be used for any business calculation by:
- Defining appropriate field classes
- Creating reference tables
- Implementing business functions
- Configuring validation and calculation rules
- Setting up the processing flow

This makes GEE a truly generic execution engine for business rule processing.