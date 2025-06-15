package runtime

import (
	"database/sql"
	"fmt"
	"log"
	"path/filepath"
	"sync"
	"time"

	"github.com/praxis/internal/models"
	_ "github.com/mattn/go-sqlite3"
)

// ForgeLoader loads data from Forge's GEE.db database
type ForgeLoader struct {
	db           *sql.DB
	dbPath       string
	lastUpdated  time.Time
	updateMutex  sync.RWMutex
}

// NewForgeLoader creates a new Forge database loader
func NewForgeLoader(forgePath string) (*ForgeLoader, error) {
	// Construct path to Forge's GEE.db
	geePath := filepath.Join(forgePath, "instance", "GEE.db")
	
	db, err := sql.Open("sqlite3", geePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open Forge database at %s: %w", geePath, err)
	}

	// Test connection
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to connect to Forge database: %w", err)
	}

	log.Printf("Connected to Forge database: %s", geePath)
	
	return &ForgeLoader{
		db:     db,
		dbPath: geePath,
	}, nil
}

// Close closes the database connection
func (f *ForgeLoader) Close() error {
	if f.db != nil {
		return f.db.Close()
	}
	return nil
}

// LoadTables loads all tables from Forge
func (f *ForgeLoader) LoadTables() ([]models.Table, error) {
	query := `
		SELECT GEC_ID, TABLE_NAME, TABLE_TYPE, QUERY, DESCRIPTION, 
		       DB_TYPE, SOURCE_CONNECTION_HANDLE, CREATE_DATE, UPDATE_DATE
		FROM GEE_TABLES
		WHERE TABLE_TYPE = 'I'  -- Only imported tables
		ORDER BY TABLE_NAME
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query tables: %w", err)
	}
	defer rows.Close()

	var tables []models.Table
	for rows.Next() {
		var table models.Table
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&table.ID, &table.TableName, &table.TableType, &table.Query,
			&table.Description, &table.DBType, &table.SourceConnectionHandle,
			&table.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning table: %v", err)
			continue
		}
		
		if updateDate.Valid {
			table.UpdateDate = &updateDate.Time
		}
		
		tables = append(tables, table)
	}

	log.Printf("Loaded %d tables from Forge", len(tables))
	return tables, nil
}

// LoadTableColumns loads all table columns from Forge
func (f *ForgeLoader) LoadTableColumns() ([]models.TableColumn, error) {
	query := `
		SELECT COLUMN_ID, GEC_ID, COLUMN_NAME, DATA_TYPE, DATA_LENGTH,
		       DATA_PRECISION, DATA_SCALE, IS_NULLABLE, IS_PRIMARY_KEY,
		       IS_FOREIGN_KEY, DEFAULT_VALUE, COLUMN_POSITION
		FROM GEE_TABLE_COLUMNS
		ORDER BY GEC_ID, COLUMN_POSITION
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query table columns: %w", err)
	}
	defer rows.Close()

	var columns []models.TableColumn
	for rows.Next() {
		var column models.TableColumn
		var dataLength, dataPrecision, dataScale sql.NullInt64
		var defaultValue sql.NullString
		
		err := rows.Scan(
			&column.ID, &column.TableID, &column.ColumnName, &column.DataType,
			&dataLength, &dataPrecision, &dataScale, &column.IsNullable,
			&column.IsPrimaryKey, &column.IsForeignKey, &defaultValue,
			&column.ColumnPosition,
		)
		if err != nil {
			log.Printf("Error scanning table column: %v", err)
			continue
		}
		
		if dataLength.Valid {
			length := int(dataLength.Int64)
			column.DataLength = &length
		}
		if dataPrecision.Valid {
			precision := int(dataPrecision.Int64)
			column.DataPrecision = &precision
		}
		if dataScale.Valid {
			scale := int(dataScale.Int64)
			column.DataScale = &scale
		}
		if defaultValue.Valid {
			column.DefaultValue = &defaultValue.String
		}
		
		columns = append(columns, column)
	}

	log.Printf("Loaded %d table columns from Forge", len(columns))
	return columns, nil
}

// LoadAutoFunctions loads all auto-generated functions from Forge
func (f *ForgeLoader) LoadAutoFunctions() ([]models.AutoFunction, error) {
	query := `
		SELECT AUTO_FUNC_ID, GEC_ID, FUNCTION_NAME, FUNCTION_TYPE, COLUMN_ID,
		       FUNCTION_SIGNATURE, RETURN_TYPE, DESCRIPTION, PARAMETERS,
		       CACHE_ENABLED, CACHE_TTL_SECONDS, IS_ACTIVE, CREATE_DATE, UPDATE_DATE
		FROM GEE_AUTO_FUNCTIONS
		WHERE IS_ACTIVE = 1
		ORDER BY GEC_ID, FUNCTION_TYPE, FUNCTION_NAME
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query auto-functions: %w", err)
	}
	defer rows.Close()

	var functions []models.AutoFunction
	for rows.Next() {
		var function models.AutoFunction
		var columnID sql.NullInt64
		var description sql.NullString
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&function.ID, &function.TableID, &function.FunctionName,
			&function.FunctionType, &columnID, &function.FunctionSignature,
			&function.ReturnType, &description, &function.Parameters,
			&function.CacheEnabled, &function.CacheTTL, &function.IsActive,
			&function.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning auto-function: %v", err)
			continue
		}
		
		if columnID.Valid {
			colID := columnID.Int64
			function.ColumnID = &colID
		}
		if description.Valid {
			function.Description = &description.String
		}
		if updateDate.Valid {
			function.UpdateDate = &updateDate.Time
		}
		
		functions = append(functions, function)
	}

	log.Printf("Loaded %d auto-functions from Forge", len(functions))
	return functions, nil
}

// LoadConnectionTokens loads all active connection tokens from Forge
func (f *ForgeLoader) LoadConnectionTokens() ([]models.ConnectionToken, error) {
	query := `
		SELECT TOKEN_ID, DB_CONFIG_ID, TOKEN_HASH, TOKEN_TYPE, ENVIRONMENT,
		       PERMISSIONS, CREATED_BY, CREATED_AT, EXPIRES_AT, LAST_USED_AT,
		       USAGE_COUNT, IS_ACTIVE
		FROM GEE_CONNECTION_TOKENS
		WHERE IS_ACTIVE = 1 AND (EXPIRES_AT IS NULL OR EXPIRES_AT > datetime('now'))
		ORDER BY CREATED_AT DESC
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query connection tokens: %w", err)
	}
	defer rows.Close()

	var tokens []models.ConnectionToken
	for rows.Next() {
		var token models.ConnectionToken
		var expiresAt, lastUsedAt sql.NullTime
		
		err := rows.Scan(
			&token.TokenID, &token.DBConfigID, &token.TokenHash,
			&token.TokenType, &token.Environment, &token.Permissions,
			&token.CreatedBy, &token.CreatedAt, &expiresAt, &lastUsedAt,
			&token.UsageCount, &token.IsActive,
		)
		if err != nil {
			log.Printf("Error scanning connection token: %v", err)
			continue
		}
		
		if expiresAt.Valid {
			token.ExpiresAt = &expiresAt.Time
		}
		if lastUsedAt.Valid {
			token.LastUsedAt = &lastUsedAt.Time
		}
		
		tokens = append(tokens, token)
	}

	log.Printf("Loaded %d connection tokens from Forge", len(tokens))
	return tokens, nil
}

// GetLastUpdateTime returns the last update time of relevant tables
func (f *ForgeLoader) GetLastUpdateTime() (time.Time, error) {
	query := `
		SELECT MAX(update_time) as last_update FROM (
			SELECT COALESCE(MAX(UPDATE_DATE), MAX(CREATE_DATE)) as update_time FROM GEE_TABLES
			UNION ALL
			SELECT COALESCE(MAX(UPDATE_DATE), MAX(CREATE_DATE)) as update_time FROM GEE_AUTO_FUNCTIONS
		)
	`
	
	var lastUpdate sql.NullTime
	err := f.db.QueryRow(query).Scan(&lastUpdate)
	if err != nil {
		return time.Time{}, fmt.Errorf("failed to get last update time: %w", err)
	}
	
	if lastUpdate.Valid {
		return lastUpdate.Time, nil
	}
	return time.Time{}, nil
}

// NeedsUpdate checks if the data needs to be reloaded from Forge
func (f *ForgeLoader) NeedsUpdate() (bool, error) {
	f.updateMutex.RLock()
	defer f.updateMutex.RUnlock()
	
	lastUpdate, err := f.GetLastUpdateTime()
	if err != nil {
		return false, err
	}
	
	return lastUpdate.After(f.lastUpdated), nil
}

// MarkUpdated marks the loader as having been updated
func (f *ForgeLoader) MarkUpdated() {
	f.updateMutex.Lock()
	defer f.updateMutex.Unlock()
	f.lastUpdated = time.Now()
}

// LoadFlows loads all flows from Forge
func (f *ForgeLoader) LoadFlows() ([]models.Flow, error) {
	query := `
		SELECT FLOW_ID, FLOW_NAME, FLOW_DESC, FLOW_TYPE, ENDPOINT_PATH,
		       HTTP_METHOD, IS_ACTIVE, CREATE_DATE, UPDATE_DATE
		FROM GEE_FLOW
		WHERE IS_ACTIVE = 1
		ORDER BY FLOW_NAME
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query flows: %w", err)
	}
	defer rows.Close()

	var flows []models.Flow
	for rows.Next() {
		var flow models.Flow
		var flowDesc sql.NullString
		var endpointPath, httpMethod sql.NullString
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&flow.FlowID, &flow.FlowName, &flowDesc, &flow.FlowType,
			&endpointPath, &httpMethod, &flow.IsActive,
			&flow.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning flow: %v", err)
			continue
		}
		
		if flowDesc.Valid {
			flow.FlowDesc = &flowDesc.String
		}
		if endpointPath.Valid {
			flow.EndpointPath = &endpointPath.String
		}
		if httpMethod.Valid {
			flow.HTTPMethod = &httpMethod.String
		}
		if updateDate.Valid {
			flow.UpdateDate = &updateDate.Time
		}
		
		// Load flow steps for this flow
		steps, err := f.LoadFlowSteps(flow.FlowID)
		if err != nil {
			log.Printf("Error loading steps for flow %s: %v", flow.FlowName, err)
		} else {
			flow.Steps = steps
		}
		
		flows = append(flows, flow)
	}

	log.Printf("Loaded %d flows from Forge", len(flows))
	return flows, nil
}

// LoadFlowSteps loads flow steps for a specific flow
func (f *ForgeLoader) LoadFlowSteps(flowID int64) ([]models.FlowStep, error) {
	query := `
		SELECT STEP_ID, FLOW_ID, STEP_ORDER, RULE_GROUP_ID, STEP_NAME,
		       STEP_DESC, STEP_TYPE, IS_ACTIVE, CREATE_DATE, UPDATE_DATE
		FROM GEE_FLOW_STEPS
		WHERE FLOW_ID = ? AND IS_ACTIVE = 1
		ORDER BY STEP_ORDER
	`

	rows, err := f.db.Query(query, flowID)
	if err != nil {
		return nil, fmt.Errorf("failed to query flow steps: %w", err)
	}
	defer rows.Close()

	var steps []models.FlowStep
	for rows.Next() {
		var step models.FlowStep
		var ruleGroupID sql.NullInt64
		var stepDesc sql.NullString
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&step.StepID, &step.FlowID, &step.StepOrder, &ruleGroupID,
			&step.StepName, &stepDesc, &step.StepType, &step.IsActive,
			&step.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning flow step: %v", err)
			continue
		}
		
		if ruleGroupID.Valid {
			groupID := ruleGroupID.Int64
			step.RuleGroupID = &groupID
		}
		if stepDesc.Valid {
			step.StepDesc = &stepDesc.String
		}
		if updateDate.Valid {
			step.UpdateDate = &updateDate.Time
		}
		
		// Load rules for this step if it has a rule group
		if step.RuleGroupID != nil {
			rules, err := f.LoadRulesForGroup(*step.RuleGroupID)
			if err != nil {
				log.Printf("Error loading rules for step %s: %v", step.StepName, err)
			} else {
				step.Rules = rules
			}
		}
		
		steps = append(steps, step)
	}

	return steps, nil
}

// LoadRuleGroups loads all rule groups from Forge
func (f *ForgeLoader) LoadRuleGroups() ([]models.RuleGroup, error) {
	query := `
		SELECT GRG_ID, GRG_NAME, GRG_DESC, GRG_PRIORITY, IS_ACTIVE,
		       CREATE_DATE, UPDATE_DATE
		FROM GEE_RULES_GROUPS
		WHERE IS_ACTIVE = 1
		ORDER BY GRG_PRIORITY, GRG_NAME
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query rule groups: %w", err)
	}
	defer rows.Close()

	var ruleGroups []models.RuleGroup
	for rows.Next() {
		var rg models.RuleGroup
		var groupDesc sql.NullString
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&rg.GroupID, &rg.GroupName, &groupDesc, &rg.GroupPriority,
			&rg.IsActive, &rg.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning rule group: %v", err)
			continue
		}
		
		if groupDesc.Valid {
			rg.GroupDesc = &groupDesc.String
		}
		if updateDate.Valid {
			rg.UpdateDate = &updateDate.Time
		}
		
		// Load rules for this group
		rules, err := f.LoadRulesForGroup(rg.GroupID)
		if err != nil {
			log.Printf("Error loading rules for group %s: %v", rg.GroupName, err)
		} else {
			rg.Rules = rules
		}
		
		ruleGroups = append(ruleGroups, rg)
	}

	log.Printf("Loaded %d rule groups from Forge", len(ruleGroups))
	return ruleGroups, nil
}

// LoadRulesForGroup loads all rules for a specific rule group
func (f *ForgeLoader) LoadRulesForGroup(groupID int64) ([]models.Rule, error) {
	query := `
		SELECT RULE_ID, RULE_NAME, RULE_DESC, RULE_EXPRESSION, RULE_PRIORITY,
		       RULE_TYPE, RULE_GROUP_ID, IS_ACTIVE, CREATE_DATE, UPDATE_DATE
		FROM GEE_RULES
		WHERE RULE_GROUP_ID = ? AND IS_ACTIVE = 1
		ORDER BY RULE_PRIORITY, RULE_NAME
	`

	rows, err := f.db.Query(query, groupID)
	if err != nil {
		return nil, fmt.Errorf("failed to query rules: %w", err)
	}
	defer rows.Close()

	var rules []models.Rule
	for rows.Next() {
		var rule models.Rule
		var ruleDesc sql.NullString
		var ruleGroupID sql.NullInt64
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&rule.RuleID, &rule.RuleName, &ruleDesc, &rule.RuleExpression,
			&rule.RulePriority, &rule.RuleType, &ruleGroupID, &rule.IsActive,
			&rule.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning rule: %v", err)
			continue
		}
		
		if ruleDesc.Valid {
			rule.RuleDesc = &ruleDesc.String
		}
		if ruleGroupID.Valid {
			gID := ruleGroupID.Int64
			rule.RuleGroupID = &gID
		}
		if updateDate.Valid {
			rule.UpdateDate = &updateDate.Time
		}
		
		rules = append(rules, rule)
	}

	return rules, nil
}

// LoadAllRules loads all rules from Forge
func (f *ForgeLoader) LoadAllRules() ([]models.Rule, error) {
	query := `
		SELECT RULE_ID, RULE_NAME, RULE_DESC, RULE_EXPRESSION, RULE_PRIORITY,
		       RULE_TYPE, RULE_GROUP_ID, IS_ACTIVE, CREATE_DATE, UPDATE_DATE
		FROM GEE_RULES
		WHERE IS_ACTIVE = 1
		ORDER BY RULE_GROUP_ID, RULE_PRIORITY, RULE_NAME
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query all rules: %w", err)
	}
	defer rows.Close()

	var rules []models.Rule
	for rows.Next() {
		var rule models.Rule
		var ruleDesc sql.NullString
		var ruleGroupID sql.NullInt64
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&rule.RuleID, &rule.RuleName, &ruleDesc, &rule.RuleExpression,
			&rule.RulePriority, &rule.RuleType, &ruleGroupID, &rule.IsActive,
			&rule.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning rule: %v", err)
			continue
		}
		
		if ruleDesc.Valid {
			rule.RuleDesc = &ruleDesc.String
		}
		if ruleGroupID.Valid {
			gID := ruleGroupID.Int64
			rule.RuleGroupID = &gID
		}
		if updateDate.Valid {
			rule.UpdateDate = &updateDate.Time
		}
		
		rules = append(rules, rule)
	}

	log.Printf("Loaded %d rules from Forge", len(rules))
	return rules, nil
}

// LoadAPIEndpoints loads all API endpoints from Forge
func (f *ForgeLoader) LoadAPIEndpoints() ([]models.APIEndpoint, error) {
	query := `
		SELECT ENDPOINT_ID, ENDPOINT_PATH, HTTP_METHOD, CLASS_NAME,
		       OPERATION_ID, DESCRIPTION, IS_ACTIVE, CREATE_DATE, UPDATE_DATE
		FROM GEE_API_ENDPOINTS
		WHERE IS_ACTIVE = 1
		ORDER BY ENDPOINT_PATH, HTTP_METHOD
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query API endpoints: %w", err)
	}
	defer rows.Close()

	var endpoints []models.APIEndpoint
	for rows.Next() {
		var endpoint models.APIEndpoint
		var className, operationID, description sql.NullString
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&endpoint.EndpointID, &endpoint.EndpointPath, &endpoint.HTTPMethod,
			&className, &operationID, &description, &endpoint.IsActive,
			&endpoint.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning API endpoint: %v", err)
			continue
		}
		
		if className.Valid {
			endpoint.ClassName = &className.String
		}
		if operationID.Valid {
			endpoint.OperationID = &operationID.String
		}
		if description.Valid {
			endpoint.Description = &description.String
		}
		if updateDate.Valid {
			endpoint.UpdateDate = &updateDate.Time
		}
		
		endpoints = append(endpoints, endpoint)
	}

	log.Printf("Loaded %d API endpoints from Forge", len(endpoints))
	return endpoints, nil
}

// LoadBaseFunctions loads all base functions from Forge
func (f *ForgeLoader) LoadBaseFunctions() ([]models.BaseFunction, error) {
	query := `
		SELECT GBF_ID, GBF_NAME, GBF_DESC, GBF_CODE, GBF_RETURN_TYPE,
		       IS_ACTIVE, CREATE_DATE, UPDATE_DATE
		FROM GEE_BASE_FUNCTIONS
		WHERE IS_ACTIVE = 1
		ORDER BY GBF_NAME
	`

	rows, err := f.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query base functions: %w", err)
	}
	defer rows.Close()

	var functions []models.BaseFunction
	for rows.Next() {
		var function models.BaseFunction
		var description sql.NullString
		var updateDate sql.NullTime
		
		err := rows.Scan(
			&function.FunctionID, &function.FunctionName, &description,
			&function.Code, &function.ReturnType, &function.IsActive,
			&function.CreateDate, &updateDate,
		)
		if err != nil {
			log.Printf("Error scanning base function: %v", err)
			continue
		}
		
		if description.Valid {
			function.Description = &description.String
		}
		if updateDate.Valid {
			function.UpdateDate = &updateDate.Time
		}
		
		functions = append(functions, function)
	}

	log.Printf("Loaded %d base functions from Forge", len(functions))
	return functions, nil
}