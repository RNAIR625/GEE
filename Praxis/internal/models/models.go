package models

import (
	"database/sql/driver"
	"encoding/json"
	"time"
)

// FieldClass represents GEE_FIELD_CLASSES table
type FieldClass struct {
	ID              int64     `json:"id" db:"GFC_ID"`
	IS              int64     `json:"is" db:"GFC_IS"`
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