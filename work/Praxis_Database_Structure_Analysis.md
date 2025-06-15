# Praxis Database Structure Analysis - Data Structures Created from SQLite Tables

## Overview

This document provides a comprehensive analysis of the data structures created in memory when Praxis reads from the `data/current.db` SQLite database. It details the transformation process from SQLite tables to Go structs and the memory enhancements that occur during API operations.

## Database Connection Strategy

### Database Loading Process
- **Primary Database**: `current.db` (symlink to latest `gee_*_execution_worker.db`)
- **Runtime Database**: `praxis_runtime.db` (separate execution data)
- **Connection Mode**: Read-only (`?mode=ro`)
- **Loading Strategy**: Lazy loading on API requests
- **Caching**: No persistent caching - fresh structures per request

## Detailed Table-to-Structure Mappings

### 1. GEE_FIELD_CLASSES → FieldClass Struct

**SQLite Table Schema:**
```sql
CREATE TABLE GEE_FIELD_CLASSES (
    GFC_ID INTEGER PRIMARY KEY,
    GFC_IS INTEGER,
    FIELD_CLASS_NAME TEXT NOT NULL,
    CLASS_TYPE TEXT NOT NULL,
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME,
    DESCRIPTION TEXT,
    PARENT_GFC_ID INTEGER,
    API_BASE_URL VARCHAR(500),
    API_VERSION VARCHAR(50),
    OPENAPI_SPEC TEXT,
    API_SERVERS TEXT,
    API_AUTH_TYPE VARCHAR(50),
    API_METADATA TEXT,
    NESTING_LEVEL INTEGER DEFAULT 0,
    HIERARCHY_PATH TEXT
);
```

**Go Memory Structure:**
```go
type FieldClass struct {
    ID              int64     `json:"id" db:"GFC_ID"`
    IS              int64     `json:"is" db:"GFC_IS"`
    FieldClassName  string    `json:"field_class_name" db:"FIELD_CLASS_NAME"`
    ClassType       string    `json:"class_type" db:"CLASS_TYPE"`
    CreateDate      time.Time `json:"create_date" db:"CREATE_DATE"`
    UpdateDate      *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
    Description     *string   `json:"description,omitempty" db:"DESCRIPTION"`
}
```

**Data Transformation Process:**
- **Location**: `manager.go:151-199`
- **Query Pattern**: `SELECT GFC_ID, GFC_IS, FIELD_CLASS_NAME, CLASS_TYPE, CREATE_DATE, UPDATE_DATE, DESCRIPTION FROM GEE_FIELD_CLASSES ORDER BY GFC_ID`
- **Memory Allocation**: Creates `[]models.FieldClass` slice
- **Null Handling**: Uses `sql.NullTime` and `sql.NullString` for optional fields
- **Pointer Optimization**: UpdateDate and Description become pointers only when database values are Valid
- **Enhancement**: Establishes hierarchy relationships via PARENT_GFC_ID
- **API Integration**: Loads API metadata for dynamic endpoint generation

**Memory Enhancement Details:**
1. Individual FieldClass struct instances allocated
2. Slice built containing all class definitions
3. Hierarchy relationships mapped (parent-child via PARENT_GFC_ID)
4. API metadata parsed for dynamic route generation

---

### 2. GEE_FIELDS → Field Struct

**SQLite Table Schema:**
```sql
CREATE TABLE GEE_FIELDS (
    GF_ID INTEGER PRIMARY KEY,
    GFC_ID INTEGER,
    GF_NAME TEXT NOT NULL,
    GF_TYPE TEXT NOT NULL,
    GF_SIZE INTEGER,
    GF_PRECISION_SIZE INTEGER,
    GF_DEFAULT_VALUE TEXT,
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME,
    GF_DESCRIPTION TEXT,
    FOREIGN KEY (GFC_ID) REFERENCES GEE_FIELD_CLASSES(GFC_ID)
);
```

**Go Memory Structure:**
```go
type Field struct {
    ID             int64      `json:"id" db:"GF_ID"`
    ClassID        int64      `json:"class_id" db:"GFC_ID"`
    Name           string     `json:"name" db:"GF_NAME"`
    Type           string     `json:"type" db:"GF_TYPE"`
    Size           *int       `json:"size,omitempty" db:"GF_SIZE"`
    PrecisionSize  *int       `json:"precision_size,omitempty" db:"GF_PRECISION_SIZE"`
    DefaultValue   *string    `json:"default_value,omitempty" db:"GF_DEFAULT_VALUE"`
    CreateDate     time.Time  `json:"create_date" db:"CREATE_DATE"`
    UpdateDate     *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
    Description    *string    `json:"description,omitempty" db:"GF_DESCRIPTION"`
}
```

**Data Transformation Process:**
- **Location**: `manager.go:202-266`
- **Complex Null Handling**:
  ```go
  var size, precisionSize sql.NullInt64
  var defaultValue, description sql.NullString
  var updateDate sql.NullTime
  ```
- **Type Conversion**: Converts `sql.NullInt64` to `*int` for size fields
- **Memory Optimization**: Only allocates pointer memory when database values exist
- **Foreign Key Resolution**: ClassID links to FieldClass.ID for relationship mapping

---

### 3. GEE_API_ENDPOINTS → APIEndpoint Struct + Dynamic Route Registration

**SQLite Table Schema:**
```sql
CREATE TABLE GEE_API_ENDPOINTS (
    GAE_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    GFC_ID INTEGER NOT NULL,
    ENDPOINT_PATH VARCHAR(500) NOT NULL,
    HTTP_METHOD VARCHAR(10) NOT NULL,
    OPERATION_ID VARCHAR(200),
    SUMMARY VARCHAR(500),
    DESCRIPTION TEXT,
    REQUEST_BODY_GFC_ID INTEGER,
    RESPONSE_BODY_GFC_ID INTEGER,
    PARAMETERS TEXT, -- JSON array
    TAGS TEXT, -- JSON array
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Go Memory Structure:**
```go
type APIEndpoint struct {
    ID               int                    `json:"id"`
    ClassID          int                    `json:"class_id"`
    EndpointPath     string                 `json:"endpoint_path"`
    HTTPMethod       string                 `json:"http_method"`
    OperationID      *string                `json:"operation_id,omitempty"`
    Summary          *string                `json:"summary,omitempty"`
    Description      *string                `json:"description,omitempty"`
    RequestBodyID    *int                   `json:"request_body_id,omitempty"`
    ResponseBodyID   *int                   `json:"response_body_id,omitempty"`
    Parameters       *string                `json:"parameters,omitempty"`
    Tags             *string                `json:"tags,omitempty"`
    ClassName        string                 `json:"class_name"`
    ClassDescription *string                `json:"class_description,omitempty"`
    APIBaseURL       *string                `json:"api_base_url,omitempty"`
    APIVersion       *string                `json:"api_version,omitempty"`
}
```

**Enhanced Data Transformation Process:**
- **Location**: `manager.go:746-813`
- **JOIN Query**: Joins with GEE_FIELD_CLASSES for class information
- **Dynamic Route Registration**: `server.go:302-333`
  - Each endpoint becomes a runtime HTTP route
  - Creates closure capturing endpoint metadata
  - Registers with Gorilla Mux router
- **Request Context Enhancement**: `server.go:335-384`

**Runtime Memory Enhancement:**
```go
// Created for each dynamic endpoint request
executionContext := map[string]interface{}{
    "endpoint":       endpoint,
    "request_data":   requestData,
    "path_params":    vars,
    "query_params":   r.URL.Query(),
    "headers":        r.Header,
    "class_id":       endpoint.ClassID,
    "class_name":     endpoint.ClassName,
}
```

---

### 4. execution_history → Multiple Runtime Execution Structures

**SQLite Table Schema:**
```sql
CREATE TABLE execution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id INTEGER NOT NULL,
    job_id TEXT UNIQUE NOT NULL,
    input_data JSON,
    output_data JSON,
    execution_time_ms INTEGER,
    status TEXT CHECK(status IN ('submitted', 'running', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Go Memory Structures Created:**
```go
// Job status response structure (manager.go:482-549)
type JobStatusResponse struct {
    JobID          string                 `json:"job_id"`
    FlowID         int                    `json:"flow_id"`
    JobType        string                 `json:"job_type"`
    Status         string                 `json:"status"`
    Priority       int                    `json:"priority"`
    CreatedAt      time.Time              `json:"created_at"`
    StartedAt      *time.Time             `json:"started_at,omitempty"`
    CompletedAt    *time.Time             `json:"completed_at,omitempty"`
    WorkerID       *string                `json:"worker_id,omitempty"`
    RetryCount     int                    `json:"retry_count"`
    ErrorMessage   *string                `json:"error_message,omitempty"`
    InputData      map[string]interface{} `json:"input_data,omitempty"`
    ExecutionConfig map[string]interface{} `json:"execution_config,omitempty"`
}

// Job result structure (manager.go:552-584)
type JobResultResponse struct {
    JobID      string                 `json:"job_id"`
    ResultData map[string]interface{} `json:"result_data"`
    OutputType string                 `json:"output_type"`
    ResultSize int                    `json:"result_size"`
    CreatedAt  time.Time              `json:"created_at"`
}
```

**Complex JSON Parsing Enhancement:**
- **Dynamic JSON Unmarshaling**: `manager.go:536-546`
  ```go
  if inputData.Valid {
      var inputMap map[string]interface{}
      if err := json.Unmarshal([]byte(inputData.String), &inputMap); err == nil {
          job["input_data"] = inputMap
      }
  }
  ```
- **Nested Structure Creation**: Creates nested `map[string]interface{}` from JSON strings
- **Type-Safe Access**: Provides typed access to dynamic JSON content

---

### 5. runtime_flows (Runtime Database) → Flow + Enhanced Execution Structures

**SQLite Table Schema (praxis_runtime.db):**
```sql
CREATE TABLE runtime_flows (
    flow_id INTEGER PRIMARY KEY,
    flow_name TEXT NOT NULL,
    flow_version TEXT NOT NULL,
    flow_definition TEXT NOT NULL, -- JSON
    is_active INTEGER DEFAULT 1
);
```

**Go Memory Structures Created:**
```go
// Basic flow structure (loader.go:15-22)
type Flow struct {
    ID         int    `json:"flow_id"`
    Name       string `json:"flow_name"`
    Version    string `json:"flow_version"`
    Definition string `json:"flow_definition"` // Raw JSON string
    IsActive   bool   `json:"is_active"`
}

// Enhanced execution structure (executor.go)
type FlowDefinition struct {
    FlowID       int                     `json:"flow_id"`
    FlowName     string                  `json:"flow_name"`
    FlowVersion  string                  `json:"flow_version"`
    StartNodes   []string                `json:"start_nodes"`
    Nodes        map[string]NodeDefinition `json:"nodes"`
    Connections  []ConnectionDefinition   `json:"connections"`
    Rules        []RuleDefinition         `json:"rules"`
    RuleGroups   []RuleGroupDefinition    `json:"rule_groups"`
    Functions    []FunctionDefinition     `json:"functions"`
}

// Execution context (executor.go)
type ExecutionContext struct {
    Input     map[string]interface{} `json:"input"`
    Variables map[string]interface{} `json:"variables"`
    Output    map[string]interface{} `json:"output"`
    Errors    []string               `json:"errors"`
    StartTime time.Time              `json:"start_time"`
}
```

**Multi-Stage Data Enhancement:**
1. **Initial Load**: `loader.go:68-93` loads basic Flow struct
2. **JSON Parsing**: Definition string parsed into complex FlowDefinition
3. **Execution Context Creation**: `executor.go` enhances with ExecutionContext
4. **Runtime Caching**: Parsed definitions cached for performance during execution

---

### 6. GEE_FLOWS + GEE_FLOW_NODES + GEE_FLOW_CONNECTIONS → Enhanced Flow Structures

**Complex Multi-Table Memory Enhancement:**
```go
// Enhanced flow structure combining multiple tables
type EnhancedFlowStructure struct {
    Flow        GEEFlow                    `json:"flow"`
    Nodes       []FlowNode                 `json:"nodes"`
    Connections []FlowConnection           `json:"connections"`
    NodeMap     map[int]*FlowNode          `json:"-"` // Runtime indexing
    Hierarchy   map[int][]int              `json:"-"` // Parent-child relationships
    RouteGraph  map[int][]ConnectionRoute  `json:"-"` // Execution routing
}

// Flow node with enhanced relationships
type FlowNode struct {
    ID            int                    `json:"node_id"`
    FlowID        int                    `json:"flow_id"`
    NodeType      string                 `json:"node_type"` // 'STATION', 'RULE_GROUP', 'RULE'
    ReferenceID   int                    `json:"reference_id"`
    ParentNodeID  *int                   `json:"parent_node_id,omitempty"`
    Position      Position               `json:"position"`
    Dimensions    Dimensions             `json:"dimensions"`
    Label         string                 `json:"label"`
    CustomSettings map[string]interface{} `json:"custom_settings"`
    Children      []int                  `json:"children"` // Enhanced at runtime
}

// Position and dimension structures
type Position struct {
    X float64 `json:"x"`
    Y float64 `json:"y"`
}

type Dimensions struct {
    Width  float64 `json:"width"`
    Height float64 `json:"height"`
}

// Flow connections with conditional logic
type FlowConnection struct {
    ID                int    `json:"connection_id"`
    FlowID           int    `json:"flow_id"`
    SourceNodeID     int    `json:"source_node_id"`
    TargetNodeID     int    `json:"target_node_id"`
    ConnectionType   string `json:"connection_type"` // 'SUCCESS', 'FAILURE', 'DEFAULT', 'CONDITIONAL'
    ConditionExpr    *string `json:"condition_expression,omitempty"`
    Label            string `json:"label"`
    StyleSettings    *string `json:"style_settings"` // JSON styling
}
```

**Data Enhancement Process:**
1. **Multi-Query Loading**: Separate queries for flows, nodes, and connections
2. **Relationship Mapping**: Parent-child relationships built in memory
3. **Execution Graph Construction**: Connection routes optimized for runtime
4. **Hierarchical Indexing**: Fast lookup structures for nested nodes

---

### 7. execution_debug_logs → Structured Debug Information

**SQLite Schema:**
```sql
CREATE TABLE execution_debug_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT CHECK(level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR')),
    component TEXT,
    message TEXT,
    context JSON
);
```

**Go Memory Structures Created:**
```go
// Basic debug log entry
type DebugLogEntry struct {
    ID        int                    `json:"id"`
    JobID     string                 `json:"job_id"`
    Timestamp time.Time              `json:"timestamp"`
    Level     string                 `json:"level"`
    Component string                 `json:"component"`
    Message   string                 `json:"message"`
    Context   map[string]interface{} `json:"context"`
}

// Enhanced debug context (debug/logger.go)
type FunctionCall struct {
    Timestamp     time.Time              `json:"timestamp"`
    Function      string                 `json:"function"`
    Module        string                 `json:"module"`
    Input         map[string]interface{} `json:"input"`
    Output        interface{}            `json:"output"`
    Error         string                 `json:"error,omitempty"`
    DurationMs    int64                  `json:"duration_ms"`
    Success       bool                   `json:"success"`
    DebugCategory string                 `json:"debug_category"`
}

// SQL query debugging
type SQLQuery struct {
    Timestamp     time.Time `json:"timestamp"`
    Query         string    `json:"query"`
    ArgsCount     int       `json:"args_count"`
    QueryType     string    `json:"query_type"`
    ResultCount   int       `json:"result_count"`
    DurationMs    int64     `json:"duration_ms"`
    Error         string    `json:"error,omitempty"`
    DebugCategory string    `json:"debug_category"`
}
```

---

### 8. Enhanced Rule Execution Structures

**Tables:** GEE_RULES, GEE_RULE_LINES, GEE_RULE_LINE_PARAMS, GEE_BASE_FUNCTIONS

**Go Memory Structures Created:**
```go
// Enhanced rule structure (rule_executor.go)
type EnhancedRule struct {
    RuleID      int                   `json:"rule_id"`
    RuleName    string                `json:"rule_name"`
    RuleType    string                `json:"rule_type"`
    Description string                `json:"description"`
    ClassID     int                   `json:"class_id"`
    Conditions  []EnhancedRuleLine    `json:"conditions"`
    Actions     []EnhancedRuleLine    `json:"actions"`
}

// Function call with parameters
type EnhancedRuleLine struct {
    LineID       int                      `json:"line_id"`
    Sequence     int                      `json:"sequence"`
    FunctionID   int                      `json:"function_id"`
    FunctionName string                   `json:"function_name"`
    IsCondition  bool                     `json:"is_condition"`
    Parameters   []EnhancedRuleParameter  `json:"parameters"`
}

// Parameter with type and value
type EnhancedRuleParameter struct {
    Index           int    `json:"index"`
    Type            string `json:"type"` // 'LITERAL', 'FIELD', 'VARIABLE', 'EXPRESSION'
    Value           string `json:"value"`
    FieldID         *int   `json:"field_id,omitempty"`
    ExpressionValue string `json:"expression_value,omitempty"`
}

// Available function for execution
type FunctionDefinition struct {
    ID             int      `json:"id"`
    Name           string   `json:"name"`
    Type           string   `json:"type"`
    ParamCount     int      `json:"param_count"`
    Description    string   `json:"description"`
    GoCode         string   `json:"go_code"`
    ParameterTypes []string `json:"parameter_types"`
    ReturnType     string   `json:"return_type"`
}
```

---

## Memory Structure Enhancement Summary by API Endpoint

### Static API Endpoints

**`/api/v1/field-classes` (GET):**
- **Tables Read:** GEE_FIELD_CLASSES
- **Memory Created:** `[]models.FieldClass` slice
- **Enhancement:** Hierarchy relationships, API metadata parsing
- **Response Structure:** 
  ```go
  {
      "success": true,
      "data": []FieldClass,
      "count": int
  }
  ```

**`/api/v1/fields` (GET):**
- **Tables Read:** GEE_FIELDS
- **Memory Created:** `[]models.Field` slice  
- **Enhancement:** Foreign key resolution to FieldClass, type conversions
- **Response Structure:** Wrapped with metadata

**`/api/v1/flow-definitions` (GET):**
- **Tables Read:** GEE_FLOW_DEFINITIONS or GEE_FLOWS (fallback)
- **Memory Created:** `[]map[string]interface{}` with parsed FlowDefinition
- **Enhancement:** JSON parsing, version handling, flow validation
- **Response Structure:** Dynamic structure based on table availability

**`/api/v1/api-endpoints` (GET):**
- **Tables Read:** GEE_API_ENDPOINTS + GEE_FIELD_CLASSES (JOIN)
- **Memory Created:** `[]db.APIEndpoint` with class information
- **Enhancement:** Dynamic route registration, class name resolution
- **Response Structure:** Enhanced with relationship data

**`/api/v1/flows` (GET):**
- **Tables Read:** runtime_flows (from praxis_runtime.db)
- **Memory Created:** `[]runtime.Flow` with active flows
- **Enhancement:** Multi-database coordination, active filtering
- **Response Structure:** Flow list with execution metadata

**`/flows/{flowId}/execute` (POST):**
- **Tables Read:** runtime_flows, runtime_rules, runtime_functions
- **Memory Created:** Complex execution context with flow definition parsing
- **Enhancement:** Multi-database coordination, execution state tracking
- **Response Structure:** 
  ```go
  {
      "success": true,
      "flow_id": int,
      "result": ExecutionResult
  }
  ```

### Dynamic Endpoints (Variable paths based on GEE_API_ENDPOINTS)

**Dynamic Route Pattern:** Based on ENDPOINT_PATH from database
- **Tables Read:** Varies based on endpoint configuration and class
- **Memory Created:** 
  ```go
  executionContext := map[string]interface{}{
      "endpoint":       endpoint,
      "request_data":   requestData,
      "path_params":    vars,
      "query_params":   r.URL.Query(),
      "headers":        r.Header,
      "class_id":       endpoint.ClassID,
      "class_name":     endpoint.ClassName,
  }
  ```
- **Enhancement:** Request parsing, parameter extraction, context building
- **Response Structure:** Endpoint-specific based on class configuration

---

## Key Memory Management Patterns

### 1. Lazy Loading Strategy
- **Implementation**: Structures created only when endpoints are called
- **Benefit**: Reduced memory footprint
- **Trade-off**: Query latency on each request

### 2. No Persistent Caching
- **Implementation**: Each request creates fresh structures
- **Benefit**: Always current data, no cache invalidation complexity
- **Trade-off**: Higher CPU/IO usage per request

### 3. JSON Flexibility vs Type Safety
- **Pattern**: Heavy use of `map[string]interface{}` for dynamic content
- **Benefit**: Handles unknown/variable structure data
- **Trade-off**: Runtime type checking required

### 4. Pointer Optimization for Optional Fields
- **Pattern**: Optional database fields become Go pointers
- **Implementation**: Only allocate pointer memory when database values exist
- **Benefit**: Memory efficiency for sparse data

### 5. Multi-Database Coordination
- **Pattern**: Separate structures for main DB vs runtime DB
- **Implementation**: Different connection managers and loaders
- **Benefit**: Separation of concerns between configuration and execution

### 6. Dynamic Route Registration
- **Pattern**: Database-driven API endpoint creation
- **Implementation**: Runtime router registration based on GEE_API_ENDPOINTS
- **Benefit**: API structure defined by data, not code

### 7. Enhanced Execution Context
- **Pattern**: Progressive enhancement of data structures during processing
- **Implementation**: Basic structs → JSON parsing → execution context → runtime enhancements
- **Benefit**: Rich context available for business logic execution

---

## Performance Characteristics

### Memory Usage
- **Per Request**: Typically 1-10KB for simple queries, 100KB-1MB for complex flow executions
- **Peak Usage**: During flow execution with large input/output data
- **Garbage Collection**: Structures cleaned up after request completion

### Query Patterns
- **Simple Selects**: Field classes, fields, API endpoints
- **Complex Joins**: API endpoints with class information
- **Multi-Table Coordination**: Flow execution across multiple tables
- **JSON Processing**: Significant CPU for large flow definitions

### Scaling Considerations
- **Read Scaling**: Excellent due to read-only database access
- **Concurrent Access**: SQLite handles multiple readers efficiently
- **Memory Scaling**: Linear with request volume (no caching)
- **CPU Scaling**: JSON parsing becomes bottleneck for complex flows

---

## Summary

Praxis implements a sophisticated data transformation pipeline that converts SQLite table data into rich Go memory structures. The system balances type safety with flexibility, using a combination of strongly-typed structs for known data and dynamic maps for variable content. The database-driven API endpoint generation creates a highly configurable system where the database schema directly influences the runtime behavior and available functionality.

The architecture prioritizes data freshness and simplicity over performance optimization, making it well-suited for configuration-driven applications where the data structure may evolve frequently.