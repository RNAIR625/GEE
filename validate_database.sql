-- Comprehensive Database Validation Script
-- This script validates all changes made to GEE.db

.mode table
.headers on

-- ============================================
-- 1. VERIFY FIELD CLASSES AND FIELDS
-- ============================================
SELECT '=== FIELD CLASSES VALIDATION ===' as Section;

-- Check if Canadian GST field class exists
SELECT 'Field Classes Count:' as Check, COUNT(*) as Count FROM GEE_FIELD_CLASSES;

SELECT 'Canadian GST Field Class:' as Check;
SELECT GFC_ID, FIELD_CLASS_NAME, CLASS_TYPE, DESCRIPTION 
FROM GEE_FIELD_CLASSES 
WHERE FIELD_CLASS_NAME = 'CanadianGSTCalculation';

-- Check if all 7 fields exist for Canadian GST
SELECT 'Canadian GST Fields Count:' as Check, COUNT(*) as Count 
FROM GEE_FIELDS f 
JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID 
WHERE fc.FIELD_CLASS_NAME = 'CanadianGSTCalculation';

SELECT 'Canadian GST Fields Details:' as Check;
SELECT f.GF_NAME, f.GF_TYPE, f.GF_SIZE, f.GF_DESCRIPTION
FROM GEE_FIELDS f 
JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID 
WHERE fc.FIELD_CLASS_NAME = 'CanadianGSTCalculation'
ORDER BY f.GF_NAME;

-- ============================================
-- 2. VERIFY REFERENCE TABLES
-- ============================================
SELECT '=== REFERENCE TABLES VALIDATION ===' as Section;

-- Check if tables exist
SELECT 'Tables Existence:' as Check;
SELECT name as TableName 
FROM sqlite_master 
WHERE type='table' 
AND name IN ('PIN_CODES', 'OBJECT_DEF')
ORDER BY name;

-- Check PIN_CODES data
SELECT 'PIN_CODES Data Count:' as Check, COUNT(*) as Count FROM PIN_CODES;

SELECT 'PIN_CODES Sample Data:' as Check;
SELECT PIN_CODE, PROVINCE, GST_RATE, HST_RATE, PST_RATE 
FROM PIN_CODES 
LIMIT 5;

-- Check OBJECT_DEF data
SELECT 'OBJECT_DEF Data Count:' as Check, COUNT(*) as Count FROM OBJECT_DEF;

SELECT 'OBJECT_DEF Sample Data:' as Check;
SELECT OBJECT_ID, OBJECT_NAME, PRICE 
FROM OBJECT_DEF 
LIMIT 5;

-- ============================================
-- 3. VERIFY BASE FUNCTIONS
-- ============================================
SELECT '=== BASE FUNCTIONS VALIDATION ===' as Section;

SELECT 'Base Functions Count:' as Check, COUNT(*) as Count FROM GEE_BASE_FUNCTIONS;

SELECT 'Canadian GST Functions:' as Check;
SELECT FUNC_NAME, PARAM_COUNT, DESCRIPTION 
FROM GEE_BASE_FUNCTIONS 
WHERE FUNC_NAME IN ('exist_in_PIN_CODE', 'exist_in_OBJECT_DEF', 'gst_in_PIN_CODE', 'hst_in_PIN_CODE', 'pst_in_PIN_CODE', 'Multiply', 'get_object_price')
ORDER BY FUNC_NAME;

-- Check function parameters
SELECT 'Function Parameters Count:' as Check, COUNT(*) as Count FROM GEE_BASE_FUNCTIONS_PARAMS;

-- ============================================
-- 4. VERIFY STATIONS
-- ============================================
SELECT '=== STATIONS VALIDATION ===' as Section;

SELECT 'Stations Count:' as Check, COUNT(*) as Count FROM GEE_STATIONS;

SELECT 'Canadian GST Stations:' as Check;
SELECT STATION_NAME, STATION_TYPE, DESCRIPTION 
FROM GEE_STATIONS 
WHERE STATION_NAME IN ('Init Station', 'Validation Station', 'Rating Station', 'Error Handler', 'Term Station')
ORDER BY STATION_NAME;

-- ============================================
-- 5. VERIFY RULE GROUPS
-- ============================================
SELECT '=== RULE GROUPS VALIDATION ===' as Section;

SELECT 'Rule Groups Count:' as Check, COUNT(*) as Count FROM GEE_RULES_GROUPS;

-- Check for both table names (GEE_RULES_GROUPS and GRG_RULE_GROUPS)
SELECT 'GRG Rule Groups Count:' as Check, COUNT(*) as Count FROM GRG_RULE_GROUPS WHERE 1=1;

SELECT 'Canadian GST Rule Groups:' as Check;
SELECT GROUP_NAME, COND_TYPE, DESCRIPTION 
FROM GEE_RULES_GROUPS 
WHERE GROUP_NAME LIKE '%Rules%'
ORDER BY GROUP_NAME;

-- ============================================
-- 6. VERIFY RULES
-- ============================================
SELECT '=== RULES VALIDATION ===' as Section;

SELECT 'Rules Count:' as Check, COUNT(*) as Count FROM GEE_RULES;

SELECT 'Canadian GST Rules Sample:' as Check;
SELECT RULE_NAME, RULE_TYPE, DESCRIPTION 
FROM GEE_RULES 
WHERE RULE_NAME LIKE 'Map_%' OR RULE_NAME LIKE 'Validate_%' OR RULE_NAME LIKE 'Calculate_%'
ORDER BY RULE_NAME
LIMIT 10;

-- ============================================
-- 7. VERIFY FLOWS
-- ============================================
SELECT '=== FLOWS VALIDATION ===' as Section;

SELECT 'Flows Count:' as Check, COUNT(*) as Count FROM GEE_FLOWS;

SELECT 'Canadian GST Flow:' as Check;
SELECT FLOW_NAME, DESCRIPTION, STATUS, VERSION 
FROM GEE_FLOWS 
WHERE FLOW_NAME = 'Canadian_GST_Flow';

-- Check flow nodes
SELECT 'Flow Nodes Count:' as Check, COUNT(*) as Count FROM GEE_FLOW_NODES;

-- Check flow connections
SELECT 'Flow Connections Count:' as Check, COUNT(*) as Count FROM GEE_FLOW_CONNECTIONS;

-- ============================================
-- 8. VERIFY TABLES REGISTRATION
-- ============================================
SELECT '=== TABLES REGISTRATION VALIDATION ===' as Section;

SELECT 'GEE Tables Count:' as Check, COUNT(*) as Count FROM GEE_TABLES;

SELECT 'Registered Tables:' as Check;
SELECT TABLE_NAME, TABLE_TYPE, DESCRIPTION 
FROM GEE_TABLES 
ORDER BY TABLE_NAME;

-- ============================================
-- 9. CHECK DATABASE INTEGRITY
-- ============================================
SELECT '=== DATABASE INTEGRITY CHECK ===' as Section;

-- Check for orphaned fields
SELECT 'Orphaned Fields Count:' as Check, COUNT(*) as Count 
FROM GEE_FIELDS f 
LEFT JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID 
WHERE fc.GFC_ID IS NULL;

-- Check for orphaned function parameters
SELECT 'Orphaned Function Parameters Count:' as Check, COUNT(*) as Count 
FROM GEE_BASE_FUNCTIONS_PARAMS p 
LEFT JOIN GEE_BASE_FUNCTIONS f ON p.GBF_ID = f.GBF_ID 
WHERE f.GBF_ID IS NULL;

-- ============================================
-- 10. VERIFY CANADIAN GST SPECIFIC DATA
-- ============================================
SELECT '=== CANADIAN GST SPECIFIC VALIDATION ===' as Section;

-- Test specific postal codes for GST calculation
SELECT 'Ontario HST Test Data:' as Check;
SELECT 
    od.OBJECT_ID,
    od.PRICE,
    pc.HST_RATE,
    ROUND(od.PRICE * pc.HST_RATE, 2) as Expected_HST
FROM OBJECT_DEF od, PIN_CODES pc 
WHERE od.OBJECT_ID = 'Parker Pen' AND pc.PIN_CODE = 'M5V 3A8';

-- Check for required sample data
SELECT 'Parker Pen Exists:' as Check, 
       CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END as Exists
FROM OBJECT_DEF WHERE OBJECT_ID = 'Parker Pen';

SELECT 'Ontario Postal Code Exists:' as Check,
       CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END as Exists
FROM PIN_CODES WHERE PIN_CODE = 'M5V 3A8';

-- ============================================
-- 11. TABLE STRUCTURE VALIDATION
-- ============================================
SELECT '=== TABLE STRUCTURE VALIDATION ===' as Section;

-- Check critical table structures
SELECT 'All Required Tables Exist:' as Check;
SELECT name as TableName, type 
FROM sqlite_master 
WHERE type='table' 
AND name IN (
    'GEE_FIELD_CLASSES', 'GEE_FIELDS', 'GEE_BASE_FUNCTIONS', 'GEE_BASE_FUNCTIONS_PARAMS',
    'GEE_RULES_GROUPS', 'GEE_RULES', 'GEE_STATIONS', 'GEE_FLOWS', 'GEE_FLOW_NODES',
    'GEE_FLOW_CONNECTIONS', 'GEE_TABLES', 'PIN_CODES', 'OBJECT_DEF'
)
ORDER BY name;

-- ============================================
-- 12. SUMMARY REPORT
-- ============================================
SELECT '=== VALIDATION SUMMARY ===' as Section;

SELECT 'Component' as Component, 'Count' as Count, 'Status' as Status
UNION ALL
SELECT 'Field Classes', CAST(COUNT(*) as TEXT), CASE WHEN COUNT(*) >= 4 THEN 'OK' ELSE 'MISSING' END FROM GEE_FIELD_CLASSES
UNION ALL
SELECT 'Canadian GST Fields', CAST(COUNT(*) as TEXT), CASE WHEN COUNT(*) = 7 THEN 'OK' ELSE 'INCORRECT' END 
FROM GEE_FIELDS f JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID WHERE fc.FIELD_CLASS_NAME = 'CanadianGSTCalculation'
UNION ALL
SELECT 'Base Functions', CAST(COUNT(*) as TEXT), CASE WHEN COUNT(*) >= 7 THEN 'OK' ELSE 'MISSING' END FROM GEE_BASE_FUNCTIONS
UNION ALL
SELECT 'PIN Codes', CAST(COUNT(*) as TEXT), CASE WHEN COUNT(*) >= 10 THEN 'OK' ELSE 'INCOMPLETE' END FROM PIN_CODES
UNION ALL
SELECT 'Products', CAST(COUNT(*) as TEXT), CASE WHEN COUNT(*) >= 5 THEN 'OK' ELSE 'INCOMPLETE' END FROM OBJECT_DEF
UNION ALL
SELECT 'Stations', CAST(COUNT(*) as TEXT), CASE WHEN COUNT(*) >= 5 THEN 'OK' ELSE 'MISSING' END FROM GEE_STATIONS
UNION ALL
SELECT 'Flows', CAST(COUNT(*) as TEXT), CASE WHEN COUNT(*) >= 1 THEN 'OK' ELSE 'MISSING' END FROM GEE_FLOWS;