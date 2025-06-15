package runtime

import (
	"database/sql"
	"fmt"
	"log"
	"time"
)

// EnhancedFlowExecutor extends the existing flow executor with rule execution capabilities
type EnhancedFlowExecutor struct {
	*FlowExecutor
	ruleExecutor *RuleExecutor
	dbConnection *sql.DB
}

// NewEnhancedFlowExecutor creates an enhanced flow executor with rule capabilities
func NewEnhancedFlowExecutor(db *sql.DB) *EnhancedFlowExecutor {
	baseExecutor := &FlowExecutor{
		// Initialize base executor fields if needed
	}
	
	return &EnhancedFlowExecutor{
		FlowExecutor: baseExecutor,
		dbConnection: db,
	}
}

// ExecuteFlowWithRules executes a flow with enhanced rule support
func (efe *EnhancedFlowExecutor) ExecuteFlowWithRules(flowDefinition FlowDefinition, inputData map[string]interface{}) (*ExecutionResult, error) {
	log.Printf("Starting enhanced flow execution: %s", flowDefinition.FlowName)
	
	// Create execution context
	context := &ExecutionContext{
		Input:     inputData,
		Variables: make(map[string]interface{}),
		Output:    make(map[string]interface{}),
		Errors:    make([]string, 0),
		StartTime: time.Now(),
	}
	
	// Initialize rule executor
	efe.ruleExecutor = NewRuleExecutor(efe.dbConnection, context)
	
	result := &ExecutionResult{
		FlowID:      flowDefinition.FlowID,
		FlowName:    flowDefinition.FlowName,
		StartTime:   context.StartTime,
		Success:     false,
		Steps:       make([]StepResult, 0),
		FinalOutput: make(map[string]interface{}),
	}
	
	// Execute flow nodes
	for _, nodeID := range flowDefinition.StartNodes {
		nodeResult, err := efe.executeNode(nodeID, flowDefinition, context)
		if err != nil {
			result.Errors = append(result.Errors, err.Error())
			log.Printf("Node execution error: %v", err)
			continue
		}
		
		result.Steps = append(result.Steps, *nodeResult)
	}
	
	// Set final results
	result.EndTime = time.Now()
	result.Duration = result.EndTime.Sub(result.StartTime)
	result.Success = len(result.Errors) == 0
	result.FinalOutput = context.Output
	result.GEEVariables = efe.ruleExecutor.geeVariables
	
	log.Printf("Enhanced flow execution completed. Success: %v, Duration: %v", result.Success, result.Duration)
	
	return result, nil
}

// executeNode executes a single flow node
func (efe *EnhancedFlowExecutor) executeNode(nodeID string, flow FlowDefinition, context *ExecutionContext) (*StepResult, error) {
	node, exists := flow.Nodes[nodeID]
	if !exists {
		return nil, fmt.Errorf("node not found: %s", nodeID)
	}
	
	log.Printf("Executing node: %s (type: %s)", nodeID, node.Type)
	
	stepResult := &StepResult{
		NodeID:    nodeID,
		NodeType:  node.Type,
		StartTime: time.Now(),
		Success:   false,
	}
	
	switch node.Type {
	case "rule":
		result, err := efe.executeRuleNode(node, flow, context)
		stepResult.Output = result
		stepResult.Error = err
		stepResult.Success = err == nil
		
	case "rule_group":
		result, err := efe.executeRuleGroupNode(node, flow, context)
		stepResult.Output = result
		stepResult.Error = err
		stepResult.Success = err == nil
		
	case "function":
		result, err := efe.executeFunctionNode(node, flow, context)
		stepResult.Output = result
		stepResult.Error = err
		stepResult.Success = err == nil
		
	default:
		// Fallback to base executor for other node types
		err := fmt.Errorf("unsupported node type: %s", node.Type)
		stepResult.Error = err
		log.Printf("Unsupported node type: %s", node.Type)
	}
	
	stepResult.EndTime = time.Now()
	stepResult.Duration = stepResult.EndTime.Sub(stepResult.StartTime)
	
	return stepResult, stepResult.Error
}

// executeRuleNode executes a rule node
func (efe *EnhancedFlowExecutor) executeRuleNode(node NodeDefinition, flow FlowDefinition, context *ExecutionContext) (map[string]interface{}, error) {
	ruleID := node.ReferenceID
	
	// Load rule from database
	rule, err := efe.loadEnhancedRule(ruleID)
	if err != nil {
		return nil, fmt.Errorf("failed to load rule %d: %w", ruleID, err)
	}
	
	// Execute rule
	result, err := efe.ruleExecutor.ExecuteRule(*rule)
	if err != nil {
		return nil, fmt.Errorf("rule execution failed: %w", err)
	}
	
	// Update context with rule results
	if result["success"].(bool) {
		// Rule succeeded, continue to next nodes
		for _, connection := range flow.Connections[node.ID] {
			// Could implement conditional connections here
			log.Printf("Rule succeeded, could continue to: %s", connection.Target)
		}
	}
	
	return result, nil
}

// executeRuleGroupNode executes a rule group node
func (efe *EnhancedFlowExecutor) executeRuleGroupNode(node NodeDefinition, flow FlowDefinition, context *ExecutionContext) (map[string]interface{}, error) {
	groupID := node.ReferenceID
	
	// Load rule group from database
	rules, err := efe.loadRuleGroup(groupID)
	if err != nil {
		return nil, fmt.Errorf("failed to load rule group %d: %w", groupID, err)
	}
	
	groupResult := map[string]interface{}{
		"group_id":      groupID,
		"executed_at":   time.Now(),
		"rule_results":  make([]map[string]interface{}, 0),
		"success_count": 0,
		"total_count":   len(rules),
	}
	
	successCount := 0
	for _, rule := range rules {
		result, err := efe.ruleExecutor.ExecuteRule(rule)
		if err != nil {
			log.Printf("Rule %d execution failed: %v", rule.RuleID, err)
			continue
		}
		
		groupResult["rule_results"] = append(groupResult["rule_results"].([]map[string]interface{}), result)
		
		if result["success"].(bool) {
			successCount++
		}
	}
	
	groupResult["success_count"] = successCount
	groupResult["success"] = successCount > 0 // At least one rule succeeded
	
	return groupResult, nil
}

// executeFunctionNode executes a function node
func (efe *EnhancedFlowExecutor) executeFunctionNode(node NodeDefinition, flow FlowDefinition, context *ExecutionContext) (map[string]interface{}, error) {
	functionID := node.ReferenceID
	
	// Load function definition
	functionDef, exists := flow.Functions[fmt.Sprintf("%d", functionID)]
	if !exists {
		return nil, fmt.Errorf("function not found: %d", functionID)
	}
	
	// Prepare parameters from node properties
	params := make([]interface{}, 0)
	if properties, ok := node.Properties["parameters"].([]interface{}); ok {
		for _, param := range properties {
			// Resolve parameter values
			resolvedParam := efe.resolveNodeParameter(param, context)
			params = append(params, resolvedParam)
		}
	}
	
	// Execute function
	result, err := efe.ruleExecutor.executeFunction(functionDef.Name, params)
	if err != nil {
		return nil, err
	}
	
	return map[string]interface{}{
		"function_id":   functionID,
		"function_name": functionDef.Name,
		"result":        result,
		"executed_at":   time.Now(),
	}, nil
}

// loadEnhancedRule loads a rule from the database
func (efe *EnhancedFlowExecutor) loadEnhancedRule(ruleID int) (*EnhancedRule, error) {
	// Load rule basic info
	ruleQuery := `
		SELECT r.RULE_ID, r.RULE_NAME, r.RULE_TYPE, r.DESCRIPTION, r.GFC_ID
		FROM GEE_RULES r
		WHERE r.RULE_ID = ?
	`
	
	var rule EnhancedRule
	err := efe.dbConnection.QueryRow(ruleQuery, ruleID).Scan(
		&rule.RuleID, &rule.RuleName, &rule.RuleType, &rule.Description, &rule.ClassID,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load rule: %w", err)
	}
	
	// Load rule lines
	linesQuery := `
		SELECT rl.LINE_ID, rl.SEQUENCE_NUM, rl.FUNCTION_ID, rl.IS_CONDITION,
		       f.FUNC_NAME
		FROM GEE_RULE_LINES rl
		JOIN GEE_BASE_FUNCTIONS f ON rl.FUNCTION_ID = f.GBF_ID
		WHERE rl.RULE_ID = ?
		ORDER BY rl.SEQUENCE_NUM
	`
	
	rows, err := efe.dbConnection.Query(linesQuery, ruleID)
	if err != nil {
		return nil, fmt.Errorf("failed to load rule lines: %w", err)
	}
	defer rows.Close()
	
	for rows.Next() {
		var line EnhancedRuleLine
		err := rows.Scan(&line.LineID, &line.Sequence, &line.FunctionID, &line.IsCondition, &line.FunctionName)
		if err != nil {
			return nil, fmt.Errorf("failed to scan rule line: %w", err)
		}
		
		// Load parameters for this line
		line.Parameters, err = efe.loadRuleLineParameters(line.LineID)
		if err != nil {
			return nil, fmt.Errorf("failed to load parameters for line %d: %w", line.LineID, err)
		}
		
		if line.IsCondition {
			rule.Conditions = append(rule.Conditions, line)
		} else {
			rule.Actions = append(rule.Actions, line)
		}
	}
	
	return &rule, nil
}

// loadRuleLineParameters loads parameters for a rule line
func (efe *EnhancedFlowExecutor) loadRuleLineParameters(lineID int) ([]EnhancedRuleParameter, error) {
	query := `
		SELECT PARAM_INDEX, FIELD_ID, LITERAL_VALUE, PARAMETER_TYPE, EXPRESSION_VALUE
		FROM GEE_RULE_LINE_PARAMS
		WHERE LINE_ID = ?
		ORDER BY PARAM_INDEX
	`
	
	rows, err := efe.dbConnection.Query(query, lineID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	
	var parameters []EnhancedRuleParameter
	for rows.Next() {
		var param EnhancedRuleParameter
		var fieldID sql.NullInt64
		var literalValue sql.NullString
		var parameterType sql.NullString
		var expressionValue sql.NullString
		
		err := rows.Scan(&param.Index, &fieldID, &literalValue, &parameterType, &expressionValue)
		if err != nil {
			return nil, err
		}
		
		if fieldID.Valid {
			fieldIDInt := int(fieldID.Int64)
			param.FieldID = &fieldIDInt
		}
		
		if literalValue.Valid {
			param.Value = literalValue.String
		}
		
		if parameterType.Valid {
			param.Type = parameterType.String
		} else {
			param.Type = "literal"
		}
		
		if expressionValue.Valid {
			param.ExpressionValue = &expressionValue.String
		}
		
		parameters = append(parameters, param)
	}
	
	return parameters, nil
}

// loadRuleGroup loads all rules in a rule group
func (efe *EnhancedFlowExecutor) loadRuleGroup(groupID int) ([]EnhancedRule, error) {
	// Get rule IDs in group
	groupQuery := `
		SELECT grr.RULE_ID
		FROM GRG_RULE_GROUP_RULES grr
		WHERE grr.GRG_ID = ?
		ORDER BY grr.SEQUENCE
	`
	
	rows, err := efe.dbConnection.Query(groupQuery, groupID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	
	var rules []EnhancedRule
	for rows.Next() {
		var ruleID int
		err := rows.Scan(&ruleID)
		if err != nil {
			return nil, err
		}
		
		rule, err := efe.loadEnhancedRule(ruleID)
		if err != nil {
			log.Printf("Failed to load rule %d in group %d: %v", ruleID, groupID, err)
			continue
		}
		
		rules = append(rules, *rule)
	}
	
	return rules, nil
}

// resolveNodeParameter resolves parameter values for function nodes
func (efe *EnhancedFlowExecutor) resolveNodeParameter(param interface{}, context *ExecutionContext) interface{} {
	if paramMap, ok := param.(map[string]interface{}); ok {
		if paramType, exists := paramMap["type"]; exists && paramType == "field" {
			if fieldPath, exists := paramMap["value"]; exists {
				if resolved, err := efe.ruleExecutor.evaluator.ResolveFieldPath(fieldPath.(string)); err == nil {
					return resolved
				}
			}
		}
		if value, exists := paramMap["value"]; exists {
			return value
		}
	}
	return param
}

// ExecutionResult represents the result of enhanced flow execution
type ExecutionResult struct {
	FlowID       int                    `json:"flow_id"`
	FlowName     string                 `json:"flow_name"`
	StartTime    time.Time              `json:"start_time"`
	EndTime      time.Time              `json:"end_time"`
	Duration     time.Duration          `json:"duration"`
	Success      bool                   `json:"success"`
	Steps        []StepResult           `json:"steps"`
	Errors       []string               `json:"errors"`
	FinalOutput  map[string]interface{} `json:"final_output"`
	GEEVariables map[string]interface{} `json:"gee_variables"`
}

// StepResult represents the result of executing a single step/node
type StepResult struct {
	NodeID    string                 `json:"node_id"`
	NodeType  string                 `json:"node_type"`
	StartTime time.Time              `json:"start_time"`
	EndTime   time.Time              `json:"end_time"`
	Duration  time.Duration          `json:"duration"`
	Success   bool                   `json:"success"`
	Output    map[string]interface{} `json:"output"`
	Error     error                  `json:"error,omitempty"`
}