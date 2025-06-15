INSERT INTO GEE_FLOW_DEFINITIONS (FLOW_ID, FLOW_NAME, FLOW_JSON, SOURCE_HASH, CREATED_AT, UPDATED_AT) 
VALUES (
    10, 
    'Currency Conversion Flow', 
    readfile('currency_conversion_flow.json'),
    'manual_creation_hash_001', 
    datetime('now'), 
    datetime('now')
);