package models

import (
	"database/sql/driver"
	"encoding/json"
	"time"
)

// FieldClass represents GEE_FIELD_CLASSES table
type FieldClass struct {
	ID              int64     `json:"id" db:"GFC_ID"`
	IS              *int64    `json:"is,omitempty" db:"GFC_IS"`
	FieldClassName  string    `json:"field_class_name" db:"FIELD_CLASS_NAME"`
	ClassType       string    `json:"class_type" db:"CLASS_TYPE"`
	CreateDate      time.Time `json:"create_date" db:"CREATE_DATE"`
	UpdateDate      *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
	Description     *string   `json:"description,omitempty" db:"DESCRIPTION"`
}

// Field represents GEE_FIELDS table
type Field struct {
	ID             int64      `json:"id" db:"GF_ID"`
	ClassID        int64      `json:"class_id" db:"GFC_ID"`
	Name           string     `json:"name" db:"GF_NAME"`
	Type           string     `json:"type" db:"GF_TYPE"`
	Size           *int       `json:"size,omitempty" db:"GF_SIZE"`
	PrecisionSize  *int       `json:"precision_size,omitempty" db:"GF_PRECISION_SIZE"`
	DefaultValue   *string    `json:"default_value,omitempty" db:"GF_DEFAULT_VALUE"`
	CreateDate     time.Time  `json:"create_date" db:"CREATE_DATE"`
	UpdateDate     *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
	Description    *string    `json:"description,omitempty" db:"GF_DESCRIPTION"`
}

// FlowDefinition represents the JSON stored in GEE_FLOW_DEFINITIONS
type FlowDefinition struct {
	ID          int64                  `json:"id"`
	Name        string                 `json:"name"`
	Version     int                    `json:"version"`
	Nodes       []FlowNode             `json:"nodes"`
	Connections []FlowConnection       `json:"connections"`
	Metadata    map[string]interface{} `json:"metadata"`
}

// FlowNode represents a node in the flow
type FlowNode struct {
	ID         string                 `json:"id"`
	Type       string                 `json:"type"`
	RefID      int64                  `json:"ref_id"`
	Position   Position               `json:"position"`
	Properties map[string]interface{} `json:"properties"`
	Children   []string               `json:"children,omitempty"`
}

// Position represents node position
type Position struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

// FlowConnection represents connections between nodes
type FlowConnection struct {
	ID        string  `json:"id"`
	Source    string  `json:"source"`
	Target    string  `json:"target"`
	Type      string  `json:"type"`
	Condition *string `json:"condition,omitempty"`
}

// JSONData is a custom type for handling JSON columns
type JSONData map[string]interface{}

func (j JSONData) Value() (driver.Value, error) {
	return json.Marshal(j)
}

func (j *JSONData) Scan(value interface{}) error {
	if value == nil {
		*j = make(map[string]interface{})
		return nil
	}
	
	switch v := value.(type) {
	case []byte:
		return json.Unmarshal(v, j)
	case string:
		return json.Unmarshal([]byte(v), j)
	default:
		return json.Unmarshal([]byte(value.(string)), j)
	}
}

// AutoFunction represents auto-generated table functions
type AutoFunction struct {
	ID               int64     `json:"id" db:"AUTO_FUNC_ID"`
	TableID          int64     `json:"table_id" db:"GEC_ID"`
	FunctionName     string    `json:"function_name" db:"FUNCTION_NAME"`
	FunctionType     string    `json:"function_type" db:"FUNCTION_TYPE"`
	ColumnID         *int64    `json:"column_id,omitempty" db:"COLUMN_ID"`
	FunctionSignature string   `json:"function_signature" db:"FUNCTION_SIGNATURE"`
	ReturnType       string    `json:"return_type" db:"RETURN_TYPE"`
	Description      *string   `json:"description,omitempty" db:"DESCRIPTION"`
	Parameters       string    `json:"parameters" db:"PARAMETERS"`
	CacheEnabled     bool      `json:"cache_enabled" db:"CACHE_ENABLED"`
	CacheTTL         int       `json:"cache_ttl_seconds" db:"CACHE_TTL_SECONDS"`
	IsActive         bool      `json:"is_active" db:"IS_ACTIVE"`
	CreateDate       time.Time `json:"create_date" db:"CREATE_DATE"`
	UpdateDate       *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
}

// TableColumn represents table column metadata
type TableColumn struct {
	ID             int64   `json:"id" db:"COLUMN_ID"`
	TableID        int64   `json:"table_id" db:"GEC_ID"`
	ColumnName     string  `json:"column_name" db:"COLUMN_NAME"`
	DataType       string  `json:"data_type" db:"DATA_TYPE"`
	DataLength     *int    `json:"data_length,omitempty" db:"DATA_LENGTH"`
	DataPrecision  *int    `json:"data_precision,omitempty" db:"DATA_PRECISION"`
	DataScale      *int    `json:"data_scale,omitempty" db:"DATA_SCALE"`
	IsNullable     string  `json:"is_nullable" db:"IS_NULLABLE"`
	IsPrimaryKey   bool    `json:"is_primary_key" db:"IS_PRIMARY_KEY"`
	IsForeignKey   bool    `json:"is_foreign_key" db:"IS_FOREIGN_KEY"`
	DefaultValue   *string `json:"default_value,omitempty" db:"DEFAULT_VALUE"`
	ColumnPosition int     `json:"column_position" db:"COLUMN_POSITION"`
}

// Table represents table metadata
type Table struct {
	ID                     int64      `json:"id" db:"GEC_ID"`
	TableName              string     `json:"table_name" db:"TABLE_NAME"`
	TableType              string     `json:"table_type" db:"TABLE_TYPE"`
	Query                  *string    `json:"query,omitempty" db:"QUERY"`
	Description            *string    `json:"description,omitempty" db:"DESCRIPTION"`
	DBType                 *string    `json:"db_type,omitempty" db:"DB_TYPE"`
	SourceConnectionHandle *string    `json:"source_connection_handle,omitempty" db:"SOURCE_CONNECTION_HANDLE"`
	CreateDate             time.Time  `json:"create_date" db:"CREATE_DATE"`
	UpdateDate             *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
}

// ConnectionToken represents database connection tokens
type ConnectionToken struct {
	TokenID      string     `json:"token_id" db:"TOKEN_ID"`
	DBConfigID   int64      `json:"db_config_id" db:"DB_CONFIG_ID"`
	TokenHash    string     `json:"token_hash" db:"TOKEN_HASH"`
	TokenType    string     `json:"token_type" db:"TOKEN_TYPE"`
	Environment  string     `json:"environment" db:"ENVIRONMENT"`
	Permissions  string     `json:"permissions" db:"PERMISSIONS"`
	CreatedBy    string     `json:"created_by" db:"CREATED_BY"`
	CreatedAt    time.Time  `json:"created_at" db:"CREATED_AT"`
	ExpiresAt    *time.Time `json:"expires_at,omitempty" db:"EXPIRES_AT"`
	LastUsedAt   *time.Time `json:"last_used_at,omitempty" db:"LAST_USED_AT"`
	UsageCount   int        `json:"usage_count" db:"USAGE_COUNT"`
	IsActive     bool       `json:"is_active" db:"IS_ACTIVE"`
}

// Flow represents GEE_FLOW table
type Flow struct {
	FlowID       int64      `json:"flow_id" db:"FLOW_ID"`
	FlowName     string     `json:"flow_name" db:"FLOW_NAME"`
	FlowDesc     *string    `json:"flow_desc,omitempty" db:"FLOW_DESC"`
	FlowType     string     `json:"flow_type" db:"FLOW_TYPE"`
	EndpointPath *string    `json:"endpoint_path,omitempty" db:"ENDPOINT_PATH"`
	HTTPMethod   *string    `json:"http_method,omitempty" db:"HTTP_METHOD"`
	IsActive     bool       `json:"is_active" db:"IS_ACTIVE"`
	CreateDate   time.Time  `json:"create_date" db:"CREATE_DATE"`
	UpdateDate   *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
	Steps        []FlowStep `json:"steps,omitempty"`
}

// FlowStep represents GEE_FLOW_STEPS table
type FlowStep struct {
	StepID      int64      `json:"step_id" db:"STEP_ID"`
	FlowID      int64      `json:"flow_id" db:"FLOW_ID"`
	StepOrder   int        `json:"step_order" db:"STEP_ORDER"`
	RuleGroupID *int64     `json:"rule_group_id,omitempty" db:"RULE_GROUP_ID"`
	StepName    string     `json:"step_name" db:"STEP_NAME"`
	StepDesc    *string    `json:"step_desc,omitempty" db:"STEP_DESC"`
	StepType    string     `json:"step_type" db:"STEP_TYPE"`
	IsActive    bool       `json:"is_active" db:"IS_ACTIVE"`
	CreateDate  time.Time  `json:"create_date" db:"CREATE_DATE"`
	UpdateDate  *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
	Rules       []Rule     `json:"rules,omitempty"`
}

// Rule represents GEE_RULES table
type Rule struct {
	RuleID         int64      `json:"rule_id" db:"RULE_ID"`
	RuleName       string     `json:"rule_name" db:"RULE_NAME"`
	RuleDesc       *string    `json:"rule_desc,omitempty" db:"RULE_DESC"`
	RuleExpression string     `json:"rule_expression" db:"RULE_EXPRESSION"`
	RulePriority   int        `json:"rule_priority" db:"RULE_PRIORITY"`
	RuleType       string     `json:"rule_type" db:"RULE_TYPE"`
	RuleGroupID    *int64     `json:"rule_group_id,omitempty" db:"RULE_GROUP_ID"`
	IsActive       bool       `json:"is_active" db:"IS_ACTIVE"`
	CreateDate     time.Time  `json:"create_date" db:"CREATE_DATE"`
	UpdateDate     *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
}

// RuleGroup represents GEE_RULES_GROUPS table
type RuleGroup struct {
	GroupID     int64      `json:"group_id" db:"GRG_ID"`
	GroupName   string     `json:"group_name" db:"GRG_NAME"`
	GroupDesc   *string    `json:"group_desc,omitempty" db:"GRG_DESC"`
	GroupPriority int      `json:"group_priority" db:"GRG_PRIORITY"`
	IsActive    bool       `json:"is_active" db:"IS_ACTIVE"`
	CreateDate  time.Time  `json:"create_date" db:"CREATE_DATE"`
	UpdateDate  *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
	Rules       []Rule     `json:"rules,omitempty"`
}

// APIEndpoint represents GEE_API_ENDPOINTS table
type APIEndpoint struct {
	EndpointID   int64      `json:"endpoint_id" db:"ENDPOINT_ID"`
	EndpointPath string     `json:"endpoint_path" db:"ENDPOINT_PATH"`
	HTTPMethod   string     `json:"http_method" db:"HTTP_METHOD"`
	ClassName    *string    `json:"class_name,omitempty" db:"CLASS_NAME"`
	OperationID  *string    `json:"operation_id,omitempty" db:"OPERATION_ID"`
	Description  *string    `json:"description,omitempty" db:"DESCRIPTION"`
	IsActive     bool       `json:"is_active" db:"IS_ACTIVE"`
	CreateDate   time.Time  `json:"create_date" db:"CREATE_DATE"`
	UpdateDate   *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
	Flow         *Flow      `json:"flow,omitempty"`
}

// BaseFunction represents GEE_BASE_FUNCTIONS table
type BaseFunction struct {
	FunctionID   int64      `json:"function_id" db:"GBF_ID"`
	FunctionName string     `json:"function_name" db:"GBF_NAME"`
	Description  *string    `json:"description,omitempty" db:"GBF_DESC"`
	Code         string     `json:"code" db:"GBF_CODE"`
	ReturnType   string     `json:"return_type" db:"GBF_RETURN_TYPE"`
	IsActive     bool       `json:"is_active" db:"IS_ACTIVE"`
	CreateDate   time.Time  `json:"create_date" db:"CREATE_DATE"`
	UpdateDate   *time.Time `json:"update_date,omitempty" db:"UPDATE_DATE"`
}