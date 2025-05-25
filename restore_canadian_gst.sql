-- Restore Canadian GST Supporting Infrastructure
-- This recreates the reference tables and supporting data

-- ============================================
-- 1. CREATE REFERENCE TABLES
-- ============================================

-- PIN_CODES reference table
DROP TABLE IF EXISTS PIN_CODES;
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
DROP TABLE IF EXISTS OBJECT_DEF;
CREATE TABLE OBJECT_DEF (
    OBJECT_ID VARCHAR(50) PRIMARY KEY,
    OBJECT_NAME VARCHAR(100) NOT NULL,
    PRICE DECIMAL(10,2) NOT NULL,
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME
);

-- Register tables in GEE_TABLES
INSERT OR REPLACE INTO GEE_TABLES (TABLE_NAME, TABLE_TYPE, DESCRIPTION) VALUES 
('PIN_CODES', 'REFERENCE', 'Reference table for postal codes and tax rates'),
('OBJECT_DEF', 'APPLICATION', 'Application table for product definitions and pricing');

-- ============================================
-- 2. INSERT SAMPLE DATA
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
-- 3. CREATE BASE FUNCTIONS
-- ============================================

-- Function to check if PIN code exists
INSERT OR REPLACE INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('exist_in_PIN_CODE', 2, 'Check if postal code exists in PIN_CODES table');

-- Function to check if object exists
INSERT OR REPLACE INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('exist_in_OBJECT_DEF', 2, 'Check if object ID exists in OBJECT_DEF table');

-- Functions to get tax rates
INSERT OR REPLACE INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('gst_in_PIN_CODE', 2, 'Get GST rate for postal code');

INSERT OR REPLACE INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('hst_in_PIN_CODE', 2, 'Get HST rate for postal code');

INSERT OR REPLACE INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('pst_in_PIN_CODE', 2, 'Get PST rate for postal code');

-- Multiply function
INSERT OR REPLACE INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('Multiply', 3, 'Multiply two numbers');

-- Function to get object price
INSERT OR REPLACE INTO GEE_BASE_FUNCTIONS (FUNC_NAME, PARAM_COUNT, DESCRIPTION) VALUES 
('get_object_price', 2, 'Get price for object ID');

-- ============================================
-- 4. CREATE STATIONS
-- ============================================

INSERT OR REPLACE INTO GEE_STATIONS (STATION_NAME, DESCRIPTION, STATION_TYPE, ICON, COLOR_CODE) VALUES 
('Init Station', 'Map request values to input class', 'INPUT', 'fas fa-play', '#28a745'),
('Validation Station', 'Validate input parameters', 'PROCESS', 'fas fa-check-circle', '#ffc107'),
('Rating Station', 'Calculate tax amounts', 'PROCESS', 'fas fa-calculator', '#007bff'),
('Error Handler', 'Handle error conditions', 'PROCESS', 'fas fa-exclamation-triangle', '#dc3545'),
('Term Station', 'Map output to response', 'OUTPUT', 'fas fa-flag-checkered', '#6c757d');

COMMIT;

-- ============================================
-- VERIFICATION
-- ============================================

SELECT 'VALIDATION RESULTS:' as Info;

SELECT 'Field Classes:' as Component, COUNT(*) as Count FROM GEE_FIELD_CLASSES;
SELECT 'Canadian GST Fields:' as Component, COUNT(*) as Count 
FROM GEE_FIELDS f JOIN GEE_FIELD_CLASSES fc ON f.GFC_ID = fc.GFC_ID 
WHERE fc.FIELD_CLASS_NAME = 'CanadianGSTCalculation';

SELECT 'PIN Codes:' as Component, COUNT(*) as Count FROM PIN_CODES;
SELECT 'Products:' as Component, COUNT(*) as Count FROM OBJECT_DEF;
SELECT 'Base Functions:' as Component, COUNT(*) as Count FROM GEE_BASE_FUNCTIONS;
SELECT 'Stations:' as Component, COUNT(*) as Count FROM GEE_STATIONS;

-- Test the business logic
SELECT 'BUSINESS LOGIC TEST:' as Info;
SELECT 
    'Parker Pen HST Test:' as Test,
    od.OBJECT_ID,
    od.PRICE as BasePrice,
    pc.HST_RATE as HSTRate,
    ROUND(od.PRICE * pc.HST_RATE, 2) as ExpectedHST
FROM OBJECT_DEF od, PIN_CODES pc 
WHERE od.OBJECT_ID = 'Parker Pen' AND pc.PIN_CODE = 'M5V 3A8';

SELECT 'DATABASE STATUS: RESTORED' as Status;