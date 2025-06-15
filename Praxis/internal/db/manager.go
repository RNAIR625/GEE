package db

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"github.com/GEE/Praxis/internal/models"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Manager struct {
	storagePath string
	currentDB   *sql.DB
	dbPath      string
	cache       *models.DataCache
}

func NewManager(storagePath string) *Manager {
	m := &Manager{
		storagePath: storagePath,
		cache:       models.NewDataCache(),
	}
	
	// Try to load the latest database on startup
	if err := m.LoadLatestDatabase(); err != nil {
		log.Printf("Warning: Failed to load latest database on startup: %v", err)
	} else {
		// Load cache after successful database connection
		if err := m.loadCacheData(); err != nil {
			log.Printf("Warning: Failed to load cache data on startup: %v", err)
		}
	}
	
	return m
}

// LoadLatestDatabase loads the most recent database file from storage
func (m *Manager) LoadLatestDatabase() error {
	// Check if storage path exists
	if _, err := os.Stat(m.storagePath); os.IsNotExist(err) {
		return fmt.Errorf("storage path does not exist: %s", m.storagePath)
	}
	
	// Look for database files matching pattern
	pattern := filepath.Join(m.storagePath, "gee_*_execution_worker.db")
	matches, err := filepath.Glob(pattern)
	if err != nil {
		return fmt.Errorf("failed to search for database files: %w", err)
	}
	
	if len(matches) == 0 {
		return fmt.Errorf("no database files found in %s", m.storagePath)
	}
	
	// Find the most recent file
	var latestFile string
	var latestTime time.Time
	
	for _, file := range matches {
		info, err := os.Stat(file)
		if err != nil {
			continue
		}
		if info.ModTime().After(latestTime) {
			latestTime = info.ModTime()
			latestFile = file
		}
	}
	
	if latestFile == "" {
		return fmt.Errorf("no valid database files found")
	}
	
	// Open the database
	db, err := sql.Open("sqlite3", latestFile+"?mode=ro")
	if err != nil {
		return fmt.Errorf("failed to open database %s: %w", latestFile, err)
	}
	
	// Verify it's a valid SQLite database
	if err := db.Ping(); err != nil {
		db.Close()
		return fmt.Errorf("invalid SQLite database %s: %w", latestFile, err)
	}
	
	// Close current database if open
	if m.currentDB != nil {
		m.currentDB.Close()
	}
	
	m.currentDB = db
	m.dbPath = latestFile
	
	// Update symlink to current database
	currentLink := filepath.Join(m.storagePath, "current.db")
	os.Remove(currentLink) // Remove old symlink if exists
	relPath, _ := filepath.Rel(m.storagePath, latestFile)
	os.Symlink(relPath, currentLink)
	
	log.Printf("Loaded database: %s", latestFile)
	
	// Load cache data after successful database connection
	if err := m.loadCacheData(); err != nil {
		log.Printf("Warning: Failed to load cache data: %v", err)
	}
	
	return nil
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
	
	// Reload cache data with new database
	if err := m.loadCacheData(); err != nil {
		log.Printf("Warning: Failed to reload cache data: %v", err)
	}

	return nil
}

// loadCacheData loads field classes and fields into cache at startup
func (m *Manager) loadCacheData() error {
	if m.currentDB == nil {
		return fmt.Errorf("no database loaded")
	}
	
	log.Printf("Loading field classes and fields into cache...")
	
	// Load field classes first
	classes, err := m.loadFieldClassesFromDB()
	if err != nil {
		return fmt.Errorf("failed to load field classes: %w", err)
	}
	
	m.cache.LoadClasses(classes)
	log.Printf("Loaded %d field classes into cache", len(classes))
	
	// Load fields
	fields, err := m.loadFieldsFromDB()
	if err != nil {
		return fmt.Errorf("failed to load fields: %w", err)
	}
	
	m.cache.LoadFields(fields)
	log.Printf("Loaded %d fields into cache", len(fields))
	
	log.Printf("Cache loading completed successfully")
	return nil
}

// loadFieldClassesFromDB loads field classes directly from database (internal method)
func (m *Manager) loadFieldClassesFromDB() ([]models.FieldClass, error) {
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
		var isValue sql.NullInt64
		var updateDate sql.NullTime
		var description sql.NullString

		err := rows.Scan(
			&class.ID,
			&isValue,
			&class.FieldClassName,
			&class.ClassType,
			&class.CreateDate,
			&updateDate,
			&description,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		if isValue.Valid {
			class.IS = &isValue.Int64
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

// loadFieldsFromDB loads fields directly from database (internal method)
func (m *Manager) loadFieldsFromDB() ([]models.Field, error) {
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

// GetFieldClasses retrieves all field classes from cache (fast, thread-safe)
func (m *Manager) GetFieldClasses() ([]models.FieldClass, error) {
	if !m.cache.IsDataLoaded() {
		return nil, fmt.Errorf("cache not loaded yet")
	}
	
	// Return cached data (creates copies for thread safety)
	return m.cache.GetAllClasses(), nil
}

// GetFields retrieves all fields from cache (fast, thread-safe)
func (m *Manager) GetFields() ([]models.Field, error) {
	if !m.cache.IsDataLoaded() {
		return nil, fmt.Errorf("cache not loaded yet")
	}
	
	// Return cached data (creates copies for thread safety)
	return m.cache.GetAllFields(), nil
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

// SubmitExecutionJob submits a job for execution
func (m *Manager) SubmitExecutionJob(jobID, workerDBName string) error {
	if m.currentDB == nil {
		return fmt.Errorf("no database loaded")
	}

	// Update job status to RUNNING
	_, err := m.currentDB.Exec(`
		UPDATE GEE_EXECUTION_JOBS 
		SET STATUS = 'RUNNING', STARTED_AT = CURRENT_TIMESTAMP, WORKER_ID = ?
		WHERE JOB_ID = ?
	`, "praxis-worker-1", jobID)
	
	if err != nil {
		return fmt.Errorf("failed to update job status: %w", err)
	}

	// Start async execution (simplified implementation)
	go m.executeJob(jobID)
	
	return nil
}

// executeJob performs the actual job execution (simplified)
func (m *Manager) executeJob(jobID string) {
	// Get job details
	var flowID int
	var inputData string
	err := m.currentDB.QueryRow(`
		SELECT FLOW_ID, INPUT_DATA FROM GEE_EXECUTION_JOBS WHERE JOB_ID = ?
	`, jobID).Scan(&flowID, &inputData)
	
	if err != nil {
		m.updateJobStatus(jobID, "FAILED", fmt.Sprintf("Failed to get job details: %v", err))
		return
	}

	// Log execution start
	m.addJobLog(jobID, "INFO", "EXECUTION_ENGINE", "Starting flow execution")

	// Simulate execution (in real implementation, this would execute the flow)
	time.Sleep(5 * time.Second) // Simulate work
	
	// Create sample result
	result := map[string]interface{}{
		"status": "completed",
		"flow_id": flowID,
		"input_data": inputData,
		"output": map[string]interface{}{
			"processed_records": 100,
			"execution_time": "5.2s",
			"result": "Flow executed successfully",
		},
		"timestamp": time.Now().Format(time.RFC3339),
	}
	
	resultJSON, _ := json.Marshal(result)
	
	// Save result
	_, err = m.currentDB.Exec(`
		INSERT INTO GEE_EXECUTION_RESULTS (JOB_ID, RESULT_DATA, OUTPUT_TYPE, RESULT_SIZE)
		VALUES (?, ?, 'JSON', ?)
	`, jobID, string(resultJSON), len(resultJSON))
	
	if err != nil {
		m.updateJobStatus(jobID, "FAILED", fmt.Sprintf("Failed to save result: %v", err))
		return
	}

	// Log completion
	m.addJobLog(jobID, "INFO", "EXECUTION_ENGINE", "Flow execution completed successfully")
	
	// Update job status to completed
	m.updateJobStatus(jobID, "COMPLETED", "")
}

// updateJobStatus updates the job status
func (m *Manager) updateJobStatus(jobID, status, errorMessage string) {
	query := `
		UPDATE GEE_EXECUTION_JOBS 
		SET STATUS = ?, COMPLETED_AT = CURRENT_TIMESTAMP, ERROR_MESSAGE = ?
		WHERE JOB_ID = ?
	`
	m.currentDB.Exec(query, status, errorMessage, jobID)
}

// addJobLog adds a log entry for a job
func (m *Manager) addJobLog(jobID, level, component, message string) {
	query := `
		INSERT INTO GEE_EXECUTION_LOGS (JOB_ID, LOG_LEVEL, COMPONENT, LOG_MESSAGE)
		VALUES (?, ?, ?, ?)
	`
	m.currentDB.Exec(query, jobID, level, component, message)
}

// GetJobStatus returns job status
func (m *Manager) GetJobStatus(jobID string) (map[string]interface{}, error) {
	if m.currentDB == nil {
		return nil, fmt.Errorf("no database loaded")
	}

	query := `
		SELECT j.JOB_ID, j.FLOW_ID, j.JOB_TYPE, j.STATUS, j.PRIORITY,
		       j.CREATED_AT, j.STARTED_AT, j.COMPLETED_AT, j.WORKER_ID,
		       j.RETRY_COUNT, j.ERROR_MESSAGE, j.INPUT_DATA, j.EXECUTION_CONFIG
		FROM GEE_EXECUTION_JOBS j
		WHERE j.JOB_ID = ?
	`
	
	var job map[string]interface{}
	var startedAt, completedAt sql.NullTime
	var workerIDVal, errorMessage, inputData, executionConfig sql.NullString
	
	var jobIDVal, jobType, status string
	var flowID, priority, retryCount int
	var createdAt time.Time
	
	err := m.currentDB.QueryRow(query, jobID).Scan(
		&jobIDVal, &flowID, &jobType, &status, &priority,
		&createdAt, &startedAt, &completedAt, &workerIDVal,
		&retryCount, &errorMessage, &inputData, &executionConfig,
	)
	
	if err != nil {
		return nil, fmt.Errorf("failed to get job status: %w", err)
	}
	
	job = map[string]interface{}{
		"job_id":     jobIDVal,
		"flow_id":    flowID,
		"job_type":   jobType,
		"status":     status,
		"priority":   priority,
		"created_at": createdAt,
		"retry_count": retryCount,
	}
	
	if startedAt.Valid {
		job["started_at"] = startedAt.Time
	}
	if completedAt.Valid {
		job["completed_at"] = completedAt.Time
	}
	if workerIDVal.Valid {
		job["worker_id"] = workerIDVal.String
	}
	if errorMessage.Valid {
		job["error_message"] = errorMessage.String
	}
	if inputData.Valid {
		var inputMap map[string]interface{}
		if err := json.Unmarshal([]byte(inputData.String), &inputMap); err == nil {
			job["input_data"] = inputMap
		}
	}
	if executionConfig.Valid {
		var configMap map[string]interface{}
		if err := json.Unmarshal([]byte(executionConfig.String), &configMap); err == nil {
			job["execution_config"] = configMap
		}
	}
	
	return job, nil
}

// GetJobResult returns job execution result
func (m *Manager) GetJobResult(jobID string) (map[string]interface{}, error) {
	if m.currentDB == nil {
		return nil, fmt.Errorf("no database loaded")
	}

	query := `
		SELECT r.RESULT_DATA, r.OUTPUT_TYPE, r.RESULT_SIZE, r.CREATED_AT
		FROM GEE_EXECUTION_RESULTS r
		WHERE r.JOB_ID = ?
	`
	
	var resultData, outputType string
	var resultSize int
	var createdAt time.Time
	
	err := m.currentDB.QueryRow(query, jobID).Scan(&resultData, &outputType, &resultSize, &createdAt)
	if err != nil {
		return nil, fmt.Errorf("failed to get job result: %w", err)
	}
	
	var resultMap map[string]interface{}
	if err := json.Unmarshal([]byte(resultData), &resultMap); err != nil {
		resultMap = map[string]interface{}{"raw_data": resultData}
	}
	
	return map[string]interface{}{
		"job_id":      jobID,
		"result_data": resultMap,
		"output_type": outputType,
		"result_size": resultSize,
		"created_at":  createdAt,
	}, nil
}

// GetJobLogs returns job execution logs
func (m *Manager) GetJobLogs(jobID string) ([]map[string]interface{}, error) {
	if m.currentDB == nil {
		return nil, fmt.Errorf("no database loaded")
	}

	query := `
		SELECT LOG_LEVEL, COMPONENT, LOG_MESSAGE, LOG_TIMESTAMP
		FROM GEE_EXECUTION_LOGS
		WHERE JOB_ID = ?
		ORDER BY LOG_TIMESTAMP ASC
	`
	
	rows, err := m.currentDB.Query(query, jobID)
	if err != nil {
		return nil, fmt.Errorf("failed to query job logs: %w", err)
	}
	defer rows.Close()
	
	var logs []map[string]interface{}
	for rows.Next() {
		var logLevel, message string
		var component sql.NullString
		var timestamp time.Time
		
		err := rows.Scan(&logLevel, &component, &message, &timestamp)
		if err != nil {
			continue
		}
		
		log := map[string]interface{}{
			"log_level":     logLevel,
			"log_message":   message,
			"log_timestamp": timestamp,
		}
		
		if component.Valid {
			log["component"] = component.String
		}
		
		logs = append(logs, log)
	}
	
	return logs, nil
}

// GetWorkerStatus returns worker status for horizontal scaling
func (m *Manager) GetWorkerStatus() ([]map[string]interface{}, error) {
	if m.currentDB == nil {
		return nil, fmt.Errorf("no database loaded")
	}

	query := `
		SELECT WORKER_ID, STATUS, LAST_HEARTBEAT, CURRENT_JOB_ID,
		       MAX_CONCURRENT_JOBS, CURRENT_JOB_COUNT, WORKER_HOST, WORKER_PORT
		FROM GEE_WORKER_STATUS
		ORDER BY WORKER_ID
	`
	
	rows, err := m.currentDB.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query worker status: %w", err)
	}
	defer rows.Close()
	
	var workers []map[string]interface{}
	for rows.Next() {
		var workerID, status string
		var lastHeartbeat time.Time
		var currentJobID sql.NullString
		var maxJobs, currentJobs int
		var workerHost sql.NullString
		var workerPort sql.NullInt64
		
		err := rows.Scan(&workerID, &status, &lastHeartbeat, &currentJobID,
			&maxJobs, &currentJobs, &workerHost, &workerPort)
		if err != nil {
			continue
		}
		
		worker := map[string]interface{}{
			"worker_id":            workerID,
			"status":               status,
			"last_heartbeat":       lastHeartbeat,
			"max_concurrent_jobs":  maxJobs,
			"current_job_count":    currentJobs,
		}
		
		if currentJobID.Valid {
			worker["current_job_id"] = currentJobID.String
		}
		if workerHost.Valid {
			worker["worker_host"] = workerHost.String
		}
		if workerPort.Valid {
			worker["worker_port"] = workerPort.Int64
		}
		
		workers = append(workers, worker)
	}
	
	return workers, nil
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
		
		// Get execution statistics if execution tables exist
		var jobCount, runningJobs int
		m.currentDB.QueryRow("SELECT COUNT(*) FROM GEE_EXECUTION_JOBS").Scan(&jobCount)
		m.currentDB.QueryRow("SELECT COUNT(*) FROM GEE_EXECUTION_JOBS WHERE STATUS = 'RUNNING'").Scan(&runningJobs)
		
		status["execution_stats"] = map[string]int{
			"total_jobs":   jobCount,
			"running_jobs": runningJobs,
		}
	}

	return status
}

// APIEndpoint represents an API endpoint from GEE_API_ENDPOINTS  
type APIEndpoint struct {
	ID               int                    `json:"id"`
	ClassID          int                    `json:"class_id"`
	EndpointPath     string                 `json:"endpoint_path"`
	HTTPMethod       string                 `json:"http_method"`
	OperationID      *string                `json:"operation_id,omitempty"`
	Summary          *string                `json:"summary,omitempty"`
	Description      *string                `json:"description,omitempty"`
	RequestBodyID    *int                   `json:"request_body_id,omitempty"`
	ResponseBodyID   *int                   `json:"response_body_id,omitempty"`
	Parameters       *string                `json:"parameters,omitempty"`
	Tags             *string                `json:"tags,omitempty"`
	ClassName        string                 `json:"class_name"`
	ClassDescription *string                `json:"class_description,omitempty"`
	APIBaseURL       *string                `json:"api_base_url,omitempty"`
	APIVersion       *string                `json:"api_version,omitempty"`
}

// GetAPIEndpoints retrieves all API endpoints with their class information
func (m *Manager) GetAPIEndpoints() ([]APIEndpoint, error) {
	if m.currentDB == nil {
		return nil, fmt.Errorf("no database loaded")
	}

	// Check if the table exists and has the expected schema
	var tableExists int
	err := m.currentDB.QueryRow(`
		SELECT COUNT(*) FROM sqlite_master 
		WHERE type='table' AND name='GEE_API_ENDPOINTS'
	`).Scan(&tableExists)
	
	if err != nil || tableExists == 0 {
		// Table doesn't exist, return empty list
		return []APIEndpoint{}, nil
	}

	// Query GEE_API_ENDPOINTS with proper column names
	query := `
		SELECT 
			e.GAE_ID,
			e.ENDPOINT_PATH,
			e.HTTP_METHOD,
			COALESCE(e.SUMMARY, ''),
			e.GFC_ID,
			c.FIELD_CLASS_NAME
		FROM GEE_API_ENDPOINTS e
		LEFT JOIN GEE_FIELD_CLASSES c ON e.GFC_ID = c.GFC_ID
		ORDER BY e.ENDPOINT_PATH, e.HTTP_METHOD
	`

	rows, err := m.currentDB.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query API endpoints: %w", err)
	}
	defer rows.Close()

	var endpoints []APIEndpoint
	for rows.Next() {
		var ep APIEndpoint
		var summary string
		var className sql.NullString

		err := rows.Scan(
			&ep.ID,
			&ep.EndpointPath,
			&ep.HTTPMethod,
			&summary,
			&ep.ClassID,
			&className,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		// Set values from scan
		ep.Summary = &summary
		if className.Valid {
			ep.ClassName = className.String
		} else {
			ep.ClassName = "Unknown"
		}

		endpoints = append(endpoints, ep)
	}

	return endpoints, nil
}

// GetFieldClassByID retrieves a specific field class by ID from cache
func (m *Manager) GetFieldClassByID(id int64) *models.FieldClass {
	return m.cache.GetClassByID(id)
}

// GetFieldClassByName retrieves a specific field class by name from cache
func (m *Manager) GetFieldClassByName(name string) *models.FieldClass {
	return m.cache.GetClassByName(name)
}

// GetFieldByID retrieves a specific field by ID from cache
func (m *Manager) GetFieldByID(id int64) *models.Field {
	return m.cache.GetFieldByID(id)
}

// GetFieldByName retrieves a specific field by name from cache
func (m *Manager) GetFieldByName(name string) *models.Field {
	return m.cache.GetFieldByName(name)
}

// GetFieldsForClass retrieves all fields for a specific class ID from cache
func (m *Manager) GetFieldsForClass(classID int64) []models.Field {
	return m.cache.GetFieldsForClass(classID)
}

// GetFieldsForClassName retrieves all fields for a specific class name from cache
func (m *Manager) GetFieldsForClassName(className string) []models.Field {
	return m.cache.GetFieldsForClassName(className)
}

// GetCacheStats returns cache statistics
func (m *Manager) GetCacheStats() map[string]interface{} {
	return m.cache.GetCacheStats()
}

// GetCache returns the data cache instance
func (m *Manager) GetCache() *models.DataCache {
	return m.cache
}

// ReloadCache forces a reload of the cache from the database
func (m *Manager) ReloadCache() error {
	if m.currentDB == nil {
		return fmt.Errorf("no database loaded")
	}
	
	m.cache.Clear()
	return m.loadCacheData()
}