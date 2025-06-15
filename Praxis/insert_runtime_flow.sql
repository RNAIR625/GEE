INSERT INTO runtime_flows (
    flow_id,
    flow_name, 
    flow_version, 
    flow_definition,
    input_schema,
    output_schema,
    is_active
) VALUES (
    10,
    'Currency Conversion Flow',
    '1.0',
    readfile('currency_conversion_flow.json'),
    json('{
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "description": "Amount to convert"
            },
            "from_currency": {
                "type": "string",
                "description": "Source currency code (e.g., USD)"
            },
            "to_currency": {
                "type": "string",
                "description": "Target currency code (e.g., EUR)"
            }
        },
        "required": ["amount", "from_currency", "to_currency"]
    }'),
    json('{
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean"
            },
            "data": {
                "type": "object"
            }
        }
    }'),
    1
);