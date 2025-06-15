package main

import (
	"encoding/json"
	"fmt"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"time"
)

// ActionExecutor manages action execution and results
type ActionExecutor struct {
	data    map[string]interface{}
	results []ActionResult
}

// ActionResult represents the result of an action execution
type ActionResult struct {
	Type            string      `json:"type"`
	Success         bool        `json:"success"`
	Result          interface{} `json:"result,omitempty"`
	Error           string      `json:"error,omitempty"`
	ExecutionTimeMs int64       `json:"execution_time_ms"`
	ActionID        string      `json:"action_id,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

// Action represents an action to be executed (from previous schema)
type Action struct {
	ID       string                 `json:"id,omitempty"`
	Type     string                 `json:"type"`
	Priority int                    `json:"priority,omitempty"`
	Target   string                 `json:"target,omitempty"`
	Params   map[string]interface{} `json:"params,omitempty"`
}

// ExternalCallRequest represents a prepared external service call
type ExternalCallRequest struct {
	URL     string            `json:"url"`
	Method  string            `json:"method"`
	Headers map[string]string `json:"headers"`
	Body    interface{}       `json:"body,omitempty"`
	Timeout int               `json:"timeout_seconds"`
}

// NewActionExecutor creates a new action executor instance
func NewActionExecutor(data map[string]interface{}) *ActionExecutor {
	if data == nil {
		data = make(map[string]interface{})
	}
	
	return &ActionExecutor{
		data:    data,
		results: make([]ActionResult, 0),
	}
}

// ExecuteActions executes a list of actions in priority order
func (ae *ActionExecutor) ExecuteActions(actions []Action) ([]ActionResult, error) {
	if len(actions) == 0 {
		return []ActionResult{}, nil
	}
	
	// Sort actions by priority (lower number = higher priority)
	sortedActions := make([]Action, len(actions))
	copy(sortedActions, actions)
	sort.Slice(sortedActions, func(i, j int) bool {
		return sortedActions[i].Priority < sortedActions[j].Priority
	})
	
	results := make([]ActionResult, 0, len(actions))
	
	// Execute each action
	for _, action := range sortedActions {
		start := time.Now()
		
		var result ActionResult
		
		switch action.Type {
		case "set":
			result = ae.ExecuteSetAction(action)
		case "get":
			result = ae.ExecuteGetAction(action)
		case "delete":
			result = ae.ExecuteDeleteAction(action)
		case "transform":
			result = ae.ExecuteTransformAction(action)
		case "validate":
			result = ae.ExecuteValidateAction(action)
		case "log":
			result = ae.ExecuteLogAction(action)
		case "webhook", "email", "external_service":
			result = ae.PrepareExternalCall(action)
		case "conditional":
			result = ae.ExecuteConditionalAction(action)
		case "aggregate":
			result = ae.ExecuteAggregateAction(action)
		default:
			result = ActionResult{
				Type:            action.Type,
				Success:         false,
				Error:           fmt.Sprintf("unsupported action type: %s", action.Type),
				ExecutionTimeMs: time.Since(start).Milliseconds(),
				ActionID:        action.ID,
			}
		}
		
		// Set execution time if not already set
		if result.ExecutionTimeMs == 0 {
			result.ExecutionTimeMs = time.Since(start).Milliseconds()
		}
		
		// Set action ID if not already set
		if result.ActionID == "" {
			result.ActionID = action.ID
		}
		
		results = append(results, result)
		ae.results = append(ae.results, result)
		
		// Stop execution on critical errors if specified
		if !result.Success && ae.shouldStopOnError(action) {
			return results, fmt.Errorf("critical action failed: %s", result.Error)
		}
	}
	
	return results, nil
}

// ExecuteSetAction executes a "set" action to modify data fields
func (ae *ActionExecutor) ExecuteSetAction(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     "set",
		ActionID: action.ID,
		Metadata: make(map[string]interface{}),
	}
	
	// Validate required parameters
	if action.Target == "" {
		result.Success = false
		result.Error = "set action requires target field path"
		return result
	}
	
	value, exists := action.Params["value"]
	if !exists {
		result.Success = false
		result.Error = "set action requires 'value' parameter"
		return result
	}
	
	// Handle different set operation modes
	mode := "replace" // default mode
	if modeParam, exists := action.Params["mode"]; exists {
		if modeStr, ok := modeParam.(string); ok {
			mode = modeStr
		}
	}
	
	// Execute the set operation
	oldValue, err := ae.getFieldValue(action.Target)
	if err != nil && mode != "create" {
		result.Success = false
		result.Error = fmt.Sprintf("failed to get current value: %v", err)
		return result
	}
	
	var newValue interface{}
	switch mode {
	case "replace", "create":
		newValue = value
	case "append":
		newValue, err = ae.appendValue(oldValue, value)
		if err != nil {
			result.Success = false
			result.Error = fmt.Sprintf("failed to append value: %v", err)
			return result
		}
	case "increment":
		newValue, err = ae.incrementValue(oldValue, value)
		if err != nil {
			result.Success = false
			result.Error = fmt.Sprintf("failed to increment value: %v", err)
			return result
		}
	default:
		result.Success = false
		result.Error = fmt.Sprintf("unsupported set mode: %s", mode)
		return result
	}
	
	// Set the new value
	if err := ae.setFieldValue(action.Target, newValue); err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("failed to set field value: %v", err)
		return result
	}
	
	result.Success = true
	result.Result = map[string]interface{}{
		"field":     action.Target,
		"old_value": oldValue,
		"new_value": newValue,
		"mode":      mode,
	}
	result.Metadata["old_value"] = oldValue
	result.Metadata["new_value"] = newValue
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// ExecuteGetAction retrieves a field value
func (ae *ActionExecutor) ExecuteGetAction(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     "get",
		ActionID: action.ID,
	}
	
	if action.Target == "" {
		result.Success = false
		result.Error = "get action requires target field path"
		return result
	}
	
	value, err := ae.getFieldValue(action.Target)
	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("failed to get field value: %v", err)
		return result
	}
	
	result.Success = true
	result.Result = map[string]interface{}{
		"field": action.Target,
		"value": value,
	}
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// ExecuteDeleteAction removes a field
func (ae *ActionExecutor) ExecuteDeleteAction(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     "delete",
		ActionID: action.ID,
	}
	
	if action.Target == "" {
		result.Success = false
		result.Error = "delete action requires target field path"
		return result
	}
	
	oldValue, err := ae.getFieldValue(action.Target)
	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("field not found: %v", err)
		return result
	}
	
	if err := ae.deleteField(action.Target); err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("failed to delete field: %v", err)
		return result
	}
	
	result.Success = true
	result.Result = map[string]interface{}{
		"field":     action.Target,
		"old_value": oldValue,
	}
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// ExecuteTransformAction applies a transformation to a field
func (ae *ActionExecutor) ExecuteTransformAction(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     "transform",
		ActionID: action.ID,
	}
	
	if action.Target == "" {
		result.Success = false
		result.Error = "transform action requires target field path"
		return result
	}
	
	transformType, exists := action.Params["type"]
	if !exists {
		result.Success = false
		result.Error = "transform action requires 'type' parameter"
		return result
	}
	
	currentValue, err := ae.getFieldValue(action.Target)
	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("failed to get current value: %v", err)
		return result
	}
	
	transformedValue, err := ae.applyTransformation(currentValue, transformType, action.Params)
	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("transformation failed: %v", err)
		return result
	}
	
	if err := ae.setFieldValue(action.Target, transformedValue); err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("failed to set transformed value: %v", err)
		return result
	}
	
	result.Success = true
	result.Result = map[string]interface{}{
		"field":            action.Target,
		"old_value":        currentValue,
		"new_value":        transformedValue,
		"transformation":   transformType,
	}
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// ExecuteValidateAction validates field values
func (ae *ActionExecutor) ExecuteValidateAction(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     "validate",
		ActionID: action.ID,
	}
	
	if action.Target == "" {
		result.Success = false
		result.Error = "validate action requires target field path"
		return result
	}
	
	value, err := ae.getFieldValue(action.Target)
	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("failed to get field value: %v", err)
		return result
	}
	
	validationRules := action.Params["rules"]
	isValid, validationErrors := ae.validateValue(value, validationRules)
	
	result.Success = true
	result.Result = map[string]interface{}{
		"field":   action.Target,
		"value":   value,
		"valid":   isValid,
		"errors":  validationErrors,
	}
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// ExecuteLogAction logs information
func (ae *ActionExecutor) ExecuteLogAction(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     "log",
		ActionID: action.ID,
	}
	
	message := "No message specified"
	if msg, exists := action.Params["message"]; exists {
		if msgStr, ok := msg.(string); ok {
			message = msgStr
		}
	}
	
	level := "info"
	if lvl, exists := action.Params["level"]; exists {
		if lvlStr, ok := lvl.(string); ok {
			level = lvlStr
		}
	}
	
	// In a real implementation, this would use a proper logging system
	logEntry := map[string]interface{}{
		"timestamp": time.Now().UTC(),
		"level":     level,
		"message":   message,
		"data":      action.Params["data"],
	}
	
	result.Success = true
	result.Result = logEntry
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// ExecuteConditionalAction executes actions based on conditions
func (ae *ActionExecutor) ExecuteConditionalAction(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     "conditional",
		ActionID: action.ID,
	}
	
	// This would integrate with the expression evaluator
	// For now, we'll simulate the logic
	condition := action.Params["condition"]
	thenActions := action.Params["then"]
	elseActions := action.Params["else"]
	
	// Simulate condition evaluation (would use actual evaluator)
	conditionMet := ae.evaluateCondition(condition)
	
	var actionsToExecute interface{}
	if conditionMet {
		actionsToExecute = thenActions
	} else {
		actionsToExecute = elseActions
	}
	
	result.Success = true
	result.Result = map[string]interface{}{
		"condition_met": conditionMet,
		"actions_type":  map[bool]string{true: "then", false: "else"}[conditionMet],
	}
	result.Metadata = map[string]interface{}{
		"actions_to_execute": actionsToExecute,
	}
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// ExecuteAggregateAction aggregates values from multiple fields
func (ae *ActionExecutor) ExecuteAggregateAction(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     "aggregate",
		ActionID: action.ID,
	}
	
	fields, exists := action.Params["fields"]
	if !exists {
		result.Success = false
		result.Error = "aggregate action requires 'fields' parameter"
		return result
	}
	
	operation := "sum" // default
	if op, exists := action.Params["operation"]; exists {
		if opStr, ok := op.(string); ok {
			operation = opStr
		}
	}
	
	fieldList, ok := fields.([]interface{})
	if !ok {
		result.Success = false
		result.Error = "fields parameter must be an array"
		return result
	}
	
	values := make([]interface{}, 0, len(fieldList))
	for _, field := range fieldList {
		if fieldStr, ok := field.(string); ok {
			if value, err := ae.getFieldValue(fieldStr); err == nil {
				values = append(values, value)
			}
		}
	}
	
	aggregateValue, err := ae.performAggregation(values, operation)
	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("aggregation failed: %v", err)
		return result
	}
	
	// Store result if target is specified
	if action.Target != "" {
		ae.setFieldValue(action.Target, aggregateValue)
	}
	
	result.Success = true
	result.Result = map[string]interface{}{
		"operation": operation,
		"fields":    fieldList,
		"values":    values,
		"result":    aggregateValue,
	}
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// PrepareExternalCall prepares external service calls (no actual HTTP calls)
func (ae *ActionExecutor) PrepareExternalCall(action Action) ActionResult {
	start := time.Now()
	
	result := ActionResult{
		Type:     action.Type,
		ActionID: action.ID,
		Metadata: make(map[string]interface{}),
	}
	
	var request ExternalCallRequest
	
	switch action.Type {
	case "webhook":
		request = ae.prepareWebhookCall(action)
	case "email":
		request = ae.prepareEmailCall(action)
	case "external_service":
		request = ae.prepareExternalServiceCall(action)
	default:
		result.Success = false
		result.Error = fmt.Sprintf("unsupported external call type: %s", action.Type)
		return result
	}
	
	// Validate the prepared request
	if err := ae.validateExternalRequest(request); err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("invalid external request: %v", err)
		return result
	}
	
	result.Success = true
	result.Result = request
	result.Metadata["prepared_at"] = time.Now().UTC()
	result.Metadata["ready_for_execution"] = true
	result.ExecutionTimeMs = time.Since(start).Milliseconds()
	
	return result
}

// Helper methods for field manipulation
func (ae *ActionExecutor) getFieldValue(path string) (interface{}, error) {
	return ae.resolveFieldPath(ae.data, path)
}

func (ae *ActionExecutor) setFieldValue(path string, value interface{}) error {
	return ae.setNestedField(ae.data, path, value)
}

func (ae *ActionExecutor) deleteField(path string) error {
	return ae.deleteNestedField(ae.data, path)
}

func (ae *ActionExecutor) resolveFieldPath(data map[string]interface{}, path string) (interface{}, error) {
	parts := strings.Split(path, ".")
	current := data
	
	for i, part := range parts {
		if i == len(parts)-1 {
			// Last part - return the value
			if val, exists := current[part]; exists {
				return val, nil
			}
			return nil, fmt.Errorf("field not found: %s", path)
		}
		
		// Navigate deeper
		if val, exists := current[part]; exists {
			if nextMap, ok := val.(map[string]interface{}); ok {
				current = nextMap
			} else {
				return nil, fmt.Errorf("cannot navigate through non-object field: %s", strings.Join(parts[:i+1], "."))
			}
		} else {
			return nil, fmt.Errorf("field not found: %s", strings.Join(parts[:i+1], "."))
		}
	}
	
	return nil, fmt.Errorf("empty field path")
}

func (ae *ActionExecutor) setNestedField(data map[string]interface{}, path string, value interface{}) error {
	parts := strings.Split(path, ".")
	current := data
	
	// Navigate to the parent of the target field
	for i, part := range parts[:len(parts)-1] {
		if val, exists := current[part]; exists {
			if nextMap, ok := val.(map[string]interface{}); ok {
				current = nextMap
			} else {
				return fmt.Errorf("cannot set field through non-object: %s", strings.Join(parts[:i+1], "."))
			}
		} else {
			// Create intermediate objects
			newMap := make(map[string]interface{})
			current[part] = newMap
			current = newMap
		}
	}
	
	// Set the final value
	finalPart := parts[len(parts)-1]
	current[finalPart] = value
	
	return nil
}

func (ae *ActionExecutor) deleteNestedField(data map[string]interface{}, path string) error {
	parts := strings.Split(path, ".")
	current := data
	
	// Navigate to the parent of the target field
	for _, part := range parts[:len(parts)-1] {
		if val, exists := current[part]; exists {
			if nextMap, ok := val.(map[string]interface{}); ok {
				current = nextMap
			} else {
				return fmt.Errorf("cannot delete field through non-object: %s", part)
			}
		} else {
			return fmt.Errorf("field not found: %s", part)
		}
	}
	
	// Delete the final field
	finalPart := parts[len(parts)-1]
	if _, exists := current[finalPart]; !exists {
		return fmt.Errorf("field not found: %s", path)
	}
	
	delete(current, finalPart)
	return nil
}

// Helper methods for value operations
func (ae *ActionExecutor) appendValue(current, toAppend interface{}) (interface{}, error) {
	switch curr := current.(type) {
	case []interface{}:
		return append(curr, toAppend), nil
	case string:
		if appendStr, ok := toAppend.(string); ok {
			return curr + appendStr, nil
		}
		return nil, fmt.Errorf("cannot append non-string to string")
	default:
		return nil, fmt.Errorf("cannot append to type %T", current)
	}
}

func (ae *ActionExecutor) incrementValue(current, increment interface{}) (interface{}, error) {
	currentNum, err := ae.toNumber(current)
	if err != nil {
		return nil, fmt.Errorf("current value is not numeric: %w", err)
	}
	
	incrementNum, err := ae.toNumber(increment)
	if err != nil {
		return nil, fmt.Errorf("increment value is not numeric: %w", err)
	}
	
	return currentNum + incrementNum, nil
}

func (ae *ActionExecutor) toNumber(value interface{}) (float64, error) {
	switch v := value.(type) {
	case float64:
		return v, nil
	case float32:
		return float64(v), nil
	case int:
		return float64(v), nil
	case int64:
		return float64(v), nil
	case string:
		return strconv.ParseFloat(v, 64)
	default:
		return 0, fmt.Errorf("cannot convert %T to number", value)
	}
}

// Helper methods for transformations
func (ae *ActionExecutor) applyTransformation(value interface{}, transformType interface{}, params map[string]interface{}) (interface{}, error) {
	transformStr, ok := transformType.(string)
	if !ok {
		return nil, fmt.Errorf("transform type must be string")
	}
	
	switch transformStr {
	case "uppercase":
		if str, ok := value.(string); ok {
			return strings.ToUpper(str), nil
		}
		return nil, fmt.Errorf("uppercase transform requires string value")
	case "lowercase":
		if str, ok := value.(string); ok {
			return strings.ToLower(str), nil
		}
		return nil, fmt.Errorf("lowercase transform requires string value")
	case "multiply":
		multiplier := params["factor"]
		num, err := ae.toNumber(value)
		if err != nil {
			return nil, err
		}
		factor, err := ae.toNumber(multiplier)
		if err != nil {
			return nil, fmt.Errorf("invalid multiplier: %w", err)
		}
		return num * factor, nil
	case "round":
		num, err := ae.toNumber(value)
		if err != nil {
			return nil, err
		}
		return float64(int(num + 0.5)), nil
	default:
		return nil, fmt.Errorf("unsupported transformation: %s", transformStr)
	}
}

// Helper methods for validation
func (ae *ActionExecutor) validateValue(value, rules interface{}) (bool, []string) {
	// Simplified validation - in real implementation would be more robust
	errors := make([]string, 0)
	
	if rules == nil {
		return true, errors
	}
	
	rulesMap, ok := rules.(map[string]interface{})
	if !ok {
		return false, []string{"invalid validation rules format"}
	}
	
	// Check required
	if required, exists := rulesMap["required"]; exists {
		if req, ok := required.(bool); ok && req {
			if value == nil || (reflect.ValueOf(value).Kind() == reflect.String && value.(string) == "") {
				errors = append(errors, "field is required")
			}
		}
	}
	
	// Check type
	if expectedType, exists := rulesMap["type"]; exists {
		if typeStr, ok := expectedType.(string); ok {
			if !ae.checkType(value, typeStr) {
				errors = append(errors, fmt.Sprintf("expected type %s", typeStr))
			}
		}
	}
	
	return len(errors) == 0, errors
}

func (ae *ActionExecutor) checkType(value interface{}, expectedType string) bool {
	switch expectedType {
	case "string":
		_, ok := value.(string)
		return ok
	case "number":
		_, err := ae.toNumber(value)
		return err == nil
	case "boolean":
		_, ok := value.(bool)
		return ok
	case "array":
		_, ok := value.([]interface{})
		return ok
	case "object":
		_, ok := value.(map[string]interface{})
		return ok
	default:
		return true
	}
}

// Helper methods for external calls
func (ae *ActionExecutor) prepareWebhookCall(action Action) ExternalCallRequest {
	method := "POST"
	if m, exists := action.Params["method"]; exists {
		if methodStr, ok := m.(string); ok {
			method = methodStr
		}
	}
	
	headers := make(map[string]string)
	headers["Content-Type"] = "application/json"
	if h, exists := action.Params["headers"]; exists {
		if headerMap, ok := h.(map[string]interface{}); ok {
			for k, v := range headerMap {
				if vStr, ok := v.(string); ok {
					headers[k] = vStr
				}
			}
		}
	}
	
	timeout := 30 // default timeout
	if t, exists := action.Params["timeout"]; exists {
		if timeoutNum, err := ae.toNumber(t); err == nil {
			timeout = int(timeoutNum)
		}
	}
	
	return ExternalCallRequest{
		URL:     action.Target,
		Method:  method,
		Headers: headers,
		Body:    action.Params["body"],
		Timeout: timeout,
	}
}

func (ae *ActionExecutor) prepareEmailCall(action Action) ExternalCallRequest {
	body := map[string]interface{}{
		"to":      action.Target,
		"subject": action.Params["subject"],
		"body":    action.Params["body"],
		"from":    action.Params["from"],
	}
	
	return ExternalCallRequest{
		URL:     "https://email-service/send", // would be configurable
		Method:  "POST",
		Headers: map[string]string{"Content-Type": "application/json"},
		Body:    body,
		Timeout: 30,
	}
}

func (ae *ActionExecutor) prepareExternalServiceCall(action Action) ExternalCallRequest {
	// action.Target would be the service name
	// This would look up service configuration from the ruleset
	
	method := "POST"
	if m, exists := action.Params["method"]; exists {
		if methodStr, ok := m.(string); ok {
			method = methodStr
		}
	}
	
	return ExternalCallRequest{
		URL:     fmt.Sprintf("https://external-service/%s", action.Target),
		Method:  method,
		Headers: map[string]string{"Content-Type": "application/json"},
		Body:    action.Params,
		Timeout: 60,
	}
}

func (ae *ActionExecutor) validateExternalRequest(request ExternalCallRequest) error {
	if request.URL == "" {
		return fmt.Errorf("URL is required")
	}
	
	if request.Method == "" {
		return fmt.Errorf("HTTP method is required")
	}
	
	if request.Timeout <= 0 {
		return fmt.Errorf("timeout must be positive")
	}
	
	return nil
}

// Helper methods
func (ae *ActionExecutor) shouldStopOnError(action Action) bool {
	if critical, exists := action.Params["critical"]; exists {
		if criticalBool, ok := critical.(bool); ok {
			return criticalBool
		}
	}
	return false
}

func (ae *ActionExecutor) evaluateCondition(condition interface{}) bool {
	// Simplified condition evaluation
	// In real implementation, this would use the expression evaluator
	return true
}

func (ae *ActionExecutor) performAggregation(values []interface{}, operation string) (interface{}, error) {
	if len(values) == 0 {
		return nil, fmt.Errorf("no values to aggregate")
	}
	
	switch operation {
	case "sum":
		sum := 0.0
		for _, val := range values {
			if num, err := ae.toNumber(val); err == nil {
				sum += num
			}
		}
		return sum, nil
	case "count":
		return len(values), nil
	case "avg":
		sum := 0.0
		count := 0
		for _, val := range values {
			if num, err := ae.toNumber(val); err == nil {
				sum += num
				count++
			}
		}
		if count == 0 {
			return nil, fmt.Errorf("no numeric values to average")
		}
		return sum / float64(count), nil
	case "max":
		var max float64
		hasValue := false
		for _, val := range values {
			if num, err := ae.toNumber(val); err == nil {
				if !hasValue || num > max {
					max = num
					hasValue = true
				}
			}
		}
		if !hasValue {
			return nil, fmt.Errorf("no numeric values for max")
		}
		return max, nil
	case "min":
		var min float64
		hasValue := false
		for _, val := range values {
			if num, err := ae.toNumber(val); err == nil {
				if !hasValue || num < min {
					min = num
					hasValue = true
				}
			}
		}
		if !hasValue {
			return nil, fmt.Errorf("no numeric values for min")
		}
		return min, nil
	default:
		return nil, fmt.Errorf("unsupported aggregation operation: %s", operation)
	}
}

// Utility methods for result management
func (ae *ActionExecutor) GetResults() []ActionResult {
	return ae.results
}

func (ae *ActionExecutor) GetResultsByType(actionType string) []ActionResult {
	var results []ActionResult
	for _, result := range ae.results {
		if result.Type == actionType {
			results = append(results, result)
		}
	}
	return results
}

func (ae *ActionExecutor) GetSuccessfulResults() []ActionResult {
	var results []ActionResult
	for _, result := range ae.results {
		if result.Success {
			results = append(results, result)
		}
	}
	return results
}

func (ae *ActionExecutor) GetFailedResults() []ActionResult {
	var results []ActionResult
	for _, result := range ae.results {
		if !result.Success {
			results = append(results, result)
		}
	}
	return results
}

func (ae *ActionExecutor) ClearResults() {
	ae.results = make([]ActionResult, 0)
}

func (ae *ActionExecutor) GetExecutionSummary() map[string]interface{} {
	total := len(ae.results)
	successful := len(ae.GetSuccessfulResults())
	failed := len(ae.GetFailedResults())
	
	var totalTime int64
	for _, result := range ae.results {
		totalTime += result.ExecutionTimeMs
	}
	
	typeCount := make(map[string]int)
	for _, result := range ae.results {
		typeCount[result.Type]++
	}
	
	return map[string]interface{}{
		"total_actions":     total,
		"successful":        successful,
		"failed":            failed,
		"success_rate":      float64(successful) / float64(total) * 100,
		"total_time_ms":     totalTime,
		"average_time_ms":   float64(totalTime) / float64(total),
		"actions_by_type":   typeCount,
	}
}

// Data access methods
func (ae *ActionExecutor) GetData() map[string]interface{} {
	return ae.data
}

func (ae *ActionExecutor) SetData(data map[string]interface{}) {
	ae.data = data
}

func (ae *ActionExecutor) MergeData(newData map[string]interface{}) {
	for key, value := range newData {
		ae.data[key] = value
	}
}

// Export results to JSON
func (ae *ActionExecutor) ExportResults() ([]byte, error) {
	return json.MarshalIndent(ae.results, "", "  ")
}

// Example usage and testing
func main() {
	// Test data
	data := map[string]interface{}{
		"user": map[string]interface{}{
			"name":  "John Doe",
			"age":   30,
			"email": "john@example.com",
			"profile": map[string]interface{}{
				"score": 85,
				"level": "intermediate",
			},
		},
		"product": map[string]interface{}{
			"name":  "Widget",
			"price": 99.99,
			"tags":  []interface{}{"electronics", "gadget"},
		},
	}
	
	executor := NewActionExecutor(data)
	
	// Test actions with different priorities
	actions := []Action{
		{
			ID:       "set_status",
			Type:     "set",
			Priority: 2,
			Target:   "user.status",
			Params: map[string]interface{}{
				"value": "active",
				"mode":  "create",
			},
		},
		{
			ID:       "increment_score",
			Type:     "set",
			Priority: 1, // Higher priority (executes first)
			Target:   "user.profile.score",
			Params: map[string]interface{}{
				"value": 10,
				"mode":  "increment",
			},
		},
		{
			ID:       "transform_name",
			Type:     "transform",
			Priority: 3,
			Target:   "user.name",
			Params: map[string]interface{}{
				"type": "uppercase",
			},
		},
		{
			ID:       "validate_email",
			Type:     "validate",
			Priority: 4,
			Target:   "user.email",
			Params: map[string]interface{}{
				"rules": map[string]interface{}{
					"required": true,
					"type":     "string",
				},
			},
		},
		{
			ID:       "send_webhook",
			Type:     "webhook",
			Priority: 5,
			Target:   "https://api.example.com/webhook",
			Params: map[string]interface{}{
				"method": "POST",
				"body": map[string]interface{}{
					"user_id": "user.id",
					"event":   "profile_updated",
				},
				"headers": map[string]interface{}{
					"Authorization": "Bearer token123",
				},
			},
		},
		{
			ID:       "aggregate_scores",
			Type:     "aggregate",
			Priority: 6,
			Target:   "user.total_score",
			Params: map[string]interface{}{
				"fields":    []interface{}{"user.profile.score", "product.price"},
				"operation": "sum",
			},
		},
		{
			ID:       "log_completion",
			Type:     "log",
			Priority: 7,
			Params: map[string]interface{}{
				"message": "Actions completed successfully",
				"level":   "info",
				"data":    map[string]interface{}{"timestamp": time.Now()},
			},
		},
	}
	
	fmt.Println("Action Executor Test Results")
	fmt.Println("============================")
	
	// Execute actions
	results, err := executor.ExecuteActions(actions)
	if err != nil {
		fmt.Printf("Execution error: %v\n", err)
		return
	}
	
	// Print results
	fmt.Printf("Executed %d actions:\n\n", len(results))
	
	for i, result := range results {
		fmt.Printf("Action %d: %s (ID: %s)\n", i+1, result.Type, result.ActionID)
		fmt.Printf("  Success: %v\n", result.Success)
		fmt.Printf("  Execution Time: %dms\n", result.ExecutionTimeMs)
		
		if result.Error != "" {
			fmt.Printf("  Error: %s\n", result.Error)
		}
		
		if result.Result != nil {
			resultJSON, _ := json.MarshalIndent(result.Result, "  ", "  ")
			fmt.Printf("  Result: %s\n", string(resultJSON))
		}
		
		fmt.Println()
	}
	
	// Print execution summary
	summary := executor.GetExecutionSummary()
	fmt.Println("Execution Summary:")
	summaryJSON, _ := json.MarshalIndent(summary, "", "  ")
	fmt.Println(string(summaryJSON))
	
	// Print final data state
	fmt.Println("\nFinal Data State:")
	dataJSON, _ := json.MarshalIndent(executor.GetData(), "", "  ")
	fmt.Println(string(dataJSON))
	
	// Test specific action types
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("Testing Individual Action Types")
	fmt.Println(strings.Repeat("=", 50))
	
	// Test set action with nested field creation
	testSetAction := Action{
		ID:     "test_nested_set",
		Type:   "set",
		Target: "user.preferences.theme",
		Params: map[string]interface{}{
			"value": "dark",
			"mode":  "create",
		},
	}
	
	setResult := executor.ExecuteSetAction(testSetAction)
	fmt.Printf("Set Action Result: %+v\n", setResult)
	
	// Test external call preparation
	testWebhookAction := Action{
		ID:     "test_webhook",
		Type:   "webhook",
		Target: "https://api.test.com/notify",
		Params: map[string]interface{}{
			"method":  "POST",
			"timeout": 45,
			"body": map[string]interface{}{
				"message": "Test notification",
				"user_id": 123,
			},
		},
	}
	
	webhookResult := executor.PrepareExternalCall(testWebhookAction)
	fmt.Printf("Webhook Preparation Result: %+v\n", webhookResult)
	
	// Test error handling
	errorAction := Action{
		ID:     "test_error",
		Type:   "set",
		Target: "nonexistent.deeply.nested.field",
		Params: map[string]interface{}{
			"value": "test",
			"mode":  "replace", // This should fail since field doesn't exist
		},
	}
	
	errorResult := executor.ExecuteSetAction(errorAction)
	fmt.Printf("Error Handling Test: Success=%v, Error=%s\n", errorResult.Success, errorResult.Error)
}