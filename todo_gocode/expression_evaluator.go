package main

import (
	"fmt"
	"math"
	"reflect"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// Core evaluation types
type Evaluator struct {
	data    map[string]interface{}
	context map[string]interface{}
	cache   map[string]interface{} // Field path resolution cache
}

// Expression represents a complex expression (for future extensions)
type Expression struct {
	Left     interface{} `json:"left"`
	Operator string      `json:"operator"`
	Right    interface{} `json:"right"`
	Type     string      `json:"type,omitempty"`
}

// Condition from the previous schema (reused here)
type Condition struct {
	Field    string      `json:"field"`
	Operator string      `json:"operator"`
	Value    interface{} `json:"value"`
	Type     string      `json:"type,omitempty"`
}

// NewEvaluator creates a new evaluator instance
func NewEvaluator(data, context map[string]interface{}) *Evaluator {
	if data == nil {
		data = make(map[string]interface{})
	}
	if context == nil {
		context = make(map[string]interface{})
	}
	
	return &Evaluator{
		data:    data,
		context: context,
		cache:   make(map[string]interface{}),
	}
}

// EvaluateCondition evaluates a condition and returns a boolean result
func (e *Evaluator) EvaluateCondition(condition Condition) (bool, error) {
	// Resolve the field value
	fieldValue, err := e.ResolveFieldPath(condition.Field)
	if err != nil {
		return false, fmt.Errorf("failed to resolve field '%s': %w", condition.Field, err)
	}
	
	// Handle different operators
	switch condition.Operator {
	case "==":
		return e.evaluateEquals(fieldValue, condition.Value)
	case "!=":
		equals, err := e.evaluateEquals(fieldValue, condition.Value)
		return !equals, err
	case "<":
		return e.evaluateComparison(fieldValue, condition.Value, "<")
	case "<=":
		return e.evaluateComparison(fieldValue, condition.Value, "<=")
	case ">":
		return e.evaluateComparison(fieldValue, condition.Value, ">")
	case ">=":
		return e.evaluateComparison(fieldValue, condition.Value, ">=")
	case "&&":
		return e.evaluateLogicalAnd(fieldValue, condition.Value)
	case "||":
		return e.evaluateLogicalOr(fieldValue, condition.Value)
	case "!":
		return e.evaluateLogicalNot(fieldValue)
	case "contains":
		return e.evaluateStringContains(fieldValue, condition.Value)
	case "starts_with":
		return e.evaluateStringStartsWith(fieldValue, condition.Value)
	case "ends_with":
		return e.evaluateStringEndsWith(fieldValue, condition.Value)
	case "matches":
		return e.evaluateStringMatches(fieldValue, condition.Value)
	case "in":
		return e.evaluateIn(fieldValue, condition.Value)
	default:
		return false, fmt.Errorf("unsupported operator: %s", condition.Operator)
	}
}

// EvaluateExpression evaluates complex expressions (arithmetic, etc.)
func (e *Evaluator) EvaluateExpression(expr Expression) (interface{}, error) {
	// Resolve left operand
	leftValue, err := e.resolveOperand(expr.Left)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve left operand: %w", err)
	}
	
	// Handle unary operators
	if expr.Operator == "!" {
		return e.evaluateLogicalNot(leftValue)
	}
	
	// Resolve right operand for binary operators
	rightValue, err := e.resolveOperand(expr.Right)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve right operand: %w", err)
	}
	
	// Handle arithmetic operators
	switch expr.Operator {
	case "+":
		return e.evaluateArithmetic(leftValue, rightValue, "+")
	case "-":
		return e.evaluateArithmetic(leftValue, rightValue, "-")
	case "*":
		return e.evaluateArithmetic(leftValue, rightValue, "*")
	case "/":
		return e.evaluateArithmetic(leftValue, rightValue, "/")
	case "%":
		return e.evaluateArithmetic(leftValue, rightValue, "%")
	case "**":
		return e.evaluateArithmetic(leftValue, rightValue, "**")
	
	// Comparison operators
	case "==", "!=", "<", "<=", ">", ">=":
		condition := Condition{
			Field:    fmt.Sprintf("%v", expr.Left),
			Operator: expr.Operator,
			Value:    rightValue,
		}
		return e.EvaluateCondition(condition)
	
	// Logical operators with short-circuit evaluation
	case "&&":
		return e.evaluateLogicalAndShortCircuit(leftValue, expr.Right)
	case "||":
		return e.evaluateLogicalOrShortCircuit(leftValue, expr.Right)
	
	// String operations
	case "concat":
		return e.evaluateStringConcat(leftValue, rightValue)
	case "substring":
		return e.evaluateStringSubstring(leftValue, rightValue)
	
	default:
		return nil, fmt.Errorf("unsupported expression operator: %s", expr.Operator)
	}
}

// ResolveFieldPath resolves field paths like "user.profile.age"
func (e *Evaluator) ResolveFieldPath(path string) (interface{}, error) {
	if path == "" {
		return nil, fmt.Errorf("empty field path")
	}
	
	// Check cache first
	if cached, exists := e.cache[path]; exists {
		return cached, nil
	}
	
	// Split the path by dots
	parts := strings.Split(path, ".")
	
	// Start with data or context
	var current interface{}
	var found bool
	
	// Try data first, then context
	if val, exists := e.data[parts[0]]; exists {
		current = val
		found = true
	} else if val, exists := e.context[parts[0]]; exists {
		current = val
		found = true
	}
	
	if !found {
		return nil, fmt.Errorf("field not found: %s", parts[0])
	}
	
	// Traverse the path
	for i := 1; i < len(parts); i++ {
		current, found = e.getNestedValue(current, parts[i])
		if !found {
			return nil, fmt.Errorf("field not found: %s (at %s)", path, strings.Join(parts[:i+1], "."))
		}
	}
	
	// Cache the result
	e.cache[path] = current
	
	return current, nil
}

// Helper function to resolve operands (can be field paths or literal values)
func (e *Evaluator) resolveOperand(operand interface{}) (interface{}, error) {
	switch v := operand.(type) {
	case string:
		// Check if it's a field path (contains dots and not a quoted string)
		if strings.Contains(v, ".") && !strings.HasPrefix(v, "\"") {
			return e.ResolveFieldPath(v)
		}
		return v, nil
	case Expression:
		return e.EvaluateExpression(v)
	default:
		return v, nil
	}
}

// getNestedValue extracts a nested value from maps, structs, or slices
func (e *Evaluator) getNestedValue(obj interface{}, key string) (interface{}, bool) {
	if obj == nil {
		return nil, false
	}
	
	objValue := reflect.ValueOf(obj)
	
	// Handle pointers
	if objValue.Kind() == reflect.Ptr {
		if objValue.IsNil() {
			return nil, false
		}
		objValue = objValue.Elem()
	}
	
	switch objValue.Kind() {
	case reflect.Map:
		mapValue := objValue.Interface().(map[string]interface{})
		if val, exists := mapValue[key]; exists {
			return val, true
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
		// Handle array/slice access by index
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

// Arithmetic evaluation
func (e *Evaluator) evaluateArithmetic(left, right interface{}, operator string) (interface{}, error) {
	leftNum, err := e.toNumber(left)
	if err != nil {
		return nil, fmt.Errorf("left operand: %w", err)
	}
	
	rightNum, err := e.toNumber(right)
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

// Comparison evaluation
func (e *Evaluator) evaluateComparison(left, right interface{}, operator string) (bool, error) {
	// Try numeric comparison first
	leftNum, leftNumErr := e.toNumber(left)
	rightNum, rightNumErr := e.toNumber(right)
	
	if leftNumErr == nil && rightNumErr == nil {
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
	
	// Try string comparison
	leftStr := e.toString(left)
	rightStr := e.toString(right)
	
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

// Equality evaluation with type coercion
func (e *Evaluator) evaluateEquals(left, right interface{}) (bool, error) {
	// Direct comparison
	if reflect.DeepEqual(left, right) {
		return true, nil
	}
	
	// Try numeric comparison
	if leftNum, err1 := e.toNumber(left); err1 == nil {
		if rightNum, err2 := e.toNumber(right); err2 == nil {
			return leftNum == rightNum, nil
		}
	}
	
	// Try string comparison
	return e.toString(left) == e.toString(right), nil
}

// Logical operations with short-circuit evaluation
func (e *Evaluator) evaluateLogicalAndShortCircuit(left interface{}, right interface{}) (interface{}, error) {
	leftBool := e.toBool(left)
	if !leftBool {
		return false, nil // Short-circuit
	}
	
	rightValue, err := e.resolveOperand(right)
	if err != nil {
		return nil, err
	}
	
	return e.toBool(rightValue), nil
}

func (e *Evaluator) evaluateLogicalOrShortCircuit(left interface{}, right interface{}) (interface{}, error) {
	leftBool := e.toBool(left)
	if leftBool {
		return true, nil // Short-circuit
	}
	
	rightValue, err := e.resolveOperand(right)
	if err != nil {
		return nil, err
	}
	
	return e.toBool(rightValue), nil
}

func (e *Evaluator) evaluateLogicalAnd(left, right interface{}) (bool, error) {
	return e.toBool(left) && e.toBool(right), nil
}

func (e *Evaluator) evaluateLogicalOr(left, right interface{}) (bool, error) {
	return e.toBool(left) || e.toBool(right), nil
}

func (e *Evaluator) evaluateLogicalNot(value interface{}) (bool, error) {
	return !e.toBool(value), nil
}

// String operations
func (e *Evaluator) evaluateStringContains(haystack, needle interface{}) (bool, error) {
	haystackStr := e.toString(haystack)
	needleStr := e.toString(needle)
	return strings.Contains(haystackStr, needleStr), nil
}

func (e *Evaluator) evaluateStringStartsWith(str, prefix interface{}) (bool, error) {
	strVal := e.toString(str)
	prefixVal := e.toString(prefix)
	return strings.HasPrefix(strVal, prefixVal), nil
}

func (e *Evaluator) evaluateStringEndsWith(str, suffix interface{}) (bool, error) {
	strVal := e.toString(str)
	suffixVal := e.toString(suffix)
	return strings.HasSuffix(strVal, suffixVal), nil
}

func (e *Evaluator) evaluateStringMatches(str, pattern interface{}) (bool, error) {
	strVal := e.toString(str)
	patternVal := e.toString(pattern)
	
	regex, err := regexp.Compile(patternVal)
	if err != nil {
		return false, fmt.Errorf("invalid regex pattern '%s': %w", patternVal, err)
	}
	
	return regex.MatchString(strVal), nil
}

func (e *Evaluator) evaluateStringConcat(left, right interface{}) (interface{}, error) {
	return e.toString(left) + e.toString(right), nil
}

func (e *Evaluator) evaluateStringSubstring(str, params interface{}) (interface{}, error) {
	strVal := e.toString(str)
	
	// params could be a single index or [start, end]
	switch p := params.(type) {
	case float64:
		start := int(p)
		if start < 0 || start >= len(strVal) {
			return "", fmt.Errorf("substring index out of range: %d", start)
		}
		return strVal[start:], nil
	case []interface{}:
		if len(p) != 2 {
			return "", fmt.Errorf("substring expects [start, end] array")
		}
		
		startNum, err := e.toNumber(p[0])
		if err != nil {
			return "", fmt.Errorf("invalid start index: %w", err)
		}
		
		endNum, err := e.toNumber(p[1])
		if err != nil {
			return "", fmt.Errorf("invalid end index: %w", err)
		}
		
		start, end := int(startNum), int(endNum)
		if start < 0 || end > len(strVal) || start > end {
			return "", fmt.Errorf("invalid substring range: [%d, %d]", start, end)
		}
		
		return strVal[start:end], nil
	default:
		return "", fmt.Errorf("invalid substring parameters: %T", params)
	}
}

// In operation (membership test)
func (e *Evaluator) evaluateIn(value, collection interface{}) (bool, error) {
	switch coll := collection.(type) {
	case []interface{}:
		for _, item := range coll {
			if equals, err := e.evaluateEquals(value, item); err == nil && equals {
				return true, nil
			}
		}
		return false, nil
	case string:
		// Treat as comma-separated values
		items := strings.Split(coll, ",")
		valueStr := e.toString(value)
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

// Type conversion utilities
func (e *Evaluator) toNumber(value interface{}) (float64, error) {
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

func (e *Evaluator) toString(value interface{}) string {
	if value == nil {
		return ""
	}
	
	switch v := value.(type) {
	case string:
		return v
	case fmt.Stringer:
		return v.String()
	default:
		return fmt.Sprintf("%v", value)
	}
}

func (e *Evaluator) toBool(value interface{}) bool {
	switch v := value.(type) {
	case bool:
		return v
	case string:
		return v != "" && strings.ToLower(v) != "false" && v != "0"
	case float64:
		return v != 0
	case int:
		return v != 0
	case nil:
		return false
	default:
		return true
	}
}

// Performance helper: Clear cache
func (e *Evaluator) ClearCache() {
	e.cache = make(map[string]interface{})
}

// Batch evaluation for performance
func (e *Evaluator) EvaluateConditions(conditions []Condition) ([]bool, error) {
	results := make([]bool, len(conditions))
	for i, condition := range conditions {
		result, err := e.EvaluateCondition(condition)
		if err != nil {
			return nil, fmt.Errorf("condition %d: %w", i, err)
		}
		results[i] = result
	}
	return results, nil
}

// Example usage and benchmark
func main() {
	// Test data
	data := map[string]interface{}{
		"user": map[string]interface{}{
			"name": "John Doe",
			"age":  30,
			"profile": map[string]interface{}{
				"email": "john@example.com",
				"preferences": map[string]interface{}{
					"theme": "dark",
					"notifications": true,
				},
			},
			"roles": []interface{}{"admin", "user"},
		},
		"product": map[string]interface{}{
			"price": 99.99,
			"category": "electronics",
		},
	}
	
	context := map[string]interface{}{
		"current_time": time.Now(),
		"version":      "1.0.0",
	}
	
	evaluator := NewEvaluator(data, context)
	
	// Test cases
	testCases := []struct {
		name      string
		condition Condition
		expected  bool
	}{
		{
			name: "Simple comparison",
			condition: Condition{
				Field:    "user.age",
				Operator: ">=",
				Value:    18,
			},
			expected: true,
		},
		{
			name: "String contains",
			condition: Condition{
				Field:    "user.name",
				Operator: "contains",
				Value:    "John",
			},
			expected: true,
		},
		{
			name: "Nested field access",
			condition: Condition{
				Field:    "user.profile.preferences.theme",
				Operator: "==",
				Value:    "dark",
			},
			expected: true,
		},
		{
			name: "In operation",
			condition: Condition{
				Field:    "user.profile.preferences.theme",
				Operator: "in",
				Value:    []interface{}{"light", "dark", "auto"},
			},
			expected: true,
		},
		{
			name: "Regex match",
			condition: Condition{
				Field:    "user.profile.email",
				Operator: "matches",
				Value:    `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`,
			},
			expected: true,
		},
	}
	
	// Run test cases
	fmt.Println("Running Expression Evaluator Tests:")
	fmt.Println("====================================")
	
	for _, tc := range testCases {
		start := time.Now()
		result, err := evaluator.EvaluateCondition(tc.condition)
		duration := time.Since(start)
		
		fmt.Printf("Test: %s\n", tc.name)
		fmt.Printf("  Field: %s %s %v\n", tc.condition.Field, tc.condition.Operator, tc.condition.Value)
		fmt.Printf("  Result: %v (expected: %v)\n", result, tc.expected)
		fmt.Printf("  Duration: %v\n", duration)
		fmt.Printf("  Status: ")
		
		if err != nil {
			fmt.Printf("ERROR - %v\n", err)
		} else if result == tc.expected {
			fmt.Printf("PASS\n")
		} else {
			fmt.Printf("FAIL\n")
		}
		fmt.Println()
	}
	
	// Test arithmetic expression
	expr := Expression{
		Left:     "user.age",
		Operator: "+",
		Right:    5,
	}
	
	result, err := evaluator.EvaluateExpression(expr)
	if err != nil {
		fmt.Printf("Expression evaluation error: %v\n", err)
	} else {
		fmt.Printf("Arithmetic expression result: %v\n", result)
	}
}