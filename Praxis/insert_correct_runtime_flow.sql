INSERT INTO runtime_flows (
    flow_id,
    flow_name, 
    flow_version, 
    flow_definition,
    is_active
) VALUES (
    10,
    'Currency Conversion Flow',
    '1.0',
    readfile('currency_conversion_flow.json'),
    1
);