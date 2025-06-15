package main

import (
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strings"
)

// Core types
type RuleSet struct {
	ID               string                     `json:"ruleset_id"`
	Rules            []Rule                     `json:"rules"`
	ExternalServices map[string]ServiceConfig   `json:"external_services,omitempty"`
}

type Rule struct {
	ID        string    `json:"id,omitempty"`
	Priority  int       `json:"priority"`
	Condition Condition `json:"condition"`
	Actions   []Action  `json:"actions"`
}

type Condition struct {
	Field    string      `json:"field"`
	Operator string      `json:"operator"`
	Value    interface{} `json:"value"`
	Type     string      `json:"type,omitempty"` // field type hint
}

type Action struct {
	Type   string                 `json:"type"`
	Target string                 `json:"target,omitempty"`
	Params map[string]interface{} `json:"params,omitempty"`
}

type ServiceConfig struct {
	URL     string            `json:"url"`
	Headers map[string]string `json:"headers,omitempty"`
	Auth    AuthConfig        `json:"auth,omitempty"`
}

type AuthConfig struct {
	Type   string `json:"type"`   // "bearer", "basic", "api_key"
	Token  string `json:"token,omitempty"`
	Header string `json:"header,omitempty"`
}

// Supported operators
var (
	ArithmeticOperators = []string{"+", "-", "*", "/", "%", "**"}
	ComparisonOperators = []string{"==", "!=", "<", "<=", ">", ">="}
	LogicalOperators    = []string{"&&", "||", "!"}
	StringOperators     = []string{"contains", "starts_with", "ends_with", "matches", "in"}
	AllOperators        = append(append(append(ArithmeticOperators, ComparisonOperators...), LogicalOperators...), StringOperators...)
)

// Action types
var ValidActionTypes = []string{
	"log", "email", "webhook", "database", "transform", "filter", "alert", "external_service",
}

// ParseRuleSet parses JSON data into a RuleSet struct
func ParseRuleSet(jsonData []byte) (*RuleSet, error) {
	var rs RuleSet
	
	// Parse JSON
	if err := json.Unmarshal(jsonData, &rs); err != nil {
		return nil, fmt.Errorf("failed to parse JSON: %w", err)
	}
	
	// Validate the parsed ruleset
	if err := ValidateRuleSet(&rs); err != nil {
		return nil, fmt.Errorf("validation failed: %w", err)
	}
	
	// Sort rules by priority
	rs.SortByPriority()
	
	return &rs, nil
}

// ValidateRuleSet validates the entire ruleset
func ValidateRuleSet(rs *RuleSet) error {
	if rs == nil {
		return fmt.Errorf("ruleset cannot be nil")
	}
	
	// Validate ruleset ID
	if strings.TrimSpace(rs.ID) == "" {
		return fmt.Errorf("ruleset_id is required and cannot be empty")
	}
	
	// Validate rules exist
	if len(rs.Rules) == 0 {
		return fmt.Errorf("at least one rule is required")
	}
	
	// Validate each rule
	ruleIDs := make(map[string]bool)
	for i, rule := range rs.Rules {
		if err := validateRule(rule, i); err != nil {
			return fmt.Errorf("rule at index %d: %w", i, err)
		}
		
		// Check for duplicate rule IDs (if provided)
		if rule.ID != "" {
			if ruleIDs[rule.ID] {
				return fmt.Errorf("duplicate rule ID: %s", rule.ID)
			}
			ruleIDs[rule.ID] = true
		}
	}
	
	// Validate external services
	if err := validateExternalServices(rs.ExternalServices); err != nil {
		return fmt.Errorf("external services validation failed: %w", err)
	}
	
	return nil
}

// validateRule validates a single rule
func validateRule(rule Rule, index int) error {
	// Validate priority (should be positive)
	if rule.Priority <= 0 {
		return fmt.Errorf("priority must be positive, got %d", rule.Priority)
	}
	
	// Validate condition
	if err := validateCondition(rule.Condition); err != nil {
		return fmt.Errorf("condition validation failed: %w", err)
	}
	
	// Validate actions
	if len(rule.Actions) == 0 {
		return fmt.Errorf("at least one action is required")
	}
	
	for i, action := range rule.Actions {
		if err := validateAction(action); err != nil {
			return fmt.Errorf("action at index %d: %w", i, err)
		}
	}
	
	return nil
}

// validateCondition validates a condition
func validateCondition(condition Condition) error {
	// Validate field
	if strings.TrimSpace(condition.Field) == "" {
		return fmt.Errorf("field is required and cannot be empty")
	}
	
	// Validate operator
	if !isValidOperator(condition.Operator) {
		return fmt.Errorf("invalid operator '%s', supported operators: %v", condition.Operator, AllOperators)
	}
	
	// Validate value exists (can be nil for some operations)
	if condition.Value == nil && !isNilValueAllowed(condition.Operator) {
		return fmt.Errorf("value is required for operator '%s'", condition.Operator)
	}
	
	// Validate operator-value compatibility
	if err := validateOperatorValue(condition.Operator, condition.Value); err != nil {
		return fmt.Errorf("operator-value validation failed: %w", err)
	}
	
	return nil
}

// validateAction validates an action
func validateAction(action Action) error {
	// Validate action type
	if !isValidActionType(action.Type) {
		return fmt.Errorf("invalid action type '%s', supported types: %v", action.Type, ValidActionTypes)
	}
	
	// Type-specific validation
	switch action.Type {
	case "email":
		if action.Target == "" {
			return fmt.Errorf("email action requires target (recipient)")
		}
		if !isValidEmail(action.Target) {
			return fmt.Errorf("invalid email address: %s", action.Target)
		}
	case "webhook":
		if action.Target == "" {
			return fmt.Errorf("webhook action requires target (URL)")
		}
		if !isValidURL(action.Target) {
			return fmt.Errorf("invalid webhook URL: %s", action.Target)
		}
	case "external_service":
		if action.Target == "" {
			return fmt.Errorf("external_service action requires target (service name)")
		}
	}
	
	return nil
}

// validateExternalServices validates external service configurations
func validateExternalServices(services map[string]ServiceConfig) error {
	for name, config := range services {
		if strings.TrimSpace(name) == "" {
			return fmt.Errorf("service name cannot be empty")
		}
		
		if strings.TrimSpace(config.URL) == "" {
			return fmt.Errorf("service '%s' URL is required", name)
		}
		
		if !isValidURL(config.URL) {
			return fmt.Errorf("service '%s' has invalid URL: %s", name, config.URL)
		}
		
		// Validate auth config if present
		if config.Auth.Type != "" {
			if err := validateAuthConfig(config.Auth, name); err != nil {
				return err
			}
		}
	}
	
	return nil
}

// validateAuthConfig validates authentication configuration
func validateAuthConfig(auth AuthConfig, serviceName string) error {
	validAuthTypes := []string{"bearer", "basic", "api_key"}
	
	found := false
	for _, validType := range validAuthTypes {
		if auth.Type == validType {
			found = true
			break
		}
	}
	
	if !found {
		return fmt.Errorf("service '%s' has invalid auth type '%s', supported: %v", serviceName, auth.Type, validAuthTypes)
	}
	
	if auth.Type == "api_key" && strings.TrimSpace(auth.Header) == "" {
		return fmt.Errorf("service '%s' with api_key auth requires header field", serviceName)
	}
	
	return nil
}

// SortByPriority sorts rules by priority (ascending order)
func (rs *RuleSet) SortByPriority() {
	sort.Slice(rs.Rules, func(i, j int) bool {
		return rs.Rules[i].Priority < rs.Rules[j].Priority
	})
}

// Helper functions
func isValidOperator(op string) bool {
	for _, validOp := range AllOperators {
		if op == validOp {
			return true
		}
	}
	return false
}

func isValidActionType(actionType string) bool {
	for _, validType := range ValidActionTypes {
		if actionType == validType {
			return true
		}
	}
	return false
}

func isNilValueAllowed(operator string) bool {
	// Operators that might work with nil values
	return operator == "!" || operator == "==" || operator == "!="
}

func validateOperatorValue(operator string, value interface{}) error {
	if value == nil {
		return nil // Already checked in isNilValueAllowed
	}
	
	switch operator {
	case "contains", "starts_with", "ends_with", "matches":
		if _, ok := value.(string); !ok {
			return fmt.Errorf("string operators require string values, got %T", value)
		}
	case "in":
		// Value should be an array
		switch v := value.(type) {
		case []interface{}:
			// Valid
		case string:
			// Allow comma-separated string for convenience
		default:
			return fmt.Errorf("'in' operator requires array or comma-separated string, got %T", v)
		}
	case "matches":
		if str, ok := value.(string); ok {
			if _, err := regexp.Compile(str); err != nil {
				return fmt.Errorf("invalid regex pattern: %w", err)
			}
		}
	}
	
	return nil
}

func isValidEmail(email string) bool {
	emailRegex := regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)
	return emailRegex.MatchString(email)
}

func isValidURL(url string) bool {
	return strings.HasPrefix(url, "http://") || strings.HasPrefix(url, "https://")
}

// Additional utility methods
func (rs *RuleSet) GetRuleByID(id string) *Rule {
	for i := range rs.Rules {
		if rs.Rules[i].ID == id {
			return &rs.Rules[i]
		}
	}
	return nil
}

func (rs *RuleSet) GetRulesByPriority(priority int) []Rule {
	var rules []Rule
	for _, rule := range rs.Rules {
		if rule.Priority == priority {
			rules = append(rules, rule)
		}
	}
	return rules
}

func (rs *RuleSet) ToJSON() ([]byte, error) {
	return json.MarshalIndent(rs, "", "  ")
}

// Example usage and test function
func main() {
	// Example JSON input
	jsonInput := `{
		"ruleset_id": "user_validation_rules",
		"rules": [
			{
				"id": "age_check",
				"priority": 1,
				"condition": {
					"field": "user.age",
					"operator": ">=",
					"value": 18,
					"type": "number"
				},
				"actions": [
					{
						"type": "log",
						"params": {
							"message": "User is adult",
							"level": "info"
						}
					}
				]
			},
			{
				"id": "email_validation",
				"priority": 2,
				"condition": {
					"field": "user.email",
					"operator": "matches",
					"value": "^[\\w\\.-]+@[\\w\\.-]+\\.[a-zA-Z]{2,}$",
					"type": "string"
				},
				"actions": [
					{
						"type": "email",
						"target": "admin@example.com",
						"params": {
							"subject": "New user registered",
							"template": "welcome"
						}
					}
				]
			}
		],
		"external_services": {
			"notification_service": {
				"url": "https://api.notifications.com/send",
				"headers": {
					"Content-Type": "application/json"
				},
				"auth": {
					"type": "bearer",
					"token": "your-token-here"
				}
			}
		}
	}`
	
	// Parse and validate
	ruleset, err := ParseRuleSet([]byte(jsonInput))
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	
	fmt.Printf("Successfully parsed ruleset: %s\n", ruleset.ID)
	fmt.Printf("Number of rules: %d\n", len(ruleset.Rules))
	fmt.Printf("Rules sorted by priority:\n")
	
	for _, rule := range ruleset.Rules {
		fmt.Printf("  - Rule ID: %s, Priority: %d, Field: %s, Operator: %s\n",
			rule.ID, rule.Priority, rule.Condition.Field, rule.Condition.Operator)
	}
	
	// Test validation with invalid input
	invalidInput := `{
		"ruleset_id": "",
		"rules": []
	}`
	
	_, err = ParseRuleSet([]byte(invalidInput))
	if err != nil {
		fmt.Printf("\nExpected validation error for invalid input: %v\n", err)
	}
}