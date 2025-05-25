-- Canadian GST Calculation Implementation
-- This script sets up the complete structure for Canadian GST calculation

-- ============================================
-- 1. CREATE FIELD CLASSES
-- ============================================

-- Input class for Canadian GST requests
INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION) 
VALUES ('cGstI', 'INPUT', 'Canadian GST Input class for request parameters');

-- Output class for Canadian GST responses  
INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION)
VALUES ('cGstO', 'OUTPUT', 'Canadian GST Output class for response parameters');

-- Internal runtime memory class
INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION)
VALUES ('geeR', 'RUNTIME', 'Generic runtime memory class - lives within request only');

-- Global execution context class
INSERT INTO GEE_FIELD_CLASSES (FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION)
VALUES ('geeX', 'GLOBAL', 'Global execution context - exists throughout framework execution');

-- ============================================
-- 2. CREATE FIELDS FOR EACH CLASS
-- ============================================

-- cGstI Fields (Input)
INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_DESCRIPTION) VALUES 
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstI'), 'objectId', 'VARCHAR', 50, 'Product identifier from request'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstI'), 'userPinCode', 'VARCHAR', 20, 'User postal code from request'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstI'), 'storePinCode', 'VARCHAR', 20, 'Store postal code from request');

-- geeR Fields (Runtime Memory)
INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DESCRIPTION) VALUES 
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'objectId', 'VARCHAR', 50, NULL, 'Product identifier in runtime memory'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'userPinCode', 'VARCHAR', 20, NULL, 'User postal code in runtime memory'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'storePinCode', 'VARCHAR', 20, NULL, 'Store postal code in runtime memory'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'PstRate', 'DECIMAL', 10, 4, 'PST rate for calculation'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'HSTRate', 'DECIMAL', 10, 4, 'HST rate for calculation'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'GSTRate', 'DECIMAL', 10, 4, 'GST rate for calculation'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'objectPrice', 'DECIMAL', 10, 2, 'Product price from database'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'errorCode', 'INTEGER', NULL, NULL, 'Error code for processing'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'errorDesc', 'VARCHAR', 255, NULL, 'Error description');

-- cGstO Fields (Output)
INSERT INTO GEE_FIELDS (GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, GF_PRECISION_SIZE, GF_DESCRIPTION) VALUES 
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'objectValue', 'VARCHAR', 20, NULL, 'Product value formatted as currency'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'objectGST', 'VARCHAR', 20, NULL, 'GST amount formatted as currency'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'objectHST', 'VARCHAR', 20, NULL, 'HST amount formatted as currency'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'objectPST', 'VARCHAR', 20, NULL, 'PST amount formatted as currency'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'error_code', 'INTEGER', NULL, NULL, 'Error code in response'),
((SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'error_desc', 'VARCHAR', 255, NULL, 'Error description in response');

-- ============================================
-- 3. CREATE REFERENCE TABLES
-- ============================================

-- PIN_CODES reference table
CREATE TABLE PIN_CODES (
    PIN_CODE VARCHAR(20) PRIMARY KEY,
    COUNTRY VARCHAR(50) NOT NULL,
    PROVINCE VARCHAR(50) NOT NULL,
    DISTRICT VARCHAR(100),
    GST_RATE DECIMAL(5,4) DEFAULT 0.0000,
    HST_RATE DECIMAL(5,4) DEFAULT 0.0000,
    PST_RATE DECIMAL(5,4) DEFAULT 0.0000,
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME
);

-- OBJECT_DEF application table
CREATE TABLE OBJECT_DEF (
    OBJECT_ID VARCHAR(50) PRIMARY KEY,
    OBJECT_NAME VARCHAR(100) NOT NULL,
    PRICE DECIMAL(10,2) NOT NULL,
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME
);

-- Register tables in GEE_TABLES
INSERT INTO GEE_TABLES (TABLE_NAME, TABLE_TYPE, DESCRIPTION) VALUES 
('PIN_CODES', 'REFERENCE', 'Reference table for postal codes and tax rates'),
('OBJECT_DEF', 'APPLICATION', 'Application table for product definitions and pricing');

-- ============================================
-- 4. INSERT SAMPLE DATA
-- ============================================

-- Sample Canadian postal codes with tax rates
INSERT INTO PIN_CODES (PIN_CODE, COUNTRY, PROVINCE, DISTRICT, GST_RATE, HST_RATE, PST_RATE) VALUES 
('M5V 3A8', 'Canada', 'Ontario', 'Toronto', 0.0000, 0.1300, 0.0000),  -- Ontario: 13% HST only
('K1A 0B1', 'Canada', 'Ontario', 'Ottawa', 0.0000, 0.1300, 0.0000),   -- Ontario: 13% HST only
('H3A 0G4', 'Canada', 'Quebec', 'Montreal', 0.0500, 0.0000, 0.0975),  -- Quebec: 5% GST + 9.975% PST
('V6E 4M2', 'Canada', 'British Columbia', 'Vancouver', 0.0500, 0.0000, 0.0700), -- BC: 5% GST + 7% PST
('T2P 2Y5', 'Canada', 'Alberta', 'Calgary', 0.0500, 0.0000, 0.0000),  -- Alberta: 5% GST only
('S7N 2R4', 'Canada', 'Saskatchewan', 'Saskatoon', 0.0500, 0.0000, 0.0600), -- SK: 5% GST + 6% PST
('R3C 4A5', 'Canada', 'Manitoba', 'Winnipeg', 0.0500, 0.0000, 0.0700), -- MB: 5% GST + 7% PST
('E1C 8K6', 'Canada', 'New Brunswick', 'Moncton', 0.0000, 0.1500, 0.0000), -- NB: 15% HST only
('B3H 1A6', 'Canada', 'Nova Scotia', 'Halifax', 0.0000, 0.1500, 0.0000), -- NS: 15% HST only
('C1A 7M4', 'Canada', 'Prince Edward Island', 'Charlottetown', 0.0000, 0.1500, 0.0000), -- PEI: 15% HST only
('A1C 6H6', 'Canada', 'Newfoundland and Labrador', 'St. Johns', 0.0000, 0.1500, 0.0000); -- NL: 15% HST only

-- Sample product data
INSERT INTO OBJECT_DEF (OBJECT_ID, OBJECT_NAME, PRICE) VALUES 
('Parker Pen', 'Parker Fountain Pen Premium', 46.00),
('Mont Blanc', 'Mont Blanc Luxury Pen', 150.00),
('Bic Pen', 'Bic Ballpoint Pen', 2.50),
('Pilot G2', 'Pilot G2 Gel Pen', 3.75),
('Sharpie', 'Sharpie Permanent Marker', 1.99);

-- ============================================
-- 5. CREATE BASE FUNCTIONS
-- ============================================

-- Function to check if PIN code exists
INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('exist_in_PIN_CODE', 2, 'Check if postal code exists in PIN_CODES table');

INSERT INTO GEE_BASE_FUNCTIONS_PARAMS (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION) VALUES 
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'exist_in_PIN_CODE'), 1, 'pin_code', 'VARCHAR', 'Postal code to check'),
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'exist_in_PIN_CODE'), 2, 'result', 'INTEGER', 'Result flag (1=exists, 0=not exists)');

-- Function to check if object exists
INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('exist_in_OBJECT_DEF', 2, 'Check if object ID exists in OBJECT_DEF table');

INSERT INTO GEE_BASE_FUNCTIONS_PARAMS (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION) VALUES 
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'exist_in_OBJECT_DEF'), 1, 'object_id', 'VARCHAR', 'Object ID to check'),
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'exist_in_OBJECT_DEF'), 2, 'result', 'INTEGER', 'Result flag (1=exists, 0=not exists)');

-- Functions to get tax rates
INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('gst_in_PIN_CODE', 2, 'Get GST rate for postal code');

INSERT INTO GEE_BASE_FUNCTIONS_PARAMS (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION) VALUES 
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'gst_in_PIN_CODE'), 1, 'pin_code', 'VARCHAR', 'Postal code'),
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'gst_in_PIN_CODE'), 2, 'gst_rate', 'DECIMAL', 'GST rate for postal code');

INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('hst_in_PIN_CODE', 2, 'Get HST rate for postal code');

INSERT INTO GEE_BASE_FUNCTIONS_PARAMS (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION) VALUES 
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'hst_in_PIN_CODE'), 1, 'pin_code', 'VARCHAR', 'Postal code'),
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'hst_in_PIN_CODE'), 2, 'hst_rate', 'DECIMAL', 'HST rate for postal code');

INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('pst_in_PIN_CODE', 2, 'Get PST rate for postal code');

INSERT INTO GEE_BASE_FUNCTIONS_PARAMS (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION) VALUES 
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'pst_in_PIN_CODE'), 1, 'pin_code', 'VARCHAR', 'Postal code'),
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'pst_in_PIN_CODE'), 2, 'pst_rate', 'DECIMAL', 'PST rate for postal code');

-- Multiply function
INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('Multiply', 3, 'Multiply two numbers');

INSERT INTO GEE_BASE_FUNCTIONS_PARAMS (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION) VALUES 
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'Multiply'), 1, 'a', 'DECIMAL', 'First number'),
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'Multiply'), 2, 'b', 'DECIMAL', 'Second number'),
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'Multiply'), 3, 'result', 'DECIMAL', 'Result of multiplication');

-- Function to get object price
INSERT INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('get_object_price', 2, 'Get price for object ID');

INSERT INTO GEE_BASE_FUNCTIONS_PARAMS (GBF_ID, GBF_SEQ, PARAM_NAME, PARAM_TYPE, DESCRIPTION) VALUES 
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'get_object_price'), 1, 'object_id', 'VARCHAR', 'Object ID'),
((SELECT GBF_ID FROM GEE_BASE_FUNCTIONS WHERE FUNC_NAME = 'get_object_price'), 2, 'price', 'DECIMAL', 'Object price');

-- ============================================
-- 6. CREATE STATIONS
-- ============================================

INSERT INTO GEE_STATIONS (STATION_NAME, DESCRIPTION, STATION_TYPE, ICON, COLOR_CODE) VALUES 
('Init Station', 'Map request values to input class', 'INPUT', 'fas fa-play', '#28a745'),
('Validation Station', 'Validate input parameters', 'PROCESS', 'fas fa-check-circle', '#ffc107'),
('Rating Station', 'Calculate tax amounts', 'PROCESS', 'fas fa-calculator', '#007bff'),
('Error Handler', 'Handle error conditions', 'PROCESS', 'fas fa-exclamation-triangle', '#dc3545'),
('Term Station', 'Map output to response', 'OUTPUT', 'fas fa-flag-checkered', '#6c757d');

-- ============================================
-- 7. CREATE RULE GROUPS
-- ============================================

-- Init Station Rule Group
INSERT INTO GEE_RULES_GROUPS (GROUP_NAME, COND_TYPE, DESCRIPTION) VALUES 
('Init_Rules', 'ALL', 'Rules to map request values to cGstI class');

-- Validation Station Rule Groups
INSERT INTO GEE_RULES_GROUPS (GROUP_NAME, COND_TYPE, DESCRIPTION) VALUES 
('Validation_Rules', 'ALL', 'Rules to validate input parameters');

-- Rating Station Rule Groups
INSERT INTO GEE_RULES_GROUPS (GROUP_NAME, COND_TYPE, DESCRIPTION) VALUES 
('Rating_Rules', 'ALL', 'Rules to calculate tax amounts');

-- Error Handler Rule Groups
INSERT INTO GEE_RULES_GROUPS (GROUP_NAME, COND_TYPE, DESCRIPTION) VALUES 
('Error_Rules', 'ANY', 'Rules to handle error conditions');

-- Term Station Rule Groups
INSERT INTO GEE_RULES_GROUPS (GROUP_NAME, COND_TYPE, DESCRIPTION) VALUES 
('Term_Rules', 'ALL', 'Rules to map output to response');

-- ============================================
-- 8. LINK STATIONS TO RULE GROUPS
-- ============================================

INSERT INTO GEE_STATION_RULE_GROUPS (STATION_ID, GRG_ID, SEQUENCE, IS_REQUIRED) VALUES 
((SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Init Station'), (SELECT GRG_ID FROM GEE_RULES_GROUPS WHERE GROUP_NAME = 'Init_Rules'), 1, 1),
((SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Validation Station'), (SELECT GRG_ID FROM GEE_RULES_GROUPS WHERE GROUP_NAME = 'Validation_Rules'), 1, 1),
((SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Rating Station'), (SELECT GRG_ID FROM GEE_RULES_GROUPS WHERE GROUP_NAME = 'Rating_Rules'), 1, 1),
((SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Error Handler'), (SELECT GRG_ID FROM GEE_RULES_GROUPS WHERE GROUP_NAME = 'Error_Rules'), 1, 0),
((SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Term Station'), (SELECT GRG_ID FROM GEE_RULES_GROUPS WHERE GROUP_NAME = 'Term_Rules'), 1, 1);

-- ============================================
-- 9. CREATE INDIVIDUAL RULES
-- ============================================

-- Init Station Rules
INSERT INTO GEE_RULES (RULE_NAME, GFC_ID, RULE_TYPE, DESCRIPTION, CONDITION_CODE, ACTION_CODE) VALUES 
('Map_ObjectId', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstI'), 'ASSIGNMENT', 'Map request objectId to cGstI.objectId', 'TRUE', 'cGstI.objectId = request.objectId'),
('Map_UserPinCode', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstI'), 'ASSIGNMENT', 'Map request userPincode to cGstI.userPinCode', 'TRUE', 'cGstI.userPinCode = request.userPincode'),
('Map_StorePinCode', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstI'), 'ASSIGNMENT', 'Map request storePincode to cGstI.storePinCode', 'TRUE', 'cGstI.storePinCode = request.storePincode'),
('Copy_to_Runtime', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'ASSIGNMENT', 'Copy input values to runtime memory', 'TRUE', 'geeR.objectId = cGstI.objectId; geeR.userPinCode = cGstI.userPinCode; geeR.storePinCode = cGstI.storePinCode');

-- Validation Station Rules
INSERT INTO GEE_RULES (RULE_NAME, GFC_ID, RULE_TYPE, DESCRIPTION, CONDITION_CODE, ACTION_CODE) VALUES 
('Validate_Object_Exists', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'VALIDATION', 'Validate object ID exists in OBJECT_DEF', 'exist_in_OBJECT_DEF(geeR.objectId) = 0', 'geeR.errorCode = 100; geeR.errorDesc = "Object ID not found"'),
('Validate_UserPin_Exists', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'VALIDATION', 'Validate user pin code exists', 'exist_in_PIN_CODE(geeR.userPinCode) = 0', 'geeR.errorCode = 101; geeR.errorDesc = "User postal code not found"'),
('Validate_StorePin_Exists', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'VALIDATION', 'Validate store pin code exists', 'exist_in_PIN_CODE(geeR.storePinCode) = 0', 'geeR.errorCode = 101; geeR.errorDesc = "Store postal code not found"');

-- Rating Station Rules
INSERT INTO GEE_RULES (RULE_NAME, GFC_ID, RULE_TYPE, DESCRIPTION, CONDITION_CODE, ACTION_CODE) VALUES 
('Fetch_Object_Price', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'LOOKUP', 'Fetch object price from OBJECT_DEF', 'geeR.errorCode = 0 OR geeR.errorCode IS NULL', 'geeR.objectPrice = get_object_price(geeR.objectId)'),
('Fetch_Tax_Rates_User', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'geeR'), 'LOOKUP', 'Fetch tax rates for user location', 'geeR.errorCode = 0 OR geeR.errorCode IS NULL', 'geeR.GSTRate = gst_in_PIN_CODE(geeR.userPinCode); geeR.HSTRate = hst_in_PIN_CODE(geeR.userPinCode); geeR.PstRate = pst_in_PIN_CODE(geeR.userPinCode)'),
('Calculate_GST', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'CALCULATION', 'Calculate GST amount', 'geeR.errorCode = 0 OR geeR.errorCode IS NULL', 'cGstO.objectGST = "$" + ROUND(Multiply(geeR.objectPrice, geeR.GSTRate), 2)'),
('Calculate_HST', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'CALCULATION', 'Calculate HST amount', 'geeR.errorCode = 0 OR geeR.errorCode IS NULL', 'cGstO.objectHST = "$" + ROUND(Multiply(geeR.objectPrice, geeR.HSTRate), 2)'),
('Calculate_PST', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'CALCULATION', 'Calculate PST amount', 'geeR.errorCode = 0 OR geeR.errorCode IS NULL', 'cGstO.objectPST = "$" + ROUND(Multiply(geeR.objectPrice, geeR.PstRate), 2)'),
('Set_Object_Value', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ASSIGNMENT', 'Set object value', 'geeR.errorCode = 0 OR geeR.errorCode IS NULL', 'cGstO.objectValue = "$" + geeR.objectPrice');

-- Error Handler Rules
INSERT INTO GEE_RULES (RULE_NAME, GFC_ID, RULE_TYPE, DESCRIPTION, CONDITION_CODE, ACTION_CODE) VALUES 
('Handle_Error_Code', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ERROR_HANDLING', 'Set error code in response', 'geeR.errorCode IS NOT NULL AND geeR.errorCode != 0', 'cGstO.error_code = geeR.errorCode'),
('Handle_Error_Desc', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ERROR_HANDLING', 'Set error description in response', 'geeR.errorDesc IS NOT NULL', 'cGstO.error_desc = geeR.errorDesc');

-- Term Station Rules  
INSERT INTO GEE_RULES (RULE_NAME, GFC_ID, RULE_TYPE, DESCRIPTION, CONDITION_CODE, ACTION_CODE) VALUES 
('Map_Object_Value', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ASSIGNMENT', 'Map object value to response', 'TRUE', 'response.objectValue = cGstO.objectValue'),
('Map_Object_GST', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ASSIGNMENT', 'Map GST to response', 'TRUE', 'response.objectGST = cGstO.objectGST'),
('Map_Object_HST', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ASSIGNMENT', 'Map HST to response', 'TRUE', 'response.objectHST = cGstO.objectHST'),
('Map_Object_PST', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ASSIGNMENT', 'Map PST to response', 'TRUE', 'response.objectPST = cGstO.objectPST'),
('Map_Error_Code', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ASSIGNMENT', 'Map error code to response', 'cGstO.error_code IS NOT NULL', 'response.code = cGstO.error_code'),
('Map_Error_Desc', (SELECT GFC_ID FROM GEE_FIELD_CLASSES WHERE FIELD_CLASS_NAME = 'cGstO'), 'ASSIGNMENT', 'Map error description to response', 'cGstO.error_desc IS NOT NULL', 'response.message = cGstO.error_desc');

-- ============================================
-- 10. CREATE MAIN FLOW
-- ============================================

INSERT INTO GEE_FLOWS (FLOW_NAME, DESCRIPTION, STATUS, CREATED_BY) VALUES 
('Canadian_GST_Flow', 'Complete flow for Canadian GST calculation', 'ACTIVE', 'System');

-- Create flow nodes for each station
INSERT INTO GEE_FLOW_NODES (FLOW_ID, NODE_TYPE, REFERENCE_ID, POSITION_X, POSITION_Y, WIDTH, HEIGHT, LABEL) VALUES 
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 'STATION', (SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Init Station'), 100, 100, 150, 80, 'Init Station'),
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 'STATION', (SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Validation Station'), 300, 100, 150, 80, 'Validation Station'),
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 'STATION', (SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Rating Station'), 500, 100, 150, 80, 'Rating Station'),
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 'STATION', (SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Error Handler'), 400, 250, 150, 80, 'Error Handler'),
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 'STATION', (SELECT STATION_ID FROM GEE_STATIONS WHERE STATION_NAME = 'Term Station'), 700, 100, 150, 80, 'Term Station');

-- Create connections between stations
INSERT INTO GEE_FLOW_CONNECTIONS (FLOW_ID, SOURCE_NODE_ID, TARGET_NODE_ID, CONNECTION_TYPE, LABEL) VALUES 
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Init Station'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Validation Station'), 
 'SUCCESS', 'Success'),
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Validation Station'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Rating Station'), 
 'SUCCESS', 'Valid'),
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Validation Station'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Error Handler'), 
 'FAILURE', 'Invalid'),
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Rating Station'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Term Station'), 
 'SUCCESS', 'Calculated'),
((SELECT FLOW_ID FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Error Handler'), 
 (SELECT NODE_ID FROM GEE_FLOW_NODES WHERE LABEL = 'Term Station'), 
 'DEFAULT', 'Error Handled');

COMMIT;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check field classes created
SELECT 'Field Classes:' as Info;
SELECT GFC_ID, FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION FROM GEE_FIELD_CLASSES 
WHERE FIELD_CLASS_NAME IN ('cGstI', 'cGstO', 'geeR', 'geeX');

-- Check fields created
SELECT 'Fields:' as Info;
SELECT fc.FIELD_CLASS_NAME, f.GF_NAME, f.GF_TYPE, f.GF_SIZE, f.GF_DESCRIPTION 
FROM GEE_FIELDS f 
JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID 
WHERE fc.FIELD_CLASS_NAME IN ('cGstI', 'cGstO', 'geeR') 
ORDER BY fc.FIELD_CLASS_NAME, f.GF_NAME;

-- Check tables created
SELECT 'Tables:' as Info;
SELECT name FROM sqlite_master WHERE type='table' AND name IN ('PIN_CODES', 'OBJECT_DEF');

-- Check sample data
SELECT 'Sample PIN_CODES:' as Info;
SELECT PIN_CODE, PROVINCE, GST_RATE, HST_RATE, PST_RATE FROM PIN_CODES LIMIT 5;

SELECT 'Sample OBJECT_DEF:' as Info;
SELECT OBJECT_ID, OBJECT_NAME, PRICE FROM OBJECT_DEF LIMIT 5;

-- Check functions
SELECT 'Base Functions:' as Info;
SELECT FUNC_NAME, PARAM_COUNT, DESCRIPTION FROM GEE_BASE_FUNCTIONS 
WHERE FUNC_NAME IN ('exist_in_PIN_CODE', 'exist_in_OBJECT_DEF', 'gst_in_PIN_CODE', 'hst_in_PIN_CODE', 'pst_in_PIN_CODE', 'Multiply', 'get_object_price');

-- Check stations and rule groups
SELECT 'Stations:' as Info;
SELECT STATION_NAME, STATION_TYPE, DESCRIPTION FROM GEE_STATIONS;

SELECT 'Rule Groups:' as Info;
SELECT GROUP_NAME, COND_TYPE, DESCRIPTION FROM GEE_RULES_GROUPS;

-- Check flow
SELECT 'Flow:' as Info;
SELECT FLOW_NAME, DESCRIPTION, STATUS FROM GEE_FLOWS WHERE FLOW_NAME = 'Canadian_GST_Flow';