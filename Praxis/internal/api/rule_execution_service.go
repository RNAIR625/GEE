package api
/*

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
	"github.com/GEE/Praxis/internal/runtime"
)

// RuleExecutionService provides HTTP endpoints for rule execution
type RuleExecutionService struct {
	db       *sql.DB
	executor *runtime.EnhancedFlowExecutor
}

// NewRuleExecutionService creates a new rule execution service
func NewRuleExecutionService(db *sql.DB) *RuleExecutionService {
	return &RuleExecutionService{
		db:       db,
		executor: runtime.NewEnhancedFlowExecutor(db),
	}
}

// RegisterRoutes registers HTTP routes for rule execution
func (res *RuleExecutionService) RegisterRoutes(router *mux.Router) {
	// Rule execution endpoints
	router.HandleFunc("/api/rules/{id}/execute", res.executeRule).Methods("POST")
	router.HandleFunc("/api/rule-groups/{id}/execute", res.executeRuleGroup).Methods("POST")
	router.HandleFunc("/api/flows/{id}/execute", res.executeFlow).Methods("POST")
	
	// Testing and debugging endpoints
	router.HandleFunc("/api/rules/{id}/test", res.testRule).Methods("POST")
	router.HandleFunc("/api/functions/{name}/test", res.testFunction).Methods("POST")
	router.HandleFunc("/api/lookup/test", res.testLookup).Methods("POST")
	
	// GEE variables endpoints
	router.HandleFunc("/api/gee-variables", res.getGEEVariables).Methods("GET")
	router.HandleFunc("/api/gee-variables/{name}", res.getGEEVariable).Methods("GET")
	router.HandleFunc("/api/gee-variables/{name}", res.setGEEVariable).Methods("PUT")
}

// executeRule executes a single rule
func (res *RuleExecutionService) executeRule(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	ruleID, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid rule ID", http.StatusBadRequest)
		return
	}
	
	// Parse request body for input data
	var requestData struct {
		InputData map[string]interface{} `json:"input_data"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	log.Printf("Executing rule %d with input data", ruleID)
	
	// Create execution context
	context := &runtime.ExecutionContext{
		Input:     requestData.InputData,
		Variables: make(map[string]interface{}),
		Output:    make(map[string]interface{}),
		Errors:    make([]string, 0),
	}
	
	// Create rule executor
	ruleExecutor := runtime.NewRuleExecutor(res.db, context)
	
	// Load and execute rule
	rule, err := res.loadRule(ruleID)
	if err != nil {
		log.Printf("Failed to load rule %d: %v", ruleID, err)
		http.Error(w, fmt.Sprintf("Failed to load rule: %v", err), http.StatusInternalServerError)
		return
	}
	
	result, err := ruleExecutor.ExecuteRule(*rule)
	if err != nil {
		log.Printf("Rule execution failed: %v", err)
		http.Error(w, fmt.Sprintf("Rule execution failed: %v", err), http.StatusInternalServerError)
		return
	}
	
	// Add GEE variables to response
	response := map[string]interface{}{
		"rule_result":   result,
		"gee_variables": ruleExecutor.GetGEEVariables(),
		"execution_context": map[string]interface{}{
			"input":     context.Input,
			"variables": context.Variables,
			"output":    context.Output,
			"errors":    context.Errors,
		},
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// executeRuleGroup executes a rule group
func (res *RuleExecutionService) executeRuleGroup(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	groupID, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid rule group ID", http.StatusBadRequest)
		return
	}
	
	var requestData struct {
		InputData map[string]interface{} `json:"input_data"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	log.Printf("Executing rule group %d", groupID)
	
	// Create a mock flow definition for rule group execution
	flowDef := runtime.FlowDefinition{
		FlowID:     -1,
		FlowName:   fmt.Sprintf("RuleGroup_%d", groupID),
		StartNodes: []string{"rule_group_node"},
		Nodes: map[string]runtime.NodeDefinition{
			"rule_group_node": {
				ID:          "rule_group_node",
				Type:        "rule_group",
				ReferenceID: groupID,
			},
		},
	}
	
	result, err := res.executor.ExecuteFlowWithRules(flowDef, requestData.InputData)
	if err != nil {
		log.Printf("Rule group execution failed: %v", err)
		http.Error(w, fmt.Sprintf("Rule group execution failed: %v", err), http.StatusInternalServerError)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

// executeFlow executes a complete flow with rules
func (res *RuleExecutionService) executeFlow(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	flowID, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid flow ID", http.StatusBadRequest)
		return
	}
	
	var requestData struct {
		InputData map[string]interface{} `json:"input_data"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	log.Printf("Executing flow %d", flowID)
	
	// Load flow definition (simplified - would need proper flow loading)
	flowDef, err := res.loadFlowDefinition(flowID)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to load flow: %v", err), http.StatusInternalServerError)
		return
	}
	
	result, err := res.executor.ExecuteFlowWithRules(*flowDef, requestData.InputData)
	if err != nil {
		log.Printf("Flow execution failed: %v", err)
		http.Error(w, fmt.Sprintf("Flow execution failed: %v", err), http.StatusInternalServerError)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

// testRule tests a rule with sample data
func (res *RuleExecutionService) testRule(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	ruleID, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid rule ID", http.StatusBadRequest)
		return
	}
	
	var testData struct {
		TestInput map[string]interface{} `json:"test_input"`
		Debug     bool                   `json:"debug"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&testData); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	log.Printf("Testing rule %d with debug mode: %v", ruleID, testData.Debug)
	
	// Execute rule in test mode
	context := &runtime.ExecutionContext{
		Input:     testData.TestInput,
		Variables: make(map[string]interface{}),
		Output:    make(map[string]interface{}),
		Errors:    make([]string, 0),
	}
	
	ruleExecutor := runtime.NewRuleExecutor(res.db, context)
	
	rule, err := res.loadRule(ruleID)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to load rule: %v", err), http.StatusInternalServerError)
		return
	}
	
	result, err := ruleExecutor.ExecuteRule(*rule)
	if err != nil {
		log.Printf("Rule test failed: %v", err)
	}
	
	// Enhanced response for testing
	response := map[string]interface{}{
		"test_result": map[string]interface{}{
			"success":       err == nil,
			"rule_result":   result,
			"error":         map[bool]interface{}{true: err.Error(), false: nil}[err != nil],
			"gee_variables": ruleExecutor.GetGEEVariables(),
		},
		"debug_info": map[string]interface{}{
			"rule_definition":    rule,
			"execution_context":  context,
			"conditions_count":   len(rule.Conditions),
			"actions_count":      len(rule.Actions),
		},
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// testFunction tests a single function
func (res *RuleExecutionService) testFunction(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	functionName := vars["name"]
	
	var testData struct {
		Parameters []interface{} `json:"parameters"`
		Context    map[string]interface{} `json:"context"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&testData); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	log.Printf("Testing function %s with %d parameters", functionName, len(testData.Parameters))
	
	// Create test context
	context := &runtime.ExecutionContext{
		Input:     testData.Context,
		Variables: make(map[string]interface{}),
		Output:    make(map[string]interface{}),
		Errors:    make([]string, 0),
	}
	
	ruleExecutor := runtime.NewRuleExecutor(res.db, context)
	
	// Execute function
	result, err := ruleExecutor.ExecuteFunction(functionName, testData.Parameters)
	
	response := map[string]interface{}{
		"function_name": functionName,
		"parameters":    testData.Parameters,
		"result":        result,
		"success":       err == nil,
		"error":         map[bool]interface{}{true: err.Error(), false: nil}[err != nil],
		"gee_variables": ruleExecutor.GetGEEVariables(),
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// testLookup tests table lookup functionality
func (res *RuleExecutionService) testLookup(w http.ResponseWriter, r *http.Request) {
	var testData struct {
		Expression string                 `json:"expression"`
		Context    map[string]interface{} `json:"context"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&testData); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	log.Printf("Testing lookup expression: %s", testData.Expression)
	
	context := &runtime.ExecutionContext{
		Input:     testData.Context,
		Variables: make(map[string]interface{}),
		Output:    make(map[string]interface{}),
		Errors:    make([]string, 0),
	}
	
	ruleExecutor := runtime.NewRuleExecutor(res.db, context)
	
	// Execute lookup
	result, err := ruleExecutor.ExecuteTableLookup(testData.Expression)
	
	response := map[string]interface{}{
		"expression": testData.Expression,
		"result":     result,
		"success":    err == nil,
		"error":      map[bool]interface{}{true: err.Error(), false: nil}[err != nil],
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// getGEEVariables returns all GEE variables
func (res *RuleExecutionService) getGEEVariables(w http.ResponseWriter, r *http.Request) {
	// This would need access to a persistent GEE variables store
	// For now, return empty response
	response := map[string]interface{}{
		"variables": make(map[string]interface{}),
		"message":   "GEE variables are session-specific and reset per execution",
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// getGEEVariable returns a specific GEE variable
func (res *RuleExecutionService) getGEEVariable(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	varName := vars["name"]
	
	// Placeholder response
	response := map[string]interface{}{
		"variable_name": varName,
		"value":         nil,
		"message":       "GEE variables are session-specific and reset per execution",
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// setGEEVariable sets a GEE variable value
func (res *RuleExecutionService) setGEEVariable(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	varName := vars["name"]
	
	var requestData struct {
		Value interface{} `json:"value"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	// Placeholder response
	response := map[string]interface{}{
		"variable_name": varName,
		"value":         requestData.Value,
		"success":       true,
		"message":       "Variable would be set in execution context",
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Helper methods

// loadRule loads a rule from the database (simplified version)
func (res *RuleExecutionService) loadRule(ruleID int) (*runtime.EnhancedRule, error) {
	// This mirrors the logic from enhanced_flow_executor.go
	ruleQuery := `
		SELECT r.RULE_ID, r.RULE_NAME, r.RULE_TYPE, r.DESCRIPTION, r.GFC_ID
		FROM GEE_RULES r
		WHERE r.RULE_ID = ?
	`
	
	var rule runtime.EnhancedRule
	err := res.db.QueryRow(ruleQuery, ruleID).Scan(
		&rule.RuleID, &rule.RuleName, &rule.RuleType, &rule.Description, &rule.ClassID,
	)
	if err != nil {
		return nil, err
	}
	
	// Load rule lines and parameters
	// Implementation would be similar to enhanced_flow_executor.go
	// For brevity, returning basic rule structure
	
	return &rule, nil
}

// loadFlowDefinition loads a flow definition (placeholder)
func (res *RuleExecutionService) loadFlowDefinition(flowID int) (*runtime.FlowDefinition, error) {
	// Placeholder implementation
	return &runtime.FlowDefinition{
		FlowID:   flowID,
		FlowName: fmt.Sprintf("Flow_%d", flowID),
	}, nil
}

*/