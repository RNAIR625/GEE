package runtime

import (
	"database/sql"
	"fmt"
	"log"
	"math"
	"reflect"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// RuleExecutor handles execution of enhanced rules with expression evaluator functions
type RuleExecutor struct {
	dbConnection *sql.DB
	context      *ExecutionContext
	evaluator    *ExpressionEvaluator
	geeVariables map[string]interface{}
	lookupCache  map[string]interface{}
}

// ExpressionEvaluator integrates the expression evaluation logic
type ExpressionEvaluator struct {
	data    map[string]interface{}
	context map[string]interface{}
	cache   map[string]interface{}
}

// Enhanced rule structure matching our database schema
type EnhancedRule struct {
	RuleID      int                `json:"rule_id"`
	RuleName    string            `json:"rule_name"`
	RuleType    string            `json:"rule_type"`
	Description string            `json:"description"`
	ClassID     int               `json:"class_id"`
	Conditions  []EnhancedRuleLine `json:"conditions"`
	Actions     []EnhancedRuleLine `json:"actions"`
}

// EnhancedRuleLine represents a function call with parameters
type EnhancedRuleLine struct {
	LineID       int                      `json:"line_id"`
	Sequence     int                      `json:"sequence"`
	FunctionID   int                      `json:"function_id"`
	FunctionName string                   `json:"function_name"`
	IsCondition  bool                     `json:"is_condition"`
	Parameters   []EnhancedRuleParameter  `json:"parameters"`
}

// EnhancedRuleParameter represents a parameter with type and value
type EnhancedRuleParameter struct {
	Index          int    `json:"index"`
	Type           string `json:"type"`           // 'literal', 'field', 'variable', 'table_lookup'
	Value          string `json:"value"`
	FieldID        *int   `json:"field_id,omitempty"`
	ExpressionValue *string `json:"expression_value,omitempty"`
}

// FunctionDefinition represents a function available for execution
type FunctionDefinition struct {
	ID           int    `json:"id"`
	Name         string `json:"name"`
	Type         string `json:"type"` // 'CONDITION', 'ACTION', 'UTILITY'
	ParamCount   int    `json:"param_count"`
	Description  string `json:"description"`
	GoCode       string `json:"go_code"`
	ParameterTypes []string `json:"parameter_types"`
	ReturnType   string `json:"return_type"`
}

// NewRuleExecutor creates a new rule executor instance
func NewRuleExecutor(db *sql.DB, context *ExecutionContext) *RuleExecutor {
	executor := &RuleExecutor{
		dbConnection: db,
		context:      context,
		geeVariables: make(map[string]interface{}),
		lookupCache:  make(map[string]interface{}),
	}
	
	// Initialize expression evaluator
	executor.evaluator = &ExpressionEvaluator{
		data:    context.Input,
		context: context.Variables,
		cache:   make(map[string]interface{}),
	}
	
	// Initialize GEE system variables
	executor.initializeGEEVariables()
	
	return executor
}

// initializeGEEVariables sets up system variables
func (re *RuleExecutor) initializeGEEVariables() {
	re.geeVariables["gee_result"] = make(map[string]interface{})
	re.geeVariables["gee_context"] = re.context.Variables
	re.geeVariables["gee_error"] = ""
	re.geeVariables["current_time"] = time.Now().Format(time.RFC3339)
	re.geeVariables["execution_id"] = fmt.Sprintf("exec_%d", time.Now().Unix())
}

// ExecuteRule executes an enhanced rule with conditions and actions
func (re *RuleExecutor) ExecuteRule(rule EnhancedRule) (map[string]interface{}, error) {
	log.Printf("Executing rule: %s (ID: %d)", rule.RuleName, rule.RuleID)
	
	result := map[string]interface{}{
		"rule_id":     rule.RuleID,
		"rule_name":   rule.RuleName,
		"executed_at": time.Now(),
		"conditions":  make([]map[string]interface{}, 0),
		"actions":     make([]map[string]interface{}, 0),
		"success":     false,
	}
	
	// Execute conditions first
	conditionsResult := true
	for _, condition := range rule.Conditions {
		conditionResult, err := re.executeRuleLine(condition, true)
		if err != nil {
			re.geeVariables["gee_error"] = err.Error()
			log.Printf("Condition execution error: %v", err)
			return result, err
		}
		
		// Convert result to boolean
		conditionBool := re.toBool(conditionResult["value"])
		conditionsResult = conditionsResult && conditionBool
		
		result["conditions"] = append(result["conditions"].([]map[string]interface{}), conditionResult)
		
		log.Printf("Condition %s result: %v", condition.FunctionName, conditionBool)
	}
	
	// Only execute actions if all conditions are true (or no conditions)
	if conditionsResult || len(rule.Conditions) == 0 {
		log.Printf("Conditions passed, executing actions")
		
		for _, action := range rule.Actions {
			actionResult, err := re.executeRuleLine(action, false)
			if err != nil {
				re.geeVariables["gee_error"] = err.Error()
				log.Printf("Action execution error: %v", err)
				return result, err
			}
			
			result["actions"] = append(result["actions"].([]map[string]interface{}), actionResult)
			log.Printf("Action %s executed with result: %v", action.FunctionName, actionResult["value"])
		}
		
		result["success"] = true
	} else {
		log.Printf("Conditions failed, skipping actions")
	}
	
	// Update GEE variables
	re.geeVariables["gee_result"] = result
	
	return result, nil
}

// executeRuleLine executes a single rule line (condition or action)
func (re *RuleExecutor) executeRuleLine(line EnhancedRuleLine, isCondition bool) (map[string]interface{}, error) {
	log.Printf("Executing %s: %s", map[bool]string{true: "condition", false: "action"}[isCondition], line.FunctionName)
	
	// Resolve parameters
	params := make([]interface{}, len(line.Parameters))
	for _, param := range line.Parameters {
		if param.Index < len(params) {
			resolvedValue, err := re.resolveParameter(param)
			if err != nil {
				return nil, fmt.Errorf("parameter %d resolution error: %w", param.Index, err)
			}
			params[param.Index] = resolvedValue
		}
	}
	
	// Execute function
	result, err := re.executeFunction(line.FunctionName, params)
	if err != nil {
		return nil, fmt.Errorf("function execution error: %w", err)
	}
	
	return map[string]interface{}{
		"line_id":       line.LineID,
		"function_name": line.FunctionName,
		"parameters":    params,
		"value":         result,
		"executed_at":   time.Now(),
	}, nil
}

// resolveParameter resolves a parameter based on its type
func (re *RuleExecutor) resolveParameter(param EnhancedRuleParameter) (interface{}, error) {
	switch param.Type {
	case "literal":
		return re.parseValue(param.Value), nil
		
	case "field":
		return re.evaluator.ResolveFieldPath(param.Value)
		
	case "variable":
		if value, exists := re.geeVariables[param.Value]; exists {
			return value, nil
		}
		return nil, fmt.Errorf("variable not found: %s", param.Value)
		
	case "table_lookup":
		return re.executeTableLookup(param.Value)
		
	default:
		return param.Value, nil
	}
}

// executeTableLookup processes table lookup expressions
func (re *RuleExecutor) executeTableLookup(expression string) (interface{}, error) {
	// Parse lookup expression: [LOOKUP: table_name WHERE column = value RETURN target_column]
	lookupRegex := regexp.MustCompile(`\[LOOKUP:\s*(\w+)\s+WHERE\s+(\w+)\s*=\s*([^R]+)\s+RETURN\s+(\w+)\]`)
	matches := lookupRegex.FindStringSubmatch(expression)
	
	if len(matches) != 5 {
		return nil, fmt.Errorf("invalid lookup expression: %s", expression)
	}
	
	tableName := strings.TrimSpace(matches[1])
	whereColumn := strings.TrimSpace(matches[2])
	whereValue := strings.TrimSpace(matches[3])
	returnColumn := strings.TrimSpace(matches[4])
	
	// Check cache first
	cacheKey := fmt.Sprintf("%s_%s_%s_%s", tableName, whereColumn, whereValue, returnColumn)
	if cached, exists := re.lookupCache[cacheKey]; exists {
		log.Printf("Lookup cache hit for: %s", cacheKey)
		return cached, nil
	}
	
	// Resolve the where value (could be a field reference)
	resolvedWhereValue := whereValue
	if strings.Contains(whereValue, ".") {
		if resolved, err := re.evaluator.ResolveFieldPath(whereValue); err == nil {
			resolvedWhereValue = fmt.Sprintf("%v", resolved)
		}
	}
	
	// Execute lookup query
	query := fmt.Sprintf("SELECT %s FROM %s WHERE %s = ? LIMIT 1", returnColumn, tableName, whereColumn)
	log.Printf("Executing lookup query: %s with value: %s", query, resolvedWhereValue)
	
	var result interface{}
	err := re.dbConnection.QueryRow(query, resolvedWhereValue).Scan(&result)
	if err != nil {
		if err == sql.ErrNoRows {
			log.Printf("No rows found for lookup: %s", cacheKey)
			return nil, nil
		}
		return nil, fmt.Errorf("lookup query failed: %w", err)
	}
	
	// Cache result
	re.lookupCache[cacheKey] = result
	log.Printf("Lookup result cached: %s = %v", cacheKey, result)
	
	return result, nil
}

// executeFunction executes a function by name with parameters
func (re *RuleExecutor) executeFunction(functionName string, params []interface{}) (interface{}, error) {
	log.Printf("Executing function: %s with %d parameters", functionName, len(params))
	
	switch functionName {
	// Comparison functions
	case "equals":
		if len(params) < 2 {
			return false, fmt.Errorf("equals requires 2 parameters")
		}
		return re.evaluateEquals(params[0], params[1])
		
	case "not_equals":
		if len(params) < 2 {
			return false, fmt.Errorf("not_equals requires 2 parameters")
		}
		equals, err := re.evaluateEquals(params[0], params[1])
		return !equals, err
		
	case "less_than":
		if len(params) < 2 {
			return false, fmt.Errorf("less_than requires 2 parameters")
		}
		return re.evaluateComparison(params[0], params[1], "<")
		
	case "greater_than":
		if len(params) < 2 {
			return false, fmt.Errorf("greater_than requires 2 parameters")
		}
		return re.evaluateComparison(params[0], params[1], ">")
		
	case "less_than_or_equal":
		if len(params) < 2 {
			return false, fmt.Errorf("less_than_or_equal requires 2 parameters")
		}
		return re.evaluateComparison(params[0], params[1], "<=")
		
	case "greater_than_or_equal":
		if len(params) < 2 {
			return false, fmt.Errorf("greater_than_or_equal requires 2 parameters")
		}
		return re.evaluateComparison(params[0], params[1], ">=")
	
	// String functions
	case "contains":
		if len(params) < 2 {
			return false, fmt.Errorf("contains requires 2 parameters")
		}
		return re.evaluateStringContains(params[0], params[1])
		
	case "starts_with":
		if len(params) < 2 {
			return false, fmt.Errorf("starts_with requires 2 parameters")
		}
		return re.evaluateStringStartsWith(params[0], params[1])
		
	case "ends_with":
		if len(params) < 2 {
			return false, fmt.Errorf("ends_with requires 2 parameters")
		}
		return re.evaluateStringEndsWith(params[0], params[1])
		
	case "exists_in":
		if len(params) < 2 {
			return false, fmt.Errorf("exists_in requires 2 parameters")
		}
		return re.evaluateIn(params[0], params[1])
	
	// Arithmetic functions
	case "add":
		if len(params) < 2 {
			return 0, fmt.Errorf("add requires 2 parameters")
		}
		return re.evaluateArithmetic(params[0], params[1], "+")
		
	case "subtract":
		if len(params) < 2 {
			return 0, fmt.Errorf("subtract requires 2 parameters")
		}
		return re.evaluateArithmetic(params[0], params[1], "-")
		
	case "multiply":
		if len(params) < 2 {
			return 0, fmt.Errorf("multiply requires 2 parameters")
		}
		return re.evaluateArithmetic(params[0], params[1], "*")
		
	case "divide":
		if len(params) < 2 {
			return 0, fmt.Errorf("divide requires 2 parameters")
		}
		return re.evaluateArithmetic(params[0], params[1], "/")
		
	case "modulo":
		if len(params) < 2 {
			return 0, fmt.Errorf("modulo requires 2 parameters")
		}
		return re.evaluateArithmetic(params[0], params[1], "%")
		
	case "power":
		if len(params) < 2 {
			return 0, fmt.Errorf("power requires 2 parameters")
		}
		return re.evaluateArithmetic(params[0], params[1], "**")
	
	// String operations
	case "concat":
		if len(params) < 2 {
			return "", fmt.Errorf("concat requires 2 parameters")
		}
		return re.evaluateStringConcat(params[0], params[1])
	
	// Variable operations
	case "set_variable":
		if len(params) < 2 {
			return nil, fmt.Errorf("set_variable requires 2 parameters")
		}
		varName := re.toString(params[0])
		value := params[1]
		re.geeVariables[varName] = value
		log.Printf("Set variable %s = %v", varName, value)
		return value, nil
		
	case "get_variable":
		if len(params) < 1 {
			return nil, fmt.Errorf("get_variable requires 1 parameter")
		}
		varName := re.toString(params[0])
		if value, exists := re.geeVariables[varName]; exists {
			return value, nil
		}
		return nil, fmt.Errorf("variable not found: %s", varName)
	
	// Table functions
	case "table_lookup":
		if len(params) < 3 {
			return nil, fmt.Errorf("table_lookup requires 3 parameters")
		}
		tableName := re.toString(params[0])
		whereClause := re.toString(params[1])
		returnColumn := re.toString(params[2])
		
		// Build lookup expression and execute
		expression := fmt.Sprintf("[LOOKUP: %s WHERE %s RETURN %s]", tableName, whereClause, returnColumn)
		return re.executeTableLookup(expression)
		
	case "table_exists_in":
		if len(params) < 2 {
			return false, fmt.Errorf("table_exists_in requires 2 parameters")
		}
		value := params[0]
		tableColumn := re.toString(params[1])
		
		// Simple exists check - could be enhanced with proper parsing
		query := fmt.Sprintf("SELECT 1 FROM %s WHERE ? = ? LIMIT 1", tableColumn)
		var exists int
		err := re.dbConnection.QueryRow(query, value, value).Scan(&exists)
		return err == nil, nil
		
	default:
		return nil, fmt.Errorf("unknown function: %s", functionName)
	}
}

// Helper methods from expression evaluator (adapted for Go execution)

// parseValue attempts to parse a string value to appropriate type
func (re *RuleExecutor) parseValue(value string) interface{} {
	// Try boolean
	if strings.ToLower(value) == "true" {
		return true
	}
	if strings.ToLower(value) == "false" {
		return false
	}
	
	// Try integer
	if intVal, err := strconv.Atoi(value); err == nil {
		return intVal
	}
	
	// Try float
	if floatVal, err := strconv.ParseFloat(value, 64); err == nil {
		return floatVal
	}
	
	// Return as string
	return value
}

// toBool converts value to boolean
func (re *RuleExecutor) toBool(value interface{}) bool {
	switch v := value.(type) {
	case bool:
		return v
	case string:
		return v != "" && strings.ToLower(v) != "false" && v != "0"
	case int, int64, int32:
		return v != 0
	case float64, float32:
		return v != 0
	case nil:
		return false
	default:
		return true
	}
}

// toString converts value to string
func (re *RuleExecutor) toString(value interface{}) string {
	if value == nil {
		return ""
	}
	return fmt.Sprintf("%v", value)
}

// toNumber converts value to float64
func (re *RuleExecutor) toNumber(value interface{}) (float64, error) {
	switch v := value.(type) {
	case float64:
		return v, nil
	case float32:
		return float64(v), nil
	case int:
		return float64(v), nil
	case int64:
		return float64(v), nil
	case int32:
		return float64(v), nil
	case string:
		if num, err := strconv.ParseFloat(v, 64); err == nil {
			return num, nil
		}
		return 0, fmt.Errorf("cannot convert string '%s' to number", v)
	case bool:
		if v {
			return 1, nil
		}
		return 0, nil
	default:
		return 0, fmt.Errorf("cannot convert %T to number", value)
	}
}

// Evaluation methods (simplified versions of expression_evaluator.go)

func (re *RuleExecutor) evaluateEquals(left, right interface{}) (bool, error) {
	if reflect.DeepEqual(left, right) {
		return true, nil
	}
	
	// Try numeric comparison
	if leftNum, err1 := re.toNumber(left); err1 == nil {
		if rightNum, err2 := re.toNumber(right); err2 == nil {
			return leftNum == rightNum, nil
		}
	}
	
	return re.toString(left) == re.toString(right), nil
}

func (re *RuleExecutor) evaluateComparison(left, right interface{}, operator string) (bool, error) {
	leftNum, leftErr := re.toNumber(left)
	rightNum, rightErr := re.toNumber(right)
	
	if leftErr == nil && rightErr == nil {
		switch operator {
		case "<":
			return leftNum < rightNum, nil
		case "<=":
			return leftNum <= rightNum, nil
		case ">":
			return leftNum > rightNum, nil
		case ">=":
			return leftNum >= rightNum, nil
		}
	}
	
	leftStr := re.toString(left)
	rightStr := re.toString(right)
	
	switch operator {
	case "<":
		return leftStr < rightStr, nil
	case "<=":
		return leftStr <= rightStr, nil
	case ">":
		return leftStr > rightStr, nil
	case ">=":
		return leftStr >= rightStr, nil
	}
	
	return false, fmt.Errorf("cannot compare %T and %T with operator %s", left, right, operator)
}

func (re *RuleExecutor) evaluateStringContains(haystack, needle interface{}) (bool, error) {
	haystackStr := re.toString(haystack)
	needleStr := re.toString(needle)
	return strings.Contains(haystackStr, needleStr), nil
}

func (re *RuleExecutor) evaluateStringStartsWith(str, prefix interface{}) (bool, error) {
	strVal := re.toString(str)
	prefixVal := re.toString(prefix)
	return strings.HasPrefix(strVal, prefixVal), nil
}

func (re *RuleExecutor) evaluateStringEndsWith(str, suffix interface{}) (bool, error) {
	strVal := re.toString(str)
	suffixVal := re.toString(suffix)
	return strings.HasSuffix(strVal, suffixVal), nil
}

func (re *RuleExecutor) evaluateIn(value, collection interface{}) (bool, error) {
	switch coll := collection.(type) {
	case []interface{}:
		for _, item := range coll {
			if equals, err := re.evaluateEquals(value, item); err == nil && equals {
				return true, nil
			}
		}
		return false, nil
	case string:
		items := strings.Split(coll, ",")
		valueStr := re.toString(value)
		for _, item := range items {
			if strings.TrimSpace(item) == valueStr {
				return true, nil
			}
		}
		return false, nil
	default:
		return false, fmt.Errorf("'in' operator requires array or string, got %T", collection)
	}
}

func (re *RuleExecutor) evaluateArithmetic(left, right interface{}, operator string) (interface{}, error) {
	leftNum, err := re.toNumber(left)
	if err != nil {
		return nil, fmt.Errorf("left operand: %w", err)
	}
	
	rightNum, err := re.toNumber(right)
	if err != nil {
		return nil, fmt.Errorf("right operand: %w", err)
	}
	
	switch operator {
	case "+":
		return leftNum + rightNum, nil
	case "-":
		return leftNum - rightNum, nil
	case "*":
		return leftNum * rightNum, nil
	case "/":
		if rightNum == 0 {
			return nil, fmt.Errorf("division by zero")
		}
		return leftNum / rightNum, nil
	case "%":
		if rightNum == 0 {
			return nil, fmt.Errorf("modulo by zero")
		}
		return math.Mod(leftNum, rightNum), nil
	case "**":
		return math.Pow(leftNum, rightNum), nil
	default:
		return nil, fmt.Errorf("unsupported arithmetic operator: %s", operator)
	}
}

func (re *RuleExecutor) evaluateStringConcat(left, right interface{}) (interface{}, error) {
	return re.toString(left) + re.toString(right), nil
}

// ResolveFieldPath resolves nested field paths like "user.profile.email"
func (ev *ExpressionEvaluator) ResolveFieldPath(path string) (interface{}, error) {
	if path == "" {
		return nil, fmt.Errorf("empty field path")
	}
	
	// Check cache first
	if cached, exists := ev.cache[path]; exists {
		return cached, nil
	}
	
	parts := strings.Split(path, ".")
	
	var current interface{}
	var found bool
	
	// Try data first, then context
	if val, exists := ev.data[parts[0]]; exists {
		current = val
		found = true
	} else if val, exists := ev.context[parts[0]]; exists {
		current = val
		found = true
	}
	
	if !found {
		return nil, fmt.Errorf("field not found: %s", parts[0])
	}
	
	// Traverse the path
	for i := 1; i < len(parts); i++ {
		current, found = ev.getNestedValue(current, parts[i])
		if !found {
			return nil, fmt.Errorf("field not found: %s (at %s)", path, strings.Join(parts[:i+1], "."))
		}
	}
	
	// Cache the result
	ev.cache[path] = current
	
	return current, nil
}

// getNestedValue extracts nested value from maps or structs
func (ev *ExpressionEvaluator) getNestedValue(obj interface{}, key string) (interface{}, bool) {
	if obj == nil {
		return nil, false
	}
	
	objValue := reflect.ValueOf(obj)
	
	if objValue.Kind() == reflect.Ptr {
		if objValue.IsNil() {
			return nil, false
		}
		objValue = objValue.Elem()
	}
	
	switch objValue.Kind() {
	case reflect.Map:
		if mapValue, ok := obj.(map[string]interface{}); ok {
			if val, exists := mapValue[key]; exists {
				return val, true
			}
		}
		return nil, false
		
	case reflect.Struct:
		fieldValue := objValue.FieldByName(key)
		if !fieldValue.IsValid() {
			// Try case-insensitive match
			for i := 0; i < objValue.NumField(); i++ {
				field := objValue.Type().Field(i)
				if strings.EqualFold(field.Name, key) {
					return objValue.Field(i).Interface(), true
				}
			}
			return nil, false
		}
		return fieldValue.Interface(), true
		
	case reflect.Slice, reflect.Array:
		if index, err := strconv.Atoi(key); err == nil {
			if index >= 0 && index < objValue.Len() {
				return objValue.Index(index).Interface(), true
			}
		}
		return nil, false
		
	default:
		return nil, false
	}
}

// Public methods for external access

// GetGEEVariables returns the current GEE variables
func (re *RuleExecutor) GetGEEVariables() map[string]interface{} {
	return re.geeVariables
}

// SetGEEVariable sets a GEE variable value
func (re *RuleExecutor) SetGEEVariable(name string, value interface{}) {
	re.geeVariables[name] = value
}

// GetGEEVariable gets a GEE variable value
func (re *RuleExecutor) GetGEEVariable(name string) (interface{}, bool) {
	value, exists := re.geeVariables[name]
	return value, exists
}

// ExecuteFunction exposes the function execution for external calls
func (re *RuleExecutor) ExecuteFunction(functionName string, params []interface{}) (interface{}, error) {
	return re.executeFunction(functionName, params)
}

// ExecuteTableLookup exposes table lookup for external calls
func (re *RuleExecutor) ExecuteTableLookup(expression string) (interface{}, error) {
	return re.executeTableLookup(expression)
}

// GetLookupCache returns the current lookup cache for debugging
func (re *RuleExecutor) GetLookupCache() map[string]interface{} {
	return re.lookupCache
}

// ClearLookupCache clears the lookup cache
func (re *RuleExecutor) ClearLookupCache() {
	re.lookupCache = make(map[string]interface{})
}