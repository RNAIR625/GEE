package models

import (
	"sync"
	"time"
)

// CachedFieldClass represents a cached field class with lookup optimizations
type CachedFieldClass struct {
	FieldClass
	FieldsByID   map[int64]*CachedField `json:"-"` // Fast field lookup by ID
	FieldsByName map[string]*CachedField `json:"-"` // Fast field lookup by name
}

// CachedField represents a cached field with parent class reference
type CachedField struct {
	Field
	ParentClass *CachedFieldClass `json:"-"` // Reference to parent class
}

// CachedAutoFunction represents a cached auto-function with optimizations
type CachedAutoFunction struct {
	AutoFunction
	TableName    string `json:"table_name"`
	DBType       string `json:"db_type"`
	CachedResult interface{} `json:"-"` // Cached function result
	CachedAt     time.Time   `json:"-"` // When the result was cached
}

// DataCache holds all cached classes, fields, tables, and auto-functions loaded at startup
type DataCache struct {
	mu                  sync.RWMutex
	ClassesByID         map[int64]*CachedFieldClass   `json:"classes_by_id"`
	ClassesByName       map[string]*CachedFieldClass  `json:"classes_by_name"`
	FieldsByID          map[int64]*CachedField        `json:"fields_by_id"`
	FieldsByName        map[string]*CachedField       `json:"fields_by_name"`
	AllClasses          []*CachedFieldClass           `json:"all_classes"`
	AllFields           []*CachedField                `json:"all_fields"`
	
	// Auto-function cache
	AutoFunctionsByID   map[int64]*CachedAutoFunction `json:"auto_functions_by_id"`
	AutoFunctionsByName map[string]*CachedAutoFunction `json:"auto_functions_by_name"`
	AutoFunctionsByTable map[int64][]*CachedAutoFunction `json:"auto_functions_by_table"`
	AllAutoFunctions    []*CachedAutoFunction         `json:"all_auto_functions"`
	
	// Table cache for auto-function lookups
	TablesByID          map[int64]*Table              `json:"tables_by_id"`
	TablesByName        map[string]*Table             `json:"tables_by_name"`
	TableColumnsByTable map[int64][]*TableColumn      `json:"table_columns_by_table"`
	
	// Flow cache for API endpoint processing
	FlowsByID           map[int64]*Flow               `json:"flows_by_id"`
	FlowsByName         map[string]*Flow              `json:"flows_by_name"`
	FlowsByEndpoint     map[string]*Flow              `json:"flows_by_endpoint"`
	AllFlows            []*Flow                       `json:"all_flows"`
	
	// Rule cache for flow processing
	RuleGroupsByID      map[int64]*RuleGroup          `json:"rule_groups_by_id"`
	RuleGroupsByName    map[string]*RuleGroup         `json:"rule_groups_by_name"`
	RulesByID           map[int64]*Rule               `json:"rules_by_id"`
	RulesByGroup        map[int64][]*Rule             `json:"rules_by_group"`
	
	// API Endpoint cache
	APIEndpointsByID    map[int64]*APIEndpoint        `json:"api_endpoints_by_id"`
	APIEndpointsByPath  map[string]*APIEndpoint       `json:"api_endpoints_by_path"`
	AllAPIEndpoints     []*APIEndpoint                `json:"all_api_endpoints"`
	
	// Base Function cache
	BaseFunctionsByID   map[int64]*BaseFunction       `json:"base_functions_by_id"`
	BaseFunctionsByName map[string]*BaseFunction      `json:"base_functions_by_name"`
	AllBaseFunctions    []*BaseFunction               `json:"all_base_functions"`
	
	LastUpdated         time.Time                     `json:"last_updated"`
	IsLoaded            bool                          `json:"is_loaded"`
}

// NewDataCache creates a new data cache instance
func NewDataCache() *DataCache {
	return &DataCache{
		ClassesByID:         make(map[int64]*CachedFieldClass),
		ClassesByName:       make(map[string]*CachedFieldClass),
		FieldsByID:          make(map[int64]*CachedField),
		FieldsByName:        make(map[string]*CachedField),
		AllClasses:          make([]*CachedFieldClass, 0),
		AllFields:           make([]*CachedField, 0),
		
		AutoFunctionsByID:   make(map[int64]*CachedAutoFunction),
		AutoFunctionsByName: make(map[string]*CachedAutoFunction),
		AutoFunctionsByTable: make(map[int64][]*CachedAutoFunction),
		AllAutoFunctions:    make([]*CachedAutoFunction, 0),
		
		TablesByID:          make(map[int64]*Table),
		TablesByName:        make(map[string]*Table),
		TableColumnsByTable: make(map[int64][]*TableColumn),
		
		FlowsByID:           make(map[int64]*Flow),
		FlowsByName:         make(map[string]*Flow),
		FlowsByEndpoint:     make(map[string]*Flow),
		AllFlows:            make([]*Flow, 0),
		
		RuleGroupsByID:      make(map[int64]*RuleGroup),
		RuleGroupsByName:    make(map[string]*RuleGroup),
		RulesByID:           make(map[int64]*Rule),
		RulesByGroup:        make(map[int64][]*Rule),
		
		APIEndpointsByID:    make(map[int64]*APIEndpoint),
		APIEndpointsByPath:  make(map[string]*APIEndpoint),
		AllAPIEndpoints:     make([]*APIEndpoint, 0),
		
		BaseFunctionsByID:   make(map[int64]*BaseFunction),
		BaseFunctionsByName: make(map[string]*BaseFunction),
		AllBaseFunctions:    make([]*BaseFunction, 0),
		
		IsLoaded:            false,
	}
}

// LoadClasses loads all field classes into the cache
func (dc *DataCache) LoadClasses(classes []FieldClass) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing data
	dc.ClassesByID = make(map[int64]*CachedFieldClass)
	dc.ClassesByName = make(map[string]*CachedFieldClass)
	dc.AllClasses = make([]*CachedFieldClass, 0, len(classes))
	
	// Load classes into cache
	for _, class := range classes {
		cachedClass := &CachedFieldClass{
			FieldClass:   class,
			FieldsByID:   make(map[int64]*CachedField),
			FieldsByName: make(map[string]*CachedField),
		}
		
		dc.ClassesByID[class.ID] = cachedClass
		dc.ClassesByName[class.FieldClassName] = cachedClass
		dc.AllClasses = append(dc.AllClasses, cachedClass)
	}
	
	dc.LastUpdated = time.Now()
}

// LoadFields loads all fields into the cache and associates them with classes
func (dc *DataCache) LoadFields(fields []Field) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing field data
	dc.FieldsByID = make(map[int64]*CachedField)
	dc.FieldsByName = make(map[string]*CachedField)
	dc.AllFields = make([]*CachedField, 0, len(fields))
	
	// Load fields into cache
	for _, field := range fields {
		cachedField := &CachedField{
			Field: field,
		}
		
		// Associate with parent class if it exists
		if parentClass, exists := dc.ClassesByID[field.ClassID]; exists {
			cachedField.ParentClass = parentClass
			parentClass.FieldsByID[field.ID] = cachedField
			parentClass.FieldsByName[field.Name] = cachedField
		}
		
		dc.FieldsByID[field.ID] = cachedField
		dc.FieldsByName[field.Name] = cachedField
		dc.AllFields = append(dc.AllFields, cachedField)
	}
	
	dc.IsLoaded = true
	dc.LastUpdated = time.Now()
}

// GetClassByID returns a copy of the cached field class by ID (thread-safe)
func (dc *DataCache) GetClassByID(id int64) *FieldClass {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedClass, exists := dc.ClassesByID[id]; exists {
		// Return a copy to prevent external modification
		classCopy := cachedClass.FieldClass
		return &classCopy
	}
	return nil
}

// GetClassByName returns a copy of the cached field class by name (thread-safe)
func (dc *DataCache) GetClassByName(name string) *FieldClass {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedClass, exists := dc.ClassesByName[name]; exists {
		// Return a copy to prevent external modification
		classCopy := cachedClass.FieldClass
		return &classCopy
	}
	return nil
}

// GetFieldByID returns a copy of the cached field by ID (thread-safe)
func (dc *DataCache) GetFieldByID(id int64) *Field {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedField, exists := dc.FieldsByID[id]; exists {
		// Return a copy to prevent external modification
		fieldCopy := cachedField.Field
		return &fieldCopy
	}
	return nil
}

// GetFieldByName returns a copy of the cached field by name (thread-safe)
func (dc *DataCache) GetFieldByName(name string) *Field {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedField, exists := dc.FieldsByName[name]; exists {
		// Return a copy to prevent external modification
		fieldCopy := cachedField.Field
		return &fieldCopy
	}
	return nil
}

// GetAllClasses returns copies of all cached field classes (thread-safe)
func (dc *DataCache) GetAllClasses() []FieldClass {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	classes := make([]FieldClass, len(dc.AllClasses))
	for i, cachedClass := range dc.AllClasses {
		classes[i] = cachedClass.FieldClass
	}
	return classes
}

// GetAllFields returns copies of all cached fields (thread-safe)
func (dc *DataCache) GetAllFields() []Field {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	fields := make([]Field, len(dc.AllFields))
	for i, cachedField := range dc.AllFields {
		fields[i] = cachedField.Field
	}
	return fields
}

// GetFieldsForClass returns copies of all fields for a specific class (thread-safe)
func (dc *DataCache) GetFieldsForClass(classID int64) []Field {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedClass, exists := dc.ClassesByID[classID]; exists {
		fields := make([]Field, 0, len(cachedClass.FieldsByID))
		for _, cachedField := range cachedClass.FieldsByID {
			fields = append(fields, cachedField.Field)
		}
		return fields
	}
	return []Field{}
}

// GetFieldsForClassName returns copies of all fields for a specific class name (thread-safe)
func (dc *DataCache) GetFieldsForClassName(className string) []Field {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedClass, exists := dc.ClassesByName[className]; exists {
		fields := make([]Field, 0, len(cachedClass.FieldsByID))
		for _, cachedField := range cachedClass.FieldsByID {
			fields = append(fields, cachedField.Field)
		}
		return fields
	}
	return []Field{}
}

// GetCacheStats returns statistics about the cache
func (dc *DataCache) GetCacheStats() map[string]interface{} {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	return map[string]interface{}{
		"is_loaded":      dc.IsLoaded,
		"last_updated":   dc.LastUpdated,
		"classes_count":  len(dc.AllClasses),
		"fields_count":   len(dc.AllFields),
		"memory_usage":   dc.estimateMemoryUsage(),
	}
}

// estimateMemoryUsage provides a rough estimate of memory usage (internal method)
func (dc *DataCache) estimateMemoryUsage() map[string]int {
	baseClassSize := 200 // Rough estimate in bytes per class
	baseFieldSize := 150 // Rough estimate in bytes per field
	
	return map[string]int{
		"classes_bytes": len(dc.AllClasses) * baseClassSize,
		"fields_bytes":  len(dc.AllFields) * baseFieldSize,
		"total_bytes":   (len(dc.AllClasses) * baseClassSize) + (len(dc.AllFields) * baseFieldSize),
	}
}

// IsDataLoaded returns whether the cache has been loaded
func (dc *DataCache) IsDataLoaded() bool {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	return dc.IsLoaded
}

// Clear clears all cached data
func (dc *DataCache) Clear() {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	dc.ClassesByID = make(map[int64]*CachedFieldClass)
	dc.ClassesByName = make(map[string]*CachedFieldClass)
	dc.FieldsByID = make(map[int64]*CachedField)
	dc.FieldsByName = make(map[string]*CachedField)
	dc.AllClasses = make([]*CachedFieldClass, 0)
	dc.AllFields = make([]*CachedField, 0)
	
	dc.AutoFunctionsByID = make(map[int64]*CachedAutoFunction)
	dc.AutoFunctionsByName = make(map[string]*CachedAutoFunction)
	dc.AutoFunctionsByTable = make(map[int64][]*CachedAutoFunction)
	dc.AllAutoFunctions = make([]*CachedAutoFunction, 0)
	
	dc.TablesByID = make(map[int64]*Table)
	dc.TablesByName = make(map[string]*Table)
	dc.TableColumnsByTable = make(map[int64][]*TableColumn)
	
	dc.IsLoaded = false
}

// LoadTables loads all tables into the cache
func (dc *DataCache) LoadTables(tables []Table) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing table data
	dc.TablesByID = make(map[int64]*Table)
	dc.TablesByName = make(map[string]*Table)
	
	// Load tables into cache
	for _, table := range tables {
		tableCopy := table
		dc.TablesByID[table.ID] = &tableCopy
		dc.TablesByName[table.TableName] = &tableCopy
	}
	
	dc.LastUpdated = time.Now()
}

// LoadTableColumns loads table columns into the cache
func (dc *DataCache) LoadTableColumns(columns []TableColumn) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing column data
	dc.TableColumnsByTable = make(map[int64][]*TableColumn)
	
	// Group columns by table
	for _, column := range columns {
		columnCopy := column
		dc.TableColumnsByTable[column.TableID] = append(dc.TableColumnsByTable[column.TableID], &columnCopy)
	}
	
	dc.LastUpdated = time.Now()
}

// LoadAutoFunctions loads all auto-functions into the cache
func (dc *DataCache) LoadAutoFunctions(functions []AutoFunction) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing auto-function data
	dc.AutoFunctionsByID = make(map[int64]*CachedAutoFunction)
	dc.AutoFunctionsByName = make(map[string]*CachedAutoFunction)
	dc.AutoFunctionsByTable = make(map[int64][]*CachedAutoFunction)
	dc.AllAutoFunctions = make([]*CachedAutoFunction, 0, len(functions))
	
	// Load auto-functions into cache
	for _, function := range functions {
		// Get table information for this function
		tableName := ""
		dbType := ""
		if table, exists := dc.TablesByID[function.TableID]; exists {
			tableName = table.TableName
			if table.DBType != nil {
				dbType = *table.DBType
			}
		}
		
		cachedFunction := &CachedAutoFunction{
			AutoFunction: function,
			TableName:    tableName,
			DBType:       dbType,
		}
		
		dc.AutoFunctionsByID[function.ID] = cachedFunction
		dc.AutoFunctionsByName[function.FunctionName] = cachedFunction
		dc.AutoFunctionsByTable[function.TableID] = append(dc.AutoFunctionsByTable[function.TableID], cachedFunction)
		dc.AllAutoFunctions = append(dc.AllAutoFunctions, cachedFunction)
	}
	
	dc.LastUpdated = time.Now()
}

// GetAutoFunctionByID returns a cached auto-function by ID
func (dc *DataCache) GetAutoFunctionByID(id int64) *CachedAutoFunction {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedFunction, exists := dc.AutoFunctionsByID[id]; exists {
		return cachedFunction
	}
	return nil
}

// GetAutoFunctionByName returns a cached auto-function by name
func (dc *DataCache) GetAutoFunctionByName(name string) *CachedAutoFunction {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedFunction, exists := dc.AutoFunctionsByName[name]; exists {
		return cachedFunction
	}
	return nil
}

// GetAutoFunctionsForTable returns all auto-functions for a specific table
func (dc *DataCache) GetAutoFunctionsForTable(tableID int64) []*CachedAutoFunction {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if functions, exists := dc.AutoFunctionsByTable[tableID]; exists {
		return functions
	}
	return []*CachedAutoFunction{}
}

// GetTableByID returns a cached table by ID
func (dc *DataCache) GetTableByID(id int64) *Table {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if table, exists := dc.TablesByID[id]; exists {
		return table
	}
	return nil
}

// GetTableByName returns a cached table by name
func (dc *DataCache) GetTableByName(name string) *Table {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if table, exists := dc.TablesByName[name]; exists {
		return table
	}
	return nil
}

// GetTableColumnsForTable returns all columns for a specific table
func (dc *DataCache) GetTableColumnsForTable(tableID int64) []*TableColumn {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if columns, exists := dc.TableColumnsByTable[tableID]; exists {
		return columns
	}
	return []*TableColumn{}
}

// CacheAutoFunctionResult caches a function execution result
func (dc *DataCache) CacheAutoFunctionResult(functionID int64, result interface{}) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	if cachedFunction, exists := dc.AutoFunctionsByID[functionID]; exists {
		cachedFunction.CachedResult = result
		cachedFunction.CachedAt = time.Now()
	}
}

// GetCachedAutoFunctionResult retrieves a cached function result if valid
func (dc *DataCache) GetCachedAutoFunctionResult(functionID int64) (interface{}, bool) {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if cachedFunction, exists := dc.AutoFunctionsByID[functionID]; exists {
		if cachedFunction.CacheEnabled && cachedFunction.CachedResult != nil {
			// Check if cache is still valid
			if time.Since(cachedFunction.CachedAt).Seconds() < float64(cachedFunction.CacheTTL) {
				return cachedFunction.CachedResult, true
			}
		}
	}
	return nil, false
}

// InvalidateAutoFunctionCache clears cached results for a function
func (dc *DataCache) InvalidateAutoFunctionCache(functionID int64) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	if cachedFunction, exists := dc.AutoFunctionsByID[functionID]; exists {
		cachedFunction.CachedResult = nil
		cachedFunction.CachedAt = time.Time{}
	}
}

// LoadFlows loads all flows into the cache
func (dc *DataCache) LoadFlows(flows []Flow) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing flow data
	dc.FlowsByID = make(map[int64]*Flow)
	dc.FlowsByName = make(map[string]*Flow)
	dc.FlowsByEndpoint = make(map[string]*Flow)
	dc.AllFlows = make([]*Flow, 0, len(flows))
	
	// Load flows into cache
	for _, flow := range flows {
		flowCopy := flow
		dc.FlowsByID[flow.FlowID] = &flowCopy
		dc.FlowsByName[flow.FlowName] = &flowCopy
		
		// Index by endpoint path for quick lookup
		if flow.EndpointPath != nil && flow.HTTPMethod != nil {
			endpointKey := *flow.HTTPMethod + " " + *flow.EndpointPath
			dc.FlowsByEndpoint[endpointKey] = &flowCopy
		}
		
		dc.AllFlows = append(dc.AllFlows, &flowCopy)
	}
	
	dc.LastUpdated = time.Now()
}

// LoadRuleGroups loads rule groups into the cache
func (dc *DataCache) LoadRuleGroups(ruleGroups []RuleGroup) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing rule group data
	dc.RuleGroupsByID = make(map[int64]*RuleGroup)
	dc.RuleGroupsByName = make(map[string]*RuleGroup)
	
	// Load rule groups into cache
	for _, rg := range ruleGroups {
		rgCopy := rg
		dc.RuleGroupsByID[rg.GroupID] = &rgCopy
		dc.RuleGroupsByName[rg.GroupName] = &rgCopy
	}
	
	dc.LastUpdated = time.Now()
}

// LoadRules loads rules into the cache and associates them with rule groups
func (dc *DataCache) LoadRules(rules []Rule) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing rule data
	dc.RulesByID = make(map[int64]*Rule)
	dc.RulesByGroup = make(map[int64][]*Rule)
	
	// Load rules into cache
	for _, rule := range rules {
		ruleCopy := rule
		dc.RulesByID[rule.RuleID] = &ruleCopy
		
		// Associate with rule group if it exists
		if rule.RuleGroupID != nil {
			dc.RulesByGroup[*rule.RuleGroupID] = append(dc.RulesByGroup[*rule.RuleGroupID], &ruleCopy)
			
			// Also add to rule group if it exists in cache
			if ruleGroup, exists := dc.RuleGroupsByID[*rule.RuleGroupID]; exists {
				ruleGroup.Rules = append(ruleGroup.Rules, ruleCopy)
			}
		}
	}
	
	dc.LastUpdated = time.Now()
}

// LoadAPIEndpoints loads API endpoints into the cache
func (dc *DataCache) LoadAPIEndpoints(endpoints []APIEndpoint) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing endpoint data
	dc.APIEndpointsByID = make(map[int64]*APIEndpoint)
	dc.APIEndpointsByPath = make(map[string]*APIEndpoint)
	dc.AllAPIEndpoints = make([]*APIEndpoint, 0, len(endpoints))
	
	// Load endpoints into cache
	for _, endpoint := range endpoints {
		endpointCopy := endpoint
		dc.APIEndpointsByID[endpoint.EndpointID] = &endpointCopy
		
		// Index by path and method for quick lookup
		pathKey := endpoint.HTTPMethod + " " + endpoint.EndpointPath
		dc.APIEndpointsByPath[pathKey] = &endpointCopy
		
		// Associate with flow if it exists
		if flow, exists := dc.FlowsByEndpoint[pathKey]; exists {
			endpointCopy.Flow = flow
		}
		
		dc.AllAPIEndpoints = append(dc.AllAPIEndpoints, &endpointCopy)
	}
	
	dc.LastUpdated = time.Now()
}

// LoadBaseFunctions loads base functions into the cache
func (dc *DataCache) LoadBaseFunctions(functions []BaseFunction) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	
	// Clear existing function data
	dc.BaseFunctionsByID = make(map[int64]*BaseFunction)
	dc.BaseFunctionsByName = make(map[string]*BaseFunction)
	dc.AllBaseFunctions = make([]*BaseFunction, 0, len(functions))
	
	// Load functions into cache
	for _, function := range functions {
		functionCopy := function
		dc.BaseFunctionsByID[function.FunctionID] = &functionCopy
		dc.BaseFunctionsByName[function.FunctionName] = &functionCopy
		dc.AllBaseFunctions = append(dc.AllBaseFunctions, &functionCopy)
	}
	
	dc.LastUpdated = time.Now()
}

// GetFlowByEndpoint returns a flow for a specific endpoint and method
func (dc *DataCache) GetFlowByEndpoint(method, path string) *Flow {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	endpointKey := method + " " + path
	if flow, exists := dc.FlowsByEndpoint[endpointKey]; exists {
		return flow
	}
	return nil
}

// GetFlowByID returns a flow by ID
func (dc *DataCache) GetFlowByID(id int64) *Flow {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if flow, exists := dc.FlowsByID[id]; exists {
		return flow
	}
	return nil
}

// GetRuleGroupByID returns a rule group by ID
func (dc *DataCache) GetRuleGroupByID(id int64) *RuleGroup {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if ruleGroup, exists := dc.RuleGroupsByID[id]; exists {
		return ruleGroup
	}
	return nil
}

// GetRulesForGroup returns all rules for a specific group
func (dc *DataCache) GetRulesForGroup(groupID int64) []*Rule {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if rules, exists := dc.RulesByGroup[groupID]; exists {
		return rules
	}
	return []*Rule{}
}

// GetAPIEndpointByPath returns an API endpoint by path and method
func (dc *DataCache) GetAPIEndpointByPath(method, path string) *APIEndpoint {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	pathKey := method + " " + path
	if endpoint, exists := dc.APIEndpointsByPath[pathKey]; exists {
		return endpoint
	}
	return nil
}

// GetBaseFunctionByName returns a base function by name
func (dc *DataCache) GetBaseFunctionByName(name string) *BaseFunction {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	if function, exists := dc.BaseFunctionsByName[name]; exists {
		return function
	}
	return nil
}

// GetMemoryStructure returns the complete memory structure for debugging
func (dc *DataCache) GetMemoryStructure() map[string]interface{} {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	
	return map[string]interface{}{
		"cache_stats": map[string]interface{}{
			"is_loaded":         dc.IsLoaded,
			"last_updated":      dc.LastUpdated,
			"classes_count":     len(dc.AllClasses),
			"fields_count":      len(dc.AllFields),
			"tables_count":      len(dc.TablesByID),
			"auto_functions_count": len(dc.AllAutoFunctions),
			"flows_count":       len(dc.AllFlows),
			"rule_groups_count": len(dc.RuleGroupsByID),
			"rules_count":       len(dc.RulesByID),
			"api_endpoints_count": len(dc.AllAPIEndpoints),
			"base_functions_count": len(dc.AllBaseFunctions),
		},
		"flow_structure": dc.buildFlowStructure(),
		"index_structure": map[string]interface{}{
			"flows_by_endpoint": dc.getEndpointKeys(),
			"rule_groups_by_name": dc.getRuleGroupNames(),
			"api_endpoints_by_path": dc.getAPIEndpointPaths(),
		},
	}
}

// Helper method to build flow structure for debugging
func (dc *DataCache) buildFlowStructure() map[string]interface{} {
	flowStructure := make(map[string]interface{})
	
	for _, flow := range dc.AllFlows {
		flowInfo := map[string]interface{}{
			"flow_id":       flow.FlowID,
			"flow_name":     flow.FlowName,
			"flow_type":     flow.FlowType,
			"endpoint_path": flow.EndpointPath,
			"http_method":   flow.HTTPMethod,
			"steps_count":   len(flow.Steps),
		}
		
		// Add step details
		steps := make([]map[string]interface{}, 0, len(flow.Steps))
		for _, step := range flow.Steps {
			stepInfo := map[string]interface{}{
				"step_id":      step.StepID,
				"step_order":   step.StepOrder,
				"step_name":    step.StepName,
				"rule_group_id": step.RuleGroupID,
				"rules_count":  len(step.Rules),
			}
			
			// Add rule details if available
			if step.RuleGroupID != nil {
				if rules := dc.GetRulesForGroup(*step.RuleGroupID); rules != nil {
					ruleInfo := make([]map[string]interface{}, 0, len(rules))
					for _, rule := range rules {
						ruleInfo = append(ruleInfo, map[string]interface{}{
							"rule_id":       rule.RuleID,
							"rule_name":     rule.RuleName,
							"rule_type":     rule.RuleType,
							"rule_priority": rule.RulePriority,
						})
					}
					stepInfo["rules"] = ruleInfo
				}
			}
			
			steps = append(steps, stepInfo)
		}
		flowInfo["steps"] = steps
		
		flowStructure[flow.FlowName] = flowInfo
	}
	
	return flowStructure
}

// Helper methods for structure debugging
func (dc *DataCache) getEndpointKeys() []string {
	keys := make([]string, 0, len(dc.FlowsByEndpoint))
	for key := range dc.FlowsByEndpoint {
		keys = append(keys, key)
	}
	return keys
}

func (dc *DataCache) getRuleGroupNames() []string {
	names := make([]string, 0, len(dc.RuleGroupsByName))
	for name := range dc.RuleGroupsByName {
		names = append(names, name)
	}
	return names
}

func (dc *DataCache) getAPIEndpointPaths() []string {
	paths := make([]string, 0, len(dc.APIEndpointsByPath))
	for path := range dc.APIEndpointsByPath {
		paths = append(paths, path)
	}
	return paths
}