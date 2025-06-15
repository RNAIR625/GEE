-- Runtime Database Schema for Praxis
-- This schema defines the runtime tables used by the Praxis execution engine

-- Flow definitions table
CREATE TABLE runtime_flows (
    flow_id INTEGER PRIMARY KEY,
    flow_name TEXT NOT NULL,
    flow_version TEXT NOT NULL,
    flow_definition TEXT NOT NULL,  -- JSON flow definition
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Rules table
CREATE TABLE runtime_rules (
    rule_id INTEGER PRIMARY KEY,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    rule_logic TEXT NOT NULL,  -- JSON rule logic
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Rule groups table
CREATE TABLE runtime_rule_groups (
    group_id INTEGER PRIMARY KEY,
    group_name TEXT NOT NULL,
    execution_mode TEXT NOT NULL,  -- SEQUENTIAL, PARALLEL
    group_logic TEXT NOT NULL,  -- AND, OR, CONDITION
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Rule group mapping table (which rules belong to which groups)
CREATE TABLE runtime_rule_group_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    rule_id INTEGER NOT NULL,
    execution_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (group_id) REFERENCES runtime_rule_groups(group_id),
    FOREIGN KEY (rule_id) REFERENCES runtime_rules(rule_id)
);

-- Functions table
CREATE TABLE runtime_functions (
    function_id INTEGER PRIMARY KEY,
    function_name TEXT NOT NULL,
    function_type TEXT NOT NULL,  -- BUILTIN, JAVASCRIPT, SQL, PYTHON
    function_code TEXT,  -- Function code/implementation
    input_parameters TEXT,  -- JSON array of input parameters
    output_type TEXT NOT NULL,  -- JSON, STRING, NUMBER, BOOLEAN
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Database connections table
CREATE TABLE db_connections (
    connection_id INTEGER PRIMARY KEY,
    connection_name TEXT NOT NULL,
    db_type TEXT NOT NULL,  -- SQLITE, MYSQL, POSTGRES, ORACLE
    connection_string TEXT NOT NULL,
    schema_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- API endpoints table (for external service calls)
CREATE TABLE api_endpoints (
    endpoint_id INTEGER PRIMARY KEY,
    endpoint_name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    endpoint_path TEXT NOT NULL,
    http_method TEXT NOT NULL,  -- GET, POST, PUT, DELETE
    headers TEXT,  -- JSON headers
    auth_config TEXT,  -- JSON auth configuration
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Execution logs table (for monitoring and debugging)
CREATE TABLE execution_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id INTEGER,
    execution_id TEXT NOT NULL,
    log_level TEXT NOT NULL,  -- DEBUG, INFO, WARN, ERROR
    message TEXT NOT NULL,
    context_data TEXT,  -- JSON context data
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flow_id) REFERENCES runtime_flows(flow_id)
);

-- Create indexes for better performance
CREATE INDEX idx_runtime_flows_active ON runtime_flows(is_active);
CREATE INDEX idx_runtime_rules_active ON runtime_rules(is_active);
CREATE INDEX idx_runtime_functions_active ON runtime_functions(is_active);
CREATE INDEX idx_rule_group_mapping_group ON runtime_rule_group_mapping(group_id);
CREATE INDEX idx_execution_logs_flow ON execution_logs(flow_id);
CREATE INDEX idx_execution_logs_timestamp ON execution_logs(timestamp);