package db

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"praxis/internal/models"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Manager struct {
	storagePath string
	currentDB   *sql.DB
	dbPath      string
}

func NewManager(storagePath string) *Manager {
	return &Manager{
		storagePath: storagePath,
	}
}

// SaveDatabase saves the uploaded database file
func (m *Manager) SaveDatabase(file io.Reader, filename string) error {
	// Create timestamped filename
	timestamp := time.Now().Format("20060102_150405")
	dbFilename := fmt.Sprintf("gee_%s_%s", timestamp, filename)
	dbPath := filepath.Join(m.storagePath, dbFilename)

	// Save file
	out, err := os.Create(dbPath)
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	defer out.Close()

	if _, err := io.Copy(out, file); err != nil {
		return fmt.Errorf("failed to save file: %w", err)
	}

	// Close current database if open
	if m.currentDB != nil {
		m.currentDB.Close()
	}

	// Open new database
	db, err := sql.Open("sqlite3", dbPath+"?mode=ro")
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}

	// Verify it's a valid SQLite database
	if err := db.Ping(); err != nil {
		db.Close()
		os.Remove(dbPath)
		return fmt.Errorf("invalid SQLite database: %w", err)
	}

	m.currentDB = db
	m.dbPath = dbPath

	// Create symlink to current database
	currentLink := filepath.Join(m.storagePath, "current.db")
	os.Remove(currentLink) // Remove old symlink if exists
	os.Symlink(dbFilename, currentLink)

	return nil
}

// GetFieldClasses retrieves all field classes
func (m *Manager) GetFieldClasses() ([]models.FieldClass, error) {
	if m.currentDB == nil {
		return nil, fmt.Errorf("no database loaded")
	}

	query := `
		SELECT GFC_ID, GFC_IS, FIELD_CLASS_NAME, CLASS_TYPE, 
		       CREATE_DATE, UPDATE_DATE, DESCRIPTION
		FROM GEE_FIELD_CLASSES
		ORDER BY GFC_ID
	`

	rows, err := m.currentDB.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query field classes: %w", err)
	}
	defer rows.Close()

	var classes []models.FieldClass
	for rows.Next() {
		var class models.FieldClass
		var updateDate sql.NullTime
		var description sql.NullString

		err := rows.Scan(
			&class.ID,
			&class.IS,
			&class.FieldClassName,
			&class.ClassType,
			&class.CreateDate,
			&updateDate,
			&description,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		if updateDate.Valid {
			class.UpdateDate = &updateDate.Time
		}
		if description.Valid {
			class.Description = &description.String
		}

		classes = append(classes, class)
	}

	return classes, nil
}

// GetFields retrieves all fields
func (m *Manager) GetFields() ([]models.Field, error) {
	if m.currentDB == nil {
		return nil, fmt.Errorf("no database loaded")
	}

	query := `
		SELECT GF_ID, GFC_ID, GF_NAME, GF_TYPE, GF_SIZE, 
		       GF_PRECISION_SIZE, GF_DEFAULT_VALUE, CREATE_DATE, 
		       UPDATE_DATE, GF_DESCRIPTION
		FROM GEE_FIELDS
		ORDER BY GF_ID
	`

	rows, err := m.currentDB.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query fields: %w", err)
	}
	defer rows.Close()

	var fields []models.Field
	for rows.Next() {
		var field models.Field
		var size, precisionSize sql.NullInt64
		var defaultValue, description sql.NullString
		var updateDate sql.NullTime

		err := rows.Scan(
			&field.ID,
			&field.ClassID,
			&field.Name,
			&field.Type,
			&size,
			&precisionSize,
			&defaultValue,
			&field.CreateDate,
			&updateDate,
			&description,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		if size.Valid {
			s := int(size.Int64)
			field.Size = &s
		}
		if precisionSize.Valid {
			ps := int(precisionSize.Int64)
			field.PrecisionSize = &ps
		}
		if defaultValue.Valid {
			field.DefaultValue = &defaultValue.String
		}
		if updateDate.Valid {
			field.UpdateDate = &updateDate.Time
		}
		if description.Valid {
			field.Description = &description.String
		}

		fields = append(fields, field)
	}

	return fields, nil
}

// GetFlowDefinitions retrieves flow definitions from GEE_FLOW_DEFINITIONS
func (m *Manager) GetFlowDefinitions() ([]map[string]interface{}, error) {
	if m.currentDB == nil {
		return nil, fmt.Errorf("no database loaded")
	}

	// First check if the table exists
	var tableExists bool
	err := m.currentDB.QueryRow(`
		SELECT COUNT(*) FROM sqlite_master 
		WHERE type='table' AND name='GEE_FLOW_DEFINITIONS'
	`).Scan(&tableExists)
	
	if err != nil || !tableExists {
		// Table doesn't exist, try to get from GEE_FLOWS
		return m.getFlowsFromFlowsTable()
	}

	query := `
		SELECT FLOW_DEF_ID, FLOW_ID, FLOW_JSON, VERSION, CREATE_DATE
		FROM GEE_FLOW_DEFINITIONS
		ORDER BY FLOW_DEF_ID
	`

	rows, err := m.currentDB.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query flow definitions: %w", err)
	}
	defer rows.Close()

	var definitions []map[string]interface{}
	for rows.Next() {
		var flowDefID, flowID int64
		var flowJSON string
		var version int
		var createDate time.Time

		err := rows.Scan(&flowDefID, &flowID, &flowJSON, &version, &createDate)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		// Parse JSON
		var flowDef models.FlowDefinition
		if err := json.Unmarshal([]byte(flowJSON), &flowDef); err != nil {
			// If parsing fails, return raw data
			definitions = append(definitions, map[string]interface{}{
				"flow_def_id": flowDefID,
				"flow_id":     flowID,
				"flow_json":   flowJSON,
				"version":     version,
				"create_date": createDate,
			})
		} else {
			definitions = append(definitions, map[string]interface{}{
				"flow_def_id": flowDefID,
				"flow_id":     flowID,
				"flow_data":   flowDef,
				"version":     version,
				"create_date": createDate,
			})
		}
	}

	return definitions, nil
}

// Fallback method to get flows from GEE_FLOWS table
func (m *Manager) getFlowsFromFlowsTable() ([]map[string]interface{}, error) {
	query := `
		SELECT FLOW_ID, FLOW_NAME, DESCRIPTION, VERSION, STATUS, 
		       CREATE_DATE, UPDATE_DATE
		FROM GEE_FLOWS
		ORDER BY FLOW_ID
	`

	rows, err := m.currentDB.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query flows: %w", err)
	}
	defer rows.Close()

	var flows []map[string]interface{}
	for rows.Next() {
		var flowID int64
		var flowName, status string
		var description sql.NullString
		var version int
		var createDate time.Time
		var updateDate sql.NullTime

		err := rows.Scan(&flowID, &flowName, &description, &version, 
			&status, &createDate, &updateDate)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		flow := map[string]interface{}{
			"flow_id":     flowID,
			"flow_name":   flowName,
			"version":     version,
			"status":      status,
			"create_date": createDate,
		}

		if description.Valid {
			flow["description"] = description.String
		}
		if updateDate.Valid {
			flow["update_date"] = updateDate.Time
		}

		flows = append(flows, flow)
	}

	return flows, nil
}

// GetStatus returns the current database status
func (m *Manager) GetStatus() map[string]interface{} {
	status := map[string]interface{}{
		"database_loaded": m.currentDB != nil,
		"storage_path":    m.storagePath,
	}

	if m.currentDB != nil {
		status["current_db_path"] = m.dbPath
		
		// Get table counts
		var classCount, fieldCount, flowCount int
		m.currentDB.QueryRow("SELECT COUNT(*) FROM GEE_FIELD_CLASSES").Scan(&classCount)
		m.currentDB.QueryRow("SELECT COUNT(*) FROM GEE_FIELDS").Scan(&fieldCount)
		m.currentDB.QueryRow("SELECT COUNT(*) FROM GEE_FLOWS").Scan(&flowCount)
		
		status["statistics"] = map[string]int{
			"field_classes": classCount,
			"fields":        fieldCount,
			"flows":         flowCount,
		}
	}

	return status
}