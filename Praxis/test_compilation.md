# Auto-Function Integration Test

## Overview
This document describes the auto-function integration between Forge and Praxis.

## Implementation Summary

### Forge Side (Python)
1. **AutoFunctionService** - Generates table functions automatically
2. **ConnectionTokenService** - Manages shared database tokens
3. **API Endpoints** - REST endpoints for function management
4. **Hierarchical UI** - Modal interface for function browsing
5. **Database Schema** - GEE_AUTO_FUNCTIONS, GEE_CONNECTION_TOKENS tables

### Praxis Side (Go)
1. **ForgeLoader** - Loads data from Forge's GEE.db
2. **Extended DataCache** - Caches auto-functions and tables
3. **Auto-Function API** - REST endpoints for function execution
4. **Function Caching** - TTL-based result caching

## Key Features

### Auto-Generated Functions
- **Primary Key Checks**: `TABLE_pk_exists(pk_value)`
- **Column Getters**: `TABLE_get_column_name(pk_value)`
- **Hierarchical Organization**: Functions grouped by table
- **Smart Caching**: TTL-based result caching

### Shared Configuration
- **Database Tokens**: Secure connection sharing between services
- **Function Templates**: Consistent naming conventions
- **Config Directory**: `/Config` for shared settings

### Integration Points
1. **Table Import**: Auto-generates functions on import
2. **Function UI**: Hierarchical function browser in Forge
3. **Rule Integration**: Functions can be inserted into rule expressions
4. **Cache Sync**: Praxis loads function definitions from Forge

## Testing Plan
1. Import table in Forge → Verify functions generated
2. Load Praxis → Verify functions cached
3. Execute function via API → Verify result and caching
4. Update table → Verify function regeneration

## API Endpoints

### Forge
- `POST /tables/auto_functions/generate/{table_id}`
- `GET /tables/auto_functions/by_table`
- `POST /tables/connection_tokens/generate`

### Praxis
- `GET /api/v1/auto-functions`
- `POST /api/v1/auto-functions/reload`
- `POST /api/v1/auto-functions/execute/{functionName}`

The implementation provides a comprehensive auto-function system that bridges the gap between table metadata and rule execution.