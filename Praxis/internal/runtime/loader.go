package runtime

import (
	"database/sql"
	"fmt"
	"log"
	_ "github.com/mattn/go-sqlite3"
)

// RuntimeLoader loads execution data from the runtime database
type RuntimeLoader struct {
	db *sql.DB
}

// Flow represents a deployed flow
type Flow struct {
	ID         int    `json:"flow_id"`
	Name       string `json:"flow_name"`
	Version    string `json:"flow_version"`
	Definition string `json:"flow_definition"`
	IsActive   bool   `json:"is_active"`
}

// Rule represents a runtime rule
type Rule struct {
	ID        int    `json:"rule_id"`
	Name      string `json:"rule_name"`
	Type      string `json:"rule_type"`
	Logic     string `json:"rule_logic"`
	IsActive  bool   `json:"is_active"`
}

// Function represents a runtime function
type Function struct {
	ID         int    `json:"function_id"`
	Name       string `json:"function_name"`
	Type       string `json:"function_type"`
	Code       string `json:"function_code"`
	InputParams string `json:"input_parameters"`
	OutputType string `json:"output_type"`
	IsActive   bool   `json:"is_active"`
}

// NewRuntimeLoader creates a new runtime loader
func NewRuntimeLoader(dbPath string) (*RuntimeLoader, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open runtime database: %w", err)
	}

	// Test connection
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to connect to runtime database: %w", err)
	}

	return &RuntimeLoader{db: db}, nil
}

// Close closes the database connection
func (r *RuntimeLoader) Close() error {
	if r.db != nil {
		return r.db.Close()
	}
	return nil
}

// LoadActiveFlows loads all active flows from the runtime database
func (r *RuntimeLoader) LoadActiveFlows() ([]Flow, error) {
	query := `
		SELECT flow_id, flow_name, flow_version, flow_definition, is_active
		FROM runtime_flows
		WHERE is_active = 1
		ORDER BY flow_id
	`

	rows, err := r.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query flows: %w", err)
	}
	defer rows.Close()

	var flows []Flow
	for rows.Next() {
		var flow Flow
		if err := rows.Scan(&flow.ID, &flow.Name, &flow.Version, &flow.Definition, &flow.IsActive); err != nil {
			log.Printf("Error scanning flow: %v", err)
			continue
		}
		flows = append(flows, flow)
	}

	return flows, nil
}

// LoadFlow loads a specific flow by ID
func (r *RuntimeLoader) LoadFlow(flowID int) (*Flow, error) {
	query := `
		SELECT flow_id, flow_name, flow_version, flow_definition, is_active
		FROM runtime_flows
		WHERE flow_id = ? AND is_active = 1
	`

	var flow Flow
	err := r.db.QueryRow(query, flowID).Scan(
		&flow.ID, &flow.Name, &flow.Version, &flow.Definition, &flow.IsActive,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("flow %d not found or not active", flowID)
		}
		return nil, fmt.Errorf("failed to load flow: %w", err)
	}

	return &flow, nil
}

// LoadRule loads a specific rule by ID
func (r *RuntimeLoader) LoadRule(ruleID int) (*Rule, error) {
	query := `
		SELECT rule_id, rule_name, rule_type, rule_logic, is_active
		FROM runtime_rules
		WHERE rule_id = ? AND is_active = 1
	`

	var rule Rule
	err := r.db.QueryRow(query, ruleID).Scan(
		&rule.ID, &rule.Name, &rule.Type, &rule.Logic, &rule.IsActive,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("rule %d not found or not active", ruleID)
		}
		return nil, fmt.Errorf("failed to load rule: %w", err)
	}

	return &rule, nil
}

// LoadFunction loads a specific function by ID
func (r *RuntimeLoader) LoadFunction(functionID int) (*Function, error) {
	query := `
		SELECT function_id, function_name, function_type, function_code, 
		       input_parameters, output_type, is_active
		FROM runtime_functions
		WHERE function_id = ? AND is_active = 1
	`

	var function Function
	err := r.db.QueryRow(query, functionID).Scan(
		&function.ID, &function.Name, &function.Type, &function.Code,
		&function.InputParams, &function.OutputType, &function.IsActive,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("function %d not found or not active", functionID)
		}
		return nil, fmt.Errorf("failed to load function: %w", err)
	}

	return &function, nil
}

// LoadRuleGroup loads rules for a specific rule group
func (r *RuntimeLoader) LoadRuleGroup(groupID int) ([]Rule, error) {
	query := `
		SELECT r.rule_id, r.rule_name, r.rule_type, r.rule_logic, r.is_active
		FROM runtime_rules r
		JOIN runtime_rule_group_mapping m ON r.rule_id = m.rule_id
		WHERE m.group_id = ? AND m.is_active = 1 AND r.is_active = 1
		ORDER BY m.execution_order
	`

	rows, err := r.db.Query(query, groupID)
	if err != nil {
		return nil, fmt.Errorf("failed to query rule group: %w", err)
	}
	defer rows.Close()

	var rules []Rule
	for rows.Next() {
		var rule Rule
		if err := rows.Scan(&rule.ID, &rule.Name, &rule.Type, &rule.Logic, &rule.IsActive); err != nil {
			log.Printf("Error scanning rule: %v", err)
			continue
		}
		rules = append(rules, rule)
	}

	return rules, nil
}