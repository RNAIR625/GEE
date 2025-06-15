# GEE Debug Mode Implementation

## Overview

I have successfully implemented a comprehensive debug mode for both Forge (Python) and Praxis (Go) that provides detailed logging of function calls, SQL queries, and errors.

## Debug Mode Features

### 1. **Enhanced Startup Scripts**
- Updated `manage.sh` with new debug commands
- Environment variable `GEE_DEBUG_MODE` controls debug logging
- Separate debug log files for Forge and Praxis

### 2. **Forge (Python) Debug Features**

#### Function Call Logging
- **Decorator**: `@log_function_call` captures all function calls
- **Input/Output**: Logs function parameters and return values in JSON format
- **Performance**: Tracks execution time in milliseconds
- **Error Handling**: Captures and logs exceptions with stack traces

#### SQL Query Logging
- **All Queries**: Every SQL query is logged with parameters
- **Performance**: Query execution time tracking
- **Query Type**: Identifies SELECT, INSERT, UPDATE, DELETE operations
- **Results**: Logs number of affected/returned rows

#### Error Logging
- **Structured Errors**: JSON-formatted error logs
- **Context**: Request correlation IDs for tracing
- **Stack Traces**: Full exception details in debug mode

### 3. **Praxis (Go) Debug Features**

#### Function Call Logging
- **Go Middleware**: Similar function call tracking for Go handlers
- **JSON Output**: Structured JSON logs for easy parsing
- **HTTP Context**: Logs request details, URLs, and methods

#### Debug Logger Package
- **Centralized Logging**: `internal/debug/logger.go` package
- **Environment Aware**: Only logs when `GEE_DEBUG_MODE=true`
- **Multiple Categories**: Function calls, SQL queries, and general debug info

## Usage Commands

### Start in Debug Mode
```bash
# Start both services in debug mode
./manage.sh debug

# Start individual services in debug mode
./manage.sh forge-debug
./manage.sh praxis-debug

# Restart in debug mode
./manage.sh restart-debug
./manage.sh forge-restart-debug
./manage.sh praxis-restart-debug
```

### Log Files
- **Forge Debug**: `logs/forge_debug.log`
- **Praxis Debug**: `logs/praxis_debug.log`
- **Normal Logs**: `logs/forge.log`, `logs/praxis.log`

## Example Debug Output

### Function Call Logging (Python)
```json
{
  "@timestamp": "2025-06-07T11:55:20.544Z",
  "level": "DEBUG",
  "logger": "forge.debug.function_calls",
  "message": "Function call started: get_available_columns",
  "function_name": "get_available_columns",
  "function_module": "routes.functions",
  "input_args": [],
  "input_kwargs": {},
  "duration_ms": 2.5,
  "success": true
}
```

### SQL Query Logging (Python)
```json
{
  "@timestamp": "2025-06-07T11:55:20.545Z", 
  "level": "DEBUG",
  "logger": "forge.debug.sql",
  "message": "SQL query executed",
  "sql_query": "SELECT TABLE_NAME, DESCRIPTION, TABLE_TYPE FROM GEE_TABLES ORDER BY TABLE_NAME",
  "query_args_count": 0,
  "query_type": "SELECT",
  "result_count": 2,
  "duration_ms": 1.2
}
```

### Function Call Logging (Go)
```json
{
  "timestamp": "2025-06-07T11:55:20.546Z",
  "function": "handleExecuteFlow", 
  "module": "api.server",
  "input": {
    "url": "/flows/execute/123",
    "method": "POST",
    "flow_id": 123
  },
  "output": {
    "success": true,
    "result": "Flow completed"
  },
  "duration_ms": 45.2,
  "success": true,
  "debug_category": "function_calls"
}
```

## Implementation Details

### Forge Implementation
1. **logging_config.py**: Added debug mode utilities
   - `is_debug_mode()`: Environment variable check
   - `log_function_call()`: Decorator for function tracking
   - `log_sql_query()`: SQL query logging utility

2. **db_helpers.py**: Enhanced with SQL logging
   - Every `query_db()` and `modify_db()` call is logged
   - Performance tracking for database operations

3. **routes/functions.py**: Applied logging decorators
   - Key API endpoints now log function calls
   - Input validation and output formatting tracked

### Praxis Implementation
1. **internal/debug/logger.go**: Debug logging package
   - Environment-aware logging
   - JSON-structured output
   - Multiple logging categories

2. **internal/api/server.go**: Enhanced handlers
   - Function call logging for API endpoints
   - HTTP request context logging

3. **cmd/praxis/main.go**: Added debug flag support
   - `-debug` command line flag
   - Environment variable setup

### Startup Script Enhancement
1. **manage.sh**: Added debug mode support
   - New debug commands
   - Environment variable propagation
   - Separate debug log files

## Security Considerations

- **Sensitive Data**: Automatic filtering of passwords, tokens, and keys
- **Data Sanitization**: Input/output data is sanitized before logging
- **Log Rotation**: Debug logs use the same rotation as normal logs
- **Performance**: Debug mode only activates when explicitly enabled

## Testing Verification

The debug mode has been tested and verified to:
- ✅ Start services with debug logging enabled
- ✅ Log function calls with input/output data
- ✅ Track SQL query performance and results
- ✅ Capture detailed error information
- ✅ Use separate debug log files
- ✅ Maintain normal operation when debug mode is disabled

## Next Steps

1. **Production Safety**: Debug mode is disabled by default
2. **Log Analysis**: Consider adding log parsing tools
3. **Performance Monitoring**: Debug logs can be used for performance analysis
4. **Troubleshooting**: Enhanced error context helps with debugging issues