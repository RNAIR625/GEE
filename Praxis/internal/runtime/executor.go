package runtime

import (
	"encoding/json"
	"fmt"
	"log"
	"strconv"
	"strings"
	"time"
)

// ExecutionContext holds the data context for flow execution
type ExecutionContext struct {
	Input     map[string]interface{}
	Variables map[string]interface{}
	Output    map[string]interface{}
	Errors    []string
	StartTime time.Time
}

// FlowDefinition represents the parsed flow structure
type FlowDefinition struct {
	FlowID      int                       `json:"flow_id"`
	FlowName    string                    `json:"flow_name"`
	FlowVersion string                    `json:"flow_version"`
	StartNodes  []string                  `json:"start_nodes"`
	Nodes       map[string]NodeDefinition `json:"nodes"`
	Connections map[string][]Connection   `json:"connections"`
	Rules       map[string]RuleDefinition `json:"rules"`
	RuleGroups  map[string]GroupDefinition `json:"rule_groups"`
	Functions   map[string]FunctionDef    `json:"functions"`
}

// NodeDefinition represents a flow node
type NodeDefinition struct {
	ID          string                 `json:"id"`
	Type        string                 `json:"type"`
	ReferenceID int                    `json:"reference_id"`
	Properties  map[string]interface{} `json:"properties"`
}

// Connection represents a connection between nodes
type Connection struct {
	Target    string `json:"target"`
	Condition string `json:"condition"`
}

// RuleDefinition represents a rule's execution logic
type RuleDefinition struct {
	ID            int           `json:"id"`
	Name          string        `json:"name"`
	Type          string        `json:"type"`
	Description   string        `json:"description"`
	ConditionCode string        `json:"condition_code"`
	ActionCode    string        `json:"action_code"`
	Conditions    []interface{} `json:"conditions"`
	Actions       []interface{} `json:"actions"`
	ErrorHandling interface{}   `json:"error_handling"`
}

// RuleLine represents a condition or action line in a rule
type RuleLine struct {
	Sequence    int    `json:"sequence"`
	Field       string `json:"field"`
	Operator    string `json:"operator"`
	Value       string `json:"value"`
	TargetType  string `json:"target_type"`
	TargetID    int    `json:"target_id"`
	TargetValue string `json:"target_value"`
}

// GroupDefinition represents a rule group
type GroupDefinition struct {
	ID    int              `json:"id"`
	Name  string           `json:"name"`
	Logic string           `json:"logic"` // AND, OR
	Rules []RuleDefinition `json:"rules"`
}

// FunctionDef represents a function definition
type FunctionDef struct {
	ID              int           `json:"id"`
	Name            string        `json:"name"`
	Type            string        `json:"type"`
	Code            string        `json:"code"`
	InputParameters []Parameter   `json:"input_parameters"`
	OutputParams    []Parameter   `json:"output_parameters"`
}

// Parameter represents a function parameter
type Parameter struct {
	Name     string      `json:"name"`
	Type     string      `json:"type"`
	Required bool        `json:"required"`
	Default  interface{} `json:"default"`
}

// FlowExecutor executes flows
type FlowExecutor struct {
	loader    *RuntimeLoader
	flowDef   *FlowDefinition
	context   *ExecutionContext
}

// NewFlowExecutor creates a new flow executor
func NewFlowExecutor(loader *RuntimeLoader) *FlowExecutor {
	return &FlowExecutor{
		loader: loader,
	}
}

// ExecuteFlow executes a flow with given input data
func (e *FlowExecutor) ExecuteFlow(flowID int, input map[string]interface{}) (map[string]interface{}, error) {
	// Load flow from runtime database
	flow, err := e.loader.LoadFlow(flowID)
	if err != nil {
		return nil, fmt.Errorf("failed to load flow: %w", err)
	}

	// Parse flow definition
	e.flowDef = &FlowDefinition{}
	if err := json.Unmarshal([]byte(flow.Definition), e.flowDef); err != nil {
		return nil, fmt.Errorf("failed to parse flow definition: %w", err)
	}

	// Initialize execution context
	e.context = &ExecutionContext{
		Input:     input,
		Variables: make(map[string]interface{}),
		Output:    make(map[string]interface{}),
		Errors:    []string{},
		StartTime: time.Now(),
	}

	// Execute flow starting from start nodes
	log.Printf("Starting flow execution with %d start nodes", len(e.flowDef.StartNodes))
	for _, startNodeID := range e.flowDef.StartNodes {
		log.Printf("Processing start node: %s", startNodeID)
		if node, exists := e.flowDef.Nodes[startNodeID]; exists {
			log.Printf("Found node %s of type %s with reference_id %d", node.ID, node.Type, node.ReferenceID)
			if err := e.executeNode(node); err != nil {
				e.context.Errors = append(e.context.Errors, fmt.Sprintf("Node %s error: %v", startNodeID, err))
			}
		} else {
			log.Printf("Start node %s not found in nodes map", startNodeID)
		}
	}

	// Prepare result
	result := map[string]interface{}{
		"output":         e.context.Output,
		"variables":      e.context.Variables,
		"errors":         e.context.Errors,
		"execution_time": time.Since(e.context.StartTime).Milliseconds(),
	}

	return result, nil
}

// executeNode executes a single node
func (e *FlowExecutor) executeNode(node NodeDefinition) error {
	log.Printf("Executing node %s of type %s", node.ID, node.Type)

	var err error
	switch node.Type {
	case "RULE", "rule":
		err = e.executeRule(node.ReferenceID)
	case "RULE_GROUP", "rule-group", "rule_group":
		err = e.executeRuleGroup(node.ReferenceID)
	case "FUNCTION", "function":
		err = e.executeFunction(node.ReferenceID)
	case "START", "start":
		// Start nodes don't have execution logic
		log.Printf("Executing start node %s", node.ID)
		err = nil
	case "END", "end":
		// End nodes might collect outputs
		log.Printf("Executing end node %s", node.ID)
		err = nil
	case "CONDITION", "condition":
		// Condition nodes evaluate expressions
		err = e.executeCondition(node)
	case "ACTION", "action":
		// Action nodes perform operations
		err = e.executeAction(node)
	case "DECISION", "decision":
		// Decision nodes for branching logic
		err = e.executeDecision(node)
	default:
		log.Printf("Warning: Unknown node type '%s' for node %s - treating as pass-through", node.Type, node.ID)
		err = nil // Continue execution instead of failing
	}

	if err != nil {
		return err
	}

	// Execute connected nodes
	if connections, exists := e.flowDef.Connections[node.ID]; exists {
		for _, conn := range connections {
			// Check condition if specified
			if conn.Condition != "" {
				if !e.evaluateCondition(conn.Condition) {
					continue
				}
			}

			// Execute target node
			if targetNode, exists := e.flowDef.Nodes[conn.Target]; exists {
				if err := e.executeNode(targetNode); err != nil {
					log.Printf("Error executing connected node %s: %v", conn.Target, err)
					// Continue with other connections even if one fails
				}
			}
		}
	}

	return nil
}

// executeRule executes a single rule
func (e *FlowExecutor) executeRule(ruleID int) error {
	ruleIDStr := fmt.Sprintf("%d", ruleID)
	ruleDef, exists := e.flowDef.Rules[ruleIDStr]
	if !exists {
		// Try loading from database
		rule, err := e.loader.LoadRule(ruleID)
		if err != nil {
			return fmt.Errorf("rule %d not found: %w", ruleID, err)
		}

		// Parse rule logic
		var ruleLogic RuleDefinition
		if err := json.Unmarshal([]byte(rule.Logic), &ruleLogic); err != nil {
			return fmt.Errorf("failed to parse rule logic: %w", err)
		}
		ruleDef = ruleLogic
	}

	log.Printf("Executing rule: %s", ruleDef.Name)

	// Evaluate conditions based on the new rule structure
	conditionsMet := true
	
	// Handle new-style conditions with function calls
	if len(ruleDef.Conditions) > 0 {
		for _, condition := range ruleDef.Conditions {
			if !e.evaluateNewRuleCondition(condition) {
				conditionsMet = false
				break
			}
		}
	} else {
		// Try to evaluate condition_code if present
		if ruleDef.ConditionCode != "" {
			conditionsMet = e.evaluateConditionCode(ruleDef.ConditionCode)
		}
	}

	// Execute actions if conditions are met
	if conditionsMet {
		for _, action := range ruleDef.Actions {
			if err := e.executeNewRuleAction(action); err != nil {
				log.Printf("Error executing action: %v", err)
				// Continue with other actions
			}
		}
	}

	return nil
}

// executeRuleGroup executes a rule group
func (e *FlowExecutor) executeRuleGroup(groupID int) error {
	groupIDStr := fmt.Sprintf("%d", groupID)
	groupDef, exists := e.flowDef.RuleGroups[groupIDStr]
	if !exists {
		// Load rules for the group from database
		rules, err := e.loader.LoadRuleGroup(groupID)
		if err != nil {
			return fmt.Errorf("failed to load rule group %d: %w", groupID, err)
		}

		// Create group definition
		groupDef = GroupDefinition{
			ID:    groupID,
			Logic: "AND", // Default
			Rules: []RuleDefinition{},
		}

		// Parse each rule
		for _, rule := range rules {
			var ruleLogic RuleDefinition
			if err := json.Unmarshal([]byte(rule.Logic), &ruleLogic); err != nil {
				log.Printf("Failed to parse rule logic for rule %d: %v", rule.ID, err)
				continue
			}
			groupDef.Rules = append(groupDef.Rules, ruleLogic)
		}
	}

	log.Printf("Executing rule group with %d rules using %s logic", len(groupDef.Rules), groupDef.Logic)

	// Execute rules based on group logic
	if groupDef.Logic == "OR" {
		// OR logic - execute until one succeeds
		for _, rule := range groupDef.Rules {
			if err := e.executeRuleDef(rule); err == nil {
				return nil // One rule succeeded
			}
		}
		return fmt.Errorf("all rules in OR group failed")
	} else {
		// AND logic - all must succeed
		for _, rule := range groupDef.Rules {
			if err := e.executeRuleDef(rule); err != nil {
				return fmt.Errorf("rule %s failed in AND group: %w", rule.Name, err)
			}
		}
	}

	return nil
}

// executeRuleDef executes a rule definition
func (e *FlowExecutor) executeRuleDef(ruleDef RuleDefinition) error {
	log.Printf("Executing rule definition: %s (type: %s)", ruleDef.Name, ruleDef.Type)
	
	// Evaluate conditions based on the new rule structure
	conditionsMet := true
	
	// Handle new-style conditions with function calls
	if len(ruleDef.Conditions) > 0 {
		log.Printf("Evaluating %d conditions for rule %s", len(ruleDef.Conditions), ruleDef.Name)
		for _, condition := range ruleDef.Conditions {
			if !e.evaluateNewRuleCondition(condition) {
				conditionsMet = false
				break
			}
		}
	} else {
		// Try to evaluate condition_code if present
		if ruleDef.ConditionCode != "" {
			log.Printf("Evaluating condition code: %s", ruleDef.ConditionCode)
			conditionsMet = e.evaluateConditionCode(ruleDef.ConditionCode)
		}
	}

	log.Printf("Rule %s conditions met: %v", ruleDef.Name, conditionsMet)

	if !conditionsMet {
		return fmt.Errorf("conditions not met for rule %s", ruleDef.Name)
	}

	// Execute actions based on new structure
	if len(ruleDef.Actions) > 0 {
		log.Printf("Executing %d actions for rule %s", len(ruleDef.Actions), ruleDef.Name)
		for _, action := range ruleDef.Actions {
			if err := e.executeNewRuleAction(action); err != nil {
				return fmt.Errorf("action failed: %w", err)
			}
		}
	} else {
		// Try to execute action_code if present
		if ruleDef.ActionCode != "" {
			log.Printf("Executing action code: %s", ruleDef.ActionCode)
			if err := e.executeActionCode(ruleDef.ActionCode); err != nil {
				return fmt.Errorf("action code failed: %w", err)
			}
		}
	}

	log.Printf("Rule %s executed successfully", ruleDef.Name)
	return nil
}

// evaluateCondition evaluates a flow condition expression
func (e *FlowExecutor) evaluateCondition(condition string) bool {
	// Simple condition evaluation
	// TODO: Implement proper expression parser
	
	// For now, check for simple variable comparisons
	if strings.Contains(condition, "==") {
		parts := strings.Split(condition, "==")
		if len(parts) == 2 {
			left := strings.TrimSpace(parts[0])
			right := strings.TrimSpace(parts[1])
			
			// Get value from context
			leftVal := e.getContextValue(left)
			rightVal := strings.Trim(right, "'\"")
			
			return fmt.Sprintf("%v", leftVal) == rightVal
		}
	}
	
	// Default to true if we can't parse
	return true
}

// evaluateRuleCondition evaluates a rule condition
func (e *FlowExecutor) evaluateRuleCondition(condition RuleLine) bool {
	// If this condition has a function call, execute it first
	if condition.TargetType == "FUNCTION" && condition.TargetID > 0 {
		if err := e.executeFunction(condition.TargetID); err != nil {
			log.Printf("Error executing condition function %d: %v", condition.TargetID, err)
			return false
		}
	}
	
	fieldValue := e.getContextValue(condition.Field)
	
	switch condition.Operator {
	case "EQUALS", "=", "==":
		return fmt.Sprintf("%v", fieldValue) == condition.Value
	case "NOT_EQUALS", "!=", "<>":
		return fmt.Sprintf("%v", fieldValue) != condition.Value
	case "GREATER_THAN", ">":
		left, err1 := e.convertToFloat(fieldValue)
		right, err2 := e.convertToFloat(condition.Value)
		if err1 == nil && err2 == nil {
			return left > right
		}
		return false
	case "LESS_THAN", "<":
		left, err1 := e.convertToFloat(fieldValue)
		right, err2 := e.convertToFloat(condition.Value)
		if err1 == nil && err2 == nil {
			return left < right
		}
		return false
	case "CONTAINS":
		return strings.Contains(fmt.Sprintf("%v", fieldValue), condition.Value)
	case "NOT_NULL", "IS_NOT_NULL":
		return fieldValue != nil
	case "NULL", "IS_NULL":
		return fieldValue == nil
	default:
		log.Printf("Unknown operator: %s", condition.Operator)
		return true
	}
}

// executeRuleAction executes a rule action
func (e *FlowExecutor) executeRuleAction(action RuleLine) error {
	switch action.TargetType {
	case "FIELD":
		// Set field value
		e.setContextValue(action.Field, action.TargetValue)
		
	case "FUNCTION":
		// Execute function
		if action.TargetID > 0 {
			return e.executeFunction(action.TargetID)
		}
		
	case "OUTPUT":
		// Set output value
		e.context.Output[action.Field] = action.TargetValue
		
	default:
		log.Printf("Unknown action target type: %s", action.TargetType)
	}
	
	return nil
}

// executeFunction executes a function
func (e *FlowExecutor) executeFunction(functionID int) error {
	// Load function from database
	function, err := e.loader.LoadFunction(functionID)
	if err != nil {
		return fmt.Errorf("failed to load function %d: %w", functionID, err)
	}

	log.Printf("Executing function: %s of type %s", function.Name, function.Type)

	switch function.Type {
	case "JAVASCRIPT", "javascript", "js":
		return e.executeJavaScriptFunction(function)
		
	case "SQL", "sql":
		return e.executeSQLFunction(function)
		
	case "BUILTIN", "builtin":
		return e.executeBuiltinFunction(function.Name, function.Code)
		
	case "PYTHON", "python", "py":
		return e.executePythonFunction(function)
		
	default:
		// Try to execute as a built-in function based on name
		log.Printf("Unknown function type '%s', attempting built-in execution for function '%s'", function.Type, function.Name)
		return e.executeBuiltinFunctionByName(function)
	}

	return nil
}

// executeBuiltinFunction executes a built-in function
func (e *FlowExecutor) executeBuiltinFunction(name, code string) error {
	// Implement some basic built-in functions
	switch name {
	case "LOG":
		log.Printf("[Flow Log] %s", code)
		
	case "SET_VARIABLE":
		// Parse code as JSON to get variable name and value
		var params map[string]interface{}
		if err := json.Unmarshal([]byte(code), &params); err == nil {
			if varName, ok := params["name"].(string); ok {
				if value, ok := params["value"]; ok {
					e.context.Variables[varName] = value
				}
			}
		}
		
	default:
		// For other functions, delegate to the comprehensive built-in function handler
		log.Printf("Delegating built-in function '%s' to comprehensive handler", name)
		mockFunction := &Function{
			Name: name,
			Type: "BUILTIN",
			Code: code,
		}
		return e.executeBuiltinFunctionByName(mockFunction)
	}
	
	return nil
}

// getContextValue gets a value from the execution context
func (e *FlowExecutor) getContextValue(path string) interface{} {
	// Check if it's an input field
	if strings.HasPrefix(path, "input.") {
		fieldName := strings.TrimPrefix(path, "input.")
		return e.context.Input[fieldName]
	}
	
	// Check if it's a variable
	if strings.HasPrefix(path, "var.") {
		varName := strings.TrimPrefix(path, "var.")
		return e.context.Variables[varName]
	}
	
	// Check direct input
	if val, exists := e.context.Input[path]; exists {
		return val
	}
	
	// Check variables
	if val, exists := e.context.Variables[path]; exists {
		return val
	}
	
	return nil
}

// setContextValue sets a value in the execution context
func (e *FlowExecutor) setContextValue(path string, value interface{}) {
	// Set in variables by default
	if strings.HasPrefix(path, "var.") {
		varName := strings.TrimPrefix(path, "var.")
		e.context.Variables[varName] = value
	} else if strings.HasPrefix(path, "output.") {
		outputName := strings.TrimPrefix(path, "output.")
		e.context.Output[outputName] = value
	} else {
		// Default to variables
		e.context.Variables[path] = value
	}
}

// executeCondition executes a condition node
func (e *FlowExecutor) executeCondition(node NodeDefinition) error {
	log.Printf("Executing condition node %s", node.ID)
	
	// Extract condition from node properties
	condition, ok := node.Properties["condition"].(string)
	if !ok {
		log.Printf("No condition property found for condition node %s", node.ID)
		return nil
	}
	
	// Evaluate the condition
	result := e.evaluateCondition(condition)
	
	// Store result in context for potential use by connected nodes
	e.context.Variables[fmt.Sprintf("condition_%s_result", node.ID)] = result
	
	log.Printf("Condition node %s evaluated to: %v", node.ID, result)
	return nil
}

// executeAction executes an action node
func (e *FlowExecutor) executeAction(node NodeDefinition) error {
	log.Printf("Executing action node %s", node.ID)
	
	// Extract action type and parameters from node properties
	actionType, ok := node.Properties["action_type"].(string)
	if !ok {
		return fmt.Errorf("no action_type property found for action node %s", node.ID)
	}
	
	switch actionType {
	case "set_variable":
		return e.executeSetVariableAction(node)
	case "log_message":
		return e.executeLogAction(node)
	case "call_function":
		if functionID, ok := node.Properties["function_id"].(float64); ok {
			return e.executeFunction(int(functionID))
		}
		return fmt.Errorf("invalid function_id for call_function action")
	case "set_output":
		return e.executeSetOutputAction(node)
	default:
		log.Printf("Unknown action type '%s' for action node %s", actionType, node.ID)
		return nil
	}
}

// executeDecision executes a decision node
func (e *FlowExecutor) executeDecision(node NodeDefinition) error {
	log.Printf("Executing decision node %s", node.ID)
	
	// Decision nodes typically have conditions that determine which path to take
	// The actual branching logic is handled by connection conditions
	
	// Extract decision criteria from node properties
	if criteria, ok := node.Properties["decision_criteria"].(string); ok {
		result := e.evaluateCondition(criteria)
		e.context.Variables[fmt.Sprintf("decision_%s_result", node.ID)] = result
		log.Printf("Decision node %s evaluated criteria '%s' to: %v", node.ID, criteria, result)
	}
	
	return nil
}

// executeSetVariableAction executes a set variable action
func (e *FlowExecutor) executeSetVariableAction(node NodeDefinition) error {
	varName, nameOk := node.Properties["variable_name"].(string)
	varValue, valueOk := node.Properties["variable_value"]
	
	if !nameOk {
		return fmt.Errorf("no variable_name property for set_variable action")
	}
	
	if !valueOk {
		// Try to get from variable_expression
		if expr, exprOk := node.Properties["variable_expression"].(string); exprOk {
			// Simple expression evaluation - could be enhanced
			varValue = e.evaluateSimpleExpression(expr)
		} else {
			varValue = ""
		}
	}
	
	e.context.Variables[varName] = varValue
	log.Printf("Set variable %s = %v", varName, varValue)
	return nil
}

// executeLogAction executes a log message action
func (e *FlowExecutor) executeLogAction(node NodeDefinition) error {
	message, ok := node.Properties["message"].(string)
	if !ok {
		message = fmt.Sprintf("Log from node %s", node.ID)
	}
	
	// Simple template replacement for variables
	for varName, varValue := range e.context.Variables {
		placeholder := fmt.Sprintf("${%s}", varName)
		message = strings.Replace(message, placeholder, fmt.Sprintf("%v", varValue), -1)
	}
	
	log.Printf("[Flow Log] %s", message)
	return nil
}

// executeSetOutputAction executes a set output action
func (e *FlowExecutor) executeSetOutputAction(node NodeDefinition) error {
	outputName, nameOk := node.Properties["output_name"].(string)
	outputValue, valueOk := node.Properties["output_value"]
	
	if !nameOk {
		return fmt.Errorf("no output_name property for set_output action")
	}
	
	if !valueOk {
		// Try to get from output_expression
		if expr, exprOk := node.Properties["output_expression"].(string); exprOk {
			outputValue = e.evaluateSimpleExpression(expr)
		} else {
			outputValue = ""
		}
	}
	
	e.context.Output[outputName] = outputValue
	log.Printf("Set output %s = %v", outputName, outputValue)
	return nil
}

// evaluateSimpleExpression evaluates a simple expression
func (e *FlowExecutor) evaluateSimpleExpression(expr string) interface{} {
	// Simple variable substitution
	if strings.HasPrefix(expr, "$") {
		varName := strings.TrimPrefix(expr, "$")
		if value, exists := e.context.Variables[varName]; exists {
			return value
		}
		if value, exists := e.context.Input[varName]; exists {
			return value
		}
	}
	
	// Return as literal string if not a variable reference
	return expr
}

// evaluateNewRuleCondition evaluates a condition from the new rule structure
func (e *FlowExecutor) evaluateNewRuleCondition(condition interface{}) bool {
	// Convert condition to map for easier access
	conditionMap, ok := condition.(map[string]interface{})
	if !ok {
		log.Printf("Invalid condition format: %T", condition)
		return false
	}
	
	// Check if this is a function-based condition
	if functionID, exists := conditionMap["function_id"]; exists {
		if fid, ok := functionID.(float64); ok && fid > 0 {
			log.Printf("Executing condition function %v", fid)
			if err := e.executeFunction(int(fid)); err != nil {
				log.Printf("Error executing condition function %v: %v", fid, err)
				return false
			}
			
			// Check if function execution set a result
			functionName, _ := conditionMap["function_name"].(string)
			if functionName != "" {
				// Check for function result
				resultKey := fmt.Sprintf("func_%s_result", functionName)
				if result := e.getContextValue(resultKey); result != nil {
					// Convert result to boolean
					return e.convertToBool(result)
				}
			}
			
			// Default to true if function executed without error
			return true
		}
	}
	
	// If not a function condition, check for basic field comparisons
	return true
}

// evaluateConditionCode evaluates condition code (like JavaScript expressions)
func (e *FlowExecutor) evaluateConditionCode(code string) bool {
	log.Printf("Evaluating condition code: %s", code)
	
	// Check for multiplication pattern like "Multiply(fields.objectValue, fields.objectHST, fields.code)"
	if strings.Contains(code, "Multiply(") {
		return e.evaluateMultiplyCondition(code)
	}
	
	// Other patterns can be added here
	result := e.evaluateJavaScriptExpression(code)
	return e.convertToBool(result)
}

// evaluateMultiplyCondition evaluates multiplication conditions
func (e *FlowExecutor) evaluateMultiplyCondition(code string) bool {
	log.Printf("Evaluating multiply condition: %s", code)
	
	// Extract field references and perform multiplication
	// Simple pattern: Multiply(fields.objectValue, fields.objectHST, fields.code)
	
	// Get values from context
	objectValue := e.getContextValue("objectValue")
	objectHST := e.getContextValue("objectHST")
	
	if objectValue != nil && objectHST != nil {
		val1, err1 := e.convertToFloat(objectValue)
		val2, err2 := e.convertToFloat(objectHST)
		
		if err1 == nil && err2 == nil {
			result := val1 * val2
			e.context.Variables["multiply_condition_result"] = result
			log.Printf("Multiply condition result: %v", result)
			
			// Condition is true if result > 0
			return result > 0
		}
	}
	
	return false
}

// convertToBool converts a value to boolean
func (e *FlowExecutor) convertToBool(value interface{}) bool {
	switch v := value.(type) {
	case bool:
		return v
	case string:
		return v != "" && v != "false" && v != "0"
	case float64:
		return v != 0
	case int:
		return v != 0
	default:
		return value != nil
	}
}

// executeNewRuleAction executes an action from the new rule structure
func (e *FlowExecutor) executeNewRuleAction(action interface{}) error {
	// Convert action to map for easier access
	actionMap, ok := action.(map[string]interface{})
	if !ok {
		log.Printf("Invalid action format: %T", action)
		return nil
	}
	
	// Check if this is a function-based action
	if functionID, exists := actionMap["function_id"]; exists {
		if fid, ok := functionID.(float64); ok && fid > 0 {
			log.Printf("Executing action function %v", fid)
			return e.executeFunction(int(fid))
		}
	}
	
	// If not a function action, check for other action types
	log.Printf("Non-function action executed: %v", actionMap)
	return nil
}

// executeActionCode executes action code (like JavaScript expressions)
func (e *FlowExecutor) executeActionCode(code string) error {
	log.Printf("Executing action code: %s", code)
	
	// Check for multiplication pattern like "Multiply(fields.objectValue, fields.objectHST, fields.code)"
	if strings.Contains(code, "Multiply(") {
		return e.executeMultiplyAction(code)
	}
	
	// Other patterns can be added here
	result := e.evaluateJavaScriptExpression(code)
	
	// Store result in output
	e.context.Output["action_result"] = result
	
	log.Printf("Action code result: %v", result)
	return nil
}

// executeMultiplyAction executes multiplication actions
func (e *FlowExecutor) executeMultiplyAction(code string) error {
	log.Printf("Executing multiply action: %s", code)
	
	// Extract field references and perform multiplication
	// Simple pattern: Multiply(fields.objectValue, fields.objectHST, fields.code)
	
	// Get values from context
	objectValue := e.getContextValue("objectValue")
	objectHST := e.getContextValue("objectHST")
	
	if objectValue != nil && objectHST != nil {
		val1, err1 := e.convertToFloat(objectValue)
		val2, err2 := e.convertToFloat(objectHST)
		
		if err1 == nil && err2 == nil {
			result := val1 * val2
			
			// Store result in context and output
			e.context.Variables["multiply_action_result"] = result
			e.context.Output["calculated_value"] = result
			
			log.Printf("Multiply action result: %v", result)
			return nil
		}
	}
	
	log.Printf("Could not execute multiply action - missing or invalid values")
	return nil
}

// executeJavaScriptFunction executes a JavaScript function
func (e *FlowExecutor) executeJavaScriptFunction(function *Function) error {
	log.Printf("Executing JavaScript function: %s", function.Name)
	
	// For now, implement a basic JavaScript-like evaluation
	// In a full implementation, you would use a JS engine like goja or v8go
	
	// Simple pattern matching for common JS operations
	code := function.Code
	if code == "" {
		log.Printf("No code provided for JavaScript function %s", function.Name)
		return nil
	}
	
	// Basic variable substitution
	result := e.evaluateJavaScriptExpression(code)
	
	// Store result in context
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = result
	
	log.Printf("JavaScript function %s executed with result: %v", function.Name, result)
	return nil
}

// executeSQLFunction executes a SQL function
func (e *FlowExecutor) executeSQLFunction(function *Function) error {
	log.Printf("Executing SQL function: %s", function.Name)
	
	// For now, implement basic SQL-like operations
	// In a full implementation, you would execute against actual databases
	
	code := function.Code
	if code == "" {
		log.Printf("No SQL code provided for function %s", function.Name)
		return nil
	}
	
	// Simple SQL simulation - can be enhanced to use actual database connections
	result := e.evaluateSQLExpression(code)
	
	// Store result in context
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = result
	
	log.Printf("SQL function %s executed with result: %v", function.Name, result)
	return nil
}

// executePythonFunction executes a Python function
func (e *FlowExecutor) executePythonFunction(function *Function) error {
	log.Printf("Executing Python function: %s", function.Name)
	
	// For now, implement basic Python-like evaluation
	// In a full implementation, you would use a Python interpreter
	
	code := function.Code
	if code == "" {
		log.Printf("No code provided for Python function %s", function.Name)
		return nil
	}
	
	// Basic evaluation
	result := e.evaluatePythonExpression(code)
	
	// Store result in context
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = result
	
	log.Printf("Python function %s executed with result: %v", function.Name, result)
	return nil
}

// executeBuiltinFunctionByName executes a built-in function based on its name
func (e *FlowExecutor) executeBuiltinFunctionByName(function *Function) error {
	log.Printf("Executing built-in function: %s", function.Name)
	
	functionNameLower := strings.ToLower(function.Name)
	log.Printf("Checking built-in function name: '%s' (lower: '%s')", function.Name, functionNameLower)
	
	switch functionNameLower {
	case "exist_in_pin_code", "exists_in_pin_code", "exists_in_pincode":
		log.Printf("Matched exist_in_pin_code function")
		return e.executeExistsInPinCode(function)
	case "multiply":
		return e.executeMultiply(function)
	case "validate_email":
		return e.executeValidateEmail(function)
	case "calculate_tax":
		return e.executeCalculateTax(function)
	case "format_currency":
		return e.executeFormatCurrency(function)
	case "log", "logger", "print":
		return e.executeLogFunction(function)
	// Tax calculation functions
	case "get_gst":
		return e.executeGetGST(function)
	case "get_hst":
		return e.executeGetHST(function) 
	case "get_pst":
		return e.executeGetPST(function)
	case "get_province_from_pincode":
		return e.executeGetProvinceFromPincode(function)
	case "calculate_tax_amount":
		return e.executeCalculateTaxAmount(function)
	default:
		log.Printf("Unknown built-in function: %s - treating as no-op", function.Name)
		return nil
	}
}

// executeExistsInPinCode implements the exist_in_PIN_CODE function
func (e *FlowExecutor) executeExistsInPinCode(function *Function) error {
	log.Printf("Executing exist_in_PIN_CODE function")
	
	// Get postal code from input or context (support both pin_code and postal_code)
	postalCode := e.getContextValue("postal_code")
	if postalCode == nil {
		postalCode = e.getContextValue("input.postal_code")
	}
	if postalCode == nil {
		postalCode = e.getContextValue("pin_code")
	}
	if postalCode == nil {
		postalCode = e.getContextValue("input.pin_code")
	}
	
	// Mock validation - check if postal code follows Canadian format
	exists := false
	if postalCode != nil {
		postalCodeStr := strings.ToUpper(fmt.Sprintf("%v", postalCode))
		// Canadian postal codes: Letter-Number-Letter (e.g., M5V, H3A, V6B)
		if len(postalCodeStr) >= 3 {
			exists = e.isValidCanadianPostalCode(postalCodeStr)
		}
	}
	
	// Store result
	e.context.Variables["postal_code_exists"] = exists
	e.context.Variables["pin_code_exists"] = exists  // For backward compatibility
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = exists
	
	log.Printf("Postal code validation result: %v for code: %v", exists, postalCode)
	return nil
}

// isValidCanadianPostalCode checks if a postal code is valid Canadian format
func (e *FlowExecutor) isValidCanadianPostalCode(postalCode string) bool {
	if len(postalCode) < 3 {
		return false
	}
	
	// Check first 3 characters follow Letter-Number-Letter pattern
	firstChar := postalCode[0]
	secondChar := postalCode[1]
	thirdChar := postalCode[2]
	
	// Valid Canadian postal code patterns
	validFirstChars := "ABCEGHJKLMNPRSTVXY" // Canadian postal code first letters
	
	return strings.Contains(validFirstChars, string(firstChar)) &&
		   secondChar >= '0' && secondChar <= '9' &&
		   thirdChar >= 'A' && thirdChar <= 'Z'
}

// executeMultiply implements multiplication function
func (e *FlowExecutor) executeMultiply(function *Function) error {
	log.Printf("Executing multiply function")
	
	// Get values to multiply from context
	values := []float64{}
	
	// Try to get from function parameters or common field names
	for _, field := range []string{"objectValue", "objectHST", "value1", "value2", "amount"} {
		if val := e.getContextValue(field); val != nil {
			if numVal, err := e.convertToFloat(val); err == nil {
				values = append(values, numVal)
			}
		}
	}
	
	// Calculate result
	result := 1.0
	for _, val := range values {
		result *= val
	}
	
	// Store result
	e.context.Variables["multiply_result"] = result
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = result
	
	log.Printf("Multiply function result: %v (from %v)", result, values)
	return nil
}

// executeValidateEmail validates an email address
func (e *FlowExecutor) executeValidateEmail(function *Function) error {
	email := e.getContextValue("email")
	if email == nil {
		email = e.getContextValue("input.email")
	}
	
	valid := false
	if email != nil {
		emailStr := fmt.Sprintf("%v", email)
		// Simple email validation
		valid = strings.Contains(emailStr, "@") && strings.Contains(emailStr, ".")
	}
	
	e.context.Variables["email_valid"] = valid
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = valid
	
	log.Printf("Email validation result: %v", valid)
	return nil
}

// executeCalculateTax calculates tax
func (e *FlowExecutor) executeCalculateTax(function *Function) error {
	amount := e.getContextValue("amount")
	if amount == nil {
		amount = e.getContextValue("input.amount")
	}
	
	var tax float64 = 0
	if amount != nil {
		if amountVal, err := e.convertToFloat(amount); err == nil {
			tax = amountVal * 0.1 // 10% tax rate
		}
	}
	
	e.context.Variables["tax_amount"] = tax
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = tax
	
	log.Printf("Tax calculation result: %v", tax)
	return nil
}

// executeFormatCurrency formats a currency value
func (e *FlowExecutor) executeFormatCurrency(function *Function) error {
	amount := e.getContextValue("amount")
	if amount == nil {
		amount = e.getContextValue("input.amount")
	}
	
	formatted := "$0.00"
	if amount != nil {
		if amountVal, err := e.convertToFloat(amount); err == nil {
			formatted = fmt.Sprintf("$%.2f", amountVal)
		}
	}
	
	e.context.Variables["formatted_currency"] = formatted
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = formatted
	
	log.Printf("Currency formatting result: %v", formatted)
	return nil
}

// executeLogFunction logs a message
func (e *FlowExecutor) executeLogFunction(function *Function) error {
	message := function.Code
	if message == "" {
		message = fmt.Sprintf("Log from function %s", function.Name)
	}
	
	// Template replacement
	for varName, varValue := range e.context.Variables {
		placeholder := fmt.Sprintf("${%s}", varName)
		message = strings.Replace(message, placeholder, fmt.Sprintf("%v", varValue), -1)
	}
	
	log.Printf("[Function Log] %s", message)
	return nil
}

// Helper methods for expression evaluation

// evaluateJavaScriptExpression evaluates a JavaScript-like expression
func (e *FlowExecutor) evaluateJavaScriptExpression(code string) interface{} {
	// Basic JS-like evaluation
	// This is a simplified implementation - real JS engine would be better
	
	// Simple variable substitution
	result := code
	for varName, varValue := range e.context.Variables {
		placeholder := fmt.Sprintf("${%s}", varName)
		result = strings.Replace(result, placeholder, fmt.Sprintf("%v", varValue), -1)
	}
	
	// Basic operations
	if strings.Contains(result, "+") {
		return e.evaluateSimpleArithmetic(result, "+")
	} else if strings.Contains(result, "*") {
		return e.evaluateSimpleArithmetic(result, "*")
	}
	
	return result
}

// evaluateSQLExpression evaluates a SQL-like expression
func (e *FlowExecutor) evaluateSQLExpression(code string) interface{} {
	// Basic SQL simulation
	code = strings.TrimSpace(code)
	
	if strings.HasPrefix(strings.ToUpper(code), "SELECT") {
		// Mock SELECT operation
		return fmt.Sprintf("Result of: %s", code)
	}
	
	// Variable substitution
	result := code
	for varName, varValue := range e.context.Variables {
		placeholder := fmt.Sprintf("${%s}", varName)
		result = strings.Replace(result, placeholder, fmt.Sprintf("%v", varValue), -1)
	}
	
	return result
}

// evaluatePythonExpression evaluates a Python-like expression
func (e *FlowExecutor) evaluatePythonExpression(code string) interface{} {
	// Basic Python-like evaluation
	result := code
	for varName, varValue := range e.context.Variables {
		placeholder := fmt.Sprintf("{%s}", varName)
		result = strings.Replace(result, placeholder, fmt.Sprintf("%v", varValue), -1)
	}
	
	return result
}

// evaluateSimpleArithmetic evaluates simple arithmetic operations
func (e *FlowExecutor) evaluateSimpleArithmetic(expr string, operator string) interface{} {
	parts := strings.Split(expr, operator)
	if len(parts) != 2 {
		return expr
	}
	
	left, err1 := e.convertToFloat(strings.TrimSpace(parts[0]))
	right, err2 := e.convertToFloat(strings.TrimSpace(parts[1]))
	
	if err1 != nil || err2 != nil {
		return expr
	}
	
	switch operator {
	case "+":
		return left + right
	case "*":
		return left * right
	case "-":
		return left - right
	case "/":
		if right != 0 {
			return left / right
		}
		return expr
	default:
		return expr
	}
}

// convertToFloat converts a value to float64
func (e *FlowExecutor) convertToFloat(value interface{}) (float64, error) {
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
		return 0, fmt.Errorf("cannot convert %T to float64", value)
	}
}

// Tax calculation functions for Canadian tax system

// executeGetGST retrieves GST rate for a postal code
func (e *FlowExecutor) executeGetGST(function *Function) error {
	log.Printf("Executing get_gst function")
	
	postalCode := e.getContextValue("postal_code")
	if postalCode == nil {
		postalCode = e.getContextValue("input.postal_code")
	}
	
	var gstRate float64 = 0.0
	if postalCode != nil {
		gstRate = e.getGSTRateForPostalCode(fmt.Sprintf("%v", postalCode))
	}
	
	e.context.Variables["gst_rate"] = gstRate
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = gstRate
	
	log.Printf("GST rate for postal code: %v", gstRate)
	return nil
}

// executeGetHST retrieves HST rate for a postal code
func (e *FlowExecutor) executeGetHST(function *Function) error {
	log.Printf("Executing get_hst function")
	
	postalCode := e.getContextValue("postal_code")
	if postalCode == nil {
		postalCode = e.getContextValue("input.postal_code")
	}
	
	var hstRate float64 = 0.0
	if postalCode != nil {
		hstRate = e.getHSTRateForPostalCode(fmt.Sprintf("%v", postalCode))
	}
	
	e.context.Variables["hst_rate"] = hstRate
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = hstRate
	
	log.Printf("HST rate for postal code: %v", hstRate)
	return nil
}

// executeGetPST retrieves PST rate for a postal code
func (e *FlowExecutor) executeGetPST(function *Function) error {
	log.Printf("Executing get_pst function")
	
	postalCode := e.getContextValue("postal_code")
	if postalCode == nil {
		postalCode = e.getContextValue("input.postal_code")
	}
	
	var pstRate float64 = 0.0
	if postalCode != nil {
		pstRate = e.getPSTRateForPostalCode(fmt.Sprintf("%v", postalCode))
	}
	
	e.context.Variables["pst_rate"] = pstRate
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = pstRate
	
	log.Printf("PST rate for postal code: %v", pstRate)
	return nil
}

// executeGetProvinceFromPincode gets province code from postal code
func (e *FlowExecutor) executeGetProvinceFromPincode(function *Function) error {
	log.Printf("Executing get_province_from_pincode function")
	
	postalCode := e.getContextValue("postal_code")
	if postalCode == nil {
		postalCode = e.getContextValue("input.postal_code")
	}
	
	var provinceCode string = ""
	if postalCode != nil {
		provinceCode = e.getProvinceCodeForPostalCode(fmt.Sprintf("%v", postalCode))
	}
	
	e.context.Variables["province_code"] = provinceCode
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = provinceCode
	
	log.Printf("Province code for postal code: %s", provinceCode)
	return nil
}

// executeCalculateTaxAmount calculates tax amount based on base amount and rate
func (e *FlowExecutor) executeCalculateTaxAmount(function *Function) error {
	log.Printf("Executing calculate_tax_amount function")
	
	baseAmount := e.getContextValue("base_amount")
	if baseAmount == nil {
		baseAmount = e.getContextValue("objectPrice")
	}
	if baseAmount == nil {
		baseAmount = e.getContextValue("input.base_amount")
	}
	
	// Try to get tax rate from various sources
	taxRate := e.getContextValue("tax_rate")
	if taxRate == nil {
		taxRate = e.getContextValue("input.tax_rate")
	}
	
	// If no specific tax_rate provided, calculate total rate from GST+HST+PST
	if taxRate == nil {
		var totalRate float64 = 0.0
		
		if gstRate := e.getContextValue("gst_rate"); gstRate != nil {
			if rate, err := e.convertToFloat(gstRate); err == nil {
				totalRate += rate
			}
		}
		
		if hstRate := e.getContextValue("hst_rate"); hstRate != nil {
			if rate, err := e.convertToFloat(hstRate); err == nil {
				totalRate += rate
			}
		}
		
		if pstRate := e.getContextValue("pst_rate"); pstRate != nil {
			if rate, err := e.convertToFloat(pstRate); err == nil {
				totalRate += rate
			}
		}
		
		taxRate = totalRate
	}
	
	var taxAmount float64 = 0.0
	if baseAmount != nil && taxRate != nil {
		if baseVal, err1 := e.convertToFloat(baseAmount); err1 == nil {
			if rateVal, err2 := e.convertToFloat(taxRate); err2 == nil {
				taxAmount = baseVal * rateVal
				// Round to 2 decimal places (cents)
				taxAmount = float64(int(taxAmount*100+0.5)) / 100
			}
		}
	}
	
	e.context.Variables["tax_amount"] = taxAmount
	e.context.Variables["total_tax"] = taxAmount  // Alternative name
	e.context.Variables[fmt.Sprintf("func_%s_result", function.Name)] = taxAmount
	
	log.Printf("Tax calculation: base=%v, rate=%v, amount=%v", baseAmount, taxRate, taxAmount)
	return nil
}

// Helper functions for tax rate lookup (mock implementation)
// In a real implementation, these would query the external tax database

func (e *FlowExecutor) getGSTRateForPostalCode(postalCode string) float64 {
	// Mock implementation based on Canadian provinces
	// In real implementation, this would query the tax database
	province := e.getProvinceCodeForPostalCode(postalCode)
	
	switch province {
	case "ON", "NB", "NS", "PE", "NL":
		return 0.0 // HST provinces - no separate GST
	default:
		return 0.05 // 5% GST for other provinces
	}
}

func (e *FlowExecutor) getHSTRateForPostalCode(postalCode string) float64 {
	province := e.getProvinceCodeForPostalCode(postalCode)
	
	switch province {
	case "ON":
		return 0.13 // 13% HST
	case "NB", "NS", "PE", "NL":
		return 0.15 // 15% HST
	default:
		return 0.0 // No HST for other provinces
	}
}

func (e *FlowExecutor) getPSTRateForPostalCode(postalCode string) float64 {
	province := e.getProvinceCodeForPostalCode(postalCode)
	
	switch province {
	case "QC":
		return 0.09975 // 9.975% PST
	case "BC", "MB":
		return 0.07 // 7% PST
	case "SK":
		return 0.06 // 6% PST
	default:
		return 0.0 // No PST for other provinces
	}
}

func (e *FlowExecutor) getProvinceCodeForPostalCode(postalCode string) string {
	// Mock implementation - map first character of postal code to province
	// In real implementation, this would query the postal code database
	if len(postalCode) == 0 {
		return ""
	}
	
	firstChar := strings.ToUpper(string(postalCode[0]))
	switch firstChar {
	case "M", "L", "N", "P", "K":
		return "ON" // Ontario
	case "H", "G", "J":
		return "QC" // Quebec
	case "V":
		return "BC" // British Columbia
	case "T":
		return "AB" // Alberta
	case "S":
		return "SK" // Saskatchewan
	case "R":
		return "MB" // Manitoba
	case "E":
		return "NB" // New Brunswick
	case "B":
		return "NS" // Nova Scotia
	case "C":
		return "PE" // Prince Edward Island
	case "A":
		return "NL" // Newfoundland and Labrador
	case "Y":
		return "YT" // Yukon
	case "X":
		return "NT" // Northwest Territories or Nunavut
	default:
		return ""
	}
}