package api

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"github.com/GEE/Praxis/internal/config"
	"github.com/GEE/Praxis/internal/db"
	"github.com/GEE/Praxis/internal/debug"
	"github.com/GEE/Praxis/internal/runtime"
	"strconv"

	"github.com/gorilla/mux"
)

type Server struct {
	config        *config.Config
	dbManager     *db.Manager
	apiEndpoints  []db.APIEndpoint
	dynamicRouter *mux.Router
	runtimeLoader *runtime.RuntimeLoader
	flowExecutor  *runtime.FlowExecutor
	forgeLoader   *runtime.ForgeLoader
}

func NewServer(cfg *config.Config, dbManager *db.Manager) *Server {
	// Initialize runtime loader with the runtime database
	runtimePath := "../Forge/praxis_runtime.db"
	if cfg.Database.RuntimeDBPath != "" {
		runtimePath = cfg.Database.RuntimeDBPath
	}
	
	runtimeLoader, err := runtime.NewRuntimeLoader(runtimePath)
	if err != nil {
		log.Printf("Warning: Failed to initialize runtime loader: %v", err)
		// Continue without runtime features
	}
	
	// Initialize Forge loader to load auto-functions
	forgePath := "../Forge"
	forgeLoader, err := runtime.NewForgeLoader(forgePath)
	if err != nil {
		log.Printf("Warning: Failed to initialize Forge loader: %v", err)
		// Continue without auto-function features
	} else {
		// Load auto-function data into cache
		if err := loadAutoFunctionData(dbManager, forgeLoader); err != nil {
			log.Printf("Warning: Failed to load auto-function data: %v", err)
		}
		
		// Load flow-related data into cache
		if err := loadFlowData(dbManager, forgeLoader); err != nil {
			log.Printf("Warning: Failed to load flow data: %v", err)
		}
	}
	
	var flowExecutor *runtime.FlowExecutor
	if runtimeLoader != nil {
		flowExecutor = runtime.NewFlowExecutor(runtimeLoader)
	}
	
	return &Server{
		config:        cfg,
		dbManager:     dbManager,
		runtimeLoader: runtimeLoader,
		flowExecutor:  flowExecutor,
		forgeLoader:   forgeLoader,
	}
}

func (s *Server) Router() http.Handler {
	r := mux.NewRouter()
	s.dynamicRouter = r

	// Load and register dynamic API endpoints
	s.registerDynamicEndpoints()

	// API routes
	api := r.PathPrefix("/api/v1").Subrouter()
	
	// Database upload endpoint
	api.HandleFunc("/database/upload", s.handleDatabaseUpload).Methods("POST")
	
	// Data retrieval endpoints
	api.HandleFunc("/field-classes", s.handleGetFieldClasses).Methods("GET")
	api.HandleFunc("/fields", s.handleGetFields).Methods("GET")
	api.HandleFunc("/flow-definitions", s.handleGetFlowDefinitions).Methods("GET")
	
	// Execution endpoints
	api.HandleFunc("/execution/jobs/{jobId}/submit", s.handleSubmitJob).Methods("POST")
	api.HandleFunc("/execution/jobs/{jobId}/status", s.handleGetJobStatus).Methods("GET")
	api.HandleFunc("/execution/jobs/{jobId}/result", s.handleGetJobResult).Methods("GET")
	api.HandleFunc("/execution/jobs/{jobId}/logs", s.handleGetJobLogs).Methods("GET")
	api.HandleFunc("/execution/workers/status", s.handleGetWorkerStatus).Methods("GET")
	
	// Status endpoints
	api.HandleFunc("/health", s.handleHealth).Methods("GET")
	api.HandleFunc("/status", s.handleStatus).Methods("GET")
	api.HandleFunc("/cache/stats", s.handleCacheStats).Methods("GET")
	api.HandleFunc("/cache/reload", s.handleCacheReload).Methods("POST")
	
	// API endpoints management
	api.HandleFunc("/api-endpoints", s.handleGetAPIEndpoints).Methods("GET")
	
	// Flow execution endpoints
	api.HandleFunc("/flows", s.handleGetFlows).Methods("GET")
	api.HandleFunc("/flows/{flowId}/execute", s.handleExecuteFlow).Methods("POST")
	api.HandleFunc("/reload", s.handleReload).Methods("POST")

	// Auto-function endpoints
	api.HandleFunc("/auto-functions", s.handleGetAutoFunctions).Methods("GET")
	api.HandleFunc("/auto-functions/reload", s.handleReloadAutoFunctions).Methods("POST")
	api.HandleFunc("/auto-functions/execute/{functionName}", s.handleExecuteAutoFunction).Methods("POST")
	
	// Flow and memory structure endpoints
	api.HandleFunc("/memory/structure", s.handleGetMemoryStructure).Methods("GET")
	api.HandleFunc("/flows/cached", s.handleGetCachedFlows).Methods("GET")
	api.HandleFunc("/rules/groups", s.handleGetRuleGroups).Methods("GET")
	api.HandleFunc("/rules", s.handleGetRules).Methods("GET")
	api.HandleFunc("/base-functions", s.handleGetBaseFunctions).Methods("GET")
	
	// Loyalty API endpoints (dynamically loaded from cache)
	api.HandleFunc("/loyalty/reload", s.handleReloadLoyaltyAPI).Methods("POST")
	api.HandleFunc("/loyalty/endpoints", s.handleGetLoyaltyEndpoints).Methods("GET")

	// Add CORS middleware
	r.Use(corsMiddleware)

	return r
}

// handleDatabaseUpload handles SQLite database file upload
func (s *Server) handleDatabaseUpload(w http.ResponseWriter, r *http.Request) {
	// Parse multipart form
	err := r.ParseMultipartForm(100 << 20) // 100 MB max
	if err != nil {
		http.Error(w, "Failed to parse form", http.StatusBadRequest)
		return
	}

	// Get file from form
	file, header, err := r.FormFile("database")
	if err != nil {
		http.Error(w, "Failed to get file from form", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Save database
	if err := s.dbManager.SaveDatabase(file, header.Filename); err != nil {
		http.Error(w, fmt.Sprintf("Failed to save database: %v", err), http.StatusInternalServerError)
		return
	}

	// Re-register dynamic endpoints with the new database
	s.registerDynamicEndpoints()

	// Return success response
	response := map[string]interface{}{
		"success": true,
		"message": "Database uploaded successfully",
		"filename": header.Filename,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleGetFieldClasses returns all field classes
func (s *Server) handleGetFieldClasses(w http.ResponseWriter, r *http.Request) {
	classes, err := s.dbManager.GetFieldClasses()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get field classes: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    classes,
		"count":   len(classes),
	})
}

// handleGetFields returns all fields
func (s *Server) handleGetFields(w http.ResponseWriter, r *http.Request) {
	fields, err := s.dbManager.GetFields()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get fields: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    fields,
		"count":   len(fields),
	})
}

// handleGetFlowDefinitions returns all flow definitions
func (s *Server) handleGetFlowDefinitions(w http.ResponseWriter, r *http.Request) {
	flows, err := s.dbManager.GetFlowDefinitions()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get flow definitions: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    flows,
		"count":   len(flows),
	})
}

// handleHealth returns server health status
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "healthy",
		"service": "praxis",
	})
}

// handleStatus returns detailed server status
func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	status := s.dbManager.GetStatus()
	status["server"] = map[string]interface{}{
		"host": s.config.Server.Host,
		"port": s.config.Server.Port,
	}
	status["cache"] = s.dbManager.GetCacheStats()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// handleSubmitJob handles job submission for execution
func (s *Server) handleSubmitJob(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	jobId := vars["jobId"]
	
	var request struct {
		WorkerDBName string `json:"worker_db_name"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	// Submit job to execution queue
	if err := s.dbManager.SubmitExecutionJob(jobId, request.WorkerDBName); err != nil {
		http.Error(w, fmt.Sprintf("Failed to submit job: %v", err), http.StatusInternalServerError)
		return
	}
	
	response := map[string]interface{}{
		"success": true,
		"message": "Job submitted for execution",
		"job_id":  jobId,
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleGetJobStatus returns job execution status
func (s *Server) handleGetJobStatus(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	jobId := vars["jobId"]
	
	status, err := s.dbManager.GetJobStatus(jobId)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get job status: %v", err), http.StatusInternalServerError)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"job":     status,
	})
}

// handleGetJobResult returns job execution result
func (s *Server) handleGetJobResult(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	jobId := vars["jobId"]
	
	result, err := s.dbManager.GetJobResult(jobId)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get job result: %v", err), http.StatusInternalServerError)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"result":  result,
	})
}

// handleGetJobLogs returns job execution logs
func (s *Server) handleGetJobLogs(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	jobId := vars["jobId"]
	
	logs, err := s.dbManager.GetJobLogs(jobId)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get job logs: %v", err), http.StatusInternalServerError)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"logs":    logs,
	})
}

// handleGetWorkerStatus returns worker status for horizontal scaling
func (s *Server) handleGetWorkerStatus(w http.ResponseWriter, r *http.Request) {
	workers, err := s.dbManager.GetWorkerStatus()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get worker status: %v", err), http.StatusInternalServerError)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"workers": workers,
		"count":   len(workers),
	})
}

// registerDynamicEndpoints loads API endpoints from the database and registers them
func (s *Server) registerDynamicEndpoints() {
	// Only register if we have a database loaded
	if s.dbManager == nil {
		return
	}

	// Get API endpoints from database
	endpoints, err := s.dbManager.GetAPIEndpoints()
	if err != nil {
		log.Printf("Failed to load API endpoints: %v", err)
		return
	}

	s.apiEndpoints = endpoints
	
	// Register each endpoint
	for _, endpoint := range endpoints {
		// Create a copy of endpoint for closure
		ep := endpoint
		
		// Register the route with the dynamic handler
		s.dynamicRouter.HandleFunc(ep.EndpointPath, func(w http.ResponseWriter, r *http.Request) {
			s.handleDynamicEndpoint(w, r, ep)
		}).Methods(ep.HTTPMethod)
		
		log.Printf("Registered dynamic endpoint: %s %s -> Class: %s", 
			ep.HTTPMethod, ep.EndpointPath, ep.ClassName)
	}
	
	log.Printf("Registered %d dynamic API endpoints", len(endpoints))
}

// handleDynamicEndpoint handles requests to dynamically registered API endpoints
func (s *Server) handleDynamicEndpoint(w http.ResponseWriter, r *http.Request, endpoint db.APIEndpoint) {
	// Log the request
	operationID := ""
	if endpoint.OperationID != nil {
		operationID = *endpoint.OperationID
	}
	log.Printf("Dynamic endpoint called: %s %s (Class: %s, Operation: %s)", 
		r.Method, r.URL.Path, endpoint.ClassName, operationID)
	
	// Parse request body if present
	var requestData map[string]interface{}
	if r.Body != nil {
		defer r.Body.Close()
		if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
			// Empty body is okay for some requests
			requestData = make(map[string]interface{})
		}
	}
	
	// Extract path parameters
	vars := mux.Vars(r)
	
	// Prepare execution context
	executionContext := map[string]interface{}{
		"endpoint":       endpoint,
		"request_data":   requestData,
		"path_params":    vars,
		"query_params":   r.URL.Query(),
		"headers":        r.Header,
		"class_id":       endpoint.ClassID,
		"class_name":     endpoint.ClassName,
	}
	
	// TODO: Here we would integrate with the rules engine to execute
	// the appropriate business logic based on the class and operation
	
	// For now, return a mock response
	response := map[string]interface{}{
		"status":    "success",
		"message":   fmt.Sprintf("Endpoint %s %s processed", endpoint.HTTPMethod, endpoint.EndpointPath),
		"class":     endpoint.ClassName,
		"operation": endpoint.OperationID,
		"data":      executionContext,
	}
	
	// Send response
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleGetAPIEndpoints returns all registered API endpoints
func (s *Server) handleGetAPIEndpoints(w http.ResponseWriter, r *http.Request) {
	endpoints, err := s.dbManager.GetAPIEndpoints()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get API endpoints: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    endpoints,
		"count":   len(endpoints),
	})
}

// corsMiddleware adds CORS headers
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// handleGetFlows returns all deployed flows
func (s *Server) handleGetFlows(w http.ResponseWriter, r *http.Request) {
	if s.runtimeLoader == nil {
		http.Error(w, "Runtime not initialized", http.StatusServiceUnavailable)
		return
	}

	flows, err := s.runtimeLoader.LoadActiveFlows()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to load flows: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"flows":   flows,
		"count":   len(flows),
	})
}

// handleExecuteFlow executes a specific flow
func (s *Server) handleExecuteFlow(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	flowIdStr := vars["flowId"]
	flowId, err := strconv.Atoi(flowIdStr)
	if err != nil {
		http.Error(w, "Invalid flow ID", http.StatusBadRequest)
		return
	}

	result, err := debug.LogFunctionCall("handleExecuteFlow", map[string]interface{}{
		"url": r.URL.String(),
		"method": r.Method,
		"flow_id": flowId,
	}, func() (interface{}, error) {
		if s.flowExecutor == nil {
			return nil, fmt.Errorf("flow executor not initialized")
		}

		// Parse input data
		var inputData map[string]interface{}
		if err := json.NewDecoder(r.Body).Decode(&inputData); err != nil {
			// Empty input is okay
			inputData = make(map[string]interface{})
		}

		// Execute flow
		result, err := s.flowExecutor.ExecuteFlow(flowId, inputData)
		if err != nil {
			return nil, fmt.Errorf("flow execution failed: %v", err)
		}

		return result, nil
	})

	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Return result
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"flow_id": flowId,
		"result":  result,
	})
}

// handleReload reloads the runtime database
func (s *Server) handleReload(w http.ResponseWriter, r *http.Request) {
	if s.runtimeLoader == nil {
		http.Error(w, "Runtime not initialized", http.StatusServiceUnavailable)
		return
	}

	// Close existing loader
	if err := s.runtimeLoader.Close(); err != nil {
		log.Printf("Error closing runtime loader: %v", err)
	}

	// Reinitialize runtime loader
	runtimePath := "../Forge/praxis_runtime.db"
	if s.config.Database.RuntimeDBPath != "" {
		runtimePath = s.config.Database.RuntimeDBPath
	}

	newLoader, err := runtime.NewRuntimeLoader(runtimePath)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to reload runtime: %v", err), http.StatusInternalServerError)
		return
	}

	s.runtimeLoader = newLoader
	s.flowExecutor = runtime.NewFlowExecutor(newLoader)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Runtime reloaded successfully",
	})
}

// handleCacheStats returns cache statistics
func (s *Server) handleCacheStats(w http.ResponseWriter, r *http.Request) {
	stats := s.dbManager.GetCacheStats()
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"cache_stats": stats,
	})
}

// handleCacheReload forces a reload of the cache
func (s *Server) handleCacheReload(w http.ResponseWriter, r *http.Request) {
	if err := s.dbManager.ReloadCache(); err != nil {
		http.Error(w, fmt.Sprintf("Failed to reload cache: %v", err), http.StatusInternalServerError)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Cache reloaded successfully",
		"cache_stats": s.dbManager.GetCacheStats(),
	})
}

// loadAutoFunctionData loads auto-function data from Forge into the cache
func loadAutoFunctionData(dbManager *db.Manager, forgeLoader *runtime.ForgeLoader) error {
	// Load tables
	tables, err := forgeLoader.LoadTables()
	if err != nil {
		return fmt.Errorf("failed to load tables: %w", err)
	}
	
	// Load table columns
	columns, err := forgeLoader.LoadTableColumns()
	if err != nil {
		return fmt.Errorf("failed to load table columns: %w", err)
	}
	
	// Load auto-functions
	functions, err := forgeLoader.LoadAutoFunctions()
	if err != nil {
		return fmt.Errorf("failed to load auto-functions: %w", err)
	}
	
	// Load data into cache
	cache := dbManager.GetCache()
	cache.LoadTables(tables)
	cache.LoadTableColumns(columns)
	cache.LoadAutoFunctions(functions)
	
	forgeLoader.MarkUpdated()
	
	log.Printf("Loaded auto-function data: %d tables, %d columns, %d functions", 
		len(tables), len(columns), len(functions))
	
	return nil
}

// loadFlowData loads flow-related data from Forge into the cache
func loadFlowData(dbManager *db.Manager, forgeLoader *runtime.ForgeLoader) error {
	// Load flows
	flows, err := forgeLoader.LoadFlows()
	if err != nil {
		return fmt.Errorf("failed to load flows: %w", err)
	}
	
	// Load rule groups
	ruleGroups, err := forgeLoader.LoadRuleGroups()
	if err != nil {
		return fmt.Errorf("failed to load rule groups: %w", err)
	}
	
	// Load all rules
	rules, err := forgeLoader.LoadAllRules()
	if err != nil {
		return fmt.Errorf("failed to load rules: %w", err)
	}
	
	// Load API endpoints
	apiEndpoints, err := forgeLoader.LoadAPIEndpoints()
	if err != nil {
		return fmt.Errorf("failed to load API endpoints: %w", err)
	}
	
	// Load base functions
	baseFunctions, err := forgeLoader.LoadBaseFunctions()
	if err != nil {
		return fmt.Errorf("failed to load base functions: %w", err)
	}
	
	// Load data into cache
	cache := dbManager.GetCache()
	cache.LoadFlows(flows)
	cache.LoadRuleGroups(ruleGroups)
	cache.LoadRules(rules)
	cache.LoadAPIEndpoints(apiEndpoints)
	cache.LoadBaseFunctions(baseFunctions)
	
	forgeLoader.MarkUpdated()
	
	log.Printf("Loaded flow data: %d flows, %d rule groups, %d rules, %d API endpoints, %d base functions", 
		len(flows), len(ruleGroups), len(rules), len(apiEndpoints), len(baseFunctions))
	
	return nil
}

// handleGetAutoFunctions returns all cached auto-functions
func (s *Server) handleGetAutoFunctions(w http.ResponseWriter, r *http.Request) {
	cache := s.dbManager.GetCache()
	
	// Get all auto-functions
	functions := cache.AllAutoFunctions
	
	// Convert to response format
	functionData := make([]map[string]interface{}, len(functions))
	for i, fn := range functions {
		functionData[i] = map[string]interface{}{
			"id":                fn.ID,
			"table_id":          fn.TableID,
			"table_name":        fn.TableName,
			"db_type":           fn.DBType,
			"function_name":     fn.FunctionName,
			"function_type":     fn.FunctionType,
			"function_signature": fn.FunctionSignature,
			"return_type":       fn.ReturnType,
			"description":       fn.Description,
			"cache_enabled":     fn.CacheEnabled,
			"cache_ttl":         fn.CacheTTL,
			"is_active":         fn.IsActive,
		}
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"functions": functionData,
		"count":     len(functionData),
	})
}

// handleReloadAutoFunctions reloads auto-function data from Forge
func (s *Server) handleReloadAutoFunctions(w http.ResponseWriter, r *http.Request) {
	if s.forgeLoader == nil {
		http.Error(w, "Forge loader not initialized", http.StatusServiceUnavailable)
		return
	}
	
	// Reload auto-function data
	if err := loadAutoFunctionData(s.dbManager, s.forgeLoader); err != nil {
		http.Error(w, fmt.Sprintf("Failed to reload auto-functions: %v", err), http.StatusInternalServerError)
		return
	}
	
	cache := s.dbManager.GetCache()
	functionCount := len(cache.AllAutoFunctions)
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Auto-functions reloaded successfully",
		"function_count": functionCount,
	})
}

// handleExecuteAutoFunction executes a specific auto-function
func (s *Server) handleExecuteAutoFunction(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	functionName := vars["functionName"]
	
	cache := s.dbManager.GetCache()
	
	// Get the function from cache
	cachedFunction := cache.GetAutoFunctionByName(functionName)
	if cachedFunction == nil {
		http.Error(w, fmt.Sprintf("Function %s not found", functionName), http.StatusNotFound)
		return
	}
	
	// Parse request parameters
	var requestData map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		requestData = make(map[string]interface{})
	}
	
	// Check for cached result
	if result, found := cache.GetCachedAutoFunctionResult(cachedFunction.ID); found {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"function": functionName,
			"result":   result,
			"cached":   true,
		})
		return
	}
	
	// Execute the function (this would be integrated with actual table data)
	// For now, return a mock result
	var result interface{}
	
	switch cachedFunction.FunctionType {
	case "PK_EXISTS":
		result = true // Mock: primary key exists
	case "COLUMN_GETTER":
		result = "mock_value" // Mock: column value
	default:
		result = nil
	}
	
	// Cache the result if caching is enabled
	if cachedFunction.CacheEnabled {
		cache.CacheAutoFunctionResult(cachedFunction.ID, result)
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"function": functionName,
		"result":   result,
		"cached":   false,
		"execution_context": map[string]interface{}{
			"table_name": cachedFunction.TableName,
			"db_type":    cachedFunction.DBType,
			"parameters": requestData,
		},
	})
}

// handleGetMemoryStructure returns the complete memory structure for debugging
func (s *Server) handleGetMemoryStructure(w http.ResponseWriter, r *http.Request) {
	cache := s.dbManager.GetCache()
	structure := cache.GetMemoryStructure()
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"memory_structure": structure,
	})
}

// handleGetCachedFlows returns all cached flows with their structure
func (s *Server) handleGetCachedFlows(w http.ResponseWriter, r *http.Request) {
	cache := s.dbManager.GetCache()
	
	flows := make([]map[string]interface{}, len(cache.AllFlows))
	for i, flow := range cache.AllFlows {
		flowData := map[string]interface{}{
			"flow_id":       flow.FlowID,
			"flow_name":     flow.FlowName,
			"flow_desc":     flow.FlowDesc,
			"flow_type":     flow.FlowType,
			"endpoint_path": flow.EndpointPath,
			"http_method":   flow.HTTPMethod,
			"is_active":     flow.IsActive,
			"steps_count":   len(flow.Steps),
			"steps":         flow.Steps,
		}
		flows[i] = flowData
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"flows":   flows,
		"count":   len(flows),
	})
}

// handleGetRuleGroups returns all cached rule groups
func (s *Server) handleGetRuleGroups(w http.ResponseWriter, r *http.Request) {
	cache := s.dbManager.GetCache()
	
	ruleGroups := make([]map[string]interface{}, 0)
	for _, rg := range cache.RuleGroupsByID {
		rgData := map[string]interface{}{
			"group_id":       rg.GroupID,
			"group_name":     rg.GroupName,
			"group_desc":     rg.GroupDesc,
			"group_priority": rg.GroupPriority,
			"is_active":      rg.IsActive,
			"rules_count":    len(rg.Rules),
			"rules":          rg.Rules,
		}
		ruleGroups = append(ruleGroups, rgData)
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":     true,
		"rule_groups": ruleGroups,
		"count":       len(ruleGroups),
	})
}

// handleGetRules returns all cached rules
func (s *Server) handleGetRules(w http.ResponseWriter, r *http.Request) {
	cache := s.dbManager.GetCache()
	
	rules := make([]map[string]interface{}, 0)
	for _, rule := range cache.RulesByID {
		ruleData := map[string]interface{}{
			"rule_id":         rule.RuleID,
			"rule_name":       rule.RuleName,
			"rule_desc":       rule.RuleDesc,
			"rule_expression": rule.RuleExpression,
			"rule_priority":   rule.RulePriority,
			"rule_type":       rule.RuleType,
			"rule_group_id":   rule.RuleGroupID,
			"is_active":       rule.IsActive,
		}
		rules = append(rules, ruleData)
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"rules":   rules,
		"count":   len(rules),
	})
}

// handleGetBaseFunctions returns all cached base functions
func (s *Server) handleGetBaseFunctions(w http.ResponseWriter, r *http.Request) {
	cache := s.dbManager.GetCache()
	
	functions := make([]map[string]interface{}, len(cache.AllBaseFunctions))
	for i, fn := range cache.AllBaseFunctions {
		fnData := map[string]interface{}{
			"function_id":   fn.FunctionID,
			"function_name": fn.FunctionName,
			"description":   fn.Description,
			"code":          fn.Code,
			"return_type":   fn.ReturnType,
			"is_active":     fn.IsActive,
		}
		functions[i] = fnData
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":   true,
		"functions": functions,
		"count":     len(functions),
	})
}

// handleReloadLoyaltyAPI reloads all loyalty API data
func (s *Server) handleReloadLoyaltyAPI(w http.ResponseWriter, r *http.Request) {
	if s.forgeLoader == nil {
		http.Error(w, "Forge loader not initialized", http.StatusServiceUnavailable)
		return
	}
	
	// Reload both auto-function and flow data
	if err := loadAutoFunctionData(s.dbManager, s.forgeLoader); err != nil {
		http.Error(w, fmt.Sprintf("Failed to reload auto-functions: %v", err), http.StatusInternalServerError)
		return
	}
	
	if err := loadFlowData(s.dbManager, s.forgeLoader); err != nil {
		http.Error(w, fmt.Sprintf("Failed to reload flow data: %v", err), http.StatusInternalServerError)
		return
	}
	
	cache := s.dbManager.GetCache()
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Loyalty API data reloaded successfully",
		"summary": map[string]interface{}{
			"flows":          len(cache.AllFlows),
			"rule_groups":    len(cache.RuleGroupsByID),
			"rules":          len(cache.RulesByID),
			"api_endpoints":  len(cache.AllAPIEndpoints),
			"base_functions": len(cache.AllBaseFunctions),
			"auto_functions": len(cache.AllAutoFunctions),
			"tables":         len(cache.TablesByID),
		},
	})
}

// handleGetLoyaltyEndpoints returns all loyalty API endpoints with their flows
func (s *Server) handleGetLoyaltyEndpoints(w http.ResponseWriter, r *http.Request) {
	cache := s.dbManager.GetCache()
	
	// Filter for loyalty endpoints
	loyaltyEndpoints := make([]map[string]interface{}, 0)
	for _, endpoint := range cache.AllAPIEndpoints {
		if len(endpoint.EndpointPath) > 0 && 
		   (endpoint.EndpointPath[:10] == "/ecommerce" || 
		    endpoint.EndpointPath[:8] == "/loyalty") {
			
			// Get associated flow
			var flowData map[string]interface{}
			if flow := cache.GetFlowByEndpoint(endpoint.HTTPMethod, endpoint.EndpointPath); flow != nil {
				flowData = map[string]interface{}{
					"flow_id":    flow.FlowID,
					"flow_name":  flow.FlowName,
					"steps_count": len(flow.Steps),
				}
				
				// Add rule details
				for _, step := range flow.Steps {
					if step.RuleGroupID != nil {
						rules := cache.GetRulesForGroup(*step.RuleGroupID)
						flowData["rules_count"] = len(rules)
						break
					}
				}
			}
			
			endpointData := map[string]interface{}{
				"endpoint_id":   endpoint.EndpointID,
				"endpoint_path": endpoint.EndpointPath,
				"http_method":   endpoint.HTTPMethod,
				"class_name":    endpoint.ClassName,
				"operation_id":  endpoint.OperationID,
				"description":   endpoint.Description,
				"flow":          flowData,
			}
			
			loyaltyEndpoints = append(loyaltyEndpoints, endpointData)
		}
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":   true,
		"endpoints": loyaltyEndpoints,
		"count":     len(loyaltyEndpoints),
	})
}